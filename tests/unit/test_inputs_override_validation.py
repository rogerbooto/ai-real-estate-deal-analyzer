# tests/unit/test_inputs_override_validation.py
"""
Defect 1 (Mission 4, PV.2): declared ``RunOptions`` field constraints (``horizon: Field(10, ge=1,
le=100)`` -- ceiling raised from ``50`` to ``100`` in Mission 5 OI.2 -- and friends) must hold no
matter which path sets them, not just JSON construction.

Before the fix, ``InputsLoader.with_overrides`` (CLI) and ``InputsLoader._apply_env_overrides``
(env vars) both applied their override via ``RunOptions.model_copy(update=...)``, which does NOT
re-run pydantic validators -- so an out-of-range ``--horizon`` silently applied anyway despite the
declared ceiling. This file pins that both override paths now re-validate and reject out-of-bound
overrides with a clear, actionable ``ValueError`` (never a raw ``pydantic.ValidationError``
traceback), while still accepting in-bound overrides normally. The out-of-range value used here is
``101`` (the current ceiling is ``100``, raised from ``50`` post-Mission-4) -- see
``tests/integration/test_horizon_range_and_cli_message.py`` for the Mission 5 OI.2/OI.3 coverage
of the raised ceiling itself and the exact clean-message contract (``HorizonRangeError``).
"""

from __future__ import annotations

import json

import pytest

from src.inputs.inputs import InputsLoader
from tests.utils import make_financial_inputs


def _app_json() -> str:
    return json.dumps({"inputs": make_financial_inputs().model_dump()})


@pytest.fixture(autouse=True)
def _clear_horizon_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AIREAL_HORIZON", raising=False)


# ---------------------------------------------------------------------------------------
# CLI override path (InputsLoader.with_overrides)
# ---------------------------------------------------------------------------------------


def test_cli_horizon_override_within_ceiling_applies() -> None:
    loader = InputsLoader()
    cfg = loader.load_json(_app_json())
    cfg2 = loader.with_overrides(cfg, horizon=45)
    assert cfg2.run.horizon == 45


def test_cli_horizon_override_above_declared_ceiling_is_rejected() -> None:
    """
    THE PIN: this is the exact reproduction from the mission brief -- config loads horizon=10,
    `--horizon 101` must no longer silently yield `run.horizon == 101`.
    """
    loader = InputsLoader()
    cfg = loader.load_json(_app_json())
    assert cfg.run.horizon == 10

    with pytest.raises(ValueError) as exc_info:
        loader.with_overrides(cfg, horizon=101)

    message = str(exc_info.value)
    # Clear and actionable: names the field and the declared limit, not a raw pydantic dump.
    assert "horizon" in message
    assert "100" in message
    assert "ValidationError" not in message


def test_cli_horizon_override_above_ceiling_does_not_mutate_original_cfg() -> None:
    loader = InputsLoader()
    cfg = loader.load_json(_app_json())
    with pytest.raises(ValueError):
        loader.with_overrides(cfg, horizon=101)
    assert cfg.run.horizon == 10  # the original, already-validated config is untouched


def test_cli_horizon_override_below_declared_floor_is_rejected() -> None:
    loader = InputsLoader()
    cfg = loader.load_json(_app_json())
    with pytest.raises(ValueError) as exc_info:
        loader.with_overrides(cfg, horizon=0)
    assert "horizon" in str(exc_info.value)


def test_cli_out_override_unaffected_by_horizon_validation() -> None:
    """A non-horizon override still works normally through the same re-validation path."""
    loader = InputsLoader()
    cfg = loader.load_json(_app_json())
    cfg2 = loader.with_overrides(cfg, out="custom_report.md")
    assert cfg2.run.out == "custom_report.md"


# ---------------------------------------------------------------------------------------
# Env override path (InputsLoader._apply_env_overrides, applied inside load/load_json)
# ---------------------------------------------------------------------------------------


def test_env_horizon_override_above_declared_ceiling_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIREAL_HORIZON", "101")
    loader = InputsLoader()
    with pytest.raises(ValueError) as exc_info:
        loader.load_json(_app_json())
    message = str(exc_info.value)
    assert "horizon" in message.lower()
    assert "100" in message
    assert "ValidationError" not in message


def test_env_horizon_override_within_ceiling_applies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIREAL_HORIZON", "30")
    cfg = InputsLoader().load_json(_app_json())
    assert cfg.run.horizon == 30
