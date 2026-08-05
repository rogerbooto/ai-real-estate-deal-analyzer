# tests/integration/test_advisor_cli_wiring.py
"""
Mission 2, Wave 3, task 3.1b (OPD-3 "wire-first") — advisor_cli.py wiring for the modules the
OPD-3 pre-work reachability survey found reachable only from tests (or from nothing at all).

Gate 3 (2026-08-05) blocked and reverted two of the five: `--what-if` (`src.core.advisor.scenarios`)
and `--narrative` (`src.core.intelligence.narrative_builder`/`report_builder`) both printed numbers
the deterministic finance engine never computed onto a file the user reads (a fabricated IRR proxy
with no amortization behind it; a duplicate, strictly-poorer report printing raw-fraction IRR where
every other surface renders a percentage). Both modules are deleted (see `CHANGELOG.md` "Removed"),
and this file's job for them is now the opposite of before: prove the flags are **rejected** by the
parser, not silently accepted as no-ops.

The three surviving items:

  - src.market.regional_income          (--regional-income flag, corrected at Gate 3 to drop its
                                          two fabricated fields — turnover_cost, str_multiplier —
                                          from every rendered output)
  - src.core.utils.markdown             (--markdown calls render_markdown() instead of a
                                          hand-rolled reimplementation that used to live inline
                                          at advisor_cli.py, drifting from src/core/utils/markdown.py)
  - src.core.utils.serialize            (--save-artifacts calls to_primitive())

Each test below is the RED-on-revert proof for its module: reverting the corresponding wiring in
advisor_cli.py (removing the flag's body, or reverting the --markdown/--save-artifacts bodies to
their pre-3.1b hand-rolled form) makes the matching test in this file fail. This was verified by
hand against a disposable `git worktree` checked out at the pre-3.1b commit and is not re-asserted
mechanically here (there is no pre-3.1b commit to diff against inside the suite itself).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.cli.advisor_cli import _deal_artifact_payload, main as advisor_main
from src.market.regional_income import build_regional_income
from tests.utils import _patched_argv_and_syspath, repo_root


def _write_json(p: Path, obj: object) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2), encoding="utf-8")


_FINANCE_JSON: dict[str, Any] = {
    "irr": 0.10,
    "cashflow_monthly": 300.0,
    "price_per_sqft": 200,
    "market_ppsf": 210,
    "purchase_price": 300000,
    "area_safety_index": 0.60,
}


def _build_deal_dir(deal_dir: Path) -> None:
    photos_dir = deal_dir / "photos"
    photos_dir.mkdir(parents=True, exist_ok=True)
    (photos_dir / "1.jpg").write_bytes(b"\xff\xd8\xff\xd9")  # minimal JPEG (SOI+EOI)

    (deal_dir / "listing.txt").write_text(
        "47 Perrot Street, Shediac, NB E4P 0H3\nPrice: $219,900 | 3 bed | 1 bath | 1016 sqft\nHeating: baseboard | Cooling: ac",
        encoding="utf-8",
    )
    _write_json(deal_dir / "finance.json", _FINANCE_JSON)


# ---------------------------------------------------------------------------
# Gate 3 — --what-if / --narrative must be rejected, not silently accepted
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_what_if_flag_is_rejected_by_the_parser(tmp_path: Path, capsys) -> None:
    """
    src.core.advisor.scenarios was deleted at Gate 3 (fabricated irr_est, no amortization, its own
    "does not re-run engine" disclaimer never reached the page). --what-if must be an argparse
    error (exit code 2), not a quietly-ignored flag -- a silent no-op would be indistinguishable
    from someone re-wiring the deleted module.
    """
    deal_dir = tmp_path / "dealA"
    _build_deal_dir(deal_dir)
    out_path = tmp_path / "advisor_output.json"

    argv = ["advisor_cli.py", "--files", str(deal_dir), "--out", str(out_path), "--what-if"]
    with _patched_argv_and_syspath(argv, str(repo_root())):
        with pytest.raises(SystemExit) as exc_info:
            advisor_main()

    assert exc_info.value.code == 2
    assert not out_path.exists()
    assert "unrecognized arguments" in capsys.readouterr().err


@pytest.mark.integration
def test_narrative_flag_is_rejected_by_the_parser(tmp_path: Path, capsys) -> None:
    """
    src.core.intelligence.narrative_builder/report_builder were deleted at Gate 3 (a duplicate,
    strictly-poorer report than deal-report's, printing raw-fraction IRR). --narrative must be an
    argparse error (exit code 2), not a quietly-ignored flag.
    """
    deal_dir = tmp_path / "dealA"
    _build_deal_dir(deal_dir)
    out_path = tmp_path / "advisor_output.json"

    argv = ["advisor_cli.py", "--files", str(deal_dir), "--out", str(out_path), "--narrative"]
    with _patched_argv_and_syspath(argv, str(repo_root())):
        with pytest.raises(SystemExit) as exc_info:
            advisor_main()

    assert exc_info.value.code == 2
    assert not out_path.exists()
    assert "unrecognized arguments" in capsys.readouterr().err
    assert not (tmp_path / "advisor_output_narratives").exists()


# ---------------------------------------------------------------------------
# src.market.regional_income — --regional-income
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_regional_income_flag_embeds_the_real_module_output(tmp_path: Path, capsys) -> None:
    deal_dir = tmp_path / "dealA"
    _build_deal_dir(deal_dir)
    comps_path = tmp_path / "comps.json"
    _write_json(comps_path, {"region": "Metro A", "bedrooms": 2, "comps": [1500, 1550, 1600, 1700, 1800]})
    out_path = tmp_path / "advisor_output.json"

    argv = [
        "advisor_cli.py",
        "--files",
        str(deal_dir),
        "--out",
        str(out_path),
        "--regional-income",
        str(comps_path),
    ]
    with _patched_argv_and_syspath(argv, str(repo_root())):
        advisor_main()

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    expected = build_regional_income("Metro A", 2, [1500, 1550, 1600, 1700, 1800])

    # Independently computed from the same comps via the real module -- not a re-derivation of
    # advisor_cli's own logic, so this cannot pass "for the wrong reason".
    assert payload["regional_income"] == {
        "region": expected.region,
        "bedrooms": expected.bedrooms,
        "median_rent": expected.median_rent,
        "p25_rent": expected.p25_rent,
        "p75_rent": expected.p75_rent,
    }

    captured = capsys.readouterr()
    assert expected.summary() in captured.out


@pytest.mark.integration
def test_regional_income_flag_never_surfaces_the_two_fabricated_fields(tmp_path: Path, capsys) -> None:
    """
    Gate 3 (mission/2-wiring-gaps): RegionalIncomeTable.turnover_cost (an uncited "median rent *
    0.5" rule of thumb) and .str_multiplier (a hardcoded 1.5x STR uplift previously gated by a
    policy hook whose entire body was `return True`, in a province that regulates short-term
    rentals) must never reach --out's JSON, the console summary, or --markdown. RED on revert: if
    either field is re-added to advisor_cli's rendering, this test catches it.
    """
    deal_dir = tmp_path / "dealA"
    _build_deal_dir(deal_dir)
    comps_path = tmp_path / "comps.json"
    _write_json(comps_path, {"region": "Metro A", "bedrooms": 2, "comps": [1500, 1550, 1600, 1700, 1800]})
    out_path = tmp_path / "advisor_output.json"

    argv = [
        "advisor_cli.py",
        "--files",
        str(deal_dir),
        "--out",
        str(out_path),
        "--regional-income",
        str(comps_path),
        "--markdown",
    ]
    with _patched_argv_and_syspath(argv, str(repo_root())):
        advisor_main()

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert "turnover_cost" not in payload["regional_income"]
    assert "str_multiplier" not in payload["regional_income"]

    captured = capsys.readouterr()
    assert "turnover" not in captured.out.lower()
    assert "strx" not in captured.out.lower()
    assert "[RegionalIncomeTable]" not in captured.out

    md_text = out_path.with_suffix(".md").read_text(encoding="utf-8")
    assert "turnover" not in md_text.lower()
    assert "strx" not in md_text.lower()
    assert "[RegionalIncomeTable]" not in md_text


@pytest.mark.integration
def test_regional_income_flag_missing_keys_fails_loud_not_silent(tmp_path: Path) -> None:
    deal_dir = tmp_path / "dealA"
    _build_deal_dir(deal_dir)
    comps_path = tmp_path / "comps.json"
    _write_json(comps_path, {"region": "Metro A"})  # missing bedrooms + comps
    out_path = tmp_path / "advisor_output.json"

    argv = [
        "advisor_cli.py",
        "--files",
        str(deal_dir),
        "--out",
        str(out_path),
        "--regional-income",
        str(comps_path),
    ]
    with _patched_argv_and_syspath(argv, str(repo_root())):
        with pytest.raises(SystemExit) as exc_info:
            advisor_main()

    message = str(exc_info.value)
    assert "bedrooms" in message and "comps" in message
    assert not out_path.exists()


@pytest.mark.integration
def test_without_regional_income_flag_no_key_is_added(tmp_path: Path) -> None:
    deal_dir = tmp_path / "dealA"
    _build_deal_dir(deal_dir)
    out_path = tmp_path / "advisor_output.json"

    argv = ["advisor_cli.py", "--files", str(deal_dir), "--out", str(out_path)]
    with _patched_argv_and_syspath(argv, str(repo_root())):
        advisor_main()

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert "regional_income" not in payload


# ---------------------------------------------------------------------------
# src.core.utils.markdown — --markdown now calls render_markdown(), not a hand-rolled block
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_markdown_output_carries_fields_only_the_shared_renderer_produces(tmp_path: Path) -> None:
    """
    The pre-3.1b inline Markdown block (F13's fixed shape, still pinned by
    ``test_advisor_cli_flags.py``) rendered title/address/score/cashflow/title-confidence/summary
    only. ``src.core.utils.markdown.deal_card`` additionally renders Price/sqft, Beds, Baths,
    Sqft, and Title source -- fields the old block never had. Their presence is only explainable
    by the CLI actually calling the shared renderer.
    """
    deal_dir = tmp_path / "dealA"
    _build_deal_dir(deal_dir)
    out_path = tmp_path / "advisor_output.json"

    argv = ["advisor_cli.py", "--files", str(deal_dir), "--out", str(out_path), "--markdown"]
    with _patched_argv_and_syspath(argv, str(repo_root())):
        advisor_main()

    md_text = out_path.with_suffix(".md").read_text(encoding="utf-8")
    assert "## Portfolio" in md_text
    assert "## Ranked Deals" in md_text
    assert "- **Price / sqft:**" in md_text
    assert "- **Beds:**" in md_text
    assert "- **Baths:**" in md_text
    assert "- **Sqft:**" in md_text
    assert "- **Title source:** text" in md_text


# ---------------------------------------------------------------------------
# src.core.utils.serialize — --save-artifacts now calls to_primitive()
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_save_artifacts_round_trips_through_the_real_pipeline(tmp_path: Path) -> None:
    deal_dir = tmp_path / "dealA"
    _build_deal_dir(deal_dir)
    out_path = tmp_path / "advisor_output.json"

    argv = ["advisor_cli.py", "--files", str(deal_dir), "--out", str(out_path), "--save-artifacts"]
    with _patched_argv_and_syspath(argv, str(repo_root())):
        advisor_main()

    artifact = json.loads((tmp_path / "advisor_output_artifacts" / "deal_01.json").read_text(encoding="utf-8"))
    assert artifact["finance"]["cashflow_monthly"] == pytest.approx(300.0)
    assert "listing" in artifact and isinstance(artifact["listing"], dict)


def test_save_artifacts_recursively_converts_a_nested_non_pydantic_finance_object() -> None:
    """
    Direct RED-on-revert proof for the ``to_primitive`` wiring in ``_deal_artifact_payload``.
    The pre-3.1b code (``d.finance.model_dump() if hasattr(...) else d.finance.__dict__``) cannot
    tell this shape apart from the pydantic case it was designed for; ``finance`` here is a
    dataclass (not pydantic, so ``hasattr(..., "model_dump")`` is False) whose own field is a
    pydantic model. The old ``__dict__`` fallback would leave that nested field as a live
    ``BaseModel`` instance -- not JSON-primitive, and not equal to the dict this test asserts.
    """
    from dataclasses import dataclass
    from types import SimpleNamespace

    from pydantic import BaseModel

    class _Nested(BaseModel):
        note: str

    @dataclass
    class _FakeFinance:
        cashflow_monthly: float
        detail: _Nested

    class _FakeListing(BaseModel):
        title: str

    d = SimpleNamespace(
        listing=_FakeListing(title="Fake St"),
        finance=_FakeFinance(cashflow_monthly=42.0, detail=_Nested(note="n")),
    )

    payload = _deal_artifact_payload(d, 0.75)

    assert payload == {
        "score": 0.75,
        "listing": {"title": "Fake St"},
        "finance": {"cashflow_monthly": 42.0, "detail": {"note": "n"}},
    }
    # The decisive assertion: the nested value is a plain dict, not a lingering BaseModel --
    # the shape json.dumps() needs and the old __dict__ fallback could not have produced.
    assert isinstance(payload["finance"]["detail"], dict)
    json.dumps(payload)  # must not raise
