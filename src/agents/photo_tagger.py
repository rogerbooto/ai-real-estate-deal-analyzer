# src/agents/photo_tagger_agent.py
"""
PhotoTaggerAgent (V1.1) — Always-AI in AI mode

Policy update
-------------
- If `AIREAL_USE_VISION=1`, run **AI on every readable image** (batch-first),
  and merge with deterministic tags (keep strongest per label).
- If AI is disabled, run deterministic-only.

Rationale
---------
- Filenames can be mislabeled; in AI mode we “forgive” mislabels and let the
  model do the heavy lifting while retaining deterministic explainability.
- Keeps configuration-driven behavior simple and predictable.

Public API
----------
class PhotoTaggerAgent:
    def analyze(self, photo_paths: list[str]) -> dict
"""

from __future__ import annotations

import os

from src.tools.cv_tagging import tag_photos


class PhotoTaggerAgent:
    def __init__(self) -> None:
        self._vision_enabled = os.getenv("AIREAL_USE_VISION", "0").lower() in ("1", "true", "yes")

    def analyze(self, photo_paths: list[str]) -> dict:
        # Delegate to the orchestrator, which now prefers batch AI when enabled.
        return tag_photos(photo_paths, use_ai=self._vision_enabled)
