# tests/integration/test_floor_value_reaches_the_demo_report.py
"""The cap-rate floor a deal was judged against must survive the whole chain to the document.

Mission 2, task 3.2, criterion (a). Every other pin for this lives one layer down — the
strategist's rationale line (`tests/integration/test_chief_strategist.py`) and the provenance
appendix (`tests/core/reports/test_computed_fields_reach_the_report.py`). Both of those pass a
market block in by hand, so neither notices if `main.py` stops passing one. That gap is exactly
the shape of the mission's root cause: a correct renderer nothing feeds.

So this runs the real zero-argument demo and reads the file it wrote.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import main as main_module

BUNDLE = Path("data/sample_listings/36_kelly_moncton")


@pytest.fixture()
def demo_report(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> str:
    out = tmp_path / "report.md"
    monkeypatch.setattr("sys.argv", ["main.py", "--out", str(out)])
    main_module.main()
    return out.read_text(encoding="utf-8")


def _configured_floor() -> float:
    floor = json.loads((BUNDLE / "inputs.json").read_text(encoding="utf-8"))["inputs"]["market"]["cap_rate_floor"]
    assert floor is not None, "the demo bundle must configure a floor for this test to mean anything"
    return float(floor)


def test_the_thesis_names_the_cap_and_the_floor(demo_report: str) -> None:
    floor = _configured_floor()

    assert f"(≥ the {floor:.2%} floor you set)." in demo_report, (
        "the demo report no longer names the floor its cap rate cleared — check that main.py "
        "still passes market=inputs.market to write_report, and crew.py to synthesize_thesis"
    )
    # The unnumbered predecessor must not come back alongside it.
    assert "breaches the configured floor" not in demo_report


def test_the_provenance_appendix_records_the_floor_policy(demo_report: str) -> None:
    floor = _configured_floor()

    assert f"| Cap-rate floor | {floor:.2%} | `market.cap_rate_floor` |" in demo_report
