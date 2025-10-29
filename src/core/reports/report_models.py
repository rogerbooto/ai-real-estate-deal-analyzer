# src/core/reports/report_models.py

"""
Pydantic DTOs for the Media Intelligence & Report Layer.

These classes are intentionally **versioned** and **stable**. They provide a contract
between the CV layer (PhotoInsights) and downstream consumers (agents, CLIs, renderers).
Only additive changes should be made within a version; breaking changes require a new
`ReportVersion` literal and coordinated migration.

Conventions:
- Keep business logic out of DTOs (pure data containers).
- Use explicit types for cross-language clarity.
- Prefer `Dict[str, ...]` and simple `List[...]` shapes to nested unions in the public API.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# ---- Versioning -----------------------------------------------------------------

#: Stable report version tag. Increment by adding a new Literal and bumping defaults on breaking changes.
ReportVersion = Literal["media_report_v1"]


# ---- Item-level summaries --------------------------------------------------------


class MediaItemSummary(BaseModel):
    """
    A per-image summary used for optional detailed sections (galleries, audits).

    Attributes:
        image_id: Logical identifier for the image (e.g., filename without path or a stable key).
        path: Filesystem path or URL to the image (if available).
        sha256: SHA-256 content hash used as the canonical key in CV indices.
        readable: Whether the image content was readable at report build time (exists/decodable).
        tags: Flat list of tag dicts emitted by the CV tagger (e.g., {'label': 'kitchen', 'score': 0.91}).
        detections: List of detection dicts (model-agnostic; may include bbox, label, score).
    """

    image_id: str = Field(..., description="Logical identifier for the image.")
    path: str = Field(..., description="Filesystem path or URL to the image.")
    sha256: str = Field(..., description="SHA-256 content hash.")
    readable: bool = Field(..., description="True if the image was accessible/decodable.")
    tags: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Model-agnostic tag records (label/score/etc.).",
    )
    detections: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Model-agnostic detection records (bbox/label/score/etc.).",
    )


class MediaCoverage(BaseModel):
    """
    Coverage and provenance of the CV pass used to build this report.

    Attributes:
        images_total: Total number of images discovered for the listing.
        images_readable: Number of images that were readable (file exists/decodable).
        detections_total: Total number of detection records emitted across images.
        provider: Provider name (e.g., 'cv_v2', 'vision', 'local').
        version: Provider/model version string (free-form; mirrors PhotoInsights.version).
    """

    images_total: int = Field(..., ge=0, description="Total images discovered.")
    images_readable: int = Field(..., ge=0, description="Images successfully read.")
    detections_total: int = Field(..., ge=0, description="Total detections emitted.")
    provider: str = Field(..., description="Provider identifier, e.g., 'cv_v2'.")
    version: str = Field(
        ...,
        description="Provider/model version string; free-form (not the report version).",
    )


class ParkingSummary(BaseModel):
    """
    Parking inference at the listing level.

    Attributes:
        parking_type: One of 'garage' | 'driveway' | 'street' | 'none'.
        parking_spots: Optional number of dedicated spots.
        ev_charging: Whether EV charging is present/likely.
    """

    parking_type: str = Field(
        ...,
        description="garage | driveway | street | none",
        examples=["garage", "driveway", "street", "none"],
    )
    parking_spots: int | None = Field(
        None,
        ge=0,
        description="Count of dedicated parking spots, if known.",
    )
    ev_charging: bool = Field(
        False,
        description="True if EV charging observed/inferred.",
    )


# ---- Top-level report ------------------------------------------------------------


class MediaReport(BaseModel):
    """
    Top-level media report for a listing, built from PhotoInsights and optional listing data.

    High-level signals (counts/booleans/scores) are designed to be agent-friendly and diffable.
    Detailed `images` are optional and can be omitted in compact modes.

    Attributes:
        report_version: Stable report schema version (Literal).
        listing_title: Optional listing title or headline.
        source_url: Optional canonical listing URL.
        address: Optional formatted address.

        room_counts: Map of room type → count (e.g., {'kitchen': 2, 'bath': 1}).
        amenities: Map of amenity → boolean.
        defects: Map of defect label → number of images flagged.
        quality_flags: Map of quality proxy → score in [0,1].
        parking: ParkingSummary block.

        coverage: MediaCoverage block (images/detections/provider).
        warnings: Non-fatal report warnings (e.g., 'no images found').

        ontology_version: Ontology identifier (e.g., 'amenities_defects_v1').
        provenance: Pass-through provenance from PhotoInsights (provider selection, flags, cache roots, etc.).

        images: Optional per-image summaries; renderers may hide this by default.
    """

    # Provenance
    report_version: ReportVersion = Field(
        "media_report_v1",
        description="Stable report schema version.",
    )
    listing_title: str | None = Field(None, description="Optional listing title/headline.")
    source_url: str | None = Field(None, description="Optional canonical listing URL.")
    address: str | None = Field(None, description="Optional formatted address.")

    # High-level signals
    room_counts: dict[str, int] = Field(
        ...,
        description="Room type → count (e.g., {'kitchen': 2, 'bath': 1}).",
    )
    amenities: dict[str, bool] = Field(
        ...,
        description="Amenity → boolean presence map.",
    )
    defects: dict[str, int] = Field(
        ...,
        description="Defect label → number of images flagged.",
    )
    quality_flags: dict[str, float] = Field(
        ...,
        description="Quality proxy → score in [0,1].",
    )
    parking: ParkingSummary = Field(..., description="Parking inference at listing level.")

    # Confidence & coverage
    coverage: MediaCoverage = Field(..., description="Images coverage and provider provenance.")
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal report warnings.",
    )

    # Ontology & provenance
    ontology_version: str = Field(..., description="Ontology identifier (e.g., 'amenities_defects_v1').")
    provenance: dict[str, Any] = Field(
        ...,
        description="Pass-through provenance from CV pipeline (provider flags, cache roots, etc.).",
    )

    # Optional details
    images: list[MediaItemSummary] = Field(
        default_factory=list,
        description="Optional per-image summaries (can be omitted in compact modes).",
    )
