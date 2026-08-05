# tests/integration/test_main_asset_config_pairing.py
"""``main.py`` must never underwrite one property's asset against another's financials.

``--listing``/``--photos`` name the property; ``--config`` carries the money. Supplying an
asset alone used to fall through to the committed 36 Kelly bundle, so the report printed the
caller's address above 36 Kelly's $399,900 purchase price, rent roll, and financing — with no
line admitting it (Mission 2, finding F2). These tests pin the fix and, just as importantly,
the two behaviours it must not break: the zero-argument demo, and a legitimate
``--listing`` **with** ``--config`` pairing.

The orchestrator is replaced by a spy so the assertions are about *which financials reached
the pipeline*, not about report text, and so the suite stays fast.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import main as main_module

BUNDLE = Path("data/sample_listings/36_kelly_moncton")
#: The demo deal's purchase price — the number a mismatched run would silently borrow.
BUNDLE_PURCHASE_PRICE = 399_900.0


class _OrchestratorSpy:
    """Stand-in for ``run_orchestration`` that records the inputs it was handed."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(
            insights=None,
            forecast=None,
            thesis=SimpleNamespace(verdict="DECLINE"),
            media_insights=None,
            media_report=None,
        )


@pytest.fixture()
def spy(monkeypatch: pytest.MonkeyPatch) -> _OrchestratorSpy:
    """Intercept the pipeline and the report write; return the spy for assertions."""
    s = _OrchestratorSpy()
    monkeypatch.setattr(main_module.deterministic_orchestrator, "run_orchestration", s)
    monkeypatch.setattr(main_module, "write_report", lambda *a, **k: None)
    return s


@pytest.fixture()
def other_property(tmp_path: Path) -> Path:
    """A listing for a *different* building than the demo bundle."""
    listing = tmp_path / "other_listing.txt"
    listing.write_text(
        "12 Elsewhere Street, Halifax, NS B3H 1A1\nAsking $1,250,000\n6-unit apartment building\n",
        encoding="utf-8",
    )
    return listing


def _run_expecting_refusal(spy: _OrchestratorSpy) -> SystemExit:
    """
    Run ``main()`` and assert it refused *before* any financials reached the pipeline.

    Reports the silent pairing explicitly when it happens, because "DID NOT RAISE" would hide
    the actual defect: which numbers the asset was underwritten against.
    """
    caught: SystemExit | None = None
    try:
        main_module.main()
    except SystemExit as exc:
        caught = exc

    if spy.calls:
        call = spy.calls[0]
        raise AssertionError(
            "asset flag without --config silently underwrote "
            f"{call['listing_txt_path']} against the demo deal's financials "
            f"(purchase_price={call['inputs'].financing.purchase_price:,.0f} from {main_module.DEFAULT_INPUTS})"
        )

    assert caught is not None, "expected a loud SystemExit; main() completed instead"
    return caught


def test_listing_without_config_refuses_to_borrow_the_demo_financials(
    monkeypatch: pytest.MonkeyPatch, spy: _OrchestratorSpy, other_property: Path
) -> None:
    """``--listing`` alone must loud-fail, not pair the asset with 36 Kelly's numbers."""
    monkeypatch.setattr("sys.argv", ["main.py", "--listing", str(other_property)])

    message = str(_run_expecting_refusal(spy))

    assert "--listing" in message
    assert "--config" in message


def test_photos_without_config_refuses_too(monkeypatch: pytest.MonkeyPatch, spy: _OrchestratorSpy, tmp_path: Path) -> None:
    """The same rule applies to ``--photos``; the message names the flag actually supplied."""
    photos = tmp_path / "photos"
    photos.mkdir()
    monkeypatch.setattr("sys.argv", ["main.py", "--photos", str(photos)])

    message = str(_run_expecting_refusal(spy))

    assert "--photos" in message
    assert "--config" in message
    assert "--listing" not in message


def test_both_asset_flags_without_config_are_both_named(
    monkeypatch: pytest.MonkeyPatch, spy: _OrchestratorSpy, other_property: Path
) -> None:
    """Supplying the full asset pair still needs financials for the same property."""
    monkeypatch.setattr("sys.argv", ["main.py", "--listing", str(other_property), "--photos", str(BUNDLE / "photos")])

    assert "--listing and --photos" in str(_run_expecting_refusal(spy))


def test_zero_argument_demo_still_underwrites_the_bundle(monkeypatch: pytest.MonkeyPatch, spy: _OrchestratorSpy) -> None:
    """No flags → the coherent 36 Kelly bundle (listing, photos, and financials together)."""
    monkeypatch.setattr("sys.argv", ["main.py"])

    main_module.main()

    assert len(spy.calls) == 1
    call = spy.calls[0]
    assert call["inputs"].financing.purchase_price == BUNDLE_PURCHASE_PRICE
    assert Path(call["listing_txt_path"]) == BUNDLE / "listing.txt"
    assert Path(call["photos_folder"]) == BUNDLE / "photos"


def test_listing_with_explicit_config_is_a_legitimate_pairing(
    monkeypatch: pytest.MonkeyPatch, spy: _OrchestratorSpy, other_property: Path
) -> None:
    """``--listing`` **with** ``--config`` is the supported way to analyse another property."""
    monkeypatch.setattr(
        "sys.argv",
        ["main.py", "--config", str(BUNDLE / "inputs.json"), "--listing", str(other_property)],
    )

    main_module.main()

    assert len(spy.calls) == 1
    call = spy.calls[0]
    assert Path(call["listing_txt_path"]) == other_property
    # The caller asked for these financials explicitly, so they are used as given.
    assert call["inputs"].financing.purchase_price == BUNDLE_PURCHASE_PRICE


def test_resolver_returns_the_bundle_when_nothing_is_supplied() -> None:
    """Unit-level pin on the default the zero-argument demo depends on."""
    assert main_module.resolve_config_path(None, None, None) == str(main_module.DEFAULT_INPUTS)


def test_resolver_passes_an_explicit_config_through() -> None:
    assert main_module.resolve_config_path("my/config.json", "l.txt", "p/") == "my/config.json"


def test_resolver_falls_back_to_none_without_a_bundle(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """No config and no committed bundle → None, so main() uses build_sample_inputs()."""
    monkeypatch.setattr(main_module, "DEFAULT_INPUTS", tmp_path / "absent" / "inputs.json")
    assert main_module.resolve_config_path(None, None, None) is None
