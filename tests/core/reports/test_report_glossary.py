# tests/core/reports/test_report_glossary.py
"""The definitions appendix, and the links into it.

A glossary is only useful if every acronym in the body actually reaches it, so the load-bearing
test here is link integrity: every ``](#g-...)`` in the rendered document must resolve to an
``<a id="g-...">`` anchor in the appendix. That check fails automatically if someone adds a
linked term without a definition, or renames an anchor.
"""

from __future__ import annotations

import re

from src.core.finance import run_financial_model
from src.core.reports.generator import _GLOSSARY, generate_report
from src.schemas.models import ListingInsights
from tests.utils import make_financial_inputs

_LINK_RE = re.compile(r"\]\(#(g-[a-z]+)\)")
_ANCHOR_RE = re.compile(r'<a id="(g-[a-z]+)"></a>')


def _render(**kwargs: object) -> str:
    forecast = run_financial_model(make_financial_inputs())
    insights = ListingInsights(address="36 Kelly", price=399900.0, sqft=1936, bedrooms=3, bathrooms=1)
    return generate_report(insights, forecast, None, **kwargs)  # type: ignore[arg-type]


def test_appendix_is_always_present() -> None:
    # Always emitted, unlike the optional media/scenario sections: a reader hitting "DSCR 0.90"
    # needs somewhere to land regardless of which optional sections a run produced.
    assert "## Appendix — Definitions" in _render()


def test_appendix_is_the_last_section() -> None:
    md = _render()
    headings = re.findall(r"^## (.+)$", md, flags=re.MULTILINE)
    assert headings[-1] == "Appendix — Definitions"


def test_every_glossary_link_resolves_to_an_anchor() -> None:
    md = _render()
    links = set(_LINK_RE.findall(md))
    anchors = set(_ANCHOR_RE.findall(md))

    assert links, "no glossary links rendered at all"
    assert not (links - anchors), f"links with no definition: {sorted(links - anchors)}"


def test_anchors_are_unique() -> None:
    anchors = _ANCHOR_RE.findall(_render())
    assert len(anchors) == len(set(anchors)), "duplicate anchor id would make links ambiguous"


def test_core_metrics_are_linked_in_the_body() -> None:
    md = _render()
    for anchor in ("g-dscr", "g-noi", "g-coc", "g-cap", "g-ds", "g-acq"):
        assert f"](#{anchor})" in md, f"{anchor} defined but never linked from the body"


def test_every_defined_term_appears_in_the_table() -> None:
    md = _render()
    for anchor, term, expansion, _definition in _GLOSSARY:
        assert f'<a id="g-{anchor}"></a>' in md
        assert expansion in md, f"expansion for {term!r} missing from the appendix"


def test_definitions_state_the_implemented_formula() -> None:
    # Guards against the glossary drifting into generic textbook prose: these are the
    # formulas the engine actually evaluates, verified against src/core/finance/engine.py.
    md = _render()
    assert "GOI = GSI × occupancy × bad_debt_factor" in md
    assert "NOI = GOI − OPEX" in md
    assert "DSCR = NOI ÷ Debt Service" in md


def test_debt_service_entry_discloses_the_annual_convention() -> None:
    # The engine amortizes on ANNUAL periods, which runs ~1.2% above a monthly-pay loan of the
    # same rate and term. A reader reconciling the number against a bank quote must be told.
    md = _render()
    assert "annual" in md.lower()
    assert "monthly-pay" in md
