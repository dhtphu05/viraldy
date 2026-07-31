# MASTER IMPLEMENTATION PROMPT — VIRALDY TIKTOK SCORER V2

**Implementation prompt revision:** V2.1 — mandatory standalone frontend module and route contract integrated.

You are the lead staff engineer and product architect implementing the next production-grade version of **Viraldy TikTok Scorer**.

## Repository and task authority

Target repository:

```text
https://github.com/dhtphu05/viraldy
```

Primary backend module:

```text
apps/backend/src/viraldy/modules/tiktok_scorer
```

Also inspect and modify, when required, the related:

```text
frontend
API routes
database models and migrations
worker jobs
asset/media pipeline
evidence contracts
Creative DNA contracts
Product Context access
recommendation and feedback contracts
product-event tracking
tests and fixtures
```

The older repository `dhtphu05/viralscore-AI-Cross-Border` may be consulted only as a legacy reference for dimension ideas. It is not the implementation target and its old “viral score”, “prediction”, or “conversion probability” semantics must not be copied.

The previous “audit only, do not implement” constraint is superseded for this task. Re-audit the current repository briefly to detect drift, write a concise implementation note, and then implement the approved target in the same task. Do not stop after the audit unless there is a genuine destructive-migration risk or an irreconcilable architecture conflict.

---

# 1. Product contract

## 1.1 Canonical definition

```text
TikTok Scorer
= video diagnostics
+ evidence
+ deterministic structural scoring
+ detailed edit-or-reshoot plan
+ revision comparison
```

User-facing value promise:

> Upload a TikTok or UGC video, see exactly what blocks it, and receive an edit-or-reshoot plan the seller, creator, or editor can apply immediately.

The scorer answers:

> Is this video structurally clear for the selected TikTok/TikTok Shop context, what is observable, what is blocked, and what exactly should be edited, reshot, confirmed, or re-uploaded?

## 1.2 Explicit non-goals

TikTok Scorer is not:

- ViralKit.
- Exact Campaign Pack Preflight.
- Performance prediction.
- Viral probability.
- GMV, sales, CTR, CVR, or ROAS prediction.
- A “winning creative” classifier.
- A complete rights/economics decision engine.
- A creator selection engine.
- A generic AI video-review chat response.

Never produce phrases such as:

```text
likely to go viral
viral probability
predicted sales
winning video
expected GMV
guaranteed performance
safe to scale
```

unless those phrases are quoted as prohibited examples.

## 1.3 Mandatory module boundaries

Keep these responsibilities separate:

```text
TikTok Scorer
= pre-publish structural and commerce-aware video diagnostics

UGC Preflight
= exact validation against one specific Campaign Pack/version

Performance Intelligence
= post-launch outcome analysis
```

TikTok Scorer must not import private implementation details from ViralKit or Campaign Pack. Cross-module access must use each module’s `public.py` contract.

TikTok Scorer may optionally hand off to:

- “Use as reference”.
- “Attach product”.
- “Generate Creative Directions”.
- “Run exact Campaign Pack Preflight”.
- “Upload revision”.

It must remain fully functional without ViralKit or Campaign Pack.

---

# 2. Research-backed TikTok semantics to encode

Treat the following as product semantics, not as marketing copy.

## 2.1 Recommendation-system boundary

TikTok recommendations use post-distribution signals such as user interactions, complete views, skips, content information, and user information. Those signals do not exist in a pre-publish video file.

Therefore:

```text
observable creative structure
≠ future distribution
≠ virality
≠ commercial performance
```

Do not train or present this module as a virality predictor.

## 2.2 TikTok 2026 trend context

Encode the 2026 research as contextual guidance, not universal score rules:

### Realness

Prefer diagnostics that recognize:

- genuine product use;
- firsthand creator experience;
- natural speech;
- human context;
- honest limitations;
- credible community language.

Do not equate “low production quality” with authenticity.

### Off-script discovery

TikTok behavior increasingly includes search, comments, follow-on discovery, and adjacent communities.

Implement optional, non-core auxiliary signals:

```text
search_discovery_readiness
community_conversation_potential
trend_relevance
```

These signals must never create a hard blocker and must not alter the stable core score unless a future profile explicitly and transparently opts in.

### Emotional ROI

Expand `offer_clarity` into the seller-facing label:

```text
Value & Offer Clarity
```

Evaluate whether the viewer can understand:

- why the product matters;
- the real-life use case;
- functional value;
- emotional or identity value where applicable;
- the verified offer.

Do not reward generic hype such as “everyone needs this” or “run, don’t walk” without product grounding.

## 2.3 TikTok Creative Codes

Use the following as contextual/platform guidelines:

- vertical 9:16 framing;
- UI-safe placement;
- readable text;
- hook → body → close structure;
- visually understandable movement/editing;
- sound-aware or caption-aware comprehension;
- TikTok-native execution.

Do not convert any one of these into a universal hard blocker unless an official placement requirement or selected profile requires it.

Examples:

- No audio is not automatically a failure when the video is understandable visually or through captions.
- Human presence is not required for a valid hands-only tutorial.
- Trending audio is not required.
- High cut count is not inherently good.
- “Product before 2 seconds” is not a universal law.

## 2.4 Creator-native guidance

Encode these as contextual guidelines:

- preserve the creator’s natural voice;
- avoid word-for-word over-scripting;
- use a natural hook;
- use trends strategically;
- choose the right community;
- allow the story to establish itself when a later reveal is genuinely necessary;
- do not force brand/product insertion before the story premise makes sense.

A late product reveal can be acceptable for `story_led_pov_v1`, while the same timing can be weak for `product_led_demo_v1`.

## 2.5 Search and discovery

When the request includes any of:

```text
target_query
target_buyer_question
selected_search_topic
content_gap_topic
```

evaluate:

- spoken query alignment;
- overlay/query alignment;
- whether the question is answered;
- product/category vocabulary;
- comment-reply suitability.

Without those inputs:

```text
search_discovery_readiness.status = "not_evaluated"
```

Do not infer search demand from the video alone.

## 2.6 Commerce and claim consistency

Official commerce rules and verified Product Context may create hard blockers for:

- wrong product or SKU;
- wrong personalization;
- false or misleading demonstration;
- product/listing mismatch;
- price or promotion mismatch;
- unauthorized urgency;
- false shipping/delivery statement;
- unsupported product claim;
- missing required disclosure;
- deceptive before/after proof.

Missing Product Context must produce `unknown` or `not_applicable`, not a fabricated verdict.

## 2.7 Disclosure behavior

Commercial relationships and material connections require clear, conspicuous disclosure when applicable.

The scorer may evaluate visible/spoken disclosure only when:

- intended use or commercial relationship is known; or
- Product Context/domain policy declares it required.

A platform disclosure toggle must not automatically be treated as sufficient visual/spoken disclosure.

## 2.8 Agency and creator-production research

Use these implementation lessons:

### Modular UGC

Recognize reusable building blocks:

- hooks;
- B-roll;
- product close-ups;
- demo clips;
- proof clips;
- CTA clips;
- raw footage.

The Fix Planner should prefer reordering/reusing verified existing footage before requiring a reshoot.

### Controlled testing

Separate:

```text
message angle
creative mechanic
hook tactic
psychological trigger
visual format
creator persona
narrative sequence
demo mechanism
proof mechanism
offer framing
CTA strategy
```

Do not call all of these “the hook”.

### Trend/reference evidence

A trend, long-running ad, popular sound, or reference asset is a directional signal, not proof of causality or a “winner”.

---

# 3. Research evidence hierarchy and policy-pack model

Implement or extend a versioned source/evidence classification:

```text
A_OFFICIAL
B_CORROBORATED
C_COMMUNITY_SIGNAL
D_INTERNAL_HYPOTHESIS
```

Rule classes:

```text
official_hard_rule
product_governance_rule
operational_hard_constraint
contextual_guideline
directional_pattern
seller_preference
```

Only these may automatically create hard blockers:

```text
official_hard_rule
product_governance_rule
operational_hard_constraint
```

`contextual_guideline`, `directional_pattern`, `C_COMMUNITY_SIGNAL`, and `D_INTERNAL_HYPOTHESIS` must not create an automatic hard blocker without independent supporting evidence.

Create or extend versioned domain packs for:

```text
tiktok_us_official_policy_pack
tiktok_us_creative_guideline_pack
tiktok_2026_trend_overlay
ftc_endorsement_pack
pod_personalization_pack
dropshipping_product_truth_pack
ugc_creator_workflow_pack
agency_directional_pattern_pack
```

Every rule must preserve:

- rule code;
- pack/version;
- source tier;
- applicability;
- required inputs;
- unknown behavior;
- exceptions;
- whether it can hard-block;
- fix-template code;
- effective and optional expiry dates;
- provenance/source IDs.

Trend overlays need TTL/expiry behavior and must not change the stable score of an already completed run.

Do not inject the full Golden Output document into runtime prompts. Compile it into small versioned rules, templates, fixtures, and evaluation cases.

---

# 4. Required scoring modes

## 4.1 Quick Score

Minimum input:

```text
asset_version_id
score_profile = general_tiktok_v1
```

Product Context is optional.

When Product Context is absent, do not evaluate exact:

- product match;
- product-specific claims;
- offer consistency;
- shipping consistency;
- personalization;
- compatibility;
- product-specific disclosure.

Return typed `unknown` or `not_applicable`.

## 4.2 Product-Aware Score

Input:

```text
asset_version_id
product_id
immutable Product Context snapshot
score profile
```

Add checks for:

- product identity/variant;
- product mechanism;
- benefit consistency;
- offer consistency;
- claim governance;
- disclosure;
- personalization;
- compatibility;
- shipping statement.

Persist the immutable Product Context snapshot/hash used by the run.

## 4.3 Usage-Aware Score

Input includes:

```text
intended_use:
- tiktok_organic
- tiktok_shop_affiliate
- ugc_paid_candidate
- spark_candidate
```

Creative and paid-use readiness must remain separate:

```text
Creative structure: ready
Paid-use rights: not_evaluated
Final paid readiness: pending_rights_confirmation
```

TikTok Scorer must not mark rights complete or recommend a paid test.

---

# 5. Content archetypes and score profiles

Implement a typed content-archetype/profile layer.

Required initial profiles:

```text
general_tiktok_v1
product_led_demo_v1
creator_review_v1
story_led_pov_v1
tutorial_howto_v1
unboxing_reaction_v1
comment_reply_faq_v1
offer_led_shop_v1
```

The model may suggest a profile, but the user must be able to confirm or override it.

Persist:

```json
{
  "profile_code": "story_led_pov_v1",
  "selection_mode": "model_suggested_user_confirmed",
  "confidence": 0.86,
  "alternative_profiles": ["creator_review_v1"],
  "evidence_ids": ["..."]
}
```

A low-confidence profile classification must not create a hard blocker.

Profile behavior examples:

### product_led_demo_v1

Prioritize:

- early product grounding;
- mechanism;
- product-in-use;
- observable proof.

### story_led_pov_v1

Allow:

- a necessary story setup;
- a later reveal when the story and product converge clearly.

Do not fire a generic “product too late” blocker solely from a global timing threshold.

### tutorial_howto_v1

Prioritize:

- ordered steps;
- product visibility during key steps;
- audio/caption comprehension;
- safe, accurate usage.

### unboxing_reaction_v1

Allow packaging before product reveal, but require the real item to become clear.

### comment_reply_faq_v1

Allow the question/comment to open the video. Do not treat a generated/fabricated comment as real social proof.

Seed profile weights and decision thresholds as versioned beta configuration, not as market truth. Tests should assert action bands and relative changes rather than overfit a single exact total score.

---

# 6. Core scoring dimensions

Keep these nine dimensions:

```text
hook_clarity
product_visibility
demo_clarity
proof_strength
creator_authenticity
offer_clarity
cta_readiness
tiktok_native_fit
claim_safety
```

Seller-facing label for `offer_clarity`:

```text
Value & Offer Clarity
```

Each dimension must return a typed contract similar to:

```python
class TikTokDimensionResultV2(BaseModel):
    code: str
    label: str
    score: int | None
    applicability: Literal["applicable", "not_applicable", "unknown"]
    evidence_status: Literal["sufficient", "partial", "insufficient"]
    confidence: Literal["high", "medium", "low"]
    reason: str
    positive_signals: list[str]
    missing_signals: list[str]
    uncertainty: list[str]
    evidence_ids: list[UUID]
    contributing_rule_codes: list[str]
```

Rules:

- `score` must be `null` when not applicable or not responsibly scoreable.
- Missing evidence must not become score zero.
- Confidence must remain separate from score.
- The overall score must be calculated in deterministic code.
- LLM output must never be the final numerical score.
- Hard blockers may override the decision band without pretending every blocker makes the structural score zero.

Suggested aggregation:

```python
eligible = [
    d for d in dimensions
    if d.applicability == "applicable"
    and d.evidence_status != "insufficient"
    and d.score is not None
]

overall_score = weighted_average(eligible, profile.weights)
```

Confidence aggregation should use:

- media coverage;
- ASR confidence;
- OCR confidence;
- visual quality;
- Product Context completeness;
- evidence lineage validity;
- extractor agreement;
- unresolved rule conflicts.

Do not calculate:

```text
score × confidence
```

---

# 7. Decision model

Implement deterministic decision precedence:

```text
1. critical evidence unavailable
   -> request_better_media

2. verified official/product-truth hard blocker
   -> blocked

3. one or more P0 required fixes
   -> revise

4. profile thresholds satisfied
   -> structurally_ready

5. otherwise
   -> usable_with_improvements
```

Required output separation:

```text
creative_structure_decision
paid_use_rights_status
final_paid_readiness
```

Possible creative decisions:

```text
request_better_media
blocked
revise
usable_with_improvements
structurally_ready
```

Do not expose “approve for paid scaling” from this module.

---

# 8. Evidence and Scene Inventory

Re-use the existing asset/media/evidence pipeline. Do not duplicate it.

The prior audit indicates the repository may already have:

- ffprobe/ffmpeg metadata and frame extraction;
- ASR;
- OCR;
- evidence persistence;
- deterministic TikTok scoring;
- versioned rules;
- hard blockers;
- recommendation records;
- worker job `score_tiktok_asset`.

Re-verify these components and extend them instead of replacing them.

Implement a typed temporal scene inventory:

```python
class VideoSceneV1(BaseModel):
    scene_id: UUID
    start_ms: int
    end_ms: int
    summary: str
    shot_type: str | None

    product_visible: bool | None
    product_match_confidence: float | None
    product_visibility_quality: str | None

    spoken_text: str | None
    overlay_texts: list[str]

    demo_step: str | None
    proof_role: str | None
    creator_present: bool | None

    visual_quality: Literal[
        "good",
        "usable",
        "dark",
        "blurry",
        "obscured",
        "unknown"
    ]

    continuity_group_id: UUID | None
    reusable_for_edit: bool
    evidence_ids: list[UUID]
```

`SceneInventoryV1` should include:

- asset version;
- duration;
- audio availability;
- scene list;
- ASR coverage;
- OCR coverage;
- product appearance ranges;
- CTA ranges;
- disclosure ranges;
- safe-zone observations;
- continuity groups;
- overall coverage/confidence;
- extractor/model versions.

Do not fabricate a scene, timestamp, transcript, overlay, product match, or continuity group.

When extraction is uncertain:

```text
unknown
partial
request_better_media
expert_review
```

are valid outcomes.

---

# 9. Finding contract

Implement typed findings:

```python
class TikTokFindingV2(BaseModel):
    id: UUID
    code: str
    rule_code: str
    rule_class: str
    source_dimension: str

    severity: Literal["hard", "high", "medium", "low", "info"]
    priority: Literal["P0", "P1", "P2", "P3"]

    applicability: Literal["applicable", "not_applicable", "unknown"]
    evidence_status: Literal["sufficient", "partial", "insufficient"]

    title: str
    reason: str
    expected: dict[str, object]
    observed: dict[str, object]

    target_time_range_ms: tuple[int, int] | None
    evidence_ids: list[UUID]
    uncertainty: list[str]

    requires_seller_truth: bool
    can_be_resolved_by_edit: bool | None
    requires_physical_reshoot: bool | None
```

Every finding must be evidence-linked.

No raw rule code should be the primary seller-facing title.

---

# 10. Detailed Fix Planner

This is the center of the feature.

Do not return generic recommendations such as:

```text
Improve the hook.
Show the product earlier.
Add a stronger CTA.
```

Every important finding must compile into a typed action.

## 10.1 Video edit operations

```python
class VideoEditOperationV1(BaseModel):
    operation: Literal[
        "move_clip",
        "trim_clip_start",
        "trim_clip_end",
        "split_clip",
        "insert_existing_clip",
        "extend_readable_hold",
        "add_overlay",
        "replace_overlay",
        "remove_overlay",
        "replace_spoken_line",
        "preserve_clip"
    ]

    source_scene_id: UUID | None
    source_range_ms: tuple[int, int] | None
    target_start_ms: int | None
    target_duration_ms: int | None

    text_value: str | None
    evidence_ids: list[UUID]

    feasibility: Literal[
        "verified_possible",
        "likely_possible",
        "requires_editor_confirmation"
    ]
```

## 10.2 Fix action contract

```python
class TikTokFixActionV1(BaseModel):
    id: UUID
    code: str

    recommendation_class: Literal[
        "required_fix",
        "high_priority_improvement"
    ]

    basis: Literal[
        "official_rule",
        "product_governance",
        "operational_constraint",
        "score_profile",
        "contextual_guideline",
        "video_diagnosis"
    ]

    priority: Literal["P0", "P1", "P2"]
    severity: Literal["hard", "high", "medium", "low"]

    source_dimension: str
    owner_role: Literal[
        "seller",
        "creator",
        "editor",
        "compliance_reviewer"
    ]

    fix_type: Literal[
        "edit_existing_footage",
        "trim_or_reorder",
        "add_overlay",
        "replace_overlay_copy",
        "replace_spoken_line",
        "reshoot_scene",
        "add_missing_scene",
        "confirm_seller_input",
        "confirm_rights",
        "request_better_media"
    ]

    title: str
    why_it_matters: str

    expected: dict[str, object]
    observed: dict[str, object]
    evidence_ids: list[UUID]

    target_time_range_ms: tuple[int, int] | None
    video_operations: list[VideoEditOperationV1]

    instructions: list[str]
    strengths_to_preserve: list[str]
    required_inputs: list[str]

    estimated_effort: Literal["low", "medium", "high"]
    reshoot_required: bool

    completion_criteria: list[str]
    verification_method: str
```

Every fix must answer:

1. What is wrong?
2. Where does it occur?
3. Why does it matter in this profile/product/use context?
4. Can existing footage fix it, or is a reshoot required?
5. What exact change should be made?
6. How will the system verify completion?

## 10.3 Edit-versus-reshoot resolver

Use this precedence:

```text
insufficient evidence
-> request better media

missing seller truth
-> confirm seller input

verified reusable scene + reorder solves finding
-> trim/reorder existing footage

verified reusable scene + overlay/copy change solves finding
-> edit existing footage

physical product truth/proof absent
-> reshoot scene

required scene does not exist
-> add missing scene

otherwise
-> editor review / creator reshoot as applicable
```

Never suggest `move_clip` or `insert_existing_clip` unless the source scene exists and has evidence.

Prefer the least expensive valid correction.

## 10.4 Fix taxonomy

Editable examples:

- reorder existing footage;
- trim dead air;
- move CTA;
- add a verified disclosure;
- replace unsafe copy;
- extend a readable product shot.

Reshoot examples:

- wrong product/SKU;
- wrong personalization;
- product mechanism absent;
- product never shown in use;
- proof cannot be verified;
- before/after uses incomparable objects/scenes;
- critical physical scene does not exist.

Seller confirmation examples:

- offer;
- shipping time;
- compatibility;
- supported materials;
- approved disclosure wording;
- rights;
- intended use.

Insufficient-evidence examples:

- dark or blurry footage;
- product obscured;
- low OCR/ASR confidence;
- multiple products with uncertain mapping;
- incomplete upload;
- missing duration.

Insufficient evidence is not creative failure.

---

# 11. Optional ViralKit / Creative Direction enrichment

ViralKit may improve recommendations, but it must not become a scoring dependency.

Canonical separation:

```text
Score
= diagnosis of the current video

Required Fix
= minimum valid repair grounded in existing evidence

Creative Direction Upgrade
= optional product-specific improvement inspired by a compatible selected direction
```

Add an optional request field:

```text
creative_direction_context_id
```

Retrieve it only through the ViralKit/Creative Directions public contract.

Use a small immutable snapshot:

```python
class CreativeDirectionContextV1(BaseModel):
    source_type: Literal["viral_kit"]
    source_id: UUID
    source_version: int
    concept_id: UUID

    product_snapshot_hash: str
    objective: str | None
    market: str | None

    buyer_context: dict[str, object]
    message_angle: str
    hook_mechanism: str
    narrative_sequence: list[str]
    demo_mechanism: str | None
    proof_mechanism: str | None
    cta_strategy: str | None

    keep: list[str]
    change: list[str]
    avoid: list[str]

    allowed_claims: list[str]
    prohibited_claims: list[str]
    required_disclosures: list[str]

    expected_learning: str | None
```

Compatibility gate:

- same Product Context snapshot hash;
- compatible market;
- compatible objective/intended use;
- valid source version;
- selected concept not rejected;
- no conflict with current product governance.

Optional upgrade contract:

```python
class CreativeUpgradeSuggestionV1(BaseModel):
    id: UUID
    source_type: Literal["viral_kit"]
    source_id: UUID
    source_version: int
    concept_id: UUID

    affects_score: Literal[False] = False
    recommendation_class: Literal[
        "optional_upgrade",
        "next_iteration_direction"
    ]

    title: str
    why_it_fits: str
    keep_from_current_video: list[str]
    change_in_current_video: list[str]
    additional_footage_needed: list[str]

    suggested_hook_mechanism: str | None
    suggested_narrative_sequence: list[str]
    suggested_demo_mechanism: str | None
    suggested_proof_mechanism: str | None
    suggested_cta_strategy: str | None

    claim_guardrails: list[str]
    evidence_ids: list[UUID]
    expected_learning: str | None
```

Required constraints:

- `affects_score` is always `false`;
- ViralKit may enrich how a fix is executed;
- ViralKit may not create a hard blocker;
- ViralKit may not lower or raise a dimension score;
- Product Context and official governance always win;
- if direction service fails, the score and required fixes still complete successfully.

Seller-facing label:

```text
Based on your selected creative direction
```

Do not expose raw “ViralKit” terminology as the primary UX label.

---

# 12. Auxiliary signals

Add optional non-core outputs:

```python
class TikTokAuxiliarySignalsV1(BaseModel):
    search_discovery_readiness: ...
    community_conversation_potential: ...
    trend_relevance: ...
```

Rules:

- not included in core score by default;
- never hard-block;
- must have `evaluated`, `not_evaluated`, or `directional` status;
- trend data must carry market, observation time, source, and expiry;
- a trending sound or hashtag does not automatically improve the video;
- a long-running reference is a candidate pattern, not a proven winner.

---

# 13. Revision loop and comparison

Support:

```text
Draft 1
→ score
→ fix actions
→ accept/reject/send/complete events
→ upload Draft 2
→ re-score
→ compare
```

Persist AI output, seller action, and revision outcome separately.

Required fix-action events:

```text
viewed
accepted
rejected
sent_to_creator
sent_to_editor
marked_completed
verified_after_revision
```

Comparison contract must include:

```text
resolved blockers
unresolved blockers
new regressions
dimension changes
evidence before/after
strengths preserved
actions verified
final next action
```

Do not return only:

```text
68 -> 84
```

Verification must be action-level:

```text
Action: move product close-up earlier
Before: 4200ms
After: 900ms
Status: verified
```

Also detect regressions, such as:

```text
CTA moved into unsafe UI zone
disclosure removed
strong creator delivery lost
wrong SKU introduced
```

---

# 14. Database and persistence

Audit the current schema and implement migrations using repository conventions.

Required logical entities:

```text
tiktok_score_profiles
tiktok_score_runs
tiktok_score_dimensions
tiktok_score_findings
tiktok_fix_actions
tiktok_fix_action_events
tiktok_score_comparisons
```

Persist or link the scene inventory through the existing evidence/artifact model. Add a dedicated table only if the repository’s current persistence pattern requires it.

Each score run must preserve:

- workspace;
- asset and immutable asset version;
- score mode;
- intended use;
- selected profile/version;
- profile selection mode/confidence;
- Product Context snapshot/hash when applicable;
- policy-pack versions;
- rule versions;
- prompt versions;
- model/provider versions;
- media checksum;
- direction-context snapshot/version when used;
- score;
- confidence;
- decision;
- created/completed timestamps;
- latency;
- token usage/cost estimate;
- failure code when applicable.

Do not overwrite completed score runs.

Use migrations, not ad-hoc table creation.

---

# 15. API contract

Implement or version routes consistent with repository conventions:

```text
POST /api/v1/workspaces/{workspace_id}/tiktok-scores
GET  /api/v1/workspaces/{workspace_id}/tiktok-scores
GET  /api/v1/workspaces/{workspace_id}/tiktok-scores/{score_id}

GET  /api/v1/workspaces/{workspace_id}/tiktok-scores/{score_id}/fixes

POST /api/v1/workspaces/{workspace_id}/tiktok-scores/{score_id}/fixes/{fix_id}/actions

POST /api/v1/workspaces/{workspace_id}/tiktok-scores/{score_id}/revisions

GET  /api/v1/workspaces/{workspace_id}/tiktok-scores/{score_id}/comparisons/{comparison_id}

GET  /api/v1/workspaces/{workspace_id}/tiktok-score-profiles
```

Create request example:

```json
{
  "asset_version_id": "uuid",
  "product_id": null,
  "score_mode": "quick",
  "score_profile": "general_tiktok_v1",
  "intended_use": "tiktok_organic",
  "creative_direction_context_id": null,
  "idempotency_key": "..."
}
```

Requirements:

- Product is not mandatory for Quick Score.
- Use idempotency.
- Do not create orphan runs on retry.
- Return job/run status consistently with existing worker architecture.
- Preserve backward compatibility where practical.
- If a response schema must change incompatibly, version it rather than silently breaking clients.

---

# 16. Worker and AI runtime

Re-use the existing job system.

Implement a versioned job flow, for example:

```text
validate_input
load_media_evidence
build_scene_inventory
suggest_or_load_profile
evaluate_rules
compute_dimensions
compute_score_and_decision
compile_fix_actions
optionally_enrich_from_direction
validate_output
persist_result
emit_events
```

AI architecture:

```text
deterministic media facts
→ typed semantic observations
→ deterministic rule evaluation
→ deterministic scoring
→ rule-based fix skeleton
→ bounded LLM wording/enrichment
→ strict validation
```

LLM may:

- summarize a scene;
- classify semantic creative structure;
- explain a finding in seller-friendly language;
- render a validated fix skeleton into natural instructions;
- write a creator/editor message;
- identify optional creative-direction upgrades.

LLM may not:

- choose the final numerical score;
- change severity;
- invent expected values;
- invent product facts;
- invent rights;
- invent timestamps;
- change approved disclosure wording;
- mark a blocker resolved;
- create a paid-test recommendation;
- claim performance.

Use strict typed output and one bounded schema-repair attempt.

Do not retry merely because prose is not “impressive”.

Runtime prompt rules:

- one canonical system prompt;
- one operation prompt;
- retrieve only applicable rules, Product Context fields, evidence, fix templates, and at most 1–2 relevant few-shot examples;
- never send the full Golden Output file;
- cache immutable artifacts by input hash;
- record prompt/model/schema version, latency, tokens, and cost.

---

# 17. Frontend implementation — mandatory standalone product module

TikTok Scorer must be implemented as a **first-class product module with its own navigation, routes, upload flow, result workspace, revision lifecycle, and history**.

It is not acceptable to implement only:

- a sidebar link;
- a static score mockup;
- a modal inside Creative DNA;
- a tab inside Campaign Pack;
- a tab inside UGC Preflight;
- a fixture-only frontend disconnected from backend jobs;
- a result card embedded in another module.

The frontend task is incomplete unless a seller can enter TikTok Scorer from the main navigation, submit a real video-analysis job, review evidence-linked fixes, upload a revision, and compare versions end to end.

## 17.1 Navigation contract

Add a permanent first-class navigation item:

```text
TikTok Scorer
```

Recommended main-navigation position:

```text
Dashboard
Products
Creative Library
TikTok Scorer
Creative Directions
Creator Briefs
UGC Preflight
Performance
```

Requirements:

- do not hide TikTok Scorer under Creative Library, Creative DNA, Campaign Pack, or UGC Preflight;
- provide correct active, hover, collapsed-sidebar, keyboard-focus, and mobile/tablet navigation states;
- preserve the existing dashboard shell, design tokens, route guards, workspace scope, permissions, and responsive behavior;
- keep unrelated navigation entries and pages functional;
- use seller-facing terminology; do not expose `PatternKit`, raw `ViralKit`, matcher IDs, or rule codes as primary navigation or page labels.

## 17.2 Mandatory route contract

Implement these canonical route shapes:

```text
/tiktok-scorer
/tiktok-scorer/new
/tiktok-scorer/{scoreId}
/tiktok-scorer/{scoreId}/compare/{comparisonId}
```

If the repository requires a workspace prefix, preserve the same route suffixes under the workspace route, for example:

```text
/workspaces/{workspaceId}/tiktok-scorer
/workspaces/{workspaceId}/tiktok-scorer/new
/workspaces/{workspaceId}/tiktok-scorer/{scoreId}
/workspaces/{workspaceId}/tiktok-scorer/{scoreId}/compare/{comparisonId}
```

Do not replace the route contract with one generic page controlled only by query parameters.

### `/tiktok-scorer`

Purpose:

```text
Module landing page + score-run history + recurring workspace utility
```

Must include:

- page title and concise value proposition;
- primary CTA: `Score a video`;
- recent analyses;
- search and filters for status, mode, profile, product, intended use, decision, and date;
- sortable columns or cards for video, product, score mode, profile, decision, confidence, run status, revision count, and last updated time;
- clear processing, completed, partial-evidence, and failed states;
- empty state that explains Quick Score and Product-Aware Score without requiring a product first;
- retry or resume action where backend semantics allow it;
- direct links into result and comparison pages;
- pagination or virtualized loading consistent with repository conventions;
- no fake history data in production mode.

### `/tiktok-scorer/new`

Purpose:

```text
Create a real score run
```

Required flow:

```text
Upload video
→ choose Quick / Product-Aware / Usage-Aware mode
→ optionally attach product
→ select intended use
→ auto-suggest or select content profile
→ optionally use a selected Creative Direction
→ review analysis settings
→ submit
```

Must include:

- drag-and-drop and file-picker upload;
- supported type, size, duration, and validation feedback;
- upload progress and cancellation behavior where supported;
- immutable asset-version creation through the real asset API;
- explicit mode selection:
  - Quick Score;
  - Product-Aware Score;
  - Usage-Aware Score;
- optional product selector for Quick Score and required product selector for Product-Aware mode;
- intended-use selector:
  - TikTok organic;
  - TikTok Shop affiliate;
  - UGC paid candidate;
  - Spark candidate;
- content-profile suggestion with confidence and user override;
- short explanation of why the suggested profile fits;
- optional seller-facing selector labeled `Use a Creative Direction`, not `Attach ViralKit`;
- compatibility warning when the selected direction is stale or incompatible;
- clear notice that the scorer does not predict virality, GMV, sales, CTR, CVR, or ROAS;
- validation that blocks submission only for genuinely required inputs;
- no requirement to create a product before using Quick Score;
- submission through the real backend route and job system;
- redirect to the created result route immediately after successful creation.

### `/tiktok-scorer/{scoreId}`

Purpose:

```text
Processing state + decision workspace + evidence-linked detailed fix plan + revision actions
```

This page must support both in-progress and completed runs.

Processing states must represent real backend/job states, including where applicable:

```text
uploading
queued
extracting_media
building_evidence
scoring
compiling_fixes
completed
partial_evidence
failed
cancelled
```

Do not show a fake progress percentage unless the backend exposes meaningful progress. Use stage-based progress when exact percentages are unavailable.

Completed result hierarchy:

1. Decision banner.
2. Overall structural score and confidence.
3. Score mode, intended use, profile used, and why.
4. Creative readiness separated from paid-use rights/readiness.
5. Strengths to preserve.
6. Hard blockers.
7. Dimension breakdown.
8. Detailed fix plan.
9. Evidence timeline and video player.
10. `Fix with current footage` group.
11. `Needs creator reshoot` group.
12. `Needs seller confirmation` group.
13. `Request better media` group when evidence is insufficient.
14. Optional `Make this version stronger` section from compatible Creative Direction context.
15. Creator/editor message.
16. Fix-action event controls.
17. Upload revision.
18. Revision history and compare entry points.

Required interactions:

- clicking a dimension, finding, or fix jumps the video player to the relevant timestamp;
- evidence preview shows the source type, time range, transcript/OCR/frame summary, and confidence;
- expected and observed values are visually separated;
- badges distinguish edit, reshoot, seller input, insufficient evidence, owner, effort, severity, and priority;
- accept, reject, send to creator, send to editor, mark completed, and verification events call real APIs;
- accepted/rejected/completed states survive refresh;
- technical rule codes may appear only in a secondary diagnostic/details view;
- Quick Score clearly labels product-specific checks as `Not evaluated` rather than failed;
- insufficient evidence is presented as uncertainty or a media request, not a creative-quality zero;
- optional creative upgrades are visually separated from mandatory fixes and always state that they do not change the current score;
- product facts, approved claims, and disclosures are never editable through free-form AI copy controls on this page;
- the user can copy or export a creator/editor message without losing the structured fix actions behind it.

## 17.3 Video and evidence workspace

Implement a usable review workspace rather than a report-only page.

Minimum behavior:

- 9:16-aware video player with normal playback controls;
- click-to-seek from evidence, dimension, finding, and fix cards;
- visible current timestamp and selected evidence range;
- markers or segments for hook, product appearance, demo, proof, offer, CTA, disclosure, and detected issue ranges when evidence exists;
- no claim that a segment exists when the corresponding evidence is absent;
- readable transcript/OCR snippets tied to time ranges;
- frame preview for visual evidence where the shared evidence API supports it;
- graceful handling of video without audio, failed OCR, dark media, partial extraction, or unavailable thumbnails;
- safe-zone overlay only when supported by evidence/profile semantics and clearly labeled as a review aid;
- no duplicated frontend-side media analysis or timestamp inference.

Use shared asset, media, and evidence contracts. Do not reimplement extraction logic in the browser.

## 17.4 Detailed fix-plan presentation

Fix cards must render the typed `TikTokFixActionV1` contract, not flatten it into generic prose.

Each card must expose:

```text
Priority and severity
Owner
Fix type
Why it matters
Expected
Observed
Evidence
Target time range
Exact instructions
Strengths to preserve
Required inputs
Effort
Reshoot required
Completion criteria
Verification method
Current action state
```

Group actions by execution cost and ownership:

```text
Fix with current footage
Needs creator reshoot
Needs seller confirmation
Needs better media
```

The page must make the cheapest valid repair path obvious.

Do not display all fixes as equal-weight checklist items. P0/P1 actions and hard blockers must have stronger visual hierarchy than optional P2 improvements.

## 17.5 Creator/editor message behavior

Generate or render a seller-friendly handoff message from validated structured actions.

Requirements:

- preserve the underlying fix/action IDs;
- include exact actionable changes without exposing internal rule codes;
- retain strengths to preserve;
- do not introduce new claims, disclosures, rights, timestamps, or product facts;
- allow copy and explicit `Send to creator` / `Send to editor` events where the existing product supports those actions;
- log the action event separately from the AI-generated message;
- do not mark an action completed merely because a message was copied or sent.

## 17.6 Revision upload and lifecycle

From a completed score page, the seller must be able to:

```text
Upload Draft 2
→ create immutable new asset version
→ launch a new score run with inherited context/profile
→ create a comparison
→ review action-level verification
```

Requirements:

- show which settings will carry forward;
- allow an explicit profile override while retaining audit history;
- preserve the prior score run and prior evidence unchanged;
- prevent overwriting Draft 1;
- link every revision to its parent score run and accepted fix actions;
- show upload, processing, partial-evidence, retry, and failure states;
- allow more than one revision over time without losing previous comparisons.

## 17.7 `/tiktok-scorer/{scoreId}/compare/{comparisonId}`

Purpose:

```text
Draft-to-draft verification, not merely a score delta
```

Must show:

- Draft 1 and Draft 2 identity and playback access;
- overall and per-dimension score changes;
- resolved blockers;
- unresolved blockers;
- new regressions;
- accepted actions verified or not verified;
- evidence before and after;
- strengths preserved;
- profile/context changes, if any;
- final next action;
- clear warning when a comparison is not like-for-like because profile, Product Context, or intended use changed.

Do not reduce this page to:

```text
71 → 84
```

The primary summary must explain whether mandatory actions were resolved and whether the revised draft introduced new problems.

## 17.8 Required UI states

Every route must handle its applicable states explicitly:

```text
loading
empty
uploading
queued
processing
partial evidence
completed
failed
permission denied
not found
stale data
network retry
```

Rules:

- never render a completed-looking score from stale fixture data while a real job is pending;
- never hide a partial-evidence state behind a generic success banner;
- preserve server errors and actionable retry guidance;
- avoid infinite spinners;
- use route-level error boundaries consistent with the repository;
- unauthorized workspace data must never be fetched or rendered.

## 17.9 Backend integration requirements

The frontend must use real backend APIs and typed contracts for:

- asset upload and immutable asset version;
- score-run creation;
- score-run status;
- dimensions and findings;
- evidence retrieval;
- fix actions;
- fix-action events;
- revision creation;
- comparison retrieval;
- optional compatible Creative Direction context.

Requirements:

- reuse the repository’s API client, query/cache layer, authentication, workspace scoping, and error conventions;
- do not create a parallel ad-hoc fetch layer for this module;
- use generated/shared types when the repository supports them;
- invalidate or update caches after action events and revision creation;
- use polling, subscriptions, SSE, or websocket behavior only according to existing architecture;
- stop polling terminal states;
- protect against duplicate submissions and accidental double score-run creation;
- preserve idempotency keys where the API supports them;
- no fixture-only or local-state-only production workflow.

## 17.10 Layout, responsive behavior, and accessibility

Requirements:

- preserve the existing Viraldy design system and dashboard shell;
- support production desktop and tablet layouts;
- provide a usable narrow layout for smaller screens without promising a full video-editing experience on mobile;
- avoid nested scrolling, clipped timelines, fixed-height overflow, and hidden action controls;
- keep the primary page scroll on the document unless the existing shell intentionally owns it;
- keep sticky panels from covering evidence or CTA controls;
- use accessible labels, keyboard focus, semantic headings, and sufficient contrast;
- do not rely on color alone for blocker, warning, success, or confidence meaning;
- provide tooltips or plain-language help for confidence, applicability, profile, and `Not evaluated` states;
- preserve stable visual hierarchy when evidence or optional sections are absent.

## 17.11 Seller-facing language

Use direct, friendly, operational language for a US-market seller/operator.

Prefer:

```text
Move the existing product close-up earlier
Needs a creator reshoot
Waiting for shipping confirmation
Product-specific checks were not evaluated
Based on your selected Creative Direction
```

Avoid primary UI labels such as:

```text
matcher_failed
rule_code_173
ViralKit enrichment
semantic adjudication pending
model confidence tensor
```

Technical details may exist in an expandable diagnostics panel for debugging and auditability.

## 17.12 Product events and analytics

Track at minimum:

```text
tiktok_scorer_opened
tiktok_score_started
tiktok_score_completed
tiktok_score_failed
tiktok_finding_viewed
tiktok_evidence_opened
tiktok_fix_accepted
tiktok_fix_rejected
tiktok_fix_sent_to_creator
tiktok_fix_sent_to_editor
tiktok_fix_marked_completed
tiktok_revision_uploaded
tiktok_comparison_viewed
tiktok_action_verified_after_revision
```

Events must include stable workspace, score-run, asset-version, fix-action, mode, profile, and intended-use identifiers where applicable, without placing sensitive media content in analytics payloads.

## 17.13 Frontend acceptance criteria

The frontend implementation is complete only when all of the following are true:

1. `TikTok Scorer` is visible as a permanent main-navigation module.
2. All four canonical route shapes exist and are directly navigable.
3. A real Quick Score can be created without a product.
4. A real Product-Aware or Usage-Aware run can be created with the required context.
5. Processing state comes from the backend job, not a simulated timer.
6. The result page renders typed dimensions, findings, evidence, and fix actions.
7. Clicking evidence or a fix seeks the player to a valid server-provided timestamp.
8. Fix actions are grouped into edit, reshoot, seller-confirmation, and better-media paths.
9. Action events persist after refresh.
10. Optional Creative Direction recommendations are clearly separated and cannot alter score display.
11. A revision creates a new immutable asset version and score run.
12. The compare route shows resolved, unresolved, and regression states with before/after evidence.
13. Loading, empty, partial-evidence, failed, permission, and not-found states are implemented.
14. No raw matcher or rule code is shown as the primary seller-facing diagnosis.
15. No nested-scroll, clipping, or route-shell regression is introduced.
16. Existing unrelated frontend pages and navigation remain functional.
17. Frontend tests, type checks, lint, and production build pass.

---

# 18. Tests and evaluation

## 18.1 Required golden cases

Add fixtures/tests for:

- generic TikTok video;
- TikTok Shop product demo;
- product-led demo;
- story-led POV with valid later reveal;
- creator review;
- tutorial/how-to;
- unboxing/reaction;
- comment reply;
- POD personalization;
- dropshipping visual demo;
- video without audio;
- dark/blurry video;
- missing product;
- wrong product/SKU;
- missing CTA;
- unsupported claim;
- missing disclosure;
- personalization mismatch;
- incomparable before/after;
- revision resolving blockers;
- revision introducing a regression;
- compatible ViralKit enrichment;
- incompatible/outdated ViralKit ignored;
- direction service failure while core scoring still succeeds.

## 18.2 Unit-test requirements

Test:

- `unknown` and `not_applicable` are excluded from score aggregation;
- confidence is separate from score;
- hard blocker overrides decision band;
- story-led late reveal does not trigger a universal blocker;
- product-led timing requirement is profile-specific;
- missing audio can still produce valid visual diagnostics;
- insufficient evidence never becomes a zero score;
- product mismatch requires reshoot;
- missing seller truth requests confirmation;
- fix operation never references a missing scene;
- optional direction never changes score;
- required fixes survive direction-service failure;
- all evidence IDs exist;
- timestamps stay within video duration;
- no full Golden Output text appears in runtime prompt fixtures.

## 18.3 Contract and integration tests

Test:

- create/list/get score;
- idempotent retry;
- worker success/failure;
- Product Context snapshot immutability;
- profile/version persistence;
- fix events;
- revision creation;
- comparison output;
- API backward compatibility where promised;
- fixture and live-mode failure handling;
- invalid provider output and bounded repair.

## 18.4 Frontend tests

Test route-level and interaction behavior for:

- `/tiktok-scorer` history, filtering, empty, processing, completed, and failed states;
- `/tiktok-scorer/new` Quick Score without product;
- Product-Aware Score and required Product Context behavior;
- Usage-Aware intended-use separation;
- profile suggestion and override;
- duplicate-submit protection;
- real processing-stage rendering;
- evidence jump and valid video seek;
- evidence preview and partial-evidence behavior;
- fix grouping;
- action events persisted after refresh;
- creator/editor message actions;
- revision upload creating a new immutable asset version;
- compare route with resolved, unresolved, regression, and preserved-strength states;
- comparison warning when profile/context changed;
- optional creative-upgrade section;
- technical codes not shown as primary labels;
- loading, permission-denied, not-found, stale-data, and network-retry states;
- responsive dashboard layout without nested-scroll or clipping regressions;
- unrelated navigation and pages remain functional.

## 18.5 Evaluation metrics

Instrument:

```text
schema_valid_rate
evidence_validity
timestamp_accuracy
dimension_agreement
blocker_precision
blocker_recall
false_hard_blocker_rate
fix_action_usefulness
edit_vs_reshoot_agreement
seller_action_agreement
seller_clarity
revision_resolution_accuracy
latency
cost_per_score
generic_output_rate
```

Golden-set requirements:

- zero fabricated evidence;
- zero out-of-duration timestamps;
- zero false universal “product before 2s” blockers;
- every P0/P1 finding has evidence;
- every required fix has completion criteria;
- every reshoot action explains what to capture;
- optional upgrades always have `affects_score=false`;
- generic-output rate target ≤ 5%;
- creator/editor-message usefulness is prepared for human review.

Do not claim real-world precision/recall until a labeled dataset exists. Build the harness and report measured results honestly.

---

# 19. Implementation phases

Execute in this order.

## Phase 0 — Drift audit and design note

- inspect current backend/frontend/contracts/migrations/tests;
- identify reusable components;
- map old contracts to V2;
- write a concise design/migration note;
- proceed without waiting for another approval.

## Phase 1 — Contracts, profiles, rules, migrations

- V2 contracts;
- score profiles;
- policy-pack/version model;
- database migrations;
- seed initial profiles/rules/fix templates;
- public module interfaces.

## Phase 2 — Evidence and Scene Inventory

- temporal scene inventory;
- coverage/confidence;
- product ranges;
- OCR/ASR ranges;
- continuity;
- reusable-footage flags;
- safe unknown behavior.

## Phase 3 — Deterministic scorer

- profile applicability;
- findings;
- dimension results;
- weighted aggregation;
- confidence;
- blocker override;
- auxiliary signals.

## Phase 4 — Detailed Fix Planner

- finding-to-fix mapping;
- edit/reshoot resolver;
- typed operations;
- strengths preservation;
- completion criteria;
- creator/editor message;
- output validator.

## Phase 5 — Optional creative-direction enrichment

- public contract;
- compatibility gate;
- optional upgrades;
- no score dependency.

## Phase 6 — Revision comparison

- fix events;
- Draft 2 flow;
- action-level verification;
- regression detection;
- strengths-preserved result.

## Phase 7 — Frontend standalone module

- permanent main-navigation item;
- `/tiktok-scorer` history and recurring-workspace page;
- `/tiktok-scorer/new` upload and mode/profile configuration;
- `/tiktok-scorer/{scoreId}` processing and decision workspace;
- evidence-linked video timeline;
- typed fix grouping and action events;
- creator/editor messages;
- immutable revision upload;
- `/tiktok-scorer/{scoreId}/compare/{comparisonId}` action-level comparison;
- real API/job integration;
- loading, empty, partial-evidence, failure, permission, and not-found states;
- responsive/accessibility work;
- route-level frontend tests and production-build verification.

## Phase 8 — Qualification and documentation

- golden fixtures;
- eval harness;
- API docs;
- architecture docs;
- runtime prompt docs;
- migration notes;
- commands and results.

---

# 20. Definition of Done

The task is complete only when:

1. TikTok Scorer is a standalone navigation/module.
2. Quick Score works without Product Context.
3. Product-Aware and Usage-Aware modes preserve immutable context.
4. All nine dimensions return typed applicability, confidence, reasons, and evidence.
5. Overall score is deterministic.
6. Confidence is not multiplied into score.
7. Hard blockers override the decision band correctly.
8. Content profile prevents universal timing mistakes.
9. Missing evidence returns unknown/request-better-media rather than failure.
10. Every P0/P1 finding produces a detailed valid action.
11. Actions correctly distinguish edit, reshoot, seller input, and insufficient evidence.
12. No action references nonexistent footage.
13. Existing strengths are preserved in fix plans and revision checks.
14. ViralKit/Creative Direction enrichment is optional and cannot affect score.
15. A direction-service failure cannot break scoring.
16. Revision comparison verifies individual actions and detects regressions.
17. Product facts and governance beat creative suggestions.
18. Rights remain separate and are never fabricated.
19. Runtime prompts do not contain the full Golden Output document.
20. All four canonical TikTok Scorer frontend route shapes exist and use real backend/job data.
21. The result workspace supports evidence seeking, typed fix groups, persisted action events, and immutable revision upload.
22. The comparison route verifies resolved, unresolved, and regression states rather than showing only score delta.
23. Loading, empty, partial-evidence, failed, permission, not-found, stale-data, and retry states are implemented.
24. The dashboard shell has no nested-scroll, clipping, or responsive-layout regression.
25. All migrations, backend tests, frontend tests, lint/type checks, and production builds pass.
26. Existing unrelated modules and routes remain functional.
27. Documentation lists changed files, architecture decisions, commands run, test results, known limitations, and next calibration needs.

---

# 21. Final response format after implementation

Return:

## A. Current-state verification

- what existed;
- what was reused;
- what changed.

## B. Architecture implemented

- modules;
- contracts;
- data flow;
- rule/AI boundary;
- ViralKit optional boundary.

## C. Database and API changes

- migrations;
- routes;
- backward compatibility.

## D. Frontend changes

- screens;
- flows;
- revision experience.

## E. Tests and qualification

- commands run;
- results;
- golden cases;
- measured limitations.

## F. Files changed

Group by backend, frontend, migration, tests, and docs.

## G. Remaining risks

Be explicit about:

- uncalibrated beta weights;
- weak/absent product recognition;
- provider limitations;
- low-confidence cases;
- missing labeled human-review data.

Do not claim production accuracy, virality prediction, or PMF merely because the implementation passes tests.
