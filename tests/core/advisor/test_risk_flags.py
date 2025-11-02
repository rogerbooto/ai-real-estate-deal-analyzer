# tests/core/advisor/test_risk_flags.py
from src.core.advisor.risk import compute_risk_flags
from src.schemas.models import ListingNormalized
from tests.utils import make_finance_summary, make_photo_insights


def test_leasehold_and_pad_fee_flags(tmp_path):
    listing = ListingNormalized(
        title="Test",
        notes="Leasehold mini-home. Pad fee: $395 monthly.",
        year_built=2015,
        heating="baseboard",
        cooling="ac",
        parking=None,
    )
    # Pass parking at creation time (PhotoInsights is frozen)
    photos = make_photo_insights(
        [tmp_path / "a.jpg"],
        parking={"parking_type": "none", "parking_spots": None, "ev_charging": False},
    )
    finance = make_finance_summary(area_safety_index=0.60)

    flags = compute_risk_flags(listing=listing, photos=photos, finance=finance, raw_text=listing.notes)
    assert "tenure:leasehold" in flags
    assert "structure:mini_home" in flags
    assert any(f.startswith("fee:pad_fee_") for f in flags)
    assert "parking:none" in flags


def test_age_flag_and_baseboard_only(tmp_path):
    listing = ListingNormalized(
        title="Old House",
        notes="Charming older home",
        year_built=1975,
        heating="baseboard",
        cooling=None,
        parking=False,
    )
    photos = make_photo_insights([tmp_path / "b.jpg"])
    finance = make_finance_summary(area_safety_index=0.60)
    flags = compute_risk_flags(listing=listing, photos=photos, finance=finance)
    assert "age:older_stock" in flags
    assert "hvac:baseboard_only" in flags
