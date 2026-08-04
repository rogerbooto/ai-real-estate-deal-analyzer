# tests/core/cv/test_filename_corroboration.py
"""
M17 / R-6: **a file name may SUGGEST; only a detector that actually looked may CONFIRM.**

The behaviour under test
------------------------
``runner._augment_from_filename`` turns a filename token into one of exactly three things, chosen
by what the CURRENT provider binding declares it is able to detect:

============================  ==========================================  =========================
provider covers the label?    provider reported it?                       result
============================  ==========================================  =========================
yes                           yes                                         ``filename_confirmed``
                                                                          conf = 0.7*cv + 0.3
yes                           no  (a real disagreement)                   ``filename_contested``
                                                                          conf = 0.30
no  (nothing could look)      n/a                                         ``filename_unconfirmed``
                                                                          **no confidence at all**
============================  ==========================================  =========================

Why the third row is not "just score it 0.30"
---------------------------------------------
Because 0.30 would be a measurement of nothing. When a provider covers a label and stays silent,
0.30 means "something looked and disagreed" -- weak, but earned. When no provider can look, the
same number would assert a degree of belief about a question nobody asked. The first is honest and
usefully weak; the second is fabricated precision. So the unconfirmed case carries no number, and
it is kept out of every path that can move a dollar.

Every test here turns RED if the fix is reverted -- see the mission report for literal
before/after output. The pre-fix behaviour was: a blank grey image named ``mold_basement.jpg``
yielded ``defects: ['mold_suspected']`` at a hardcoded 0.90 confidence, with no pixels examined.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from src.agents.financial_forecaster import forecast_financials
from src.agents.listing_analyst import analyze_listing
from src.core.cv import amenities_defects as ad
from src.core.cv.photo_insights import build_photo_insights
from src.core.cv.runner import (
    CV_CONFIRMATION_WEIGHT,
    FILENAME_CORROBORATION_BONUS,
    corroborated_confidence,
    tag_amenities_and_defects,
)
from src.core.finance import engine as finance_engine
from src.core.insights.synthesis import synthesize_listing_insights
from src.orchestrators.cv_tagging_orchestrator import CvTaggingOrchestrator
from src.schemas.models import ListingNormalized
from tests.utils import make_financial_inputs

_MOLD = "mold_suspected"


def _photo(dirpath: Path, name: str) -> Path:
    """A blank grey image big enough to survive the photo sanity filters.

    Blank on purpose: the whole point is that the FILE NAME, not the content, is what used to
    produce a 0.90-confidence defect.
    """
    dirpath.mkdir(parents=True, exist_ok=True)
    p = dirpath / name
    Image.new("RGB", (900, 700), color=(128, 128, 128)).save(p, quality=95)
    return p


@pytest.fixture
def mold_photo(tmp_path: Path) -> Path:
    _photo(tmp_path / "photos", "mold_basement.jpg")
    return tmp_path / "photos"


def _bind(provider: str, fn: Any, *, detects: list[str]) -> None:
    ad.register_provider(provider, fn, detects=detects)  # type: ignore[arg-type]


@pytest.fixture
def restore_providers() -> Iterator[None]:
    """Snapshot/restore the provider registry so a test's fake binding cannot leak."""
    saved = dict(ad._PROVIDERS)
    yield
    ad._PROVIDERS.clear()
    ad._PROVIDERS.update(saved)


def _silent(_img: Image.Image) -> list[Any]:
    """A detector that looked and reported nothing."""
    return []


def _sees_mold(_img: Image.Image) -> list[dict[str, Any]]:
    """A detector that looked and reported mould at 0.80."""
    return [{"name": _MOLD, "confidence": 0.80, "evidence": ["patch_ratio=0.31"]}]


def _only(dets: dict[str, list[Any]], name: str) -> dict[str, Any]:
    matches = [d for per_img in dets.values() for d in per_img if d.get("name") == name]
    assert len(matches) == 1, f"expected exactly one {name!r} entry, got {matches}"
    return dict(matches[0])


# ---------------------------------------------------------------------------------
# The weights themselves
# ---------------------------------------------------------------------------------


def test_the_two_weights_are_a_split_not_two_unrelated_numbers() -> None:
    """70/30 is a split: it must sum to 1.0, or "70% CV + 30% filename" stops being true.

    Pinned so a future recalibration moves both halves deliberately rather than one of them by
    accident. RED if someone tunes 0.70 to 0.85 and forgets the bonus.
    """
    assert CV_CONFIRMATION_WEIGHT + FILENAME_CORROBORATION_BONUS == pytest.approx(1.0)
    assert 0.0 < FILENAME_CORROBORATION_BONUS < 1.0


def test_the_bonus_is_flat_because_a_filename_match_is_binary() -> None:
    """The 0.30 does not scale with anything: there is no "more matched" file name.

    A corroborated score is therefore always exactly the bonus above the discounted detector
    confidence -- which is what makes it readable as "credit for a second signal", not "we are
    30% sure".
    """
    for cv in (0.0, 0.25, 0.5, 0.9, 1.0):
        assert corroborated_confidence(cv) - CV_CONFIRMATION_WEIGHT * cv == pytest.approx(FILENAME_CORROBORATION_BONUS)


def test_a_contested_score_lands_below_the_strong_threshold_the_pipeline_already_uses() -> None:
    """0.30 must stay under the 0.6 bar ``photo_insights._parking_summary`` calls "strong".

    That is what makes case 1 *usefully* weak rather than merely small: a filename-only claim
    cannot, on its own, promote a property to "has a garage".
    """
    assert corroborated_confidence(0.0) == pytest.approx(0.30)
    assert corroborated_confidence(0.0) < 0.6


# ---------------------------------------------------------------------------------
# Case 2 — nothing can look
# ---------------------------------------------------------------------------------


def test_uncovered_label_carries_no_confidence_at_all(mold_photo: Path) -> None:
    """RED on revert. Pre-fix this entry read ``confidence: 0.90, source: "filename"``.

    The built-in providers declare only light and grey, so mould is a question nothing in this
    process is able to answer. The record says so by omitting the number entirely -- an absent
    confidence and a low confidence are different claims, and only one of them is true here.
    """
    assert _MOLD not in ad.provider_capabilities("local"), "fixture assumption: no built-in provider covers mould"

    det = _only(tag_amenities_and_defects([mold_photo / "mold_basement.jpg"], provider="local", use_cache=False), _MOLD)

    assert det["source"] == "filename_unconfirmed"
    assert "confidence" not in det, f"a label nothing measured was given a confidence: {det}"
    assert ad.is_unconfirmed_hint(det)


def test_uncovered_label_never_reaches_the_insight_modifiers(mold_photo: Path) -> None:
    """RED on revert, and the load-bearing test of this whole change.

    ``finance.engine._apply_insight_modifiers`` selects OPEX and income rules by membership in
    ``insights.amenities`` / ``condition_tags`` / ``defects``. This asserts on what the REAL engine
    function actually receives on the real deterministic path, not on an intermediate object: a tag
    that never arrives cannot select a rule, whatever the rule table grows into later.
    """
    seen: dict[str, list[str]] = {}
    original = finance_engine._apply_insight_modifiers

    def _spy(income: Any, opex: Any, insights: Any, **kwargs: Any) -> Any:
        seen["amenities"] = list(insights.amenities) if insights else []
        seen["condition_tags"] = list(insights.condition_tags) if insights else []
        seen["defects"] = list(insights.defects) if insights else []
        return original(income, opex, insights, **kwargs)

    finance_engine._apply_insight_modifiers = _spy  # type: ignore[assignment]
    try:
        insights = analyze_listing(listing_txt_path=None, photos_folder=str(mold_photo), fallback_text="1 Test St.")
        forecast_financials(inputs=make_financial_inputs(), insights=insights, horizon_years=2)
    finally:
        finance_engine._apply_insight_modifiers = original  # type: ignore[assignment]

    assert seen, "sanity: the engine's modifier hook never ran"
    for list_name, tags in seen.items():
        assert _MOLD not in tags, f"an unmeasured filename claim reached the money path via {list_name}: {tags}"


def test_uncovered_hint_is_shown_to_the_reader_rather_than_dropped(mold_photo: Path) -> None:
    """Keeping it out of the money path must not mean hiding it.

    ``notes`` is the carrier because the report renders it and the finance core never reads it.
    RED if the hint is silently swallowed instead of surfaced.
    """
    insights = analyze_listing(listing_txt_path=None, photos_folder=str(mold_photo), fallback_text="1 Test St.")

    hint_notes = [n for n in insights.notes if _MOLD in n]
    assert hint_notes, f"the hint vanished entirely; the reader learns nothing: {insights.notes}"
    note = hint_notes[0]
    assert "no registered detector" in note
    assert "does not affect any number" in note


def test_uncovered_hint_is_not_counted_as_a_detection_in_photo_insights(mold_photo: Path) -> None:
    """The ingest path's roll-ups must separate "a detector saw it" from "a file name said it"."""
    photos = build_photo_insights(mold_photo)

    assert photos.defect_counts == {}, f"an unmeasured claim was counted as a defect: {photos.defect_counts}"
    assert photos.unconfirmed_hint_counts.get(_MOLD) == 1
    # ...and it stays out of ListingInsights.defects on that path too.
    insights = synthesize_listing_insights(ListingNormalized(address="1 Test St"), photos)
    assert _MOLD not in insights.defects
    assert any(_MOLD in n for n in insights.notes)


# ---------------------------------------------------------------------------------
# Case 1 — a detector covers the label and did not report it
# ---------------------------------------------------------------------------------


def test_covered_but_unfired_label_scores_exactly_the_bonus(mold_photo: Path, restore_providers: None) -> None:
    """RED on revert. Something looked and disagreed, so the claim is scoreable -- and scores 0.30.

    This is the case the naive formula gets right, and the only case in which 0.30 means anything.
    """
    _bind("onnx", _silent, detects=[_MOLD])

    det = _only(tag_amenities_and_defects([mold_photo / "mold_basement.jpg"], provider="onnx", use_cache=False), _MOLD)

    assert det["source"] == "filename_contested"
    assert det["confidence"] == pytest.approx(0.30)
    assert not ad.is_unconfirmed_hint(det)
    assert "did not report it" in str(det["rationale"])


def test_a_contested_label_does_enter_the_tag_lists(mold_photo: Path, restore_providers: None) -> None:
    """The guard is narrow on purpose: only the UNMEASURED case is withheld.

    A contested label is a real, weak signal about the property and belongs in ``defects`` where
    the reader and the rules can see it. Withholding it too would be its own dishonesty.
    """
    _bind("local", _silent, detects=[_MOLD])

    rollup = CvTaggingOrchestrator().analyze_folder(str(mold_photo))["rollup"]

    assert _MOLD in rollup["defects"]
    assert _MOLD not in rollup["unconfirmed_hints"]


# ---------------------------------------------------------------------------------
# Case 3 — a detector covers the label and reported it
# ---------------------------------------------------------------------------------


def test_covered_and_fired_label_scores_the_seventy_thirty_blend(mold_photo: Path, restore_providers: None) -> None:
    """RED on revert: 0.7 x 0.80 + 0.30 = 0.86. Two independent signals agreeing raises confidence.

    The detector's OWN number is preserved in the rationale rather than overwritten silently --
    a reader must be able to recover what the detector actually said.
    """
    _bind("onnx", _sees_mold, detects=[_MOLD])

    det = _only(tag_amenities_and_defects([mold_photo / "mold_basement.jpg"], provider="onnx", use_cache=False), _MOLD)

    assert det["source"] == "filename_confirmed"
    assert det["confidence"] == pytest.approx(CV_CONFIRMATION_WEIGHT * 0.80 + FILENAME_CORROBORATION_BONUS)
    assert det["confidence"] == pytest.approx(0.86)
    assert "0.80" in str(det["rationale"]), "the detector's own confidence was overwritten without trace"
    assert "patch_ratio=0.31" in (det["evidence"] or []), "the detector's evidence was discarded"


def test_corroboration_is_applied_once_not_compounded_by_a_warm_cache(mold_photo: Path, restore_providers: None, tmp_path: Path) -> None:
    """The bonus must not be re-added every time a cached entry is re-read.

    ``tag_amenities_and_defects`` deliberately re-runs the filename pass over cache hits, so
    without the already-corroborated guard 0.86 would drift to 0.90, 0.93, ... on repeat runs.
    """
    _bind("onnx", _sees_mold, detects=[_MOLD])
    img = mold_photo / "mold_basement.jpg"

    first = _only(tag_amenities_and_defects([img], provider="onnx", use_cache=True), _MOLD)
    second = _only(tag_amenities_and_defects([img], provider="onnx", use_cache=True), _MOLD)
    third = _only(tag_amenities_and_defects([img], provider="onnx", use_cache=True), _MOLD)

    assert first["confidence"] == pytest.approx(0.86)
    assert second["confidence"] == pytest.approx(0.86)
    assert third["confidence"] == pytest.approx(0.86)


# ---------------------------------------------------------------------------------
# Auto-upgrade — the point of the capability declaration
# ---------------------------------------------------------------------------------


def test_registering_a_covering_provider_moves_the_same_input_from_case_2_to_case_1(mold_photo: Path, restore_providers: None) -> None:
    """RED on revert, and the reason capabilities are keyed by FUNCTION and not by slot name.

    Identical image, identical file name, identical call. The only thing that changes is which
    function is bound to the ``local`` slot -- and the label moves from "nothing measured it" to
    "something looked and disagreed" with no edit to any rule, table or label list.
    """
    img = mold_photo / "mold_basement.jpg"

    before = _only(tag_amenities_and_defects([img], provider="local", use_cache=True), _MOLD)
    assert before["source"] == "filename_unconfirmed"
    assert "confidence" not in before

    _bind("local", _silent, detects=[_MOLD])

    after = _only(tag_amenities_and_defects([img], provider="local", use_cache=True), _MOLD)
    assert after["source"] == "filename_contested", "registering a covering detector changed nothing -- the upgrade is not automatic"
    assert after["confidence"] == pytest.approx(0.30)


def test_a_warm_cache_cannot_serve_a_pre_registration_answer(mold_photo: Path, restore_providers: None) -> None:
    """The auto-upgrade guarantee has to survive the cache, or it is a guarantee only on cold disks.

    Cache entries are keyed by (provider slot, declared capabilities, image sha). Registering a
    detector with a different vocabulary lands in a different namespace, so the previous answer
    is neither read nor overwritten -- it simply stops being the answer to this question.
    """
    img = mold_photo / "mold_basement.jpg"

    tag_amenities_and_defects([img], provider="local", use_cache=True)  # warms the cache
    _bind("local", _silent, detects=[_MOLD])

    after = _only(tag_amenities_and_defects([img], provider="local", use_cache=True), _MOLD)
    assert after["source"] == "filename_contested", "a stale cached classification outlived the reason it was true"


def test_the_upgrade_reaches_the_reader_facing_lists_too(mold_photo: Path, restore_providers: None) -> None:
    """End-to-end: the same photo folder yields a note before registration and a defect after."""
    before = analyze_listing(listing_txt_path=None, photos_folder=str(mold_photo), fallback_text="1 Test St.")
    assert _MOLD not in before.defects
    assert any(_MOLD in n for n in before.notes)

    _bind("local", _silent, detects=[_MOLD])

    after = analyze_listing(listing_txt_path=None, photos_folder=str(mold_photo), fallback_text="1 Test St.")
    assert _MOLD in after.defects, "the label never graduated out of the hint channel"
    assert not any("Unconfirmed photo hint" in n and _MOLD in n for n in after.notes)


# ---------------------------------------------------------------------------------
# The declarations themselves
# ---------------------------------------------------------------------------------


def test_every_builtin_declares_a_vocabulary_and_it_is_small_and_honest() -> None:
    """The built-in stubs are three thresholds over image statistics. Their declarations say so.

    Guards the failure mode that would silently un-do this whole feature: declaring the full
    ontology for a stub would tell every filename claim "a detector covers you and disagreed",
    scoring all six at 0.30 -- the exact fabricated-precision outcome the guard exists to avoid.
    """
    for provider in ("local", "vision", "llm"):
        caps = ad.provider_capabilities(provider)  # type: ignore[arg-type]
        assert caps, f"{provider} declares no vocabulary at all"
        assert len(caps) <= 3, f"{provider} claims a suspiciously broad vocabulary for a heuristic stub: {sorted(caps)}"

    # And none of them claims any of the six labels a file name is allowed to suggest.
    from src.core.cv.runner import _FILENAME_RULES, _covered_labels

    suggestible = {rule.label for rule in _FILENAME_RULES}
    for provider in ("local", "vision", "llm"):
        assert not (_covered_labels(provider) & suggestible), f"{provider} declares coverage it does not have"  # type: ignore[arg-type]


@pytest.mark.parametrize("provider", ["local", "vision", "llm"])
def test_a_stub_never_emits_a_label_it_did_not_declare(provider: str, tmp_path: Path) -> None:
    """Declaration >= emission, checked against the functions rather than trusted.

    A threshold added to a stub without updating its declaration would make that provider silently
    under-declare, which is the one direction that cannot be caught by reading the table.
    """
    from src.core.cv.amenities_defects import detect_from_image
    from src.core.cv.ontology import AMENITIES_DEFECTS_V1

    declared = {
        meta["name"]
        for raw in ad.provider_capabilities(provider)  # type: ignore[arg-type]
        if (meta := AMENITIES_DEFECTS_V1.lookup(raw)) is not None
    }

    # Sweep the input space the stubs actually branch on: brightness, greyness, orientation.
    for size in ((96, 64), (64, 96), (64, 64)):
        for shade in (0, 60, 128, 200, 245, 255):
            for tint in ((0, 0, 0), (30, 0, 0), (0, 0, 30)):
                colour = tuple(min(255, shade + t) for t in tint)
                img = Image.new("RGB", size, color=colour)  # type: ignore[arg-type]
                emitted = {d["name"] for d in detect_from_image(img, provider=provider, ontology=AMENITIES_DEFECTS_V1)}  # type: ignore[arg-type]
                undeclared = emitted - declared
                assert not undeclared, f"{provider} emitted {sorted(undeclared)} without declaring it"


def test_an_undeclared_provider_covers_nothing_rather_than_everything(mold_photo: Path, restore_providers: None) -> None:
    """Silence is not evidence that something looked.

    A function poked straight into ``_PROVIDERS`` (which several tests and any quick script do)
    declares nothing. Treating that as full coverage would score every filename claim 0.30 on the
    strength of a provider that may not look for any of them.

    Uses a function this module never registers: declarations are keyed by the function object and
    outlive any one binding on purpose (a function's vocabulary is a property of the function, not
    of the slot it happens to occupy), so reusing a previously-declared helper here would be
    asserting on this test file's history rather than on the behaviour.
    """

    def _never_declared(_img: Image.Image) -> list[dict[str, Any]]:
        return [{"name": _MOLD, "confidence": 0.80}]

    ad._PROVIDERS["onnx"] = _never_declared

    assert ad.provider_capabilities("onnx") == frozenset()
    det = _only(tag_amenities_and_defects([mold_photo / "mold_basement.jpg"], provider="onnx", use_cache=False), _MOLD)
    # The detector DID fire, so this is still a confirmed corroboration -- coverage only decides
    # what happens when it does NOT fire.
    assert det["source"] == "filename_confirmed"


def test_provider_capabilities_rejects_an_unregistered_provider(restore_providers: None) -> None:
    """Same loud failure as ``detect_from_image``/``provider_kind``: no silent empty answer."""
    ad._PROVIDERS.pop("onnx", None)
    with pytest.raises(ValueError):
        ad.provider_capabilities("onnx")


def test_an_onnx_labels_file_is_the_capability_declaration(monkeypatch: pytest.MonkeyPatch, restore_providers: None) -> None:
    """``register_onnx_provider(model_path, labels_path)`` already takes the vocabulary; use it.

    Stubs ``_OnnxModel`` so this runs without onnxruntime or a real model file: what is under test
    is that the labels a model was built with become what the pipeline believes it can see, not
    onnxruntime's behaviour.
    """

    class _FakeOnnxModel:
        def __init__(self, model_path: str, labels_path: str, **kwargs: Any) -> None:
            self.labels = [_MOLD, "parking_garage"]

        def predict_proba(self, img: Image.Image) -> list[tuple[str, float]]:
            return [(_MOLD, 0.42)]

    monkeypatch.setattr(ad, "_OnnxModel", _FakeOnnxModel)
    ad.register_onnx_provider("model.onnx", "labels.json")

    assert ad.provider_capabilities("onnx") == frozenset({_MOLD, "parking_garage"})
