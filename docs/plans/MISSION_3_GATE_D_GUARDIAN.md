# Mission 3 — Gate D Guardian Review (Overclaim VETO)

_Reviewer: `principal-principles-guardian`. Blocking pre-implementation gate. Reviewed against
`docs/plans/MISSION_3_DISCOVERY_SPEC.md` and `docs/plans/MISSION_3_byo_onnx_provider.md` at
branch `mission/3-byo-onnx-provider`, `HEAD = 6d9c000` (confirmed via `git log`/`git status`;
matches both documents' stated baseline)._

---

## VERDICT: NO VETO WITH CONDITIONS

The spec is fundamentally honest and self-policing — it flags its own overclaim risks (§6.3, §7)
before I had to. It clears review with eight checkable conditions below, none of which require
re-architecture; all are docs/wording/scope discipline for the Implementation and Gate V waves.

---

## Conditions (checkable at Gate V)

1. **`ONNX_BYO_VERSION = "onnx-byo-v1"` ships exactly as specified (spec §3.2).** The constant,
   its docstring, and every place it is echoed (report appendix, CLI print, tests) must not be
   restated as "real AI," "AI-powered," or any language implying verified accuracy. The name
   itself is honest (see Rationale §1) — this condition is about not eroding that honesty in
   surrounding prose during implementation.

2. **`--onnx-model` / `--onnx-labels` help text ships with all three disclosures drafted in spec
   §4.2, unwatered-down:**
   (a) "this is YOUR OWN model — the project does not vouch for its accuracy";
   (b) the `provenance.provider_kind='model'` explanation ("a real classifier ran, not that its
   output is trustworthy");
   (c) the explicit statement that `main.py` does not read these flags.

3. **No user-facing string introduced by this mission** (CLI help, error message, README,
   CHANGELOG, or report copy) may use "real AI," "AI-powered," "verified," "validated,"
   "accurate," "trustworthy," "state-of-the-art," or any comparative-quality claim of the ONNX
   path over the stub/local path.

4. **The six-label unlock must be described as "detector-adjudicated" (confirmed OR contested),
   never flatly "confirmed."** This applies to CHANGELOG, README, and — critically — the Mission
   3 manual-testing doc Roger will run by hand: it must not assert one specific outcome (fired vs.
   not-fired) without a fixture engineered to guarantee it (spec §6.3, §8.3's biased-output-unit
   technique). I concur with the spec's own finding here and extend it: the charter's DoD bullet
   4 ("become detector-confirmed observations") is itself imprecise by this same standard — it is
   a historical planning artifact I am not asking anyone to rewrite, but no *downstream*,
   Roger-facing document may repeat its imprecision as fact.

5. **`src/core/README.md:196` must be corrected in this mission's docs pass**, not deferred. It
   currently reads:

   > "The package is intentionally not declared in `requirements.txt` because it is an opt-in
   > dependency for advanced users only."

   This is false today — `requirements.txt:27` pins `onnxruntime>=1.16.0,<2.0.0` unconditionally
   (confirmed by direct read), added in `66ffacd`, before this mission. Independently confirmed,
   matching the spec's §0.1 finding. See "In scope" ruling below for why this is this mission's
   obligation and not a deferrable pre-existing bug.

6. **`README.md`'s "Optional Dependencies → ONNX Runtime" section (lines 379–400, confirmed by
   direct read) must be updated in the same docs pass.** Two of its claims become actively false
   the moment this mission ships, not just stale:
   - "install `onnxruntime` separately: `pip install onnxruntime`" — it is already installed by
     every documented setup path.
   - "This is a **Python-API-only feature** — no CLI command automatically loads ONNX models." —
     the new `--onnx-model`/`--onnx-labels` flags on `ingest-listing` do exactly that.
   Shipping this mission without touching this section leaves `README.md` contradicting itself
   within one file: one section says a CLI flag registers the model, another says no CLI does.

7. **If the `SessionOptions` single-thread/sequential-execution determinism pin (spec §7) is
   deferred rather than shipped**, every place this mission describes ONNX-path determinism
   (CHANGELOG, README, DoD sign-off, manual-testing doc) must scope the claim honestly: "verified
   for the shipped synthetic fixture; not a guarantee for arbitrary user-supplied models" — not an
   unqualified "byte-identical" or "deterministic" claim for the ONNX path in general. The
   **default** (nothing registered) path's byte-identical guarantee is a structural property
   (spec §3.4) and may be stated without qualification regardless of this condition.

8. **`staff-documentation-maintainer` is held to the do-say / do-not-say list in the Rationale
   below (§5), verbatim, at Gate V.**

---

## Rationale

### 1. The version constant (`ONNX_BYO_VERSION = "onnx-byo-v1"`) — honest, does not overclaim

Spec §3.2 (`docs/plans/MISSION_3_DISCOVERY_SPEC.md:236-257`). The string says two true things and
nothing else: this is the BYO-ONNX code path, and `v1` names the wiring's version, not the
model's accuracy. It deliberately avoids `VISION_STUB_VERSION`'s reuse (that word says "stub,"
which this mission's own honesty obligation forbids saying about a real classifier) and avoids
embedding a per-model fingerprint (which would be new information belonging in `provenance`, not
a repurposing of `version`'s existing coarse producer-type meaning). Verified against the actual
file: `VISION_STUB_VERSION`/`DETERMINISTIC_VERSION` at `src/core/cv/photo_insights.py:46,50`
follow the identical "names the code path, not a quality claim" convention already — the new
constant is consistent with, not a deviation from, established practice. It does not underclaim
either: `provider_kind` (computed independently by `amenities_defects.provider_kind`,
`amenities_defects.py:644-654`, verified) still flips to `"model"` and is stamped alongside
`version` in the same Run Provenance appendix row (`src/core/reports/generator.py:587-593`,
verified — `_flatten_provenance` walks `media_report.provenance`, which carries both keys). A
report reader gets both facts side by side, exactly as the existing `vision-stub-v1` /
`heuristic_stub` pair already does. No veto.

### 2. CLI help text (§4.2) — meets the honesty bar, states the `main.py` scope limit

Both flags' help strings (quoted in full at spec `MISSION_3_DISCOVERY_SPEC.md:397-424`) contain
the mandated disclosure almost verbatim: *"This is YOUR OWN model -- the project does not vouch
for its accuracy."* They also state the `main.py` scope limitation I was asked to check for
("Applies to `ingest-listing` only... does not read this flag"), so a `main.py`-only user is not
left wondering why the flag appears inert there — this mirrors the existing precedent at
`README.md:31` (the `--config`-without-`--listing`/`--photos` refusal message) and the existing
`--ai` flag's own self-deprecating help text at `src/cli/ingest_cli.py:53-64` (verified: "It is
NOT a model call... Treat its labels as a placeholder, not as observations"). No veto; codified as
Condition 2 so nothing is softened during implementation.

### 3. Error messages (§5 table) — no overclaim, no unhelpful user-blaming

Reviewed all eleven rows. None assert accuracy or trustworthiness; all are neutral and actionable
("file not found. Check the path passed to this flag.", "must contain a JSON object with a
'labels' list, e.g. `{"labels": [...]}`"). Row 2's inclusion of the raw `onnxruntime` exception
text (`f"...failed to load ONNX model ({e})."`) surfaces real information about the user's *own*
file failing to parse as a valid ONNX protobuf — appropriate and not "leaking confusing internals"
in the pejorative sense, since it is the most actionable thing available for debugging a file the
user supplied themselves; this is a code-reviewer style question, not a principles violation. No
veto.

### 4. Six-label unlock framing (§6) — honest; correctly distinguishes declaration from evidence

I independently traced the mechanism against the live code, not just the spec's narrative:

- `provider_capabilities`/`_declare_capabilities` (`src/core/cv/amenities_defects.py:364-380`,
  verified) frames a provider's `labels.json` as exactly what the spec calls it — a
  **declaration**, never evidence. The `core/README.md:112` docstring already states this
  invariant independently of this mission: "A provider **declares** the label vocabulary it can
  emit... An undeclared provider covers **nothing** (silence is not evidence that something
  looked)." This mission does not touch that mechanism; it only makes a new caller reach it.
- Critically, `"filename_confirmed"` (the strong outcome) requires **two** independent things: the
  model's `labels.json` declares the label (the assertion) **and** the model's own
  `predict_proba` actually reports it for that specific image (a real inference result,
  `runner.py:258-269`). Declaring capability alone, with no firing, lands the record in
  `"filename_contested"` at a flat 0.30 confidence — a materially weaker claim, and one the schema
  README (`src/schemas/README.md:105-109`) already documents as **less** trustworthy than an
  unconfirmed hint in some respects, not more. So the mechanism does not let a self-declared
  capability alone masquerade as a confirmed observation; it requires a real per-image inference
  to reach the strong outcome. This is the correct, non-overclaiming design.
- Spec §6.3 (`MISSION_3_DISCOVERY_SPEC.md:683-696`) already catches and corrects the charter's own
  imprecise "become detector-confirmed observations" wording, replacing it with "detector-
  **adjudicated** (confirmed OR contested)." I concur with this finding and elevate it to a
  binding condition (Condition 4) rather than leaving it as spec-author advice, specifically
  because the artifact most likely to repeat the imprecise wording is the Roger-facing manual-
  testing doc, which I do not otherwise gate.

No veto; Condition 4 makes the correction binding rather than advisory.

### 5. Docs guidance for `staff-documentation-maintainer` — do-say / do-not-say (binding at Gate V)

**Do say:**
- "bring your own ONNX classifier" / "user-supplied model."
- "the project does not vouch for its accuracy" (or a materially equivalent phrase), stated in
  the same breath as any capability claim, not in a separate paragraph a reader can skip.
- "`provider_kind` flips to `'model'`" paired with what that does and does not mean: a real
  (non-stub) classifier ran; its output's correctness is not something the project assessed.
- "applies to `ingest-listing` only; `main.py` is unaffected."
- the six labels "become measurable" / "become detector-adjudicated (confirmed or contested)."
- the true dependency status: `onnxruntime` ships by default today (Condition 5/6) — do not
  reintroduce the "install it separately" framing anywhere it is corrected.

**Do not say:**
- "real AI," "AI-powered," "powered by artificial intelligence" as a project capability claim.
- "more accurate," "smarter," "better detection" relative to the stub or local providers — the
  project has no basis for a comparative claim about a file it has never evaluated.
- "verified," "validated," "tested," "benchmarked," or any language implying the project audited,
  trained, or endorsed the user's model. (Note: the structural checks in `_OnnxModel.__init__` —
  non-empty inputs/outputs, valid protobuf — are load-time sanity checks, not a quality or
  security audit; docs must not conflate the two.)
- flatly "confirmed" for the six-label mechanism without the confirmed-or-contested caveat.
- anything that blurs this mission (backlog #3 offering 1, bring-your-own) with offering 3 (a
  future project-shipped, project-trained model) — the charter (`MISSION_3_byo_onnx_provider.md:101-106`)
  keeps these explicitly separate and out-of-scope for each other; docs must too.

### 6. The stale-doc finding — IN SCOPE for this mission's honesty obligations

Independently confirmed: `requirements.txt:27` reads `onnxruntime>=1.16.0,<2.0.0`, an
unconditional line (not a `[project.optional-dependencies]` extra — `pyproject.toml` has no
`[project.dependencies]`/extras table for it), while `src/core/README.md:196` claims it is
"intentionally not declared in `requirements.txt`." That statement is false as of `66ffacd`,
independent of this mission.

**Ruling: correcting it is in scope for this mission, on two grounds specific to Mission 3 — not
a general "fix all doc drift" mandate:**

1. The spec's own touched-files table (§9) already schedules `src/core/README.md` for a docs edit
   this mission ("document the new CLI path per §2"). The false line sits in the same
   "Dependencies / Optional Providers" section (`src/core/README.md:186-197`) that edit lands in.
   Leaving a known-false adjacent sentence uncorrected while editing the paragraph around it is
   not "out of scope," it is drafting a new paragraph next to a false one and pretending not to
   notice.
2. Substantively, the false claim would directly contradict the new claim this mission must make
   honestly: that the `--onnx-model`/`--onnx-labels` flags work out of the box against the
   documented install path. A reader hitting "not declared... opt-in dependency for advanced
   users" immediately before or after "pass `--onnx-model` and it works" is reading a
   self-contradicting document, which is exactly the kind of drift this guardian role exists to
   prevent (README.md's own "Last reconciled" footer, `README.md:475`, records prior guardian-
   driven corrections of the identical class of defect).

Same reasoning extends to `README.md:379-400`'s "Optional Dependencies" section (Condition 6),
which I found independently while verifying the spec against the live README — the spec's
touched-files table did not flag this second location, but it contains the same-class defect
("Python-API-only feature — no CLI command automatically loads ONNX models") and becomes false for
the same reason. I am not treating this as a new scope expansion beyond the mission; I am treating
it as the mission's own DoD bullet ("README ... describe the new path honestly") applied to a
location the spec missed.

### Also weighed

- **Charter's own framing ("confirmed observations," Executive Summary line
  `MISSION_3_byo_onnx_provider.md:27-31` and DoD bullet 4, `:148-150`).** Overclaims by the same
  margin the spec's own §6.3 identifies — see Condition 4/Rationale §4. I am not bound by the
  charter's language and am not requiring the charter file itself be edited (it is a dated
  planning artifact, not a live claim a reader trusts), but every *downstream* artifact,
  especially the manual-testing doc, must use the corrected language.
- **Deterministic-core invariant.** Confirmed not eroded. Spec §9 "NOT touched" is accurate against
  a live read: zero symbols from `src/core/finance/**` or `src/schemas/models.py` appear anywhere
  in the diff plan. The ONNX model's `predict_proba` output only ever reaches
  `DetectedLabel`/`ListingInsights.amenities|defects|condition_tags` through the same
  `_augment_from_filename`/`is_uncorroborated_filename_claim` gate every other provider already
  goes through (`src/core/README.md:126-142`, verified against `runner.py` as cited in spec §6.1).
  The verdict path (`agents.chief_strategist.synthesize_thesis`) is untouched and unreachable from
  anywhere in this diff. No erosion, direct or by implication.
- **Determinism (§7).** The spec's own honest scoping of the "byte-identical" claim if the
  `SessionOptions` pin is deferred is exactly the right instinct — codified as Condition 7 so it
  survives into whatever CHANGELOG/README prose Wave Implementation actually writes, rather than
  remaining a spec-only caveat nobody re-reads at Gate V.
- **Security/dependency-footprint items (§8, `onnx` package for fixture generation) are not
  overclaim/honesty matters** — no veto trigger implicated (no paid contract, no always-on
  service, no license conflict: `onnx` is Apache-2.0, dev-only, never distributed). Left to
  `staff-code-reviewer`/`principal-security-engineer` at their respective gates.
- **License posture.** No proposal here touches `LICENSE.md`/`LICENSE-commercial.md`/`NOTICE.md`
  framing. Noted for the record: this project's actual license is a **Research & Education
  License** with a separate commercial license (`LICENSE.md:1-19`, `NOTICE.md:8-9`), not an MIT +
  commercial dual license — my standing instructions describe the latter pattern generically; the
  documented posture here is the R&E + commercial pattern. Not implicated by this mission either
  way.

---

## Evidence of reading

- `docs/plans/MISSION_3_DISCOVERY_SPEC.md` (full) — the proposal under review; §3.2 version
  constant, §4.2 help text, §5 error table, §6 six-label mechanism, §6.3 self-correction, §7
  determinism honesty, §9 touched/not-touched files.
- `docs/plans/MISSION_3_byo_onnx_provider.md` (full) — charter; binding constraint 5 is the
  overclaim line I enforce; Executive Summary and DoD bullet 4's "confirmed" wording assessed
  and found imprecise (Rationale, "Also weighed").
- `README.md` — Tech Stack line 242 (accurately says "user-registered ONNX models," no overclaim);
  Roadmap V4 entry (lines 466-468, honestly frames `--ai` as a labelled heuristic today); the
  stale "Optional Dependencies → ONNX Runtime" section, lines 379-400 (Condition 6).
- `src/core/README.md` — CV v2 API list (line 69, 109-112) and Dependencies section, lines
  186-197, containing the false "not declared in requirements.txt" claim (Condition 5); the
  SUGGEST-vs-CONFIRM table (lines 114-124) that makes "confirmed" require real per-image
  inference, not just a `labels.json` declaration.
- `src/schemas/README.md` — `ObservationProvenance`/`provider_kind` migration notes (lines 56-57,
  113-121): "Read `provider_kind` before claiming a tag was AI-observed — every built-in CV
  provider today is a `heuristic_stub`," the existing invariant this mission's honesty obligation
  extends rather than invents.
- `LICENSE.md`, `NOTICE.md`, `LICENSE-commercial.md` (listed) — Research & Education + commercial
  posture; not implicated by this mission.
- `CONTRIBUTING.md` — engineering-culture/setup norms; not implicated.
- `requirements.txt:27` — `onnxruntime>=1.16.0,<2.0.0`, confirmed unconditional, independently
  verifying spec §0.1 and grounding Condition 5.
- `CHANGELOG.md` `[Unreleased]` — confirms the `onnxruntime` dependency-declaration history
  (`66ffacd`), corroborating the stale-doc timeline.
- `docs/plans/ROADMAP_TRACKER.md` — backlog #3 row ("No real AI provider... Any 'AI-powered'
  marketing claim... Open — deferred") — the standing guardrail this mission's Condition 3
  operationalizes for the ONNX slice specifically.
- Source verified directly (not taken on the spec's word): `src/core/cv/amenities_defects.py`
  (`_OnnxModel.__init__`, `make_onnx_provider`, `register_onnx_provider`, `provider_kind`,
  `_PROVIDERS`, `_BUILTIN_STUB_FNS` — lines 258-398, 613-654); `src/core/cv/photo_insights.py`
  (version constants lines 39-50, selection logic lines 314-324); `src/cli/ingest_cli.py` (current
  state, no ONNX flags yet, confirming the spec's "before" picture); `src/core/reports/generator.py`
  (lines 530-669, confirming Run Provenance / `provider_kind` / `selected_provider` already
  surface generically for any `ProviderName` including `"onnx"`, with no schema/report change
  needed); `tests/ai/test_vision_stub_provenance_honesty.py` and
  `tests/ai/test_ai_onnx_registration.py` (existing honesty-test precedent this mission's QA task
  should extend, not invent from scratch).
- Memory directory (`~/.claude/projects/.../memory/`): no `project_*`/`feedback_*` entries exist
  for this project; only environment/workflow notes (conda env, git signing, graphify usage),
  none of which bear on this review.
