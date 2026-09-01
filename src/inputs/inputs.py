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
       "listing": "data/sample_listings/36_kelly_moncton/listing.txt",
       "photos": "data/sample_listings/36_kelly_moncton/photos"
     }
   }

Environment overrides (optional)
--------------------------------
- AIREAL_OUT      -> AppInputs.run.out
- AIREAL_HORIZON  -> AppInputs.run.horizon (int, 1-100; unparseable or out-of-range raises
                     HorizonRangeError -- loud fail, never silently ignored, see Mission 5 OI.3)
- AIREAL_LISTING  -> AppInputs.run.listing
- AIREAL_PHOTOS   -> AppInputs.run.photos
- AIREAL_SCENARIOS-> AppInputs.run.scenarios (truthy 1/true/yes/on enables the scenario overlay)

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

#: `RunOptions.horizon`'s declared bounds -- named constants (not literals) so `Field(ge=...,
#: le=...)` below and every CLI/env/config error message built by `horizon_bounds()` share a
#: single source of truth and cannot drift from each other. (No dependency on
#: `annotated_types` or `RunOptions.model_fields[...].metadata` needed for this -- N5.1.)
HORIZON_MIN = 1
HORIZON_MAX = 100


class RunOptions(BaseModel):
    """Runtime (non-financial) options controlling the analysis run."""

    out: str = Field("investment_analysis.md", description="Path to write the Markdown report.")
    horizon: int = Field(
        10,
        ge=HORIZON_MIN,
        le=HORIZON_MAX,
        description=(
            "Forecast horizon in years. Capped at 100, deliberately: 99-year ground leases and "
            "leaseholds are real financial instruments (see docs/manual testing/"
            "MISSION_4_MANUAL_TESTING.md Case 8), and Mission 4 fixed the IRR solver OverflowError "
            "that made a 99-year horizon crash. No guardrail reads past Year 10 under the shipped "
            "configuration, so years beyond that add rows to the pro forma table without changing "
            "the verdict."
        ),
    )
    listing: str | None = Field(None, description="Path to listing .txt (optional).")
    photos: str | None = Field(None, description="Path to photos folder (optional).")
    engine: str = Field("deterministic", description='Orchestration engine: "deterministic" or "crewai".')
    scenarios: bool = Field(
        False,
        description="Opt-in Market Scenarios overlay (Mission 1). Default OFF; when ON the pipeline runs the market "
        "scenario engine and appends a 'Market Scenarios' report section. Off => byte-identical to today's output.",
    )


class AppInputs(BaseModel):
    """
    Full input payload.

    Attributes:
        inputs: The validated FinancialInputs used by the financial engine.
        run:    Non-financial, runtime options for the current execution.
        market: Optional raw market-snapshot block (region/vacancy_rate/cap_rate/rent_growth/
                expense_growth/interest_rate) used ONLY by the opt-in scenario engine. It is carried
                alongside — deliberately NOT part of the frozen FinancialInputs schema — and parsed by
                ``src.market.snapshot.build_snapshot`` when scenarios are ON.
    """

    inputs: FinancialInputs
    run: RunOptions = RunOptions()
    market: dict[str, Any] | None = None


# ----------------------------
# Horizon out-of-range: one clean line, no traceback (Mission 5 OI.3)
# ----------------------------
#
# `docs/plans/mission-5-discovery/PD1_product_calls.md` §(e). Three entry points can set
# `run.horizon` -- a bare `--horizon` CLI flag, `AIREAL_HORIZON`, and `run.horizon` in the config
# JSON itself -- and all three must fail the same way on an out-of-range or unparseable value: one
# line on stderr naming which of the three the user set, `SystemExit`, exit code 1, no traceback.
# The bounds in every message below are read from `RunOptions.horizon`'s live Field constraints
# (never typed as literals), so a message can never disagree with the rule it describes.


class HorizonRangeError(ValueError):
    """A `run.horizon` value from the CLI, `AIREAL_HORIZON`, or a config file violates the
    declared `RunOptions.horizon` bounds.

    `str(self)` is already the single clean line PD.1 specifies -- no pydantic dump, no "Error:"
    prefix. The CLI entry point (`main.py`) is expected to catch this and re-raise it as
    `SystemExit(str(e))`, matching the convention already at `main.py:200`.
    """


def horizon_bounds() -> tuple[int, int]:
    """Return `RunOptions.horizon`'s declared `(HORIZON_MIN, HORIZON_MAX)` bounds.

    These are the same module constants passed to `RunOptions.horizon`'s `Field(ge=..., le=...)`
    above, so a message built from this can't drift from the schema -- with no dependency on
    `annotated_types` (only a transitive pydantic dependency, never declared in
    `requirements*.txt`/`pyproject.toml`) and no reliance on `RunOptions.model_fields[...]
    .metadata` internals that can move between pydantic releases (N5.1).
    """
    return HORIZON_MIN, HORIZON_MAX


def format_cli_horizon_error(got: int) -> str:
    """The bare `--horizon` flag variant: "Forecast horizon must be between 1 and 100 years; got 101."."""
    lo, hi = horizon_bounds()
    return f"Forecast horizon must be between {lo} and {hi} years; got {got}."


def format_env_horizon_error(raw: str, parsed: int | None) -> str:
    """The `AIREAL_HORIZON` variant. `parsed` is the int value when `raw` parsed but landed
    out of range, or `None` when `raw` could not be parsed as an int at all (quoted in the
    message so "got 'abc'" is unambiguous)."""
    lo, hi = horizon_bounds()
    got = parsed if parsed is not None else repr(raw)
    return f"AIREAL_HORIZON must be a whole number of years between {lo} and {hi}; got {got}."


def format_config_horizon_error(got: int, source_path: str | Path | None) -> str:
    """The config-file variant: names `run.horizon` and the file it came from, e.g.
    "... got 101 (run.horizon in data/my_deal/inputs.json")."""
    lo, hi = horizon_bounds()
    where = f"run.horizon in {source_path}" if source_path is not None else "run.horizon"
    return f"Forecast horizon must be between {lo} and {hi} years; got {got} ({where})."


def validate_cli_horizon(value: int) -> int:
    """Validate a horizon value supplied via a bare CLI flag (no env, no config in play).

    Shared by `InputsLoader.with_overrides` (the `--config` path) and `main.py`'s no-config
    fallback (the `--horizon` bypass PD.1 flagged at `main.py:256`) so both branches enforce the
    exact same rule instead of one of them growing a second, looser door.
    """
    lo, hi = horizon_bounds()
    if not (lo <= value <= hi):
        raise HorizonRangeError(format_cli_horizon_error(value))
    return value


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
        1) ./data/sample_listings/36_kelly_moncton/inputs.json
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
        cfg = self._parse_root(data, source_path=p)
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
        scenarios: bool | None = None,
    ) -> AppInputs:
        """
        Return a *new* AppInputs with provided non-null overrides applied to RunOptions.
        Does not mutate the original instance.

        ``scenarios`` uses ``None`` to mean "no CLI override" (so the ``--scenarios``
        ``store_true`` flag, which is ``False`` when absent, can defer to env/JSON); pass
        ``True`` to force it on.
        """
        updates: dict[str, Any] = {}
        if out is not None:
            updates["out"] = out
        if horizon is not None:
            # Validated here (not left to the generic `_revalidate_run` dump below) so an
            # out-of-range `--horizon` gets PD.1's one clean line, not a per-field pydantic
            # error listing. Raises `HorizonRangeError` (a `ValueError`) on failure.
            updates["horizon"] = validate_cli_horizon(horizon)
        if listing is not None:
            updates["listing"] = listing
        if photos is not None:
            updates["photos"] = photos
        if engine is not None:
            updates["engine"] = engine
        if scenarios is not None:
            updates["scenarios"] = scenarios

        if not updates:
            return cfg

        run_new = self._revalidate_run(cfg.run, updates, source="CLI")
        return cfg.model_copy(update={"run": run_new})

    # ---------- Internals ----------

    def _revalidate_run(self, base: RunOptions, updates: dict[str, Any], *, source: str) -> RunOptions:
        """
        Apply ``updates`` to ``base`` and re-run ``RunOptions``' declared field validators
        (``ge``/``le`` bounds, etc.) against the result.

        ``RunOptions.model_copy(update=...)`` -- used to build the naive merged instance below --
        does **not** re-run pydantic validators (this is documented pydantic v2 behaviour). Every
        override path in this loader (CLI ``with_overrides`` and env-var
        ``_apply_env_overrides``) therefore MUST come back through this method, or a declared
        constraint such as ``horizon: Field(10, ge=1, le=100)`` is silently unenforceable the
        moment it is overridden -- which is exactly the bug this method exists to close (Mission 4
        PV.2; see ``docs/plans/MISSION_4_SPRINT_TRACKER.md`` "SYSTEMIC FINDING").

        Raises:
            ValueError: with a message naming the rejected field(s) and their declared
                constraint(s) -- never a raw ``pydantic.ValidationError`` traceback -- if the
                merged result violates the schema (invariant: "loud fail on misconfig").
        """
        merged = {**base.model_dump(), **updates}
        try:
            return RunOptions.model_validate(merged)
        except ValidationError as e:
            raise ValueError(self._format_override_validation_error(e, source)) from e

    @staticmethod
    def _format_override_validation_error(e: ValidationError, source: str) -> str:
        lines = [f"Rejected {source} override(s) to run options:"]
        for err in e.errors():
            field = ".".join(str(p) for p in err["loc"]) or "<run>"
            lines.append(f"  - {field}: {err['msg']} (got {err.get('input')!r})")
        return "\n".join(lines)

    def _resolve_path(self, path: str | Path | None) -> Path:
        if path is not None:
            p = Path(path)
            if not p.exists():
                raise FileNotFoundError(f"Inputs file not found: {p}")
            return p

        # Default search order
        for candidate in (Path("data/sample_listings/36_kelly_moncton/inputs.json"), Path("config.json")):
            if candidate.exists():
                return candidate
        raise FileNotFoundError(
            "No inputs path provided and no default inputs found. Looked for "
            "./data/sample_listings/36_kelly_moncton/inputs.json and ./config.json."
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

    def _parse_root(self, data: dict[str, Any], *, source_path: str | Path | None = None) -> AppInputs:
        """
        Validate and return structured AppInputs.

        A `run.horizon` value violating its declared bounds gets PD.1's clean, single-line
        `HorizonRangeError` naming `source_path` (Mission 5 OI.3) rather than the raw multi-line
        pydantic dump every other validation failure here still gets (out of scope for this pass;
        see `PD1_product_calls.md` §(c) "Out of scope, noted").
        """
        try:
            return AppInputs.model_validate(data)
        except ValidationError as e:
            horizon_error = self._as_horizon_range_error(e, source_path)
            if horizon_error is not None:
                raise horizon_error from e
            raise ValueError(f"Inputs validation failed:\n{e}") from e

    @staticmethod
    def _as_horizon_range_error(e: ValidationError, source_path: str | Path | None) -> HorizonRangeError | None:
        """If `e` is (among other things) an out-of-bound `run.horizon`, build the config-file
        variant of the clean horizon message; otherwise return None so the generic pydantic dump
        still surfaces for every other kind of validation failure."""
        for err in e.errors():
            loc = tuple(str(p) for p in err["loc"])
            if loc == ("run", "horizon") and err["type"] in ("greater_than_equal", "less_than_equal"):
                # pydantic validates type before ge/le, so by the time a ge/le error fires the
                # input has already been coerced to int; cast records that for the checker.
                got = cast(int, err.get("input"))
                return HorizonRangeError(format_config_horizon_error(got, source_path))
        return None

    def _apply_env_overrides(self, cfg: AppInputs) -> AppInputs:
        """
        Apply light, optional overrides from environment variables to run options.
        """
        prefix = self.env_prefix
        updates: dict[str, Any] = {}

        out = os.getenv(f"{prefix}OUT")
        if out:
            updates["out"] = out

        horizon_raw = os.getenv(f"{prefix}HORIZON")
        if horizon_raw:
            # Unparseable or out-of-range AIREAL_HORIZON is a loud failure (Mission 5 OI.3), not
            # a silently-ignored override: a report produced at a horizon the user did not choose
            # is worse than a traceback (PD1_product_calls.md §(e)).
            lo, hi = horizon_bounds()
            try:
                horizon_val = int(horizon_raw)
            except ValueError:
                raise HorizonRangeError(format_env_horizon_error(horizon_raw, None)) from None
            if not (lo <= horizon_val <= hi):
                raise HorizonRangeError(format_env_horizon_error(horizon_raw, horizon_val))
            updates["horizon"] = horizon_val

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

        scenarios = os.getenv(f"{prefix}SCENARIOS")
        if scenarios is not None and scenarios.strip() != "":
            # Truthy 1/true/yes/on (case-insensitive) enables; anything else explicitly disables.
            updates["scenarios"] = scenarios.strip().lower() in ("1", "true", "yes", "on")

        if not updates:
            return cfg

        run_new = self._revalidate_run(cfg.run, updates, source="environment variable")
        return cfg.model_copy(update={"run": run_new})


# ----------------------------
# Convenience function
# ----------------------------


def load_inputs(path: str | Path | None = None) -> AppInputs:
    """Convenience wrapper for one-shot callers."""
    return InputsLoader().load(path)
