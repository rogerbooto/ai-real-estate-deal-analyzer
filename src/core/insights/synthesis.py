# src/core/insights/synthesis.py
"""
Synthesize a durable ListingInsights from normalized primitives.

Inputs:
  - ListingNormalized: parsed facts (title, price, beds/baths, hvac, parking, etc.)
  - PhotoInsights    : room counts, amenity booleans, quality scores

Output:
  - ListingInsights  : address (guaranteed non-empty), amenities, condition_tags, defects, notes

Design goals
------------
- Single source of truth: no scraping or CV here; we only adapt normalized inputs.
- Deterministic: pure function without side effects/network access.
- Address guard: always emit a non-empty address (fallbacks documented below).
"""

from __future__ import annotations

from urllib.parse import urlparse

from src.schemas.models import ListingInsights, ListingNormalized, PhotoInsights

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


def _amenities_from(listing: ListingNormalized, photos: PhotoInsights) -> list[str]:
    """
    Union of normalized listing facts and photo-derived amenities.
    Only include amenities that are confidently true/explicit.
    """
    out: set[str] = set()

    # From normalized listing facts
    if listing.parking:
        out.add("parking")
    if listing.laundry:
        # normalize laundry variants to canonical names for ListingInsights
        if listing.laundry == "in-unit":
            out.add("in-unit laundry")
        elif listing.laundry == "on-site":
            out.add("on-site laundry")
        elif listing.laundry == "none":
            pass  # explicit none → don't add
        else:
            out.add("laundry")

    if listing.heating:
        out.add(f"heating:{listing.heating}")
    if listing.cooling:
        out.add(f"cooling:{listing.cooling}")

    # From photo insights (boolean map)
    for k, v in photos.amenities.items():
        if not v:
            continue
        # map project-internal keys to human-friendly
        if k == "in_unit_laundry":
            out.add("in-unit laundry")
        elif k == "stainless_kitchen":
            out.add("stainless appliances")
        elif k == "kitchen_island":
            out.add("kitchen island")
        else:
            out.add(k.replace("_", " "))

    return sorted(out)


# ----------------------------
# Condition & quality notes
# ----------------------------


def _condition_tags_from(photos: PhotoInsights) -> list[str]:
    """
    Convert quality flags into coarse condition tags using simple thresholds.
    """
    tags: set[str] = set()
    reno = photos.quality_flags.get("renovated_score", 0.0)
    light = photos.quality_flags.get("natural_light_score", 0.0)
    curb = photos.quality_flags.get("curb_appeal_score", 0.0)

    if reno >= 0.6:
        tags.add("renovated")
    elif 0.35 <= reno < 0.6:
        tags.add("partially updated")

    if light >= 0.6:
        tags.add("good natural light")

    if curb >= 0.6:
        tags.add("strong curb appeal")

    return sorted(tags)


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

    return notes


# ----------------------------
# Public API
# ----------------------------


def synthesize_listing_insights(listing: ListingNormalized, photos: PhotoInsights) -> ListingInsights:
    """
    Deterministically construct ListingInsights:
      • address: always non-empty (resolver fallback)
      • amenities: merged from listing + photos
      • condition_tags: derived from photo quality flags (thresholded)
      • defects: (placeholder for future wired signals; empty for now)
      • notes: compact, human-friendly rollup
    """
    address = _resolve_address(listing)
    amenities = _amenities_from(listing, photos)
    condition = _condition_tags_from(photos)
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

    return ListingInsights(
        address=address,
        amenities=amenities,
        condition_tags=condition,
        defects=defects,
        notes=notes,
    )
