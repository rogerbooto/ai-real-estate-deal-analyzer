from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image

from src.core.cv import runner as cv_runner


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def test_tag_images_keys_are_sha(tmp_path: Path):
    p = tmp_path / "kitchen_updated_dishwasher.jpg"
    Image.new("RGB", (16, 16), color=(245, 245, 245)).save(p)
    out = cv_runner.tag_images([p])
    assert set(out.keys()) == {_sha(p)}
    assert isinstance(next(iter(out.values())), list)


def test_tag_amenities_cache_layout(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AIREDEAL_CACHE_DIR", str(tmp_path / "cache"))
    p = tmp_path / "bright.png"
    Image.new("RGB", (96, 64), color=(245, 245, 245)).save(p)
    sha = _sha(p)
    res = cv_runner.tag_amenities_and_defects([p], provider="local", use_cache=True)
    assert sha in res

    # The behaviour-version segment is deliberate, not incidental. Entries are keyed by
    # (provider, image sha256), which records what was looked at but not what the looker would
    # say today -- so without it a provider behaviour fix never reaches anyone holding a warm
    # cache. Read the constant rather than hardcoding it, so a future bump does not break this.
    provider_dir = tmp_path / "cache" / "providers" / "local"
    cache_file = provider_dir / cv_runner._CACHE_BEHAVIOUR_VERSION / f"{sha}.json"
    assert (
        cache_file.exists()
    ), f"expected a version-scoped cache entry; tree was {sorted(pth.relative_to(provider_dir) for pth in provider_dir.rglob('*'))}"

    # ...and an entry written under a PREVIOUS behaviour version must not be served.
    assert not (
        provider_dir / f"{sha}.json"
    ).exists(), "cache entry written unversioned — a stale detection would outlive the code that produced it"
