# src/agents/listing_ingest_agent.py
from __future__ import annotations

from pathlib import Path

from src.core.ingest.listing_ingest import run_listing_ingest_tool
from src.schemas.models import FetchPolicy, IngestResult, ListingInsights, ListingNormalized


def _listing_to_insights_address_first(listing: ListingNormalized) -> ListingInsights:
    return ListingInsights(
        address=listing.address or listing.title,
        amenities=[],
        condition_tags=[],
        defects=[],
        notes=[],
    )


class ListingIngestAgent:
    """Network-aware ingestion (URL or file) → normalized contracts via the canonical ingest tool."""

    def run(
        self,
        *,
        url: str | None = None,
        file: Path | None = None,
        photos_dir: Path | None = None,
        policy: FetchPolicy | None = None,
        use_ai_cv: bool = False,
    ) -> IngestResult:
        if not (url or file):
            raise ValueError("Provide either url or file.")

        pol = policy or FetchPolicy()

        listing, photo_insights = run_listing_ingest_tool(
            url=url,
            file=str(file) if file else None,
            photos_dir=str(photos_dir) if photos_dir else None,
            fetch_policy=pol,
            use_ai=use_ai_cv,
        )

        insights = _listing_to_insights_address_first(listing)

        return IngestResult(listing=listing, photos=photo_insights, insights=insights)
