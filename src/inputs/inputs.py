# src/inputs/inputs.py
"""
Inputs loader for The AI Real Estate Deal Analyzer (V1+).

Goals
-----
- Deterministic, file-first inputs with validation via Pydantic.
- Backward compatible with the original "FinancialInputs-only" JSON shape.
- Forward-compatible structured shape that includes run options (output path,
  horizon, listing text path, photos folder).
- Minimal environment-variable overrides for CI/CLI convenience.

Supported JSON shapes
---------------------
1) Legacy (root = FinancialInputs)
   {
     ... all FinancialInputs fields here ...
   }

2) Structured (root = AppInputs)
   {
     "inputs": { ... FinancialInputs ... },
     "run": {
       "out": "investment_analysis.md",
       "horizon": 10,
       "listing": "data/sample/listing.txt",
       "photos": "data/sample/photos"
     }
   }

Environment overrides (optional)
--------------------------------
- AIREAL_OUT      -> AppInputs.run.out
- AIREAL_HORIZON  -> AppInputs.run.horizon (int)
- AIREAL_LISTING  -> AppInputs.run.listing
- AIREAL_PHOTOS   -> AppInputs.run.photos

Public API
----------
- class InputsLoader:
    - load(path: str | Path | None) -> AppInputs
    - load_json(text: str) -> AppInputs
    - with_overrides(**kwargs) -> AppInputs (non-destructive copies)
- function load_inputs(path: str | Path | None) -> AppInputs  (convenience)

Notes
-----
- This module *does not* hit the network; all inputs are local.
- Keep thresholds / policies in agents & tools, not in input parsing.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel, Field, ValidationError

from src.schemas.models import FinancialInputs, IncomeModel, UnitIncome

# ----------------------------
# Pydantic models for structured inputs
# ----------------------------


class RunOptions(BaseModel):
    """Runtime (non-financial) options controlling the analysis run."""

    out: str = Field("investment_analysis.md", description="Path to write the Markdown report.")
    horizon: int = Field(10, ge=1, le=50, description="Forecast horizon in years.")
    listing: str | None = Field(None, description="Path to listing .txt (optional).")
    photos: str | None = Field(None, description="Path to photos folder (optional).")
    engine: str = Field("deterministic", description='Orchestration engine: "deterministic" or "crewai".')


class AppInputs(BaseModel):
    """
    Full input payload.

    Attributes:
        inputs: The validated FinancialInputs used by the financial engine.
        run:    Non-financial, runtime options for the current execution.
    """

    inputs: FinancialInputs
    run: RunOptions = RunOptions()


# ----------------------------
# Loader
# ----------------------------


@dataclass(frozen=True)
class InputsLoader:
    """
    File-first inputs loader with light env overrides.

    Responsibilities:
        - Read JSON from a file or string
        - Accept both the legacy and structured shapes
        - Validate with Pydantic
        - Apply environment overrides for run options

    Default search (when path=None):
        1) ./data/sample/inputs.json
        2) ./config.json
    """

    env_prefix: str = "AIREAL_"

    # ---------- Public API ----------

    def load(self, path: str | Path | None = None) -> AppInputs:
        """
        Load inputs from a JSON file (path). If path is None, try defaults.

        Args:
            path: Path to JSON file. If None, uses default search order.

        Returns:
            AppInputs (validated).
        """
        p = self._resolve_path(path)
        raw = self._read_json_file(p)
        data = self._maybe_translate_legacy(raw)
        cfg = self._parse_root(data)
        cfg = self._apply_env_overrides(cfg)
        return cfg

    def load_json(self, text: str) -> AppInputs:
        """
        Load inputs from a JSON string.

        Accepts both the legacy FinancialInputs-only shape and the structured AppInputs shape.
        """
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON payload: {e}") from e
        data = self._maybe_translate_legacy(raw)
        cfg = self._parse_root(data)
        cfg = self._apply_env_overrides(cfg)
        return cfg

    def with_overrides(
        self,
        cfg: AppInputs,
        *,
        out: str | None = None,
        horizon: int | None = None,
        listing: str | None = None,
        photos: str | None = None,
        engine: str | None = None,
    ) -> AppInputs:
        """
        Return a *new* AppInputs with provided non-null overrides applied to RunOptions.
        Does not mutate the original instance.
        """
        updates: dict[str, Any] = {}
        if out is not None:
            updates["out"] = out
        if horizon is not None:
            updates["horizon"] = horizon
        if listing is not None:
            updates["listing"] = listing
        if photos is not None:
            updates["photos"] = photos
        if engine is not None:
            updates["engine"] = engine

        if not updates:
            return cfg

        run_new = cfg.run.model_copy(update=updates)
        return cfg.model_copy(update={"run": run_new})

    # ---------- Internals ----------

    def _resolve_path(self, path: str | Path | None) -> Path:
        if path is not None:
            p = Path(path)
            if not p.exists():
                raise FileNotFoundError(f"Inputs file not found: {p}")
            return p

        # Default search order
        for candidate in (Path("data/sample/inputs.json"), Path("config.json")):
            if candidate.exists():
                return candidate
        raise FileNotFoundError(
            "No inputs path provided and no default inputs found. Looked for ./data/sample/inputs.json and ./config.json."
        )

    def _read_json_file(self, p: Path) -> dict[str, Any]:
        if p.suffix.lower() != ".json":
            raise ValueError(f"Unsupported inputs format for {p.name}; only .json supported in V1.")
        try:
            json_file = json.loads(p.read_text(encoding="utf-8"))
            return cast(dict[str, Any], json_file)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {p}: {e}") from e

    def _maybe_translate_legacy(self, raw: dict[str, Any]) -> dict[str, Any]:
        """
        Accept legacy (FinancialInputs at root) or structured (AppInputs shape).
        If legacy 'income' uses a scalar model (units:int + rent_month:float),
        expand it into a per-unit list by splitting totals evenly.
        NOTE: This is a best-effort bridge; prefer the new per-unit shape.
        """
        if "inputs" in raw:
            return raw  # already structured

        # Legacy shape: FinancialInputs at root
        income = raw.get("income")
        if isinstance(income, dict) and "units" in income and "rent_month" in income and isinstance(income["units"], int):
            unit_count = max(1, int(income["units"]))
            total_rent = float(income.get("rent_month", 0.0))
            other_total = float(income.get("other_income_month", 0.0))
            per_unit_rent = total_rent / unit_count if unit_count > 0 else 0.0
            per_unit_other = other_total / unit_count if unit_count > 0 else 0.0
            raw["income"] = IncomeModel(
                units=[UnitIncome(rent_month=per_unit_rent, other_income_month=per_unit_other) for _ in range(unit_count)],
                occupancy=income.get("occupancy", 0.97),
                bad_debt_factor=income.get("bad_debt_factor", 0.90),
                rent_growth=income.get("rent_growth", 0.03),
            ).model_dump()

        return {"inputs": raw}

    def _parse_root(self, data: dict[str, Any]) -> AppInputs:
        """
        Validate and return structured AppInputs.
        """
        try:
            return AppInputs.model_validate(data)
        except ValidationError as e:
            raise ValueError(f"Inputs validation failed:\n{e}") from e

    def _apply_env_overrides(self, cfg: AppInputs) -> AppInputs:
        """
        Apply light, optional overrides from environment variables to run options.
        """
        prefix = self.env_prefix
        updates: dict[str, Any] = {}

        out = os.getenv(f"{prefix}OUT")
        if out:
            updates["out"] = out

        horizon = os.getenv(f"{prefix}HORIZON")
        if horizon:
            try:
                updates["horizon"] = int(horizon)
            except ValueError:
                # Ignore bad value; keep validated cfg.horizon
                pass

        listing = os.getenv(f"{prefix}LISTING")
        if listing:
            updates["listing"] = listing

        photos = os.getenv(f"{prefix}PHOTOS")
        if photos:
            updates["photos"] = photos

        engine = os.getenv(f"{prefix}ENGINE")
        if engine:
            normalized = engine.strip().lower()
            if normalized in ("deterministic", "crewai"):
                updates["engine"] = normalized

        if not updates:
            return cfg

        run_new = cfg.run.model_copy(update=updates)
        return cfg.model_copy(update={"run": run_new})


# ----------------------------
# Convenience function
# ----------------------------


def load_inputs(path: str | Path | None = None) -> AppInputs:
    """Convenience wrapper for one-shot callers."""
    return InputsLoader().load(path)
