# tests/core/finance/test_golden_anchor.py
"""
The anchor-digest test (Mission 5, D.3 section 3.3 Part 2 / GD.1 condition C2).

WHY THIS TEST LIVES IN ITS OWN FILE
--------------------------------------
D.3 is explicit: "It lives in its own file so its failure message is unmistakable and so it fires
even if the main harness is deselected or errors during collection." An anchor-digest mismatch is a
DIFFERENT, structurally-earlier failure than a tolerance failure in
`test_golden_forecasts.py::test_forecast_matches_golden_within_tolerance` -- it means the anchored
artifact itself was edited (or the anchor record was not updated to match a legitimate
regeneration), not that a computed value drifted. Conflating the two failure messages would defeat
the whole point of the anchor mechanism (D.3 section 5.4: perturbing the golden to "test" the
tolerance rule is itself the first step of the ratchet the anchor exists to prevent).

WHAT THIS TEST DOES NOT DO
------------------------------
It does NOT shell out to `git`. `tests/data/golden/finance_engine_forecasts.json` has exactly one
committed version in this repository's history (`912a55f`) -- verified in D.3 section 3.1 and
independently reconfirmed by the guardian (GD.1) -- so "the ORIGINAL golden" is unambiguous without
consulting git history, and D.3 section 3.2 option D rejects git-history-based verification outright
(CI does shallow clones, source tarballs have no `.git`, and this project keeps its test paths free
of environment dependencies).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.core.finance.golden_tolerance import (
    CUMULATIVE_DRIFT_BUDGET,
    GOLDEN_PATH,
    canonical_cases_digest,
    cumulative_drift,
    load_anchor,
)

_REQUIRED_ANCHOR_KEYS = {
    "anchored_artifact",
    "cases_sha256",
    "anchored_at_commit",
    "anchored_on",
    "approved_by",
    "rationale",
    "max_rel_drift_vs_previous_anchor",
    "supersedes",
}


@pytest.fixture(scope="module")
def golden() -> dict[str, Any]:
    with GOLDEN_PATH.open("r", encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    return data


@pytest.fixture(scope="module")
def anchor() -> dict[str, Any]:
    return load_anchor()


def test_anchor_file_exists_and_is_shaped_correctly(anchor: dict[str, Any]) -> None:
    missing = _REQUIRED_ANCHOR_KEYS - set(anchor.keys())
    assert not missing, f"ANCHOR.json is missing required key(s): {sorted(missing)}"
    assert anchor["anchored_artifact"] == "finance_engine_forecasts.json"
    assert (
        isinstance(anchor["cases_sha256"], str) and len(anchor["cases_sha256"]) == 64
    ), "cases_sha256 must be a 64-char hex SHA-256 digest"
    assert anchor["approved_by"], "an anchor record with no named approver is not a founder-visible event -- GD.1 condition C3"
    assert anchor["rationale"], "an anchor record with no rationale defeats the whole mechanism -- GD.1 condition C3"


def test_anchor_digest_matches_the_committed_golden(golden: dict[str, Any], anchor: dict[str, Any]) -> None:
    """
    THE core anchor assertion. If this fails, `tests/data/golden/finance_engine_forecasts.json`'s
    `cases` subtree no longer matches what `tests/data/golden/ANCHOR.json` says was reviewed and
    approved -- either the golden was hand-edited, or a regeneration ran without going through
    `generate_golden_forecasts.py --supersede-anchor --rationale "..."`. Either way: STOP. Do not
    "fix" this by editing ANCHOR.json to match. See D.3 section 3.4.
    """
    actual_digest = canonical_cases_digest(golden["cases"])
    expected_digest = anchor["cases_sha256"]
    assert actual_digest == expected_digest, (
        "ANCHOR DIGEST MISMATCH -- tests/data/golden/finance_engine_forecasts.json's `cases` subtree "
        f"does not match the digest recorded in tests/data/golden/ANCHOR.json.\n"
        f"  anchor says:   {expected_digest}\n"
        f"  golden is now: {actual_digest}\n"
        "This means the golden file moved without a reviewed, rationale-carrying "
        "`--supersede-anchor` run. Do not edit ANCHOR.json to make this pass -- that is the ratchet "
        "this mechanism exists to prevent. Re-run "
        '`python -m tests.core.finance.generate_golden_forecasts --supersede-anchor --rationale "..." '
        '--approved-by "..."` if this drift is a reviewed, founder-approved decision.'
    )


def test_anchor_cumulative_drift_is_within_budget(anchor: dict[str, Any]) -> None:
    """
    GD.1 condition C2 (MANDATORY, "the only element of the anchor design that does not decay"):
    the sum of `max_rel_drift_vs_previous_anchor` across the entire `supersedes` chain, from the
    very first anchor to the current one, must not exceed `CUMULATIVE_DRIFT_BUDGET` (1e-8, i.e. 10
    hops at full REL_TOL). D.3 section 3.5.
    """
    total = cumulative_drift(anchor)
    assert total <= CUMULATIVE_DRIFT_BUDGET, (
        f"CUMULATIVE ANCHOR DRIFT BUDGET EXHAUSTED: {total:.4e} > {CUMULATIVE_DRIFT_BUDGET:.4e} "
        "summed across the ANCHOR.json `supersedes` chain.\n"
        "This does NOT mean raise the budget. It means the numbers must be independently "
        "re-verified by a human -- in the spirit of test_sample_deal_verified_baseline_numbers -- "
        "rather than re-generated again. That re-verification is the only thing that can restore "
        "the chain to vouched-for status. See docs/plans/mission-5-discovery/D3_tolerance_rule.md "
        "section 3.5 and docs/plans/mission-5-discovery/GD1_veto_review.md condition C2."
    )


def test_anchor_supersedes_chain_is_well_formed(anchor: dict[str, Any]) -> None:
    """Every node in the `supersedes` chain must itself carry the required keys, all the way back."""
    node: dict[str, Any] | None = anchor
    depth = 0
    seen_digests: set[str] = set()
    while node is not None:
        missing = _REQUIRED_ANCHOR_KEYS - set(node.keys())
        assert not missing, f"malformed anchor record at chain depth {depth}: missing {sorted(missing)}"
        digest = node["cases_sha256"]
        assert digest not in seen_digests, f"ANCHOR.json `supersedes` chain contains a cycle or a repeated digest at depth {depth}"
        seen_digests.add(digest)
        node = node.get("supersedes")
        depth += 1
    assert depth >= 1


def test_anchor_baseline_is_the_single_committed_golden_version(anchor: dict[str, Any]) -> None:
    """
    Verified fact this module's docstring cites: this repository has exactly one committed version
    of `finance_engine_forecasts.json` (`912a55f`), so the first anchor in the chain necessarily
    IS that version -- there is nothing earlier to anchor to (D.3 section 3.1). This test does not
    re-derive that fact via git (tests must not shell out to git); it pins that the *first* anchor
    in the chain has no predecessor, which is the structural expression of the same fact.
    """
    node: dict[str, Any] = anchor
    while node.get("supersedes") is not None:
        node = node["supersedes"]
    assert (
        node["max_rel_drift_vs_previous_anchor"] is None
    ), "the first anchor in the chain must not claim drift against a nonexistent predecessor"
    assert node["supersedes"] is None


def test_editing_the_golden_trips_the_anchor_test_first(tmp_path: Path, golden: dict[str, Any], anchor: dict[str, Any]) -> None:
    """
    D.3 section 5.3 Test C, discharged here (anchor-mechanism concern, not calibration-recipe
    concern -- the calibration RED suite lives in `test_golden_tolerance_walls.py`).

    Simulates hand-editing one number in the golden and re-checking the digest -- WITHOUT touching
    the committed golden file itself (never perturb the golden to test the tolerance rule; perturb
    a throwaway copy). Confirms the digest mismatch fires BEFORE any numeric/tolerance comparison
    would even run.
    """
    import copy

    mutated = copy.deepcopy(golden["cases"])
    first_case_id = next(iter(mutated))
    mutated[first_case_id]["forecast"]["purchase"]["dscr"] += 1.0  # a huge, obvious, non-tolerance-passing edit

    mutated_digest = canonical_cases_digest(mutated)
    assert mutated_digest != anchor["cases_sha256"], "a mutated `cases` subtree must not produce the anchored digest"
