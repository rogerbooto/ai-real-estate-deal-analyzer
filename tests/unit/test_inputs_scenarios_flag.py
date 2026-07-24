# tests/unit/test_inputs_scenarios_flag.py
"""Opt-in wiring for the Market Scenarios overlay (Mission 1, Wave 2, Task 2.3).

Pins the additive ``RunOptions.scenarios`` field and its precedence:
    explicit CLI flag (with_overrides) > env AIREAL_SCENARIOS > JSON run.scenarios > default False.
Also pins that the raw ``market`` block is carried on ``AppInputs`` (not the frozen FinancialInputs).
"""

from __future__ import annotations

import json

import pytest

from src.inputs.inputs import InputsLoader
from tests.utils import make_financial_inputs


def _app_json(*, scenarios: bool | None = None, with_market: bool = False) -> str:
    payload: dict = {"inputs": make_financial_inputs().model_dump()}
    if scenarios is not None:
        payload["run"] = {"scenarios": scenarios}
    if with_market:
        payload["market"] = {
            "region": "Moncton, NB",
            "vacancy_rate": 0.06,
            "cap_rate": 0.055,
            "rent_growth": 0.03,
            "expense_growth": 0.02,
            "interest_rate": 0.055,
        }
    return json.dumps(payload)


@pytest.fixture(autouse=True)
def _clear_scenarios_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Ensure no ambient AIREAL_SCENARIOS leaks into the precedence assertions.
    monkeypatch.delenv("AIREAL_SCENARIOS", raising=False)


def test_default_is_off() -> None:
    cfg = InputsLoader().load_json(_app_json())
    assert cfg.run.scenarios is False


def test_json_true_enables() -> None:
    cfg = InputsLoader().load_json(_app_json(scenarios=True))
    assert cfg.run.scenarios is True


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "On"])
def test_env_truthy_enables(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("AIREAL_SCENARIOS", value)
    cfg = InputsLoader().load_json(_app_json())
    assert cfg.run.scenarios is True


def test_env_overrides_json_true_to_false(monkeypatch: pytest.MonkeyPatch) -> None:
    # env is more specific than JSON: an explicit falsy env disables a JSON-on value.
    monkeypatch.setenv("AIREAL_SCENARIOS", "0")
    cfg = InputsLoader().load_json(_app_json(scenarios=True))
    assert cfg.run.scenarios is False


def test_env_overrides_json_false_to_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIREAL_SCENARIOS", "yes")
    cfg = InputsLoader().load_json(_app_json(scenarios=False))
    assert cfg.run.scenarios is True


def test_cli_flag_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Explicit CLI flag (with_overrides scenarios=True) beats an env that would disable it.
    monkeypatch.setenv("AIREAL_SCENARIOS", "0")
    loader = InputsLoader()
    cfg = loader.load_json(_app_json(scenarios=True))
    assert cfg.run.scenarios is False  # env won so far
    cfg2 = loader.with_overrides(cfg, scenarios=True)
    assert cfg2.run.scenarios is True


def test_with_overrides_none_is_noop() -> None:
    loader = InputsLoader()
    cfg = loader.load_json(_app_json(scenarios=True))
    cfg2 = loader.with_overrides(cfg, scenarios=None)
    assert cfg2.run.scenarios is True


def test_market_block_carried_on_appinputs() -> None:
    cfg = InputsLoader().load_json(_app_json(with_market=True))
    assert cfg.market is not None
    assert cfg.market["region"] == "Moncton, NB"
    assert cfg.market["cap_rate"] == 0.055


def test_market_block_absent_is_none() -> None:
    cfg = InputsLoader().load_json(_app_json())
    assert cfg.market is None
