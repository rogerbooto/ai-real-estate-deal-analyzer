# tests/core/insights/test_synthesis_field_guard.py
"""
Anti-regression transform guard (Mission 2, Wave 1, root cause 2) for
``synthesize_listing_insights`` (src/core/insights/synthesis.py).

F4 (fixed in commit 6f0642a) was the canonical instance of the defect class this guard
exists to catch: the transform rebuilt ``ListingInsights`` field-by-field and silently
dropped ``title/price/sqft/bedrooms/bathrooms/year_built`` — six stated listing facts that
existed on ``ListingNormalized`` but were never copied across.

This test does NOT hand-list "the six fields we know about today". It enumerates
``ListingNormalized.model_fields`` and ``ListingInsights.model_fields`` dynamically (the
same set-intersection the fix itself uses, computed independently here) and asserts, for
every field name shared by both schemas, that a sentinel value set on the source model
survives into the output. A field added to BOTH schemas under the same name tomorrow is
picked up automatically — no edit to this file required.
"""

from __future__ import annotations

from src.core.insights.synthesis import _COMPUTED_INSIGHT_FIELDS, synthesize_listing_insights
from src.schemas.models import ListingInsights, ListingNormalized, PhotoInsights
from tests.utils import build_sentinel_model

# PhotoInsights.quality_flags has a custom validator (values must be in [0, 1]) that the
# generic sentinel builder can't discover from Field(...) metadata alone (see tests/utils.py
# module docstring). Supply an explicit, valid, non-default override instead of a silent one.
_PHOTO_OVERRIDES = {"quality_flags": {"SENTINEL::quality_flags_key": 0.42}}


def _shared_stated_fact_fields() -> set[str]:
    """
    The fields this test asserts round-trip verbatim: every field name present on BOTH
    schemas, minus the ones the transform is documented to compute itself (see
    ``_COMPUTED_INSIGHT_FIELDS`` in synthesis.py — address/amenities/condition_tags/
    defects/notes have different semantics on each side and are exercised separately
    below, not asserted to be byte-identical passthroughs).

    Computed as a set intersection, not a hand-list, for the same reason the production
    fix does it that way: a field added to both schemas under a shared name is included
    automatically.
    """
    return (set(ListingNormalized.model_fields) & set(ListingInsights.model_fields)) - _COMPUTED_INSIGHT_FIELDS


def test_stated_facts_survive_synthesis_for_every_shared_field() -> None:
    listing = build_sentinel_model(ListingNormalized)
    photos = build_sentinel_model(PhotoInsights, overrides=_PHOTO_OVERRIDES)

    out = synthesize_listing_insights(listing, photos)

    shared = _shared_stated_fact_fields()
    assert shared, "sanity: ListingNormalized and ListingInsights must share at least one stated-fact field"

    failures = []
    for name in sorted(shared):
        expected = getattr(listing, name)
        actual = getattr(out, name)
        if actual != expected:
            failures.append(f"synthesize_listing_insights dropped field {name!r}: expected {expected!r}, got {actual!r}")

    assert not failures, "synthesize_listing_insights silently dropped stated fact(s):\n" + "\n".join(failures)


def test_address_survives_synthesis() -> None:
    """
    ``address`` is one of the ``_COMPUTED_INSIGHT_FIELDS`` (resolved via ``_resolve_address``,
    not a verbatim passthrough), so it's asserted separately: when ``listing.address`` is a
    non-empty sentinel string, the resolver must surface it unchanged (not silently drop it
    in favor of a fallback).
    """
    listing = build_sentinel_model(ListingNormalized)
    photos = build_sentinel_model(PhotoInsights, overrides=_PHOTO_OVERRIDES)

    out = synthesize_listing_insights(listing, photos)

    assert (
        out.address == listing.address
    ), f"synthesize_listing_insights dropped the stated address: expected {listing.address!r}, got {out.address!r}"


def test_computed_fields_are_present_not_silently_empty() -> None:
    """
    amenities/condition_tags/defects/notes are genuinely DERIVED (not passthrough) — this
    test doesn't assert byte-identity with any source field, only that the transform still
    produces *something* for the signals it's supposed to compute from sentinel-populated
    listing/photo inputs, i.e. that the derivation logic itself hasn't silently gone dead.
    """
    listing = build_sentinel_model(ListingNormalized)
    photos = build_sentinel_model(PhotoInsights, overrides=_PHOTO_OVERRIDES)

    out = synthesize_listing_insights(listing, photos)

    # amenities are derived from listing.parking/laundry/heating/cooling (all sentinel-truthy
    # here) plus photos.amenities (sentinel dict with one True-valued entry) -> non-empty.
    assert out.amenities, "synthesize_listing_insights produced no amenities from sentinel-populated inputs"
    # notes always gets a compact size headline when bedrooms/bathrooms/sqft are present.
    assert out.notes, "synthesize_listing_insights produced no notes from sentinel-populated inputs"


def test_guard_is_general_not_hand_tuned_to_f4() -> None:
    """
    Proves the guard enumerates fields rather than hand-listing the six F4 fields: assert
    the shared-field set discovered dynamically actually contains all six historical F4
    fields as a SUBSET, without the test itself hard-coding "these are the only ones".
    """
    shared = _shared_stated_fact_fields()
    f4_fields = {"title", "price", "sqft", "bedrooms", "bathrooms", "year_built"}
    assert f4_fields <= shared, f"expected F4 fields to be a subset of the dynamically-discovered shared fields; got {shared}"
