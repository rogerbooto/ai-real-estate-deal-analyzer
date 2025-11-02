# src/core/advisor/risk.py
from __future__ import annotations

import re
from collections.abc import Iterable

from src.core.finance.adapters import FinanceSummary
from src.schemas.models import ListingNormalized, PhotoInsights

_LEASEHOLD_TOKENS = [r"\bleasehold\b", r"\blot\s+lease\b", r"\bpad\s+fee\b", r"\blease\s+land\b"]
_MINI_HOME_TOKENS = [r"\bmini[-\s]?home\b", r"\bmanufactured\b", r"\bmobile\s+home\b", r"\bmini\b"]
_PAD_FEE_RE = re.compile(r"(?i)\b(pad|lot)\s+fee[s]?\s*[:\-]?\s*\$?\s*([0-9][0-9,\.]*)\b")


def _has_token(text: str, pats: Iterable[str]) -> bool:
    return any(re.search(p, text, flags=re.IGNORECASE) for p in pats)


def _try_pad_fee(text: str) -> float | None:
    m = _PAD_FEE_RE.search(text or "")
    if not m:
        return None
    try:
        return float(m.group(2).replace(",", ""))
    except Exception:
        return None


def compute_risk_flags(
    *, listing: ListingNormalized, photos: PhotoInsights, finance: FinanceSummary, raw_text: str | None = None
) -> list[str]:
    flags: list[str] = []
    lt = raw_text or listing.notes or ""

    # 1) Tenure / structure
    if _has_token(lt, _LEASEHOLD_TOKENS):
        flags.append("tenure:leasehold")
    if _has_token(lt, _MINI_HOME_TOKENS):
        flags.append("structure:mini_home")

    # 2) Heating/cooling simple heuristics
    if (listing.heating or "").lower() == "baseboard" and (listing.cooling or "").lower() != "heat pump":
        flags.append("hvac:baseboard_only")

    # 3) Parking (from amenities surface)
    if not listing.parking and not photos.parking or (photos.parking and photos.parking.parking_type == "none"):
        flags.append("parking:none")

    # 4) Age
    if listing.year_built and listing.year_built <= 1980:
        flags.append("age:older_stock")

    # 5) Pad/Lot fee extraction
    pad_fee = _try_pad_fee(lt)
    if pad_fee and pad_fee > 0:
        flags.append(f"fee:pad_fee_${int(pad_fee)}")

    # 6) Area safety heuristic (already in finance)
    if finance.area_safety_index is not None and finance.area_safety_index < 0.5:
        flags.append("neighborhood:low_safety_index")

    return flags
