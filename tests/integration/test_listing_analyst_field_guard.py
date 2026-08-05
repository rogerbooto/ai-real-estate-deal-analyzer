# tests/integration/test_listing_analyst_field_guard.py
"""
Anti-regression transform guard (Mission 2, Wave 1, root cause 2) for
``analyze_listing`` (src/agents/listing_analyst.py).

``analyze_listing`` builds its ``ListingInsights`` from a text parse
(``parse_listing_text``/``parse_listing_string``) and then merges in photo-derived
signals via ``text_insights.model_copy(update={...})`` — naming only the four fields it
actually merges (amenities/condition_tags/defects/notes). That is the fix pattern F4 also
adopted: ``model_copy(update=...)`` carries every OTHER field across untouched, so a field
added to ``ListingInsights`` tomorrow survives this transform without anyone touching
``listing_analyst.py``.

This guard proves that property empirically: monkeypatch the text-parse entrypoint to
return a fully sentinel-populated ``ListingInsights`` (every field enumerated dynamically
via ``ListingInsights.model_fields`` — nothing hand-listed) and assert every field NOT in
the transform's own named merge-set survives ``analyze_listing`` unchanged.
"""

from __future__ import annotations

from src.agents import listing_analyst
from src.schemas.models import ListingInsights, ObservationProvenance
from tests.utils import build_sentinel_model

# The only fields analyze_listing's merge step (model_copy(update=...)) is documented to
# rewrite — see the "Merge" comment in src/agents/listing_analyst.py. Every other field on
# ListingInsights, present or future, must pass through untouched; that is asserted below by
# enumerating model_fields, not by hand-listing "the fields we expect to survive".
_MERGED_FIELDS = frozenset({"amenities", "condition_tags", "defects", "notes"})

# `observations` (the per-tag provenance ledger) is neither passed through nor unioned: the merge
# REBUILDS it from the text ledger plus the photo ledger, then drops any record whose tag did not
# survive the tag-list merge (src/core/insights/provenance.retain_recorded_tags). A dangling
# provenance record — one attributing a tag the reader cannot find in any list — is worse than no
# record, so "must pass through untouched" is the wrong contract for this field. Its actual
# contract is asserted by test_analyze_listing_rebuilds_the_observation_ledger below.
_REBUILT_FIELDS = frozenset({"observations"})


def _sentinel_insights_with_distinct_items() -> ListingInsights:
    """
    A ListingInsights where every list field has exactly one, uniquely-named item, so
    set-based dedup/union in the merge step can't accidentally collapse two sentinels into
    one and mask a drop.
    """
    return build_sentinel_model(ListingInsights)


def test_analyze_listing_preserves_every_non_merged_field(monkeypatch, tmp_path) -> None:
    sentinel = _sentinel_insights_with_distinct_items()

    # analyze_listing takes a *path* to a text file, not a ListingInsights; the parse step is
    # the seam we control here (fallback_text + parse_listing_string) so we can inject a
    # fully-populated sentinel without depending on the text parser's own field coverage.
    monkeypatch.setattr(listing_analyst, "parse_listing_string", lambda text: sentinel)

    out = listing_analyst.analyze_listing(listing_txt_path=None, photos_folder=None, fallback_text="irrelevant, patched away")

    non_merged = [name for name in ListingInsights.model_fields if name not in _MERGED_FIELDS | _REBUILT_FIELDS]
    assert non_merged, "sanity: ListingInsights must have at least one non-merged field"

    failures = []
    for name in non_merged:
        expected = getattr(sentinel, name)
        actual = getattr(out, name)
        if actual != expected:
            failures.append(f"analyze_listing dropped/changed non-merged field {name!r}: expected {expected!r}, got {actual!r}")

    assert not failures, "analyze_listing silently dropped field(s) it should pass through untouched:\n" + "\n".join(failures)


def test_analyze_listing_merged_fields_still_carry_text_signal_with_no_photos(monkeypatch) -> None:
    """
    With no photos_folder, the merge step still runs but photo-derived sets are empty, so
    each merged field should reduce to exactly the (deduped/sorted) text-derived value —
    the sentinel item must not vanish.
    """
    sentinel = _sentinel_insights_with_distinct_items()
    monkeypatch.setattr(listing_analyst, "parse_listing_string", lambda text: sentinel)

    out = listing_analyst.analyze_listing(listing_txt_path=None, photos_folder=None, fallback_text="irrelevant, patched away")

    for name in sorted(_MERGED_FIELDS):
        expected_items = set(getattr(sentinel, name))
        actual_items = set(getattr(out, name))
        assert (
            expected_items <= actual_items
        ), f"analyze_listing dropped text-derived {name!r} sentinel item(s): {expected_items - actual_items}"


def test_analyze_listing_rebuilds_the_observation_ledger(monkeypatch) -> None:
    """
    The contract for the field in ``_REBUILT_FIELDS``: a text-derived provenance record whose tag
    survives the merge is carried into the output ledger; one whose tag is nowhere in the merged
    tag lists is dropped rather than rendered as a dangling attribution.
    """
    sentinel = build_sentinel_model(ListingInsights)
    kept = ObservationProvenance(tag=sentinel.amenities[0], kind="amenity", origin="listing_text", detail="phrase that fired")
    dangling = ObservationProvenance(tag="tag-that-is-in-no-list", kind="amenity", origin="listing_text", detail="orphan")
    sentinel = sentinel.model_copy(update={"observations": [kept, dangling]})

    monkeypatch.setattr(listing_analyst, "parse_listing_string", lambda text: sentinel)
    out = listing_analyst.analyze_listing(listing_txt_path=None, photos_folder=None, fallback_text="irrelevant, patched away")

    tags = {o.tag for o in out.observations}
    assert kept.tag in tags, "a provenance record whose tag survived the merge must survive with it"
    assert dangling.tag not in tags, "a provenance record attributing a tag that shipped nowhere must be dropped"


def test_guard_is_general_not_hand_tuned_to_known_merge_fields() -> None:
    """
    Proves the non-merged field set is computed dynamically: it must contain every stated
    fact field (title/price/sqft/bedrooms/bathrooms/year_built/address) as a subset, without
    this test hard-coding that as the exhaustive list.
    """
    non_merged = {name for name in ListingInsights.model_fields if name not in _MERGED_FIELDS | _REBUILT_FIELDS}
    known_passthrough = {"address", "title", "price", "sqft", "bedrooms", "bathrooms", "year_built"}
    assert known_passthrough <= non_merged, f"expected known passthrough fields to be a subset of {non_merged}"
