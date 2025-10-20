# tests/unit/test_strategist_rules_unit.py

from src.core.strategy.strategist import form_thesis


def test_strategist_buy_when_metrics_strong(baseline_financial_inputs, baseline_forecast, market_assumptions_baseline):
    financial_inputs = baseline_financial_inputs()
    fin_forcast = baseline_forecast(financial_inputs)
    market_assumption = market_assumptions_baseline()
    thesis = form_thesis(ff=fin_forcast, mkt=market_assumption)
    assert thesis.verdict == "BUY"


def test_strategist_conditional_on_thin_spread_or_dscr(
    baseline_financial_inputs,
    baseline_forecast,
    market_assumptions_baseline,
):
    # leaving financials at baseline, and raise target spread
    # so the baseline deal triggers a spread shortfall → CONDITIONAL.
    fi = baseline_financial_inputs()  # baseline inputs
    ff = baseline_forecast(fi)  # forecast for those inputs

    # Increase target spread above the baseline spread (~1.94%)
    mkt = market_assumptions_baseline(cap_rate_spread_target=0.03)

    thesis = form_thesis(ff=ff, mkt=mkt)
    assert thesis.verdict == "CONDITIONAL"


def test_strategist_pass_on_negative_cashflow_or_poor_metrics(
    baseline_financial_inputs,
    baseline_forecast,
    market_assumptions_baseline,
):
    # Force: CoC < 0 and DSCR < 1.0 (both required for PASS in form_thesis).
    # We’ll hike the interest rate and bump taxes to push cash flow negative.
    base = baseline_financial_inputs()
    stressed = base.model_copy(
        update={
            "financing": base.financing.model_copy(
                update={
                    "interest_rate": 0.10,  # push debt service way up
                    "io_years": 0,  # ensure amortizing right away
                }
            ),
            "opex": base.opex.model_copy(
                update={
                    "taxes": base.opex.taxes * 2.5,  # extra stress to ensure CoC < 0
                }
            ),
        }
    )

    ff = baseline_forecast(stressed)
    mkt = market_assumptions_baseline()  # default guardrails are fine here

    thesis = form_thesis(ff=ff, mkt=mkt)
    assert thesis.verdict == "PASS"
