# tests/core/insights/test_provider_failure_note.py
"""
Gate V (Mission 3) — the one production modification the guardian required before Mission 3 ships.

The problem
-----------
Blocker B-2 fixed a real defect: an image whose provider inference RAISED must never be scored
``filename_contested`` ("a detector examined the pixels and did not report it"), because nothing
examined it. The fix routes that image's filename matches to ``filename_unconfirmed`` instead --
correct, and covered by ``tests/core/cv/test_filename_corroboration.py``'s "Case 4 (B-2)" section.

But the reused reader-facing sentence for that case, ``UNCONFIRMED_HINT_NOTE`` --

    "...but no registered detector can examine the pixels for it..."

-- is inexact in the crash case: a detector IS registered and DOES declare the capability; it
failed at inference. The guardian ruled (and confirmed independently, and this suite re-confirms
below) that ``covered = _covered_labels(provider)`` (``src/core/cv/runner.py``) is resolved ONCE
PER CALL, outside the per-image loop -- so within one run, a given label's unconfirmed entries are
either ALL genuinely-uncovered or ALL covered-but-crashed, never mixed. That is what makes a
single, additive, RUN-LEVEL note true, without rewording ``UNCONFIRMED_HINT_NOTE`` itself and
without per-label/per-image plumbing -- both explicitly out of scope per the guardian's ruling.

What is under test here
------------------------
1. A run WITH provider failures emits :data:`PROVIDER_FAILURE_NOTE` exactly once, with the
   correct count -- on both producers that read notes from photo insights
   (``core.insights.synthesis.synthesize_listing_insights``, the ``build_photo_insights`` /
   ingest path) and its sibling (``agents.listing_analyst.analyze_listing``, the
   ``CvTaggingOrchestrator`` path).
2. A run WITHOUT provider failures emits NO such note on either path -- the byte-identity guard:
   the default pipeline (no provider ever fails) must produce the exact same ``notes`` it produced
   before this change.
3. Both call sites render IDENTICAL text for the same failure count, because both route through
   the same ``amenities_defects.provider_failure_note`` renderer -- the pattern the module already
   follows for ``UNCONFIRMED_HINT_NOTE`` / ``CONTESTED_HINT_NOTE``.

Every image below is a fresh, freshly-dithered synthetic buffer, never a renamed copy of any
fixture used elsewhere in this suite or of anything under ``data/sample_listings/`` -- the on-disk
CV cache is keyed by image sha256, not by filename, so two tests sharing pixel bytes would
silently share (and could poison) a cache entry.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from src.agents.listing_analyst import analyze_listing
from src.core.cv import amenities_defects as ad
from src.core.cv.amenities_defects import provider_failure_note
from src.core.cv.photo_insights import build_photo_insights
from src.core.insights.synthesis import synthesize_listing_insights
from src.schemas.models import ListingNormalized

_MOLD = "mold_suspected"
_FAILURE_PREFIX = "Note: a registered detector failed to examine"


@pytest.fixture
def restore_providers() -> Iterator[None]:
    """Snapshot/restore the provider registry so a test's fake binding cannot leak."""
    saved = dict(ad._PROVIDERS)
    yield
    ad._PROVIDERS.clear()
    ad._PROVIDERS.update(saved)


def _dithered_photo(dirpath: Path, name: str, shade: int) -> Path:
    """A fresh, faintly-dithered near-solid image so ``_filter_photos`` (1 KiB minimum plus a
    low-entropy drop) does not discard it -- content is irrelevant here since the fake provider
    below raises unconditionally regardless of what it is handed.
    """
    dirpath.mkdir(parents=True, exist_ok=True)
    p = dirpath / name
    img = Image.new("RGB", (900, 700), color=(shade, shade, shade))
    px = img.load()
    assert px is not None
    for y in range(0, 700, 3):
        for x in range(0, 900, 3):
            px[x, y] = (max(0, shade - 1), min(255, shade + 1), shade)
    img.save(p, quality=95)
    return p


def _raises_on_every_image(_img: Image.Image) -> list[Any]:
    """A registered detector that crashes every time it is called (hostile model, OOM, a bug)."""
    raise RuntimeError("simulated provider crash: this detector never examined any pixels")


def _silent(_img: Image.Image) -> list[Any]:
    """A detector that looked and reported nothing -- the ordinary Case 1, no crash at all."""
    return []


@pytest.fixture
def two_mold_photos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Two distinct, freshly-generated photos whose file names both trigger the ``mold`` filename
    rule -- so a provider that crashes on every image produces exactly two failures this run.
    """
    monkeypatch.setenv("AIREDEAL_CACHE_DIR", str(tmp_path / "cache"))
    photos_dir = tmp_path / "photos"
    _dithered_photo(photos_dir, "mold_north_wall.jpg", 128)
    _dithered_photo(photos_dir, "mold_south_wall.jpg", 150)
    return photos_dir


def _failure_notes(notes: list[str]) -> list[str]:
    return [n for n in notes if n.startswith(_FAILURE_PREFIX)]


# ---------------------------------------------------------------------------------
# 1) A run WITH provider failures — the note, exactly once, with the correct count.
# ---------------------------------------------------------------------------------


def test_ingest_path_emits_the_failure_note_once_with_the_correct_count(two_mold_photos: Path, restore_providers: None) -> None:
    """``build_photo_insights`` -> ``synthesize_listing_insights``, the default V2 pipeline."""
    ad.register_provider("local", _raises_on_every_image, detects=[_MOLD])

    photos = build_photo_insights(two_mold_photos)
    assert (
        photos.provenance.get("provider_examination_failures", {}).get("count") == 2
    ), f"sanity: expected 2 provider failures this run, got {photos.provenance.get('provider_examination_failures')}"

    insights = synthesize_listing_insights(ListingNormalized(address="1 Test St"), photos)
    matches = _failure_notes(insights.notes)
    assert len(matches) == 1, f"expected exactly one failure note, got: {matches}"
    assert matches[0] == provider_failure_note(2)
    assert "2 photo(s)" in matches[0]
    assert "may reflect" in matches[0], "the wording must stay a possibility, not an assertion"
    assert "does reflect" not in matches[0]


def test_analyst_path_emits_the_failure_note_once_with_the_correct_count(two_mold_photos: Path, restore_providers: None) -> None:
    """``agents.listing_analyst.analyze_listing`` -> ``CvTaggingOrchestrator``, the sibling path."""
    ad.register_provider("local", _raises_on_every_image, detects=[_MOLD])

    insights = analyze_listing(listing_txt_path=None, photos_folder=str(two_mold_photos), fallback_text="1 Test St.")

    matches = _failure_notes(insights.notes)
    assert len(matches) == 1, f"expected exactly one failure note, got: {matches}"
    assert matches[0] == provider_failure_note(2)
    assert "2 photo(s)" in matches[0]


# ---------------------------------------------------------------------------------
# 2) A run WITHOUT provider failures — no such note, on either path. The byte-identity guard:
#    the default pipeline (nothing ever fails) must not gain a new note.
# ---------------------------------------------------------------------------------


def test_ingest_path_emits_no_failure_note_when_nothing_failed(two_mold_photos: Path, restore_providers: None) -> None:
    ad.register_provider("local", _silent, detects=[_MOLD])

    photos = build_photo_insights(two_mold_photos)
    assert "provider_examination_failures" not in photos.provenance

    insights = synthesize_listing_insights(ListingNormalized(address="1 Test St"), photos)
    assert _failure_notes(insights.notes) == []


def test_analyst_path_emits_no_failure_note_when_nothing_failed(two_mold_photos: Path, restore_providers: None) -> None:
    ad.register_provider("local", _silent, detects=[_MOLD])

    insights = analyze_listing(listing_txt_path=None, photos_folder=str(two_mold_photos), fallback_text="1 Test St.")
    assert _failure_notes(insights.notes) == []


def test_default_pipeline_with_no_provider_registered_emits_no_failure_note(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No fake binding at all -- the actual shipped default path. Must stay exactly as before."""
    monkeypatch.setenv("AIREDEAL_CACHE_DIR", str(tmp_path / "cache"))
    photos_dir = tmp_path / "photos"
    _dithered_photo(photos_dir, "mold_hallway.jpg", 128)

    photos = build_photo_insights(photos_dir)
    assert "provider_examination_failures" not in photos.provenance

    insights = synthesize_listing_insights(ListingNormalized(address="1 Test St"), photos)
    assert _failure_notes(insights.notes) == []


# ---------------------------------------------------------------------------------
# 3) Both call sites render IDENTICAL text for the same count -- same renderer, not two strings
#    that happen to look alike.
# ---------------------------------------------------------------------------------


def test_both_call_sites_produce_consistent_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, restore_providers: None) -> None:
    """Each producer gets its OWN folder (and therefore its own image shas), so a warm on-disk
    cache from one call site cannot suppress ``on_provider_failure`` on the other -- caching is
    keyed by (provider, declared capabilities, image sha256), and a cache hit never re-invokes
    the provider function, by design (see ``runner.tag_amenities_and_defects``). Sharing one
    folder between the two calls below would make the SECOND call a cache hit for the FIRST
    call's already-failed images, silently zeroing its failure count -- a fixture artifact, not a
    property of the code under test.
    """
    monkeypatch.setenv("AIREDEAL_CACHE_DIR", str(tmp_path / "cache"))
    ad.register_provider("local", _raises_on_every_image, detects=[_MOLD])

    ingest_dir = tmp_path / "ingest_photos"
    _dithered_photo(ingest_dir, "mold_ceiling.jpg", 90)
    _dithered_photo(ingest_dir, "mold_baseboard.jpg", 170)

    analyst_dir = tmp_path / "analyst_photos"
    _dithered_photo(analyst_dir, "mold_closet.jpg", 60)
    _dithered_photo(analyst_dir, "mold_stairwell.jpg", 200)

    photos = build_photo_insights(ingest_dir)
    ingest_insights = synthesize_listing_insights(ListingNormalized(address="1 Test St"), photos)
    analyst_insights = analyze_listing(listing_txt_path=None, photos_folder=str(analyst_dir), fallback_text="1 Test St.")

    ingest_notes = _failure_notes(ingest_insights.notes)
    analyst_notes = _failure_notes(analyst_insights.notes)
    assert len(ingest_notes) == len(analyst_notes) == 1
    assert ingest_notes[0] == analyst_notes[0] == provider_failure_note(2)
