# tests/core/utils/test_markdown.py
"""
Mission 2, Wave 3, task 3.1b (OPD-3 wire-first) — src/core/utils/markdown.py.

Before this task the module had zero production and zero test references (OPD-3 pre-work
reachability survey): ``advisor_cli.py`` hand-rolled its own Markdown rendering inline
(``advisor_output.md``'s ``--markdown`` block) instead of calling this module, so
``render_markdown``/``deal_card``/``portfolio_block`` were reachable only by importing them
directly here. This file is that direct coverage AND doubles as the RED-on-revert proof for the
CLI wiring: ``tests/integration/test_advisor_cli_wiring.py`` proves the CLI actually calls
``render_markdown``; these tests pin exactly what it renders so a regression in either the wiring
or the renderer itself is caught.
"""

from __future__ import annotations

from src.core.intelligence.deal_fusion import fuse_deal_intelligence
from src.core.utils.markdown import deal_card, portfolio_block, render_markdown


def test_deal_card_renders_core_fields(listing_fixture, photos_fixture, finance_fixture) -> None:
    deal = fuse_deal_intelligence(listing_fixture, photos_fixture, finance_fixture)
    card = deal_card(deal, 0.53)

    assert "### Charming 2BR Near River" in card
    assert "- **Address:** 123 Main St, Moncton, NB" in card
    assert "- **Composite score:** 0.53" in card
    assert "- **Cashflow (monthly):** 125" in card
    assert "- **Price / sqft:** 210.00" in card
    assert "- **Beds:** 2.0" in card
    assert "- **Baths:** 1.0" in card
    assert "- **Sqft:** 900" in card
    # listing_fixture never sets `price` (list price, distinct from `finance.purchase_price`),
    # so the Price line is correctly omitted rather than fabricated from the wrong source.
    assert "- **Price:**" not in card


def test_deal_card_includes_the_listing_summary_line(listing_fixture, photos_fixture, finance_fixture) -> None:
    """
    ``ListingNormalized.summary()`` is a real, informative one-line rollup (title, price,
    location, beds/baths/sqft) that the CLI's old hand-rolled Markdown block printed as a
    "- Summary: ..." line. Wiring the CLI onto this module must not silently drop that fact.
    """
    deal = fuse_deal_intelligence(listing_fixture, photos_fixture, finance_fixture)
    card = deal_card(deal, 0.53)

    assert "- **Summary:**" in card
    assert deal.listing.summary() in card


def test_deal_card_renders_price_when_the_listing_states_one(listing_fixture, photos_fixture, finance_fixture) -> None:
    """
    Companion to ``test_deal_card_renders_core_fields``'s no-price case above: this is the
    RED-on-revert half of a pre-existing latent bug caught while wiring this module in --
    ``_kv("Price", f"{price:,.0f}")`` used to format ``price`` unconditionally, so any listing
    with ``price is None`` (the default, exercised above) raised ``TypeError`` the instant this
    function actually ran on real data, which it never did prior to this task in any live path.
    Reverting the ``price is not None else None`` guard makes *both* tests fail, not just one --
    this one on wrong output, the no-price one on an uncaught exception.
    """
    priced = listing_fixture.model_copy(update={"price": 250_000.0})
    deal = fuse_deal_intelligence(priced, photos_fixture, finance_fixture)

    card = deal_card(deal, 0.53)

    assert "- **Price:** 250,000" in card


def test_portfolio_block_renders_the_three_summary_numbers() -> None:
    block = portfolio_block({"avg_score": 0.4321, "total_cashflow": 1500.0, "risk_items": 3.0})

    assert "## Portfolio" in block
    assert "- **Average score:** 0.43" in block
    assert "- **Total monthly cashflow:** 1,500" in block
    assert "- **Risk items:** 3.0" in block


def test_render_markdown_composes_portfolio_and_ranked_deal_cards(listing_fixture, photos_fixture, finance_fixture) -> None:
    deal = fuse_deal_intelligence(listing_fixture, photos_fixture, finance_fixture)
    ranked = [(deal, 0.53)]
    portfolio = {"avg_score": 0.53, "total_cashflow": 125.0, "risk_items": 1.0}

    md = render_markdown(ranked, portfolio)

    assert md.startswith("# Deal Advisor Report")
    assert "## Portfolio" in md
    assert "## Ranked Deals" in md
    assert "### 1. Charming 2BR Near River" in md
    # Ordering: the portfolio summary appears before the ranked deals section.
    assert md.index("## Portfolio") < md.index("## Ranked Deals")


def test_render_markdown_numbers_every_deal_in_rank_order(listing_fixture, photos_fixture, finance_fixture) -> None:
    """A section titled "Ranked Deals" has to show the ranks.

    The inline block this renderer replaced (``cli/advisor_cli.py``, task 3.1b) numbered its deal
    headings ``## 1.``, ``## 2.``; ``deal_card`` did not, so adopting the shared renderer silently
    cost a multi-deal report its rank ordinals — invisible on the one-deal sample, plain on any
    real portfolio. RED on revert: drop the ``rank=`` argument in ``render_markdown`` and the
    headings come back as bare ``### <title>``, failing every assertion below.

    The numbers must also follow ``ranked``'s own order rather than being re-derived from the
    scores here — a second ordering rule is a second thing that can disagree with the first.
    """
    deal = fuse_deal_intelligence(listing_fixture, photos_fixture, finance_fixture)
    ranked = [(deal, 0.91), (deal, 0.42), (deal, 0.10)]

    md = render_markdown(ranked, {"avg_score": 0.48, "total_cashflow": 300.0, "risk_items": 2.0})

    headings = [line for line in md.splitlines() if line.startswith("### ")]
    assert [h.split(".")[0] for h in headings] == ["### 1", "### 2", "### 3"], headings
    assert md.index("### 1.") < md.index("### 2.") < md.index("### 3.")
