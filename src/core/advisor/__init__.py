# src/core/advisor/__init__.py
"""Package marker for `src.core.advisor`.

This module used to re-export `rank_deals` / `portfolio_summary` / `compute_risk_flags` as lazy
wrapper functions. Every real caller (`src/cli/advisor_cli.py`, `src/core/intelligence/
deal_fusion.py`) has always imported the submodules directly
(`src.core.advisor.recommender.rank_deals`, `src.core.advisor.portfolio.portfolio_summary`,
`src.core.advisor.risk.compute_risk_flags`), so the wrappers were dead code with zero callers.
Mission 2 (Wave 3, task 3.1b) removed them.

The file itself stays: deleting it would break every submodule import
(`from src.core.advisor.recommender import rank_deals`, etc.) by removing the package marker.
"""

from __future__ import annotations
