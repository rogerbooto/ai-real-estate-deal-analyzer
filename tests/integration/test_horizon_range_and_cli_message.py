# tests/integration/test_horizon_range_and_cli_message.py
"""
Mission 5 OI.2 + OI.3 (Gate D, PD.1 §(d)/(e)): the forecast horizon ceiling and the CLI's
out-of-range/unparseable horizon behaviour.

OI.2: ``RunOptions.horizon`` is raised from ``le=50`` to ``le=100`` -- a real financial
instrument (a 99-year ground lease; see ``docs/manual testing/MISSION_4_MANUAL_TESTING.md``
Case 8) is otherwise blocked for no reason anyone chose. 100 is accepted, 101 is rejected.

OI.3: an out-of-range or unparseable horizon -- via a bare ``--horizon`` flag, ``AIREAL_HORIZON``,
or ``run.horizon`` in a config JSON -- fails with ONE clean line on stderr, ``SystemExit``, exit
code 1, no traceback. The bounds in the message are read from ``RunOptions.horizon``'s live Field
constraints (``src.inputs.inputs.horizon_bounds``), never typed as literals, so the message cannot
disagree with the schema. Two further holes folded into this same defect (PD.1 §(e)):
``main.py``'s no-config fallback used to do ``args.horizon or 10``, bypassing validation entirely
(and silently turning a legitimate ``--horizon 0`` into 10); and ``AIREAL_HORIZON=abc`` used to be
silently ignored rather than failing loudly.

Two test styles are used deliberately:
  - In-process (``main_module.main()`` with the orchestrator spied out) for the fast, exact-message
    assertions and for "no financials reached the pipeline" checks.
  - Real ``subprocess`` runs of ``python main.py`` for the "the real process prints one line to
    stderr, no traceback, and exits 1" claim -- that is a property of the interpreter's top-level
    ``SystemExit`` handling, not something an in-process ``pytest.raises`` can observe.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import ValidationError

import main as main_module
from src.inputs.inputs import HorizonRangeError, InputsLoader, RunOptions, horizon_bounds

REPO_ROOT = Path(__file__).resolve().parents[2]
BUNDLE_CONFIG = REPO_ROOT / "data" / "sample_listings" / "36_kelly_moncton" / "inputs.json"


# ---------------------------------------------------------------------------------------
# OI.2: RunOptions.horizon bounds themselves
# ---------------------------------------------------------------------------------------


def test_horizon_bounds_are_1_and_100() -> None:
    """Pins the read-from-schema helper OI.3's messages depend on, and the OI.2 ceiling itself."""
    assert horizon_bounds() == (1, 100)


def test_horizon_100_accepted() -> None:
    ro = RunOptions(horizon=100)
    assert ro.horizon == 100


def test_horizon_101_rejected() -> None:
    with pytest.raises(ValidationError):
        RunOptions(horizon=101)


def test_horizon_99_accepted_the_ground_lease_case() -> None:
    """The concrete instrument that justifies the raised ceiling (PD.1 §(d))."""
    ro = RunOptions(horizon=99)
    assert ro.horizon == 99


# ---------------------------------------------------------------------------------------
# OI.3: message formatting reads bounds from the schema, never literals
# ---------------------------------------------------------------------------------------


def test_cli_message_names_current_bounds() -> None:
    from src.inputs.inputs import format_cli_horizon_error

    msg = format_cli_horizon_error(101)
    assert msg == "Forecast horizon must be between 1 and 100 years; got 101."


def test_env_message_for_unparseable_value() -> None:
    from src.inputs.inputs import format_env_horizon_error

    msg = format_env_horizon_error("abc", None)
    assert msg == "AIREAL_HORIZON must be a whole number of years between 1 and 100; got 'abc'."


def test_env_message_for_out_of_range_value() -> None:
    from src.inputs.inputs import format_env_horizon_error

    msg = format_env_horizon_error("200", 200)
    assert msg == "AIREAL_HORIZON must be a whole number of years between 1 and 100; got 200."


def test_config_message_names_the_file() -> None:
    from src.inputs.inputs import format_config_horizon_error

    msg = format_config_horizon_error(101, "data/my_deal/inputs.json")
    assert msg == "Forecast horizon must be between 1 and 100 years; got 101 (run.horizon in data/my_deal/inputs.json)."


# ---------------------------------------------------------------------------------------
# OI.3: InputsLoader raises HorizonRangeError (never a silent ignore, never a raw ValidationError)
# ---------------------------------------------------------------------------------------


def test_env_horizon_unparseable_fails_loudly_not_silently(monkeypatch: pytest.MonkeyPatch) -> None:
    """THE PIN for the silent-ignore hole: AIREAL_HORIZON=abc used to be caught and dropped,
    leaving cfg.horizon at its previously-validated value with no line of output saying so."""
    monkeypatch.setenv("AIREAL_HORIZON", "abc")
    loader = InputsLoader()
    with pytest.raises(HorizonRangeError) as exc_info:
        loader.load(str(BUNDLE_CONFIG))
    assert str(exc_info.value) == "AIREAL_HORIZON must be a whole number of years between 1 and 100; got 'abc'."


def test_env_horizon_out_of_range_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIREAL_HORIZON", "101")
    loader = InputsLoader()
    with pytest.raises(HorizonRangeError) as exc_info:
        loader.load(str(BUNDLE_CONFIG))
    assert str(exc_info.value) == "AIREAL_HORIZON must be a whole number of years between 1 and 100; got 101."


def test_env_horizon_100_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIREAL_HORIZON", "100")
    cfg = InputsLoader().load(str(BUNDLE_CONFIG))
    assert cfg.run.horizon == 100


def test_cli_override_horizon_101_rejected() -> None:
    loader = InputsLoader()
    cfg = loader.load(str(BUNDLE_CONFIG))
    with pytest.raises(HorizonRangeError) as exc_info:
        loader.with_overrides(cfg, horizon=101)
    assert str(exc_info.value) == "Forecast horizon must be between 1 and 100 years; got 101."


def test_cli_override_horizon_100_accepted() -> None:
    loader = InputsLoader()
    cfg = loader.load(str(BUNDLE_CONFIG))
    cfg2 = loader.with_overrides(cfg, horizon=100)
    assert cfg2.run.horizon == 100


def test_config_json_horizon_101_rejected(tmp_path: Path) -> None:
    import json

    raw = json.loads(BUNDLE_CONFIG.read_text(encoding="utf-8"))
    raw["run"] = {"horizon": 101}
    bad = tmp_path / "bad_horizon.json"
    bad.write_text(json.dumps(raw), encoding="utf-8")

    loader = InputsLoader()
    with pytest.raises(HorizonRangeError) as exc_info:
        loader.load(str(bad))
    assert str(exc_info.value) == f"Forecast horizon must be between 1 and 100 years; got 101 (run.horizon in {bad})."


# ---------------------------------------------------------------------------------------
# OI.3: main.py's no-config fallback validates through the same door (main.py:256 hole)
# ---------------------------------------------------------------------------------------


class _OrchestratorSpy:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(
            insights=None,
            forecast=None,
            thesis=SimpleNamespace(verdict="DECLINE"),
            media_insights=None,
            media_report=None,
        )


@pytest.fixture()
def spy(monkeypatch: pytest.MonkeyPatch) -> _OrchestratorSpy:
    s = _OrchestratorSpy()
    monkeypatch.setattr(main_module.deterministic_orchestrator, "run_orchestration", s)
    monkeypatch.setattr(main_module, "write_report", lambda *a, **k: None)
    return s


def _force_true_no_config_branch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Force ``resolve_config_path`` to return None so ``main()`` actually reaches the
    ``else:`` fallback branch (``build_sample_inputs()``), instead of silently falling through
    to the committed 36 Kelly bundle's ``inputs.json`` (which exists in this repo and would
    otherwise make these tests exercise the CONFIG branch's validation, not the fallback
    branch's -- see ``test_resolver_falls_back_to_none_without_a_bundle`` for the same pattern)."""
    monkeypatch.setattr(main_module, "DEFAULT_INPUTS", tmp_path / "absent" / "inputs.json")


def test_no_config_bypass_horizon_101_is_rejected_not_silently_capped(
    monkeypatch: pytest.MonkeyPatch, spy: _OrchestratorSpy, tmp_path: Path
) -> None:
    """THE PIN for the main.py:256 hole: ``args.horizon or 10`` used to accept ANY integer
    (including 500 and negatives) on the no-config fallback path. Nothing reaches the pipeline."""
    _force_true_no_config_branch(monkeypatch, tmp_path)
    monkeypatch.setattr("sys.argv", ["main.py", "--horizon", "101"])

    with pytest.raises(SystemExit) as exc_info:
        main_module.main()

    assert str(exc_info.value) == "Forecast horizon must be between 1 and 100 years; got 101."
    assert spy.calls == []


def test_no_config_bypass_horizon_0_is_rejected_not_silently_swapped_for_10(
    monkeypatch: pytest.MonkeyPatch, spy: _OrchestratorSpy, tmp_path: Path
) -> None:
    """``args.horizon or 10`` also swallowed a legitimate ``--horizon 0`` (falsy int), silently
    substituting 10. 0 is invalid (ge=1) and must now be REJECTED, not silently replaced."""
    _force_true_no_config_branch(monkeypatch, tmp_path)
    monkeypatch.setattr("sys.argv", ["main.py", "--horizon", "0"])

    with pytest.raises(SystemExit) as exc_info:
        main_module.main()

    assert str(exc_info.value) == "Forecast horizon must be between 1 and 100 years; got 0."
    assert spy.calls == []


def test_no_config_bypass_horizon_default_is_10_when_unset(monkeypatch: pytest.MonkeyPatch, spy: _OrchestratorSpy, tmp_path: Path) -> None:
    _force_true_no_config_branch(monkeypatch, tmp_path)
    monkeypatch.setattr("sys.argv", ["main.py"])

    main_module.main()

    assert spy.calls[0]["horizon_years"] == 10


def test_no_config_bypass_horizon_100_accepted(monkeypatch: pytest.MonkeyPatch, spy: _OrchestratorSpy, tmp_path: Path) -> None:
    _force_true_no_config_branch(monkeypatch, tmp_path)
    monkeypatch.setattr("sys.argv", ["main.py", "--horizon", "100"])

    main_module.main()

    assert spy.calls[0]["horizon_years"] == 100


# ---------------------------------------------------------------------------------------
# OI.3: the real process -- one clean line on stderr, no traceback, exit code 1
# ---------------------------------------------------------------------------------------


def _run_main(args: list[str], env_overrides: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, **(env_overrides or {})}
    return subprocess.run(
        [sys.executable, "main.py", *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )


def test_cli_flag_out_of_range_process_exit_code_1_no_traceback() -> None:
    proc = _run_main(["--config", str(BUNDLE_CONFIG), "--horizon", "101"])

    assert proc.returncode == 1
    assert proc.stderr.strip() == "Forecast horizon must be between 1 and 100 years; got 101."
    assert "Traceback" not in proc.stderr
    assert "ValidationError" not in proc.stderr


def test_env_var_unparseable_process_exit_code_1_no_traceback() -> None:
    proc = _run_main(["--config", str(BUNDLE_CONFIG)], env_overrides={"AIREAL_HORIZON": "abc"})

    assert proc.returncode == 1
    assert proc.stderr.strip() == "AIREAL_HORIZON must be a whole number of years between 1 and 100; got 'abc'."
    assert "Traceback" not in proc.stderr


def test_bare_horizon_flag_without_config_process_exit_code_1_no_traceback() -> None:
    """No ``--config`` supplied: ``resolve_config_path`` still resolves to the committed 36
    Kelly bundle in this checkout (so this exercises the CONFIG branch's ``with_overrides``
    validation end to end, not the true no-config fallback -- that branch is pinned in-process
    above with ``DEFAULT_INPUTS`` monkeypatched away, which a real subprocess run of this repo
    cannot do without moving the committed bundle). Confirms the same clean-exit contract holds
    for the zero-``--config`` invocation a real user would actually run."""
    proc = _run_main(["--horizon", "101"])

    assert proc.returncode == 1
    assert proc.stderr.strip() == "Forecast horizon must be between 1 and 100 years; got 101."
    assert "Traceback" not in proc.stderr


def test_cli_flag_100_process_succeeds() -> None:
    """Confirms the raised ceiling is actually reachable end-to-end, not just at the schema."""
    out = REPO_ROOT / "out_test_horizon_100.md"
    try:
        proc = _run_main(["--config", str(BUNDLE_CONFIG), "--horizon", "100", "--out", str(out)])
        assert proc.returncode == 0, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        assert out.exists()
    finally:
        out.unlink(missing_ok=True)
