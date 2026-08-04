# VIRALDY — M1 + M3 + M4 IMPLEMENTATION GOAL

## Intelligence Orchestration, Progressive Onboarding, and Creative Directions V1

Repository:

- `https://github.com/dhtphu05/viraldy`
- Base branch: `main`
- Target branch: `feature/intelligence-orchestration-onboarding-directions-v1`

Product:

- Viraldy — vertical Creative Intelligence and Creative Operations for TikTok Shop US, POD/personalization, dropshipping, and cross-border ecommerce teams.

This document is an implementation contract for Codex Goal Mode.

---

# 0. Mission

Implement and production-harden the following milestones as one coherent product slice:

- **M1 — AI prompt and model-output architecture hardening**
- **M3 — Progressive onboarding and Product Context confirmation**
- **M4 — Seller-facing Creative Directions flow backed by internal PatternKit/ViralKit orchestration**

The result must let a newly authenticated seller:

```text
Create or enter a workspace
→ add one product with minimal friction
→ review only decision-critical product facts
→ see readiness by workflow
→ optionally choose references
→ request three Creative Directions
→ review three product-specific concepts
→ select one direction
→ generate a Creator Brief
→ refresh the page and resume from backend-canonical state
```

The seller must not need to understand or manually manage:

```text
PatternKit
ViralKit
prompt versions
schema versions
evidence IDs
provider payloads
internal model runs
```

Those remain internal, versioned, auditable intelligence artifacts.

Do not expand this goal into TikTok Scorer V2, UGC Preflight V2, creator marketplace, billing, performance intelligence, full rights management, or platform integrations.

---

# 1. Mandatory source-of-truth files

Before planning or changing code, confirm that these files are readable from the current repository root:

```text
VIRALDY_OPENAI_PRODUCTION_INTELLIGENCE_AUDIT.md
VIRALDY_OPENAI_NATIVE_PRODUCTION_INTELLIGENCE_SHOWCASE_GOAL.md
VIRALDY_GOLDEN_OUTPUT_REFERENCE_AND_ACCEPTANCE_EXAMPLES.md
```

The third file must be the current **Golden Output V1.0** supplied with this goal.

The current repository may still contain:

```text
VIRALDY_GOLDEN_OUTPUT_REFERENCE_AND_ACCEPTANCE_EXAMPLES_V0_9.md
```

Rules:

1. The exact V1.0 filename above becomes the authoritative semantic baseline.
2. V0.9 may remain only as an archived historical document.
3. Update audits, docs, prompt metadata, fixtures, and test references so they do not identify V0.9 as authoritative.
4. Do not inject either complete Golden document into runtime requests.
5. If the V1.0 file is absent, stop before implementation and report:
   - current branch;
   - repository root;
   - paths searched;
   - exact missing filename.

Read the entire V1.0 Golden Output file before planning implementation.

Use it for:

- domain semantics;
- product-specific personalization;
- Prompt Policy extraction;
- domain-matched examples;
- PatternKit and ViralKit semantics;
- seller-facing presentation;
- deterministic assertions;
- semantic regression cases;
- insufficient-evidence behavior.

Do not use it as a per-request prompt payload.

---

# 2. Current-state constraints

The repository already includes substantial production foundations.

Reuse and harden them rather than creating parallel systems.

Current foundations include, subject to source verification:

```text
FastAPI modular monolith
PostgreSQL + async SQLAlchemy + Alembic
Celery + Redis
S3-compatible object storage
OIDC/local-test auth boundaries
Product Context V1
Product URL crawl preview
Media processing and evidence
Creative DNA
PatternKit V1
ViralKit V1
Campaign Pack
Preflight
OpenAI native Responses API provider
OpenAI-compatible provider
Versioned prompt packages
Strict structured outputs
Model-run provenance
Mock and fixture E2E
Frontend Product Catalog
Guided Production Run
```

Known architectural gaps this goal must address:

1. The model still returns full persisted `PatternKitV1` and `ViralKitV1` objects, including infrastructure-owned fields.
2. Product Context lacks a first-class, field-level verification/provenance layer.
3. Product import is still a flat review form rather than progressive confirmation.
4. Readiness is presented as catalog-level labels rather than deterministic workflow readiness.
5. Seller-facing screens still expose internal PatternKit/ViralKit concepts too directly.
6. Product and production screens still mix backend data with seeded/Zustand mirrors in configured backend mode.
7. Product-first Creative Directions should not require the seller to manually select a PatternKit.
8. The OpenAI implementation is mock-verified but not live-qualified. This goal must not falsely claim live qualification.

---

# 3. Operating rules

1. Audit the current source before modifying it.
2. Extend the Lean Modular Monolith; do not introduce deep DDD folder trees.
3. Cross-module calls must use `public.py`.
4. Do not import another module’s private models, repository, service, or provider.
5. Keep business logic out of routers and React route files.
6. Keep PostgreSQL as the source of truth.
7. Do not store canonical product or creative-plan state only in Zustand, component state, query strings, or local storage.
8. Query strings may hold stable IDs for resumability, but the backend owns the state.
9. Do not duplicate Product Context, PatternKit, ViralKit, Campaign Pack, evidence, jobs, or model-run persistence.
10. Do not create a generic repository, command bus, query bus, event-sourcing platform, or speculative microservices.
11. Every new table or field requires Alembic migration and zero-to-head migration coverage.
12. Every workspace-owned query must be scoped by `workspace_id`.
13. Every AI call must preserve prompt/model/schema/context provenance.
14. Unknown data remains unknown.
15. Imported or AI-inferred data is not equivalent to seller-confirmed data.
16. No universal TikTok timing rule may be invented.
17. No output may promise virality, sales, conversion, GMV, or ROAS.
18. Fixture and mock success must never be reported as real OpenAI qualification.
19. Commit after every completed implementation milestone.
20. Do not stop after defining interfaces or schemas. Complete services, repositories, APIs, frontend integration, tests, and audit evidence.

---

# 4. Branch and milestone commits

Create:

```text
feature/intelligence-orchestration-onboarding-directions-v1
```

Use milestone commits:

```text
M1A  audit current prompt, product, and creative-plan boundaries
M1B  split model-output contracts from persisted domain artifacts
M1C  harden prompt/context compilation and provider execution
M3A  add product verification and workflow-readiness backend
M3B  implement progressive workspace/product onboarding frontend
M4A  implement Creative Directions orchestration and seller-facing API
M4B  implement Creative Directions frontend and Creator Brief handoff
M4C  fixture/mock E2E, regression hardening, and final audit
```

Do not combine unrelated cleanup into these commits.

---

# 5. M1 — AI prompt architecture hardening

## 5.1 Objective

Preserve the current OpenAI-native implementation, but make the semantic boundary safer:

```text
Prompt Compiler
→ semantic model-output contract
→ strict validation
→ deterministic server assembly
→ persisted domain artifact
```

The model must propose semantic content.

The server must own identity, tenancy, versioning, lifecycle, verified source lineage, and provenance.

---

## 5.2 Do not rebuild working M1 foundations

Audit and reuse the current equivalents of:

```text
prompt_packages.py
prompt_content/*
ViraldyOperationContextV1
execute_structured_operation(...)
OpenAI native provider
OpenAI-compatible provider
structured-output validation
request identity
usage/provenance logging
workspace concurrency limiter
```

If an existing abstraction already fulfills a requirement, improve it rather than adding another class with overlapping responsibility.

---

## 5.3 Split model-output contracts from persisted artifacts

### Problem to remove

The model currently receives or returns values such as:

```text
id
workspace_id
version
status
created_by
created_at
model_run_id
performance_summary
product snapshot
provenance
selected concept state
campaign pack links
```

These fields belong to deterministic application code, not the model.

### Required new semantic contracts

Implement typed model-output contracts, naming may vary only if the chosen names are clearer:

```text
PatternKitModelOutputV2
ViralKitModelOutputV2
CampaignPackModelOutputV2
```

At minimum implement the first two in this goal.

### `PatternKitModelOutputV2`

It may contain only semantic judgments:

```text
name suggestion
summary
sequence
opening pattern
product reveal observations and reusable guidance
narrative pattern
demo pattern
proof pattern
creator pattern
editing pattern
offer pattern
CTA pattern
applicability
contraindications
keep/change/avoid instructions
uncertainties
semantic confidence
```

It must not contain:

```text
pattern_kit_id
workspace_id
version
status
source IDs not supplied by the server
created_by
created_at
model_run_id
performance evidence
verified metrics
lifecycle transition
```

### `ViralKitModelOutputV2`

It may contain:

```text
pattern-product semantic match explanations
adaptation plan
exactly three concepts
test hypotheses
expected learning
test matrix
production requirement drafts
generation brief drafts
risks
uncertainties
semantic confidence
```

It must not contain:

```text
viral_kit_id
workspace_id
version
product snapshot
selected_concept_id
campaign pack links
created_by
created_at
model_run_id
verified provenance
status transition
```

### Server assemblers

Implement deterministic assemblers:

```text
PatternKitAssembler
ViralKitAssembler
```

Responsibilities:

```text
generate IDs
enforce workspace
attach immutable source snapshots
attach exact source version IDs
set initial status
set version
attach verified evidence links
attach verified performance status
attach product snapshot
attach prompt/model/schema provenance
attach created_by and created_at
validate lifecycle invariants
produce persisted PatternKitV1/ViralKitV1
```

The assemblers must reject:

```text
unknown evidence IDs
changed product identity
changed source IDs
invented performance
invalid concept count
insufficient concept diversity
prohibited claims lost during adaptation
required disclosures lost during adaptation
seller-confirmed fields changed by the model
```

### Compatibility

Prefer preserving existing external `PatternKitV1` and `ViralKitV1` API responses.

Provider internals may move to V2 semantic output contracts.

Add compatibility adapters only where needed.

Do not expose new model-draft contracts as seller-facing API objects.

---

## 5.4 Prompt registry and compiler

The target runtime package is:

```text
Canonical System Policy
+ one Operation Prompt
+ zero or one applicable Domain Overlay
+ bounded typed runtime context
+ zero or one domain-matched example by default
+ strict output schema
```

Two examples may be used only when explicitly justified by the operation’s prompt specification and token budget.

### Required contracts

Implement or extend:

```python
PromptSpec
CompiledPromptPackage
PromptContextManifestV1
PromptExampleRefV1
PromptBudgetV1
ProviderCapabilities
```

A `PromptSpec` must declare:

```text
operation
system prompt version
operation prompt version
semantic output contract
output schema version
allowed domain overlays
example policy
maximum examples
input budget
output budget
reasoning profile
repair policy
```

### `PromptContextManifestV1`

Persist enough information to reproduce why the output changed:

```text
operation
workspace_id
product_id
product_context_version
source version IDs
evidence IDs
selected PatternKit version IDs
selected reference IDs
domain overlay IDs and versions
example IDs
seller-supplied constraint keys
prompt version
schema version
model profile
context hash
```

Do not store secrets or full signed URLs.

### Context compiler

The compiler must include only data needed by the operation.

Examples:

```text
PatternKit:
Creative DNA source summaries
allowed evidence catalog
source taxonomy versions
requested applicability

ViralKit:
immutable Product Context snapshot
selected/retrieved PatternKit snapshots
objective
buyer selection
seller constraints
governance
reference provenance

Campaign Pack:
selected concept
Product Context snapshot
production and governance constraints
```

The compiler must not include:

```text
entire workspace history
entire Golden Output file
unrelated products
unrelated PatternKits
raw database models
raw object-storage credentials
```

### Domain overlays in this goal

Create an extension-ready selector for:

```text
tiktok_shop_us
pod_personalization
dropshipping
```

The initial overlays may contain only behavior already authorized by:

```text
Golden Output V1.0
existing typed Product Context
existing deterministic rules
```

Do not promote blog advice, seller anecdotes, or incomplete expert research into a hard blocker.

Future `DomainExpertPolicyPack` integration must be possible without rewriting the compiler.

Do not implement the full expert-policy management module in this goal.

---

## 5.5 OpenAI and provider behavior

Preserve:

```text
OpenAI Responses API
strict structured output
store=false
bounded retries
one targeted repair at most
refusal handling
incomplete-output handling
usage and latency capture
request identity
workspace concurrency controls
no silent fallback
```

Add or preserve a provider-neutral interface:

```python
class StructuredModelProvider(Protocol):
    async def generate_structured(...): ...
```

The OpenAI-compatible path must use the same semantic output contracts and deterministic assemblers.

Do not allow provider-specific code to assemble database domain artifacts.

---

## 5.6 Semantic repair behavior

Validation order:

```text
JSON/SDK structured parse
→ Pydantic semantic-output validation
→ evidence validation
→ product-fact validation
→ operation semantic validation
→ deterministic assembly
→ persisted artifact validation
```

Only one targeted repair is allowed when:

```text
required semantic field missing
invalid enum
unsupported evidence reference
concept diversity invalid
semantic structure internally inconsistent
```

A repair request must include:

```text
original model output
machine-readable validation issues
relevant schema
minimum relevant context
```

Do not repeat the entire initial prompt unless technically necessary.

Do not retry simply because prose is not attractive.

---

## 5.7 M1 tests

Add tests proving:

```text
model cannot set PatternKit ID/workspace/version/status
model cannot create performance evidence
model cannot change Product Context identity
model cannot set ViralKit selected concept
server assembler attaches exact source lineage
server assembler attaches exact product snapshot
unknown evidence IDs fail
exactly three concepts are enforced
concept diversity is enforced
buyer persona remains separate from creator persona
required disclosures propagate
prohibited claims propagate
prompt package selects bounded examples
Golden file is not injected into runtime
prompt/context hash changes when relevant context changes
prompt/context hash is stable for equivalent canonical input
OpenAI and compatible provider share semantic contract behavior
one repair attempt is bounded
provider failure does not create a completed artifact
```

---

# 6. M3 — Progressive onboarding and Product Context confirmation

## 6.1 Product principle

Do not require a seller to complete a large Product Context form before receiving value.

Use:

```text
Value first
→ confirm critical facts
→ enrich context just in time
```

The user should be able to save a product with unknown optional fields.

Each workflow decides which fields are required.

---

## 6.2 Onboarding stages

Implement a backend-canonical onboarding state machine:

```text
workspace_created
→ workspace_defaults_confirmed
→ first_product_added
→ critical_product_facts_reviewed
→ first_job_selected
→ activated
```

The user may leave and resume.

Do not store the canonical onboarding stage only in the frontend.

### Minimal workspace defaults

Ask only:

```text
business model
primary target market
seller-facing language
creator-message language
default intended use
```

Supported business models:

```text
tiktok_shop_seller
pod_personalization
dropshipping
agency_operator
other
```

Do not ask for economics, rights, inventory, or detailed creator policy during first-run onboarding.

Create typed contracts such as:

```text
WorkspaceOnboardingStateV1
WorkspaceDefaultsV1
```

Prefer a dedicated module or a small extension of the workspace module, whichever best preserves current boundaries.

---

## 6.3 Product intake entry points

Implement in this goal:

```text
Paste public product URL
Create manually
```

Keep extension points for:

```text
CSV import
store connector
```

Do not implement catalog bulk intelligence or official store integrations.

Reuse the current product crawl preview.

Do not rewrite the crawler unless a bug blocks the onboarding flow.

---

## 6.4 Field-level verification without breaking ProductContextV1

Keep `ProductContextV1` as the typed business-value contract.

Do not wrap every Product Context value in a nested generic verification object.

Instead, add a separate typed verification layer keyed by JSON field path.

### Required verification record

Implement a table and contract equivalent to:

```text
product_context_field_verifications
```

Fields:

```text
id
workspace_id
product_id
product_context_version
field_path
status
source_type
source_reference
source_value_hash
confidence
confirmed_value_hash
confirmed_by_user_id
confirmed_at
observed_at
expires_at
conflict_reason
created_at
updated_at
```

Statuses:

```text
unknown
imported
ai_inferred
seller_confirmed
system_verified
conflicted
expired
```

Source types:

```text
manual
product_url
crawler
model
seller
system
connector
```

Rules:

1. Imported and AI-inferred fields are not seller-confirmed.
2. Seller confirmation is attached to the exact Product Context version and value hash.
3. Updating a confirmed value creates a new Product Context version.
4. Confirmations whose value hash no longer matches become expired or superseded.
5. Conflicted critical fields cannot silently become ready.
6. Unknown optional fields do not block unrelated workflows.
7. Verification metadata is workspace-scoped.
8. Product deletion removes verification rows through documented cascade behavior.

---

## 6.5 Critical fields by workflow

Implement deterministic readiness profiles.

### `creative_dna`

Minimum:

```text
product identity optional
asset required elsewhere
```

Product-specific checks may be unknown when no Product Context is attached.

### `creative_directions`

Minimum:

```text
identity.name
identity.category
identity.market
at least one buyer persona or explicit target-buyer description
at least one product feature or benefit
at least one demonstration mechanism, visual differentiator, or explicit no-demo constraint
```

Decision-critical confirmations:

```text
identity
market
product mechanism when used in a concept
personalization values when applicable
```

### `creator_brief`

Minimum:

```text
creative_directions readiness
selected concept
approved offer or explicit no-offer
governance reviewed
required disclosures reviewed
personalization values confirmed when applicable
```

### `ugc_preflight`

Minimum:

```text
creator brief version
compiled requirements
Product Context snapshot
UGC asset version
```

Do not reimplement Preflight in this goal.

### `paid_use_decision`

May require later:

```text
rights
economics
budget
inventory
```

This workflow remains out of scope beyond a readiness placeholder.

---

## 6.6 `ProductWorkflowReadinessV1`

Implement deterministic output:

```python
class ProductWorkflowReadinessV1(BaseModel):
    workflow: str
    status: Literal[
        "ready",
        "needs_confirmation",
        "blocked",
        "not_applicable",
    ]
    missing_fields: list[str]
    unconfirmed_fields: list[str]
    conflicted_fields: list[str]
    blocker_codes: list[str]
    explanation: str
    next_questions: list[ProductContextQuestionV1]
```

Do not expose one generic “62% complete” score as the primary UX.

Expose:

```text
Ready for Creative DNA
Needs 2 confirmations for Creative Directions
Blocked for Creator Brief: offer and disclosure not confirmed
Paid-use decision not evaluated
```

---

## 6.7 Just-in-time questions

Implement endpoint behavior equivalent to:

```text
GET  /workspaces/{workspace_id}/products/{product_id}/readiness
GET  /workspaces/{workspace_id}/products/{product_id}/readiness/{workflow}
GET  /workspaces/{workspace_id}/products/{product_id}/next-questions?workflow=...
POST /workspaces/{workspace_id}/products/{product_id}/confirm-fields
```

`confirm-fields` input:

```text
expected_product_context_version
confirmations[]
```

Each confirmation:

```text
field_path
expected_value_hash
action:
  confirm
  replace
  mark_unknown
replacement_value optional
comment optional
```

Concurrency rules:

```text
stale Product Context version → 409
stale value hash → 409
cross-workspace resource → forbidden/not found per project convention
```

A replacement creates a new Product Context version and updates synchronized relational projections.

---

## 6.8 Product import preview contract

Evolve the current preview so the frontend does not inspect arbitrary crawler dictionaries.

Return typed field candidates:

```python
class ProductFieldCandidateV1(BaseModel):
    field_path: str
    value: object
    display_value: str
    source_type: str
    source_reference: str | None
    confidence: float | None
    critical_for: list[str]
    proposed_status: str
```

The preview should include:

```text
product draft
candidate fields
warnings
unresolved critical fields
source summary
```

Do not return raw crawler payload as the only presentation contract.

Raw crawl data may remain internal/operator data if needed.

---

## 6.9 Progressive onboarding frontend

Create a dedicated resumable onboarding experience.

Recommended route:

```text
/onboarding
```

Stages:

### Stage 1 — Workspace

```text
What do you sell?
Primary market
Seller-facing language
Creator-message language
Default use
```

Use choice cards and small inputs.

### Stage 2 — First product

Options:

```text
Paste product link
Create manually
```

Primary recommendation:

```text
Start with one product
```

Do not show bulk import during first activation.

### Stage 3 — Review critical facts

Show compact cards:

```text
Product identity             Confirmed/imported
Market                       Needs confirmation
Buyer                        Suggested — review
Product mechanism            Suggested — review
Offer                        Unknown — not needed yet
Claims and disclosures       Needed before Creator Brief
Personalization              Not applicable / needs review
```

Actions:

```text
Confirm
Edit
Mark unknown
```

Do not display a 40-field form.

### Stage 4 — Choose first job

```text
Generate Creative Directions
Analyze a reference
Upload a UGC draft
```

For this goal, `Generate Creative Directions` is the primary completed path.

---

## 6.10 Product catalog UX

Update the Product Catalog and Product Drawer:

```text
Workflow readiness badges
verification source
critical warnings
next recommended action
```

When the backend is configured:

1. Do not merge backend products with demo seed products in the same canonical catalog.
2. Demo/seed content must appear only in explicit demo mode.
3. Backend products are canonical.
4. Campaign and direction counts must come from backend records for the M3/M4 flow.
5. Do not match backend entities by product name.

Use stable IDs.

---

## 6.11 M3 tests

Backend:

```text
URL preview creates imported candidates
manual product can contain unknown optional fields
seller confirmation persists
confirmation is tied to value hash and context version
stale confirmation returns 409
replacement creates new Product Context version
projection fields remain synchronized
conflicted critical field blocks readiness
unknown optional field does not block Creative Directions
POD personalization requires confirmation when applicable
readiness is deterministic
workspace isolation passes
deletion cascade passes
```

Frontend:

```text
onboarding can resume after refresh
backend-configured mode does not merge seed products
critical facts render as cards
confirm/edit/mark-unknown work
readiness copy is workflow-specific
first product can be added from URL
manual fallback works
first job navigation preserves product ID
```

---

# 7. M4 — Creative Directions flow

## 7.1 Product semantics

Seller-facing terminology:

```text
Creative Directions
Creative Plan
What We’re Testing
Why This Fits
Keep / Change / Avoid
Creator Brief
```

Internal terminology may remain:

```text
PatternKit
ViralKit
Campaign Pack
```

The UI must not ask the seller to:

```text
create a ViralKit
select a PatternKit version
manage PatternKit status
edit provenance
choose taxonomy versions
```

---

## 7.2 Seller-facing flow

```text
Select product
→ choose objective
→ choose or confirm buyer
→ optionally choose 1–3 references
→ add simple production constraints
→ Generate 3 Creative Directions
→ compare directions
→ select one
→ Generate Creator Brief
```

The system creates and persists the internal ViralKit.

---

## 7.3 Creative Directions request

Implement a seller-facing request contract equivalent to:

```python
class GenerateCreativeDirectionsRequestV1(BaseModel):
    product_id: UUID
    expected_product_context_version: int

    objective: Literal[
        "tiktok_shop_affiliate_test",
        "tiktok_shop_organic_test",
        "ugc_paid_asset",
        "spark_candidate",
        "pod_gift_campaign",
        "dropshipping_demo_test",
        "creative_refresh",
    ]

    target_market: str
    buyer_persona_id: str | None = None
    buyer_description: str | None = None

    reference_ids: list[UUID] = []
    excluded_direction_ids: list[str] = []

    creator_constraints: CreatorConstraintsV1
    production_constraints: ProductionConstraintsV1
    commercial_constraints: CommercialConstraintsV1

    change_request: str | None = None
```

Validation:

```text
expected Product Context version must match
product must satisfy creative_directions readiness
reference IDs must belong to workspace
reference analysis must be completed or explicitly queued
buyer must be supplied or deterministically resolved from confirmed Product Context
```

---

## 7.4 Internal orchestration

Implement a small seller-facing orchestration/facade module.

Suggested module name:

```text
creative_plans
```

Alternative:

```text
creative_directions
```

It must not duplicate PatternKit or ViralKit persistence.

Responsibilities:

```text
validate Product Context readiness
resolve buyer and objective
resolve selected references
load Creative DNA through public boundaries
resolve or create internal PatternKit inputs
retrieve eligible workspace PatternKits
rank applicability
compose ViralKit
assemble seller-facing Creative Plan response
record events
expose selection and Creator Brief handoff
```

Cross-module calls:

```text
products.public
references.public
creative_dna.public
pattern_kits.public
viral_kits.public
campaign_packs.public
jobs.public
product_events.public
```

No private imports.

---

## 7.5 References are optional

Support two composition modes.

### Reference-grounded mode

```text
selected references
→ completed Creative DNA
→ source PatternKit candidates/versions
→ ViralKit composition
```

### Product-first exploration mode

When no reference is selected:

```text
confirmed Product Context
+ objective
+ buyer
+ approved Golden/domain baseline
→ exploratory directions
```

Rules:

1. Do not invent a “winning PatternKit.”
2. Mark provenance as product-first exploration.
3. No performance-supported language.
4. No fake evidence IDs.
5. Directions remain hypotheses.
6. Seller-facing copy must say they are test directions, not proven winners.

Adjust contracts safely so product-first mode does not require a fabricated PatternKit ID.

Options:

```text
ViralKit V2 supports composition_mode and zero PatternKit links
```

or:

```text
an internal non-performance baseline source artifact with explicit source_type
```

Choose the simpler truthful design.

Do not create a fake validated PatternKit merely to satisfy a minimum-length validator.

---

## 7.6 Pattern retrieval

When references are not explicitly selected, retrieval may use:

```text
workspace-private reviewed PatternKits
product category
market
platform
objective
required product traits
contraindications
seller exclusions
```

Retrieval output must include:

```text
match score
applicability status
matched traits
conflicts
selection reason
source status
performance evidence status
```

Hard rejection:

```text
prohibited category conflict
required product trait absent
seller-confirmed constraint conflict
personalization incompatibility
unresolved critical governance conflict
```

A low sample size or no performance evidence is not a hard rejection; it lowers confidence and changes language.

---

## 7.7 Exactly three meaningful directions

The system must return exactly three concepts.

Each pair must differ on at least two meaningful axes:

```text
buyer persona
buyer pain
awareness stage
hook mechanism
creator persona
delivery style
narrative structure
demo mechanism
proof mechanism
offer framing
CTA strategy
```

At least one direction must vary hook mechanism.

At least one direction must vary demo, proof, or narrative mechanism.

Do not accept:

```text
same concept with three rewritten hooks
same buyer and proof with only creator label changed
generic “problem / solution / testimonial” cards with no product mechanism
```

---

## 7.8 Direction output

Create a seller-facing DTO such as:

```python
class CreativeDirectionCardV1(BaseModel):
    id: str
    name: str
    strategic_axis: str

    target_buyer: str
    buyer_pain: str
    desired_outcome: str

    creative_angle: str
    hook: CreativeDirectionHookV1
    opening_visual: str

    creator_persona: str
    delivery_style: str

    narrative_structure: str
    demo_mechanism: str
    proof_mechanism: str

    offer_framing: str | None
    cta_strategy: str

    why_this_fits: list[str]
    strengths_inherited: list[str]
    product_specific_changes: list[str]
    elements_to_avoid: list[str]

    must_show: list[str]
    claims_to_avoid: list[str]
    required_disclosures: list[str]

    what_this_tests: str
    expected_learning: str

    feasibility: Literal["high", "medium", "low"]
    risks: list[CreativeDirectionRiskV1]
    confidence: Literal["low", "medium", "high"]
```

Seller-facing DTO must not expose raw model IDs or evidence UUIDs as primary copy.

A debug/internal section may include:

```text
ViralKit version
PatternKit source versions
prompt/model/schema versions
evidence links
```

---

## 7.9 Creative Plan response

Implement:

```python
class CreativePlanV1(BaseModel):
    id: UUID
    version: int
    product_id: UUID
    product_context_version: int

    composition_mode: Literal[
        "reference_grounded",
        "workspace_pattern_grounded",
        "product_first_exploration",
    ]

    objective: str
    target_market: str
    buyer_summary: str

    directions: list[CreativeDirectionCardV1]
    what_is_held_constant: list[str]
    what_intentionally_changes: list[str]
    recommended_test_order: list[str]

    selected_direction_id: str | None
    readiness: str
    uncertainties: list[str]

    created_at: datetime
```

This is a seller-facing projection over the internal ViralKit.

Do not create a second canonical concept store.

---

## 7.10 API surface

Implement clear seller-facing endpoints.

Recommended:

```text
POST /workspaces/{workspace_id}/products/{product_id}/creative-plans
GET  /workspaces/{workspace_id}/creative-plans
GET  /workspaces/{workspace_id}/creative-plans/{creative_plan_id}
GET  /workspaces/{workspace_id}/creative-plans/{creative_plan_id}/versions

POST /workspaces/{workspace_id}/creative-plans/{creative_plan_id}/directions/{direction_id}/select
POST /workspaces/{workspace_id}/creative-plans/{creative_plan_id}/directions/{direction_id}/reject

POST /workspaces/{workspace_id}/creative-plans/{creative_plan_id}/regenerate
POST /workspaces/{workspace_id}/creative-plans/{creative_plan_id}/creator-briefs
```

Internally these may delegate to ViralKit endpoints/services.

Requirements:

```text
idempotency for generation
workspace scope
stable response contracts
typed errors
async job when model work is required
status polling
pagination for lists
version history
OpenAPI descriptions
```

Do not remove internal ViralKit APIs if they are needed for debug, compatibility, or existing tests.

---

## 7.11 Direction actions and versioning

Supported seller actions:

```text
viewed
selected
rejected
restored
regenerated
creator_brief_created
```

Rejection should optionally record:

```text
reason code
free-text explanation
```

Reason codes:

```text
wrong_buyer
wrong_creator_style
hard_to_produce
claim_risk
weak_product_fit
too_similar
not_on_brand
other
```

Rules:

1. Never overwrite an old Creative Plan/ViralKit version.
2. Regeneration creates a new version.
3. Preserve the prior plan, seller action, inputs, prompt/model version, and selected references.
4. One direction may be active at a time.
5. Historical selection events remain queryable.
6. Creator Brief must reference exact Creative Plan/ViralKit version and direction ID.

---

## 7.12 Creator Brief handoff

After selecting a direction:

```text
Generate Creator Brief
```

The system:

```text
loads exact selected direction
loads exact Product Context snapshot
loads governance and personalization
creates Campaign Pack
compiles exact requirements
links Campaign Pack to Creative Plan/ViralKit
returns seller-facing Creator Brief projection
```

Do not ask the seller to create a Campaign Pack manually from raw ViralKit data.

Do not expand Campaign Pack into ad-platform campaign management.

---

## 7.13 Creative Directions frontend

Create a dedicated seller-facing experience.

Recommended routes:

```text
/products/{productId}/creative-directions/new
/creative-directions/{creativePlanId}
```

Alternative TanStack Router layout is acceptable if URLs remain stable and resumable.

### Input screen

Show:

```text
Product summary and readiness
Objective
Buyer
Optional references
Creator preference
Maximum duration
Offer selection
Simple constraints
```

Hide internal PatternKit selection.

If product readiness is incomplete:

```text
show exact missing confirmations
let seller confirm inline
resume generation afterward
```

### Result screen

Page hierarchy:

1. Header:
   ```text
   3 Creative Directions for {Product}
   Objective
   Buyer
   Product Context version
   ```

2. Direction comparison cards.

3. For each direction:
   ```text
   Why this fits your product
   Hook and opening visual
   Creator and delivery style
   Demo and proof
   Offer and CTA
   What this tests
   Risks
   Feasibility
   ```

4. Comparison panel:
   ```text
   What stays constant
   What changes
   Recommended test order
   ```

5. Action tray:
   ```text
   Select direction
   Reject
   Generate three new directions
   Change buyer/objective
   Generate Creator Brief
   ```

6. Optional debug drawer.

### UX language

Use:

```text
Creative Directions
Why This Fits
What We’re Testing
Keep
Change
Avoid
Generate Creator Brief
```

Do not use as primary labels:

```text
ViralKit
PatternKit
Pattern match
adaptation schema
model run
```

---

## 7.14 Backend-canonical state

For M4:

```text
Creative Plan
direction selection
direction rejection
version history
Creator Brief links
```

must be backend-canonical.

Remove any M3/M4 behavior that depends on:

```text
matching by product name
Zustand-only campaign creation
seed campaign mirrors
component-only selected concept
query-string-only completion state
```

Query strings may hold:

```text
productId
creativePlanId
directionId
```

but must resolve state from APIs.

---

## 7.15 Events

Record transactionally with the action:

```text
workspace_defaults_confirmed
product_import_previewed
product_created
product_field_confirmed
product_field_replaced
product_readiness_changed
creative_plan_requested
creative_plan_generated
creative_direction_viewed
creative_direction_selected
creative_direction_rejected
creative_plan_regenerated
creator_brief_created
creator_brief_exported
```

Do not emit duplicate events on query/refetch.

---

## 7.16 M4 tests

Backend:

```text
reference-grounded composition
product-first exploration
workspace PatternKit retrieval
incompatible PatternKit rejection
exactly three directions
meaningful diversity
buyer/creator separation
product fact preservation
offer preservation
claim/disclosure propagation
no fabricated performance language
selection persistence
rejection persistence
regeneration versioning
Creator Brief exact-version handoff
idempotent generation
workspace isolation
stale Product Context conflict
```

Frontend:

```text
internal PatternKit/ViralKit terms are hidden from primary UX
product readiness blocks only when appropriate
reference selection is optional
three directions render
comparison axes render
selection persists after refresh
rejection reason persists
regeneration creates new version
Creator Brief handoff uses backend ID
configured backend mode does not use seed mirrors
stable URL resumes result
loading/error/empty states are usable
keyboard and focus behavior pass
```

---

# 8. Full acceptance flow

Automate fixture and mock-provider E2E for this flow:

```text
1. Authenticate using local-test mode in test environment.
2. Create a workspace.
3. Save minimal Workspace Defaults.
4. Paste a product URL and receive typed preview candidates.
5. Create the product.
6. Confirm identity, market, buyer, and product mechanism.
7. Query workflow readiness.
8. Verify Creative Directions becomes ready.
9. Generate Creative Directions without a reference.
10. Receive exactly three product-specific directions.
11. Verify product-first exploration language contains no winning claim.
12. Select one direction.
13. Generate a Creator Brief.
14. Verify exact product snapshot and selected direction lineage.
15. Refresh/re-fetch every resource from backend IDs.
16. Regenerate directions with a changed buyer constraint.
17. Verify a new version and preserved history.
18. Repeat with one analyzed reference.
19. Verify reference-grounded provenance.
20. Delete the test workspace and verify cascade/storage cleanup.
```

A second E2E case must cover POD personalization:

```text
approved personalization value
seller confirmation
three product-specific directions
personalization preserved in every relevant direction
Creator Brief compiles exact personalization requirement
```

A third E2E case must cover dropshipping:

```text
compatibility unknown
Creative Directions allowed with explicit uncertainty
Creator Brief blocked from unsupported universal claim
seller confirmation resolves the question
```

No real OpenAI call is required by this goal’s automated acceptance.

Use fixture and local mock provider.

---

# 9. Error contracts

Add stable errors where required:

```text
GOLDEN_BASELINE_NOT_FOUND
PRODUCT_CONTEXT_VERSION_CONFLICT
PRODUCT_FIELD_VALUE_CONFLICT
PRODUCT_FIELD_CONFIRMATION_INVALID
PRODUCT_WORKFLOW_NOT_READY
CREATIVE_PLAN_NOT_FOUND
CREATIVE_PLAN_VERSION_CONFLICT
CREATIVE_DIRECTION_NOT_FOUND
CREATIVE_DIRECTION_ALREADY_SELECTED
CREATIVE_DIRECTION_REJECTED
CREATIVE_PLAN_INPUT_INVALID
CREATIVE_PLAN_PATTERN_INCOMPATIBLE
CREATIVE_PLAN_OUTPUT_INVALID
CREATOR_BRIEF_DIRECTION_REQUIRED
```

Follow the project-standard API error envelope.

Do not leak internal provider responses.

---

# 10. Migrations

Expected new persistence may include:

```text
workspace onboarding/default fields or table
product context field verifications
creative-plan seller action projection if not already represented by ViralKit actions
additional ViralKit composition-mode/source fields
```

Prefer reusing current ViralKit version/action tables.

Do not add a second full `creative_plans` table if a stable projection can be built from ViralKit.

A small facade/projection table is allowed only when needed for stable seller-facing IDs or query efficiency and must document why duplication is avoided.

Migration requirements:

```text
clean zero-to-head passes
upgrade current development schema passes
existing PatternKit/ViralKit rows remain readable
safe defaults are explicit
downgrade included when reasonably safe
migration integration tests pass
```

---

# 11. Security and privacy

Preserve:

```text
workspace isolation
OIDC/local-test environment boundary
secret redaction
signed URL redaction
SSRF protections in product crawler
private object storage
model-run audit
deletion cascade
```

This goal does not complete the separate per-asset media-consent milestone.

Do not falsely mark that audit gap resolved.

Product URLs and crawl sources must be recorded safely.

Do not store authentication cookies, private page content, or crawler secrets.

---

# 12. Cost and latency controls

M1 must preserve or improve:

```text
bounded prompt context
bounded examples
operation-specific output limits
exact request identity
idempotent paid requests
workspace concurrency limiter
one repair maximum
no whole-Golden runtime injection
```

Creative Directions generation should make one primary composition call.

Do not call the model separately for each of three concepts.

Do not automatically analyze every product in a catalog.

Do not regenerate PatternKit when an exact eligible version already exists.

Record:

```text
operation
model
prompt version
schema version
context hash
input/output usage
latency
repair count
safe failure
```

---

# 13. Test and verification commands

Run and report exact results.

Backend:

```bash
cd apps/backend
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv run pip-audit
```

Focused suites must cover:

```text
prompt registry/compiler
model/domain contract split
PatternKit assembler
ViralKit assembler
product verification
workflow readiness
onboarding
Creative Directions orchestration
Creator Brief handoff
workspace isolation
migrations
OpenAPI
fixture E2E
mock-provider E2E
```

Frontend:

```bash
cd apps/web
pnpm test
pnpm lint
pnpm build
pnpm audit --prod
```

Repository:

```bash
git diff --check
```

Do not claim GitHub CI passed unless a workflow actually ran.

Do not run real OpenAI qualification as part of this goal unless the user explicitly requests it after mock acceptance passes.

---

# 14. Non-goals

Do not build:

```text
TikTok Scorer V2
UGC Preflight V2
Domain expert management UI
full DomainExpertPolicyPack implementation
creator marketplace
creator CRM
payments
billing
performance CSV intelligence
GMV prediction
viral probability
rights/Spark full workflow
full video editor
Seedance production editor
catalog-wide AI generation
Shopify/TikTok integrations
agency multi-workspace expansion
global ad crawler
```

Create extension points only where required.

---

# 15. Definition of Done

## M1

```text
[ ] Golden Output V1.0 is authoritative in repository docs/tests.
[ ] Existing prompt infrastructure was audited and reused.
[ ] PatternKit model output is separate from persisted PatternKit.
[ ] ViralKit model output is separate from persisted ViralKit.
[ ] Server assemblers own identity, tenancy, version, status, provenance, and snapshots.
[ ] Prompt package has bounded context manifest and example policy.
[ ] Domain overlay selector is extension-ready.
[ ] OpenAI native and compatible providers use the same semantic contracts.
[ ] One bounded repair attempt is enforced.
[ ] No full Golden document enters runtime requests.
[ ] Prompt/model/schema/context provenance is persisted.
```

## M3

```text
[ ] Workspace onboarding state is backend-canonical and resumable.
[ ] Minimal workspace defaults are saved.
[ ] Product URL preview returns typed candidates.
[ ] Manual product creation works.
[ ] ProductContextV1 remains the business contract.
[ ] Field verification metadata is persisted separately.
[ ] Seller confirmation is tied to value hash and Product Context version.
[ ] Workflow-specific readiness is deterministic.
[ ] Just-in-time questions are available.
[ ] UI shows readiness by workflow, not one generic percentage.
[ ] Backend-configured Product Catalog does not merge demo seeds.
[ ] Critical fact confirmation works after refresh.
```

## M4

```text
[ ] Seller can request Creative Directions from a product.
[ ] References are optional.
[ ] Product-first exploration is truthful and supported.
[ ] Reference-grounded mode is supported.
[ ] PatternKit remains internal.
[ ] ViralKit remains the canonical internal orchestration artifact.
[ ] Seller receives exactly three meaningful directions.
[ ] Product facts, personalization, claims, disclosures, and constraints are preserved.
[ ] Seller can select/reject/regenerate directions.
[ ] Actions and versions persist.
[ ] Selection survives refresh.
[ ] Seller can generate a Creator Brief from the exact selected direction.
[ ] Creator Brief links exact Product Context and Creative Plan/ViralKit versions.
[ ] Primary UX does not expose internal technical names.
[ ] Fixture and mock E2E pass.
```

## Quality

```text
[ ] Backend tests pass.
[ ] Backend coverage does not regress and targets at least 80%.
[ ] Full mypy passes.
[ ] Ruff lint/format pass.
[ ] Clean migration passes.
[ ] Frontend tests/lint/build pass.
[ ] Workspace isolation passes.
[ ] No secret or signed-URL leakage.
[ ] No claim of live OpenAI qualification.
```

---

# 16. Final audit deliverable

Create:

```text
VIRALDY_M1_M3_M4_IMPLEMENTATION_AUDIT.md
```

It must contain:

1. Branch and final commit SHA.
2. Baseline main SHA.
3. PR URL, if created.
4. Changed files grouped by M1/M3/M4.
5. Migrations.
6. New and changed contracts.
7. API endpoint list.
8. Prompt package and context-manifest design.
9. Model-output/domain-artifact split.
10. Product verification and readiness matrix.
11. Seller-facing terminology map.
12. Creative Directions orchestration diagram.
13. Fixture and mock E2E evidence.
14. Test commands and exact results.
15. Known limitations.
16. Deferred domain-expert policy work.
17. Confirmation that live OpenAI qualification was not claimed.
18. Confirmation that PatternKit/ViralKit remain internal artifacts.
19. Screenshot or browser evidence for:
    - first product onboarding;
    - critical-fact confirmation;
    - three Creative Directions;
    - selected direction;
    - Creator Brief handoff;
    - refresh/resume.
20. Remaining seller-validation questions.

Do not mark an item complete without code and automated evidence.

---

# 17. Final permissible completion statement

Use this statement only when all Definition of Done items are proven:

> Viraldy now has a production-structured prompt and semantic-output boundary, progressive Product Context onboarding, and a backend-canonical Creative Directions flow. PatternKit and ViralKit remain internal intelligence artifacts; sellers can add one product, confirm only decision-critical facts, generate three product-specific directions, select one, and create a versioned Creator Brief. The system remains mock-verified rather than live-model- or seller-validated.
