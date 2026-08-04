# src/core/runtime_flags.py
"""
Environment flags that decide what a run actually did, in a module with no heavy imports.

Why this exists as its own file rather than living beside the code it gates: the report's Run
Provenance appendix must record whether a language model authored the listing observations, and
that record is built on *every* run, including the default deterministic one. Reading the flag
from ``src.agents.crewai_components`` (where it used to live) made ``main.py`` import that module
unconditionally, which transitively imports the ``crewai``/``litellm`` SDK tree — measured at
~2.9s and both packages resident on a run with AI entirely off. That breaks the project's
lazy-heavy-SDK rule, and it bought nothing: the check itself is two lines of ``os.getenv`` with no
dependency on crewai at all. The cost was purely a function of which module the function sat in.

So the flag lives here, and the consumers that *do* pull in heavy SDKs import it from here. One
source of truth, no drift, and the deterministic path stays cheap.

Deliberately reads the environment on each call rather than caching at import, matching how the
crewai path itself consults it — a cached value could disagree with the branch the run actually
took, and a provenance record that disagrees with the run is the defect this whole area is about.
"""

from __future__ import annotations

import os

_TRUTHY = {"1", "true", "yes", "on"}


def llm_mode_enabled() -> bool:
    """Whether ``AIREAL_LLM_MODE`` asks for LLM-backed listing analysis.

    Note this reports the *request*, not the outcome: the flag is only consulted by the crewai
    engine, and even there the model call can fail and fall back to the deterministic path. Callers
    recording provenance must confirm a model actually authored something (see
    ``ListingInsights.observations`` and ``origin="llm"``) rather than treating this as proof.
    """
    return os.getenv("AIREAL_LLM_MODE", "").strip() in _TRUTHY
