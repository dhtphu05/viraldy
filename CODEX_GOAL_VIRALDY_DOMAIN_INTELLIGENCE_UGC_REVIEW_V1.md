# CODEX GOAL — Implement Viraldy Domain Intelligence + UGC Review MVP end to end

You are Codex working directly in the existing repository:

- Repository: `dhtphu05/viralscore-AI-Cross-Border`
- Backend: existing FastAPI + Pydantic v2 modular monolith
- Persistence: existing PostgreSQL/Supabase pattern with local test fallback
- Frontend: existing React + TypeScript + TanStack Router application
- Existing reusable capabilities: video upload, async jobs/polling, media extraction, ASR/OCR/frame/timeline evidence, result mapping, video markers, toast/error handling, Supabase repositories and SQL migrations

Treat this as one implementation goal. Inspect the repository first, then implement the complete vertical slice. Do not stop after producing a plan. Do not rewrite the application or migrate frameworks. Follow existing conventions and keep all existing ViralScore/VN flows backward compatible.

---

## 1. Goal

Implement a database-backed **Domain Intelligence Layer** and expose its first product vertical slice as a new **UGC Review** feature across backend and frontend.

The seller-facing workflow must be:

1. Upload a creator UGC draft.
2. Optionally add Product Context, the original creator brief, commerce domain and intended use.
3. Reuse the current media-analysis pipeline to extract evidence.
4. Query only the applicable domain rules from the database.
5. Return dynamic recommendations in exactly three user-facing groups:
   - `fix_first`
   - `improve`
   - `confirm`
6. Show strengths that should be preserved.
7. Produce a creator-ready revision message.
8. Persist seller actions on each recommendation.
9. Allow a revised draft to be uploaded and compare Draft 1 with Draft 2 using actual analysis results.

The product promise is:

> Review a creator draft, see exactly what to keep and fix, and get a revision message the seller can use immediately.

This is a structural, product-aware and workflow-aware review. It is **not** a virality prediction, performance guarantee, GMV prediction, ROAS prediction, legal opinion or automatic publishing gate.

---

## 2. Input research artifacts

The following files will be attached to this task or made available in the Codex environment. Locate them by exact filename. Do not recreate their content from memory.

- `DomainExpertPolicyPackV1.json`
- `DomainExpertPolicyPackV1.schema.json`
- `source_registry_v1.csv`
- `GoldenCasesV1.json`
- `semantic_regression_tests_v1.jsonl`
- `viraldy_domain_research_v1.md`

Copy them into the repository as follows:

```text
docs/domain-research/v1/
└── viraldy_domain_research_v1.md

backend/resources/domain_intelligence/v1/
├── DomainExpertPolicyPackV1.json
├── DomainExpertPolicyPackV1.schema.json
└── source_registry_v1.csv

backend/tests/fixtures/domain_intelligence/
├── GoldenCasesV1.json
└── semantic_regression_tests_v1.jsonl
```

Do not commit the ZIP bundle. Do not load Golden Cases or semantic test fixtures into the production database.

Expected research-pack counts:

```text
58 domain policies
23 creative patterns
20 mistake definitions
15 disagreement/uncertainty records
66 source records
3 Golden Cases
35 semantic regression cases
```

Validate these counts during import and tests. Fail clearly when an input artifact is missing or malformed.

---

## 3. Non-negotiable product behavior

### 3.1 Recommendation-first, never flow-blocking

Do not create a user-facing `BLOCKED`, `FAILED`, `REJECTED` or global pass/fail state for the asset.

A finding may recommend that the seller fix something before a particular intended use, but it must not lock the asset, campaign, workspace, editing flow or revision flow.

The UI must always make unaffected actions available, such as:

- continue reviewing;
- save the asset;
- edit existing footage;
- send a revision message;
- upload a revision;
- confirm missing seller information;
- mark a recommendation not applicable;
- ignore for now;
- continue with acknowledged risk outside automation.

There is no publishing or ad-launch automation in this MVP, so do not build an Action Eligibility Engine, approval workflow or automation hold system.

### 3.2 Exactly one product experience; no user-facing modes

Do not add Explore, Standard, Governance, strictness profiles or policy modes.

Dynamic behavior must be driven invisibly by available context:

```text
video only
→ structural review

video + product context
→ product-aware review

video + product + brief
→ expected-versus-observed review

video + intended paid/Spark use
→ add rights/disclosure confirmations
```

More context creates deeper analysis. Missing context creates typed unknowns, not failure.

### 3.3 Three recommendation groups only

Every seller-facing recommendation belongs to exactly one group:

- `fix_first`: evidence is sufficiently clear and the fix has high value before the current intended use;
- `improve`: contextual creative optimization that the seller may accept or ignore;
- `confirm`: a material fact cannot be verified and needs seller input, better media or publish-time checking.

Do not expose internal policy severities as the primary UX hierarchy.

### 3.4 Unknown is not failure

Support typed unknown states internally:

```text
unknown
insufficient_evidence
seller_confirmation_required
expert_review_required
policy_conflict
rights_incomplete
economics_insufficient
supplier_data_stale
publish_check_required
```

Examples:

- A draft video cannot prove that a product tag will be attached at publish time.
- Low OCR confidence cannot prove a POD personalization mismatch.
- Missing rights data cannot prove rights do not exist.
- A timing heuristic is not a platform violation unless an actual brief or hard requirement specifies it.

### 3.5 No unsupported performance language

Never output:

- viral probability;
- guaranteed performance;
- predicted GMV or ROAS;
- “winning” without linked performance evidence;
- a fake score lift from applying recommendations;
- a universal product-reveal second rule.

When relevant, use labels such as:

```text
observed_structure
pattern_candidate
directional_pattern
insufficient_evidence
```

### 3.6 Preserve the good parts

Every review must explicitly identify `strengths_to_keep`.

Every reshoot recommendation must state what existing footage, creator delivery, proof, CTA, audio or narrative should remain unchanged.

---

## 4. Scope

### Build now

- Research artifacts committed in the correct locations.
- JSON Schema validation and idempotent database importer.
- Database-backed policy/source/pattern/mistake/uncertainty registry.
- Feature-specific policy selector.
- Bounded deterministic + semantic evaluation.
- New UGC Review backend contracts and endpoints.
- New UGC Review frontend entry and result experience.
- Seller recommendation-action persistence.
- Creator revision message.
- Actual Draft 1 versus Draft 2 comparison.
- Golden Case and semantic regression tests.
- Documentation and reproducible commands.

### Do not build now

- policy admin UI;
- workspace modes;
- user-configurable governance;
- automatic publish or Spark launch;
- TikTok/Shopify/Ads integrations;
- full rights tracker;
- expert-review operations UI;
- creator CRM;
- payments or marketplace;
- performance prediction;
- GMV feedback loop;
- full PatternKit/ViralKit UI;
- bulk review;
- agency approval roles;
- global ad crawler;
- broad refactor of the existing ViralScore/VN modules.

---

## 5. Start with a repository audit, then implement

Before editing code:

1. Read any `AGENTS.md` files.
2. Read the root README and backend/frontend setup docs.
3. Inspect:
   - current API-router registration;
   - current Pydantic schema conventions;
   - current analysis job lifecycle and polling;
   - current media extraction and raw multimodal pipeline;
   - current Supabase client and local repository fallback;
   - existing migrations;
   - frontend router conventions;
   - `frontend/src/lib/types.ts`;
   - `frontend/src/lib/api.ts`;
   - result-page components, especially video markers and evidence timeline;
   - existing lint/test/build commands.
4. Write a concise implementation note at:
   - `docs/implementation/domain-intelligence-ugc-review-v1.md`
5. Continue immediately into implementation. Do not stop after the note.

Prefer small adapters over copying existing media-processing code.

---

## 6. Target architecture

```text
Research files
    ↓
Validated importer
    ↓
PostgreSQL / Supabase domain registry
    ↓
Context-based policy selector
    ↓
Existing media evidence pipeline
    ↓
Deterministic evaluator
    + bounded semantic evaluator
    ↓
Recommendation mapper
    ↓
UGCReviewResult
    ↓
Frontend decision page
    ↓
Seller action events
    ↓
Revision upload and comparison
```

Backend intelligence owns policy selection and recommendation semantics.

Frontend owns interaction and presentation.

Database owns durable memory and auditability.

Never import the policy JSON into the frontend bundle. Never evaluate policy applicability in React.

---

## 7. Backend module boundaries

Add a reusable bounded module:

```text
backend/app/domain_intelligence/
├── __init__.py
├── schemas.py
├── repository.py
├── importer.py
├── selector.py
├── evidence_adapter.py
├── deterministic_evaluator.py
├── semantic_evaluator.py
├── recommendation_mapper.py
├── message_renderer.py
└── public.py
```

Add the UGC Review feature as a separate product module, reusing the shared domain-intelligence API:

```text
backend/app/ugc_review/
├── __init__.py
├── schemas.py
├── repository.py
├── service.py
├── comparison.py
└── public.py
```

Use current repository naming conventions when the repo already has a stronger pattern. Do not create circular dependencies. Other modules should access domain intelligence through `domain_intelligence.public`, not internal repositories.

---

## 8. Database migration

Create the next sequential SQL migration after the current latest migration. Use the repository’s current migration naming convention.

The migration must add at least these domain-registry tables:

### `domain_policy_packs`

Required fields:

```text
id uuid primary key
pack_name text
version text
status text
content_hash text
meta jsonb
raw_payload jsonb
imported_at timestamptz
updated_at timestamptz
unique(pack_name, version)
```

### `domain_policy_sources`

```text
source_id text primary key
title text
publisher text
url text
source_type text
source_date text nullable
evidence_strength integer or text
notes text nullable
raw_payload jsonb
imported_at timestamptz
updated_at timestamptz
```

### `domain_policy_rules`

```text
code text primary key
pack_id uuid references domain_policy_packs(id)
domain text
title text
rule_type text
severity text
enabled_for_mvp boolean default false
applicability jsonb
required_conditions jsonb
implementation jsonb
source_ids jsonb
raw_payload jsonb
created_at timestamptz
updated_at timestamptz
```

### `domain_creative_patterns`

```text
code text primary key
pack_id uuid
name text
finding_classification text
performance_evidence_status text nullable
enabled_for_mvp boolean default false
raw_payload jsonb
created_at timestamptz
updated_at timestamptz
```

### `domain_mistake_definitions`

```text
code text primary key
pack_id uuid
category text
title text
severity text
editable_or_reshoot text
enabled_for_mvp boolean default false
raw_payload jsonb
created_at timestamptz
updated_at timestamptz
```

### `domain_uncertainties`

```text
code text primary key
pack_id uuid
topic text
classification text
raw_payload jsonb
created_at timestamptz
updated_at timestamptz
```

Add a normalized rule-source join table when it fits the existing DB style:

```text
domain_policy_rule_sources(rule_code, source_id)
```

Add UGC Review persistence tables. Reuse the existing `analysis_jobs` table for asynchronous job lifecycle when safe, using a distinct mode such as `ugc_review_v1`. Do not duplicate the job framework.

### `ugc_review_results`

```text
id uuid primary key
analysis_job_id uuid unique references analysis_jobs(id) on delete cascade
headline text
summary text
recommended_next_action text
overall_confidence text
strengths_to_keep jsonb
creator_revision_message text
policy_pack_version text
analysis_provenance jsonb
result_payload jsonb
created_at timestamptz
updated_at timestamptz
```

### `ugc_review_findings`

```text
id uuid primary key
analysis_job_id uuid references analysis_jobs(id) on delete cascade
rule_code text nullable references domain_policy_rules(code)
mistake_code text nullable references domain_mistake_definitions(code)
recommendation_group text check in ('fix_first','improve','confirm')
title text
reason text
owner_role text
fix_type text nullable
confidence text
evidence jsonb
recommendation_payload jsonb
created_at timestamptz
```

### `ugc_review_recommendation_events`

```text
id uuid primary key
analysis_job_id uuid
finding_id uuid
seller_action text check in ('accepted','ignored','not_applicable','sent_to_creator','marked_completed')
reason text nullable
created_at timestamptz
```

### `ugc_review_revisions`

```text
id uuid primary key
parent_analysis_job_id uuid
child_analysis_job_id uuid unique
created_at timestamptz
```

### `ugc_review_comparisons`

```text
id uuid primary key
parent_analysis_job_id uuid
child_analysis_job_id uuid
resolved_findings jsonb
still_open_findings jsonb
new_findings jsonb
strengths_preserved jsonb
summary text
comparison_payload jsonb
created_at timestamptz
```

Add useful indexes for active policies, job lookups, findings and revision relations.

Follow current RLS comments/patterns. Do not invent authentication or workspace RLS in this goal.

---

## 9. Research-pack importer

Add a CLI module, for example:

```text
backend/app/scripts/import_domain_policy_pack.py
```

Support commands equivalent to:

```bash
cd backend
python -m app.scripts.import_domain_policy_pack \
  --pack resources/domain_intelligence/v1/DomainExpertPolicyPackV1.json \
  --schema resources/domain_intelligence/v1/DomainExpertPolicyPackV1.schema.json \
  --sources resources/domain_intelligence/v1/source_registry_v1.csv \
  --activate-mvp
```

Also support:

```text
--validate-only
--dry-run
```

Importer requirements:

1. Validate the JSON using the supplied JSON Schema. Add a small maintained dependency such as `jsonschema>=4.23,<5` if needed.
2. Validate expected top-level collections and expected record counts.
3. Compare the CSV source registry against the embedded JSON source registry and fail on material ID mismatch.
4. Calculate a SHA-256 content hash.
5. Upsert the pack, sources, all 58 policies, all 23 patterns, all 20 mistakes and all 15 uncertainty records.
6. Populate rule-source relationships.
7. Be idempotent: a second run must not duplicate records.
8. Preserve the full raw record in JSONB while exposing filterable columns.
9. Print a clear summary with inserted/updated/skipped counts.
10. Fail clearly when Supabase/DB is required but unavailable; `--validate-only` must still work without DB.
11. Do not silently mutate a published production version. In development, same-version idempotent upsert is acceptable; document this behavior.

Import every policy, but activate only this focused MVP set:

```text
TT-CONTENT-001
TT-CLAIM-001
TT-OFFER-001
TT-URGENCY-001
DISC-001
FTC-SHIP-001
POD-PERS-001
POD-MOCK-001
DROP-COMP-001
DROP-SHIP-001
UGC-REV-002
UGC-RIGHTS-001
PERF-PREFLIGHT-001
PERF-TIME-001
SYS-UNKNOWN-001
SYS-PROV-001
```

All other policies remain queryable with `enabled_for_mvp = false`.

Add a developer/status endpoint returning current pack version, record counts and active rule codes. Do not build a policy-management frontend.

---

## 10. Backend contracts

Use strict Pydantic v2 models consistent with the repository.

### Input context

Support a multipart UGC Review request containing a required video plus optional context:

```text
video_file: required
market: default 'US'
platform: default 'tiktok_shop'
commerce_domain: one of generic, tiktok_shop_us, pod_personalization, dropshipping
intended_use: one of organic, affiliate, paid_candidate, spark_candidate, unknown
product_name: optional
product_category: optional
exact_variant_or_sku: optional
product_description: optional
current_offer: optional
verified_shipping_language: optional
approved_personalization: optional
physical_sample_available: optional boolean
creator_brief: optional text
material_connection: yes, no or unknown
seller_notes: optional
```

Do not make optional context mandatory just to start a review.

### Core enums

```python
RecommendationGroup = Literal['fix_first', 'improve', 'confirm']

ReviewFixType = Literal[
    'edit_existing_footage',
    'add_overlay',
    'replace_copy',
    'reshoot_scene',
    'confirm_seller_input',
    'request_better_media',
]

OwnerRole = Literal['seller', 'creator', 'editor']

ReviewNextAction = Literal[
    'use_as_is',
    'revise',
    'reshoot_scene',
    'confirm_information',
    'request_better_media',
]
```

### Evidence contract

```python
class ReviewEvidence(StrictBaseModel):
    id: str
    source: Literal['video', 'transcript', 'ocr', 'seller_input', 'brief', 'policy']
    observed: str
    start_ms: int | None = None
    end_ms: int | None = None
    confidence: Literal['high', 'medium', 'low']
```

### Recommendation contract

```python
class UGCRecommendation(StrictBaseModel):
    id: str
    rule_code: str | None = None
    mistake_code: str | None = None
    group: RecommendationGroup
    title: str
    reason: str
    why_it_matters: str
    owner: OwnerRole
    fix_type: ReviewFixType | None = None
    instructions: list[str]
    strengths_to_preserve: list[str]
    completion_criteria: list[str]
    evidence: list[ReviewEvidence]
    confidence: Literal['high', 'medium', 'low']
    affected_use: str | None = None
```

### Result contract

```python
class UGCReviewResult(StrictBaseModel):
    review_id: str
    status: Literal['completed']
    headline: str
    summary: str
    recommended_next_action: ReviewNextAction
    overall_confidence: Literal['high', 'medium', 'low']
    strengths_to_keep: list[str]
    fix_first: list[UGCRecommendation]
    improvements: list[UGCRecommendation]
    confirmations: list[UGCRecommendation]
    creator_revision_message: str
    policy_pack_version: str
    analysis_provenance: dict[str, object]
    created_at: str
```

No overall fail field. No predicted score lift.

### Revision comparison contract

```python
class UGCRevisionComparison(StrictBaseModel):
    parent_review_id: str
    revision_review_id: str
    summary: str
    resolved: list[dict[str, object]]
    still_open: list[dict[str, object]]
    new_findings: list[dict[str, object]]
    strengths_preserved: list[str]
```

Compare actual finding identities and evidence. Do not fabricate an improved score.

---

## 11. Evidence adapter and evaluator

### 11.1 Reuse current media processing

Create an adapter over the current raw/VN analysis outputs. Do not reimplement FFmpeg, ASR, OCR, frame sampling, metadata extraction, transcript handling or timeline evidence.

Normalize available output into an internal evidence bundle containing, where available:

```text
transcript segments with timestamps
OCR segments with timestamps
scene/timeline observations
media quality and analysis coverage
first product appearance
product visibility observations
hook/opening observations
demo observations
proof observations
offer/price/urgency phrases
CTA observations
disclosure observations
claim candidates
confidence per signal
```

When the current pipeline cannot prove a signal, leave it unknown.

### 11.2 Policy selector

Select only active rules applicable to:

```text
market
platform
commerce domain
intended use
available product context
available brief
observed claim/offer/shipping/disclosure signals
```

Do not send all 58 policies into every model call.

### 11.3 Deterministic evaluation first

Implement deterministic comparisons where facts exist, including:

- expected exact SKU/variant versus confidently observed SKU/variant;
- approved personalization versus confidently readable observed personalization;
- current offer versus observed price/discount/bundle text;
- explicit brief requirement versus observed evidence;
- material connection yes plus disclosure missing;
- observed shipping promise plus no verified seller shipping language;
- rights/Spark intended use plus no rights information;
- media quality too weak to verify a material fact;
- contextual timing rule behavior.

Important mappings:

```text
Clear exact mismatch
→ fix_first

Missing or low-confidence material fact
→ confirm

Contextual guideline
→ improve

Explicit brief miss with clear evidence
→ fix_first
```

Timing rule:

```text
No campaign/brief timing requirement
→ never call it a platform violation;
→ optionally suggest an earlier reveal under improve.

Explicit brief timing requirement missed
→ fix_first with expected-versus-observed evidence.
```

### 11.4 Bounded semantic evaluator

Use the current model/provider abstraction for ambiguous semantic judgments such as:

- demo understandable or unclear;
- proof supports the spoken claim;
- creator delivery appears forced;
- CTA is product-specific;
- product appears disconnected from the opening;
- claim is objective, subjective or absolute.

The semantic evaluator must:

- receive only relevant active rules and normalized evidence;
- return strict Pydantic JSON;
- separate observation from inference;
- include evidence IDs;
- be unable to change policy source, rule type or internal severity;
- be unable to mark unknown as pass;
- be unable to invent seller facts, rights, economics, product identity or timestamps;
- return no finding when confidence is inadequate.

Provide a deterministic fallback so the endpoint still returns a useful partial review when the semantic provider is unavailable.

### 11.5 Recommendation mapper

Merge deterministic and semantic candidates, remove duplicates and map them into:

```text
fix_first
improve
confirm
```

Prioritize a small number of high-value recommendations. Avoid flooding the result with every possible rule.

Default result target:

```text
2–5 strengths
0–3 fix_first recommendations
0–3 improvements
0–3 confirmations
```

### 11.6 Creator message renderer

Generate a concise creator-facing message from accepted review facts.

The message must:

- begin by preserving what is working;
- explain exact scene/copy changes;
- distinguish edit from reshoot;
- avoid legal jargon and internal policy codes;
- never add a new unsupported claim;
- never expand the original brief scope;
- have a deterministic template fallback.

---

## 12. Recommended mistake mapping

Use the imported taxonomy. At minimum support these codes in the MVP evaluator:

```text
M-PROD-001 product mismatch
M-PROD-002 late or forced product appearance
M-DEMO-001 unclear demo
M-PROOF-001 unsupported proof
M-OFFER-001 offer mismatch
M-OFFER-002 false urgency
M-CLAIM-001 claim risk
M-DISC-001 disclosure
M-CTA-001 product tag and CTA
M-CREATOR-001 creator authenticity
M-REV-001 revision scope
M-RIGHTS-001 rights and Spark
M-POD-001 POD personalization
M-POD-002 mockup versus physical sample
M-DROP-001 dropshipping compatibility
M-SUP-001 supplier and shipping risk
M-EVID-001 insufficient evidence
```

Internal taxonomy severity does not become a global user-facing blocked state.

---

## 13. Backend endpoints

Add versioned endpoints consistent with the current API style:

### Create review

```http
POST /api/v1/ugc-reviews
Content-Type: multipart/form-data
```

Response:

```json
{
  "review_id": "uuid",
  "status": "queued",
  "mode": "ugc_review_v1"
}
```

### Poll status

```http
GET /api/v1/ugc-reviews/{review_id}/status
```

Return status, progress, stage and error using the current job pattern.

### Get result

```http
GET /api/v1/ugc-reviews/{review_id}
```

Return `UGCReviewResult` after completion.

### Record seller action

```http
POST /api/v1/ugc-reviews/{review_id}/recommendations/{recommendation_id}/actions
```

Request:

```json
{
  "action": "accepted | ignored | not_applicable | sent_to_creator | marked_completed",
  "reason": "optional"
}
```

Persist the event. Do not only update frontend local state.

### Upload revision

```http
POST /api/v1/ugc-reviews/{review_id}/revisions
Content-Type: multipart/form-data
```

Create a child analysis job using the same context snapshot as Draft 1 unless the request explicitly supplies changes. Store the parent-child relation.

### Get comparison

```http
GET /api/v1/ugc-reviews/{review_id}/comparisons/latest
```

Return actual resolved, still-open and new findings plus strengths preserved.

### Domain status

```http
GET /api/v1/domain-intelligence/status
```

Return pack version, total counts and active rule codes for operational diagnostics.

Register routes using the current API-router convention.

---

## 14. Repository behavior

Create a dedicated `UGCReviewRepository` using the same Supabase/local fallback conventions as the existing repositories.

- Use the existing analysis repository for generic job lifecycle where practical.
- Persist results, findings, seller events, revision relations and comparisons in dedicated tables.
- Production/Supabase is the durable source of truth.
- A read-only resource or in-memory fallback is acceptable for local tests, but log clearly that it is not durable.
- Do not silently claim persistence when Supabase is not configured.

Every result must preserve:

```text
analysis job ID
asset/upload path
request context snapshot
policy pack version
applicable rule codes
model/provider version where available
analysis coverage
finding evidence
seller action events
parent/revision relation
```

---

## 15. Frontend integration

Create a dedicated product entry. Do not add another mode branch to the existing generic result page.

Suggested structure, adapted to current repository conventions:

```text
frontend/src/routes/
├── ugc-review.tsx
└── ugc-review-result.tsx

frontend/src/components/ugc-review/
├── UGCReviewForm.tsx
├── ReviewDecisionHeader.tsx
├── StrengthsToKeep.tsx
├── RecommendationSection.tsx
├── RecommendationCard.tsx
├── ReviewVideoPanel.tsx
├── CreatorRevisionMessage.tsx
├── SellerConfirmationCard.tsx
├── RevisionUploader.tsx
└── RevisionComparison.tsx

frontend/src/lib/
├── ugc-review-types.ts
├── ugc-review-api.ts
└── ugc-review-mapper.ts
```

Use existing shared components when appropriate. Reuse, do not duplicate:

- `Layout`;
- file-upload primitives;
- current request helper and error behavior;
- polling pattern;
- `sonner` toasts;
- existing video preview/marker behavior;
- evidence-timeline interaction;
- existing loading and error visual language.

Add a main navigation item named **UGC Review** or **Review UGC**. Keep existing navigation and routes working.

Do not expose internal names such as PatternKit, ViralKit, policy pack or rule severity in the main seller UX.

---

## 16. Frontend input page

Build one simple form.

### Required

- video upload;

### Optional, under “Add context for a more precise review”

- commerce domain;
- intended use;
- product name;
- category;
- exact variant/SKU;
- product description;
- current offer;
- verified shipping language;
- approved personalization;
- physical sample available;
- original creator brief;
- material connection;
- seller notes.

The page must not force a long onboarding form before value.

Primary CTA:

> Review draft

Show accepted video formats, current size limit and clear validation errors using existing backend rules.

On submit:

1. create the review;
2. navigate to the UGC Review result route;
3. poll progress using stages;
4. handle retry and errors without losing typed context.

---

## 17. Frontend result hierarchy

The result page must be action-first, not score-first.

### Header example

```text
Strong draft — one main fix recommended
Recommended next action: Reshoot one product scene
Confidence: High
```

Do not lead with a red failure banner or blocker count.

### Section order

1. **Keep** — strengths to preserve.
2. **Fix first** — high-value recommendations.
3. **Improve** — optional contextual improvements.
4. **Confirm** — missing facts or unverified publish information.
5. **Creator revision message**.
6. **Upload revised draft**.
7. **Revision comparison**, after a revision exists.

### Recommendation card

Show:

- title;
- concise reason;
- owner: seller, creator or editor;
- edit/reshoot/confirm badge;
- timestamp/location when available;
- exact instructions;
- strengths to preserve;
- completion criteria;
- evidence list;
- confidence;
- an expandable “Why Viraldy recommends this” area with rule code and policy version for audit, not as the main content.

Actions:

```text
Apply recommendation
Send to creator
Mark completed
Ignore for now
Not applicable
```

Only render actions that make sense for the recommendation. Persist every action through the API.

### Evidence interaction

Clicking a timestamp or evidence chip must seek/highlight the corresponding video moment using the existing video marker capability.

Do not claim a finding is timestamped when no timestamp exists.

### Creator message

Provide:

- copy button;
- mark-as-sent button;
- feedback when copied/sent;
- editable text only when current product patterns already support safe editing, otherwise copy-only is acceptable for this goal.

### Revision comparison

Display:

```text
Resolved
Still open
New in Draft 2
Strengths preserved
```

Do not show a simulated score increase. Only compare actual child-review output.

---

## 18. Frontend design requirements

Preserve the current Viraldy visual system and primary pink accent. Do not replace the theme.

Use:

- clear visual hierarchy;
- soft canvas/surface depth;
- white content surfaces;
- restrained borders;
- subtle shadows only where useful;
- semantic green/amber/blue/red accents without turning the screen into an alert dashboard;
- real video/evidence as the main visual content;
- responsive behavior;
- stable dashboard scrolling;
- 180–220 ms interaction transitions where the project already uses motion;
- no continuous animation, glow or decorative gradient overload.

The tone should feel like a helpful creative strategist, not compliance police.

Preferred copy:

```text
Recommended before paid use
Needs confirmation
One scene should be reshot
This part can be fixed in the edit
Keep this creator delivery
```

Avoid copy such as:

```text
Failed
Blocked asset
Policy violation
You cannot continue
```

except inside developer/audit details when the exact source terminology must be preserved.

---

## 19. Frontend types and API client

Define strict TypeScript types matching backend contracts. Do not use `any` for the core result.

Add API functions equivalent to:

```ts
createUGCReview(payload)
getUGCReviewStatus(reviewId)
getUGCReviewResult(reviewId)
recordUGCRecommendationAction(reviewId, recommendationId, action)
uploadUGCRevision(reviewId, file)
getLatestUGCRevisionComparison(reviewId)
```

Reuse the existing request helper, timeout behavior and `ApiError` user messaging. Add endpoint-specific friendly errors.

Keep API response mapping separate from React rendering.

---

## 20. Golden Cases and tests

### 20.1 Importer tests

Test:

- schema validation;
- expected counts;
- malformed artifact failure;
- source registry mismatch failure;
- idempotent second import;
- active MVP policy list;
- content-hash behavior.

### 20.2 Domain selector/evaluator tests

Cover at least:

- contextual timing never becomes a platform violation;
- explicit brief timing can produce `fix_first`;
- low-confidence product identity produces `confirm`, not mismatch;
- clear product mismatch recommends reshoot but does not globally block flow;
- missing rights affects paid-use confirmation, not creative quality;
- missing publish metadata becomes `publish_check_required`;
- mockup-only POD proof returns insufficient evidence/physical sample recommendation;
- unsupported shipping language requests confirmation/removal;
- views do not create a winning label;
- insufficient evidence never becomes a creative failure.

### 20.3 Semantic regression JSONL

Load every record from `semantic_regression_tests_v1.jsonl` into parameterized pytest tests or an equivalent contract harness.

Do not skip cases silently. When a case is outside the live UI subset, it must still validate the domain-intelligence contract behavior.

### 20.4 Golden Cases

Use all three cases from `GoldenCasesV1.json` as deterministic fixtures/snapshot expectations:

1. TikTok Shop US product demo;
2. POD personalized product;
3. dropshipping visual-demo product.

Test that each maps to the new recommendation-first result shape without turning the whole asset into a blocked UX state.

At minimum verify:

- strengths are preserved;
- expected versus observed evidence is represented;
- edit versus reshoot is explicit;
- missing rights/economics become confirmations;
- creator message is present;
- performance evidence status does not become a promise.

### 20.5 Repository/API tests

Test:

- create/poll/get result;
- local fallback;
- Supabase payload mapping where current test infrastructure allows;
- seller action persistence;
- revision parent/child relation;
- comparison resolved/still-open/new behavior;
- 404 and invalid-action handling.

### 20.6 Frontend quality gates

Use the existing frontend test setup if present. Do not add a large new testing stack merely for this goal.

Required:

- TypeScript passes;
- lint passes;
- production build passes;
- core result mapper is unit-tested when a test framework exists;
- result route renders all three recommendation groups correctly;
- timestamp click-to-seek is verified where practical.

---

## 21. Backward compatibility

Do not change existing public contracts unless required for a shared bug fix.

Do not break:

- existing ViralScore analysis endpoints;
- VN analysis pipeline;
- raw-analysis endpoints;
- sample/demo flows;
- current result page;
- existing database migrations;
- current frontend routes.

Run the entire existing backend test suite and frontend build after implementation.

---

## 22. Documentation

Update or add documentation covering:

- feature architecture;
- DB migration;
- importer commands;
- how to validate/import the research pack;
- environment variables;
- API contracts;
- how to run tests;
- how local fallback differs from durable Supabase persistence;
- current limitations;
- why the feature uses recommendation-first UX;
- why no performance prediction is made.

Document a reproducible local flow:

```text
apply migration
validate/import policy pack
start backend
start frontend
open UGC Review
upload a draft
see recommendations
record an action
upload Draft 2
see comparison
```

Do not document a feature as complete unless it works.

---

## 23. Definition of done

The goal is complete only when all of the following are true.

### Data and import

- Research files are placed correctly.
- Schema validation works.
- Importer is idempotent.
- DB contains 58 policies, 23 patterns, 20 mistakes, 15 uncertainties and 66 sources.
- The exact MVP policy set is active.
- Domain status endpoint reports the imported version and counts.

### Backend

- A real video can create a UGC Review job.
- Existing media-analysis code is reused.
- Applicable policies are queried from DB, not hardcoded entirely in a prompt.
- Result is persisted.
- Result contains strengths, fix_first, improvements, confirmations and creator message.
- Unknowns are typed and not treated as failure.
- Seller actions are persisted.
- A revised video creates a child review.
- Draft 1/Draft 2 comparison is based on actual findings.
- No endpoint returns virality/GMV/ROAS guarantees.

### Frontend

- UGC Review appears as a dedicated navigation entry.
- Upload/context form works.
- Async progress works.
- Result page is decision-first and positive.
- Video evidence can be opened at timestamps.
- Recommendation actions call backend APIs.
- Creator message can be copied and marked sent.
- Revision upload and comparison work.
- Existing pages remain functional.
- Responsive layout has no broken nested scrolling.

### Tests and quality

- Existing backend tests pass.
- New importer, selector, evaluator, API and revision tests pass.
- All semantic regression cases are exercised.
- Three Golden Cases are exercised.
- Frontend typecheck/lint/build pass.
- No core-path TODO, placeholder or fake prediction remains.

---

## 24. Execution rules

- Make the code changes; do not return only a design proposal.
- Prefer the smallest cohesive implementation that satisfies the vertical slice.
- Do not add user-facing modes.
- Do not implement global blocking.
- Do not put policy logic in React.
- Do not paste the full research pack into every LLM prompt.
- Do not duplicate the media pipeline.
- Do not overfit the current VN score dimensions to the US commerce domain.
- Do not manufacture evidence, timestamps, product facts, rights or performance.
- Preserve current coding style and module boundaries.
- Add comments only where they explain non-obvious domain behavior.
- Keep user-facing language friendly and actionable.
- When repository reality conflicts with a suggested path above, preserve the intent and adapt to the existing architecture; document the deviation.

At completion, provide:

1. a concise implementation summary;
2. key files changed;
3. migration/import commands;
4. backend and frontend run commands;
5. tests/build commands and results;
6. current limitations or intentionally deferred items;
7. one exact end-to-end manual verification flow.
