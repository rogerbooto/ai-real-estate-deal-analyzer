# src/core/insights/synthesis.py
"""
Synthesize a durable ListingInsights from normalized primitives.

Inputs:
  - ListingNormalized: parsed facts (title, price, beds/baths, hvac, parking, etc.)
  - PhotoInsights    : room counts, amenity booleans, quality scores

Output:
  - ListingInsights  : address (guaranteed non-empty), stated facts (title, price, sqft,
                       bedrooms, bathrooms, year_built - passed through from the normalized
                       listing, None when not stated), amenities, condition_tags, defects, notes

Design goals
------------
- Single source of truth: no scraping or CV here; we only adapt normalized inputs.
- Deterministic: pure function without side effects/network access.
- Address guard: always emit a non-empty address (fallbacks documented below).
"""

from __future__ import annotations

from urllib.parse import urlparse

from src.core.cv.amenities_defects import unconfirmed_hint_note
from src.core.insights.provenance import (
    attach,
    derived_observation,
    detection_observation,
    filename_observation,
    text_observation,
    unattributed_observation,
)
from src.schemas.labels import (
    MATERIAL_TO_AMENITY_SURFACE,
    PARKING_SPECIFIC_AMENITIES,
    PHOTOINSIGHTS_AMENITY_SURFACE,
    AmenityLabel,
    MaterialTag,
)
from src.schemas.models import (
    ListingInsights,
    ListingNormalized,
    ObservationProvenance,
    PhotoInsights,
)

# ----------------------------
# Address resolution
# ----------------------------


def _resolve_address(listing: ListingNormalized) -> str:
    """
    Guarantee a non-empty address string for downstream agents.

    Priority:
      1) listing.address (if present and non-empty)
      2) A synthesized hint from source_url (netloc/path shard)
      3) listing.title if it looks like an address
      4) "Unknown address"

    Notes:
      - We deliberately keep this conservative. If you later add a text/DOM-based
        address extractor, do it upstream and set listing.address explicitly.
    """
    if listing.address and listing.address.strip():
        return listing.address.strip()

    # Try to compose a stable hint from the source URL
    if listing.source_url:
        try:
            u = urlparse(listing.source_url)
            host = (u.netloc or "").strip()
            tail = (u.path or "").strip("/").split("/")[-1] if u.path else ""
            if host:
                if tail:
                    return f"{host} :: {tail}"
                return host
        except Exception:
            pass

    # If title looks address-like (very light heuristic), use it
    if listing.title and any(
        k in listing.title.lower() for k in ("st", "street", "ave", "rd", "road", "blvd", "dr", "lane", "ln", "court", "ct")
    ):
        return listing.title.strip()

    return "Unknown address"


# ----------------------------
# Amenity synthesis
# ----------------------------


def _provider_facts(photos: PhotoInsights) -> tuple[str | None, str | None, str | None]:
    """(provider, provider_kind, provider_version) as recorded by ``build_photo_insights``.

    Read from ``photos.provenance`` rather than assumed, because a PhotoInsights built by an
    older producer (or a test factory) legitimately has neither key -- in which case the
    provenance records say so instead of naming a provider that never ran.
    """
    prov = photos.provenance or {}
    provider = prov.get("selected_provider")
    kind = prov.get("provider_kind")
    return (
        str(provider) if isinstance(provider, str) else None,
        str(kind) if isinstance(kind, str) else None,
        photos.version or None,
    )


def _surface_key_for_detection(name: str) -> str | None:
    """Which PhotoInsights amenity-surface key an ontology detection name feeds, if any.

    Mirrors ``core.cv.photo_insights._amenities_surface_from`` (detections -> surface) and
    ``labels.to_photoinsights_amenities_surface`` (parking specifics -> "parking"). Walking that
    mapping backwards is what lets a surfaced boolean point at the detection that set it.
    """
    lowered = name.lower()
    if lowered == "laundry_in_unit":
        return AmenityLabel.in_unit_laundry.value
    if lowered == MaterialTag.stainless_appliances.value:
        return AmenityLabel.stainless_kitchen.value
    if lowered in {a.value for a in PARKING_SPECIFIC_AMENITIES}:
        return AmenityLabel.parking.value
    try:
        label = AmenityLabel(lowered)
    except ValueError:
        return None
    return label.value if label in PHOTOINSIGHTS_AMENITY_SURFACE else None


def _photo_amenity_observations(photos: PhotoInsights, *, surface_key: str, tag: str) -> list[ObservationProvenance]:
    """Explain one True amenity boolean: which detections and/or filenames set it.

    Returns one record per supporting sighting. When nothing supports it -- the boolean is True
    but no detection and no filename token in this PhotoInsights accounts for it -- a single
    ``unknown`` record is emitted. That case is real (a caller can hand-build the boolean map),
    and saying "we cannot attribute this" is the honest answer, not silence.
    """
    provider, provider_kind_val, version = _provider_facts(photos)
    out: list[ObservationProvenance] = []

    for sha, dets in (photos.image_detections or {}).items():
        for det in dets or []:
            # `PhotoInsights.image_detections` is `dict[str, list[DetectedLabelModel]]`
            # (models.py:622), so this is always a model. The raw-dict fallback that used to
            # live here was unreachable, and --strict mypy said so by narrowing `{}` to
            # `dict[Never, Never]`; a defensive branch that cannot run is just untested code.
            name = det.name
            if _surface_key_for_detection(name) != surface_key:
                continue
            out.append(
                detection_observation(
                    det,
                    tag=tag,
                    kind="amenity",
                    provider=provider or "unknown",
                    provider_kind=provider_kind_val,
                    provider_version=version,
                    source_image_sha=sha,
                )
            )

    for sha, labels in (photos.image_labels or {}).items():
        for lab in labels or []:
            try:
                material = MaterialTag(str(lab))
            except ValueError:
                continue
            mapped = MATERIAL_TO_AMENITY_SURFACE.get(material)
            if mapped is not None and mapped.value == surface_key:
                out.append(filename_observation(tag, kind="amenity", detail=material.value, source_image_sha=sha))

    if not out:
        out.append(
            unattributed_observation(tag, kind="amenity", detail=f"photo amenity surface '{surface_key}' with no supporting detection")
        )
    return out


def _amenities_from(listing: ListingNormalized, photos: PhotoInsights) -> tuple[list[str], list[ObservationProvenance]]:
    """
    Union of normalized listing facts and photo-derived amenities.
    Only include amenities that are confidently true/explicit.

    Also returns one provenance record per sighting: an amenity stated by the copy AND seen in a
    photo yields two, so a reader can tell agreement from a single unverified claim.
    """
    out: set[str] = set()
    observations: list[ObservationProvenance] = []

    # From normalized listing facts
    if listing.parking:
        out.add("parking")
        observations.append(text_observation("parking", kind="amenity", detail=f"listing.parking={listing.parking}"))
    if listing.laundry:
        # normalize laundry variants to canonical names for ListingInsights
        if listing.laundry == "in-unit":
            out.add("in-unit laundry")
            observations.append(text_observation("in-unit laundry", kind="amenity", detail=f"listing.laundry={listing.laundry}"))
        elif listing.laundry == "on-site":
            out.add("on-site laundry")
            observations.append(text_observation("on-site laundry", kind="amenity", detail=f"listing.laundry={listing.laundry}"))
        elif listing.laundry == "none":
            pass  # explicit none → don't add
        else:
            out.add("laundry")
            observations.append(text_observation("laundry", kind="amenity", detail=f"listing.laundry={listing.laundry}"))

    if listing.heating:
        out.add(f"heating:{listing.heating}")
        observations.append(text_observation(f"heating:{listing.heating}", kind="amenity", detail=f"listing.heating={listing.heating}"))
    if listing.cooling:
        out.add(f"cooling:{listing.cooling}")
        observations.append(text_observation(f"cooling:{listing.cooling}", kind="amenity", detail=f"listing.cooling={listing.cooling}"))

    # From photo insights (boolean map)
    for k, v in photos.amenities.items():
        if not v:
            continue
        # map project-internal keys to human-friendly
        if k == "in_unit_laundry":
            tag = "in-unit laundry"
        elif k == "stainless_kitchen":
            tag = "stainless appliances"
        elif k == "kitchen_island":
            tag = "kitchen island"
        else:
            tag = k.replace("_", " ")
        out.add(tag)
        observations.extend(_photo_amenity_observations(photos, surface_key=k, tag=tag))

    return sorted(out), observations


# ----------------------------
# Condition & quality notes
# ----------------------------


def _condition_tags_from(photos: PhotoInsights) -> tuple[list[str], list[ObservationProvenance]]:
    """
    Convert quality flags into coarse condition tags using simple thresholds.

    These tags are DERIVED from an aggregate score, not from any single detection, so their
    provenance carries the threshold that tripped in ``detail`` and no ``DetectedLabelModel``.
    The producing provider is still named, because the scores came from its output.
    """
    provider, provider_kind_val, version = _provider_facts(photos)

    def _derived(tag: str, metric: str, value: float, bound: str) -> ObservationProvenance:
        return derived_observation(
            tag,
            kind="condition",
            detail=f"{metric}={value:.2f} {bound}",
            provider=provider,
            provider_kind=provider_kind_val,
            provider_version=version,
        )

    tags: set[str] = set()
    observations: list[ObservationProvenance] = []
    reno = photos.quality_flags.get("renovated_score", 0.0)
    light = photos.quality_flags.get("natural_light_score", 0.0)
    curb = photos.quality_flags.get("curb_appeal_score", 0.0)

    if reno >= 0.6:
        tags.add("renovated")
        observations.append(_derived("renovated", "renovated_score", reno, ">= 0.60"))
    elif 0.35 <= reno < 0.6:
        tags.add("partially updated")
        observations.append(_derived("partially updated", "renovated_score", reno, "in [0.35, 0.60)"))

    if light >= 0.6:
        tags.add("good natural light")
        observations.append(_derived("good natural light", "natural_light_score", light, ">= 0.60"))

    if curb >= 0.6:
        tags.add("strong curb appeal")
        observations.append(_derived("strong curb appeal", "curb_appeal_score", curb, ">= 0.60"))

    return sorted(tags), observations


def _notes_from(listing: ListingNormalized, photos: PhotoInsights) -> list[str]:
    """
    Compact human notes blending listing.notes and a couple of derived lines.
    """
    notes: list[str] = []
    if listing.notes:
        notes.extend([s.strip() for s in str(listing.notes).split(";") if s.strip()])

    # include a compact size headline when available
    if listing.bedrooms is not None or listing.bathrooms is not None or listing.sqft is not None:
        parts: list[str] = []
        if listing.bedrooms is not None:
            br = int(listing.bedrooms) if listing.bedrooms.is_integer() else listing.bedrooms
            parts.append(f"{br} BR")
        if listing.bathrooms is not None:
            ba = int(listing.bathrooms) if float(listing.bathrooms).is_integer() else listing.bathrooms
            parts.append(f"{ba} BA")
        if listing.sqft is not None:
            parts.append(f"{listing.sqft:,} sqft")
        if parts:
            notes.append(" • ".join(parts))

    # mention provider/version used for image analysis for traceability
    if photos.provider and photos.version:
        notes.append(f"vision:{photos.provider}@{photos.version}")

    # Labels a file name suggested that no registered provider is able to look for. They are
    # deliberately absent from `amenities`/`condition_tags`/`defects` -- those three lists are what
    # `finance.engine._apply_insight_modifiers` reads, and an unmeasured claim must not be able to
    # select an OPEX or income rule. `notes` is read by the report and by nothing in the finance
    # core, so the reader still learns the hint exists without it touching a number.
    notes.extend(unconfirmed_hint_note(label) for label in sorted(photos.unconfirmed_hint_counts or {}))

    return notes


# ----------------------------
# Stated-fact passthrough
# ----------------------------

# Fields on ListingInsights that we compute ourselves (via the helpers above) rather
# than copy verbatim from ListingNormalized. "address" and "notes" happen to exist on
# both models but with different semantics/types there (address is resolved with
# fallbacks; notes is a derived list vs. a raw string) so they must stay excluded.
_COMPUTED_INSIGHT_FIELDS = frozenset({"address", "amenities", "condition_tags", "defects", "notes"})


def _stated_facts_from(listing: ListingNormalized) -> dict[str, object]:
    """
    Carry every "stated fact" straight through from the normalized listing to
    ListingInsights: any field whose name is shared by both schemas (title, price,
    sqft, bedrooms, bathrooms, year_built today) and isn't one of the fields we derive
    ourselves. Computed as a set intersection - rather than hand-listing the field
    names - so that a future field added with the same name to both schemas flows
    through automatically instead of being silently dropped by this transform.
    """
    shared = (set(ListingInsights.model_fields) & set(ListingNormalized.model_fields)) - _COMPUTED_INSIGHT_FIELDS
    return {name: getattr(listing, name) for name in shared}


def synthesize_listing_insights(listing: ListingNormalized, photos: PhotoInsights) -> ListingInsights:
    """
    Deterministically construct ListingInsights:
      • address: always non-empty (resolver fallback)
      • stated facts (title/price/sqft/bedrooms/bathrooms/year_built): passed through
        verbatim from the normalized listing; None when not stated/parsed
      • amenities: merged from listing + photos
      • condition_tags: derived from photo quality flags (thresholded)
      • defects: (placeholder for future wired signals; empty for now)
      • notes: compact, human-friendly rollup
    """
    address = _resolve_address(listing)
    stated_facts = _stated_facts_from(listing)
    amenities, amenity_observations = _amenities_from(listing, photos)
    condition, condition_observations = _condition_tags_from(photos)
    defects: list[str] = []  # keep empty until wired to explicit signals
    notes = _notes_from(listing, photos)

    # Add a concise amenities roll-up note if any are present (sorted for determinism)
    try:
        present_amenities = sorted([k for k, v in (photos.amenities or {}).items() if v])
    except Exception:
        present_amenities = []
    if present_amenities:
        note = "Amenities present: " + ", ".join(present_amenities)
        if note not in notes:
            notes.append(note)

    insights = ListingInsights(
        address=address,
        amenities=amenities,
        condition_tags=condition,
        defects=defects,
        notes=notes,
        **stated_facts,
    )
    return attach(insights, [*amenity_observations, *condition_observations])
