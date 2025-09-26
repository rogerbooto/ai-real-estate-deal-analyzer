# tests/unit/test_financial_forecaster.py

from src.agents.financial_forecaster import forecast_financials
from src.schemas.models import FinancialForecast
from tests.utils import make_financial_inputs, make_listing_insights


def test_forecast_financials_smoke():
    inputs = make_financial_inputs(do_refi=True)
    listing = make_listing_insights()
    result = forecast_financials(inputs, listing)
    # The forecaster returns a FinancialForecast model
    assert isinstance(result, FinancialForecast)
    # Basic smoke: key attributes exist
    assert hasattr(result, "purchase") and result.purchase is not None
    assert hasattr(result, "irr_10yr")
    assert hasattr(result, "equity_multiple_10yr")
