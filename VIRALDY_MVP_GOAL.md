# VIRALDY MVP GOAL
## Codex Goal-Mode Execution Contract

> **Repository:** `dhtphu05/viraldy`  
> **Baseline:** current `main` branch; preserve existing Git history and Alembic history  
> **Primary objective:** complete a usable end-to-end Viraldy MVP before production hardening  
> **Execution style:** continue milestone by milestone until the MVP Definition of Done is satisfied or a genuine external blocker remains  
> **Product scope:** Creative Intelligence MVP with a shared media-evidence pipeline, Quick TikTok Scorer, Creative DNA, Product Adaptation, Campaign Pack, and brief-aware UGC Preflight  
> **Deferred:** deployment, production scaling, large test expansion, CI hardening, performance tuning, billing, platform integrations, and creator-commerce expansion

---

# 0. HOW CODEX MUST USE THIS FILE

This file is the single execution contract for Goal Mode.

Codex must:

1. Read the repository before changing code.
2. Compare the current repository against the assumptions in this file.
3. Preserve existing working behavior and API conventions.
4. Implement the milestones in order.
5. Update the checkboxes and the **Execution Log** at the bottom of this same file.
6. Continue after each milestone instead of stopping to produce another plan.
7. Avoid broad architecture refactors unless required to complete the MVP.
8. Avoid spending the goal on deployment, production hardening, test-coverage expansion, or speculative infrastructure.
9. Never claim a live AI integration works unless it was actually exercised with valid credentials.
10. When credentials are missing, finish the provider adapter, provide a clearly labeled fixture mode, document the exact environment variables, and continue every task that does not require the missing secret.
11. Never silently present fixture outputs as real AI results.
12. Keep all user-visible AI outputs structured, traceable, versioned, and linked to the inputs that produced them.

## Goal-mode behavior

Do not stop after creating schemas, migrations, interfaces, or placeholders.

The goal is finished only when a seller can complete these two flows:

### Flow A — Quick TikTok Scorer

```text
Upload TikTok/UGC video
→ process media
→ extract evidence
→ calculate TikTok Structure Score
→ receive action label
→ receive evidence-backed fixes
```

### Flow B — Full Creative Intelligence Loop

```text
Create/select product
→ create reference board
→ upload reference
→ analyze Creative DNA
→ adapt reference to product
→ generate editable Campaign Pack
→ upload UGC draft
→ run brief-aware UGC Preflight
→ receive score, action, blockers, fixes, and revision message
```

If implementation is blocked by an external provider, Flow A and Flow B must still work in a clearly labeled fixture mode, while the live provider path remains fully wired and documented.

---

# 1. PRODUCT GOAL

Viraldy is not a generic video reviewer, ad generator, or viral predictor.

The MVP must help TikTok Shop US, POD, dropshipping, and cross-border sellers answer:

- What is happening inside this creative?
- Which structural elements are worth learning?
- How should this pattern be adapted to my product without copying it?
- What should I send to a creator?
- Is this creator draft structurally ready?
- Should I approve, revise, reject, test organic, or run a small paid/Spark test?
- What exactly needs to be changed?

The unit of value is not a score by itself.

The unit of value is:

```text
evidence
→ diagnosis
→ action
→ specific fix
```

---

# 2. MVP SCOPE

## 2.1 Must ship

The MVP must include:

1. Existing workspace and product foundation.
2. Reference Boards.
3. Reference records linked to assets and products.
4. Real media processing pipeline.
5. Media artifacts and evidence persistence.
6. Creative DNA Analyzer.
7. Quick TikTok Structure Scorer.
8. Deterministic score calculation.
9. Decision and Fix Engine.
10. Product Adaptation Engine.
11. Versioned Campaign Pack Generator.
12. Brief-aware UGC Preflight.
13. Creator-friendly Revision Copilot.
14. Frontend integration for the complete core flow.
15. Clearly labeled live and fixture analysis modes.
16. Minimal manual smoke verification of the end-to-end flow.

## 2.2 Explicitly deferred

Do not implement these in this goal:

- Cloud deployment.
- Kubernetes.
- Production autoscaling.
- Load testing.
- Large CI/CD redesign.
- Increasing coverage for its own sake.
- Full E2E automation suite.
- Billing and credit metering.
- TikTok Shop OAuth.
- TikTok Ads API.
- Shopify API.
- Meta Ads API.
- Competitor crawler.
- Browser extension.
- Creator marketplace.
- Creator CRM.
- Creator Fit Scorer.
- Sample ROI.
- Rights/Spark tracker as a full module.
- Performance CSV loop.
- Fatigue detection.
- PatternKit Registry.
- ViralKit Registry.
- Fine-tuning.
- Proprietary prediction model.
- Full video editor.
- AI agent/MCP.
- Production observability dashboards.
- Production retention/storage lifecycle work.

Do not delete existing foundation capabilities merely because they are not the focus.

---

# 3. CURRENT REPOSITORY BASELINE

Before implementing, inspect the current source and update this section only if the repository has materially changed.

Expected current backend modules:

```text
identity
workspaces
products
assets
jobs
recommendations
```

Expected current backend behavior:

- FastAPI API under `/api/v1`.
- PostgreSQL source of truth.
- SQLAlchemy and Alembic.
- Workspace-scoped authorization.
- S3-compatible upload using presigned URLs.
- Celery/Redis background jobs.
- `processing_jobs` persisted in PostgreSQL.
- Asset and asset-version foundation.
- Recommendation and recommendation-action foundation.
- Existing API response envelope.
- Current processing task is still a foundation placeholder.
- Current model gateway is disabled or placeholder-only.

Expected current frontend:

- React/Vite/TanStack frontend.
- Existing Viraldy design system and screens.
- Most feature data still comes from mocks.
- Backend integration is incomplete.

## Baseline rule

Do not create another repository.

Do not re-run another architecture refactor.

Do not rewrite the current foundation.

Build the product modules on top of the current Lean Modular Monolith.

---

# 4. ARCHITECTURE GUARDRAILS

Use the existing feature-module convention.

A normal module should look like:

```text
modules/<feature>/
├── models.py
├── schemas.py
├── repository.py
├── service.py
├── router.py
├── public.py          # only when another module needs it
├── tasks.py           # only when background work exists
├── validators.py      # only when meaningful
├── rules.py           # only when meaningful
├── scorer.py          # only for scoring modules
├── taxonomy.py        # only for taxonomy-owning modules
└── exceptions.py
```

## Keep these rules

- Routers remain thin.
- Business logic lives in services/rules/scorers.
- Repositories own database queries.
- Every business query is scoped by `workspace_id`.
- Cross-module access uses `public.py`.
- Worker tasks receive stable IDs, not large payloads.
- Binary media stays in object storage.
- Structured results stay in PostgreSQL.
- Existing API response envelopes remain consistent.
- Existing migration history must not be reset.
- New schema changes use new Alembic migrations.
- Existing auth/workspace behavior must remain intact.
- Existing frontend design system must be preserved.

## Do not introduce

- Generic repository frameworks.
- Command bus.
- Query bus.
- Event sourcing.
- Microservices.
- Kafka.
- Deep DDD folders for every module.
- A single giant `ai_service.py`.
- Business logic inside Celery tasks.
- Scores generated directly by an LLM.
- Unversioned prompt outputs.
- Free-form JSON without Pydantic validation.
- Silent fallback from live mode to fixture mode.

---

# 5. TARGET MVP MODULES

Add only the modules needed for the core product:

```text
modules/
├── reference_boards/
├── references/
├── media_analysis/
├── creative_dna/
├── tiktok_scorer/
├── adaptations/
├── campaign_packs/
└── preflight/
```

Keep existing:

```text
identity
workspaces
products
assets
jobs
recommendations
```

## Module responsibilities

### `reference_boards`

- Create/list/get/update boards.
- Group references by product, campaign direction, or research theme.
- Workspace ownership.
- Basic filtering.

### `references`

- Link a reference asset to a board.
- Optional product link.
- Source URL/platform metadata.
- Notes and title.
- Trigger analysis.
- Expose analysis status and latest Creative DNA.

### `media_analysis`

- Shared media evidence pipeline.
- ffprobe metadata.
- Audio extraction.
- ASR.
- Frame sampling.
- OCR.
- Scene boundaries.
- Thumbnails.
- Normalized artifacts.
- Reusable evidence records.
- No final score.

### `creative_dna`

- Convert normalized media evidence into Creative DNA.
- Version taxonomy.
- Persist versioned DNA.
- Expose evidence-backed observations.
- No generic viral prediction.

### `tiktok_scorer`

- Quick structure score for any TikTok/UGC creative.
- Deterministic weighted scorer.
- Hard blockers.
- Action labels.
- Fix recommendations.
- No brief required.

### `adaptations`

- Combine product context and one or more Creative DNA versions.
- Produce `keep`, `change`, `avoid`.
- Produce three differentiated concepts.
- Persist structured output and provenance.

### `campaign_packs`

- Create a campaign pack from a selected adaptation concept.
- Store structured brief JSON.
- Support editable, immutable versions.
- Preserve prior versions.
- Expose creator-friendly content blocks.

### `preflight`

- Compare a UGC asset against a Campaign Pack version.
- Reuse media artifacts and structural scorer.
- Calculate brief alignment.
- Apply hard blockers.
- Produce final action and revision message.
- Store recommendation.

---

# 6. DATABASE AND MIGRATIONS

Do not rewrite migration `0001_initial_foundation`.

Create new incremental migrations.

## 6.1 `reference_boards`

Fields:

```text
id UUID primary key
workspace_id UUID foreign key
product_id UUID nullable
name varchar
description text nullable
board_type varchar default 'creative_research'
status varchar default 'active'
created_by_user_id UUID
created_at timestamptz
updated_at timestamptz
deleted_at timestamptz nullable
```

Indexes:

```text
workspace_id
product_id
(workspace_id, created_at)
```

## 6.2 `references`

Fields:

```text
id UUID primary key
workspace_id UUID
board_id UUID
product_id UUID nullable
asset_id UUID
source_platform varchar nullable
source_url text nullable
title varchar
notes text nullable
status varchar
created_by_user_id UUID
created_at timestamptz
updated_at timestamptz
deleted_at timestamptz nullable
```

Constraints:

- Asset belongs to same workspace.
- Product, if present, belongs to same workspace.
- Board belongs to same workspace.

## 6.3 `media_artifacts`

Fields:

```text
id UUID primary key
workspace_id UUID
asset_version_id UUID
artifact_type varchar
storage_key text nullable
payload_json JSONB nullable
provider varchar
model_version varchar nullable
analysis_mode varchar
created_at timestamptz
```

Artifact types:

```text
video_metadata
thumbnail
audio
transcript
ocr
sampled_frames
scene_boundaries
visual_observations
```

Rules:

- A file artifact uses `storage_key`.
- A structured artifact uses `payload_json`.
- Either may contain both where useful.
- Do not place large binary content in JSONB.

## 6.4 `evidence_items`

Fields:

```text
id UUID primary key
workspace_id UUID
asset_version_id UUID
analysis_run_type varchar
analysis_run_id UUID nullable
evidence_type varchar
start_ms bigint nullable
end_ms bigint nullable
frame_storage_key text nullable
value_json JSONB
confidence numeric nullable
source varchar
provider varchar nullable
model_version varchar nullable
created_at timestamptz
```

Evidence types:

```text
transcript_segment
on_screen_text
scene_boundary
product_presence
product_first_appearance
hook_signal
demo_signal
proof_signal
offer_signal
cta_signal
creator_signal
claim_signal
platform_signal
brief_requirement
brief_violation
```

Evidence source values:

```text
asr
ocr
vision
rule
user
derived
```

## 6.5 `creative_dna_versions`

Fields:

```text
id UUID primary key
workspace_id UUID
reference_id UUID nullable
asset_version_id UUID
version_number integer
status varchar
dna_json JSONB
confidence varchar
analysis_mode varchar
taxonomy_version varchar
model_version varchar nullable
prompt_version varchar nullable
created_at timestamptz
```

Constraints:

```text
unique(asset_version_id, version_number)
```

Do not overwrite old DNA versions.

## 6.6 `tiktok_score_runs`

Fields:

```text
id UUID primary key
workspace_id UUID
asset_version_id UUID
creative_dna_version_id UUID nullable
status varchar
structural_score numeric
confidence varchar
action_label varchar
dimension_scores_json JSONB
strengths_json JSONB
blockers_json JSONB
fixes_json JSONB
evidence_ids_json JSONB
analysis_mode varchar
rubric_version varchar
rule_version varchar
model_version varchar nullable
created_at timestamptz
```

## 6.7 `adaptation_runs`

Fields:

```text
id UUID primary key
workspace_id UUID
product_id UUID
creative_dna_version_id UUID
objective varchar
target_market varchar
target_buyer_json JSONB
constraints_json JSONB
result_json JSONB
analysis_mode varchar
model_version varchar nullable
prompt_version varchar
created_by_user_id UUID
created_at timestamptz
```

## 6.8 `campaign_packs`

Fields:

```text
id UUID primary key
workspace_id UUID
product_id UUID
adaptation_run_id UUID
status varchar
current_version_id UUID nullable
created_by_user_id UUID
created_at timestamptz
updated_at timestamptz
deleted_at timestamptz nullable
```

## 6.9 `campaign_pack_versions`

Fields:

```text
id UUID primary key
campaign_pack_id UUID
version_number integer
brief_json JSONB
change_note text nullable
created_by_user_id UUID
created_at timestamptz
```

Constraints:

```text
unique(campaign_pack_id, version_number)
```

A new edit creates a new version.

Do not mutate a historical version in place.

## 6.10 `preflight_runs`

Fields:

```text
id UUID primary key
workspace_id UUID
ugc_asset_version_id UUID
campaign_pack_version_id UUID
structural_score_run_id UUID nullable
status varchar
structural_score numeric
brief_alignment_score numeric
preflight_score numeric
confidence varchar
action_label varchar
dimension_scores_json JSONB
brief_alignment_json JSONB
strengths_json JSONB
blockers_json JSONB
fixes_json JSONB
revision_message text
evidence_ids_json JSONB
analysis_mode varchar
rubric_version varchar
rule_version varchar
model_version varchar nullable
created_at timestamptz
```

## 6.11 Existing recommendations

After a TikTok score or Preflight run is completed, create a record in the existing `recommendations` table.

Use:

```text
subject_type = 'tiktok_score_run' or 'preflight_run'
subject_id = run ID
recommendation_type = 'tiktok_structure_decision' or 'ugc_preflight_decision'
action = action label
confidence = low/medium/high
reasoning = short human-readable explanation
evidence_json = evidence references and blockers
model_version = extraction model version
rule_version = scorer rule version
source_run_id = run ID
```

---

# 7. SHARED MEDIA EVIDENCE PIPELINE

Replace the current placeholder processing behavior with a real pipeline.

The media pipeline must be reusable by:

- Creative DNA.
- Quick TikTok Scorer.
- UGC Preflight.

## 7.1 Job types

Add these job types to the existing durable job system:

```text
analyze_reference
score_tiktok_asset
run_ugc_preflight
```

Optional internal reusable job:

```text
process_media_evidence
```

Do not create a second job framework.

## 7.2 Processing stages

Use these job stages:

```text
queued
loading_asset
downloading_source
probing_media
creating_thumbnail
extracting_audio
transcribing_audio
sampling_frames
running_ocr
detecting_scenes
extracting_visual_evidence
building_creative_dna
calculating_score
checking_brief_alignment
generating_fixes
persisting_results
completed
```

Not every job must use every stage.

## 7.3 ffprobe metadata

Extract and store:

```text
duration_ms
container
video_codec
audio_codec
width
height
fps
video_stream_count
audio_stream_count
```

Update the immutable `asset_version` metadata fields that are currently nullable.

Reject analysis with a safe error when:

- No video stream exists.
- The container cannot be read.
- Duration is zero.
- The media is clearly invalid.

For MVP, support:

```text
video/mp4
video/quicktime
```

A reasonable local MVP maximum duration may be configured, such as 180 seconds.

Do not turn duration enforcement into a billing system.

## 7.4 Audio extraction

Use FFmpeg to create an audio artifact suitable for the selected ASR provider.

Store:

```text
media_artifacts.artifact_type = 'audio'
storage_key
```

Temporary local files must be cleaned after the worker finishes.

## 7.5 ASR

Produce a timestamped transcript contract:

```json
{
  "language": "en",
  "segments": [
    {
      "start_ms": 0,
      "end_ms": 2100,
      "text": "My counter was always a mess."
    }
  ],
  "full_text": "..."
}
```

Persist transcript artifact and transcript evidence items.

When ASR returns no speech:

- Do not fail the whole analysis.
- Mark transcript availability as false.
- Continue with visual/OCR evidence.

## 7.6 Frame sampling

Sample:

- Dense opening frames during the first three seconds.
- Regular frames every 1–2 seconds.
- Scene-boundary frames when available.
- A reasonable maximum frame count.

Store frame files in object storage.

Persist a `sampled_frames` artifact listing:

```json
{
  "frames": [
    {
      "timestamp_ms": 500,
      "storage_key": "..."
    }
  ]
}
```

## 7.7 OCR

OCR output contract:

```json
{
  "segments": [
    {
      "start_ms": 300,
      "end_ms": 1800,
      "text": "I did not know I needed this",
      "confidence": 0.91,
      "frame_storage_key": "..."
    }
  ]
}
```

Persist OCR artifact and evidence items.

## 7.8 Scene detection

Scene output contract:

```json
{
  "scenes": [
    {
      "scene_index": 0,
      "start_ms": 0,
      "end_ms": 2300
    }
  ]
}
```

Scene detection may use PySceneDetect, FFmpeg filters, or a lightweight implementation.

Do not require GPU infrastructure.

## 7.9 Visual evidence extraction

The visual model receives:

- Sampled frames.
- Frame timestamps.
- Product context if available.
- Transcript summary.
- OCR text.
- Versioned extraction schema.

It must produce structured observations, not scores.

Example:

```json
{
  "product_first_appearance_ms": 2400,
  "face_present_opening": true,
  "opening_visual": "messy kitchen counter",
  "demo_detected": true,
  "demo_type": "before_after",
  "close_up_present": true,
  "cta_visual_detected": false,
  "proof_type": "visual_before_after",
  "claim_candidates": [
    {
      "text": "best ever",
      "risk": "medium",
      "timestamp_ms": 14200
    }
  ]
}
```

Each important observation must be convertible into one or more evidence items.

---

# 8. MODEL PROVIDER STRATEGY

The MVP needs a live AI path and an explicit fixture path.

## 8.1 Configuration

Add settings similar to:

```text
AI_MODE=fixture|live

AI_BASE_URL=
AI_API_KEY=
AI_TEXT_MODEL=
AI_VISION_MODEL=

ASR_PROVIDER=fixture|openai_compatible
ASR_MODEL=

OCR_PROVIDER=fixture|vision
OCR_MODEL=

AI_REQUEST_TIMEOUT_SECONDS=120
AI_MAX_RETRIES=2
```

Use names compatible with the repository's existing settings style.

## 8.2 Live mode

Live mode must:

- Call configured external providers.
- Validate structured output through Pydantic.
- Retry malformed structured output only a small number of times.
- Persist provider/model/prompt versions.
- Return a safe failure when credentials are missing.
- Never silently switch to fixture mode.

## 8.3 Fixture mode

Fixture mode exists to allow local UI and workflow completion without secrets.

Fixture mode must:

- Be deterministic.
- Be labeled in all saved results with `analysis_mode = 'fixture'`.
- Display a visible badge in the frontend.
- Never use phrases that imply the model actually analyzed the uploaded media unless fixture data corresponds to a known demo fixture.
- Prefer matching a known demo fixture by checksum or fixture ID.
- Return an explicit unsupported-fixture error for unknown files rather than fabricating believable analysis.

## 8.4 Model responsibility boundaries

Models may:

- Transcribe.
- Extract text.
- Identify visual observations.
- Classify creative elements.
- Generate adaptation concepts.
- Generate Campaign Pack content.
- Write explanations and revision messages.

Models may not:

- Invent the final numerical score.
- Override deterministic hard blockers.
- Claim a video will go viral.
- Claim a video will create GMV.
- Mark Spark rights as complete.
- Infer platform authorization that the user did not provide.

---

# 9. CREATIVE DNA V1

Creative DNA is an observation layer.

It is not a prediction score.

## 9.1 Taxonomy version

Create:

```text
CREATIVE_DNA_TAXONOMY_VERSION = "creative_dna_v1"
```

Initial enumerations should include a practical subset.

### Hook types

```text
problem_first
curiosity
question
surprising_result
before_after
testimonial
social_proof
deal_offer
product_demo
authority
story
unknown
```

### Narrative structures

```text
problem_solution
before_after
testimonial
comparison
unboxing
review
tutorial
gift_reaction
day_in_the_life
listicle
demo_only
unknown
```

### Buyer emotions

```text
curiosity
convenience
identity
social_proof
urgency
transformation
gifting
personalization
trust
value
```

### Demo types

```text
hands_on
before_after
transformation
comparison
unboxing
tutorial
close_up_mechanism
lifestyle_use
none
unknown
```

### Proof types

```text
before_after
demonstration
testimonial
review
comment_social_proof
measurement
visual_result
none
unknown
```

### CTA types

```text
shop_now
product_tag
link_in_shop
learn_more
comment
follow
none
unknown
```

### Creator styles

```text
authentic_review
expert
lifestyle
home_organizer
mom_creator
student_creator
beauty_reviewer
pet_creator
voiceover_demo
faceless_demo
unknown
```

## 9.2 Creative DNA response contract

```json
{
  "opening": {
    "hook_type": "problem_first",
    "hook_text": "My counter was always a mess",
    "opening_visual": "messy kitchen counter",
    "face_present": true,
    "evidence_ids": []
  },
  "product": {
    "first_appearance_ms": 2400,
    "screen_time_ratio": 0.42,
    "close_up_present": true,
    "demo_type": "before_after",
    "evidence_ids": []
  },
  "narrative": {
    "structure": "problem_solution",
    "angle": "small_space_organization",
    "buyer_emotions": ["convenience", "transformation"],
    "evidence_ids": []
  },
  "proof": {
    "proof_type": "visual_result",
    "strength_label": "medium",
    "evidence_ids": []
  },
  "offer": {
    "present": false,
    "offer_type": null,
    "evidence_ids": []
  },
  "cta": {
    "present": true,
    "cta_type": "product_tag",
    "first_appearance_ms": 18200,
    "evidence_ids": []
  },
  "creator": {
    "persona": "home_organizer",
    "delivery_style": "authentic_review",
    "evidence_ids": []
  },
  "platform": {
    "tiktok_native_signals": [],
    "shop_signals": [],
    "evidence_ids": []
  },
  "risks": [
    {
      "code": "SHIPPING_PROMISE",
      "severity": "medium",
      "message": "Potential shipping promise detected.",
      "evidence_ids": []
    }
  ],
  "summary": {
    "what_to_keep": [],
    "what_to_change": [],
    "what_not_to_copy": [],
    "test_hypotheses": []
  }
}
```

## 9.3 Creative DNA rules

- Every important non-null conclusion should have evidence.
- Missing evidence lowers confidence.
- Unknown is better than invented certainty.
- User may edit or confirm tags later, but manual-confirmation UI is optional for this goal.
- Store source model, prompt, taxonomy, and asset version.

---

# 10. QUICK TIKTOK STRUCTURE SCORER

The Quick TikTok Scorer is the fastest entry feature.

Input:

```text
asset_version_id
optional product_id
optional objective
```

No Campaign Pack is required.

## 10.1 Scoring dimensions

Use version:

```text
tiktok_structure_rubric_v1
```

Weights:

```text
hook_clarity             20%
product_visibility       15%
demo_clarity             15%
proof_strength           10%
creator_authenticity     10%
offer_clarity            10%
cta_readiness            10%
tiktok_native_fit         5%
claim_safety              5%
```

Total: 100%.

## 10.2 Dimension result contract

```json
{
  "score": 55,
  "confidence": "high",
  "reason": "The product first appears after six seconds.",
  "evidence_ids": ["..."],
  "signals": {
    "first_product_appearance_ms": 6100
  }
}
```

## 10.3 Deterministic score ownership

`scorer.py` calculates the score from normalized evidence and rubric rules.

The model may return labels such as:

```text
clear
partial
missing
strong
medium
weak
```

The scorer converts those labels and measurable signals to numeric dimension values.

Do not ask the LLM:

```text
Return a score from 0 to 100.
```

## 10.4 Example measurable rules

These are directional MVP rules and must be versioned.

### Product visibility

```text
first appearance <= 3000 ms   → strong
3001–5000 ms                  → acceptable
5001–8000 ms                  → weak
> 8000 ms                     → very weak
not detected                  → missing
```

### CTA readiness

```text
explicit shop/product-tag CTA present before ending → strong
generic CTA only                                  → medium
CTA appears only at final moment                  → weak
no CTA                                            → missing
```

### Claim safety

```text
no detected risk candidates          → high
medium-risk unsupported phrasing     → reduced
high-risk unsupported claim          → hard blocker
```

Rules must remain explainable.

## 10.5 Structural action mapping

Default thresholds:

```text
0–49    → reject_or_reshoot
50–69   → revise
70–84   → organic_ready_or_small_test
85–100  → approve_structure
```

Hard blockers override thresholds.

## 10.6 Quick scorer output

```json
{
  "structural_score": 74,
  "confidence": "medium",
  "action": "revise",
  "dimensions": {},
  "strengths": [],
  "blockers": [],
  "fixes": [],
  "summary": "The demo is understandable, but the product reveal and CTA need revision.",
  "rubric_version": "tiktok_structure_rubric_v1",
  "rule_version": "tiktok_structure_rules_v1"
}
```

## 10.7 User-facing warning

Always display:

> This is a structural readiness score, not a guarantee of viral reach, sales, or GMV.

---

# 11. DECISION AND FIX ENGINE

The score is not the final product.

The Decision and Fix Engine converts:

```text
dimension results
+ evidence
+ hard blockers
+ objective
```

into:

```text
action
+ priority fixes
+ explanation
```

## 11.1 Hard blockers

Initial blocker codes:

```text
MEDIA_UNREADABLE
PRODUCT_NOT_VISIBLE
WRONG_PRODUCT_OR_PRODUCT_MISMATCH
MISSING_REQUIRED_DEMO
HIGH_RISK_UNSUPPORTED_CLAIM
BRIEF_PRODUCT_MISMATCH
MISSING_MUST_SHOW_SCENE
```

Initial warning/fix codes:

```text
LATE_PRODUCT_REVEAL
WEAK_OPENING
MISSING_CLOSE_UP
UNCLEAR_DEMO
WEAK_PROOF
MISSING_OFFER
MISSING_SHOP_CTA
CTA_TOO_LATE
OVER_SCRIPTED_DELIVERY
LOW_TIKTOK_NATIVE_FIT
MEDIUM_RISK_CLAIM
```

## 11.2 Fix contract

```json
{
  "code": "LATE_PRODUCT_REVEAL",
  "priority": 1,
  "instruction": "Add a clear product close-up within the first three seconds.",
  "why": "The product first appears at 6.1 seconds.",
  "evidence_ids": ["..."]
}
```

## 11.3 Fix ordering

Order fixes by:

1. Hard blocker.
2. Product correctness and visibility.
3. Hook/opening.
4. Demo completeness.
5. Claim safety.
6. CTA.
7. Offer.
8. Platform fit.
9. Nice-to-have polish.

Return no more than five primary fixes in MVP.

---

# 12. PRODUCT ADAPTATION ENGINE

Input:

```text
product_id
creative_dna_version_id
objective
target_market
target_buyer
constraints
```

## 12.1 Output contract

```json
{
  "keep": [
    {
      "element": "problem_first_structure",
      "reason": "The opening makes the buyer pain immediately visible.",
      "evidence_ids": []
    }
  ],
  "change": [
    {
      "element": "buyer_persona",
      "reason": "Adapt the persona to the selected product and target buyer."
    }
  ],
  "avoid": [
    {
      "element": "exact_script_copy",
      "reason": "Use the mechanism, not the original wording."
    }
  ],
  "concepts": [
    {
      "id": "concept_1",
      "name": "Small apartment counter reset",
      "angle": "small_space_convenience",
      "buyer_persona": "US apartment renter",
      "creator_persona": "budget home organizer",
      "hook": "This gave me half my counter back",
      "opening_visual": "crowded countertop",
      "demo_sequence": [
        "show the clutter",
        "show the product close-up",
        "demonstrate use",
        "show the result",
        "show TikTok Shop CTA"
      ],
      "proof": "before_after",
      "cta": "Linked in my TikTok Shop",
      "risks": [],
      "test_hypothesis": "Test whether space-saving value outperforms generic organization."
    }
  ]
}
```

## 12.2 MVP limits

Generate exactly three differentiated concepts by default.

Do not generate twenty near-duplicate hooks.

Concepts must differ by at least one meaningful axis:

- Buyer persona.
- Buyer pain.
- Emotional trigger.
- Demo mechanism.
- Proof mechanism.
- Creator style.
- Offer framing.

No vector database is required in this goal.

No PatternKit registry is required.

---

# 13. CAMPAIGN PACK V1

A Campaign Pack is structured, editable, and versioned.

It is not one markdown blob.

## 13.1 Brief contract

```json
{
  "objective": "tiktok_shop_affiliate_test",
  "target_market": "US",
  "target_buyer": {
    "persona": "small apartment renter",
    "pain": "limited counter space",
    "desired_outcome": "faster organization"
  },
  "core_angle": {
    "name": "small_space_convenience",
    "promise": "Create more usable counter space"
  },
  "creator_persona": {
    "type": "budget home organizer",
    "delivery_style": "authentic_review"
  },
  "hooks": [],
  "scripts": [],
  "storyboard": [],
  "must_show": [],
  "text_overlays": [],
  "talking_points": [],
  "cta": {
    "spoken": "",
    "overlay": "",
    "product_tag_required": true
  },
  "claims_allowed": [],
  "claims_to_avoid": [],
  "do": [],
  "dont": [],
  "rights_request": {
    "raw_footage_requested": false,
    "editing_permission_requested": false,
    "usage_note": ""
  },
  "spark_request": {
    "request_authorization": false,
    "message": ""
  },
  "revision_checklist": []
}
```

## 13.2 Minimum generated content

A completed MVP pack must include:

- Five hooks.
- Two scripts.
- One storyboard.
- Five or fewer must-show items.
- Text overlay suggestions.
- Talking points.
- TikTok Shop CTA.
- Claims to avoid.
- Do/don't.
- Revision checklist.

Rights and Spark fields may be informational only in this goal.

Do not build the full rights module.

## 13.3 Editing behavior

Frontend must allow:

- Edit individual sections.
- Save a new version.
- View current version.
- View basic version history.
- Copy creator-facing text.

Regeneration of individual blocks is optional.

PDF/DOCX export is deferred.

---

# 14. UGC PREFLIGHT V1

Input:

```text
ugc_asset_version_id
campaign_pack_version_id
```

The service must load:

- UGC media evidence.
- Product context.
- Campaign Pack version.
- Structural score.
- Brief requirements.

## 14.1 Shared structural score

Reuse the Quick TikTok Structure Scorer.

Do not duplicate scoring formulas.

## 14.2 Brief alignment

Calculate a separate score:

```text
brief_alignment_score 0–100
```

Check:

- Required scenes present.
- Product shown correctly.
- Must-show items present.
- Core angle represented.
- CTA matches brief.
- Product tag instruction addressed.
- Claims avoid forbidden language.
- Delivery does not contradict the brief.

## 14.3 Final formula

Use:

```text
preflight_score =
0.80 * structural_score
+ 0.20 * brief_alignment_score
```

Version:

```text
ugc_preflight_rubric_v1
```

This is a structural/brief-readiness score.

It is not a performance prediction.

## 14.4 Action mapping

Default behavior:

```text
hard reject blocker
→ reject

fixable hard blocker
→ revise

score 0–49
→ reject_or_reshoot

score 50–69
→ revise

score 70–84
→ organic_ready_or_small_paid_test

score 85–100 and no blockers
→ spark_ready_pending_rights
```

Do not claim `spark_ready` without rights information.

Use:

```text
spark_ready_pending_rights
```

## 14.5 Preflight output

```json
{
  "preflight_score": 74,
  "structural_score": 76,
  "brief_alignment_score": 66,
  "confidence": "medium",
  "action": "revise",
  "dimensions": {},
  "brief_alignment": {},
  "strengths": [],
  "blockers": [
    {
      "code": "LATE_PRODUCT_REVEAL",
      "severity": "high",
      "message": "Product first appears at 6.1 seconds.",
      "evidence_ids": []
    }
  ],
  "fixes": [
    {
      "priority": 1,
      "instruction": "Add a product close-up within the first three seconds.",
      "evidence_ids": []
    }
  ],
  "revision_message": "The demonstration feels clear. Could you add a product close-up within the first three seconds and move the TikTok Shop CTA before the ending?",
  "rubric_version": "ugc_preflight_rubric_v1",
  "rule_version": "ugc_preflight_rules_v1"
}
```

## 14.6 Revision Copilot

The LLM may rewrite deterministic fixes into a natural creator-facing message.

The message must:

- Preserve every critical fix.
- Remain respectful.
- Avoid vague language.
- Avoid insulting the creator.
- Avoid over-controlling creator voice.
- Use plain US English by default.
- Never introduce a new claim or requirement not present in the fixes/brief.

---

# 15. API CONTRACTS

Use existing `/api/v1` prefix and response envelope.

Names may be adapted to repository conventions, but the lifecycle must remain equivalent.

## 15.1 Reference Boards

```http
POST   /api/v1/workspaces/{workspace_id}/reference-boards
GET    /api/v1/workspaces/{workspace_id}/reference-boards
GET    /api/v1/workspaces/{workspace_id}/reference-boards/{board_id}
PATCH  /api/v1/workspaces/{workspace_id}/reference-boards/{board_id}
DELETE /api/v1/workspaces/{workspace_id}/reference-boards/{board_id}
```

## 15.2 References

```http
POST /api/v1/workspaces/{workspace_id}/references
GET  /api/v1/workspaces/{workspace_id}/references
GET  /api/v1/workspaces/{workspace_id}/references/{reference_id}
POST /api/v1/workspaces/{workspace_id}/references/{reference_id}/analyze
```

Create reference request should accept:

```text
board_id
asset_id
product_id nullable
source_platform nullable
source_url nullable
title
notes nullable
```

## 15.3 Creative DNA

```http
GET /api/v1/workspaces/{workspace_id}/creative-dna/{dna_version_id}
GET /api/v1/workspaces/{workspace_id}/references/{reference_id}/creative-dna
```

## 15.4 Quick TikTok Scorer

```http
POST /api/v1/workspaces/{workspace_id}/tiktok-scores
GET  /api/v1/workspaces/{workspace_id}/tiktok-scores/{score_run_id}
```

Create request:

```json
{
  "asset_id": "uuid",
  "product_id": "uuid-or-null",
  "objective": "generic_structure"
}
```

Return HTTP 202 with job and run IDs.

## 15.5 Adaptations

```http
POST /api/v1/workspaces/{workspace_id}/adaptations
GET  /api/v1/workspaces/{workspace_id}/adaptations/{adaptation_id}
```

## 15.6 Campaign Packs

```http
POST  /api/v1/workspaces/{workspace_id}/campaign-packs
GET   /api/v1/workspaces/{workspace_id}/campaign-packs
GET   /api/v1/workspaces/{workspace_id}/campaign-packs/{campaign_pack_id}
PATCH /api/v1/workspaces/{workspace_id}/campaign-packs/{campaign_pack_id}
POST  /api/v1/workspaces/{workspace_id}/campaign-packs/{campaign_pack_id}/versions
GET   /api/v1/workspaces/{workspace_id}/campaign-packs/{campaign_pack_id}/versions
```

## 15.7 Preflight

```http
POST /api/v1/workspaces/{workspace_id}/preflight-runs
GET  /api/v1/workspaces/{workspace_id}/preflight-runs/{preflight_run_id}
```

Create request:

```json
{
  "ugc_asset_id": "uuid",
  "campaign_pack_version_id": "uuid"
}
```

Return HTTP 202 with job and run IDs.

## 15.8 Jobs

Reuse existing job polling:

```http
GET /api/v1/workspaces/{workspace_id}/jobs/{job_id}
```

Frontend polling must stop on:

```text
completed
failed
cancelled
```

---

# 16. FRONTEND INTEGRATION

The frontend already exists.

Do not redesign it from scratch.

Preserve:

- Existing React/Vite setup.
- Existing component library.
- Existing navigation.
- Existing visual hierarchy.
- Existing feature folders where practical.

Replace mock adapters only for the MVP flow.

## 16.1 Shared API layer

Create or normalize:

```text
src/shared/api/
├── client.ts
├── auth.ts
├── envelope.ts
├── errors.ts
├── uploads.ts
└── jobs.ts
```

Use:

```text
VITE_API_BASE_URL
VITE_LOCAL_AUTH_TOKEN
```

Local development may use:

```text
Authorization: Bearer local-test
```

Do not hard-code production URLs.

## 16.2 Upload flow

Frontend upload behavior:

```text
request upload session
→ PUT file to presigned URL
→ complete upload
→ receive asset
```

Show:

- Upload progress.
- Upload error.
- Complete-upload error.
- Asset status.

## 16.3 Job polling

Use React Query polling.

Display:

```text
queued
running
retrying
completed
failed
cancelled
```

Display current job stage and progress.

## 16.4 Required MVP screens

### Quick TikTok Scorer

User can:

- Upload/select video.
- Start score.
- Watch progress.
- See score.
- See dimensions.
- See evidence.
- See blockers.
- See prioritized fixes.
- See fixture/live badge.
- See structural-score warning.

### Reference Boards

User can:

- Create board.
- Add reference from uploaded asset.
- Link optional product.
- Start analysis.
- View analysis status.

### Creative DNA Detail

Display:

- Hook.
- Angle.
- Product reveal.
- Demo.
- Proof.
- Offer.
- CTA.
- Creator style.
- Risks.
- Evidence timeline.
- Keep/change/avoid.
- Test hypotheses.

### Product Adaptation

User can:

- Select product.
- Select DNA version.
- Enter objective, market, buyer, constraints.
- Generate three concepts.
- Choose one concept.

### Campaign Pack Editor

Display editable sections:

- Objective.
- Target buyer.
- Core angle.
- Creator persona.
- Hooks.
- Scripts.
- Storyboard.
- Must-show.
- CTA.
- Claims.
- Do/don't.
- Revision checklist.

Save creates a new version.

### UGC Preflight

User can:

- Upload/select UGC draft.
- Select Campaign Pack version.
- Start Preflight.
- View score, action, blockers, evidence, fixes.
- Copy revision message.

## 16.5 Existing mock screens

Do not remove all mock screens.

Only replace mock data for the core MVP paths.

Mark remaining mock-only areas clearly in code comments or development UI.

---

# 17. IMPLEMENTATION MILESTONES

Codex must execute in this order.

---

## MILESTONE 0 — REPOSITORY ALIGNMENT

### Tasks

- [x] Inspect current backend and frontend trees.
- [x] Confirm current migration head.
- [x] Confirm current API envelope and auth dependencies.
- [x] Confirm current asset upload and job flow.
- [x] Confirm frontend feature folders and mock adapters.
- [x] Update this file's Current Repository Baseline if needed.
- [x] Identify files that will be extended rather than rewritten.
- [x] Add the first entry to the Execution Log.

### Exit condition

There is a concrete implementation map against the actual repository.

Do not produce a separate planning document.

Continue immediately to Milestone 1.

---

## MILESTONE 1 — MVP DATA MODEL

### Tasks

- [x] Add `reference_boards`.
- [x] Add `references`.
- [x] Add `media_artifacts`.
- [x] Add `evidence_items`.
- [x] Add `creative_dna_versions`.
- [x] Add `tiktok_score_runs`.
- [x] Add `adaptation_runs`.
- [x] Add `campaign_packs`.
- [x] Add `campaign_pack_versions`.
- [x] Add `preflight_runs`.
- [x] Add SQLAlchemy models.
- [x] Add repositories.
- [x] Add Pydantic schemas.
- [x] Add new Alembic migration.
- [x] Preserve migration `0001_initial_foundation`.
- [x] Register new models with Alembic metadata.
- [x] Add routers to FastAPI app.

### Exit condition

The application can create/read the new core entities using fixture/manual data.

Continue to Milestone 2.

---

## MILESTONE 2 — REAL MEDIA PIPELINE

### Tasks

- [x] Replace or supersede `process_asset_placeholder`.
- [x] Add ffprobe metadata extraction.
- [x] Add thumbnail creation.
- [x] Add audio extraction.
- [x] Add timestamped ASR adapter.
- [x] Add frame sampling.
- [x] Add OCR adapter.
- [x] Add scene detection.
- [x] Add visual evidence extraction.
- [x] Persist media artifacts.
- [x] Persist evidence items.
- [x] Update job stages/progress.
- [x] Reuse existing processing jobs and worker.
- [x] Add live and fixture analysis mode.
- [x] Ensure fixture mode rejects unknown files instead of fabricating results.
- [x] Ensure temporary files are cleaned.

### Exit condition

A supported video asset produces:

```text
metadata
thumbnail
audio/transcript where available
sampled frames
OCR where available
scene boundaries
normalized evidence
```

Continue to Milestone 3.

---

## MILESTONE 3 — CREATIVE DNA

### Tasks

- [x] Add Creative DNA taxonomy v1.
- [x] Add extraction Pydantic schema.
- [x] Add Creative DNA builder.
- [x] Map artifacts/evidence to DNA.
- [x] Persist Creative DNA version.
- [x] Expose Creative DNA APIs.
- [x] Link DNA to reference and asset version.
- [x] Add evidence IDs to conclusions.
- [x] Add confidence calculation based on evidence completeness.
- [x] Expose fixture/live mode.
- [x] Add frontend Creative DNA view.
- [x] Add reference analyze action.

### Exit condition

A reference video produces a structured Creative DNA view with evidence.

Continue to Milestone 4.

---

## MILESTONE 4 — QUICK TIKTOK SCORER

### Tasks

- [x] Add rubric version.
- [x] Add deterministic dimension scoring.
- [x] Add hard-blocker rules.
- [x] Add action mapping.
- [x] Add prioritized fix generation.
- [x] Persist score run.
- [x] Create recommendation record.
- [x] Expose score APIs.
- [x] Add Quick TikTok Scorer frontend.
- [x] Show score warning.
- [x] Show evidence.
- [x] Show fixture/live mode.

### Exit condition

A user can upload/select a video and receive:

```text
structural score
dimension scores
confidence
action
blockers
fixes
evidence
```

Continue to Milestone 5.

---

## MILESTONE 5 — PRODUCT ADAPTATION

### Tasks

- [x] Add adaptation input schema.
- [x] Add live provider prompt/schema.
- [x] Add deterministic fixture support for known demo fixtures.
- [x] Produce keep/change/avoid.
- [x] Produce exactly three differentiated concepts.
- [x] Persist adaptation run.
- [x] Expose adaptation APIs.
- [x] Add adaptation frontend flow.
- [x] Allow concept selection.

### Exit condition

A product plus DNA version produces three useful, differentiated, traceable concepts.

Continue to Milestone 6.

---

## MILESTONE 6 — CAMPAIGN PACK

### Tasks

- [x] Add Campaign Pack structured schema.
- [x] Generate minimum content.
- [x] Persist Campaign Pack and version 1.
- [x] Add version creation.
- [x] Prevent historical version mutation.
- [x] Expose Campaign Pack APIs.
- [x] Add frontend editor.
- [x] Add version history.
- [x] Add creator-facing copy view.

### Exit condition

A selected adaptation concept becomes an editable Campaign Pack that can be copied and used as a creator brief.

Continue to Milestone 7.

---

## MILESTONE 7 — UGC PREFLIGHT

### Tasks

- [x] Add Preflight request flow.
- [x] Reuse media pipeline.
- [x] Reuse TikTok structural scorer.
- [x] Calculate brief alignment.
- [x] Apply Preflight hard blockers.
- [x] Calculate final Preflight score.
- [x] Generate action label.
- [x] Generate prioritized fixes.
- [x] Generate creator-friendly revision message.
- [x] Persist Preflight run.
- [x] Create recommendation record.
- [x] Expose Preflight APIs.
- [x] Add UGC Preflight frontend screen.
- [x] Add copy-revision-message action.

### Exit condition

A UGC asset plus Campaign Pack version returns a usable approve/revise/reject/test decision with evidence.

Continue to Milestone 8.

---

## MILESTONE 8 — END-TO-END MVP POLISH

### Tasks

- [x] Remove blocking mock data from core MVP routes.
- [x] Keep non-MVP mock areas intact.
- [x] Add sensible empty/loading/error states.
- [x] Add clear fixture/live badges.
- [x] Add one known demo product.
- [x] Add one known reference fixture.
- [x] Add one known UGC fixture with fixable issues.
- [x] Add fixture analysis outputs tied to checksums.
- [x] Ensure complete navigation between steps.
- [x] Add concise local run instructions.
- [x] Update OpenAPI output if repository practice requires it.
- [x] Complete manual smoke flows.
- [x] Complete the Execution Log.
- [x] Mark all satisfied Definition of Done items.

### Exit condition

Both core flows work end to end.

---

# 18. MVP DEFINITION OF DONE

The MVP is complete only when all applicable items are satisfied.

## 18.1 Quick TikTok Scorer

- [x] User can upload or select a video.
- [x] Media is processed outside the API request.
- [x] User can poll progress.
- [x] Media artifacts are persisted.
- [x] Evidence is persisted.
- [x] Structural score is deterministic.
- [x] Dimension scores are visible.
- [x] Blockers are visible.
- [x] Fixes are specific.
- [x] Action label is visible.
- [x] Fixture/live mode is visible.
- [x] Product does not claim viral or GMV prediction.

## 18.2 Reference and Creative DNA

- [x] User can create a board.
- [x] User can attach reference asset.
- [x] Reference can link to product.
- [x] Reference can be analyzed.
- [x] Creative DNA is structured.
- [x] Creative DNA is versioned.
- [x] Creative DNA conclusions link to evidence.
- [x] Keep/change/avoid is available.
- [x] Test hypotheses are available.

## 18.3 Adaptation

- [x] User selects product and Creative DNA.
- [x] User enters objective and market.
- [x] System returns three differentiated concepts.
- [x] Concepts are persisted.
- [x] Concept output is structured.
- [x] Exact-copy avoidance guidance is included.

## 18.4 Campaign Pack

- [x] User generates a Campaign Pack.
- [x] Pack is structured JSON.
- [x] Pack contains five hooks.
- [x] Pack contains two scripts.
- [x] Pack contains storyboard.
- [x] Pack contains must-show items.
- [x] Pack contains CTA.
- [x] Pack contains claim guardrails.
- [x] Pack contains revision checklist.
- [x] User can edit.
- [x] Saving creates a new version.
- [x] Historical versions remain accessible.

## 18.5 UGC Preflight

- [x] User uploads/selects UGC asset.
- [x] User selects Campaign Pack version.
- [x] Structural score is reused.
- [x] Brief alignment is calculated.
- [x] Final score is deterministic.
- [x] Hard blockers override threshold.
- [x] Action label is returned.
- [x] Evidence-backed blockers are returned.
- [x] No more than five primary fixes are returned.
- [x] Creator-friendly revision message is returned.
- [x] Recommendation record is created.

## 18.6 Frontend

- [x] Core screens use backend data.
- [x] Upload uses presigned URL.
- [x] Job polling works.
- [x] Errors are understandable.
- [x] Loading states are visible.
- [x] Fixture/live mode is visible.
- [x] Core navigation works.
- [x] Existing design system is preserved.

## 18.7 Local usability

- [x] Backend can start locally.
- [x] Worker can start locally.
- [x] Database migration can apply.
- [x] Frontend can start locally.
- [x] Known demo fixtures complete both flows.
- [x] Live provider path is documented.
- [x] Missing provider credentials produce a clear error.
- [x] Known limitations are documented.

---

# 19. MINIMAL VERIFICATION POLICY

Testing and production hardening are not the goal of this execution.

Do not spend substantial time expanding the test suite.

However, do not deliver an MVP that was never exercised.

Minimum verification:

1. Apply migrations to the local database.
2. Start API.
3. Start worker.
4. Start frontend.
5. Run Quick TikTok Scorer with a known fixture.
6. Run Reference → DNA → Adaptation → Campaign Pack.
7. Run UGC draft → Preflight.
8. Confirm persisted results survive page refresh and API restart.
9. Run existing lint/type checks only when they are fast and do not derail product completion.
10. Run frontend build once at the end if practical.
11. Document commands actually run.
12. Do not claim passes for commands not run.

Do not create a large testing backlog during the goal.

Add hardening/test debt to the deferred section instead.

---

# 20. HARDENING BACKLOG AFTER MVP

Do not implement these unless they directly block MVP completion.

Record them for the next goal.

## Job reliability

- Duplicate dispatch prevention.
- Dispatch recovery/outbox.
- Retry-state consistency.
- Dead-letter strategy.
- Cancellation.
- Per-stage retry.
- Job leasing/locking.
- Worker concurrency policy.

## Media security

- Magic-byte MIME detection.
- Full codec/container allowlist.
- Virus scanning.
- Orphan object cleanup.
- Storage lifecycle.
- Media deletion workflow.
- Quotas.

## Async and performance

- Remove blocking provider I/O from async request paths.
- Connection pooling review.
- Queue separation.
- Caching.
- Frame-count cost controls.
- Provider batching.
- Cost metering.

## Database

- Review foreign keys.
- Review cascade rules.
- Current-version integrity.
- Idempotency races.
- Pagination and indexes.
- Data retention.
- Audit events.

## Production configuration

- Explicit production settings.
- Secret management.
- Rate limiting.
- Trusted hosts.
- CSP.
- Production CORS review.
- OIDC/JWKS caching.
- Tenant isolation audit.

## Testing

- Integration tests with Postgres/Redis/MinIO.
- Worker tests.
- Provider contract tests.
- Frontend component tests.
- E2E tests.
- Score-rule tests.
- Golden Creative DNA fixtures.
- Regression evaluation.
- Coverage policy.

## Deployment

- Container hardening.
- Cloud environments.
- Managed services.
- CI/CD.
- Preview environments.
- Monitoring.
- Sentry/OpenTelemetry.
- Cost dashboards.
- Autoscaling.

## Product intelligence

- Score calibration against GMV.
- PatternKit.
- ViralKit.
- Performance CSV.
- Creator Fit.
- Sample ROI.
- Rights/Spark.
- Fatigue.
- Benchmarks.
- Agent/API/MCP.

---

# 21. CODEX FINAL OUTPUT REQUIREMENTS

At the end of the goal, Codex must report:

1. Actual repository baseline found.
2. Modules added.
3. Migrations added.
4. Tables added.
5. API endpoints added.
6. Job types and stages added.
7. AI providers implemented.
8. Fixture-mode behavior.
9. Live-mode environment variables.
10. Frontend routes/screens integrated.
11. End-to-end flows completed.
12. Commands actually run.
13. What was not run.
14. Known limitations.
15. Hardening backlog.
16. Exact remaining blockers, if any.
17. Updated checklist status.
18. Updated Execution Log.

Do not provide a vague summary such as “MVP is done.”

State exactly which Definition of Done items passed and which remain open.

---

# 22. EXECUTION LOG

Codex must update this section during the goal.

## Entry template

```text
Date:
Milestone:
Status: not_started | in_progress | completed | blocked

Files changed:
- ...

Migrations:
- ...

Endpoints:
- ...

Manual verification:
- ...

Blockers:
- ...

Notes:
- ...
```

## Log entries

### Milestone 0

```text
Date: 2026-07-28
Status: completed

Files changed:
- VIRALDY_MVP_GOAL.md

Migrations:
- Confirmed current head before this goal was 0001_initial_foundation.

Endpoints:
- Confirmed existing /api/v1 envelope, auth dependency, asset upload, jobs, products, recommendations, workspaces.

Manual verification:
- Inspected backend/frontend trees with rg/find.

Blockers:
- None.

Notes:
- Actual baseline matched the goal: FastAPI, SQLAlchemy/Alembic, Celery/Redis jobs, S3-compatible uploads, React/Vite/TanStack frontend with mocks.
```

### Milestone 1

```text
Date: 2026-07-28
Status: completed

Files changed:
- apps/backend/src/viraldy/modules/reference_boards/*
- apps/backend/src/viraldy/modules/references/*
- apps/backend/src/viraldy/modules/media_analysis/*
- apps/backend/src/viraldy/modules/creative_dna/*
- apps/backend/src/viraldy/modules/tiktok_scorer/*
- apps/backend/src/viraldy/modules/adaptations/*
- apps/backend/src/viraldy/modules/campaign_packs/*
- apps/backend/src/viraldy/modules/preflight/*
- apps/backend/src/viraldy/api/main.py
- apps/backend/src/viraldy/platform/database/models.py

Migrations:
- apps/backend/alembic/versions/0002_creative_intelligence_mvp.py

Endpoints:
- Added reference boards, references, creative DNA, TikTok scores, adaptations, campaign packs, preflight, and media-analysis evidence endpoints.

Manual verification:
- python3 -m compileall apps/backend/src apps/backend/scripts apps/backend/alembic/versions
- PYTHONPATH=.backend_deps:src python -m pytest tests -q --no-cov

Blockers:
- None.

Notes:
- Preserved 0001_initial_foundation and registered all new models through platform/database/models.py.
```

### Milestone 2

```text
Date: 2026-07-28
Status: completed

Files changed:
- apps/backend/src/viraldy/modules/media_analysis/*
- apps/backend/src/viraldy/worker/tasks/process_asset.py
- apps/backend/src/viraldy/platform/config/settings.py

Migrations:
- 0002_creative_intelligence_mvp adds media_artifacts and evidence_items.

Endpoints:
- GET /api/v1/workspaces/{workspace_id}/assets/{asset_id}/media-analysis

Manual verification:
- python3 -m compileall apps/backend/src apps/backend/scripts apps/backend/alembic/versions
- PYTHONPATH=.backend_deps:src python -m pytest tests -q --no-cov
- Testcontainers fixture smoke migrated a clean Postgres database and ran reference analysis, quick score, and UGC preflight through the worker task path.

Blockers:
- Live media object download/upload and provider calls were not exercised with real provider credentials.

Notes:
- Fixture mode persists metadata, thumbnail/audio placeholders, transcript, OCR, sampled frames, scenes, visual observations, and normalized evidence only for known checksums. Unknown files fail with UNSUPPORTED_FIXTURE_ASSET.
```

### Milestone 3

```text
Date: 2026-07-28
Status: completed

Files changed:
- apps/backend/src/viraldy/modules/creative_dna/*
- apps/backend/src/viraldy/modules/references/*
- apps/web/src/features/mvp-flow/routes/mvp-route.tsx

Migrations:
- 0002_creative_intelligence_mvp adds creative_dna_versions.

Endpoints:
- GET /api/v1/workspaces/{workspace_id}/creative-dna/{dna_version_id}
- GET /api/v1/workspaces/{workspace_id}/references/{reference_id}/creative-dna
- POST /api/v1/workspaces/{workspace_id}/references/{reference_id}/analyze

Manual verification:
- Backend compileall.
- pnpm build.
- Testcontainers fixture smoke produced Creative DNA from the seeded reference fixture.

Blockers:
- None for fixture mode. Live provider calls were not exercised with real credentials.

Notes:
- Creative DNA stores taxonomy/prompt version, fixture/live mode, confidence, and evidence IDs.
```

### Milestone 4

```text
Date: 2026-07-28
Status: completed

Files changed:
- apps/backend/src/viraldy/modules/tiktok_scorer/*
- apps/backend/src/viraldy/worker/tasks/process_asset.py
- apps/web/src/features/mvp-flow/routes/mvp-route.tsx

Migrations:
- 0002_creative_intelligence_mvp adds tiktok_score_runs.

Endpoints:
- POST /api/v1/workspaces/{workspace_id}/tiktok-scores
- GET /api/v1/workspaces/{workspace_id}/tiktok-scores/{score_run_id}

Manual verification:
- Backend compileall.
- pnpm lint.
- pnpm build.
- Testcontainers fixture smoke completed Quick TikTok Score with score 78 and action organic_ready_or_small_test.

Blockers:
- None for fixture mode.

Notes:
- Scoring is deterministic from evidence. Worker creates recommendation records for score runs.
```

### Milestone 5

```text
Date: 2026-07-28
Status: completed

Files changed:
- apps/backend/src/viraldy/modules/adaptations/*
- apps/web/src/features/mvp-flow/routes/mvp-route.tsx

Migrations:
- 0002_creative_intelligence_mvp adds adaptation_runs.

Endpoints:
- POST /api/v1/workspaces/{workspace_id}/adaptations
- GET /api/v1/workspaces/{workspace_id}/adaptations/{adaptation_id}

Manual verification:
- Backend compileall.
- pnpm build.

Blockers:
- Live provider calls were not exercised with real credentials.

Notes:
- Fixture output returns keep/change/avoid plus exactly three differentiated concepts.
```

### Milestone 6

```text
Date: 2026-07-28
Status: completed

Files changed:
- apps/backend/src/viraldy/modules/campaign_packs/*
- apps/web/src/features/mvp-flow/routes/mvp-route.tsx

Migrations:
- 0002_creative_intelligence_mvp adds campaign_packs and campaign_pack_versions.

Endpoints:
- POST /api/v1/workspaces/{workspace_id}/campaign-packs
- GET /api/v1/workspaces/{workspace_id}/campaign-packs
- GET /api/v1/workspaces/{workspace_id}/campaign-packs/{campaign_pack_id}
- PATCH /api/v1/workspaces/{workspace_id}/campaign-packs/{campaign_pack_id}
- POST /api/v1/workspaces/{workspace_id}/campaign-packs/{campaign_pack_id}/versions
- GET /api/v1/workspaces/{workspace_id}/campaign-packs/{campaign_pack_id}/versions

Manual verification:
- Backend compileall.
- pnpm build.
- Testcontainers fixture smoke created a Campaign Pack version used by UGC Preflight.

Blockers:
- None for fixture mode.

Notes:
- Historical versions are immutable; edits create a new version and move current_version_id.
```

### Milestone 7

```text
Date: 2026-07-28
Status: completed

Files changed:
- apps/backend/src/viraldy/modules/preflight/*
- apps/backend/src/viraldy/worker/tasks/process_asset.py
- apps/web/src/features/mvp-flow/routes/mvp-route.tsx

Migrations:
- 0002_creative_intelligence_mvp adds preflight_runs.

Endpoints:
- POST /api/v1/workspaces/{workspace_id}/preflight-runs
- GET /api/v1/workspaces/{workspace_id}/preflight-runs/{preflight_run_id}

Manual verification:
- Backend compileall.
- pnpm build.
- Testcontainers fixture smoke completed Preflight with score 68, action revise, and recommendation persistence.

Blockers:
- None for fixture mode.

Notes:
- Preflight reuses the TikTok structure scorer, calculates brief alignment, applies blocker action mapping, persists results, and creates recommendation records.
```

### Milestone 8

```text
Date: 2026-07-28
Status: completed

Files changed:
- apps/backend/scripts/seed_local.py
- .env.example
- apps/backend/README.md
- apps/web/README.md
- apps/web/src/shared/api/*
- apps/web/src/features/mvp-flow/routes/mvp-route.tsx
- apps/web/src/routes/mvp.tsx
- apps/web/src/widgets/app-shell/app-sidebar.tsx
- apps/web/src/routeTree.gen.ts

Migrations:
- 0002_creative_intelligence_mvp

Endpoints:
- /mvp frontend route uses core MVP backend APIs and existing upload/jobs APIs.

Manual verification:
- python3 -m compileall apps/backend/src apps/backend/scripts apps/backend/alembic/versions
- pnpm lint
- pnpm build
- PYTHONPATH=.backend_deps:src python -m ruff check src scripts alembic tests
- PYTHONPATH=.backend_deps:src python -m pytest tests -q --no-cov
- Uvicorn smoke: started API on 127.0.0.1:8011 and GET /health returned 200.
- Celery smoke: started worker with memory broker and confirmed process_mvp_job registered.
- Testcontainers fixture smoke: migration + seed + analyze reference + quick score + UGC preflight completed.

Blockers:
- Docker Compose stack was not started through docker compose in this shell. Verification used testcontainers and direct service/process smoke instead.

Notes:
- Seed local now creates known product, board, reference fixture, quick-score fixture, and fixable UGC fixture.
- Frontend /mvp includes upload, polling, Quick Scorer, Reference DNA, Adaptation, Campaign Pack, and Preflight panels.
```

### Final verification

```text
Date: 2026-07-28
Status: completed

Files changed:
- Full MVP implementation across backend modules, worker, migration, seed script, frontend /mvp route, shared web API client, and docs.

Migrations:
- 0002_creative_intelligence_mvp applied successfully to a clean Postgres 16.6 testcontainer.

Endpoints:
- FastAPI app imports with 21 routes.
- API health smoke passed with GET /health returning {"status":"ok"}.

Manual verification:
- PYTHONPATH=.backend_deps:src python -m ruff check src scripts alembic tests
- PYTHONPATH=.backend_deps:src python -m pytest tests -q --no-cov -> 23 passed
- Testcontainers fixture smoke -> analyze_evidence=10, score=78, score_action=organic_ready_or_small_test, preflight=68, preflight_action=revise, recommendations=2
- pnpm lint -> 0 errors, 11 existing Fast Refresh warnings
- pnpm build -> passed
- Celery worker startup smoke with memory broker -> process_mvp_job registered and worker ready
- AI_MODE=live missing credentials check -> AI_PROVIDER_NOT_CONFIGURED with required env list

Blockers:
- No MVP fixture-mode blocker remains.
- Live provider was wired and schema-validated but not exercised against a real AI provider because no valid credentials were supplied.
- The docker compose stack was not started end-to-end in this shell; verification used testcontainers plus direct API/worker startup smoke.

Notes:
- The frontend dev server is running at http://localhost:8080/mvp from this goal session.
- The repository has no committed OpenAPI artifact practice, so no generated OpenAPI file was updated.
```

---

# 23. FINAL EXECUTION DIRECTIVE

Execute the MVP now.

Do not stop after planning.

Do not refactor the architecture again.

Do not spend this goal on deployment or broad hardening.

Build the shared media-evidence pipeline first, then complete:

```text
Quick TikTok Scorer
+
Reference Board
→ Creative DNA
→ Product Adaptation
→ Campaign Pack
→ UGC Preflight
```

The goal is complete when a seller can use the product end to end and receive a structured, evidence-backed decision with a clear next action.
