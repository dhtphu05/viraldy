# VIRALDY — PRIVATE BETA BACKEND, AUTH, PATTERNKIT & VIRALKIT COMPLETION GOAL

## Codex Goal-Mode Implementation Prompt

**Repository:** `dhtphu05/viraldy`  
**Current main reference:** `5708b11b8e1c2a869f5ab210392e54024148d924`  
**Target branch:** `release/private-beta-tech-freeze`  
**Target release:** `v0.1.0-beta-rc1`  
**Primary stack:** FastAPI, Python 3.12, PostgreSQL, SQLAlchemy async, Alembic, Celery, Redis, S3-compatible object storage  
**Architecture:** Lean Modular Monolith  
**Product:** Viraldy — AI Creative Intelligence & Iteration OS for TikTok Shop US, POD, dropshipping, and cross-border ecommerce teams

---

# 0. Mission

Complete the backend technical foundation required for a supervised private beta.

The next month should be used mainly for:

- collecting seller-authorized product, creative, UGC, and performance data;
- labeling and reviewing AI output;
- live Dola/Seed model qualification;
- intelligence calibration;
- prompt, rule, threshold, taxonomy, and confidence tuning;
- small compatibility and bug fixes.

The team must not need to rebuild authentication, tenant isolation, persistence, artifact versioning, job infrastructure, provider boundaries, PatternKit, ViralKit, or the core decision workflow next month.

This task is not a generic CRUD sprint. It must produce one coherent domain system:

```text
Product Context
+ Creative References
        ↓
Media Evidence
        ↓
Creative DNA
        ↓
PatternKit
        ↓
ViralKit
        ↓
Creative Campaign Pack
        ↓
UGC Structural Score + Exact Preflight
        ↓
Recommendation
        ↓
Seller Action + Human Correction
        ↓
Outcome data for later calibration
```

Final permissible completion statement:

> Viraldy backend is technically frozen for supervised private beta. Remaining work is live-model qualification, data collection, intelligence calibration, and small bug fixes.

Do not use this statement unless source code, migrations, automated tests, and a complete mock/fixture E2E flow prove it.

---

# 1. Product and business design basis

Do not invent PatternKit and ViralKit as generic AI objects. Implement them from the following validated product patterns and the real Viraldy customer domain.

## 1.1 Patterns adapted from benchmark products

| Source pattern | Product lesson | Viraldy implementation |
|---|---|---|
| Foreplay: capture, organize, research, brief | A saved creative must become reusable workflow data, not a bookmark | References and Creative DNA become evidence sources for PatternKit; PatternKit can be compiled into ViralKit and Campaign Packs |
| Alison: Creative Genome, Preflight, Smart Brief | Creative must be decomposed into structured elements, scored, and turned into production guidance | Creative DNA provides observations; PatternKit abstracts reusable structures; ViralKit creates product-specific hypotheses; Preflight verifies execution |
| VidMob: creative as measurable data, score before spend | Creative attributes need evidence, versions, confidence, and later outcome mapping | PatternKit retains provenance and optional performance evidence; ViralKit produces test and decision contracts |
| Pencil: one brief to many variants, orchestration, governance, feedback loop | Generation is useful only when constrained by a structured brief and learning loop | ViralKit creates exactly three strategically diverse concepts and generation briefs; Campaign Pack and Preflight remain the execution contract |
| Creator-commerce operations | Seller decisions include product, creator, sample, UGC, claims, rights, product tags, shipping, and performance | Product-aware applicability, creator direction, claim governance, TikTok Shop CTA, fulfillment constraints, and seller action tracking are first-class fields |

## 1.2 Real customer domain

Initial ICP:

- Cross-border TikTok Shop US seller or small operator in Vietnam/SEA;
- team size approximately 1–10;
- uses creators, affiliates, UGC, organic TikTok, or Spark Ads;
- tests product and creative weekly;
- currently manages work through TikTok Seller Center, Sheets, Drive, chat, and judgment;
- does not have a dedicated creative strategist or data analyst;
- has real sample, creator, or ad spend.

Relevant domain constraints:

- TikTok Shop product-tag CTA;
- product visibility timing;
- clear, observable demonstration;
- creator authenticity without vague instructions;
- US-market buyer language;
- prohibited claims and required disclosures;
- shipping and fulfillment promises;
- POD recipient, occasion, identity, and personalization flows;
- dropshipping trust, demo, margin, and shipping risks;
- UGC revision and version comparison;
- later mapping to clicks, orders, GMV, gross profit, sample cost, and seller decisions.

## 1.3 Terminology that must remain precise

```text
Creative DNA
= What was observed in one specific creative asset.

PatternKit
= A reusable, evidence-backed structural creative pattern abstracted from one or more Creative DNA versions.

ViralKit
= A product-specific, test-ready creative hypothesis package compiled from Product Context, one or more PatternKit versions, objective, buyer context, and seller constraints.

Creative Campaign Pack
= A creator-production brief for one selected concept. It is not a TikTok Ads or Meta Ads campaign object.

UGC Preflight
= Exact evaluation of a UGC draft against structural readiness and the requirements compiled from the selected Campaign Pack/ViralKit.
```

The name `ViralKit` is branding. It must never be presented as a guarantee of virality, GMV, ROAS, or sales.

---

# 2. Non-negotiable engineering rules

1. Inspect the current repository and reuse existing working modules.
2. Preserve the Lean Modular Monolith.
3. Cross-module calls must use `public.py` boundaries.
4. Do not import another module's internal `models.py`, `repository.py`, or `service.py` unless the existing architecture explicitly allows it and an architecture test documents the exception.
5. Routers contain transport logic only.
6. Repositories contain persistence queries only.
7. Services own business rules and state transitions.
8. Every workspace-owned query must scope by `workspace_id`.
9. Every intelligence artifact must be versioned, immutable after creation, and traceable to exact source versions.
10. Do not overwrite AI output with user corrections.
11. Use `unknown` or an explicit missing state instead of inventing values.
12. No score may be invented by an LLM.
13. Rules handle hard constraints; models extract/classify evidence; LLMs explain and propose actions.
14. Live provider mode must never silently fall back to fixture/mock mode.
15. Do not hardcode product facts, category facts, seller examples, prompts, secrets, or model IDs in business logic.
16. All substantial work requires migrations, unit tests, integration tests, and an audit entry.
17. Commit after each milestone.
18. Do not stop at schemas, interfaces, TODOs, or placeholders.

---

# 3. Required module inventory

Complete or add the following backend modules:

```text
identity
workspaces
products
assets
reference_boards
references
media_analysis
creative_dna
pattern_kits
viral_kits
adaptations
campaign_packs
tiktok_scorer
preflight
recommendations
feedback
product_events
jobs
model_runs
generation
health
```

Each business module must contain, where applicable:

```text
contracts.py
schemas.py
models.py
repository.py
service.py
router.py
public.py
```

Add migrations and tests for all new persistence.

---

# 4. Authentication and identity completion

The repository already has Bearer authentication, local-test and OIDC verifier boundaries, `/me`, and workspace permission foundations. Harden and complete them. Do not build a custom password database.

## 4.1 Required request contract

```http
Authorization: Bearer <access_token>
```

## 4.2 Token verification requirements

Validate:

- JWT signature;
- issuer;
- audience;
- expiration;
- `nbf` when present;
- subject;
- email;
- allowed algorithms;
- JWKS rotation.

Normalize failures to a project-standard `401` response. Never expose token content or raw provider errors.

## 4.3 User persistence target

```text
users
- id UUID primary key
- external_auth_id varchar not null unique
- email citext/varchar not null
- display_name varchar nullable
- status enum(active, suspended, deleted)
- last_login_at timestamptz nullable
- created_at timestamptz not null
- updated_at timestamptz not null
```

Rules:

- first authenticated request provisions the user;
- repeat requests do not create duplicates;
- concurrent provisioning must be safe;
- internal UUID is stable;
- profile updates are limited to safe provider-owned fields;
- suspended users cannot access the application.

## 4.4 Auth API

```text
GET /api/v1/me
GET /api/v1/auth/config
```

`GET /api/v1/auth/config` output:

```json
{
  "data": {
    "auth_mode": "oidc",
    "enabled": true,
    "issuer_url": "https://public-issuer.example",
    "audience": "viraldy-api"
  },
  "meta": {
    "request_id": "..."
  }
}
```

Do not expose secrets, JWKS cache internals, private client secrets, or tokens.

## 4.5 Environment safety

Staging/production must fail startup when any of the following is true:

```text
AUTH_MODE=local_test
AUTH_DISABLED=true
wildcard CORS
missing OIDC issuer
missing OIDC audience
missing OIDC JWKS URL
```

Local-test mode is allowed only for local and automated tests.

## 4.6 Auth tests

Cover:

- missing token;
- malformed header;
- wrong signature;
- wrong issuer;
- wrong audience;
- expired token;
- token not active yet;
- missing subject;
- missing email;
- successful provisioning;
- repeated request;
- concurrent provisioning;
- suspended user;
- production safety validation;
- local-test isolation.

---

# 5. Workspace tenancy and RBAC

## 5.1 Roles

```text
owner
admin
member
viewer
```

## 5.2 Permission matrix

| Permission | Owner | Admin | Member | Viewer |
|---|---:|---:|---:|---:|
| workspace.read | yes | yes | yes | yes |
| workspace.manage | yes | yes | no | no |
| members.read | yes | yes | yes | no |
| members.manage | yes | yes | no | no |
| product.read | yes | yes | yes | yes |
| product.write | yes | yes | yes | no |
| reference.read | yes | yes | yes | yes |
| reference.write | yes | yes | yes | no |
| analysis.run | yes | yes | yes | no |
| pattern_kit.write | yes | yes | yes | no |
| viral_kit.write | yes | yes | yes | no |
| campaign_pack.write | yes | yes | yes | no |
| preflight.run | yes | yes | yes | no |
| recommendation.act | yes | yes | yes | no |
| feedback.write | yes | yes | yes | no |
| data.export | yes | yes | no | no |
| data.delete | yes | yes | no | no |

Centralize this matrix. Do not scatter role string comparisons through routers.

## 5.3 Workspace API

```text
GET    /api/v1/workspaces
POST   /api/v1/workspaces
GET    /api/v1/workspaces/{workspace_id}
PATCH  /api/v1/workspaces/{workspace_id}
DELETE /api/v1/workspaces/{workspace_id}

GET    /api/v1/workspaces/{workspace_id}/members
POST   /api/v1/workspaces/{workspace_id}/members
PATCH  /api/v1/workspaces/{workspace_id}/members/{member_id}
DELETE /api/v1/workspaces/{workspace_id}/members/{member_id}
```

Rules:

- creator becomes owner;
- the only owner cannot remove or demote themself;
- viewer cannot mutate resources;
- member addition by email is sufficient for private beta;
- all resource access verifies membership;
- cross-workspace UUID enumeration must fail;
- add explicit tenant-isolation tests for every major resource.

---

# 6. Product Context — required input foundation

PatternKit and ViralKit must not generate useful-looking generic output from only a product name. Product Context is the source of truth.

## 6.1 ProductContextV1 target sections

```text
identity
classification
market_context
buyer_personas
problems_and_outcomes
features_and_benefits
commercial_context
fulfillment_context
creative_context
proof_context
governance
assets
```

## 6.2 Required input fields for a usable ViralKit

The following fields are required or must explicitly be `unknown`:

```text
identity.name
identity.product_type
classification.primary_category
market_context.target_market
buyer_personas at least one persona OR explicit unknown
features_and_benefits at least one benefit OR explicit unknown
creative_context.visual_demo_potential
governance.prohibited_claims
governance.required_disclosures
```

Commercial fields are optional but must be carried when provided:

```text
selling_price
currency
compare_at_price
discount_text
bundle
COGS
shipping_days
fulfillment_type
commission_range
inventory_constraints
```

## 6.3 Product snapshot rule

Every ViralKit, Adaptation, Campaign Pack, Preflight run, and recommendation must retain an immutable product snapshot containing:

```text
product_id
product_context_schema_version
product_context_version
snapshot_json
captured_at
```

Changing a product later must not mutate historical artifacts.

---

# 7. Media and Creative DNA foundation

PatternKit must be based on Creative DNA and evidence, never directly on a free-form LLM summary.

## 7.1 Media evidence families

At minimum support:

```text
hook_signal
product_appearance
product_visibility_summary
demo_summary
demo_step
proof_signal
creator_signal
editing_signal
offer_signal
cta_signal
claim_signal
platform_signal
spoken_text
on_screen_text
```

## 7.2 CreativeDnaV1 required output families

```text
opening
product
narrative
demo
proof
creator
editing
offer
cta
platform
claims
risks
reusable_mechanisms
uncertainties
completeness
overall_confidence
```

Every observed field must carry:

```text
value
status = observed | inferred | unknown
confidence
source_evidence_ids
```

PatternKit extraction may use observed and carefully identified inferred fields, but must never silently convert `unknown` into a positive pattern.

---

# 8. PatternKit V1 — authoritative domain design

## 8.1 Definition

PatternKit is a versioned, reusable, evidence-backed structural creative pattern abstracted from one or more Creative DNA versions.

It answers:

> What creative structure is reusable, in what context, with which evidence, constraints, confidence, and anti-copy rules?

PatternKit is not:

- a saved video;
- a generic prompt;
- a long AI paragraph;
- a guarantee of performance;
- a collection of copied scripts;
- a direct replacement for Creative DNA.

## 8.2 PatternKit kinds

```text
single_asset_abstraction
multi_asset_cluster
workspace_learned_pattern
category_playbook
```

Private beta supports the first three. `category_playbook` may exist behind an internal/admin flag.

## 8.3 PatternKit scope

```text
workspace_private
product_specific
```

Do not implement cross-customer global sharing in private beta.

## 8.4 PatternKit lifecycle

```text
candidate
reviewed
validated
deprecated
archived
```

Rules:

- AI-created kits start as `candidate`;
- a user/domain reviewer can mark `reviewed`;
- `validated` requires explicit human validation;
- do not infer `validated` from generation success;
- performance-backed labels are separate from validation status;
- archived kits are read-only and excluded from default retrieval.

## 8.5 PatternKitCreateRequestV1

```json
{
  "name": "Problem → Fast Reveal → Observable Transformation",
  "kind": "multi_asset_cluster",
  "scope": "workspace_private",
  "source_creative_dna_version_ids": [
    "uuid-dna-v1",
    "uuid-dna-v2"
  ],
  "primary_category": "home_organization",
  "target_platforms": ["tiktok_shop"],
  "target_markets": ["US"],
  "objectives": ["affiliate", "organic_test", "small_paid_test"],
  "extraction_mode": "ai_assisted",
  "review_notes": null
}
```

Validation:

- at least one Creative DNA version;
- all source versions belong to the workspace;
- all source versions exist and are completed;
- no duplicate source IDs;
- `name` length 3–160;
- `target_platforms` cannot be empty;
- `target_markets` cannot be empty;
- `kind=multi_asset_cluster` requires at least two Creative DNA versions;
- `kind=workspace_learned_pattern` requires at least one seller action or performance reference when promoted from candidate.

## 8.6 Shared evidence reference contract

```python
class PatternEvidenceRefV1(BaseModel):
    creative_dna_version_id: UUID
    asset_version_id: UUID
    evidence_id: UUID
    feature_path: str
    source_type: Literal[
        "vision",
        "asr",
        "ocr",
        "derived",
        "human_correction",
        "performance"
    ]
    start_ms: int | None
    end_ms: int | None
    observation_summary: str
    confidence: float
```

Rules:

- `feature_path` must point to an actual Creative DNA field or performance evidence field;
- `end_ms >= start_ms`;
- evidence IDs must resolve to the same workspace;
- no arbitrary external evidence ID;
- performance evidence is optional in V1.

## 8.7 Temporal sequence contract

```python
class PatternSequenceBeatV1(BaseModel):
    beat_id: str
    order: int
    beat_type: Literal[
        "hook",
        "problem",
        "product_reveal",
        "demo",
        "proof",
        "offer",
        "cta",
        "reaction",
        "transition",
        "other"
    ]
    purpose: str
    recommended_start_ms_min: int | None
    recommended_start_ms_max: int | None
    recommended_duration_ms_min: int | None
    recommended_duration_ms_max: int | None
    requiredness: Literal["required", "recommended", "optional"]
    evidence_refs: list[PatternEvidenceRefV1]
    confidence: float
```

Sequence rules:

- order starts at 1 and is contiguous;
- duplicate `beat_id` is invalid;
- required beats require evidence or explicit human-authored origin;
- timing ranges cannot be fabricated when source evidence has no timing;
- when sources conflict, store a range or variants and record uncertainty.

## 8.8 Pattern component contracts

### OpeningPatternV1

```text
primary_hook_types[]
hook_mechanism
opening_visual_pattern
first_three_second_structure
face_presence_preference
product_presence_preference
pattern_interrupt_strategy
evidence_refs[]
confidence
uncertainties[]
```

### ProductRevealPatternV1

```text
first_appearance_window_ms
preferred_shot_types[]
close_up_expectation
usage_visibility_expectation
screen_time_guidance
reveal_role
product_match_requirement
evidence_refs[]
confidence
uncertainties[]
```

### NarrativePatternV1

```text
structures[]
angle_family
buyer_pain_pattern
desired_outcome_pattern
emotional_drivers[]
awareness_stage
narrative_progression[]
evidence_refs[]
confidence
uncertainties[]
```

### DemoPatternV1

```text
demo_types[]
mechanism_pattern
required_steps[]
before_state_expectation
after_state_expectation
result_visibility_expectation
continuity_expectation
demo_failure_modes[]
evidence_refs[]
confidence
uncertainties[]
```

### ProofPatternV1

```text
proof_types[]
proof_mechanism
verifiability_requirement
proof_timing_guidance
proof_strength_conditions[]
unsupported_proof_risks[]
evidence_refs[]
confidence
uncertainties[]
```

### CreatorPatternV1

```text
creator_personas[]
delivery_styles[]
face_presence_preference
speaking_preference
emotion_range[]
pacing_preference
authenticity_cues[]
sales_language_intensity
creator_constraints[]
evidence_refs[]
confidence
uncertainties[]
```

### EditingPatternV1

```text
pacing
cut_density
first_three_second_cut_guidance
caption_density
transition_types[]
pattern_interrupt_guidance[]
dead_air_tolerance
visual_safe_zone_guidance[]
evidence_refs[]
confidence
uncertainties[]
```

### OfferPatternV1

```text
offer_required
offer_types[]
offer_positioning_pattern
offer_timing_guidance
urgency_policy
price_display_policy
commerce_constraints[]
evidence_refs[]
confidence
uncertainties[]
```

### CtaPatternV1

```text
cta_required
cta_types[]
modalities[]
product_tag_expectation
cta_timing_guidance
cta_language_pattern
cta_failure_modes[]
evidence_refs[]
confidence
uncertainties[]
```

## 8.9 Applicability contract

```python
class PatternApplicabilityV1(BaseModel):
    suitable_categories: list[str]
    unsuitable_categories: list[str]
    required_product_traits: list[str]
    preferred_product_traits: list[str]
    buyer_contexts: list[str]
    markets: list[str]
    platforms: list[str]
    objectives: list[str]
    fulfillment_constraints: list[str]
    compliance_sensitivities: list[str]
    pod_context: PodApplicabilityV1 | None
    dropshipping_context: DropshippingApplicabilityV1 | None
```

`PodApplicabilityV1`:

```text
recipient_types[]
occasions[]
personalization_requirements[]
identity_cues[]
emotional_payoff_patterns[]
mockup_accuracy_risks[]
```

`DropshippingApplicabilityV1`:

```text
visual_demo_required
trust_mechanisms[]
shipping_promise_constraints[]
quality_proof_requirements[]
margin_or_offer_constraints[]
claim_risks[]
```

## 8.10 Adaptation policy contract

```python
class PatternAdaptationInstructionV1(BaseModel):
    element_path: str
    instruction_type: Literal["keep", "change", "avoid"]
    instruction: str
    rationale: str
    evidence_refs: list[PatternEvidenceRefV1]
    severity: Literal["hard", "high", "medium", "low"]
```

Rules:

- `keep` means retain structural mechanism, not exact wording or exact scene replication;
- `change` identifies product-, buyer-, creator-, market-, or offer-specific elements;
- `avoid` includes exact scripts, unique visual identity, unsupported claims, misleading proof, and category-inappropriate mechanics;
- exact competitor wording must not be emitted as a reusable instruction unless the user owns it and explicitly marks it authorized.

## 8.11 Performance evidence contract

V1 stores optional evidence; it does not train or predict automatically.

```python
class PatternPerformanceSummaryV1(BaseModel):
    evidence_status: Literal["none", "directional", "supported"]
    asset_count: int
    campaign_count: int
    date_range_start: date | None
    date_range_end: date | None
    metrics: list[PatternMetricSummaryV1]
    caveats: list[str]
    confidence: Literal["low", "medium", "high"]
```

`PatternMetricSummaryV1`:

```text
metric_name
sample_size
median
mean
p25
p75
unit
source
```

Rules:

- no `winning` label when `evidence_status=none`;
- `directional` must display sample-size caveat;
- `supported` requires configured minimum sample criteria, documented in code and tests;
- correlation is not causal proof;
- performance data stays workspace-private.

## 8.12 PatternKitV1 final output

```json
{
  "schema_version": "pattern_kit_v1",
  "id": "uuid",
  "workspace_id": "uuid",
  "version": 1,
  "name": "Problem → Fast Reveal → Observable Transformation",
  "summary": "A problem-first structure with early product reveal, visible product use, and observable result proof.",
  "kind": "multi_asset_cluster",
  "scope": "workspace_private",
  "status": "candidate",
  "source": {
    "creative_dna_version_ids": ["uuid", "uuid"],
    "source_asset_count": 2,
    "source_category_count": 1,
    "extraction_mode": "ai_assisted"
  },
  "sequence": [],
  "opening": {},
  "product_reveal": {},
  "narrative": {},
  "demo": {},
  "proof": {},
  "creator": {},
  "editing": {},
  "offer": {},
  "cta": {},
  "applicability": {},
  "adaptation_instructions": [],
  "performance_summary": {
    "evidence_status": "none",
    "asset_count": 0,
    "campaign_count": 0,
    "metrics": [],
    "caveats": ["No performance data is linked yet."],
    "confidence": "low"
  },
  "overall_confidence": "medium",
  "uncertainties": [],
  "created_by": "uuid",
  "created_at": "2026-07-30T00:00:00Z",
  "provenance": {
    "taxonomy_version": "creative_dna_taxonomy_v1",
    "model_run_id": "uuid",
    "prompt_version": "pattern_kit_extraction_v1"
  }
}
```

## 8.13 PatternKit persistence

Add:

```text
pattern_kits
- id
- workspace_id
- name
- kind
- scope
- status
- latest_version
- created_by
- created_at
- updated_at
- archived_at

pattern_kit_versions
- id
- pattern_kit_id
- workspace_id
- version
- schema_version
- pattern_json JSONB
- overall_confidence
- model_run_id nullable
- created_by
- created_at

pattern_kit_sources
- id
- pattern_kit_version_id
- creative_dna_version_id
- asset_version_id
- source_order

pattern_kit_evidence_links
- id
- pattern_kit_version_id
- evidence_id
- feature_path

pattern_kit_actions
- id
- pattern_kit_id
- version
- action(reviewed, validated, deprecated, archived, restored)
- reason
- actor_user_id
- created_at
```

Constraints:

- unique `(pattern_kit_id, version)`;
- versions immutable;
- all rows repeat workspace_id for safe scoping;
- no cascade that silently removes historical source provenance;
- deleting a source asset must follow documented deletion policy and mark affected pattern provenance unavailable or delete the entire dependent artifact when required by user deletion rights.

## 8.14 PatternKit API

```text
POST   /api/v1/workspaces/{workspace_id}/pattern-kits
GET    /api/v1/workspaces/{workspace_id}/pattern-kits
GET    /api/v1/workspaces/{workspace_id}/pattern-kits/{pattern_kit_id}
GET    /api/v1/workspaces/{workspace_id}/pattern-kits/{pattern_kit_id}/versions
GET    /api/v1/workspaces/{workspace_id}/pattern-kits/{pattern_kit_id}/versions/{version}
POST   /api/v1/workspaces/{workspace_id}/pattern-kits/{pattern_kit_id}/versions
POST   /api/v1/workspaces/{workspace_id}/pattern-kits/{pattern_kit_id}/actions
POST   /api/v1/workspaces/{workspace_id}/pattern-kits/{pattern_kit_id}/feedback
DELETE /api/v1/workspaces/{workspace_id}/pattern-kits/{pattern_kit_id}
```

List filters:

```text
status
kind
category
platform
market
objective
source_creative_dna_version_id
created_by
search
```

## 8.15 PatternKit service behavior

`create_pattern_kit()`:

1. authorize workspace;
2. load exact Creative DNA versions;
3. validate evidence links;
4. construct normalized extraction input;
5. call provider only in mock/live modes as configured;
6. validate strict `PatternKitV1` output;
7. run deterministic anti-copy and evidence checks;
8. persist kit, version, sources, evidence links, and model run;
9. emit `pattern_kit_created` event;
10. return typed response.

`create_pattern_kit_version()`:

- never mutate the prior version;
- permit user-edited correction or AI-assisted regeneration;
- retain parent version and change reason;
- emit a version-created event.

---

# 9. ViralKit V1 — authoritative domain design

## 9.1 Definition

ViralKit is a product-specific, test-ready creative hypothesis package compiled from:

```text
Product Context snapshot
+ one or more PatternKit versions
+ target buyer
+ objective
+ platform/market
+ seller constraints
+ creator/production constraints
```

It answers:

> For this exact product and objective, which differentiated creative concepts should be tested, why, under which constraints, and how will execution be validated?

ViralKit is not:

- a virality guarantee;
- a generic hook generator;
- a duplicate of Adaptation;
- a duplicate of Campaign Pack;
- a TikTok Ads campaign;
- an unstructured idea dump;
- a package of near-identical concepts.

## 9.2 ViralKit lifecycle

```text
draft
generating
ready_for_review
concept_selected
production_ready
testing
completed
archived
failed
```

## 9.3 ViralKitCreateRequestV1

```json
{
  "product_id": "uuid",
  "expected_product_context_version": 3,
  "pattern_kit_version_ids": ["uuid"],
  "objective": "tiktok_shop_affiliate_test",
  "platform": "tiktok_shop",
  "target_market": "US",
  "buyer_persona_id": "busy_college_student",
  "creator_constraints": {
    "allowed_personas": ["student_lifestyle", "faceless_demo"],
    "disallowed_personas": [],
    "delivery_style_preferences": ["authentic_review", "demonstration"]
  },
  "production_constraints": {
    "max_duration_ms": 20000,
    "required_aspect_ratio": "9:16",
    "raw_footage_required": false,
    "concept_preview_requested": false
  },
  "commercial_constraints": {
    "offer_required": false,
    "product_tag_required": true,
    "shipping_claim_policy": "use_product_context_only"
  },
  "concept_count": 3,
  "notes": "Test an early product reveal without copying the source script."
}
```

Validation:

- product belongs to workspace;
- expected product version matches current or request fails with conflict;
- PatternKit versions belong to workspace and are not archived;
- exactly three concepts for V1;
- platform and market required;
- objective must be known enum;
- constraints cannot contradict Product Context governance;
- user cannot weaken prohibited-claim rules;
- product-tag requirement can be true only for applicable objectives/platforms;
- selected PatternKits must have at least one applicability match or a documented override reason.

## 9.4 Supported objectives

```text
tiktok_shop_affiliate_test
tiktok_shop_organic_test
small_paid_test
spark_candidate
ugc_paid_asset
pod_gift_campaign
dropshipping_demo_test
creative_refresh
```

No budget allocation or media buying is performed.

## 9.5 Pattern match result

```python
class ViralKitPatternMatchV1(BaseModel):
    pattern_kit_version_id: UUID
    match_score: float
    applicability_status: Literal["matched", "partial", "override", "rejected"]
    matched_product_traits: list[str]
    conflicts: list[str]
    selection_reason: str
    evidence_summary: list[str]
```

Rules:

- match score is deterministic/rubric-backed, not an arbitrary LLM number;
- hard contraindication produces rejected unless user explicitly records an allowed override and no governance rule is violated;
- matching considers product demo potential, category, market, objective, buyer, creator feasibility, fulfillment, and claims.

## 9.6 ViralKit adaptation plan

```python
class ViralKitAdaptationPlanV1(BaseModel):
    keep: list[AdaptationDecisionV1]
    change: list[AdaptationDecisionV1]
    avoid: list[AdaptationDecisionV1]
```

`AdaptationDecisionV1`:

```text
element_path
decision
source_pattern_kit_version_ids[]
product_context_paths[]
rationale
severity
evidence_refs[]
```

Example:

```json
{
  "element_path": "demo.mechanism",
  "decision": "keep",
  "source_pattern_kit_version_ids": ["uuid"],
  "product_context_paths": ["creative_context.visual_demo_potential"],
  "rationale": "The product supports an observable in-use transformation.",
  "severity": "high",
  "evidence_refs": []
}
```

## 9.7 ViralKitConceptV1

Exactly three concepts must be generated.

```python
class ViralKitConceptV1(BaseModel):
    id: str
    name: str
    strategic_axis: str
    diversity_axes: list[Literal[
        "buyer_persona",
        "buyer_pain",
        "awareness_stage",
        "hook_mechanism",
        "creator_persona",
        "delivery_style",
        "narrative_structure",
        "demo_mechanism",
        "proof_mechanism",
        "offer_framing",
        "cta_strategy"
    ]]
    buyer_persona_id: str
    buyer_persona_label: str
    buyer_pain: str
    desired_outcome: str
    awareness_stage: str | None
    creative_angle: str
    hook: ViralKitHookV1
    opening_visual: str
    narrative_structure: str
    creator_persona: str
    delivery_style: str
    demo_mechanism: str
    proof_mechanism: str
    offer_framing: str | None
    cta_strategy: str
    must_show: list[ViralKitRequirementDraftV1]
    overlays: list[str]
    spoken_lines: list[str]
    claims_to_avoid: list[str]
    required_disclosures: list[str]
    test_hypothesis: str
    expected_learning: str
    feasibility: Literal["high", "medium", "low"]
    risks: list[ViralKitRiskV1]
    source_pattern_kit_version_ids: list[UUID]
    evidence_refs: list[PatternEvidenceRefV1]
    confidence: Literal["low", "medium", "high"]
```

`ViralKitHookV1`:

```text
hook_type
spoken_text nullable
overlay_text nullable
opening_visual
target_time_ms
product_present
buyer_pain
```

`ViralKitRequirementDraftV1`:

```text
id
requirement_type
instruction
required
severity
expected_before_ms nullable
matcher_hint
```

`ViralKitRiskV1`:

```text
code
severity
message
source
mitigation
```

## 9.8 Concept diversity rules

All three concepts must satisfy:

- each pair differs across at least two meaningful diversity axes;
- changing only wording is invalid;
- changing only creator persona is insufficient;
- buyer persona must remain separate from creator persona;
- at least one concept tests a different hook mechanism;
- at least one concept tests a different demo, proof, or narrative mechanism;
- concepts must remain feasible for the Product Context;
- no concept may violate claims, required disclosures, fulfillment, or platform constraints;
- duplicate or semantically near-duplicate concepts fail validation and must be regenerated.

## 9.9 Test matrix contract

```python
class ViralKitTestMatrixV1(BaseModel):
    primary_hypothesis: str
    concepts: list[ViralKitTestCellV1]
    controlled_variables: list[str]
    intentionally_changed_variables: list[str]
    recommended_test_order: list[str]
    decision_criteria: list[ViralKitDecisionCriterionV1]
```

`ViralKitTestCellV1`:

```text
concept_id
hypothesis
changed_axes[]
held_constant[]
minimum_execution_requirements[]
metrics_to_observe[]
```

`ViralKitDecisionCriterionV1`:

```text
criterion
signal_type(structural, behavioral, commercial)
comparison
caveat
```

Private beta does not claim statistical significance automatically.

## 9.10 Campaign Pack compilation plan

ViralKit stores references to Campaign Packs; it does not embed and mutate the entire Campaign Pack as its own business logic.

For each concept:

```text
ViralKit concept
→ Adaptation output contract
→ Campaign Pack service
→ CampaignPackBriefV1
→ CompiledRequirementsSnapshotV2
```

Required link fields:

```text
concept_id
campaign_pack_id
campaign_pack_version_id
compiled_requirements_schema_version
created_at
```

Campaign Pack remains the authoritative production brief.

## 9.11 Preflight requirement snapshot

ViralKit retains a read-only summary of expected evaluation classes per concept:

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
offer_before_cta
creator_style_match
prohibited_claim_absence
required_disclosure_presence
allowed_claim_qualification
```

The authoritative compiled requirements are created by Campaign Pack and stored with its version. ViralKit references them.

## 9.12 Generation brief for Seedream/Seedance

This is optional and feature-flagged. It is for concept preview, not final ad production.

```python
class GenerationBriefV1(BaseModel):
    concept_id: str
    purpose: Literal["storyboard_preview", "concept_video_preview"]
    aspect_ratio: Literal["9:16", "1:1", "16:9"]
    duration_ms: int | None
    product_asset_ids: list[UUID]
    reference_asset_ids: list[UUID]
    scenes: list[GenerationSceneV1]
    consistency_constraints: list[str]
    negative_constraints: list[str]
    overlay_instructions: list[str]
    audio_direction: str | None
    claim_guardrails: list[str]
    rights_confirmation_required: bool
```

`GenerationSceneV1`:

```text
scene_id
order
start_ms nullable
end_ms nullable
purpose
visual_prompt
camera_direction
product_visibility
creator_direction
overlay_text nullable
spoken_direction nullable
reference_asset_ids[]
```

Rules:

- generation requires authorized product/reference assets;
- no face/voice cloning without separate consent;
- concept preview remains labeled AI-generated;
- generated preview can be sent through Preflight but must carry generation provenance.

## 9.13 ViralKitV1 final output

```json
{
  "schema_version": "viral_kit_v1",
  "id": "uuid",
  "workspace_id": "uuid",
  "version": 1,
  "status": "ready_for_review",
  "product": {
    "product_id": "uuid",
    "product_context_version": 3,
    "snapshot": {}
  },
  "objective": "tiktok_shop_affiliate_test",
  "platform": "tiktok_shop",
  "target_market": "US",
  "buyer_context": {},
  "constraints": {
    "creator": {},
    "production": {},
    "commercial": {},
    "governance": {}
  },
  "pattern_matches": [],
  "adaptation_plan": {
    "keep": [],
    "change": [],
    "avoid": []
  },
  "concepts": [],
  "test_matrix": {},
  "selected_concept_id": null,
  "campaign_pack_links": [],
  "preflight_requirement_links": [],
  "generation_briefs": [],
  "risks": [],
  "overall_confidence": "medium",
  "uncertainties": [],
  "provenance": {
    "pattern_kit_version_ids": ["uuid"],
    "adaptation_schema_version": "adaptation_v2",
    "model_run_id": "uuid",
    "prompt_version": "viral_kit_composer_v1"
  },
  "created_by": "uuid",
  "created_at": "2026-07-30T00:00:00Z"
}
```

## 9.14 ViralKit persistence

Add:

```text
viral_kits
- id
- workspace_id
- product_id
- name
- objective
- platform
- target_market
- status
- latest_version
- selected_concept_id nullable
- created_by
- created_at
- updated_at
- archived_at

viral_kit_versions
- id
- viral_kit_id
- workspace_id
- version
- schema_version
- product_context_version
- product_snapshot_json JSONB
- viral_kit_json JSONB
- model_run_id nullable
- created_by
- created_at

viral_kit_pattern_links
- id
- viral_kit_version_id
- pattern_kit_version_id
- match_score
- applicability_status
- selection_reason

viral_kit_concept_actions
- id
- viral_kit_id
- viral_kit_version
- concept_id
- action(selected, rejected, restored, campaign_pack_created)
- reason nullable
- actor_user_id
- created_at

viral_kit_campaign_pack_links
- id
- viral_kit_version_id
- concept_id
- campaign_pack_id
- campaign_pack_version_id
- created_at
```

Constraints:

- unique `(viral_kit_id, version)`;
- selected concept must exist in latest version;
- version is immutable;
- exact PatternKit versions are retained;
- all links are workspace-scoped;
- product snapshot cannot be updated after version creation.

## 9.15 ViralKit API

```text
POST   /api/v1/workspaces/{workspace_id}/viral-kits
GET    /api/v1/workspaces/{workspace_id}/viral-kits
GET    /api/v1/workspaces/{workspace_id}/viral-kits/{viral_kit_id}
GET    /api/v1/workspaces/{workspace_id}/viral-kits/{viral_kit_id}/versions
GET    /api/v1/workspaces/{workspace_id}/viral-kits/{viral_kit_id}/versions/{version}
POST   /api/v1/workspaces/{workspace_id}/viral-kits/{viral_kit_id}/versions
POST   /api/v1/workspaces/{workspace_id}/viral-kits/{viral_kit_id}/concept-actions
POST   /api/v1/workspaces/{workspace_id}/viral-kits/{viral_kit_id}/concepts/{concept_id}/campaign-pack
POST   /api/v1/workspaces/{workspace_id}/viral-kits/{viral_kit_id}/feedback
DELETE /api/v1/workspaces/{workspace_id}/viral-kits/{viral_kit_id}
```

Create returns `202` with a job when AI generation is async, or `201` only in deterministic fixture mode when completed synchronously by existing conventions.

## 9.16 ViralKit service behavior

`create_viral_kit()`:

1. authorize workspace;
2. load exact Product Context version and create snapshot;
3. load exact PatternKit versions;
4. run deterministic applicability matcher;
5. reject hard conflicts;
6. build strict composer input;
7. generate exactly three concepts;
8. validate concept diversity;
9. validate buyer/creator separation;
10. validate product, commercial, fulfillment, and claim constraints;
11. persist version and links;
12. emit `viral_kit_created` event;
13. return typed output.

`select_concept()`:

- verify concept exists in current version;
- persist separate action;
- update current selected concept projection;
- emit `concept_selected`;
- do not delete rejected concepts.

`create_campaign_pack_from_concept()`:

- call Campaign Pack public service boundary;
- pass exact product snapshot, concept, PatternKit provenance, and governance constraints;
- store link;
- return typed Campaign Pack response.

---

# 10. Fixture behavior for PatternKit and ViralKit

Fixture output must be category-neutral and generated from the input contracts. Do not hardcode kitchen, beauty, pet, fashion, or POD-specific content into business logic.

Provide deterministic fixtures for at least:

```text
home_organization
a beauty accessory
POD personalized gift
pet accessory
fashion accessory
```

Fixture tests must prove:

- no cross-category leakage;
- PatternKit evidence points to the correct DNA sources;
- ViralKit product facts come from Product Context;
- exactly three diverse concepts;
- buyer persona is not creator persona;
- prohibited claims are preserved;
- required disclosures are preserved;
- product-tag requirements are objective/platform dependent;
- generated requirements compile successfully.

---

# 11. Core backend module input/output completion

The following existing modules must remain authoritative and integrate with PatternKit/ViralKit.

## 11.1 References

Input:

```text
board_id
product_id optional
source_platform
source_url optional
asset_id optional
notes optional
```

Output:

```text
reference_id
source metadata
processing status
latest asset version
latest Creative DNA version
PatternKit usage links
created_by
created_at
```

## 11.2 Adaptation

Input:

```text
product snapshot
Creative DNA version
optional PatternKit versions
buyer context
objective
seller constraints
```

Output exactly three concepts compatible with `ViralKitConceptV1` or an explicit shared public concept contract.

Do not create two competing concept contracts. Reuse one public contract or create a stable adapter.

## 11.3 Creative Campaign Pack

Input:

```text
product snapshot
selected ViralKit concept
PatternKit provenance
objective
creator direction
rights notes
claim governance
```

Output:

```text
CampaignPackBriefV1
compiled requirements V2
product snapshot
source ViralKit ID/version/concept ID
source PatternKit versions
```

Do not convert spoken hooks into required overlays.

## 11.4 TikTok scorer

Input:

```text
evidence items
product context present flag
media duration
```

Output per dimension:

```text
score
reason
signals
missing_signals
confidence
evidence_ids
```

No LLM score.

## 11.5 Preflight

Input:

```text
structural score result
compiled Campaign Pack requirements
evidence
product snapshot
media duration
```

Output:

```text
structural_score
brief_alignment_score
preflight_score
requirement evaluations
blockers
fixes
action
revision message
```

Formula remains:

```text
80% structural readiness
20% exact brief alignment
```

Hard requirements that are `missing`, `violated`, or `unknown` cannot lead to approval.

---

# 12. Recommendations, seller actions, and correction data

## 12.1 Recommendation persistence

Store:

```text
source artifact IDs
source artifact versions
action
reason
confidence
evidence IDs
blockers
fixes
rule/rubric/model/prompt/schema versions
created_at
```

Supported seller actions:

```text
viewed
accepted
rejected
applied
ignored
```

Seller actions are append-only and separate from AI output.

## 12.2 Field-level feedback

Subjects:

```text
Creative DNA
PatternKit
ViralKit
TikTok score
Preflight
Recommendation
```

Fields:

```text
subject_type
subject_id
subject_version nullable
field_path
feedback_type
ai_value_json
user_value_json
comment
model_run_id
created_by
created_at
```

Feedback types:

```text
correct
incorrect
partial
missing
false_positive
false_negative
not_useful
```

## 12.3 Required product events

```text
user_signed_up
workspace_created
product_created
reference_uploaded
reference_analyzed
creative_dna_viewed
creative_dna_corrected
pattern_kit_created
pattern_kit_version_created
pattern_kit_reviewed
pattern_kit_validated
pattern_kit_corrected
viral_kit_created
viral_kit_version_created
concept_selected
concept_rejected
campaign_pack_created
campaign_pack_exported
ugc_uploaded
preflight_viewed
recommendation_accepted
recommendation_rejected
recommendation_applied
revision_uploaded
```

Events must be stored first-party in PostgreSQL and exportable by authorized users.

---

# 13. AI provider, model runs, and generation foundation

## 13.1 Provider configuration

```text
AI_MODE
AI_PROVIDER
AI_BASE_URL
AI_API_KEY
AI_TEXT_MODEL
AI_VISION_MODEL
AI_SUPPORTS_JSON_SCHEMA
AI_SUPPORTS_IMAGE_URL
AI_REQUEST_TIMEOUT_SECONDS
AI_MAX_RETRIES
IMAGE_GENERATION_ENABLED
VIDEO_GENERATION_ENABLED
IMAGE_GENERATION_MODEL
VIDEO_GENERATION_MODEL
```

## 13.2 Dola/Seed analysis operations

Define explicit operations:

```text
media_observation
creative_dna_build
pattern_kit_extract
viral_kit_compose
adaptation_generate
campaign_pack_generate
revision_message_generate
```

Each operation must have:

- typed input contract;
- typed output contract;
- prompt version;
- schema version;
- timeout;
- retry policy;
- model-run record;
- mock-provider fixture.

## 13.3 Seedream/Seedance operations

```text
storyboard_image_generate
concept_video_preview_generate
```

Feature flags are off by default.

## 13.4 Model run persistence

```text
provider
model
operation
status
prompt_version
schema_version
input_hash
provider_request_id
latency_ms
attempt_count
usage_json
estimated_cost
error_code
safe_error_message
created_at
completed_at
```

Never persist secrets or full signed URLs.

---

# 14. Jobs and asynchronous flow

Statuses:

```text
queued
running
retrying
succeeded
failed
cancelled
```

Fields:

```text
workspace_id
job_type
subject_type
subject_id
idempotency_key
progress_percent
current_stage
attempt_count
max_attempts
safe_error_code
safe_error_message
created_at
started_at
completed_at
```

Required job types:

```text
media_analysis
creative_dna_build
pattern_kit_extract
viral_kit_compose
campaign_pack_generate
preflight_run
storyboard_generate
concept_video_generate
retention_cleanup
```

Requirements:

- stable IDs only in Celery payloads;
- idempotent processing;
- retries cannot duplicate artifacts or evidence;
- job status endpoint;
- stale-job recovery;
- worker health endpoint;
- remove placeholder naming from production tasks.

---

# 15. API response and error rules

Use the project-standard envelope.

Successful example:

```json
{
  "data": {},
  "meta": {
    "request_id": "uuid"
  }
}
```

Error example:

```json
{
  "error": {
    "code": "PATTERN_KIT_SOURCE_INVALID",
    "message": "One or more Creative DNA versions are unavailable.",
    "details": {}
  },
  "meta": {
    "request_id": "uuid"
  }
}
```

Required domain error codes include:

```text
PATTERN_KIT_SOURCE_INVALID
PATTERN_KIT_EVIDENCE_INVALID
PATTERN_KIT_CONFLICT
PATTERN_KIT_ARCHIVED
VIRAL_KIT_PRODUCT_VERSION_CONFLICT
VIRAL_KIT_PATTERN_INAPPLICABLE
VIRAL_KIT_CONCEPT_DIVERSITY_FAILED
VIRAL_KIT_GOVERNANCE_CONFLICT
VIRAL_KIT_CONCEPT_NOT_FOUND
VIRAL_KIT_CAMPAIGN_PACK_FAILED
```

Do not return raw Pydantic, SQLAlchemy, provider, or stack-trace errors.

---

# 16. Database migration requirements

Add backward-compatible Alembic migrations for:

```text
user identity hardening if required
PatternKit tables
ViralKit tables
feedback
product events
recommendation actions
model runs additions
generation runs if required
job progress/idempotency additions
```

Requirements:

- clean database migrates from zero to head;
- existing development database upgrades without manual SQL;
- no destructive data loss;
- explicit defaults;
- downgrade where safe;
- migration test;
- indexes on workspace and list/filter columns;
- JSONB GIN only where justified;
- unique constraints described above.

---

# 17. Data deletion and retention

Implement:

- delete asset and storage objects;
- delete reference;
- delete Creative DNA;
- delete PatternKit;
- delete ViralKit;
- delete Campaign Pack;
- delete product;
- delete workspace data;
- orphan cleanup;
- retention cleanup.

When deleting a source used by PatternKit/ViralKit:

- honor user deletion rights;
- remove or invalidate dependent artifacts according to documented cascade policy;
- never leave a UI-visible artifact claiming evidence that no longer exists;
- record deletion initiator and timestamp in a minimal audit record when legally/operationally permitted.

Configuration:

```text
ASSET_RETENTION_DAYS
MODEL_OUTPUT_RETENTION_DAYS
MAX_MEDIA_DURATION_SECONDS
MAX_UPLOAD_SIZE_BYTES
```

---

# 18. Health and observability

Provide:

```text
GET /health/live
GET /health/ready
GET /health/dependencies
GET /health/worker
```

Check:

- API;
- database;
- Redis;
- object storage;
- worker;
- AI provider configuration.

Do not expose secrets.

Logs include safe identifiers:

```text
request_id
workspace_id
job_id
model_run_id
release_version
git_sha
```

---

# 19. Evaluation harness

Support:

```text
fixture
mock
live
```

PatternKit metrics:

```text
schema validity
evidence resolution rate
source-field agreement
sequence agreement
applicability agreement
keep/change/avoid reviewer agreement
cross-category leakage
unsupported generalization count
```

ViralKit metrics:

```text
schema validity
product-grounding rate
constraint preservation
concept diversity pass rate
buyer/creator separation
claim/disclosure preservation
PatternKit traceability
Campaign Pack compile rate
Preflight requirement compile rate
human concept usefulness
```

Existing media/Creative DNA/Preflight metrics remain:

```text
timestamp accuracy
hook agreement
product detection
demo/proof agreement
CTA/offer agreement
claim agreement
blocker agreement
action agreement
hallucination count
latency
cost estimate
```

Generate JSON and Markdown reports. Do not use exact prose match as the primary metric.

---

# 20. Automated test matrix

## 20.1 Auth and tenancy

- all auth cases from section 4;
- all RBAC permissions;
- cross-workspace denial for Product, Reference, DNA, PatternKit, ViralKit, Campaign Pack, Preflight, Recommendation, feedback, events, jobs, and model runs.

## 20.2 PatternKit

- single-source candidate;
- multi-source candidate;
- duplicate source rejection;
- cross-workspace source rejection;
- missing evidence rejection;
- timing validation;
- source conflict retained as uncertainty;
- no exact-script copying;
- no winner claim without performance evidence;
- version immutability;
- review/validate/archive state transitions;
- feedback persistence;
- deletion behavior.

## 20.3 ViralKit

- product version conflict;
- PatternKit applicability match;
- hard contraindication rejection;
- exactly three concepts;
- pairwise diversity across at least two axes;
- buyer persona not creator persona;
- governance preservation;
- Product Context grounding;
- concept selection append-only action;
- Campaign Pack creation;
- compiled requirement linkage;
- generation brief feature flag;
- version immutability;
- cross-category fixtures;
- deletion behavior.

## 20.4 E2E

Automate:

```text
Authenticate
→ create workspace
→ create product
→ upload two references
→ media analysis
→ Creative DNA for both
→ create PatternKit
→ review PatternKit
→ create ViralKit
→ select concept
→ create Creative Campaign Pack
→ upload UGC draft
→ structural score
→ exact Preflight
→ recommendation
→ seller action
→ field correction
→ revision upload
→ query events/model runs
→ delete workspace
→ confirm storage cleanup
```

Run in fixture and mock-provider modes.

---

# 21. CI requirements

GitHub CI must run without external provider credentials:

```text
ruff
backend unit tests
backend integration tests
architecture tests
auth tests
tenant isolation tests
clean migration tests
fixture E2E
mock-provider E2E
no-audio regression
frontend lint
frontend build
secret scan
git diff --check
```

Do not claim CI success based only on local runs.

---

# 22. Explicitly out of scope

Do not build:

```text
billing
payments
creator marketplace
creator payouts
full creator CRM
global ad crawler
private API reverse engineering
automatic TikTok/Meta campaign creation
automatic media buying
GMV guarantees
ROAS guarantees
virality guarantees
full video editor
enterprise SSO/SCIM
cross-customer PatternKit sharing
fully automatic statistical winner certification
```

---

# 23. Execution milestones

## S0 — Baseline

- create branch;
- record current tests and migration head;
- write implementation log.

## S1 — Auth and RBAC

- harden OIDC;
- user provisioning;
- workspace permissions;
- isolation tests.

## S2 — Persistence foundations

- feedback;
- events;
- recommendation actions;
- model-run/job additions;
- migrations.

## S3 — PatternKit

- contracts;
- persistence;
- services;
- API;
- fixtures;
- tests.

## S4 — ViralKit

- contracts;
- matcher;
- composer;
- persistence;
- Campaign Pack orchestration;
- API;
- fixtures;
- tests.

## S5 — Provider and async integration

- Dola/Seed operations;
- generation foundation;
- model runs;
- jobs.

## S6 — Deletion, health, evaluation

- deletion/cascade;
- health endpoints;
- evaluation harness.

## S7 — E2E and release

- fixture E2E;
- mock E2E;
- CI;
- audit;
- tag release candidate.

---

# 24. Definition of Done

```text
[ ] Production OIDC verification is secure and tested
[ ] User provisioning is concurrency-safe
[ ] Workspace RBAC and tenant isolation pass
[ ] Product Context snapshots are immutable
[ ] Creative DNA remains typed and evidence-grounded
[ ] PatternKit V1 is fully implemented, not guessed by Codex
[ ] PatternKit stores exact sources, evidence, applicability, adaptation policy, confidence, and optional performance evidence
[ ] PatternKit versions are immutable
[ ] ViralKit V1 is fully implemented, not a generic idea generator
[ ] ViralKit creates exactly three diverse, product-grounded concepts
[ ] ViralKit separates buyer persona from creator persona
[ ] ViralKit preserves claims, disclosures, fulfillment, and product-tag constraints
[ ] ViralKit orchestrates Adaptation and Campaign Pack instead of duplicating them
[ ] Campaign Pack links back to exact ViralKit/PatternKit versions
[ ] Preflight evaluates exact requirements
[ ] Recommendations and seller actions are separate
[ ] AI output and human corrections are separate
[ ] First-party events are persisted and exportable
[ ] Dola/Seed provider is key-ready
[ ] Seedream/Seedance concept-preview foundations are feature-flagged
[ ] Jobs are idempotent and expose progress
[ ] Model runs are traceable
[ ] Data deletion and storage cleanup work
[ ] Evaluation runner covers PatternKit and ViralKit
[ ] Clean migrations pass
[ ] Fixture and mock E2E pass
[ ] GitHub CI passes
[ ] Release tag v0.1.0-beta-rc1 exists
```

---

# 25. Final deliverables

Create:

```text
VIRALDY_PRIVATE_BETA_TECH_FREEZE_AUDIT.md
```

The audit must contain:

1. branch and commit SHA;
2. PR URL;
3. changed files grouped by module;
4. migration list;
5. PatternKit contract summary;
6. ViralKit contract summary;
7. API endpoint list;
8. RBAC matrix;
9. exact test commands and results;
10. CI result;
11. fixture/mock E2E evidence;
12. known limitations;
13. environment variables required for OIDC;
14. environment variables required for Dola/Seed;
15. Seedream/Seedance activation steps;
16. data deletion evidence;
17. any item not completed, with an honest explanation.

Do not claim a capability is complete unless implemented and covered by automated tests.

