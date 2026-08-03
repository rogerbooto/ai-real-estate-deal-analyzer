# tests/integration/test_ingest_cli.py
"""
Mission 2 / Wave 2 — CLI honesty fixes in ``src/cli/ingest_cli.py``.

Covers:
  F10 - computed insights/photos are printed, not silently discarded.
  F11 - --file mode without --url prints a clear note that media-discovery flags are inert
        (they need an HTML source `collect_media` can scan; `collect_local_assets` is not
        wired into `ingest_listing`), instead of silently returning an empty media bundle.
  F15 - --ai has accurate help text (wired, but stub providers -- no overclaiming).
  F16 - --pretty / --save-screenshot are independent, documented flags.
  F18 - an invalid --media-kinds value is a clean argparse usage error, not a traceback.
  F20 - the console dump reads the real model field `address_structure`, not the old
        `address_struct` typo, so the structured-address print actually fires.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import src.cli.ingest_cli as ingest_cli

SAMPLE_LISTING = Path("data/sample_listings/36_kelly_moncton/listing.txt")


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    rc = ingest_cli.main(argv)
    captured = capsys.readouterr()
    return rc, captured.out, captured.err


# ---------------------------------------------------------------------------
# F10 - insights/photos are printed
# ---------------------------------------------------------------------------


def test_insights_and_photos_are_printed(capsys: pytest.CaptureFixture[str]) -> None:
    rc, out, _err = _run(["--file", str(SAMPLE_LISTING), "--pretty", "0"], capsys)
    assert rc == 0
    assert "listing insights:" in out
    assert "photo insights:" in out
    # Real computed values reach the console, not just the section header.
    assert "36 Kelly" in out
    assert "provider=" in out and "images_total=" in out


def test_pretty_mode_also_dumps_full_insights_and_photos(capsys: pytest.CaptureFixture[str]) -> None:
    rc, out, _err = _run(["--file", str(SAMPLE_LISTING), "--pretty", "1"], capsys)
    assert rc == 0
    assert "insights (full):" in out
    assert "photos (full):" in out


# ---------------------------------------------------------------------------
# F11 - media flags in --file mode
# ---------------------------------------------------------------------------


def test_file_mode_without_url_warns_media_flags_are_inert(capsys: pytest.CaptureFixture[str]) -> None:
    rc, out, err = _run(["--file", str(SAMPLE_LISTING)], capsys)
    assert rc == 0
    assert "require an HTML source (--url)" in err
    assert "media: 0 assets" in out


def test_file_mode_with_download_media_off_suppresses_the_note(capsys: pytest.CaptureFixture[str]) -> None:
    rc, _out, err = _run(["--file", str(SAMPLE_LISTING), "--download-media", "0"], capsys)
    assert rc == 0
    assert "require an HTML source" not in err


# ---------------------------------------------------------------------------
# F15 - --ai help text
# ---------------------------------------------------------------------------


def test_ai_flag_help_is_present_and_honest() -> None:
    help_text = ingest_cli._build_parser().format_help()
    assert "--ai AI" in help_text
    # It must not claim AI does nothing -- it IS wired through to build_photo_insights.
    assert "wired" in help_text
    # It must not overclaim real model inference either.
    assert "deterministic stub" in help_text


# ---------------------------------------------------------------------------
# F16 - --pretty / --save-screenshot independence
# ---------------------------------------------------------------------------


def test_pretty_and_save_screenshot_are_documented_and_independent() -> None:
    help_text = ingest_cli._build_parser().format_help()
    assert "--save-screenshot" in help_text
    assert "--pretty" in help_text
    # Each flag's help explains what it does, not just an undocumented dual purpose.
    assert "console" in help_text
    assert "screenshot" in help_text.lower()


def test_pretty_off_does_not_suppress_screenshot_flag_value(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """--pretty 0 must not silently disable --save-screenshot (they used to be the same knob)."""
    captured_policy = {}
    real_ingest_listing = ingest_cli.ingest_listing

    def _spy(*, policy, **kwargs):  # type: ignore[no-untyped-def]
        captured_policy["save_screenshot"] = policy.save_screenshot
        return real_ingest_listing(policy=policy, **kwargs)

    monkeypatch.setattr(ingest_cli, "ingest_listing", _spy)
    rc, _out, _err = _run(["--file", str(SAMPLE_LISTING), "--pretty", "0", "--save-screenshot", "1"], capsys)
    assert rc == 0
    assert captured_policy["save_screenshot"] is True


# ---------------------------------------------------------------------------
# F18 - invalid --media-kinds is a clean usage error
# ---------------------------------------------------------------------------


def test_invalid_media_kinds_is_a_clean_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        ingest_cli.main(["--file", str(SAMPLE_LISTING), "--media-kinds", "bogus"])
    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "invalid media kind" in err
    assert "usage:" in err


# ---------------------------------------------------------------------------
# F20 - address_structure key, not address_struct
# ---------------------------------------------------------------------------


def test_pretty_dump_prints_address_structure_block(capsys: pytest.CaptureFixture[str]) -> None:
    rc, out, _err = _run(["--file", str(SAMPLE_LISTING), "--pretty", "1"], capsys)
    assert rc == 0
    assert "address_structure:" in out
    assert "Moncton" in out
