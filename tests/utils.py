# tests/utils.py
"""
Single source of truth for test data, factories, and canonical payloads.
Update values here to cascade across the test suite.
"""

from __future__ import annotations

import os
import runpy
import subprocess
import sys
from collections.abc import Iterable
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

# Project models
from src.core.finance.adapters import FinanceSummary
from src.schemas.models import (
    # Financial model types
    FinancialForecast,
    FinancialInputs,
    FinancingTerms,
    HtmlSnapshot,
    HypothesisSet,
    IncomeModel,
    InvestmentThesis,
    ListingInsights,
    MarketAssumptions,
    MarketHypothesis,
    MarketSnapshot,
    OperatingExpenses,
    PhotoInsights,
    PurchaseMetrics,
    RefinancePlan,
    UnitIncome,
    YearBreakdown,
)

# -----------------------------
# Global defaults (edit once)
# -----------------------------

DEFAULT_REGION = "TestRegion"
DEFAULT_VACANCY = 0.05
DEFAULT_CAP_RATE = 0.065
DEFAULT_RENT_GROWTH = 0.03
DEFAULT_EXPENSE_GROWTH = 0.02
DEFAULT_MARKET_RATE = 0.045

# Refi defaults
DEFAULT_REFI = RefinancePlan(
    do_refi=True,
    year_to_refi=5,
    refi_ltv=0.75,
    exit_cap_rate=None,
    market_cap_rate=None,
)

# Market policy defaults
DEFAULT_MARKET_ASSUMPTIONS = MarketAssumptions(
    cap_rate_purchase=None, cap_rate_floor=0.05, cap_rate_spread_target=0.015, cap_rate_drift=0.03
)

# Listing insights defaults
DEFAULT_LISTING_INSIGHTS = ListingInsights(address=None, amenities=[], condition_tags=[], defects=[], notes=[])

DEFAULT_THESES: list[InvestmentThesis] = [
    InvestmentThesis(
        title="Cashflow First",
        body="Prioritize DSCR >= 1.2",
        verdict="PASS",
        rationale=[
            "Ensures the property comfortably covers debt service",
            "Builds resilience against minor shocks",
        ],
    ),
    InvestmentThesis(
        title="Value-Add",
        body="Budget light renovations for rent lift",
        verdict="CONSIDER",
        rationale=[
            "Upside depends on local comp premiums",
            "Execution risk on timeline and scope",
        ],
    ),
]


def png_bytes(w: int = 2, h: int = 3) -> bytes:
    """
    Generate a PNG that doesn't compress to <1 KiB by using a gradient
    and disabling PNG compression/optimization.
    """
    img = Image.new("RGB", (w, h))
    # Fill with a simple gradient so pixels vary a lot (hard to compress)
    pixels = [(x % 256, y % 256, (x * y) % 256) for y in range(h) for x in range(w)]
    img.putdata(pixels)
    buf = BytesIO()
    # Disable compression/optimization to ensure the file exceeds 1 KiB
    img.save(buf, format="PNG", optimize=False, compress_level=0)
    return buf.getvalue()


def make_gradient_img(path: Path, size: tuple[int, int], delta: int = 0) -> None:
    """
    Create a simple RGB gradient image so the pHash has meaningful structure.
    `delta` lets us make a slightly different image without changing dimensions.
    """
    w, h = size
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    # Gradient with a small delta to perturb content deterministically
    for y in range(h):
        for x in range(w):
            arr[y, x, 0] = (x + delta) % 256
            arr[y, x, 1] = (y) % 256
            arr[y, x, 2] = ((x * y) + delta) % 256
    Image.fromarray(arr, mode="RGB").save(path, format="PNG")


# -----------------------------
# Snapshot/Hypotheses factories
# -----------------------------


def make_snapshot(
    region: str = DEFAULT_REGION,
    vacancy_rate: float = DEFAULT_VACANCY,
    cap_rate: float = DEFAULT_CAP_RATE,
    rent_growth: float = DEFAULT_RENT_GROWTH,
    expense_growth: float = DEFAULT_EXPENSE_GROWTH,
    interest_rate: float = DEFAULT_MARKET_RATE,
    notes: str | None = None,
) -> MarketSnapshot:
    return MarketSnapshot(
        region=region,
        vacancy_rate=vacancy_rate,
        cap_rate=cap_rate,
        rent_growth=rent_growth,
        expense_growth=expense_growth,
        interest_rate=interest_rate,
        notes=notes,
    )


def make_hypothesis(
    rent_delta: float = 0.01,
    expense_growth_delta: float = 0.005,
    interest_rate_delta: float = 0.0,
    cap_rate_delta: float = 0.0025,
    vacancy_delta: float = 0.0,
    str_viability: bool = True,
    prior: float = 0.25,
    rationale: str = "Factory default hypothesis",
) -> MarketHypothesis:
    return MarketHypothesis(
        rent_delta=rent_delta,
        expense_growth_delta=expense_growth_delta,
        interest_rate_delta=interest_rate_delta,
        cap_rate_delta=cap_rate_delta,
        vacancy_delta=vacancy_delta,
        str_viability=str_viability,
        prior=prior,
        rationale=rationale,
    )


def make_hypothesis_set(
    region: str = DEFAULT_REGION,
    seed: int = 42,
    n: int = 3,
    base_rationale: str = "Hypothesis",
) -> HypothesisSet:
    items: tuple[MarketHypothesis, ...] = tuple(make_hypothesis(rationale=f"{base_rationale} {i + 1}") for i in range(n))
    return HypothesisSet(snapshot_region=region, seed=seed, items=items)


# -----------------------------
# Financial factories
# -----------------------------


def make_financing_terms(
    purchase_price: float = 500_000.0,
    closing_costs: float = 10_000.0,
    down_payment_rate: float = 0.20,
    interest_rate: float = 0.055,
    amort_years: int = 30,
    io_years: int = 0,
    mortgage_insurance_rate: float = 0.0,
) -> FinancingTerms:
    return FinancingTerms(
        purchase_price=purchase_price,
        closing_costs=closing_costs,
        down_payment_rate=down_payment_rate,
        interest_rate=interest_rate,
        amort_years=amort_years,
        io_years=io_years,
        mortgage_insurance_rate=mortgage_insurance_rate,
    )


def make_opex(
    insurance: float = 2000.0,
    taxes: float = 5000.0,
    utilities: float = 3000.0,
    water_sewer: float = 1500.0,
    property_management: float = 3600.0,
    repairs_maintenance: float = 1800.0,
    trash: float = 900.0,
    landscaping: float = 600.0,
    snow_removal: float = 400.0,
    hoa_fees: float = 0.0,
    reserves: float = 1000.0,
    other: float = 500.0,
    expense_growth: float = 0.02,
) -> OperatingExpenses:
    return OperatingExpenses(
        insurance=insurance,
        taxes=taxes,
        utilities=utilities,
        water_sewer=water_sewer,
        property_management=property_management,
        repairs_maintenance=repairs_maintenance,
        trash=trash,
        landscaping=landscaping,
        snow_removal=snow_removal,
        hoa_fees=hoa_fees,
        reserves=reserves,
        other=other,
        expense_growth=expense_growth,
    )


def make_income_model(
    num_units: int = 4,
    rent_month: float = 1200.0,
    other_income_month: float = 100.0,
    occupancy: float = 0.95,
    bad_debt_factor: float = 0.97,
    rent_growth: float = 0.03,
) -> IncomeModel:
    units = [UnitIncome(rent_month=rent_month, other_income_month=other_income_month) for _ in range(num_units)]
    return IncomeModel(
        units=units,
        occupancy=occupancy,
        bad_debt_factor=bad_debt_factor,
        rent_growth=rent_growth,
    )


def make_refi_plan(**overrides: Any) -> RefinancePlan:
    base = DEFAULT_REFI
    return RefinancePlan(
        do_refi=overrides.get("do_refi", base.do_refi),
        year_to_refi=overrides.get("year_to_refi", base.year_to_refi),
        refi_ltv=overrides.get("refi_ltv", base.refi_ltv),
        exit_cap_rate=overrides.get("exit_cap_rate", base.exit_cap_rate),
        market_cap_rate=overrides.get("market_cap_rate", base.market_cap_rate),
    )


def make_market_assumptions(**overrides: Any) -> MarketAssumptions:
    base = DEFAULT_MARKET_ASSUMPTIONS
    return MarketAssumptions(
        cap_rate_purchase=overrides.get("cap_rate_purchase", base.cap_rate_purchase),
        cap_rate_floor=overrides.get("cap_rate_floor", base.cap_rate_floor),
        cap_rate_spread_target=overrides.get("cap_rate_spread_target", base.cap_rate_spread_target),
        cap_rate_drift=overrides.get("cap_rate_drift", base.cap_rate_drift),
    )


def make_listing_insights(**overrides: Any) -> ListingInsights:
    return ListingInsights(
        address=overrides.get("address"),
        amenities=overrides.get("amenities", []),
        condition_tags=overrides.get("condition_tags", []),
        defects=overrides.get("defects", []),
        notes=overrides.get("notes", []),
    )


def make_financial_inputs(
    do_refi: bool = False,
    num_units: int = 4,
) -> FinancialInputs:
    return FinancialInputs(
        financing=make_financing_terms(),
        opex=make_opex(),
        income=make_income_model(num_units=num_units),
        refi=make_refi_plan(do_refi=do_refi),
        market=make_market_assumptions(),
    )


# -----------------------------
# Report helpers
# -----------------------------


def default_theses() -> list[InvestmentThesis]:
    return list(DEFAULT_THESES)


def make_document(
    tmp_dir: Path,
    *,
    html: str | None = None,
    text: str | None = None,
    filename: str | None = None,
) -> Path:
    """
    Create a simple document in tmp_dir and return its Path.

    - If `html` is provided, writes an .html file (unless a custom filename is given).
    - Else if `text` is provided, writes a .txt file (unless a custom filename is given).
    - Exactly one of `html` or `text` should be provided.
    """
    if (html is None) and (text is None):
        raise ValueError("Provide exactly one of `html` or `text`.")

    if html is not None:
        name = filename or "doc.html"
        content = html
    else:
        name = filename or "doc.txt"
        content = text or ""

    tmp_dir.mkdir(parents=True, exist_ok=True)
    path = tmp_dir / name
    path.write_text(content, encoding="utf-8")
    return path


# -----------------------------
# HTML snapshot helpers
# -----------------------------

DEFAULT_LISTING_HTML = """<!doctype html>
<html>
  <head><title>Test Listing</title></head>
  <body><img src="/img.jpg" alt="front"></body>
</html>
"""


def make_html_snapshot(
    tmp_dir: Path,
    *,
    html: str = DEFAULT_LISTING_HTML,
    url: str = "https://example.com/listing/123",
    filename: str = "index.raw.html",
) -> HtmlSnapshot:
    """
    Write `html` to tmp_dir/filename and return a HtmlSnapshot pointing to it.
    Useful for media finders and DOM parsers.
    """
    tmp_dir.mkdir(parents=True, exist_ok=True)
    html_path = tmp_dir / filename
    html_bytes = html.encode("utf-8")
    html_path.write_bytes(html_bytes)

    return HtmlSnapshot(
        url=url,
        fetched_at=datetime.now(timezone.utc),
        status_code=200,
        html_path=html_path,
        tree_path=None,
        bytes_size=len(html_bytes),
        sha256="deadbeef",  # tests don't rely on this; fine to keep static
    )


def sha256_of(path: Path) -> str:
    """
    Compute a deterministic SHA-256 for a file path.
    If file is missing, hash a sentinel string so the key is still stable.
    """
    if path.exists():
        data = path.read_bytes() + str(path.name).encode("utf-8")  # add filename for uniqueness
    else:
        data = b"missing-" + str(path.name).encode("utf-8")
    return sha256(data).hexdigest()


def make_photo_insights(
    image_paths: Iterable[Path],
    *,
    room_counts: dict[str, int] | None = None,
    amenities: dict[str, bool] | None = None,
    defects: dict[str, int] | None = None,
    quality_flags: dict[str, float] | None = None,
    parking: dict[str, Any] | None = None,
    labels_by_sha: dict[str, list[Any]] | None = None,
    detections_by_sha: dict[str, list[dict[str, Any]]] | None = None,
    provider: str = "cv_v2",
    version: str = "deterministic",
    ontology_version: str = "amenities_defects_v1",
    provenance: dict[str, Any] | None = None,
) -> PhotoInsights:
    """
    Build a minimal-but-realistic PhotoInsights instance from a list of image paths.
    Coerces:
      - labels_by_sha values to List[str]
      - detections_by_sha values to List[{'name','category','confidence'}]
    """
    # Build sha index
    shas: list[str] = [sha256_of(Path(p)) for p in image_paths]
    image_index: dict[str, str] = {s: str(Path(p)) for s, p in zip(shas, image_paths, strict=False)}

    # Defaults
    parking = parking or {"parking_type": "street", "parking_spots": 1, "ev_charging": False}
    provenance = provenance or {"selected_provider": "local", "use_ai": False, "cache_root": ".cache/cv"}

    # ---- Coerce labels to List[str]
    labels_by_sha = labels_by_sha or {}
    labels_norm: dict[str, list[str]] = {}
    for k, vals in labels_by_sha.items():
        out: list[str] = []
        for v in vals or []:
            if isinstance(v, str):
                out.append(v)
            elif isinstance(v, dict):
                # accept {'label': 'kitchen', 'score': 0.98} -> 'kitchen'
                if "label" in v and isinstance(v["label"], str):
                    out.append(v["label"])
            else:
                # ignore unknown types
                pass
        labels_norm[k] = out

    # ---- Coerce detections to required keys
    detections_by_sha = detections_by_sha or {}
    det_norm: dict[str, list[dict[str, Any]]] = {}
    for k, dets in detections_by_sha.items():
        out: list[dict[str, Any]] = []
        for d in dets or []:
            if {"name", "category", "confidence"}.issubset(d.keys()):
                # ensure confidence is float
                out.append({"name": d["name"], "category": d["category"], "confidence": float(d["confidence"])})
            else:
                # accept {'label': 'toilet', 'score': 0.88} -> map to amenity by default
                label = d.get("label")
                score = d.get("score")
                if isinstance(label, str) and isinstance(score, (int | float)):
                    out.append({"name": label, "category": "amenity", "confidence": float(score)})
        det_norm[k] = out

    images_total = len(image_index)
    detections_total = sum(len(v) for v in det_norm.values())

    payload = dict(
        room_counts=room_counts or {},
        amenities=amenities or {},
        defect_counts=defects or {},
        quality_flags=quality_flags or {},
        parking=parking,
        image_index=image_index,
        image_labels=labels_norm,
        image_detections=det_norm,
        images_total=images_total,
        detections_total=detections_total,
        provider=provider,
        version=version,
        ontology_version=ontology_version,
        provenance=provenance,
    )
    return PhotoInsights(**payload)


def make_photo_insights_from_photo_dir(
    photo_dir: Path,
    *,
    set_dishwasher: bool = True,
    renovated_score: float | None = 0.62,
) -> PhotoInsights:
    """
    Convenience wrapper tailored to the `photo_dir` fixture:
      - kitchen_updated_dishwasher.png
      - bathroom_1.png
      - kitchen_2.png
    """
    img1 = photo_dir / "kitchen_updated_dishwasher.png"
    img2 = photo_dir / "bathroom_1.png"
    img3 = photo_dir / "kitchen_2.png"

    sha1 = sha256_of(img1)
    sha2 = sha256_of(img2)
    sha3 = sha256_of(img3)

    labels = {
        sha1: ["kitchen"],
        sha2: ["bathroom"],
        sha3: ["kitchen"],
    }

    detections = {
        sha1: ([{"name": "dishwasher", "category": "amenity", "confidence": 0.90}] if set_dishwasher else []),
        sha2: [{"name": "toilet", "category": "amenity", "confidence": 0.88}],
    }

    amenities = {"dishwasher": bool(set_dishwasher), "in_unit_laundry": False}
    quality = {}
    if renovated_score is not None:
        quality["renovated_score"] = float(renovated_score)

    return make_photo_insights(
        [img1, img2, img3],
        room_counts={"kitchen": 2, "bath": 1},
        amenities=amenities,
        defects={"mold_suspected": 1},
        quality_flags=quality,
        labels_by_sha=labels,
        detections_by_sha=detections,
        provider="cv_v2",
        version="deterministic",
    )


def repo_root() -> Path:
    # tests/ -> <root>
    return Path(__file__).resolve().parents[1]


def run_root_cli(script_name: str, args: list[str]) -> subprocess.CompletedProcess:
    """
    Run a Python CLI that lives at the repository root (same folder as src/ and tests/).
    Ensures PYTHONPATH includes the repo root so 'src.*' imports work.

    Example:
        res = run_root_cli("report_cli.py", ["--forecast", "...", "--out", "..."])
    """
    root = repo_root()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root)
    script_path = root / script_name
    cmd = [sys.executable, str(script_path), *args]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(root), env=env)


# ---------- Minimal forecast factory ----------
def make_minimal_forecast() -> FinancialForecast:
    purchase = PurchaseMetrics(
        cap_rate=0.0744, coc=0.0521, dscr=1.31, annual_debt_service=24000.0, acquisition_cash=110000.0, spread_vs_rate=0.0194
    )
    years = [
        YearBreakdown(
            year=1,
            gsi=86400.0,
            goi=79200.0,
            insurance=2000.0,
            taxes=5000.0,
            utilities=3000.0,
            water_sewer=1500.0,
            property_management=3600.0,
            repairs_maintenance=1800.0,
            trash=900.0,
            landscaping=600.0,
            snow_removal=400.0,
            hoa_fees=0.0,
            reserves=1000.0,
            other_expenses=500.0,
            total_opex=20300.0,
            noi=58900.0,
            debt_service=24000.0,
            principal_paid=9000.0,
            interest_paid=15000.0,
            cash_flow=34900.0,
            dscr=2.45,
            ending_balance=391000.0,
            cap_rate_applied=0.075,
            est_value=785333.33,
            ltv_pct=49.8,
            available_equity=0.0,
            notes=[],
        ),
    ]
    return FinancialForecast(purchase=purchase, years=years, refi=None, irr_10yr=0.0661, equity_multiple_10yr=1.47, warnings=[])


@contextmanager
def _patched_argv_and_syspath(argv: list[str], add_path: str):
    old_argv = sys.argv[:]
    old_path0 = list(sys.path)
    try:
        sys.argv = argv
        if add_path not in sys.path:
            sys.path.insert(0, add_path)
        yield
    finally:
        sys.argv = old_argv
        sys.path = old_path0


def run_root_script(script_name: str, args: list[str]) -> tuple[int, str]:
    """
    Execute a root-level CLI script in-process using runpy.
    Returns (returncode, stderr_text). Non-exception paths return (0, "").
    """
    root = Path(__file__).resolve().parents[1]  # repo root
    script_path = root / script_name
    if not script_path.exists():
        return (1, f"Script not found: {script_path}")

    with _patched_argv_and_syspath([script_path.name, *args], str(root)):
        try:
            runpy.run_path(str(script_path), run_name="__main__")
            return (0, "")
        except SystemExit as ex:  # allow sys.exit(...) in scripts
            code = getattr(ex, "code", 0) or 0
            return (int(code), "")
        except Exception as ex:  # capture unexpected exceptions as non-zero
            return (1, f"{type(ex).__name__}: {ex}")


def make_finance_summary(
    *,
    irr: float = 0.10,
    cashflow_monthly: float = 300.0,
    price_per_sqft: float = 200.0,
    market_ppsf: float = 210.0,
    purchase_price: float = 300000.0,
    area_safety_index: float | None = 0.60,
) -> FinanceSummary:
    """
    Minimal FinanceSummary factory for advisor/risk tests.
    """
    return FinanceSummary(
        irr=irr,
        cashflow_monthly=cashflow_monthly,
        price_per_sqft=price_per_sqft,
        market_ppsf=market_ppsf,
        purchase_price=purchase_price,
        area_safety_index=area_safety_index,
    )


def make_finance_summary_safe() -> FinanceSummary:
    return make_finance_summary(area_safety_index=0.8)


def make_finance_summary_risky() -> FinanceSummary:
    return make_finance_summary(area_safety_index=0.4)
