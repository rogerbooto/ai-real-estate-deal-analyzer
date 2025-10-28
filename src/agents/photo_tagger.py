# src/agents/photo_tagger_agent.py

from __future__ import annotations

from typing import Any

from src.orchestrators.cv_tagging_orchestrator import CvTaggingOrchestrator


class PhotoTaggerAgent:
    """
    Thin wrapper that delegates to the CV Tagging Orchestrator.

    Benefits:
      - Schema-shaped image records (image_id, path, sha256, tags, readable).
      - Closed-set detections (amenities/defects) with ontology thresholds.
      - Filename-derived materials promoted to amenities in rollup.
    """

    def analyze(self, photo_paths: list[str]) -> dict[str, Any]:
        orc = CvTaggingOrchestrator()
        return orc.analyze_paths(photo_paths)
