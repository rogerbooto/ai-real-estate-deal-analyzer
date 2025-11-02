# src/core/ingest/__init__.py

from pathlib import Path
from typing import Any

from src.schemas.models import IngestResult

from .listing_ingest import ingest_listing


def _discover_listing_file(deal_dir: Path) -> Path | None:
    for pat in ("listing.txt", "listing.md", "listing.html"):
        p = deal_dir / pat
        if p.exists():
            return p
    for ext in ("*.txt", "*.md", "*.html"):
        for p in deal_dir.glob(ext):
            if p.is_file():
                return p
    return None


def run_ingest(
    *,
    url: str | None = None,
    file: Path | None = None,
    photos_dir: Path | None = None,
    **kwargs: Any,
) -> IngestResult:
    """
    Wrapper around ingest_listing with bundle support.
    Always returns an IngestResult or raises if input is invalid.
    """

    # Allow "file" to be a directory bundle (auto-discover listing + photos/)
    if file is not None and isinstance(file, Path) and file.is_dir():
        deal_dir = file
        file = _discover_listing_file(deal_dir)
        pd = deal_dir / "photos"
        photos_dir = photos_dir or (pd if pd.exists() else None)

    # Validate inputs to ensure we never return None
    if url is None and file is None:
        raise ValueError("run_ingest: must provide either 'url' or 'file' (path or bundle directory).")

    if isinstance(file, Path) and not file.exists():
        raise FileNotFoundError(f"Listing file not found: {file}")

    # Perform ingest
    result = ingest_listing(url=url, file=file, photos_dir=photos_dir, **kwargs)

    # Safety net: ensure a valid IngestResult
    if not isinstance(result, IngestResult):
        raise RuntimeError(f"ingest_listing returned unexpected type: {type(result)}")

    return result
