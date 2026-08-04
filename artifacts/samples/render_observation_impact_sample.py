#!/usr/bin/env python
"""
Regenerate the observation-impact sample report.

    source /home/rtokime/anaconda3/etc/profile.d/conda.sh; conda activate airedeal
    python artifacts/samples/render_observation_impact_sample.py

Writes ``artifacts/samples/observation_impact_sample.md``.

Why a script and not ``python main.py``
---------------------------------------
The engine's insight modifiers (``src/core/finance/engine.py::_apply_insight_modifiers``) match the
literal tags ``"old roof"``, ``"water stain"``, ``"in-unit laundry"`` and ``"parking"``. Neither live
observation path emits those strings today: the listing-text parser's condition vocabulary is
``new roof`` / ``updated kitchen`` / ... (``listing_parser.py:_CONDITION_KEYWORDS``) and the CV path
normalizes a water stain to the label ``water_leak_suspected`` (``schemas/labels.py:241``). So the
modifiers — and therefore this report section — are only reachable with hand-built insights, which is
what this script supplies. The vocabulary mismatch is a real wiring gap, reported separately; it is
upstream of the report layer and is not papered over here.

Everything below the insights is the production path: the same ``FinancialInputs`` the committed demo
bundle uses, the same engine, the same ``build_baseline_outlook`` both orchestrators call, and the
same ``write_report``. The numbers are the engine's; only the observations are hand-fed.

``vision_enabled=True`` in the provenance below is likewise deliberate: it renders the AI-assisted
state of the section (the column suffix and the AI source line). With it False the only differences
are that suffix and that one line.
"""

from __future__ import annotations

from pathlib import Path

from src.agents.chief_strategist import synthesize_thesis
from src.agents.financial_forecaster import forecast_financials
from src.core.reports.generator import write_report
from src.inputs.inputs import InputsLoader
from src.orchestrators.crew import build_baseline_outlook
from src.schemas.models import ListingInsights, RunProvenance

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG = REPO_ROOT / "data/sample_listings/36_kelly_moncton/inputs.json"
OUT = REPO_ROOT / "artifacts/samples/observation_impact_sample.md"
HORIZON = 10


def main() -> None:
    cfg = InputsLoader().load(str(CONFIG))
    # income_is_estimated=True so the amenity-uplift rules are live too: the sample then shows all
    # three kinds of attribution the engine can produce (condition -> reserves, defect -> R&M,
    # amenity -> other income) rather than only the two OPEX ones.
    inputs = cfg.inputs.model_copy(update={"income_is_estimated": True})

    # Hand-built observations. These stand in for what an inspector's notes -- or a vision model's
    # tags -- would report. They compute nothing; each one only selects a fixed engine rule.
    insights = ListingInsights(
        address="36 Kelly Ave, Moncton NB (SAMPLE — observations are hand-fed, not from a real tagger)",
        condition_tags=["old roof"],
        defects=["water stain"],
        amenities=["in-unit laundry", "parking"],
        notes=["Sample artifact: the observations on this report were supplied by hand to exercise the comparison section."],
    )

    forecast = forecast_financials(inputs=inputs, insights=insights, horizon_years=HORIZON)
    thesis = synthesize_thesis(forecast)
    baseline = build_baseline_outlook(inputs, forecast, horizon_years=HORIZON)

    write_report(
        OUT,
        insights,
        forecast,
        thesis,
        provenance=RunProvenance(
            engine="deterministic",
            scenarios_enabled=False,
            vision_enabled=True,
            config_path=str(CONFIG.relative_to(REPO_ROOT)),
        ),
        baseline=baseline,
    )
    print(f"Wrote {OUT.relative_to(REPO_ROOT)}")
    print(f"Verdict (with observations): {thesis.verdict}")
    if baseline is not None and baseline.thesis is not None:
        print(f"Verdict (baseline):          {baseline.thesis.verdict}")


if __name__ == "__main__":
    main()
