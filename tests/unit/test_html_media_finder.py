# tests/unit/test_html_media_finder.py
from __future__ import annotations

from src.core.media.html_finder import HtmlMediaFinder

HTML = """<!doctype html>
<html>
<head>
  <meta property="og:image" content="/imgs/hero.jpg">
  <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "RealEstateListing",
      "image": [
        "https://cdn.example.com/a.jpg",
        "https://cdn.example.com/b.webp"
      ]
    }
  </script>
  <script>
    var x = {
      property: {
        hasphoto: 'yes',
        photos: '39',
        city: 'Moncton'
      }
    };
  </script>
  <style>
    .hero { background-image: url('/imgs/bg.png'); }
  </style>
</head>
<body>
  <picture>
    <source srcset="/imgs/pic-800.jpg 800w, /imgs/pic-1200.jpg 1200w">
    <img src="/imgs/fallback.jpg" alt="Front">
  </picture>
</body>
</html>
"""


def test_html_media_finder_discovers_candidates(html_snapshot_factory) -> None:
    snap = html_snapshot_factory(HTML, url="https://example.com/listing/123")
    finder = HtmlMediaFinder()
    res = finder.find(url=snap.url, snapshot=snap)

    assert res.has_media is True
    # site hint should carry across
    assert res.photo_count_hint == 39

    urls = sorted(c.url for c in res.candidates)

    # sanity: og image absolutized, json-ld, picture/srcset, img src, background
    assert "https://example.com/imgs/hero.jpg" in urls
    assert "https://cdn.example.com/a.jpg" in urls
    assert "https://cdn.example.com/b.webp" in urls
    assert "https://example.com/imgs/pic-1200.jpg" in urls
    assert "https://example.com/imgs/fallback.jpg" in urls
