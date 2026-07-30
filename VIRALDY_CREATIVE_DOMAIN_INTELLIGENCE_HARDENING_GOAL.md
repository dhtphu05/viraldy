# VIRALDY CREATIVE DOMAIN CONTRACT & INTELLIGENCE HARDENING GOAL
## Codex Goal-Mode Execution Contract

> **Repository:** `dhtphu05/viraldy`
> **Target branch:** `hardening/keyless-product-hardening`
> **Baseline state:** keyless infrastructure hardening completed; fixture and mock-provider workflows pass
> **Primary objective:** replace MVP-grade generic JSON and hardcoded creative logic with strongly typed, evidence-grounded, versioned creative-domain contracts and real brief-aware decision logic
> **Execution style:** preserve the current working product, harden one semantic layer at a time, update this file continuously, and continue until the Definition of Done is satisfied
> **Do not deploy. Do not add later roadmap features. Do not rewrite the platform foundation.**

---

# 0. EXECUTION DIRECTIVE

Read the current source before modifying it.

The existing system already provides:

```text
Asset/version persistence
PostgreSQL
Redis/Celery jobs
MinIO/S3-compatible storage
Media artifacts
Evidence items
Creative DNA versions
TikTok score runs
Adaptation runs
Campaign Pack versions
UGC Preflight runs
Recommendations
AI model-run audit
Fixture mode
Mock-provider HTTP mode
Live provider readiness
```

The current problem is not missing infrastructure.

The current problem is that the creative-domain layer is still MVP-grade:

```text
generic dict[str, object] payloads
hardcoded Creative DNA values
hardcoded evidence timestamps/text
fixed dimension scores
thin product context
untyped Campaign Pack brief_json
brief alignment that does not actually verify each brief requirement
category-specific kitchen defaults
```

This goal must fix those problems without breaking the working job/provider/storage architecture.

Do not stop after adding Pydantic models.

Do not mark a milestone complete while the old hardcoded path is still active.

Do not add compatibility wrappers that silently continue using the old untyped path.

The final product must analyze arbitrary supported TikTok/UGC product creatives, not only the seeded kitchen-organizer fixture.

---

# 1. SOURCE FINDINGS TO TREAT AS DEFECTS

Confirm each finding against the branch and record the actual file/line in the Execution Log.

## 1.1 Creative DNA is not actually derived from the complete evidence bundle

Current behavior includes fixed values such as:

```text
problem_first
"My counter was always a mess."
messy kitchen counter
screen_time_ratio = 0.42
before_after
small_space_organization
home_organizer
CTA at 18.2 seconds
```

These values must not appear for arbitrary uploaded media unless they are supported by actual evidence.

## 1.2 Evidence normalization contains fixture assumptions

Current evidence creation may construct fixed:

```text
hook signal at 0–2.1s
demo signal at 6.5–15s
proof signal at 15–18.2s
CTA signal at 18.2–27s
```

Evidence must come from provider/derived observations with real timestamps.

No CTA evidence may be persisted when no CTA was detected.

No demo evidence may be persisted when no demo was detected.

## 1.3 Visual observation schema is too shallow

The current observation schema is insufficient for production-quality:

```text
hook analysis
product visibility
demo sequence
proof quality
creator delivery
editing/pacing
offer/CTA
claim risk
TikTok-native fit
brief alignment
```

It must be expanded and versioned.

## 1.4 TikTok scoring uses fixed scores

The existing scorer assigns fixed values when an evidence type exists.

Replace fixed values with deterministic signal-based calculators.

## 1.5 Preflight is not truly brief-aware

The current implementation largely reuses structural dimensions and derives a must-show score from the number of brief items.

Replace this with requirement compilation and evidence-backed requirement evaluation.

## 1.6 Campaign Pack accepts arbitrary JSON

The current `brief_json` request/response is a generic dictionary.

Replace it with a versioned `CampaignPackBriefV1` contract at every service/API boundary.

JSONB may remain the persistence format.

## 1.7 Product context is too thin

The current product contract does not provide enough:

```text
buyer context
benefits
features
offer
proof
claim governance
creative constraints
visual differentiators
```

Add a typed product context and persist snapshots in generated runs.

## 1.8 Adaptation provenance is stronger than its semantics

Adaptation has a better output schema than other modules, but still receives insufficient product context and persists generic JSON.

Harden its input/output contracts and diversity rules.

---

# 2. FINAL ARCHITECTURE

Use this architecture:

```text
Relational envelope
+ strongly typed JSON documents
+ normalized evidence facts
+ deterministic scoring/rules
+ model-assisted semantic classification/generation
+ immutable versions/provenance
```

Do not create hundreds of SQL columns for every creative property.

Do not leave arbitrary unvalidated JSON at API/service boundaries.

## 2.1 Relational envelope

Keep the current aggregate/run tables:

```text
products
assets
asset_versions
media_artifacts
evidence_items
creative_dna_versions
tiktok_score_runs
adaptation_runs
campaign_packs
campaign_pack_versions
preflight_runs
recommendations
ai_model_runs
processing_jobs
processing_job_events
```

## 2.2 Strongly typed JSON

Persist JSONB, but validate it through versioned Pydantic contracts before:

```text
provider response acceptance
database persistence
service return
API request acceptance
API response generation
scoring
preflight alignment
```

## 2.3 Normalized evidence facts

Every evidence item must have:

```text
schema_version
evidence_type
source
timestamps
confidence
typed value payload
provider/model provenance
pipeline version
identity hash
```

## 2.4 Deterministic decision layer

Models may:

```text
extract
classify
summarize
generate copy
explain
```

Models may not decide:

```text
final structural score
hard blocker override
final preflight action
rights readiness
performance/GMV prediction
```

---

# 3. SCOPE

## 3.1 In scope

```text
ProductContextV1
MediaObservationBundleV1
typed evidence payloads
CreativeDnaV1
TikTokScoreResultV2
AdaptationInputV2
AdaptationOutputV2
CampaignPackBriefV1
compiled brief requirements
PreflightAlignmentResultV2
RecommendationPayloadV2
schema versioning
product snapshots
provider contract expansion
hardcode removal
evidence-driven scorer
real brief-alignment engine
fixture/mock updates
golden semantic regression cases
frontend rendering of typed results
migration and backward compatibility
```

## 3.2 Out of scope

```text
deployment
billing
performance CSV
GMV prediction
benchmarks
PatternKit
ViralKit
creator marketplace
sample ROI
rights workflow implementation
Spark authorization workflow
campaign performance analytics
TikTok crawler
fine-tuning
custom foundation models
vector database
microservices
large dashboard redesign
```

Rights fields may remain informational in Campaign Pack, but must not claim actual authorization.

---

# 4. VERSIONING RULES

Create explicit constants:

```text
PRODUCT_CONTEXT_SCHEMA_VERSION = "product_context_v1"
MEDIA_OBSERVATION_SCHEMA_VERSION = "media_observation_v1"
EVIDENCE_SCHEMA_VERSION = "evidence_v1"
CREATIVE_DNA_SCHEMA_VERSION = "creative_dna_v1"
TIKTOK_SCORE_SCHEMA_VERSION = "tiktok_score_v2"
TIKTOK_RUBRIC_VERSION = "tiktok_structure_rubric_v2"
TIKTOK_RULE_VERSION = "tiktok_structure_rules_v2"
ADAPTATION_SCHEMA_VERSION = "adaptation_v2"
CAMPAIGN_PACK_SCHEMA_VERSION = "campaign_pack_brief_v1"
PREFLIGHT_SCHEMA_VERSION = "ugc_preflight_v2"
PREFLIGHT_RUBRIC_VERSION = "ugc_preflight_rubric_v2"
PREFLIGHT_RULE_VERSION = "ugc_preflight_rules_v2"
RECOMMENDATION_SCHEMA_VERSION = "recommendation_v2"
```

Rules:

- Never overwrite old analytical versions.
- New schema behavior creates a new run/version.
- Existing historical v1 rows remain readable.
- New writes must use the new schema.
- Do not silently interpret malformed old data as valid v2 data.
- Add explicit legacy adapters only for reading historical rows.
- Do not use a legacy adapter for new writes.

---

# 5. PRODUCT CONTEXT CONTRACT

Create a new domain contract module, preferably:

```text
apps/backend/src/viraldy/modules/products/context.py
```

or:

```text
apps/backend/src/viraldy/modules/products/contracts.py
```

## 5.1 `ProductContextV1`

Implement a typed structure equivalent to:

```python
class ProductIdentityV1(BaseModel):
    name: str
    brand: str | None
    category: str
    subcategory: str | None
    variant: str | None
    market: str
    currency: str | None

class BuyerPersonaV1(BaseModel):
    id: str
    label: str
    description: str | None
    pain_points: list[str]
    desired_outcomes: list[str]
    objections: list[str]
    awareness_stage: Literal[
        "unaware",
        "problem_aware",
        "solution_aware",
        "product_aware",
        "most_aware",
        "unknown",
    ]

class ProductBenefitV1(BaseModel):
    id: str
    label: str
    description: str
    proof_available: list[str]
    claim_strength: Literal["observed", "supported", "subjective", "unknown"]

class ProductFeatureV1(BaseModel):
    id: str
    label: str
    description: str | None
    visual_demo_possible: bool
    visual_cues: list[str]

class CommercialContextV1(BaseModel):
    price: Decimal | None
    compare_at_price: Decimal | None
    discount_text: str | None
    bundle_text: str | None
    shipping_text: str | None
    commission_percent: Decimal | None
    margin_band: Literal["low", "medium", "high", "unknown"]
    offer_notes: list[str]

class CreativeContextV1(BaseModel):
    primary_angles: list[str]
    demonstration_mechanisms: list[str]
    visual_differentiators: list[str]
    available_proof: list[str]
    creator_personas: list[str]
    preferred_delivery_styles: list[str]
    brand_voice: list[str]
    prohibited_visuals: list[str]

class ClaimRuleV1(BaseModel):
    id: str
    text: str
    rule_type: Literal[
        "allowed",
        "allowed_with_qualification",
        "prohibited",
        "required_disclosure",
    ]
    qualification: str | None
    severity: Literal["low", "medium", "high", "critical"]

class ProductGovernanceV1(BaseModel):
    claims: list[ClaimRuleV1]
    required_disclosures: list[str]
    prohibited_content: list[str]
    rights_notes: list[str]

class ProductContextV1(BaseModel):
    schema_version: Literal["product_context_v1"]
    identity: ProductIdentityV1
    personas: list[BuyerPersonaV1]
    benefits: list[ProductBenefitV1]
    features: list[ProductFeatureV1]
    commercial: CommercialContextV1
    creative: CreativeContextV1
    governance: ProductGovernanceV1
```

The exact field names may adapt to source conventions, but semantic coverage must remain.

## 5.2 Persistence

Preferred MVP-compatible approach:

```text
products.product_context_json JSONB
products.context_schema_version varchar
```

Keep existing columns for indexing/display:

```text
name
description
market
status
```

Use those as projections from the context where practical.

Do not put the full context only into the old generic `metadata_json`.

## 5.3 Backfill

For existing products:

- Create a minimal valid `ProductContextV1`.
- Use `unknown` or empty lists when the old row has no information.
- Do not fabricate benefits, claims, personas, price, or proof.

## 5.4 API

Update create/update product requests to accept typed context.

Backward-compatible option:

```text
accept old minimal request
→ build a minimal ProductContextV1
```

New responses must expose:

```text
product_context
context_schema_version
```

## 5.5 Snapshot rule

Persist immutable `product_snapshot_json` and `product_context_schema_version` in:

```text
adaptation_runs
campaign_pack_versions
preflight_runs
```

A later product edit must not alter historical meaning.

---

# 6. MEDIA OBSERVATION CONTRACT

Replace the shallow observation response with a comprehensive versioned bundle.

Recommended module:

```text
apps/backend/src/viraldy/modules/media_analysis/contracts.py
```

## 6.1 Shared primitives

```python
class TimeRangeV1(BaseModel):
    start_ms: int
    end_ms: int

class ObservationRefV1(BaseModel):
    observation_id: str
    confidence: float
    frame_storage_keys: list[str]
```

## 6.2 Opening observations

```python
class HookObservationV1(BaseModel):
    observation_id: str
    time_range: TimeRangeV1
    hook_type: Literal[
        "problem_first",
        "result_first",
        "curiosity",
        "question",
        "contrarian",
        "testimonial",
        "offer_first",
        "product_first",
        "pattern_interrupt",
        "story_open",
        "unknown",
    ]
    spoken_text: str | None
    overlay_text: str | None
    visual_description: str
    buyer_pain: str | None
    clarity: Literal["clear", "partial", "unclear", "unknown"]
    face_present: bool | None
    product_present: bool | None
    confidence: float
    frame_storage_keys: list[str]
```

## 6.3 Product observations

```python
class ProductAppearanceV1(BaseModel):
    observation_id: str
    time_range: TimeRangeV1
    visibility: Literal["clear", "partial", "obstructed", "uncertain"]
    shot_type: Literal[
        "hero",
        "close_up",
        "medium",
        "wide",
        "in_use",
        "packaging",
        "result_only",
        "unknown",
    ]
    usage_visible: bool
    product_match_confidence: float | None
    confidence: float
    frame_storage_keys: list[str]

class ProductVisibilitySummaryV1(BaseModel):
    first_appearance_ms: int | None
    total_visible_ms: int | None
    screen_time_ratio: float | None
    clear_close_up_present: bool
    usage_present: bool
```

## 6.4 Demo observations

```python
class DemoStepV1(BaseModel):
    observation_id: str
    step_index: int
    time_range: TimeRangeV1
    action: str
    product_visible: bool
    mechanism_visible: bool
    result_visible: bool
    confidence: float
    frame_storage_keys: list[str]

class DemoObservationV1(BaseModel):
    detected: bool
    demo_type: Literal[
        "before_after",
        "tutorial",
        "installation",
        "usage",
        "comparison",
        "unboxing",
        "result_reveal",
        "none",
        "unknown",
    ]
    steps: list[DemoStepV1]
    before_state_visible: bool
    after_state_visible: bool
    mechanism_clarity: Literal["clear", "partial", "unclear", "unknown"]
    continuity: Literal["continuous", "edited_but_clear", "fragmented", "unknown"]
    confidence: float
```

## 6.5 Proof observations

```python
class ProofMomentV1(BaseModel):
    observation_id: str
    time_range: TimeRangeV1
    proof_type: Literal[
        "visual_result",
        "before_after",
        "demonstration",
        "testimonial",
        "rating",
        "review",
        "comment_social_proof",
        "measurement",
        "comparison",
        "authority",
        "none",
        "unknown",
    ]
    description: str
    verifiability: Literal["observable", "partially_observable", "not_observable", "unknown"]
    confidence: float
    frame_storage_keys: list[str]
```

## 6.6 CTA and offer observations

```python
class CtaObservationV1(BaseModel):
    observation_id: str
    time_range: TimeRangeV1
    modality: Literal["spoken", "overlay", "visual", "mixed"]
    cta_type: Literal[
        "product_tag",
        "shop_now",
        "link_in_shop",
        "learn_more",
        "comment",
        "follow",
        "generic",
        "unknown",
    ]
    text: str | None
    product_tag_visible: bool
    confidence: float
    frame_storage_keys: list[str]

class OfferObservationV1(BaseModel):
    observation_id: str
    time_range: TimeRangeV1
    offer_type: Literal[
        "price",
        "discount",
        "bundle",
        "free_shipping",
        "limited_time",
        "value_statement",
        "none",
        "unknown",
    ]
    text: str | None
    price_text: str | None
    confidence: float
    frame_storage_keys: list[str]
```

## 6.7 Creator observations

```python
class CreatorObservationV1(BaseModel):
    face_present: bool | None
    speaking_present: bool | None
    delivery_style: Literal[
        "authentic_review",
        "testimonial",
        "tutorial",
        "demonstration",
        "storytelling",
        "sales_pitch",
        "voiceover",
        "faceless_demo",
        "unknown",
    ]
    creator_persona: str | None
    emotion: Literal[
        "neutral",
        "excited",
        "surprised",
        "frustrated",
        "relieved",
        "confident",
        "unknown",
    ]
    pacing: Literal["slow", "moderate", "fast", "mixed", "unknown"]
    sales_language_intensity: Literal["low", "medium", "high", "unknown"]
    authenticity_cues: list[str]
    confidence: float
```

## 6.8 Editing observations

```python
class EditingObservationV1(BaseModel):
    cut_count: int | None
    average_shot_duration_ms: int | None
    first_three_second_cut_count: int | None
    pattern_interrupts: list[TimeRangeV1]
    dead_air_ranges: list[TimeRangeV1]
    caption_density: Literal["none", "low", "medium", "high", "unknown"]
    visual_pacing: Literal["slow", "moderate", "fast", "mixed", "unknown"]
    transition_types: list[str]
    confidence: float
```

## 6.9 Claim observations

```python
class ClaimCandidateV1(BaseModel):
    observation_id: str
    time_range: TimeRangeV1 | None
    text: str
    source: Literal["spoken", "overlay", "caption", "visual_inference"]
    category: Literal[
        "performance",
        "health",
        "safety",
        "financial",
        "shipping",
        "scarcity",
        "superlative",
        "guarantee",
        "comparison",
        "other",
        "unknown",
    ]
    risk: Literal["none", "low", "medium", "high", "critical", "unknown"]
    qualification_present: bool
    confidence: float
    frame_storage_keys: list[str]
```

## 6.10 Platform observations

```python
class PlatformObservationV1(BaseModel):
    aspect_ratio: str | None
    vertical: bool | None
    native_signals: list[str]
    shop_signals: list[str]
    caption_style: list[str]
    visual_safe_zone_risk: bool | None
    confidence: float
```

## 6.11 Bundle

```python
class MediaObservationBundleV1(BaseModel):
    schema_version: Literal["media_observation_v1"]
    duration_ms: int
    hooks: list[HookObservationV1]
    product_appearances: list[ProductAppearanceV1]
    product_visibility: ProductVisibilitySummaryV1
    demo: DemoObservationV1
    proof_moments: list[ProofMomentV1]
    ctas: list[CtaObservationV1]
    offers: list[OfferObservationV1]
    creator: CreatorObservationV1
    editing: EditingObservationV1
    claims: list[ClaimCandidateV1]
    platform: PlatformObservationV1
    uncertainties: list[str]
```

## 6.12 Validation invariants

Validate:

- All timestamps are non-negative.
- All end times are greater than or equal to start times.
- All times are within media duration.
- Confidence is in 0..1.
- Product first appearance is consistent with appearances.
- `demo.detected = false` means no demo steps.
- `cta` evidence exists only when CTA observations exist.
- `offer` evidence exists only when offer observations exist.
- Observation IDs are unique within the bundle.
- Unknown is accepted.
- Unsupported extra fields are rejected for live/mock responses.

---

# 7. TYPED EVIDENCE CONTRACTS

Keep the `evidence_items` table, but stop treating `value_json` as an arbitrary dictionary.

Recommended:

```text
apps/backend/src/viraldy/modules/media_analysis/evidence_contracts.py
```

## 7.1 Base envelope

```python
class EvidenceValueBaseV1(BaseModel):
    schema_version: Literal["evidence_v1"]
    observation_id: str | None
```

## 7.2 Typed union

Implement discriminated models for:

```text
transcript_segment
on_screen_text
hook_signal
product_appearance
product_visibility_summary
demo_step
demo_summary
proof_signal
cta_signal
offer_signal
creator_signal
editing_signal
claim_signal
platform_signal
```

Replace or deprecate the old ambiguous evidence types for new writes.

Compatibility may map old evidence for historical reads.

## 7.3 No fabricated rows

Rules:

- No hook evidence without a hook observation.
- No CTA evidence without CTA observation.
- No proof evidence without proof moment.
- No claim evidence without exact claim candidate.
- No fixed timestamps.
- No category-specific hardcoded text.
- No default confidence unless a documented derivation supplies one.
- Every evidence identity hash must include the typed payload schema version.

## 7.4 Deterministic evidence

Editing facts such as:

```text
cut count
average shot duration
aspect ratio
audio presence
duration
```

should come from deterministic processing where possible.

Do not ask the LLM for values that FFmpeg/scene detection can compute.

---

# 8. CREATIVE DNA CONTRACT

Create:

```text
apps/backend/src/viraldy/modules/creative_dna/contracts.py
```

## 8.1 Principles

Creative DNA answers:

```text
What is observed in this creative?
What reusable mechanism is present?
What is uncertain?
What evidence supports every conclusion?
```

Creative DNA does not answer:

```text
What final score should this receive?
Will this go viral?
Will this produce GMV?
Should the seller approve spend?
```

## 8.2 Field-level observation contract

Use a reusable wrapper equivalent to:

```python
class ObservedValueV1(BaseModel):
    value: object
    confidence: float
    evidence_ids: list[UUID]
    status: Literal["observed", "inferred", "unknown", "not_present"]
```

Concrete typed wrappers are preferred over `object` where practical.

## 8.3 `CreativeDnaV1`

Implement semantic coverage equivalent to:

```python
class CreativeDnaV1(BaseModel):
    schema_version: Literal["creative_dna_v1"]
    opening: OpeningDnaV1
    product: ProductDnaV1
    narrative: NarrativeDnaV1
    demo: DemoDnaV1
    proof: ProofDnaV1
    creator: CreatorDnaV1
    editing: EditingDnaV1
    offer: OfferDnaV1
    cta: CtaDnaV1
    platform: PlatformDnaV1
    claims: list[ClaimDnaV1]
    risks: list[RiskDnaV1]
    reusable_mechanisms: list[ReusableMechanismV1]
    uncertainties: list[str]
    completeness: dict[str, bool]
    overall_confidence: Literal["low", "medium", "high"]
```

Required semantic fields:

```text
opening
  primary_hook_type
  hook_text
  opening_visual
  buyer_pain
  face_present
  product_present
  first_three_second_structure
  pattern_interrupts

product
  first_appearance_ms
  total_visible_ms
  screen_time_ratio
  close_up_present
  hero_shot_present
  usage_present
  product_match
  appearance_sequence

narrative
  structure
  angle
  buyer_pain
  desired_outcome
  emotional_drivers
  awareness_stage

demo
  detected
  demo_type
  mechanism_clarity
  before_state_visible
  after_state_visible
  result_clarity
  steps

proof
  proof_types
  strongest_proof
  verifiability
  proof_strength_label

creator
  face_present
  delivery_style
  creator_persona
  emotion
  pacing
  authenticity_cues
  sales_language_intensity

editing
  cut_count
  average_shot_duration_ms
  first_three_second_cut_count
  pacing
  caption_density
  dead_air_present
  transition_types

offer
  present
  offer_types
  price_text
  discount_text
  urgency_present

cta
  present
  cta_types
  first_appearance_ms
  spoken_text
  overlay_text
  product_tag_visible

platform
  vertical
  native_signals
  shop_signals
  safe_zone_risk
  format
```

## 8.4 Remove adaptation-specific summary

Do not store product-specific:

```text
what_to_change for the user's SKU
```

inside reference Creative DNA.

Allowed reference-level interpretation:

```text
reusable mechanisms
copy risks
uncertainties
generic test hypotheses
```

Product-specific keep/change/avoid belongs in Adaptation.

## 8.5 Builder behavior

Replace the current hardcoded builder.

Recommended flow:

```text
typed evidence bundle
→ deterministic observation projection
→ optional LLM taxonomy interpretation
→ evidence-reference validation
→ CreativeDnaV1
→ confidence/completeness calculation
→ persist
```

The model may classify:

```text
hook type
narrative structure
angle
creator style
emotional drivers
```

The model must reference existing evidence IDs.

A post-validator must reject:

- Unknown evidence IDs.
- Evidence IDs from another asset version.
- Timestamps outside duration.
- Claims with no transcript/OCR/visual source.
- Product visibility unsupported by product evidence.
- CTA present without CTA evidence.
- Demo present without demo evidence.

## 8.6 Confidence

Calculate overall confidence from:

```text
required evidence completeness
source confidence
model response validation
cross-source agreement
number of unknown critical fields
```

Do not accept a model-provided global confidence without deterministic recalculation.

---

# 9. PROVIDER PROMPTS AND SCHEMAS

## 9.1 Capability split

Media provider:

```text
transcribe_audio
extract_ocr
extract_visual_observations_v1
classify_creative_taxonomy_v1
```

Generation provider:

```text
generate_adaptation_v2
generate_campaign_pack_v1
write_revision_message_v2
```

## 9.2 JSON Schema

Use provider JSON schema mode when supported.

Fallback must still validate Pydantic contracts.

Do not use generic `json_object` without a schema when provider capability supports schemas.

## 9.3 Prompt rules

All extraction prompts must say:

```text
Use only supplied frames, transcript, OCR, metadata, and product context.
Return unknown when evidence is insufficient.
Do not infer hidden events.
Do not create timestamps that are not supported.
Do not return a score.
Do not predict virality, orders, sales, or GMV.
Return exact observation IDs and frame references.
Follow the response schema exactly.
```

## 9.4 Mock provider

Update the local OpenAI-compatible mock provider to return all new contracts.

It must support at least these scenarios:

```text
strong home product video
beauty demonstration
POD personalized gift
pet accessory demonstration
late product reveal
missing CTA
no offer
no speech
high-risk claim
product absent
brief mismatch
malformed response
```

Mock mode must exercise the same provider HTTP client and validators as live mode.

---

# 10. TIKTOK SCORER V2

Create a new rubric and rule version.

Do not modify historical v1 scores.

## 10.1 Typed result

Create:

```text
apps/backend/src/viraldy/modules/tiktok_scorer/contracts.py
```

```python
class ScoreSignalV2(BaseModel):
    code: str
    value: str | int | float | bool | None
    contribution: float
    confidence: float
    evidence_ids: list[UUID]

class DimensionScoreV2(BaseModel):
    dimension: str
    score: int
    confidence: Literal["low", "medium", "high"]
    reason: str
    signals: list[ScoreSignalV2]
    evidence_ids: list[UUID]
    missing_signals: list[str]

class BlockerV2(BaseModel):
    code: str
    severity: Literal["hard", "high", "medium"]
    message: str
    evidence_ids: list[UUID]
    remediation_code: str | None

class FixV2(BaseModel):
    code: str
    priority: int
    instruction: str
    why: str
    expected_impact_dimensions: list[str]
    evidence_ids: list[UUID]

class StrengthV2(BaseModel):
    code: str
    message: str
    dimensions: list[str]
    evidence_ids: list[UUID]

class TikTokScoreResultV2(BaseModel):
    schema_version: Literal["tiktok_score_v2"]
    structural_score: int
    confidence: Literal["low", "medium", "high"]
    action: Literal[
        "reject_or_reshoot",
        "revise",
        "organic_ready_or_small_test",
        "approve_structure",
    ]
    dimensions: dict[str, DimensionScoreV2]
    strengths: list[StrengthV2]
    blockers: list[BlockerV2]
    fixes: list[FixV2]
    rubric_version: Literal["tiktok_structure_rubric_v2"]
    rule_version: Literal["tiktok_structure_rules_v2"]
    disclaimer: str
```

## 10.2 Dimension calculators

Implement separate calculators:

```text
HookClarityCalculator
ProductVisibilityCalculator
DemoClarityCalculator
ProofStrengthCalculator
CreatorAuthenticityCalculator
OfferClarityCalculator
CtaReadinessCalculator
TikTokNativeFitCalculator
ClaimSafetyCalculator
```

Each receives:

```text
CreativeDnaV1
EvidenceBundle
ProductContextV1 optional
```

Each returns `DimensionScoreV2`.

## 10.3 Initial deterministic signal formulas

The exact implementation may adjust weights after golden evaluation, but it must be signal-driven.

### Hook clarity

```text
hook detected                              20
starts within first 1.5 seconds            20
clear semantic proposition                 20
visual and spoken/overlay consistency      15
specific buyer pain/result                 15
opening evidence confidence                10
```

### Product visibility

```text
first appearance timing                    40
total screen-time ratio                    20
clear close-up/hero shot                   15
usage visible                              15
product match confidence                   10
```

### Demo clarity

```text
demo detected                              15
step completeness                          25
mechanism visible                          25
before/after or result visible             20
continuity                                 10
evidence confidence                         5
```

### Proof strength

```text
proof present                              20
observable/verifiable result               25
proof type strength                        20
specificity                                15
source credibility                         10
evidence confidence                        10
```

### Creator authenticity

```text
creator/voice presence                     15
native delivery style                      20
authenticity cues                          20
sales-language restraint                   15
emotion/context fit                        10
pacing                                     10
evidence confidence                        10
```

Do not assume face presence is always better.

Faceless demonstrations may be strong for some formats.

### Offer clarity

```text
offer/value present                        30
specificity                                25
consistency across speech/overlay          15
timing before CTA                          15
product/commercial-context match           15
```

No offer may be acceptable for organic/reference analysis.

Scoring reason must state that limitation.

### CTA readiness

```text
CTA present                                30
CTA clarity                                25
product tag/shop cue                       20
timing                                     15
spoken/overlay consistency                 10
```

### TikTok-native fit

```text
vertical format                            15
opening pacing                             20
caption/overlay use                        15
creator-native delivery                    20
pattern interrupts/editing                 15
shop-native cues                           15
```

### Claim safety

Start from 100 and subtract deterministic penalties:

```text
critical prohibited claim                 hard blocker
high-risk unsupported claim               -80
medium-risk unsupported claim             -40
low-risk ambiguous claim                  -15
missing required qualification            additional penalty
```

Use ProductContext governance where available.

## 10.4 Weight validation

Keep current top-level dimension weights unless intentionally changed.

Validate:

- Sum exactly 1.0.
- Scores remain 0..100.
- Same inputs produce same outputs.
- LLM output cannot override final score.
- Missing evidence is represented.
- Strengths are derived from actual high-scoring dimensions.
- No unconditional fixed strengths.

## 10.5 Blocker registry

Implement at least:

```text
PRODUCT_NOT_VISIBLE
PRODUCT_MISMATCH
HIGH_RISK_UNSUPPORTED_CLAIM
CRITICAL_PROHIBITED_CLAIM
MEDIA_UNREADABLE
VISUAL_EVIDENCE_INSUFFICIENT
```

Quick structural scoring should not enforce Campaign Pack requirements.

Those belong to Preflight.

## 10.6 Fix registry

Create deterministic fix templates keyed by signal/rule code.

The LLM may rewrite for tone later, but may not remove hard requirements.

---

# 11. ADAPTATION V2

## 11.1 Typed input

```python
class AdaptationInputV2(BaseModel):
    schema_version: Literal["adaptation_v2"]
    product_snapshot: ProductContextV1
    creative_dna: CreativeDnaV1
    objective: str
    target_market: str
    selected_persona_id: str | None
    constraints: AdaptationConstraintsV2
```

## 11.2 Typed output

```python
class AdaptationGuidanceV2(BaseModel):
    element_type: str
    source_path: str
    action: Literal["keep", "change", "avoid"]
    reason: str
    evidence_ids: list[UUID]
    product_context_refs: list[str]
    risk_codes: list[str]

class AdaptationConceptV2(BaseModel):
    id: str
    name: str
    strategic_axis: str
    angle: str
    buyer_persona_id: str | None
    buyer_pain: str
    desired_outcome: str
    creator_persona: str
    delivery_style: str
    hook_options: list[str]
    opening_visual: str
    demo_mechanism: str
    demo_sequence: list[str]
    proof_mechanism: str
    offer_framing: str | None
    cta_strategy: str
    claim_guardrails: list[str]
    must_show: list[str]
    risks: list[dict[str, object]]
    test_hypothesis: str
    source_evidence_ids: list[UUID]

class AdaptationOutputV2(BaseModel):
    schema_version: Literal["adaptation_v2"]
    guidance: list[AdaptationGuidanceV2]
    concepts: list[AdaptationConceptV2]
    uncertainties: list[str]
```

## 11.3 Diversity validator

Exactly three concepts.

They must differ meaningfully across at least two axes:

```text
buyer persona/pain
angle
creator persona/delivery
demo mechanism
proof mechanism
offer framing
opening mechanism
```

Reject outputs that merely rephrase the same concept.

## 11.4 No category hardcode

Remove all kitchen-specific defaults from shared code.

Fixture generators may be category-specific per fixture case.

Production code must use ProductContext.

---

# 12. CAMPAIGN PACK BRIEF CONTRACT

Create:

```text
apps/backend/src/viraldy/modules/campaign_packs/contracts.py
```

## 12.1 Typed structure

```python
class CampaignObjectiveV1(BaseModel):
    objective_type: str
    primary_action: str
    channel: Literal["tiktok_shop", "tiktok_organic", "tiktok_paid", "unknown"]

class CampaignAudienceV1(BaseModel):
    persona_id: str | None
    persona_label: str
    pain_points: list[str]
    desired_outcomes: list[str]
    objections: list[str]
    awareness_stage: str

class CampaignAngleV1(BaseModel):
    name: str
    promise: str
    mechanism: str
    emotional_driver: str
    differentiation: str | None

class CreatorDirectionV1(BaseModel):
    persona: str
    delivery_style: str
    tone: list[str]
    avoid_tones: list[str]
    authenticity_notes: list[str]

class HookOptionV1(BaseModel):
    id: str
    spoken_text: str | None
    overlay_text: str | None
    opening_visual: str
    hook_type: str
    target_time_ms: int
    mandatory: bool

class ScriptBeatV1(BaseModel):
    id: str
    sequence: int
    beat_type: str
    instruction: str
    expected_start_ms: int | None
    expected_end_ms: int | None
    required: bool

class StoryboardSceneV1(BaseModel):
    id: str
    sequence: int
    instruction: str
    shot_type: str
    product_visibility_required: bool
    overlay_text: str | None
    spoken_direction: str | None
    required: bool

class MustShowRequirementV1(BaseModel):
    id: str
    requirement_type: Literal[
        "product",
        "demo",
        "proof",
        "offer",
        "cta",
        "overlay",
        "creator",
        "scene",
        "claim",
    ]
    description: str
    severity: Literal["hard", "high", "medium", "low"]
    expected_before_ms: int | None
    source_path: str

class CtaDirectionV1(BaseModel):
    spoken: str | None
    overlay: str | None
    cta_type: str
    product_tag_required: bool
    required_before_ms: int | None

class ClaimGuardrailsV1(BaseModel):
    allowed: list[str]
    allowed_with_qualification: list[str]
    prohibited: list[str]
    required_disclosures: list[str]

class RightsNoteV1(BaseModel):
    raw_footage_requested: bool
    editing_permission_requested: bool
    spark_authorization_requested: bool
    note: str

class CampaignPackBriefV1(BaseModel):
    schema_version: Literal["campaign_pack_brief_v1"]
    product_snapshot: ProductContextV1
    objective: CampaignObjectiveV1
    audience: CampaignAudienceV1
    angle: CampaignAngleV1
    creator_direction: CreatorDirectionV1
    hooks: list[HookOptionV1]
    script_beats: list[ScriptBeatV1]
    storyboard: list[StoryboardSceneV1]
    must_show: list[MustShowRequirementV1]
    talking_points: list[str]
    text_overlays: list[str]
    proof_direction: list[str]
    offer_direction: list[str]
    cta: CtaDirectionV1
    claim_guardrails: ClaimGuardrailsV1
    do: list[str]
    dont: list[str]
    rights_note: RightsNoteV1
    revision_checklist: list[str]
    source_adaptation_run_id: UUID
    source_concept_id: str
```

## 12.2 API rules

Replace:

```python
brief_json: dict[str, object]
```

at request boundaries with:

```python
brief: CampaignPackBriefV1
```

Persistence may still use `brief_json`.

New version creation must validate the full contract.

Invalid dictionaries must return a validation error.

## 12.3 Status

Use controlled statuses:

```text
draft
ready
sent
archived
```

Do not use arbitrary strings.

## 12.4 Product-specific generation

Campaign Pack generation must derive from:

```text
AdaptationConceptV2
ProductContextV1 snapshot
objective
target buyer
claim governance
```

Remove all kitchen-specific hardcoded defaults.

---

# 13. BRIEF REQUIREMENT COMPILER

Create:

```text
apps/backend/src/viraldy/modules/preflight/requirements.py
```

## 13.1 Compile typed brief into explicit requirements

```python
class CompiledRequirementV1(BaseModel):
    id: str
    requirement_type: str
    source_path: str
    description: str
    severity: Literal["hard", "high", "medium", "low"]
    matcher_type: str
    matcher_config: dict[str, object]
```

Compile from:

```text
hooks
script beats
storyboard
must_show
CTA
claim guardrails
product snapshot
offer direction
creator direction
text overlays
```

Examples:

```text
product must appear before 3000ms
product must be visible in use
required demo mechanism must be present
before/after result must be visible
product tag CTA required before end
specific overlay must be detected
prohibited claim must not appear
required disclosure must appear
creator delivery style should match
```

## 13.2 Persistence

Store compiled requirements with the Campaign Pack version:

```text
campaign_pack_versions.compiled_requirements_json JSONB
requirements_schema_version varchar
```

Compilation must occur when a version is created.

Preflight must use the immutable compiled requirements saved with that version.

---

# 14. PREFLIGHT V2

## 14.1 Requirement evaluation

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

class BriefAlignmentResultV2(BaseModel):
    schema_version: Literal["ugc_preflight_v2"]
    score: int
    confidence: Literal["low", "medium", "high"]
    requirements: list[RequirementEvaluationV2]
    coverage: dict[str, object]
    blockers: list[BlockerV2]
    fixes: list[FixV2]
```

## 14.2 Deterministic matchers

Implement matchers for:

```text
product visibility timing
product match
product in-use visibility
demo present
demo mechanism
before/after presence
proof type
CTA presence/type/timing
product tag
offer presence
overlay text similarity
spoken keyword similarity
claim allow/prohibit/qualification
creator style
scene coverage
```

LLM-assisted semantic matchers may be used for:

```text
hook meaning
buyer pain alignment
angle alignment
creator delivery similarity
demo-mechanism semantic classification
```

When an LLM matcher is used:

- It returns only requirement status, confidence, reason, and evidence IDs.
- It cannot set final preflight score/action.
- It must reference existing evidence.
- It must be audited in `ai_model_runs`.

## 14.3 No list-length scoring

Delete logic equivalent to:

```text
must_show_score = 80 if len(must_show) >= 3
```

Score actual requirement satisfaction.

## 14.4 Alignment score

Initial formula:

```text
hard requirements: evaluated individually and may create blockers
weighted requirement coverage: 100-point brief-alignment score
```

Suggested requirement weights:

```text
product match/visibility        25%
demo/must-show                  25%
hook/angle                      15%
proof                           10%
CTA/offer                       10%
claim safety                    10%
creator/format                   5%
```

If a group has no requirements, redistribute its weight deterministically or mark not applicable.

## 14.5 Final score

Keep:

```text
80% structural score
20% brief alignment
```

for continuity.

Persist the formula version.

Hard blockers override the numeric band.

## 14.6 Actions

```text
reject
reject_or_reshoot
revise
organic_ready_or_small_paid_test
spark_ready_pending_rights
```

Never return `spark_ready` without pending-rights wording.

## 14.7 Revision message

Generate from deterministic missing/violated requirements.

The model may rewrite the message for creator tone, but:

- Critical requirements cannot be removed.
- Claim-risk warnings cannot be softened away.
- Evidence references remain available in the structured result.

---

# 15. DATABASE MIGRATION

Create a new migration after `0003_keyless_product_hardening`.

Do not edit old migrations.

Suggested revision:

```text
0004_creative_domain_contracts
```

## 15.1 Products

Add:

```text
product_context_json JSONB nullable initially
context_schema_version varchar nullable initially
```

Backfill minimal valid contexts.

Then make non-null if safely possible.

## 15.2 Evidence

Add:

```text
evidence_schema_version varchar
```

Optional:

```text
observation_id varchar
```

## 15.3 Creative DNA

Add:

```text
schema_version varchar
```

Backfill old rows as:

```text
creative_dna_legacy_v1
```

New rows use:

```text
creative_dna_v1
```

## 15.4 TikTok score

Add:

```text
schema_version varchar
```

Historical runs:

```text
tiktok_score_v1
```

New runs:

```text
tiktok_score_v2
```

## 15.5 Adaptation

Add:

```text
schema_version varchar
product_snapshot_json JSONB
product_context_schema_version varchar
```

## 15.6 Campaign Pack versions

Add:

```text
brief_schema_version varchar
product_snapshot_json JSONB
compiled_requirements_json JSONB
requirements_schema_version varchar
```

## 15.7 Preflight

Add:

```text
schema_version varchar
product_snapshot_json JSONB
product_context_schema_version varchar
requirements_snapshot_json JSONB
```

## 15.8 Recommendation

Add:

```text
payload_schema_version varchar
```

if the existing model lacks it.

---

# 16. BACKWARD COMPATIBILITY

## 16.1 Historical rows

Existing fixture/mock data must remain readable.

Create explicit adapters:

```text
legacy Creative DNA → legacy response
legacy Campaign Pack → legacy response
legacy score/preflight → legacy response
```

Do not pretend legacy payloads are valid new contracts.

## 16.2 API

Preferred approach:

- Existing endpoint paths remain.
- Responses gain `schema_version`.
- New typed fields use stable names.
- Frontend is updated in the same goal.
- No new `/v2` URL is required unless source conventions demand it.

## 16.3 Fixture data

Replace one kitchen-only fixture with a small multi-category fixture pack.

Keep deterministic behavior.

---

# 17. GOLDEN SEMANTIC CASES

Create a focused golden evaluation set.

Required categories:

```text
home organization
beauty tool
POD personalized gift
pet accessory
fashion/accessory
```

Required conditions:

```text
strong problem-first hook
result-first hook
late product reveal
product absent
clear demo
unclear demo
before/after proof
testimonial proof
no proof
CTA present
CTA missing
offer present
offer missing
no speech
heavy OCR
high-risk unsupported claim
required disclosure missing
brief product mismatch
must-show scene missing
```

## 17.1 Golden case format

```yaml
case_id: beauty_tool_late_reveal_001
category: beauty_tool
asset_fixture: ...
product_context_fixture: ...
campaign_pack_fixture: ...

expected_observations:
  hook_type:
    allowed: [problem_first, curiosity]
  product_first_appearance_ms:
    min: 4500
    max: 7500
  demo_detected: true
  cta_present: true

expected_dna:
  demo.demo_type:
    allowed: [usage, tutorial]
  product.close_up_present: true

expected_score:
  action:
    allowed: [revise]
  required_fixes:
    - LATE_PRODUCT_REVEAL

expected_preflight:
  missing_requirements:
    - product_before_3000ms
```

## 17.2 Evaluation dimensions

Evaluate:

```text
schema validity
no fabricated evidence
timestamp tolerance
evidence ID validity
observation agreement
DNA classification agreement
score reproducibility
blocker agreement
fix coverage
requirement-alignment agreement
cross-category hardcode leakage
```

## 17.3 Hardcode-leak test

A beauty/POD/pet case must not contain:

```text
kitchen
counter
no-drill storage
apartment renter
home organizer
```

unless present in the fixture input.

---

# 18. FRONTEND HARDENING

Do not redesign the whole application.

Update the existing workflow UI.

## 18.1 Typed API layer

Replace generic records with typed frontend contracts corresponding to:

```text
ProductContextV1
CreativeDnaV1
TikTokScoreResultV2
AdaptationOutputV2
CampaignPackBriefV1
BriefAlignmentResultV2
```

Use OpenAPI generation or maintained shared TypeScript types.

## 18.2 Creative DNA UI

Render:

```text
opening
product
narrative
demo
proof
creator
editing
offer
CTA
claims/risks
reusable mechanisms
uncertainties
completeness
evidence timeline
```

Unknown fields must display as unknown, not disappear as success.

## 18.3 Score UI

Render:

```text
dimension signals
missing signals
confidence
evidence
blockers
fixes
structural-score disclaimer
```

## 18.4 Campaign Pack editor

Use structured sections.

Do not allow the UI to send arbitrary malformed dictionaries.

Client validation must mirror the backend contract.

## 18.5 Preflight UI

Render requirement coverage:

```text
Satisfied
Partial
Missing
Violated
Unknown
Not applicable
```

Each item should show:

```text
expected
observed
reason
evidence
fix
```

## 18.6 Mode/version detail

Development details may show:

```text
analysis mode
pipeline version
schema version
model
prompt
rubric
rule
```

---

# 19. MODULE BOUNDARIES

Preserve modular-monolith boundaries.

## 19.1 `products.public`

Expose:

```text
get_product_context_snapshot
validate_product_context
```

## 19.2 `media_analysis.public`

Expose:

```text
get_evidence_bundle
get_media_observation_bundle
validate_evidence_refs
```

## 19.3 `creative_dna.public`

Expose:

```text
get_creative_dna_snapshot
get_creative_dna_v1
```

## 19.4 `tiktok_scorer.public`

Expose:

```text
score_from_creative_dna
score_from_evidence_bundle
```

## 19.5 `campaign_packs.public`

Expose:

```text
get_pack_version_snapshot
get_compiled_requirements
```

## 19.6 No deep imports

Do not import another module's repository or ORM model when a public contract exists.

---

# 20. FAILURE CODES

Add or normalize:

```text
PRODUCT_CONTEXT_INVALID
PRODUCT_CONTEXT_NOT_FOUND
MEDIA_OBSERVATION_INVALID
MEDIA_OBSERVATION_INCONSISTENT
EVIDENCE_SCHEMA_INVALID
EVIDENCE_REFERENCE_INVALID
CREATIVE_DNA_SCHEMA_INVALID
CREATIVE_DNA_EVIDENCE_MISMATCH
TIKTOK_SCORE_INPUT_INVALID
CAMPAIGN_PACK_SCHEMA_INVALID
CAMPAIGN_PACK_REQUIREMENTS_INVALID
PREFLIGHT_REQUIREMENT_EVALUATION_FAILED
PREFLIGHT_EVIDENCE_INSUFFICIENT
MODEL_RESPONSE_INVALID
MODEL_EVIDENCE_REFERENCE_INVALID
```

Do not leak provider payloads or secrets.

---

# 21. HARDENING MILESTONES

Execute in order.

## C0 — BASELINE AND CONTRACT INVENTORY

- [x] Confirm current branch and commit.
- [x] Preserve the passing keyless hardening state.
- [x] Run existing fixture smoke.
- [x] Run existing mock-provider smoke.
- [x] Inventory every generic `dict[str, object]` in core creative modules.
- [x] Inventory every hardcoded category-specific value.
- [x] Inventory fixed timestamps and fixed scores.
- [x] Record findings in the Execution Log.

### Exit

The exact legacy path is documented and reproducible.

---

## C1 — PRODUCT CONTEXT V1

- [x] Add `ProductContextV1`.
- [x] Add nested buyer/commercial/creative/governance contracts.
- [x] Add migration columns.
- [x] Backfill existing products without fabricating facts.
- [x] Update product create/update/read APIs.
- [x] Add product snapshot public contract.
- [x] Add unit validation cases.
- [x] Update seeded products.

### Exit

Every new adaptation/brief/preflight can receive a validated product context.

---

## C2 — MEDIA OBSERVATION V1

- [x] Add comprehensive observation contracts.
- [x] Update provider prompt/schema.
- [x] Add timestamp and consistency validators.
- [x] Update mock provider.
- [x] Remove shallow observation assumptions.
- [x] Add multi-category fixture observations.
- [x] Persist observation schema version.
- [x] Add failure cases for malformed provider output.

### Exit

Provider output contains enough evidence for real Creative DNA/scoring and contains no fixed domain defaults.

---

## C3 — TYPED EVIDENCE V1

- [x] Add discriminated evidence value contracts.
- [x] Add evidence schema version.
- [x] Replace fixed evidence rows.
- [x] Persist only detected observations.
- [x] Remove fixed CTA/demo/proof timestamps.
- [x] Validate evidence identity and references.
- [x] Update evidence bundle completeness.
- [x] Add no-fabrication regression tests.

### Exit

Every evidence row is traceable to actual media/provider observation or deterministic extraction.

---

## C4 — CREATIVE DNA V1

- [x] Add typed Creative DNA contract.
- [x] Add field-level confidence/evidence/status.
- [x] Remove kitchen hardcodes.
- [x] Build DNA from typed evidence.
- [x] Add optional taxonomy-classification provider path.
- [x] Validate every evidence ID.
- [x] Calculate deterministic completeness/confidence.
- [x] Separate reusable mechanisms from product adaptation.
- [x] Persist schema version.
- [x] Keep legacy reads.
- [x] Update API/frontend.

### Exit

The same builder can analyze multiple categories without leaking fixture language.

---

## C5 — TIKTOK SCORER V2

- [x] Add typed score result.
- [x] Add rubric v2.
- [x] Split dimension calculators.
- [x] Implement signal-based formulas.
- [x] Remove fixed scores and fixed strengths.
- [x] Add blocker registry.
- [x] Add fix registry.
- [x] Handle missing evidence explicitly.
- [x] Preserve disclaimer.
- [x] Persist score schema version.
- [x] Add golden deterministic cases.

### Exit

Scores and actions change because real signals change, not because an evidence type merely exists.

---

## C6 — ADAPTATION V2

- [x] Add typed adaptation input/output.
- [x] Persist product snapshot.
- [x] Expand concept semantics.
- [x] Validate evidence references.
- [x] Enforce exactly three concepts.
- [x] Enforce meaningful concept diversity.
- [x] Remove category hardcodes.
- [x] Update provider prompt/schema/mock.
- [x] Update frontend.

### Exit

Adaptation is product-specific and evidence-backed across multiple categories.

---

## C7 — CAMPAIGN PACK BRIEF V1

- [x] Add typed Campaign Pack contract.
- [x] Validate create/version requests.
- [x] Persist schema/product/provenance.
- [x] Remove arbitrary brief dictionaries.
- [x] Remove kitchen defaults.
- [x] Generate from ProductContext + AdaptationConcept.
- [x] Add compiled requirement contract.
- [x] Compile and persist requirements at version creation.
- [x] Update version history/frontend.

### Exit

Every Campaign Pack version is a valid immutable creator-ready brief.

---

## C8 — PREFLIGHT V2

- [x] Add typed requirement evaluation.
- [x] Add deterministic matchers.
- [x] Add model-assisted semantic matchers only where needed.
- [x] Remove list-length scoring.
- [x] Evaluate every compiled requirement.
- [x] Add product-match validation.
- [x] Add claim guardrail validation.
- [x] Add requirement-derived blockers/fixes.
- [x] Keep 80/20 final formula with versioning.
- [x] Persist requirement snapshot and schema version.
- [x] Update revision-message generation.
- [x] Update frontend requirement coverage.

### Exit

Preflight verifies the uploaded UGC against the exact immutable Campaign Pack version.

---

## C9 — MULTI-CATEGORY GOLDEN EVALUATION

- [x] Add five product categories.
- [x] Add strong/weak/edge cases.
- [x] Run fixture evaluations.
- [x] Run mock-provider evaluations.
- [x] Verify no category hardcode leakage.
- [x] Verify no fabricated evidence.
- [x] Verify score reproducibility.
- [x] Verify requirement alignment.
- [x] Record pass/failure metrics.

### Exit

The semantic contracts work outside the original kitchen fixture.

---

## C10 — END-TO-END REGRESSION AND HANDOFF

- [x] Apply migrations `0001` through `0004` to a clean DB.
- [x] Seed multi-category data.
- [x] Run fixture Quick Scorer.
- [x] Run fixture full loop.
- [x] Run mock-provider Quick Scorer.
- [x] Run mock-provider full loop.
- [x] Verify historical v1 records remain readable.
- [x] Verify new writes use typed schemas.
- [x] Run backend checks.
- [x] Run frontend lint/build.
- [x] Update audit.
- [x] Update Execution Log.
- [x] List deferred live-provider uncertainties.

### Exit

The product is semantically ready for live-model qualification and private-beta review.

---

# 22. DEFINITION OF DONE

## Product context

- [x] New products have valid `ProductContextV1`.
- [x] Missing information remains unknown/empty.
- [x] Generated runs store product snapshots.
- [x] Historical results are unaffected by product edits.

## Media observations

- [x] Observation contract covers opening/product/demo/proof/CTA/offer/creator/editing/claims/platform.
- [x] Timestamps are valid.
- [x] No observation is fabricated.
- [x] Live/mock responses are strictly validated.
- [x] Schema version persists.

## Evidence

- [x] New evidence payloads are typed.
- [x] No fixed hook/demo/proof/CTA timestamps remain in production logic.
- [x] No CTA evidence exists when CTA is absent.
- [x] No demo evidence exists when demo is absent.
- [x] Every evidence item has provenance and schema version.
- [x] Retry dedupe remains intact.

## Creative DNA

- [x] No category-specific hardcoded content remains.
- [x] Every observed conclusion has valid evidence IDs.
- [x] Unknown fields remain unknown.
- [x] Confidence is calculated from evidence.
- [x] Creative DNA is valid `CreativeDnaV1`.
- [x] Historical rows remain readable.

## Scoring

- [x] No dimension uses unconditional fixed success scores.
- [x] Scores derive from signals.
- [x] Missing evidence reduces confidence.
- [x] Strengths derive from actual dimensions.
- [x] Blockers override bands.
- [x] LLM cannot set final score/action.
- [x] Score v2 is deterministic.

## Adaptation

- [x] Uses full product snapshot.
- [x] Uses exact Creative DNA version.
- [x] Exactly three concepts.
- [x] Concepts are meaningfully different.
- [x] No fixture-category leakage.
- [x] Output is typed.

## Campaign Pack

- [x] `brief_json` is validated as `CampaignPackBriefV1`.
- [x] Arbitrary dictionaries are rejected.
- [x] Product snapshot persists.
- [x] Requirements compile and persist.
- [x] Version history remains immutable.
- [x] No kitchen defaults remain in shared code.

## Preflight

- [x] Evaluates actual requirements.
- [x] Does not score list length.
- [x] Product mismatch can block.
- [x] Must-show coverage uses evidence.
- [x] CTA/offer/claim requirements use evidence.
- [x] Each requirement has expected/observed/evidence.
- [x] Final action is deterministic.
- [x] Rights wording remains pending-rights.

## Multi-category

- [x] Home case passes.
- [x] Beauty case passes.
- [x] POD case passes.
- [x] Pet case passes.
- [x] Fashion/accessory case passes.
- [x] No cross-category hardcode leakage.

## Runtime

- [x] Fixture mode passes.
- [x] Mock-provider HTTP mode passes.
- [x] Existing job/model-run hardening remains.
- [x] No silent fallback exists.
- [x] Clean migration succeeds.
- [x] Frontend build succeeds.

---

# 23. EXECUTION LOG

Update after every milestone.

## Template

```text
Date:
Milestone:
Status: not_started | in_progress | completed | blocked

Branch:
Commit:
Files changed:
Migration changes:
Contracts added:
Legacy adapters:
Commands run:
Results:
Semantic cases:
Known failures:
Blockers:
Notes:
```

## C0

```text
Date: 2026-07-29
Milestone: C0 — Baseline and contract inventory
Status: completed

Branch: hardening/keyless-product-hardening
Commit: d16a32d
Files changed:
- VIRALDY_CREATIVE_DOMAIN_INTELLIGENCE_HARDENING_GOAL.md
Migration changes:
- none
Contracts added:
- none
Legacy adapters:
- none
Commands run:
- git branch --show-current
- git rev-parse --short HEAD
- docker compose -p viraldy-cdomain -f docker-compose.h9.yml up -d postgres redis minio minio-init
- alembic upgrade head
- scripts/seed_local.py
- scripts/smoke_mvp_flow.py --expect-mode fixture --verify-db --run-id cdomain-c0-fixture
- scripts/mock_openai_provider.py
- scripts/smoke_mvp_flow.py --expect-mode mock --verify-db --run-id cdomain-c0-mock
- rg inventory for brief_json, dict[str, object], hardcoded kitchen/counter values, fixed timestamps, fixed scores
Results:
- Branch confirmed as hardening/keyless-product-hardening at d16a32d.
- Fixture HTTP smoke passed with quick_score_run_id ebbc04b6-47b8-49e9-b2d7-0842727ecafa, creative_dna_version_id 23ed7693-189c-485a-b557-ba2c3bb1ee48, adaptation_run_id ee56071d-5eb0-464a-9b8e-ffe69f47a94a, campaign_pack_version_id 47ad9285-6eb9-4d9b-a257-1bef29836e60.
- Mock-provider HTTP smoke passed with quick_score_run_id 97384470-cc8b-4b1c-ac41-d5a91d05a9dc, creative_dna_version_id d71aa9bc-4f3f-4578-80c8-167206332df9, adaptation_run_id 094972dd-67aa-4340-9f27-11eb41cf7634, campaign_pack_version_id ba1b0aed-aefb-4171-a26b-ee497a030490.
- Sample media-analysis endpoint response is reproducible and contains artifacts, evidence, and evidence_bundle.
Semantic cases:
- Legacy fixture/mock currently exercise a kitchen organizer scenario only.
Known failures:
- apps/backend/src/viraldy/modules/creative_dna/service.py contains hardcoded problem_first, counter/kitchen opening copy, screen_time_ratio=0.42, before_after, small_space_organization, and home_organizer.
- apps/backend/src/viraldy/modules/media_analysis/service.py creates fixed hook/demo/proof/CTA rows, including 0-2100ms hook, 6500-15000ms demo, 15000-18200ms proof, and 18200-27000ms CTA.
- apps/backend/src/viraldy/modules/tiktok_scorer/scorer.py assigns fixed dimension scores and unconditional strengths when evidence types exist.
- apps/backend/src/viraldy/modules/preflight/service.py uses list-length scoring for must_show.
- apps/backend/src/viraldy/modules/campaign_packs/schemas.py and service.py expose generic brief_json and kitchen defaults.
- apps/backend/scripts/mock_openai_provider.py returns only kitchen/counter scenario payloads.
- apps/web/src/features/mvp-flow/routes/mvp-route.tsx still models score dimensions and campaign brief as generic records.
Blockers:
- none
Notes:
- The active defect is semantic/domain intelligence, not job/provider/storage infrastructure.
```

## C1

```text
Date: 2026-07-29
Milestone: C1 — Product Context V1
Status: completed

Branch: hardening/keyless-product-hardening
Files changed:
- apps/backend/src/viraldy/modules/products/contracts.py
- apps/backend/src/viraldy/modules/products/{models,schemas,repository,service,public}.py
- apps/backend/alembic/versions/0004_creative_domain_contracts.py
- apps/backend/scripts/seed_local.py
Results:
- New products persist product_context_json and context_schema_version=product_context_v1.
- Seed creates five category product contexts: home_organization, beauty_tool, pod_personalized_gift, pet_accessory, fashion_accessory.
- Adaptation, Campaign Pack, and Preflight persist immutable product snapshots.
Commands run:
- pytest apps/backend/tests/unit/test_product_context.py -q --no-cov
- clean alembic upgrade head
```

## C2

```text
Date: 2026-07-29
Milestone: C2 — Media Observation V1
Status: completed

Files changed:
- apps/backend/src/viraldy/modules/media_analysis/contracts.py
- apps/backend/src/viraldy/modules/media_analysis/{provider,fixtures,service,schemas,models,repository,public}.py
- apps/backend/scripts/mock_openai_provider.py
Results:
- Provider/mock responses validate as MediaObservationBundleV1.
- Observation contract covers opening, product visibility, demo, proof, CTA, offer, creator, editing, claim, platform, and uncertainties.
- Mock provider supports 12 scenarios and bounds timestamps to media duration.
Commands run:
- pytest apps/backend/tests/unit/test_media_observation_contracts.py -q --no-cov
- mock scenario contract check: scenario_contracts_checked 12
```

## C3

```text
Date: 2026-07-29
Milestone: C3 — Typed Evidence V1
Status: completed

Files changed:
- apps/backend/src/viraldy/modules/media_analysis/evidence_contracts.py
- apps/backend/src/viraldy/modules/media_analysis/evidence_bundle.py
- apps/backend/src/viraldy/modules/media_analysis/service.py
Results:
- New evidence rows validate as evidence_v1.
- Evidence identity hash includes typed payload schema version.
- No CTA/offer/product/demo/proof observations are emitted for absence cases in the mock scenario contract check.
- OCR category leak was found and fixed; final hardcode_leak_count is 0.
Commands run:
- DB schema invariant query
- DB hardcode-leak query
- mock scenario no-fabrication check
```

## C4

```text
Date: 2026-07-29
Milestone: C4 — Creative DNA V1
Status: completed

Files changed:
- apps/backend/src/viraldy/modules/creative_dna/contracts.py
- apps/backend/src/viraldy/modules/creative_dna/{service,repository,schemas,models,public}.py
- apps/backend/src/viraldy/modules/creative_dna/taxonomy.py
Results:
- Creative DNA is built from typed evidence rows, not kitchen defaults.
- Field-level observed/unknown status, confidence, and evidence IDs are persisted.
- New rows use schema_version=creative_dna_v1 and taxonomy_version=creative_dna_v1.
- Cross-category fixture/mock runs did not leak home/kitchen/counter language into non-home DNA.
Notes:
- Semantic classification currently comes from the MediaObservationBundle provider path and deterministic DNA projection; no separate live-only Creative DNA LLM override can set final score/action.
```

## C5

```text
Date: 2026-07-29
Milestone: C5 — TikTok Scorer V2
Status: completed

Files changed:
- apps/backend/src/viraldy/modules/tiktok_scorer/contracts.py
- apps/backend/src/viraldy/modules/tiktok_scorer/{scorer,rubric,repository,schemas,models,public}.py
- apps/backend/tests/unit/test_tiktok_scorer.py
Results:
- New score runs persist schema_version=tiktok_score_v2.
- Scores are signal-driven by hook, product visibility, demo, proof, creator, offer, CTA, native fit, and claim safety.
- Missing evidence is represented in missing_signals and confidence/action changes.
- Product mismatch and risky claims can create blockers.
Commands run:
- pytest apps/backend/tests/unit/test_tiktok_scorer.py -q --no-cov
- fixture and mock HTTP smoke with --verify-db
```

## C6

```text
Date: 2026-07-29
Milestone: C6 — Adaptation V2
Status: completed

Files changed:
- apps/backend/src/viraldy/modules/adaptations/contracts.py
- apps/backend/src/viraldy/modules/adaptations/{provider,service,repository,schemas,models}.py
Results:
- Adaptation input includes product snapshot and Creative DNA.
- Output validates as adaptation_v2.
- Exactly three concepts are required and diversity is enforced across strategic axes.
- Non-home adaptation rows passed hardcode-leak checks.
```

## C7

```text
Date: 2026-07-29
Milestone: C7 — Campaign Pack Brief V1
Status: completed

Files changed:
- apps/backend/src/viraldy/modules/campaign_packs/contracts.py
- apps/backend/src/viraldy/modules/campaign_packs/{service,repository,schemas,models,public}.py
- apps/backend/src/viraldy/modules/preflight/requirements.py
Results:
- Version creation validates CampaignPackBriefV1 from the `brief` request field.
- Campaign Pack versions persist brief_schema_version, product_snapshot_json, compiled_requirements_json, and requirements_schema_version.
- Arbitrary malformed brief dictionaries are rejected by Pydantic/FastAPI validation.
```

## C8

```text
Date: 2026-07-29
Milestone: C8 — Preflight V2
Status: completed

Files changed:
- apps/backend/src/viraldy/modules/preflight/contracts.py
- apps/backend/src/viraldy/modules/preflight/{requirements,service,repository,schemas,models}.py
Results:
- Preflight uses immutable compiled requirements saved on the Campaign Pack version.
- List-length scoring was replaced by requirement-by-requirement evaluation.
- Product visibility, demo, proof, CTA, offer, overlay/spoken text, claim guardrails, and creator/format requirements are evaluated deterministically.
- Final action keeps pending-rights wording; no bare spark_ready is returned.
Notes:
- Model-assisted semantic matchers were not needed for the verified MVP cases; deterministic matchers handle the current contract surface.
```

## C9

```text
Date: 2026-07-29
Milestone: C9 — Multi-Category Golden Evaluation
Status: completed

Semantic cases:
- Fixture: home/default, beauty, POD personalized gift, pet accessory, fashion/accessory.
- Mock HTTP: home/default, beauty, POD personalized gift, pet accessory, fashion/accessory.
- Mock provider direct contract cases: late_product_reveal, missing_cta, no_offer, no_speech, brief_mismatch, product_absent, high_risk_claim, malformed_json, missing_field.
Results:
- All fixture and mock category smoke flows passed.
- hardcode_leak_count 0 after OCR fix and rerun.
- schema invariant counts all 0 for new writes.
```

## C10

```text
Date: 2026-07-29
Milestone: C10 — End-to-End Regression and Handoff
Status: completed

Commands run:
- docker compose -p viraldy-cdomain -f docker-compose.h9.yml down -v
- docker compose -p viraldy-cdomain -f docker-compose.h9.yml up -d postgres redis minio minio-init
- alembic upgrade head
- scripts/seed_local.py
- scripts/smoke_mvp_flow.py --expect-mode fixture --verify-db for five category flows
- scripts/smoke_mvp_flow.py --expect-mode mock --verify-db for five category flows
- pytest tests/unit -q --no-cov
- ruff check src/viraldy scripts tests/unit
- pnpm lint
- pnpm build
Results:
- Backend unit: 38 passed, 1 warning.
- Backend ruff: all checks passed.
- Frontend lint: passed with existing react-refresh warnings.
- Frontend build: passed with chunk-size warnings.
- Audit written to VIRALDY_CREATIVE_DOMAIN_INTELLIGENCE_AUDIT.md.
Known live-provider uncertainties:
- Fixture/mock pass validates contracts and workflow, not live model extraction quality.
- Real MP4 category corpus and live-provider sampling remain required before private-beta confidence.
- Rights workflow remains informational and intentionally out of scope.
```

---

# 24. FINAL REPORT REQUIREMENTS

At completion, report:

1. Baseline branch/commit.
2. Hardcoded values removed.
3. Generic dictionaries replaced.
4. Contracts introduced.
5. Migration added.
6. Product-context changes.
7. Media-observation changes.
8. Evidence-type changes.
9. Creative DNA changes.
10. Scorer v2 formulas.
11. Adaptation v2 changes.
12. Campaign Pack schema changes.
13. Requirement compiler behavior.
14. Preflight v2 behavior.
15. Historical-row compatibility.
16. Fixture cases.
17. Mock-provider cases.
18. Multi-category results.
19. No-fabrication checks.
20. No-hardcode-leak checks.
21. Commands actually run.
22. What was not run.
23. Remaining live-provider risks.
24. Deferred performance/creator roadmap.
25. Final Definition of Done status.
26. Updated Execution Log.

Do not claim production intelligence readiness unless:

- Arbitrary uploaded categories no longer receive fixture-specific DNA.
- Evidence is not fabricated.
- Score dimensions use actual signals.
- Campaign Pack is typed.
- Preflight verifies actual brief requirements.
- Multi-category golden cases pass.

---

# 25. FINAL COMMAND TO CODEX

Read `VIRALDY_CREATIVE_DOMAIN_INTELLIGENCE_HARDENING_GOAL.md` and execute it as the single source of truth.

Preserve the existing keyless infrastructure hardening.

Do not deploy.

Do not build Performance CSV, PatternKit, Creator Fit, Sample ROI, rights workflow, or later roadmap features.

Continue from C0 through C10.

Update every checkbox and the Execution Log.

Do not stop after planning, migrations, Pydantic schemas, or scaffolding.

The goal is complete only when:

```text
ProductContextV1
→ MediaObservationBundleV1
→ typed Evidence V1
→ CreativeDnaV1
→ TikTokScoreResultV2
→ AdaptationOutputV2
→ CampaignPackBriefV1
→ compiled requirements
→ Preflight V2
```

runs end to end in fixture and mock-provider HTTP modes across multiple product categories without hardcoded category leakage or fabricated evidence.
