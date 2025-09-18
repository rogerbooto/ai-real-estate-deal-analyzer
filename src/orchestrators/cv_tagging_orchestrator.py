# src/orchestrators/cv_tagging_orchestrator.py
"""
CV Tagging Orchestrator (Portfolio V1)

Purpose
-------
Provide a single, high-level entry point for computer-vision tagging that:
  - Accepts paths (files or folders) and normalizes them into an ordered list
    of images (preserving caller order and de-duplicating safely).
  - Routes execution to the configured strategy:
      * If `AIREAL_PHOTO_AGENT=1` → use `PhotoTaggerAgent` (which, in AI mode,
        runs AI on every readable image and merges with deterministic tags).
      * Else → call `tag_photos` directly (same schema, deterministic by default).
  - Returns strict, JSON-compatible results (same schema as `tag_photos`).

Design
------
- Pure Python, no network assumptions beyond what the provider requires.
- No business policy duplicated here: all confidence thresholds, ontology
  filtering, and AI/deterministic merging live in `src/tools/cv_tagging.py`.
- Folder/glob convenience is included for CLI or agent callers.
- Stable ordering: original user-provided ordering is respected, with
  de-duplication by absolute path (first occurrence wins).
- Conservative behavior for unreadable inputs: flagged per image, never errors.

Public API
----------
class CvTaggingOrchestrator:
    def analyze_paths(self, photo_paths: list[str]) -> dict
        # direct list of file paths → strict schema dict

    def analyze_folder(self, folder: str, *, recursive: bool = False) -> dict
        # scans a folder for image files, preserves name-sorted stable order

    @staticmethod
    def list_images(folder: str, *, recursive: bool = False) -> list[str]
        # helper used by analyze_folder; exposed for CLI

Environment Flags (honored indirectly)
--------------------------------------
AIREAL_PHOTO_AGENT=1    # use PhotoTaggerAgent (recommended)
AIREAL_USE_VISION=1     # enable AI path inside tagger/orchestrator
AIREAL_VISION_PROVIDER  # "mock" (default) | "openai" | future providers

Notes
-----
- This orchestrator keeps the “single door” mental model for photo tagging.
- Upstream components (CLI, ListingAnalystAgent) should call this, not
  `tag_photos` directly, to preserve feature-flag behavior consistently.

Example
-------
orc = CvTaggingOrchestrator()
out = orc.analyze_folder("data/photos", recursive=True)
# out matches the strict schema from tag_photos

Portfolio signals
-----------------
- Strong separation of concerns: orchestration vs. policy vs. provider.
- Input normalization & stable ordering for reproducibility.
- Explicit guardrails and de-duplication to prevent accidental double-sends.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Iterable, List, Set

from src.tools.cv_tagging import tag_photos


_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
_USE_PHOTO_AGENT = os.getenv("AIREAL_PHOTO_AGENT", "0").lower() in ("1", "true", "yes")
_VISION_ENABLED = os.getenv("AIREAL_USE_VISION", "0").lower() in ("1", "true", "yes")


class CvTaggingOrchestrator:
    """
    High-level orchestrator for CV tagging with folder & list helpers.
    """

    # --------------- Public API ---------------

    def analyze_paths(self, photo_paths: List[str]) -> Dict:
        """
        Analyze an explicit, ordered list of paths.

        Behavior:
        - Preserves order; first occurrence of a real path wins (de-dup).
        - If `AIREAL_PHOTO_AGENT=1`, use PhotoTaggerAgent (which delegates to
          batch-aware cv_tagging). Otherwise call tag_photos directly.
        - Returns strict JSON-compatible dict with images[] and rollup{}.

        Never raises on unreadable inputs; those are flagged per-image.
        """
        normalized = _normalize_paths(photo_paths)
        if not normalized:
            return {"images": [], "rollup": {"amenities": [], "condition_tags": [], "defects": [], "warnings": []}}

        if _USE_PHOTO_AGENT:
            try:
                from src.agents.photo_tagger import PhotoTaggerAgent
                agent = PhotoTaggerAgent()
                return agent.analyze(normalized)
            except Exception:
                # If agent wiring fails, degrade gracefully to direct call
                return tag_photos(normalized, use_ai=_VISION_ENABLED)

        # Direct path (no agent indirection)
        return tag_photos(normalized, use_ai=_VISION_ENABLED)

    def analyze_folder(self, folder: str, *, recursive: bool = False) -> Dict:
        """
        Scan a folder for image files and analyze them.

        - Stable ordering: name-sorted within a folder, and deterministic
          traversal across subfolders when recursive=True.
        - Returns the same strict schema as analyze_paths().
        """
        images = self.list_images(folder, recursive=recursive)
        return self.analyze_paths(images)

    # --------------- Utilities ---------------

    @staticmethod
    def list_images(folder: str, *, recursive: bool = False) -> List[str]:
        """
        Return a stable, name-sorted list of image file paths under `folder`.

        - Filters by known image extensions (case-insensitive).
        - Ignores non-files (directories, symlinks to dirs, etc.).
        - When recursive, sorts directories and files for reproducibility.
        """
        base = Path(folder)
        if not base.exists() or not base.is_dir():
            return []

        if not recursive:
            files = [p for p in sorted(base.iterdir(), key=lambda x: x.name.lower())
                     if p.is_file() and p.suffix.lower() in _IMAGE_EXTS]
            return [str(p) for p in files]

        # Recursive: deterministic directory walk
        collected: List[str] = []
        for dirpath, dirnames, filenames in _walk_sorted(base):
            for name in filenames:
                p = Path(dirpath) / name
                if p.suffix.lower() in _IMAGE_EXTS and p.is_file():
                    collected.append(str(p))
        return collected


# --------------- Internal helpers ---------------

def _normalize_paths(paths: Iterable[str]) -> List[str]:
    """
    Normalize and de-duplicate input paths while preserving first-seen order.

    Rules:
    - Keep entries that point to files with known image extensions *or* unknown
      readability (we do not drop them here; the tagging layer will mark them
      'unreadable' if needed). This ensures the caller’s order is preserved.
    - De-duplication key is the *absolute* path string (case-normalized).
    """
    out: List[str] = []
    seen: Set[str] = set()
    for p in paths:
        # Convert to absolute path for consistent de-dupe semantics
        ap = str(Path(p).resolve())
        key = ap.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(ap)
    return out


def _walk_sorted(base: Path):
    """
    Deterministic recursive directory walk:
    - Yields (dirpath, dirnames, filenames) like os.walk
    - dirnames and filenames sorted case-insensitively
    """
    # Emulate os.walk but sorted
    stack = [base]
    while stack:
        current = stack.pop(0)
        if not current.is_dir():
            continue
        dirnames = sorted([d.name for d in current.iterdir() if d.is_dir()], key=str.lower)
        filenames = sorted([f.name for f in current.iterdir() if f.is_file()], key=str.lower)
        yield (str(current), dirnames, filenames)
        # Queue subdirectories in sorted order
        for d in dirnames:
            stack.append(current / d)
