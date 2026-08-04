# VIRALDY PR #14 — SEMANTIC CORRECTNESS COMPLETION GOAL
## Codex Goal-Mode Execution Contract

> **Repository:** `dhtphu05/viraldy`  
> **Target branch:** `hardening/keyless-product-hardening`  
> **Pull request:** `#14 feat: harden creative domain intelligence contracts`  
> **Current audited head:** `2878bf2075ee22d268c91adf94cfbbdb92f04390`  
> **Primary objective:** complete the semantic correctness work required before PR #14 is merge-ready  
> **Do not deploy. Do not add later roadmap features. Do not rewrite the platform foundation.**

---

# 0. EXECUTION DIRECTIVE

Read the current PR #14 source before modifying it.

The branch already contains major improvements:

```text
ProductContextV1
MediaObservationBundleV1
typed evidence_v1
CreativeDnaV1
TikTokScoreResultV2
AdaptationOutputV2
CampaignPackBriefV1
compiled requirements
Preflight V2
multi-category fixture/mock flows
```

Preserve them.

This is not another architecture rewrite. The remaining problem is semantic correctness: the product can pass schema and smoke tests while still making a wrong business decision.

Do not stop after planning, interfaces, migrations, or tests. Do not merge while the P0 defects remain active.

The goal is complete only when:

```text
required disclosures are checked for presence
prohibited claims are checked for absence
brief requirements are matched against exact observed evidence
buyer persona and creator persona remain separate
silent/no-audio video completes the workflow
core new API results are strongly typed
cross-module ownership is clean
semantic regression cases pass
```

---

# 1. CURRENT DEFECTS

Treat every item below as an acceptance requirement.

## 1.1 P0 — Required disclosure is compiled as a prohibited claim

Current behavior combines:

```text
claim_guardrails.prohibited
claim_guardrails.required_disclosures
```

and treats both as something that must not appear.

Correct behavior:

```text
prohibited claim → must not appear
required disclosure → must appear when required
allowed-with-qualification claim → claim and qualification must both appear
```

## 1.2 P0 — Preflight uses broad dimensions instead of exact requirements

A requirement such as:

```text
Demo must show steam removing wrinkles
```

must not pass merely because `demo_clarity` is high. It must be matched against the exact observed demo mechanism and its evidence.

## 1.3 P0 — CTA type and timing are incomplete

Preflight must verify:

```text
CTA exists
CTA type matches
product tag requirement
spoken/overlay requirement
required_before_ms
```

## 1.4 P0 — Product timing is not directly enforced

`expected_before_ms` must be compared directly with observed product first appearance.

## 1.5 P0 — Buyer persona and creator persona are conflated

Correct mapping:

```text
buyer persona → CampaignAudience
creator persona → CreatorDirection
```

## 1.6 P0 — No-audio MP4 can fail

Required behavior:

```text
no audio stream
→ skip audio extraction
→ skip ASR
→ empty TranscriptContract
→ continue OCR/vision/scoring/preflight
```

## 1.7 P1 — Core response payloads remain generic dictionaries

Persistence may remain JSONB, but new service/API boundaries should expose typed contracts for DNA, score, brief, compiled requirements, and Preflight alignment.

## 1.8 P1 — `ObservedValueV1.value` is `Any`

Core fields must reject invalid types, for example:

```text
first_appearance_ms = "early"
face_present = ["yes"]
screen_time_ratio = "a lot"
```

## 1.9 P1 — Product projections can drift

Prevent:

```text
products.name != product_context.identity.name
products.market != product_context.identity.market
```

## 1.10 P1 — Captured observation fields are discarded

Preserve and use:

```text
editing.pattern_interrupts
editing.dead_air_ranges
CTA spoken text
CTA overlay text
offer urgency
offer timing
```

## 1.11 P1 — Scorer shortcuts remain

Fix:

```text
offer timing credited because any timestamp exists
CTA timing credited because any timestamp exists
claim safety high-confidence despite incomplete text/vision coverage
product mismatch applied when no product context exists
```

## 1.12 P1 — Cross-module ownership is inconsistent

The Campaign Pack module must not depend on internal Preflight compiler code. Shared compiler ownership must be moved to Campaign Pack or Creative Domain and exposed publicly.

---

# 2. NON-GOALS

Do not build:

```text
deployment
billing
performance CSV
GMV prediction
PatternKit
ViralKit
creator marketplace
sample ROI
rights workflow
Spark authorization workflow
benchmarks
fatigue
TikTok crawler
fine-tuning
custom foundation model
microservices
large dashboard redesign
```

---

# 3. TARGET FLOW

```text
CampaignPackBriefV1
→ CompiledRequirementV2
→ requirement-specific matcher
→ RequirementEvaluationV2
→ BriefAlignmentResultV2
→ deterministic Preflight score/action
```

Every requirement evaluation must answer:

```text
expected
observed
status
confidence
reason
evidence_ids
```

Allowed statuses:

```text
satisfied
partial
missing
violated
unknown
not_applicable
```

Unknown must never be silently treated as satisfied.

---

# 4. CLAIM AND DISCLOSURE SEMANTICS

## 4.1 Matcher types

Add:

```text
prohibited_claim_absence
required_disclosure_presence
allowed_claim_qualification
```

Do not use one generic `claim_safety` matcher for all meanings.

## 4.2 Compiled requirement contract

Extend the current requirement contract or create V2:

```python
class CompiledRequirementV2(BaseModel):
    id: str
    requirement_type: str
    source_path: str
    description: str
    severity: Literal["hard", "high", "medium", "low"]
    matcher_type: str
    matcher_config: dict[str, object]
    expected_semantics: Literal[
        "presence",
        "absence",
        "qualified_presence",
        "timing",
        "type_match",
        "semantic_match",
    ]
    requirement_group_id: str | None = None
    minimum_satisfied: int | None = None
```

## 4.3 Prohibited claim compilation

Input:

```json
{"prohibited": ["guaranteed instant results"]}
```

Output:

```json
{
  "matcher_type": "prohibited_claim_absence",
  "expected_semantics": "absence",
  "matcher_config": {"text": "guaranteed instant results"}
}
```

## 4.4 Required disclosure compilation

Input:

```json
{"required_disclosures": ["results vary by fabric"]}
```

Output:

```json
{
  "matcher_type": "required_disclosure_presence",
  "expected_semantics": "presence",
  "matcher_config": {"text": "results vary by fabric"}
}
```

## 4.5 Evidence sources

Search normalized text from:

```text
transcript_segment
on_screen_text
cta_signal spoken/overlay text
offer_signal text
claim_signal
```

Do not evaluate exact text requirements using only aggregate dimension scores.

## 4.6 Deterministic text matching

Normalize:

```text
Unicode
lowercase
whitespace
punctuation
tokens
```

Initial pass criteria:

```text
normalized substring match
OR token overlap >= 0.75
```

When uncertain:

```text
status = unknown
confidence = low
```

## 4.7 Qualification behavior

For allowed-with-qualification claims:

```text
claim present + qualification present → satisfied
claim present + qualification missing → violated
claim absent → not_applicable or satisfied according to contract
```

## 4.8 Tests

Add:

```text
prohibited claim absent → satisfied
prohibited claim present → violated
required disclosure in transcript → satisfied
required disclosure in OCR → satisfied
required disclosure missing → missing
similar but different text → not falsely satisfied
qualified claim missing qualification → violated
```

---

# 5. REQUIREMENT COMPILER V2

Move compiler ownership to one of:

```text
modules/campaign_packs/requirements.py
modules/creative_domain/requirements.py
```

Expose it through `public.py`.

Remove:

```text
campaign_packs → preflight.requirements internal import
```

## 5.1 Compile all relevant sections

Compile from:

```text
must_show
mandatory hooks
script beats
required storyboard scenes
text overlays
creator direction
proof direction
offer direction
CTA
claim guardrails
product snapshot
angle/mechanism
```

## 5.2 Required matcher types

```text
product_visibility
product_visibility_timing
product_match
product_in_use
demo_presence
demo_mechanism_match
proof_presence
proof_type_match
overlay_text_presence
spoken_text_presence
hook_semantic_match
cta_presence
cta_type_match
cta_timing
product_tag_presence
offer_presence
offer_text_match
creator_style_match
prohibited_claim_absence
required_disclosure_presence
allowed_claim_qualification
```

## 5.3 Hook groups

Optional hooks must not all become hard requirements.

Support one-of behavior:

```text
requirement_group_id
minimum_satisfied = 1
```

Compile only mandatory hooks or selected hook groups.

## 5.4 Offer behavior

When `offer_direction` is empty, do not generate offer requirements.

When present, compile:

```text
offer_presence
offer_text_match
offer_before_cta
```

## 5.5 Tests

Add tests proving:

```text
required disclosure is not prohibited
mandatory hook compiles
optional hook alternatives form one-of group
required storyboard compiles
offer compiles only when configured
buyer persona does not become creator persona
```

---

# 6. MATCHER ENGINE

Create a registry, for example:

```text
modules/preflight/matchers/
├── base.py
├── product.py
├── demo.py
├── proof.py
├── text.py
├── cta.py
├── offer.py
├── creator.py
├── claims.py
└── registry.py
```

A flatter structure is acceptable if responsibilities remain explicit.

## 6.1 Matcher context

```python
class RequirementMatcherContext(BaseModel):
    requirement: CompiledRequirementV2
    evidence: EvidenceBundleSnapshot
    creative_dna: CreativeDnaV1 | None
    structural_score: TikTokScoreResultV2
    product_snapshot: ProductContextV1
    media_duration_ms: int
```

## 6.2 Matcher output

```python
class RequirementEvaluationV2(BaseModel):
    requirement_id: str
    status: Literal[
        "satisfied",
        "partial",
        "missing",
        "violated",
        "unknown",
        "not_applicable",
    ]
    score: int
    confidence: Literal["low", "medium", "high"]
    reason: str
    evidence_ids: list[UUID]
    expected: dict[str, object]
    observed: dict[str, object]
```

## 6.3 Product timing matcher

Compare directly:

```text
first_appearance_ms <= expected_before_ms
```

Example:

```json
{
  "expected": {"before_ms": 3000},
  "observed": {"first_appearance_ms": 4200},
  "status": "missing"
}
```

## 6.4 Product match matcher

Initial thresholds:

```text
>= 0.70 satisfied
0.40–0.69 partial
< 0.40 violated
missing confidence unknown
```

Only apply when product context exists.

## 6.5 Product-in-use matcher

Use:

```text
product_appearance.usage_visible
product_visibility_summary.usage_present
demo_step.product_visible
```

## 6.6 Demo mechanism matcher

Compare expected mechanism against:

```text
demo_step.action
demo_summary.demo_type
Creative DNA demo fields
transcript/OCR evidence
```

Do not pass simply because global demo score is high.

## 6.7 Proof matcher

Support:

```text
presence
type
verifiability
before/after
measurement
testimonial
visual result
```

## 6.8 Overlay matcher

Use only OCR/on-screen-text evidence.

## 6.9 Spoken matcher

Use transcript and spoken CTA/offer evidence.

## 6.10 CTA matcher

Evaluate separately:

```text
presence
type
product tag
required_before_ms
spoken requirement
overlay requirement
```

## 6.11 Creator matcher

Compare:

```text
delivery_style
creator_persona
speaking_present
face_present
```

## 6.12 Alignment action policy

```text
hard + missing/violated → hard blocker
high + missing/violated → revise blocker
hard + unknown → cannot approve
```

---

# 7. BUYER PERSONA VS CREATOR PERSONA

## 7.1 Adaptation contract

Ensure separate fields:

```text
buyer_persona_id
buyer_persona_label
buyer_pain
desired_outcome
creator_persona
delivery_style
```

## 7.2 Campaign Pack mapping

```python
CampaignAudienceV1(
    persona_id=concept.buyer_persona_id,
    persona_label=concept.buyer_persona_label,
)
```

```python
CreatorDirectionV1(
    persona=concept.creator_persona,
    delivery_style=concept.delivery_style,
)
```

## 7.3 Fallback rules

Buyer:

```text
selected ProductContext persona
target_buyer payload
unspecified buyer
```

Creator:

```text
concept creator persona
ProductContext creative creator persona
unspecified creator
```

## 7.4 Tests

Create a case where:

```text
buyer = busy college student
creator = beauty reviewer
```

and verify Campaign Pack preserves both separately.

---

# 8. PRODUCT PROJECTION CONSISTENCY

Treat ProductContext identity as authoritative and relational fields as indexed projections.

## 8.1 Create

When context is supplied:

```text
products.name = context.identity.name
products.market = context.identity.market
```

Reject conflicting top-level values.

## 8.2 Update

Context-only update must update projections.

Top-level name/market-only update must update context identity.

Use one transaction.

## 8.3 Tests

```text
context-only name syncs product.name
context-only market syncs product.market
top-level name syncs context identity
conflicting payload → PRODUCT_CONTEXT_INVALID
```

---

# 9. NO-AUDIO VIDEO SUPPORT

Use `audio_stream_count` from ffprobe.

When zero:

```text
skip ffmpeg audio extraction
skip audio upload
skip ASR
return empty transcript
continue OCR/vision
```

Do not reference nonexistent `audio.wav`.

Add an actual no-audio MP4 test generated with `-an`.

Verify full Quick Scorer and Preflight workflows complete.

---

# 10. STRONGER FIELD-LEVEL TYPING

Replace `ObservedValueV1(value: Any)` for critical fields.

Add concrete or generic typed wrappers:

```text
ObservedStringV1
ObservedBoolV1
ObservedIntV1
ObservedFloatV1
ObservedStringListV1
ObservedObjectListV1
```

At minimum type:

```text
first_appearance_ms → int | None
total_visible_ms → int | None
screen_time_ratio → float | None
close_up_present → bool | None
hero_shot_present → bool | None
usage_present → bool | None
face_present → bool | None
product_present → bool | None
cut_count → int | None
average_shot_duration_ms → int | None
CTA present → bool | None
product_tag_visible → bool | None
```

Expose typed new-row API contracts:

```text
CreativeDnaV1
TikTokScoreResultV2
CampaignPackBriefV1
CompiledRequirementsV2
BriefAlignmentResultV2
```

Keep explicit legacy read adapters.

---

# 11. PRESERVE OBSERVATIONS

Do not discard:

```text
pattern_interrupts
dead_air_ranges
CTA spoken text
CTA overlay text
offer timing
offer urgency
```

Populate Creative DNA accordingly.

Do not set narrative angle equal to hook type.

When angle cannot be classified:

```text
angle = unknown
```

is correct.

---

# 12. SCORER CORRECTNESS

## 12.1 Offer timing

Compare offer timestamp against CTA timestamp.

## 12.2 CTA timing

Quick score: evaluate CTA position relative to media duration.

Preflight: evaluate exact `required_before_ms`.

## 12.3 Claim confidence

```text
no risky claim + complete transcript/OCR/vision → high confidence possible
no risky claim + incomplete evidence → lower confidence
```

## 12.4 Product mismatch

Only evaluate mismatch when a product context/snapshot was supplied.

## 12.5 Tests

```text
offer after CTA loses timing credit
CTA too late loses timing credit
no claim + incomplete evidence lowers confidence
generic scorer does not enforce product mismatch without context
```

---

# 13. MODULE BOUNDARIES

Move requirement compilation to Campaign Pack or Creative Domain ownership.

Expose public functions such as:

```text
compile_campaign_requirements
get_compiled_requirements_snapshot
```

Use `public.py` across modules.

Reduce direct cross-module imports introduced/touched by PR #14.

Do not turn this into a full worker rewrite.

Add architecture tests for changed modules.

---

# 14. SEMANTIC GOLDEN MATRIX

## Categories

```text
home organization
beauty tool
POD personalized gift
pet accessory
fashion accessory
```

## Scenarios

```text
strong structure
late product reveal
product absent
missing CTA
wrong CTA type
CTA too late
no offer
offer after CTA
no speech
no audio stream
high-risk claim
required disclosure present
required disclosure missing
prohibited claim present
product mismatch
wrong demo mechanism
missing required overlay
wrong creator style
```

## Assertions

Do not only assert `status ok` and `score 0..100`.

Assert:

```text
schema version
exact requirement status
exact blocker/fix code
expected/observed payload
evidence IDs exist
buyer/creator separation
no category leakage
```

---

# 15. MIGRATION

Create a new migration only when persistence changes are required.

Suggested:

```text
0005_semantic_correctness_completion
```

Do not edit `0004`.

New compiled snapshots should use:

```text
compiled_requirements_v2
```

Historical snapshots remain readable.

---

# 16. MILESTONES

## S0 — Baseline

- [ ] Confirm branch/PR head.
- [ ] Run current unit checks.
- [ ] Run fixture smoke.
- [ ] Run mock smoke.
- [ ] Record current behavior.

## S1 — Claim/disclosure correctness

- [ ] Separate prohibited/disclosure compilation.
- [ ] Add exact matcher types.
- [ ] Add normalized text matching.
- [ ] Add qualification logic.
- [ ] Add tests.

## S2 — Requirement compiler V2

- [ ] Move compiler ownership.
- [ ] Compile hooks/storyboard/overlays/creator/offer.
- [ ] Compile product timing/use/match.
- [ ] Compile exact demo/proof semantics.
- [ ] Add compiler tests.

## S3 — Matcher engine

- [ ] Add matcher registry.
- [ ] Implement product timing/match/use.
- [ ] Implement demo/proof semantic matching.
- [ ] Implement spoken/overlay matching.
- [ ] Implement CTA type/tag/timing.
- [ ] Implement offer/creator/claims.
- [ ] Return exact expected/observed data.

## S4 — Persona and product consistency

- [ ] Separate buyer and creator persona.
- [ ] Sync ProductContext and projections.
- [ ] Update frontend labels.
- [ ] Add tests.

## S5 — Media edge cases

- [ ] Support no-audio video.
- [ ] Preserve editing ranges.
- [ ] Preserve CTA spoken/overlay.
- [ ] Preserve offer timing/urgency.
- [ ] Add actual no-audio test.

## S6 — Typed responses

- [ ] Type critical DNA values.
- [ ] Add typed DNA response.
- [ ] Add typed score response.
- [ ] Add typed Campaign Pack response.
- [ ] Add typed Preflight response.
- [ ] Preserve legacy reads.

## S7 — Scorer corrections

- [ ] Fix offer timing.
- [ ] Fix CTA timing.
- [ ] Fix claim confidence.
- [ ] Gate product mismatch by context.
- [ ] Add tests.

## S8 — Boundaries

- [ ] Move compiler ownership.
- [ ] Replace changed cross-module internal imports.
- [ ] Update architecture tests.

## S9 — Semantic regression

- [ ] Run all categories.
- [ ] Run all edge scenarios.
- [ ] Verify exact statuses/blockers/fixes.
- [ ] Verify no hardcode leakage.
- [ ] Run fixture full loop.
- [ ] Run mock full loop.
- [ ] Run no-audio full loop.

## S10 — Merge-ready handoff

- [ ] Backend ruff passes.
- [ ] Backend unit tests pass.
- [ ] Clean migrations pass.
- [ ] Frontend lint/build pass.
- [ ] PR description updated with actual results.
- [ ] PR architecture checklist completed honestly.
- [ ] Audit and Execution Log updated.

---

# 17. DEFINITION OF DONE

## Claim governance

- [ ] Prohibited claim absence is evaluated.
- [ ] Required disclosure presence is evaluated.
- [ ] Qualification presence is evaluated.
- [ ] Required disclosure is never compiled as prohibited.

## Preflight

- [ ] Product timing uses exact first appearance.
- [ ] Product use/match are evaluated.
- [ ] Demo mechanism is matched.
- [ ] Proof type is matched.
- [ ] OCR overlays are matched from OCR.
- [ ] Spoken requirements are matched from transcript.
- [ ] CTA type/tag/timing are matched.
- [ ] Offer and creator requirements are matched.
- [ ] Every requirement includes expected/observed/evidence.
- [ ] Hard requirements override action.

## Persona/product

- [ ] Buyer and creator personas are separate.
- [ ] ProductContext and relational projections cannot drift.
- [ ] Historical snapshots remain immutable.

## Media

- [ ] No-audio video completes.
- [ ] No fake audio artifact is created.
- [ ] Editing ranges and text modality are preserved.

## Typing

- [ ] Critical DNA values are typed.
- [ ] New core API responses expose typed contracts.
- [ ] Legacy rows remain readable.

## Scoring

- [ ] Offer timing compares with CTA.
- [ ] CTA timing uses real duration/deadline.
- [ ] Claim confidence reflects evidence coverage.
- [ ] Product mismatch is context-aware.

## Architecture

- [ ] Requirement compiler has correct ownership.
- [ ] Changed modules use public contracts.
- [ ] PR checklist is accurate.

## Verification

- [ ] Fixture full loop passes.
- [ ] Mock-provider full loop passes.
- [ ] No-audio full loop passes.
- [ ] Semantic category matrix passes.
- [ ] Backend/frontend checks pass.

---

# 18. EXECUTION LOG

Update after every milestone.

```text
Date:
Milestone:
Status: not_started | in_progress | completed | blocked

Branch:
Commit:
Files changed:
Migration:
Contracts:
Matchers:
Tests added:
Commands run:
Results:
Semantic failures:
Known risks:
Notes:
```

## S0

```text
Status: not_started
```

## S1

```text
Status: not_started
```

## S2

```text
Status: not_started
```

## S3

```text
Status: not_started
```

## S4

```text
Status: not_started
```

## S5

```text
Status: not_started
```

## S6

```text
Status: not_started
```

## S7

```text
Status: not_started
```

## S8

```text
Status: not_started
```

## S9

```text
Status: not_started
```

## S10

```text
Status: not_started
```

---

# 19. FINAL REPORT

Report:

1. Baseline PR/head.
2. Claim/disclosure defect and fix.
3. Requirement compiler changes.
4. Matchers implemented.
5. Persona separation.
6. Product projection consistency.
7. No-audio handling.
8. Typed response changes.
9. Creative DNA typing.
10. Scorer corrections.
11. Module-boundary changes.
12. Migration/legacy compatibility.
13. Unit results.
14. Fixture E2E results.
15. Mock E2E results.
16. No-audio E2E result.
17. Semantic category results.
18. No-leak results.
19. Remaining live-provider risks.
20. Final merge recommendation.

Do not claim production-ready until a real provider has been qualified.

Acceptable completion statement:

```text
PR #14 is semantically merge-ready for live-provider qualification and private-beta preparation.
```

---

# 20. FINAL COMMAND TO CODEX

Read `VIRALDY_PR14_SEMANTIC_CORRECTNESS_COMPLETION_GOAL.md` and execute it as the single source of truth.

Continue from S0 through S10.

Preserve the current typed-domain and keyless infrastructure work.

Do not deploy and do not add later roadmap features.

Do not stop after planning, schemas, matcher interfaces, or tests.

The goal is complete only when:

```text
required disclosures are checked for presence
prohibited claims are checked for absence
Campaign Pack requirements are matched against exact evidence
buyer and creator personas remain separate
no-audio videos complete
new core API responses are typed
semantic regression cases pass
PR #14 satisfies its architecture checklist
```
