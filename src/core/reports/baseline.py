# src/core/reports/baseline.py

"""
The "second picture" a report can be compared against.

Why this exists
---------------
Listing observations — condition tags, defects, amenities — reach the numbers through the
deterministic insight modifiers in ``src/core/finance/engine.py`` (``_apply_insight_modifiers``).
An observation never computes anything; it selects a fixed rule ("old roof" → reserves +$300/yr)
that the engine then applies. The result is a forecast whose OPEX, NOI, cash flow and ratios are
partly a consequence of what the pipeline *thought it saw*.

A reader cannot audit that from the adjusted figures alone: the adjustment is baked into every
downstream number with nothing to compare it against. ``BaselineOutlook`` carries the same deal
re-run with **no** observations applied, so the report can show both pictures side by side and the
observation-dependent part of the analysis can be read apart from the part that does not depend
on it.

Pure carrier by design
----------------------
This module holds data only. It does not run the engine and imports nothing from the agent or
orchestration layers — the *construction* of a baseline belongs to whoever owns the inputs
(``src/orchestrators/crew.py::build_baseline_outlook``), and the rendering belongs to the report
generator. That keeps ``src/core/reports/`` free of a dependency on the pipeline that feeds it.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.schemas.models import FinancialForecast, InvestmentThesis


@dataclass(frozen=True)
class BaselineOutlook:
    """
    The deterministic outlook for a deal with no listing-observation adjustments applied.

    Attributes:
        forecast: The forecast produced by running the same inputs with ``insights=None`` — i.e.
            with every insight modifier suppressed. Same engine, same horizon, same everything
            else; the only difference is that no observation fired.
        thesis: The verdict that same baseline forecast produces, when the caller computed one.
            Optional: a caller with only a forecast to offer supplies ``None`` and the report
            omits the verdict comparison rather than inventing one.
    """

    forecast: FinancialForecast
    thesis: InvestmentThesis | None = None
