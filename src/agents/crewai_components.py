# src/agents/crewai_components.py
"""
CrewAI Agent wrappers (V2 seam)

Purpose
-------
Provide thin CrewAI Agent/Task shells that *delegate to deterministic*
local Python functions. This keeps tests deterministic and makes it easy
to swap in real LLM reasoning later by changing only the .run() bodies
or by adding tool-calling prompts.

Design
------
- No network calls here by default.
- Construct Agent/Task objects for future parity, but .run() calls the
  existing V1 functions under src/agents/* and src/tools/* unless the
  LLM branch is explicitly enabled via env.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

try:
    # Optional import: present when users actually run with engine="crewai"
    from crewai import Agent, Crew, Process, Task

    _CREW_AVAILABLE = True
except Exception:  # pragma: no cover - exercised by smoke test
    _CREW_AVAILABLE = False

import json
import logging
import os
import re
import sys
import traceback
from logging.handlers import RotatingFileHandler

from pydantic import BaseModel, TypeAdapter

from src.agents.chief_strategist import synthesize_thesis

# deterministic local functions
from src.agents.financial_forecaster import forecast_financials
from src.agents.listing_analyst import analyze_listing
from src.schemas.models import (
    FinancialForecast,
    FinancialInputs,
    InvestmentThesis,
    ListingInsights,
)

# -----------------------------
# Logging / debug helpers
# -----------------------------

_LOGGER: logging.Logger | None = None


def _get_debug_logger() -> logging.Logger:
    """Create/reuse a rotating file logger for CrewAI debug output."""
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER

    logger = logging.getLogger("crewai_debug")
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers if reloaded in REPL/tests
    if not logger.handlers:
        log_path = os.path.join("logs", "crewai_debug.log")
        try:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
        except Exception:
            # don't fail just because we couldn't create the directory
            pass

        try:
            handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
            formatter = logging.Formatter(
                fmt="%(asctime)s %(levelname)s %(message)s",
                datefmt="(%Y-%m-%d %H:%M:%S)",
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        except Exception:
            # If file handler fails, we still return the logger without handlers.
            # stderr printing in _print_debug_exc keeps working.
            pass

    _LOGGER = logger
    return logger


def _debug_enabled() -> bool:
    return os.getenv("AIREAL_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}


def _print_debug_exc(prefix: str, exc: BaseException) -> None:
    """Always print errors to console (stderr) and best-effort log to file."""
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

    # Basic redaction: remove obvious keys if they appear in a message
    def _redact(s: str) -> str:
        for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY"):
            val = os.getenv(k)
            if val:
                s = s.replace(val, "[REDACTED]")
        return s

    redacted_tb = _redact(tb)
    redacted_msg = _redact(f"{prefix}: {exc}\n{redacted_tb}")

    # stderr (unconditional)
    print(f"[CREWAI ERROR] {redacted_msg}", file=sys.stderr, flush=True)

    # rotating file log (best-effort)
    try:
        logger = _get_debug_logger()
        if logger.handlers:
            logger.error(redacted_msg)
    except Exception:
        # never break the app from logging issues
        pass


def _print_raw_preview(text: str, label: str) -> None:
    if not _debug_enabled():
        return
    preview = text if len(text) <= 5000 else text[:5000] + "…"
    line = f"[CREWAI DEBUG] {label} (preview, first 5000 chars):\n{preview}\n"
    print(line, file=sys.stderr)
    try:
        logger = _get_debug_logger()
        if logger.handlers:
            logger.debug(line)
    except Exception:
        pass


# -----------------------------
# Config helpers
# -----------------------------

T = TypeVar("T", bound=BaseModel)


def _llm_enabled() -> bool:
    """Check if LLM reasoning is enabled."""
    v = os.getenv("AIREAL_LLM_MODE", "").strip()
    return v in {"1", "true", "yes", "on"}


def _get_model_name() -> str:
    """Get the model name for CrewAI or OpenAI."""
    return os.getenv("CREWAI_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"


def _ensure_crewai_ready() -> bool:
    """Check if CrewAI is ready to use."""
    if not _CREW_AVAILABLE:
        return False
    if any(os.getenv(k) for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY")):
        return True
    return False


# -----------------------------
# JSON parsing helper
# -----------------------------


def _sanitize_json_like(text: str) -> str:
    """Best-effort cleanup of model output into strict JSON.

    - Strips code fences and markdown artifacts
    - Removes unicode ellipsis and zero-width spaces
    - Replaces NaN/Infinity/-Infinity with null
    - Removes trailing commas before '}' or ']'
    - Collapses duplicate commas and stray commas after braces/brackets
    - Trims to the outermost JSON object/array
    """
    if not isinstance(text, str):
        return text

    s = text.strip()

    # Strip common markdown fences
    # ```json ... ``` or ``` ... ```
    s = re.sub(r"^[\s`]*json[\s`]*\n", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE | re.MULTILINE)
    s = re.sub(r"\s*```$", "", s, flags=re.MULTILINE)

    # Remove zero-width spaces and non-printing junk
    s = s.replace("\u200b", "").replace("\ufeff", "")

    # Remove unicode ellipsis (often shows up when models truncate)
    s = s.replace("…", "")

    # Heuristic: trim to outermost JSON object or array
    first_obj = s.find("{")
    first_arr = s.find("[")
    candidates = [i for i in [first_obj, first_arr] if i != -1]
    if candidates:
        start = min(candidates)
        # try matching closing brace/bracket from the end
        last_obj = s.rfind("}")
        last_arr = s.rfind("]")
        ends = [i for i in [last_obj, last_arr] if i != -1]
        if ends:
            end = max(ends)
            if end > start:
                s = s[start : end + 1]

    # Replace invalid JSON numbers with null
    s = re.sub(r"\bNaN\b", "null", s)
    s = re.sub(r"\bInfinity\b", "null", s)
    s = re.sub(r"\b-Infinity\b", "null", s)

    # Remove trailing commas before } or ]
    # e.g., {"a":1,} or [1,2,]
    s = re.sub(r",\s*([}\]])", r"\1", s)

    # Remove stray commas after opening { or [
    s = re.sub(r"([\{\[])\s*,\s*", r"\1", s)

    # Collapse duplicate commas ", ,"
    s = re.sub(r",\s*,+", ",", s)

    return s


def _parse_json_as(model_cls: type[T], text: str, fallback: Callable[[], T]) -> T:
    """Parse JSON text into a Pydantic model instance."""
    cleaned = _sanitize_json_like(text)

    # Strict parse
    try:
        return model_cls.model_validate_json(cleaned)
    except Exception as e:
        _print_debug_exc(f"_parse_json_as initial parse failed for {model_cls.__name__}", e)
        _print_raw_preview(cleaned, f"{model_cls.__name__} cleaned output")

    # Tolerant parse
    try:
        adapter = TypeAdapter(model_cls)  # pydantic's typing can be loose here
        return adapter.validate_json(cleaned)
    except Exception as e:
        _print_debug_exc(f"_parse_json_as TypeAdapter parse failed for {model_cls.__name__}", e)

    # Blob (object) strict
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            blob = _sanitize_json_like(text[start : end + 1])
            return model_cls.model_validate_json(blob)
    except Exception as e2:
        _print_debug_exc(f"_parse_json_as blob strict parse failed for {model_cls.__name__}", e2)

    # Blob (object) tolerant
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            blob = _sanitize_json_like(text[start : end + 1])
            adapter2 = TypeAdapter(model_cls)
            return adapter2.validate_json(blob)
    except Exception as e3:
        _print_debug_exc(f"_parse_json_as blob TypeAdapter parse failed for {model_cls.__name__}", e3)

    # Top-level array strict
    try:
        first_arr = text.find("[")
        last_arr = text.rfind("]")
        if first_arr != -1 and last_arr != -1 and last_arr > first_arr:
            arr_blob = _sanitize_json_like(text[first_arr : last_arr + 1])
            return model_cls.model_validate_json(arr_blob)
    except Exception:
        pass

    return fallback()


# -----------------------------
# Agents
# -----------------------------


class ListingAnalystAgent:
    """CrewAI wrapper that deterministically produces ListingInsights."""

    def __init__(self) -> None:
        if _CREW_AVAILABLE:
            self.agent = Agent(
                role="Listing Analyst",
                goal="Extract high-signal insights from local listing assets.",
                backstory="Parses local listing text and tags photos using a CV stub.",
                verbose=False,
                allow_delegation=False,
                llm=_get_model_name(),
            )
            self.task = Task(
                description=(
                    "Analyze local listing text and photos and produce ListingInsights "
                    "(address, amenities, notes, condition_tags, defects). "
                    "Respond with JSON ONLY that matches the ListingInsights schema."
                ),
                expected_output="JSON matching ListingInsights",
                agent=self.agent,
            )

    def _run_llm(self, listing_txt_path: str | None, photos_folder: str | None) -> ListingInsights:
        if not _ensure_crewai_ready():
            # No model/keys: fallback to deterministic
            return analyze_listing(listing_txt_path=listing_txt_path, photos_folder=photos_folder)

        # Compose compact, deterministic context (no heavy file I/O—keep it simple)
        listing_text = ""
        try:
            if listing_txt_path and os.path.exists(listing_txt_path):
                listing_text = open(listing_txt_path, encoding="utf-8").read()[:8000]
        except Exception:
            pass
        photo_names = []
        try:
            if photos_folder and os.path.isdir(photos_folder):
                photo_names = sorted([p for p in os.listdir(photos_folder) if "." in p])[:24]
        except Exception:
            pass

        prompt = (
            "You are a meticulous real-estate listing analyst. "
            "Given a listing text and photo filenames, produce a structured summary.\n\n"
            "Return JSON ONLY in this shape:\n"
            "{\n"
            '  "address": "str | null",\n'
            '  "amenities": ["str", ...],\n'
            '  "notes": ["str", ...],\n'
            '  "condition_tags": ["str", ...],\n'
            '  "defects": ["str", ...]\n'
            "}\n\n"
            "Do not use ellipses; output MUST be complete and valid JSON without truncation.\n"
            "Do not include comments or trailing commas.\n"
            f"LISTING_TEXT:\n{listing_text}\n\n"
            f"PHOTOS:\n{photo_names}\n"
        )

        try:
            task = Task(
                description=prompt,
                expected_output="JSON for ListingInsights only.",
                agent=self.agent,
            )

            # Run via a Crew (Task has no .execute())
            crew = Crew(
                agents=[self.agent],
                tasks=[task],
                process=Process.sequential,
                verbose=False,
            )
            _ = crew.kickoff()

            # Pull result from task.output
            result_text = getattr(task, "output", None) or ""
            return _parse_json_as(
                ListingInsights,
                str(result_text),
                lambda: analyze_listing(listing_txt_path=listing_txt_path, photos_folder=photos_folder),
            )
        except Exception as e:
            # cache & print, then fallback
            try:
                self._last_llm_error = e  # stash for programmatic access
            except Exception:
                pass
            _print_debug_exc("ListingAnalystAgent.crew.kickoff failed", e)
            return analyze_listing(listing_txt_path=listing_txt_path, photos_folder=photos_folder)

    def run(self, listing_txt_path: str | None, photos_folder: str | None) -> ListingInsights:
        if _llm_enabled():
            return self._run_llm(listing_txt_path, photos_folder)
        return analyze_listing(listing_txt_path=listing_txt_path, photos_folder=photos_folder)


class FinancialForecasterAgent:
    """Deterministic wrapper that produces FinancialForecast via local engine.

    Intentionally *not* LLM-backed: financial math must be exact, reproducible,
    and fast. We keep an Agent/Task (if crewai is present) only for future
    parity/observability, but .run() always calls forecast_financials.
    """

    def __init__(self) -> None:
        if _CREW_AVAILABLE:
            self.agent = Agent(
                role="Financial Forecaster (Deterministic)",
                goal="Generate a rigorous, deterministic financial forecast using the local model.",
                backstory="Wraps the local financial model engine; no LLM reasoning.",
                verbose=False,
                allow_delegation=False,
                llm=None,  # explicitly no model
            )
            self.task = Task(
                description=(
                    "Run the local financial model to produce NOI, DSCR, cash flows, IRR, and equity multiple "
                    "for the specified horizon. This is a deterministic computation; do not call an LLM."
                ),
                expected_output="A valid FinancialForecast object (Pydantic).",
                agent=self.agent,
            )

    def run(
        self,
        inputs: FinancialInputs,
        insights: ListingInsights | None,
        horizon_years: int,
    ) -> FinancialForecast:
        # Hard clamp horizon for safety
        if horizon_years < 1:
            horizon_years = 1
        elif horizon_years > 50:
            horizon_years = 50

        return forecast_financials(inputs=inputs, insights=insights, horizon_years=horizon_years)


class ChiefStrategistAgent:
    """CrewAI wrapper that deterministically produces an InvestmentThesis."""

    def __init__(self) -> None:
        if _CREW_AVAILABLE:
            self.agent = Agent(
                role="Chief Strategist",
                goal="Synthesize a clear, defensible investment thesis.",
                backstory="Applies rule-based guardrails and levers.",
                verbose=False,
                allow_delegation=False,
                llm=_get_model_name(),
            )
            self.task = Task(
                description=(
                    "Given FinancialForecast (+ optional ListingInsights), produce a BUY/CONDITIONAL/PASS thesis. "
                    "Respond with JSON ONLY matching InvestmentThesis."
                ),
                expected_output="JSON matching InvestmentThesis",
                agent=self.agent,
            )

    def _run_llm(
        self,
        forecast: FinancialForecast,
        insights: ListingInsights | None = None,
    ) -> InvestmentThesis:
        if not _ensure_crewai_ready():
            return synthesize_thesis(forecast)

        payload = {
            "forecast": forecast.model_dump(),
            "listing_insights": insights.model_dump() if insights else None,
        }

        prompt = (
            "You are a buy-side real-estate chief strategist.\n"
            "Given a FinancialForecast (+ optional ListingInsights), "
            "produce a clear investment thesis.\n\n"
            "Respond with JSON ONLY that conforms to the InvestmentThesis schema. "
            "No prose, no markdown, no extra text.\n\n"
            "Schema:\n"
            '{ "verdict": "BUY|CONDITIONAL|PASS",\n'
            '  "rationale": ["string", ...],\n'
            '  "key_metrics": { "dscr": float, "irr": float, "coc": float }\n'
            "}\n\n"
            "Do not use ellipses; output MUST be complete and valid JSON without truncation.\n"
            "Do not include comments or trailing commas.\n"
            f"DATA:\n{json.dumps(payload, indent=2)}"
        )

        try:
            task = Task(
                description=prompt,
                expected_output="JSON for InvestmentThesis only.",
                agent=self.agent,
            )

            crew = Crew(
                agents=[self.agent],
                tasks=[task],
                process=Process.sequential,
                verbose=False,
            )
            _ = crew.kickoff()

            result_text = getattr(task, "output", None) or ""
            return _parse_json_as(
                InvestmentThesis,
                str(result_text),
                lambda: synthesize_thesis(forecast),
            )
        except Exception as e:
            try:
                self._last_llm_error = e
            except Exception:
                pass
            _print_debug_exc("ChiefStrategistAgent.crew.kickoff failed", e)
            return synthesize_thesis(forecast)

    def run(
        self,
        forecast: FinancialForecast,
        insights: ListingInsights | None = None,
    ) -> InvestmentThesis:
        if _llm_enabled():
            return self._run_llm(forecast, insights)
        return synthesize_thesis(forecast)
