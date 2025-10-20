# tests/unit/test_html_finder_basic.py

from pathlib import Path

from src.core.media.html_finder import HtmlMediaFinder


def test_find_media_basic_img_and_srcset(tmp_path: Path, html_snapshot_factory):
    html = """
    <html><body>
      <img src="/a.jpg">
      <img srcset="/b1.jpg 1x, /b2.jpg 2x">
      <a href="/doc.pdf">doc</a>
      <video src="/v.mp4"></video>
    </body></html>
    """
    snap = html_snapshot_factory(html=html, base_dir=tmp_path)

    out = HtmlMediaFinder().find(url=snap.url, snapshot=snap)
    kinds = {c.kind for c in out.candidates}
    urls = {c.url for c in out.candidates}
    assert "image" in kinds and "video" in kinds
    assert "https://example.com/a.jpg" in urls
    assert "https://example.com/v.mp4" in urls
