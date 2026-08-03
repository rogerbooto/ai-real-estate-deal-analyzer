# tests/core/reports/test_report_header_identity.py
"""The report header must name the property whenever anything identifies it.

Before this, ``_render_header`` read ``insights.address`` alone, so a listing whose street
line carries no street type (e.g. "36 Kelly") produced a report titled "Subject Property"
even though a usable title had been inferred. ``ListingInsights.title`` is the fallback.

Precedence pinned here: address → title → "Subject Property".
"""

from __future__ import annotations

from src.core.finance import run_financial_model
from src.core.reports.generator import generate_report
from src.schemas.models import ListingInsights
from tests.utils import make_financial_inputs


def _header(insights: ListingInsights) -> str:
    forecast = run_financial_model(make_financial_inputs())
    return generate_report(insights, forecast, None).splitlines()[0]


def test_address_names_the_report() -> None:
    assert _header(ListingInsights(address="36 Kelly", title="ignored")) == "# Investment Analysis – 36 Kelly"


def test_title_is_used_when_no_address_parsed() -> None:
    # The regression: this used to render "Subject Property" and drop the title entirely.
    assert _header(ListingInsights(address=None, title="36 Kelly, Moncton")) == "# Investment Analysis – 36 Kelly, Moncton"


def test_generic_fallback_when_nothing_identifies_the_property() -> None:
    assert _header(ListingInsights()) == "# Investment Analysis – Subject Property"


def test_empty_strings_fall_through_rather_than_naming_the_report() -> None:
    assert _header(ListingInsights(address="", title="")) == "# Investment Analysis – Subject Property"
