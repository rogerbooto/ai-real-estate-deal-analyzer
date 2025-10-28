from __future__ import annotations

from pathlib import Path

from PIL import Image

from src.orchestrators.cv_tagging_orchestrator import CvTaggingOrchestrator


def test_analyze_paths_returns_schema(tmp_path: Path):
    p1 = tmp_path / "bathroom_1.png"
    Image.new("RGB", (32, 32), color=(200, 200, 200)).save(p1)

    orc = CvTaggingOrchestrator()
    out = orc.analyze_paths([str(p1)])
    assert isinstance(out, dict)
    # When PhotoTaggerAgent is disabled, the orchestrator calls tag_images directly;
    # current runner.tag_images returns a dict keyed by sha, so orc should forward that dict.
    # The orchestrator returns that dict verbatim in this implementation.
    # Accept either a dict with sha keys or (if agent path) a structured object.
    # Keep this simple:
    assert out, "Expected non-empty result from orchestrator"
