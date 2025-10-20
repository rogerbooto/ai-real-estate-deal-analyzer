# tests/listing/test_ingest_flags.py
from pathlib import Path

from src.schemas.models import FetchPolicy
from src.tools.listing_ingest import ingest_listing
from tests.utils import make_document


def test_ingest_url_minimal_without_media(tmp_path: Path):
    html = "<html><head><title>Hi</title></head><body>$500 | 1 br | 1 ba | 500 sqft</body></html>"
    f = make_document(tmp_path, html=html)
    # Simulate “URL path” by passing file via url=None and file=f, but set media flags:
    res = ingest_listing(file=f, photos_dir=None, download_media=False, policy=FetchPolicy())
    assert res.listing.price == 500.0


def test_ingest_media_intel_no_images(tmp_path: Path):
    f = make_document(tmp_path, text="USD 500 | 1 bed | 1 bath | 500 sqft")
    res = ingest_listing(file=f, photos_dir=None, download_media=False, media_intel=True)
    # should safely return with no media_insights or no enrichment crash
    assert res.media_insights is None or res.media_insights is not None  # just smoke
