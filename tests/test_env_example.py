# tests/test_env_example.py
"""`.env.example` must stay truthful, because it is the reproducibility contract.

`.env` is gitignored and VS Code auto-loads it, so `.env.example` is the only committed
record of which knobs exist and what they default to. Two ways it can lie, both of which
have already happened in this repo:

  1. It documents a value that is NOT the code default — the previous version shipped
     `AIREAL_CAP_DRIFT_BPS=5` against a code default of `0`, so anyone who copied it got a
     drifting cap rate and a report nobody else could reproduce.
  2. A new env var gets read by the code and never documented here.

These tests fail on both.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ENV_EXAMPLE = REPO / ".env.example"

# Vars the code reads but that are intentionally not assigned a default in .env.example:
# they are path/run overrides that must defer to the config file when unset.
_COMMENTED_BY_DESIGN = {
    "AIREAL_OUT",
    "AIREAL_HORIZON",
    "AIREAL_LISTING",
    "AIREAL_PHOTOS",
    "AIREAL_ENGINE",
}

# Defaults asserted against the literal defaults in the source. Keeping this list explicit
# (rather than importing the accessors) means a change to either side must be deliberate.
_EXPECTED_DEFAULTS = {
    "AIREAL_CAP_DRIFT_BPS": "0",
    "AIREAL_APPRECIATION_PCT": "0.03",
    "AIREAL_STRESS_ADJ": "0.0",
    "AIREAL_USE_VISION": "0",
    "AIREAL_SCENARIOS": "0",
}


def _source_files() -> list[Path]:
    return [*(REPO / "src").rglob("*.py"), REPO / "main.py"]


def _env_vars_read_by_code() -> set[str]:
    """Names read via a literal getenv, plus the f-string prefix form used by InputsLoader."""
    literal = re.compile(r"getenv\(\s*[\"'](AIREAL_[A-Z0-9_]+)[\"']")
    prefixed = re.compile(r"getenv\(\s*f[\"']\{prefix\}([A-Z0-9_]+)[\"']")

    found: set[str] = set()
    for path in _source_files():
        text = path.read_text(encoding="utf-8")
        found.update(literal.findall(text))
        found.update(f"AIREAL_{name}" for name in prefixed.findall(text))
    return found


def _documented_vars() -> dict[str, str | None]:
    """Map documented name -> assigned value, or None when present only as a comment."""
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    documented: dict[str, str | None] = {}

    for raw in text.splitlines():
        line = raw.strip()
        assigned = re.match(r"^(AIREAL_[A-Z0-9_]+)=(.*)$", line)
        if assigned:
            documented[assigned.group(1)] = assigned.group(2).split("#")[0].strip()
            continue
        mentioned = re.search(r"\b(AIREAL_[A-Z0-9_]+)\b", line)
        if mentioned and mentioned.group(1) not in documented:
            documented[mentioned.group(1)] = None
    return documented


def test_env_example_exists_and_is_committed() -> None:
    assert ENV_EXAMPLE.is_file(), ".env.example is the only committed record of the env contract"


def test_every_env_var_the_code_reads_is_documented() -> None:
    undocumented = _env_vars_read_by_code() - set(_documented_vars())
    assert not undocumented, f"read by code but absent from .env.example: {sorted(undocumented)}"


def test_documented_values_match_the_code_defaults() -> None:
    documented = _documented_vars()
    wrong = {name: (documented.get(name), expected) for name, expected in _EXPECTED_DEFAULTS.items() if documented.get(name) != expected}
    assert not wrong, f"documented value != code default (name: (documented, expected)): {wrong}"


def test_run_override_vars_are_left_unset() -> None:
    # These must stay commented out: an assigned value would override the config file for
    # every run, which is precisely the surprise this file exists to prevent.
    documented = _documented_vars()
    assigned = [n for n in _COMMENTED_BY_DESIGN if documented.get(n) is not None]
    assert not assigned, f"should be commented out, not assigned: {sorted(assigned)}"


def test_unimplemented_vars_are_flagged_and_never_assigned() -> None:
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    read_by_code = _env_vars_read_by_code()

    for name in ("AIREAL_PHOTO_AGENT", "AIREAL_VISION_PROVIDER", "AIREAL_VISION_MODEL"):
        assert name not in read_by_code, f"{name} is now implemented — move it out of the unimplemented list"
        assert name in text, f"{name} should be listed as unimplemented so it is not copied forward"
        assert not re.search(rf"^{name}=", text, flags=re.MULTILINE), f"{name} is assigned but nothing reads it"
