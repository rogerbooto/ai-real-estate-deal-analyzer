# src/core/cv/ontology.py

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Literal, TypedDict

# Enum-aligned labels
from src.schemas.labels import AmenityLabel, DefectLabel, MaterialTag

Category = Literal["amenity", "defect"]


class OntologyLabel(TypedDict, total=False):
    """
    Canonical label entry in the closed-set ontology.

    Fields:
      - name: canonical key (snake_case)
      - category: "amenity" | "defect"
      - synonyms: alt spellings / surface forms (lowercased match)
      - confidence_cutoff: per-label min confidence in [0,1]
      - maps_to: optional roll-up / normalized field name
    """

    name: str
    category: Category
    synonyms: list[str]
    confidence_cutoff: float
    maps_to: str | None


@dataclass(slots=True)
class Ontology:
    version: str
    labels: dict[str, OntologyLabel]
    _syn_index: dict[str, str] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        # Build synonym index (lowercased) → canonical name
        syn: dict[str, str] = {}
        for canon, meta in self.labels.items():
            canon_l = canon.lower()
            syn[canon_l] = canon
            for s in meta.get("synonyms", []):
                s_l = s.strip().lower()
                if not s_l:
                    continue
                # First writer wins; collisions resolve to the first canonical term defined
                syn.setdefault(s_l, canon)
        self._syn_index = syn

    # ---- Public API ---------------------------------------------------------

    def all_names(self) -> set[str]:
        """Canonical label names in this closed set."""
        return set(self.labels.keys())

    def lookup(self, name_or_synonym: str) -> OntologyLabel | None:
        """
        Resolve a name or synonym (case-insensitive) to its canonical OntologyLabel.
        Returns None if not found.
        """
        if not name_or_synonym:
            return None
        key = name_or_synonym.strip().lower()
        canon = self._syn_index.get(key)
        if not canon:
            return None
        return self.labels.get(canon)

    def validate(self) -> None:
        """
        Lightweight internal validation: categories, cutoffs in [0,1], names consistent.
        Raises AssertionError on violation.
        """
        for canon, meta in self.labels.items():
            assert meta.get("name") == canon, f"name mismatch for {canon}"
            cat = meta.get("category")
            assert cat in ("amenity", "defect"), f"bad category {cat} for {canon}"
            cutoff = meta.get("confidence_cutoff")
            assert isinstance(cutoff, float), f"cutoff must be float for {canon}"
            assert 0.0 <= cutoff <= 1.0, f"cutoff out of range for {canon}"
            syns = meta.get("synonyms", [])
            assert isinstance(syns, list), f"synonyms must be list for {canon}"
            # ensure synonyms don't equal the canonical name verbatim (case-insensitive)
            for s in syns:
                assert s.strip().lower() != canon.lower(), f"duplicate synonym {s} for {canon}"


# ---- Seed Ontology: amenities + defects (v1) -------------------------------

_DEFAULT_CUTOFF = 0.60  # conservative default unless noted otherwise


def _amenity(
    name: str, synonyms: Iterable[str] | None = None, *, cutoff: float = _DEFAULT_CUTOFF, maps_to: str | None = None
) -> OntologyLabel:
    return {
        "name": name,
        "category": "amenity",
        "synonyms": list(synonyms) if synonyms else [],
        "confidence_cutoff": float(cutoff),
        "maps_to": maps_to,
    }


def _defect(
    name: str, synonyms: Iterable[str] | None = None, *, cutoff: float = _DEFAULT_CUTOFF, maps_to: str | None = None
) -> OntologyLabel:
    return {
        "name": name,
        "category": "defect",
        "synonyms": list(synonyms) if synonyms else [],
        "confidence_cutoff": float(cutoff),
        "maps_to": maps_to,
    }


def build_amenities_defects_v1() -> Ontology:
    """
    Closed-set v1 ontology for media tagging: amenities + defects.
    """
    labels: dict[str, OntologyLabel] = {}

    # ---- Amenities (enum-aligned where available) --------------------------
    labels[AmenityLabel.parking_garage.value] = _amenity(
        AmenityLabel.parking_garage.value,
        ["garage", "car garage", "two car garage", "2-car garage", "attached garage"],
        maps_to=AmenityLabel.parking_garage.value,
    )
    labels[AmenityLabel.parking_driveway.value] = _amenity(
        AmenityLabel.parking_driveway.value,
        ["driveway", "private driveway", "two car driveway", "2-car driveway", "off-street parking"],
        maps_to=AmenityLabel.parking_driveway.value,
    )
    labels[AmenityLabel.street_parking.value] = _amenity(
        AmenityLabel.street_parking.value,
        ["on-street parking", "street parking", "curbside parking"],
        maps_to=AmenityLabel.street_parking.value,
    )
    labels[AmenityLabel.ev_charger.value] = _amenity(
        AmenityLabel.ev_charger.value,
        ["ev charger", "ev charging", "electric vehicle charger", "level 2 charger", "tesla charger"],
        cutoff=0.65,  # slightly stricter
        maps_to=AmenityLabel.ev_charger.value,
    )
    labels[AmenityLabel.dishwasher.value] = _amenity(
        AmenityLabel.dishwasher.value,
        ["built-in dishwasher", "dish washer", "dw"],
        maps_to=AmenityLabel.dishwasher.value,
    )
    labels[AmenityLabel.in_unit_laundry.value] = _amenity(
        AmenityLabel.in_unit_laundry.value,
        ["in-unit laundry", "in unit laundry", "in suite laundry", "washer/dryer", "w/d", "wd"],
        maps_to=AmenityLabel.in_unit_laundry.value,
    )
    # Stainless appliances are modeled in enums as a MaterialTag, but we also keep it
    # as an amenity-class detection in the closed set so providers can emit it directly.
    labels[MaterialTag.stainless_appliances.value] = _amenity(
        MaterialTag.stainless_appliances.value,
        ["stainless appliances", "stainless steel appliances", "ss kitchen"],
        maps_to=MaterialTag.stainless_appliances.value,
    )
    labels[AmenityLabel.fireplace.value] = _amenity(
        AmenityLabel.fireplace.value,
        ["gas fireplace", "wood fireplace", "wood stove"],
        maps_to=AmenityLabel.fireplace.value,
    )
    labels[AmenityLabel.balcony.value] = _amenity(
        AmenityLabel.balcony.value,
        ["balcony deck", "balconies"],
        maps_to=AmenityLabel.balcony.value,
    )
    labels[AmenityLabel.patio.value] = _amenity(
        AmenityLabel.patio.value,
        ["terrace", "back patio", "deck"],
        maps_to=AmenityLabel.patio.value,
    )
    labels[AmenityLabel.fenced_yard.value] = _amenity(
        AmenityLabel.fenced_yard.value,
        ["fenced yard", "fenced backyard", "fenced-in yard"],
        maps_to=AmenityLabel.fenced_yard.value,
    )

    # Keep additional non-enum amenity used by providers (quality proxy)
    labels["natural_light_high"] = _amenity(
        "natural_light_high",
        ["bright natural light", "great natural light", "sun-drenched", "south-facing windows", "natural light"],
        cutoff=0.70,
        maps_to="natural_light_high",
    )

    # ---- Defects (enum-aligned) --------------------------------------------
    labels[DefectLabel.mold_suspected.value] = _defect(
        DefectLabel.mold_suspected.value,
        ["mold", "mould", "black mold", "mildew"],
        cutoff=0.70,  # high-risk → stricter
    )
    labels[DefectLabel.water_leak_suspected.value] = _defect(
        DefectLabel.water_leak_suspected.value,
        ["leak", "leaking", "water leak", "roof leak"],
        cutoff=0.65,
    )

    # (Optional) keep a few extra defects from earlier versions if helpful
    labels["water_stain_ceiling"] = _defect(
        "water_stain_ceiling",
        ["ceiling water stain", "water damage ceiling", "brown stain ceiling"],
        cutoff=0.65,
    )

    onto = Ontology(version="amenities_defects_v1", labels=labels)
    onto.validate()
    return onto


# Public singleton for convenience
AMENITIES_DEFECTS_V1: Ontology = build_amenities_defects_v1()
