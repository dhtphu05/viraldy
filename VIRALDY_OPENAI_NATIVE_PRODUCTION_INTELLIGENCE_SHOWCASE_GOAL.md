# VIRALDY — OPENAI-NATIVE PRODUCTION INTELLIGENCE & COMMERCIAL SHOWCASE COMPLETION GOAL

**Repository:** `dhtphu05/viraldy`  
**Base branch:** `main`  
**Expected baseline:** PR #15 merged; private-beta backend technical freeze already exists.  
**Working branch:** `release/openai-production-intelligence-showcase`  
**Target release:** `v0.1.1-openai-showcase-rc1`

---

# 0. Mission

Implement a production-grade OpenAI integration and a canonical Viraldy prompt system so that the AI layer can run the complete supervised private-beta workflow with only one required secret filled by the operator:

```env
OPENAI_API_KEY=<real key>
```

All other OpenAI settings must have safe, documented defaults and remain overridable through environment variables.

The completed application must support this real workflow:

```text
Authenticated seller
→ Create Product Context
→ Upload/reference creative video
→ Media processing and observation
→ Creative DNA
→ PatternKit
→ ViralKit with exactly three differentiated concepts
→ Select concept
→ Creative Campaign Pack
→ Upload creator UGC draft
→ TikTok structural score
→ Exact Campaign Pack Preflight
→ Seller recommendation
→ Friendly creator revision message
→ Upload revision
→ Compare versions
→ Record seller action and feedback
```

The goal is not merely to make API requests succeed.

The goal is to make Viraldy outputs:

- grounded in the exact product and evidence;
- commercially useful for TikTok Shop US, POD and dropshipping sellers;
- friendly and clear enough for customer demonstrations;
- structured enough for persistence, measurement and later provider comparison;
- safe enough for a supervised paid pilot;
- portable to Dola/Seed later without rewriting domain intelligence.

Do not claim that entering an API key alone makes the entire application production-ready. PostgreSQL, Redis, object storage, worker, HTTPS, authentication and deployment configuration are still required infrastructure. This goal makes the **OpenAI intelligence path plug-and-play once normal Viraldy infrastructure is running**.

---

# 1. Authoritative product and quality references

Before changing code, read and treat the following as authoritative:

```text
VIRALDY_PRIVATE_BETA_TECH_FREEZE_AUDIT.md
VIRALDY_GOLDEN_OUTPUT_REFERENCE_AND_ACCEPTANCE_EXAMPLES.md
VIRALDY_PRIVATE_BETA_BACKEND_AUTH_PATTERNKIT_VIRALKIT_COMPLETION_GOAL.md
VIRALDY_CREATIVE_DOMAIN_INTELLIGENCE_HARDENING_GOAL.md
VIRALDY_PR14_SEMANTIC_CORRECTNESS_AUDIT.md
```

If one of these files is not in the repository but is supplied in the Codex workspace, copy it into an appropriate documentation location before implementation.

The Golden Output reference is the semantic quality bar. Do not replace its examples with generic marketing copy.

The current typed contracts and private-beta architecture remain the code-level source of truth. Do not perform a broad schema rewrite merely to fit a model response.

---

# 2. Required outcome

After implementation, the operator must be able to use a documented OpenAI environment template such as:

```env
AI_MODE=live
AI_PROVIDER=openai
OPENAI_API_KEY=replace_me
```

and receive working defaults for:

```env
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_TEXT_MODEL=gpt-5
OPENAI_VISION_MODEL=gpt-5
OPENAI_TRANSCRIPTION_MODEL=whisper-1
OPENAI_REASONING_EFFORT=medium
OPENAI_STORE_RESPONSES=false
OPENAI_MAX_OUTPUT_TOKENS=16000
OPENAI_REQUEST_TIMEOUT_SECONDS=180
OPENAI_MAX_RETRIES=2
OPENAI_IMAGE_DETAIL=auto
OPENAI_IMAGE_TRANSPORT=base64
```

Every setting must remain overridable.

Do not silently switch to fixture or mock mode when OpenAI fails.

If a configured model is unavailable, return a clear configuration error naming the operation and environment variable that must be changed. Do not expose the API key.

---

# 3. Scope freeze

## 3.1 In scope

Implement and qualify:

1. Native OpenAI provider adapter.
2. Responses API integration for structured text and image reasoning.
3. OpenAI Audio Transcriptions integration for timestamped ASR.
4. Canonical Viraldy system prompt.
5. Versioned operation prompts.
6. Strict structured outputs from existing Pydantic contracts.
7. Prompt registry and provider-neutral prompt packages.
8. Full OpenAI model-run provenance.
9. Friendly seller-facing and creator-facing presentation contracts.
10. OpenAI live qualification script.
11. Full live OpenAI E2E path.
12. Golden-case evaluation and regression tests.
13. Frontend rendering for customer-friendly outputs.
14. Documentation and production runbook.
15. CI that does not require a real OpenAI key.

## 3.2 Explicitly out of scope

Do not build:

```text
billing
creator marketplace
creator payment system
full video editor
automatic TikTok/Meta campaign creation
global ad crawler
GMV or virality prediction guarantees
new major product modules
fine-tuned proprietary foundation model
Seedream/Seedance production generation
Dola/Seed-specific prompt fork
```

Keep Dola/Seed compatibility through provider-neutral contracts and prompts, but do not implement unverified BytePlus behavior in this milestone.

---

# 4. Non-negotiable implementation rules

1. Inspect the current repository before editing.
2. Reuse the existing modular-monolith boundaries.
3. Do not put domain logic into the OpenAI client.
4. Do not put prompt text inline inside individual service methods.
5. Do not let an LLM invent deterministic scores.
6. Do not let friendly presentation replace the persisted structured result.
7. Never persist or log API keys.
8. Never log complete seller video URLs, presigned URLs, raw images, raw product payloads or full model responses in production logs.
9. Preserve exact input, prompt, schema, model and evidence provenance.
10. Use `unknown` or typed null states instead of guessing.
11. A provider response must pass the existing Pydantic contract before persistence.
12. Failed validation may use at most one bounded schema-repair attempt.
13. No silent fixture fallback in `live` mode.
14. Preserve current API behavior unless an intentional versioned change is documented.
15. Commit after each milestone.
16. Do not claim “production quality” from smoke success alone. Run the defined quality gates.

---

# 5. Provider architecture

Create or harden a provider-neutral interface under the AI gateway.

Suggested structure, adapted to the current repository rather than imposed blindly:

```text
apps/backend/src/viraldy/modules/ai_gateway/
├── providers/
│   ├── base.py
│   ├── openai_native.py
│   ├── openai_compatible.py
│   └── router.py
├── prompt_registry.py
├── prompt_packages.py
├── structured_output.py
├── capabilities.py
├── usage.py
└── public.py
```

The provider boundary must expose typed capabilities similar to:

```python
class StructuredGenerationRequest(BaseModel):
    operation: AiOperationName
    model: str
    system_prompt: str
    developer_prompt: str
    user_content: list[InputContentPart]
    output_model: type[BaseModel]
    prompt_version: str
    schema_version: str
    reasoning_effort: str | None
    max_output_tokens: int | None
    request_id: str
    input_hash: str


class StructuredGenerationResult(BaseModel):
    parsed_output: BaseModel
    provider: str
    model: str
    provider_request_id: str | None
    latency_ms: int
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    cached_input_tokens: int | None
    response_status: str
    refusal: str | None
    incomplete_reason: str | None
```

Use the official OpenAI Python SDK for the native OpenAI provider.

Keep the existing OpenAI-compatible HTTP adapter for later Dola/Seed or local mock-provider compatibility.

The router must select:

```text
AI_PROVIDER=openai
→ OpenAINativeProvider

AI_PROVIDER=openai_compatible
→ existing compatible adapter

AI_MODE=fixture
→ deterministic fixture provider

AI_MODE=mock
→ local mock-compatible provider
```

Do not infer provider from arbitrary URL strings in business services.

---

# 6. OpenAI native API requirements

## 6.1 Responses API

Use OpenAI Responses API for:

```text
media observation from sampled frames
Creative DNA construction where model reasoning is used
PatternKit extraction
ViralKit composition
adaptation generation
Campaign Pack generation
friendly decision summary
creator revision message
```

Use strict JSON Schema Structured Outputs generated from the exact Pydantic output model.

The request must include:

```text
system role: canonical Viraldy intelligence policy
developer role: operation-specific rules
user role: typed serialized business context and multimodal inputs
text format: json_schema
strict: true
store: false by default
```

Do not use legacy JSON mode when strict schema is available.

Handle these response states explicitly:

```text
completed
incomplete
failed
cancelled
refusal
```

Do not treat refusal text or incomplete output as valid JSON.

## 6.2 Audio transcription

Use OpenAI Audio Transcriptions for ASR.

Viraldy requires timestamps for evidence alignment. The default OpenAI transcription model must therefore support the response format needed by the current timestamp pipeline.

Use the following safe default unless repository tests prove a better compatible path:

```env
OPENAI_TRANSCRIPTION_MODEL=whisper-1
OPENAI_TRANSCRIPTION_RESPONSE_FORMAT=verbose_json
OPENAI_TRANSCRIPTION_TIMESTAMP_GRANULARITIES=segment
```

Allow optional word timestamps through configuration.

Do not send audio when the video has no audio stream.

Do not create fake transcript segments for silent videos.

## 6.3 Image transport

The default private-data transport should be base64 data URLs for sampled frames:

```env
OPENAI_IMAGE_TRANSPORT=base64
```

An optional signed-URL mode may exist, but:

- URLs must be short-lived;
- complete signed URLs must never be logged or persisted in model-run summaries;
- the provider request must not outlive the URL validity window;
- the default must remain base64 unless the operator opts in.

Do not send the entire source video to the text/vision model when sampled frames, transcript, OCR and scenes are sufficient.

## 6.4 Model defaults and routing

Implement default model routing in code, while allowing operation-level environment overrides.

Required optional variables:

```env
OPENAI_TEXT_MODEL=gpt-5
OPENAI_VISION_MODEL=gpt-5
OPENAI_MODEL_MEDIA_OBSERVATION=
OPENAI_MODEL_CREATIVE_DNA=
OPENAI_MODEL_PATTERN_KIT=
OPENAI_MODEL_VIRAL_KIT=
OPENAI_MODEL_ADAPTATION=
OPENAI_MODEL_CAMPAIGN_PACK=
OPENAI_MODEL_DECISION_SUMMARY=
OPENAI_MODEL_REVISION_MESSAGE=
OPENAI_TRANSCRIPTION_MODEL=whisper-1
```

Resolution order:

```text
operation-specific model
→ family model
→ documented default
```

Do not hardcode model IDs in service modules.

## 6.5 OpenAI request behavior

Implement:

- bounded retries for timeout, rate limit and retryable 5xx failures;
- exponential backoff with jitter;
- `Retry-After` support;
- request IDs;
- idempotency key when supported;
- explicit timeouts;
- cancellation propagation where practical;
- safe error mapping;
- usage extraction;
- cached-token extraction when available;
- model-run completion/failure persistence;
- `store=false` default;
- no automatic web search or external tools.

The model must never browse the web during Viraldy analysis. It must use only supplied product, creative and seller context.

---

# 7. Environment and “fill one key” developer experience

Create:

```text
.env.openai.example
docs/runbooks/OPENAI_PROVIDER.md
apps/backend/scripts/qualify_openai.py
```

`.env.openai.example` must contain all safe defaults and require the operator to fill only:

```env
OPENAI_API_KEY=
```

It must also include the normal Viraldy infrastructure variables as documented placeholders, but clearly distinguish them from AI settings.

Configuration behavior:

1. When `AI_MODE=live` and `AI_PROVIDER=openai`, `OPENAI_API_KEY` is required.
2. `OPENAI_BASE_URL` defaults to the official API base URL.
3. Model defaults resolve automatically.
4. Staging/production startup rejects an empty key.
5. Local development may use fixture/mock without a key.
6. A live OpenAI failure must never trigger fixture output.
7. `/health/dependencies` reports only safe states:

```text
configured
not_configured
configuration_invalid
not_yet_qualified
qualified
```

Do not expose key prefixes, organization identifiers, project identifiers, URLs containing credentials or raw provider messages.

---

# 8. Canonical prompt architecture

Create a provider-neutral prompt registry.

Suggested structure:

```text
apps/backend/src/viraldy/modules/ai_gateway/prompts/
├── system_v2.py
├── media_observation_v2.py
├── creative_dna_v2.py
├── pattern_kit_v2.py
├── viral_kit_v2.py
├── adaptation_v2.py
├── campaign_pack_v2.py
├── decision_summary_v1.py
├── revision_message_v2.py
├── examples/
│   ├── tiktok_shop.py
│   ├── pod.py
│   └── dropshipping.py
└── registry.py
```

Do not store prompts as unversioned free strings.

Each prompt package must include:

```python
class PromptPackage(BaseModel):
    operation: AiOperationName
    prompt_name: str
    prompt_version: str
    system_prompt: str
    developer_prompt: str
    example_ids: list[str]
    output_schema_version: str
    default_reasoning_effort: str | None
    default_max_output_tokens: int | None
```

Prompt versions must be persisted in `ai_model_runs`.

Changing prompt semantics requires a new version constant.

---

# 9. Canonical Viraldy system prompt — exact required content

Implement the following policy as the canonical system prompt. Minor formatting changes are allowed, but meaning must remain exact.

```text
You are Viraldy Creative Intelligence Engine, a product-aware decision-support system for creator-commerce teams.

You analyze products, references, creator UGC, briefs and evidence for:
- TikTok Shop US sellers;
- print-on-demand and personalized products;
- dropshipping products;
- cross-border ecommerce operators and small agencies.

Your responsibility is to turn supplied evidence into structured creative intelligence and actionable next steps. You do not predict guaranteed performance.

GROUNDING
1. Use only information supplied in Product Context, creative observations, evidence items, PatternKits, seller constraints, rights data and performance records.
2. Never invent product features, price, discount, shipping time, fulfillment, compatibility, buyer facts, creator facts, timestamps, scenes, claims, disclosures, performance, rights or availability.
3. Represent unavailable information explicitly as unknown, null, unsupported or insufficient_evidence according to the output schema.
4. Every observed creative claim must reference supplied evidence IDs.
5. Keep observed facts, interpretations, hypotheses and recommendations distinct.
6. Do not infer that a creative is winning, viral, profitable or high-converting without linked performance evidence.
7. Never promise virality, orders, GMV, ROAS, conversion, profitability or policy approval.

PRODUCT PERSONALIZATION
1. When available, use the actual product name, product mechanism, buyer context, offer, market and campaign objective.
2. Recommendations must reflect the product category, price, offer, shipping, fulfillment, claims and creative constraints.
3. Product Context may guide relevance and evaluation, but it must not be used to fabricate something that was not observed in the creative.
4. Separate buyer persona from creator persona at all times.
5. Do not produce generic advice that could be pasted unchanged onto an unrelated product.

TIKTOK SHOP US
1. Evaluate early product visibility, product-in-use, demonstration, observable proof, offer, product-tag cue, CTA timing, disclosures and paid-use readiness when those fields are relevant.
2. Do not claim that a product tag exists unless evidence shows it.
3. Do not treat a generic spoken CTA as proof of a product tag.
4. Do not create shipping urgency, scarcity or platform claims that were not supplied.

PRINT-ON-DEMAND AND PERSONALIZATION
1. Preserve recipient, occasion, personalization text, spelling, variant and design details exactly.
2. Distinguish mockup imagery from a filmed physical product.
3. Flag personalization mismatch as a hard execution risk when the brief requires an exact name, breed, date, relationship or variant.
4. Never invent production or delivery promises.

DROPSHIPPING
1. Evaluate product-in-use, visible mechanism, compatibility, trust, shipping and overclaim risk.
2. Do not convert an observed use case into a universal compatibility claim.
3. Do not describe a result as proven when the video only shows the product operating without a visible outcome.
4. Prefer specific observable language over universal superlatives.

EVIDENCE AND CONFIDENCE
1. Evidence IDs, source IDs and versions must remain unchanged.
2. Timestamps must come from supplied timed evidence.
3. Confidence must reflect evidence quality, evidence coverage, source agreement and missing information.
4. Absence claims require adequate evidence coverage. Missing detection is not automatically proof of absence.
5. Hard requirements that cannot be evaluated must remain unknown rather than satisfied.

DECISIONS
1. Return an actionable decision rather than generic marketing advice.
2. Separate hard blockers, high-priority fixes and optional improvements.
3. Preserve strong observed elements while proposing changes.
4. For execution evaluation, provide expected versus observed facts.
5. Explain what should be kept, changed and avoided.
6. Recommendations must be concrete enough for a seller or creator to act on without rewriting the entire result.

COPYRIGHT AND DIFFERENTIATION
1. Extract reusable structure and mechanisms, not protected expression.
2. Do not copy exact source scripts, slogans, visual identity, creator identity or distinctive scene execution.
3. State which structural elements may be retained and which product-specific elements must change.

OUTPUT
1. Return only output matching the supplied schema.
2. Do not add undocumented keys.
3. Do not wrap JSON in Markdown.
4. Do not include hidden reasoning or chain-of-thought.
5. Provide concise evidence-based reasons in the schema's explanation fields.
6. Keep machine enums stable even when seller-facing prose is localized.
```

---

# 10. Shared operation input envelope

Every model operation must receive a typed, explicit envelope rather than an interpolated Python object representation.

Implement or adapt a contract similar to:

```python
class ViraldyOperationContextV1(BaseModel):
    operation: str
    request_id: str
    workspace_id: UUID
    actor_user_id: UUID | None
    locale: Literal["en-US", "vi-VN"]
    creator_output_locale: Literal["en-US"]

    product_context: ProductContextV1 | None
    product_context_version: int | None
    objective: str | None
    target_market: str | None

    source_artifact_ids: list[UUID]
    source_version_ids: list[UUID]
    evidence_catalog: list[EvidenceItemForModelV1]

    seller_constraints: dict[str, object]
    operation_payload: dict[str, object]

    schema_version: str
    prompt_version: str
```

Serialize with stable JSON:

- sorted keys where appropriate;
- ISO timestamps;
- enum values;
- no SQLAlchemy repr;
- no secret URLs;
- no duplicated binary content inside JSON.

Images are separate multimodal content parts and reference frame/evidence IDs included in the envelope.

---

# 11. Operation prompt: Media Observation V2

## 11.1 Purpose

Observe the supplied media without evaluating marketing quality or inventing product context.

## 11.2 Required input

```text
asset ID and immutable version ID
video duration
audio presence
transcript segments with timestamps, when available
OCR snippets with timestamps
scene boundaries
sampled frames with frame ID and timestamp
optional target product reference images
optional Product Context used only for product-match comparison
```

## 11.3 Developer prompt requirements

The prompt must require:

1. Describe only what is visible, spoken or displayed.
2. Separate direct observations from uncertain interpretations.
3. Attach evidence to every observation.
4. Do not score creative quality.
5. Do not infer buyer persona from appearance alone.
6. Do not infer protected personal traits.
7. Do not infer product claims from visual operation alone.
8. Do not say a product result occurred unless before/after or observable result evidence exists.
9. For silent videos, use visual/OCR evidence and keep spoken fields absent.
10. Detect possible:

```text
opening event
face presence
product presence
product first appearance
product-in-use
scene actions
demo steps
visible result
proof event
overlay text
offer text
CTA text
product-tag cue
required disclosure
creator delivery cues
editing cues
```

## 11.4 Output quality requirements

- all evidence IDs must exist in the supplied catalog;
- no timestamp outside video duration;
- no duplicated observation with conflicting values unless marked uncertain;
- no product match claim without target-product context;
- no generic recommendations in the observation output.

---

# 12. Operation prompt: Creative DNA V2

## 12.1 Purpose

Convert normalized observations into an evidence-grounded description of what one creative does.

Creative DNA is an observation artifact, not a winning-pattern claim.

## 12.2 Required dimensions

```text
opening
hook
product presence and reveal
demo
proof
narrative
buyer pain represented in the creative
creator delivery
editing and pacing
offer
CTA
TikTok Shop cues
claims and disclosures
risks
reusable mechanisms
uncertainties
completeness
overall confidence
```

## 12.3 Exact rules

1. Use the actual evidence fields.
2. Product Context may identify mismatch but may not overwrite observation.
3. Do not fill missing offer or CTA with expected values from the brief.
4. Preserve multiple observed hook signals when present, while selecting one primary hook only with evidence.
5. Distinguish:

```text
demo present
demo mechanism clear
result visible
proof present
proof verifiable
```

6. Distinguish spoken text, overlay text and inferred intent.
7. Product-tag presence requires explicit evidence.
8. Claims must include source, text, timing and confidence.
9. Unknown must remain unknown.
10. The seller-facing summary must mention the actual product when product context exists, but the structured observation cannot fabricate product use.

## 12.4 Friendly summary quality

The presentation layer should produce:

```text
What this creative is doing
What is clearly working structurally
What is missing or uncertain
What is reusable
What must not be copied
```

Avoid:

```text
“This video has a strong hook.”
“Add a clearer CTA.”
“Make it more engaging.”
```

Require concrete wording such as:

```text
“The video opens with the wrinkled-shirt problem, but the SwiftPress product is not visible until 4.2 seconds.”
```

---

# 13. Operation prompt: PatternKit V2

## 13.1 Purpose

Extract a reusable, evidence-backed creative mechanism from one or more Creative DNA versions.

PatternKit is not an ad template and not a promise of performance.

## 13.2 Required input

```text
selected Creative DNA versions
source evidence catalog
source categories and markets when known
optional verified performance summary
requested PatternKit scope and name
```

## 13.3 Required output semantics

PatternKit must include:

```text
name and plain-language summary
source count and source lineage
sequence beats
opening pattern
product-reveal pattern
narrative pattern
demo mechanism
proof mechanism
creator pattern
editing pattern
offer pattern
CTA pattern
applicability
contraindications
keep instructions
change instructions
avoid instructions
performance evidence status
confidence
uncertainties
provenance
```

## 13.4 Exact rules

1. Generalize structure, not exact scripts.
2. Every pattern component must reference source evidence.
3. Do not claim a pattern is “winning” when performance evidence status is `none` or insufficient.
4. If sources disagree, record a range, multiple variants or uncertainty.
5. Applicability must be product/domain-aware.
6. Include domain-specific applicability where supported:

```text
TikTok Shop product-demo suitability
POD personalization/gifting suitability
dropshipping visual-demo suitability
```

7. Include contraindications such as:

```text
product has no observable demo
result requires long-term use
proof cannot be shown safely
exact personalization is unavailable
shipping claim is unknown
```

8. `keep`, `change` and `avoid` must be actionable.
9. Never copy source creator identity, exact hook text or distinctive visual execution.
10. Performance summary is immutable unless backed by verified records.

## 13.5 User-facing PatternKit card

The frontend must render:

```text
Pattern name
One-sentence mechanism
Sequence timeline
Why it may fit
When not to use it
Keep / Change / Avoid
Evidence source count
Performance evidence status
Confidence and uncertainty
```

Do not show raw JSON as the primary view.

---

# 14. Operation prompt: ViralKit V2

## 14.1 Purpose

Compile Product Context, selected PatternKit versions, campaign objective and seller constraints into a product-specific creative experiment package.

ViralKit is a test-ready hypothesis package, not a guarantee of virality.

## 14.2 Required input

```text
immutable Product Context snapshot
selected PatternKit version snapshots
pattern-match scores and reasons
campaign objective
platform
target market
buyer persona selection
creator constraints
commercial constraints
claim governance
required disclosures
seller creative constraints
```

## 14.3 Exactly three concepts

Return exactly three concepts.

Each pair of concepts must differ across at least two meaningful axes from this list:

```text
buyer context
hook mechanism
narrative structure
creator persona
delivery style
demo mechanism
proof mechanism
emotional driver
offer framing
```

Changing only wording does not count as diversity.

## 14.4 Each concept must include

```text
concept ID
customer-friendly concept name
one-sentence idea
selected buyer persona
buyer pain
desired outcome
hook mechanism
exact hook direction, not copied source wording
opening visual
audience context
creator persona
creator delivery style
narrative progression
demo mechanism
proof mechanism
product reveal guidance
offer framing
CTA strategy
product-tag requirement
must-show elements
claims to avoid
required disclosures
creative risks
test hypothesis
primary decision criterion
pattern source links
evidence links
confidence
```

## 14.5 Domain personalization requirements

### TikTok Shop US

Use actual:

```text
product mechanism
buyer use context
offer
product-tag requirement
CTA type
shipping constraints
claim governance
```

### POD

Use actual:

```text
recipient
occasion
personalization field
variant/design detail
reveal moment
ordering instructions
production/delivery constraints
```

### Dropshipping

Use actual:

```text
observable mechanism
supported use case
compatibility boundaries
trust mechanism
shipping constraint
claim restrictions
```

## 14.6 Test matrix

Create a matrix that states:

```text
what remains fixed
what changes by concept
primary metric or seller decision signal
minimum execution requirements
main confounders
```

Do not invent performance targets.

## 14.7 Friendly concept cards

Each card must show:

```text
Concept name
Who it is for
The opening
Why it fits this product
What the creator must demonstrate
What counts as proof
What not to say
What this concept is testing
```

No card may read like a generic prompt template.

---

# 15. Operation prompt: Adaptation V2

## 15.1 Responsibility

Adaptation translates observed reusable mechanisms into product-specific concept decisions.

It must not duplicate PatternKit storage or ViralKit orchestration.

## 15.2 Required behavior

1. Receive Product Context, Creative DNA and optional PatternKit.
2. State:

```text
keep
change
avoid
```

3. Produce exactly three strategically distinct concepts when called in concept-generation mode.
4. Separate buyer persona and creator persona.
5. Keep product facts exact.
6. Preserve claim/disclosure constraints.
7. Avoid direct copying.
8. Produce a test hypothesis for each concept.
9. Mark unsupported assumptions explicitly.

ViralKit may orchestrate Adaptation, but there must be one source of truth for concept-generation semantics.

---

# 16. Operation prompt: Creative Campaign Pack V2

## 16.1 Product meaning

A Creative Campaign Pack is a creator-production brief. It is not a TikTok Ads or Meta Ads campaign object.

## 16.2 Required machine contract

Persist typed fields for:

```text
objective
product snapshot
selected ViralKit concept snapshot
target buyer
creator direction
hero angle
hook options
spoken hook directions
overlay directions
script beats
storyboard scenes
must-show requirements
product visibility timing
demo requirements
proof requirements
offer requirements
CTA requirements
product-tag requirement
allowed claims
prohibited claims
claims requiring qualification
required disclosures
shipping language
rights notes
raw footage request
revision checklist
compiled requirement snapshot
```

## 16.3 Exact generation rules

1. Do not copy the source ad script.
2. Do not convert every spoken hook into a required overlay.
3. Spoken text and overlay text are independent fields.
4. Required scenes must be testable by Preflight.
5. Every hard requirement needs:

```text
requirement class
expected value
severity
source path
rationale
```

6. Use exact required disclosure text supplied by Product Context.
7. Do not invent price, discount, delivery, stock or compatibility.
8. Preserve creator authenticity. Do not over-script every sentence.
9. Creator-facing language defaults to natural `en-US`.
10. Seller-facing explanation follows workspace locale.

## 16.4 Creator-friendly output

The primary view must include:

```text
Campaign goal
Who the video is speaking to
Core idea
Three opening options
What to film, in order
What the product must visibly do
What proof must be shown
What to say and what not to say
CTA and product-tag instruction
Disclosure
Submission checklist
```

The creator view should be concise enough to use on a phone.

Do not expose internal score weights, schema IDs or provider details in the creator view.

---

# 17. Deterministic scoring and Preflight boundary

Do not move scoring into OpenAI.

The existing hybrid rule remains:

```text
rules and typed matchers
→ structural score and exact brief alignment
→ deterministic action and blockers
→ optional OpenAI-friendly explanation
```

OpenAI may explain a score or render a revision message, but must not decide the numeric score.

Required final Preflight presentation:

```text
Decision label
Final score
Structural score
Brief-alignment score
Confidence
Strengths to preserve
Hard blockers
High-priority fixes
Optional improvements
Expected versus observed
Creator revision message
Next action
Guardrail
```

Hard requirements in `missing`, `violated` or unresolved `unknown` states must block paid-use approval according to existing rules.

---

# 18. Operation prompt: Seller Decision Summary V1

Add a bounded operation or deterministic presenter for a customer-friendly summary.

Input must be the persisted structured result, never raw media.

Output fields:

```text
headline
one_sentence_decision
why_this_matters
strengths_to_keep
blockers_to_fix
next_actions
confidence_explanation
commercial_guardrail
```

Exact rules:

1. Mention the actual product name.
2. Mention the objective when available.
3. Do not repeat every internal field.
4. Do not use hype language.
5. Do not say “viral-ready”.
6. Use “structurally ready”, “ready for organic”, “small paid test” or the exact domain action label.
7. Make the first next action executable.
8. Preserve factual blocker wording.
9. Keep seller locale separate from creator locale.

Use deterministic templates as a fallback only when the OpenAI friendly-summary call fails. This fallback is not a fixture result and must be derived solely from persisted structured fields.

---

# 19. Operation prompt: Creator Revision Message V2

## 19.1 Required tone

Friendly, professional, direct and respectful.

The message must:

1. Start with one or two specific strengths worth preserving.
2. Request the minimum set of changes needed.
3. Use concrete scene/timing language.
4. Quote exact disclosure text when required.
5. Avoid blame.
6. Avoid jargon such as rubric, blocker class, schema or confidence score.
7. Avoid vague phrases such as:

```text
make it more viral
make it catchier
make it pop
improve engagement
make the hook stronger
```

8. Preserve creator voice and current strengths.
9. End with a clear resubmission request.
10. Reference only blockers supplied to the operation.

## 19.2 Example quality

Good:

```text
The student setup feels natural, and the product-tag ending works well. Please move the product close-up into the first two seconds, return to the same shirt section after steaming so the result is clearly visible, and add the spoken or on-screen disclosure: “Results vary by fabric type.” Please keep the current tone and CTA, then upload the revised version for review.
```

Bad:

```text
The hook is weak. Make it more engaging and add a better CTA.
```

---

# 20. Localization

Support:

```text
seller-facing locale: en-US or vi-VN
creator-facing locale: en-US for the private beta
machine enums: stable English values
```

Do not translate stable IDs, enum values, evidence IDs, claim text or required disclosures unless a separately approved localized field exists.

When seller locale is Vietnamese:

- keep US creator messages in natural English;
- explain product strategy to the seller in Vietnamese;
- do not mix languages inside one field unless the field explicitly represents creator copy.

---

# 21. Presentation contracts

Do not make the frontend reconstruct meaning from arbitrary nested JSON.

Add typed presentation DTOs where necessary.

## 21.1 Creative DNA presentation

```text
summary
sequence timeline
observed strengths
missing or uncertain elements
reusable mechanisms
adaptation warnings
evidence links
```

## 21.2 PatternKit presentation

```text
name
mechanism summary
sequence beats
applicability chips
contraindications
keep/change/avoid
source count
performance evidence status
confidence
```

## 21.3 ViralKit presentation

```text
product and objective header
three concept cards
concept diversity comparison
test matrix
selected concept
risk summary
source PatternKit links
```

## 21.4 Preflight presentation

```text
decision banner
score breakdown
strengths
hard blockers
fixes
expected vs observed rows
clickable evidence timestamps
creator revision message
next-action button
```

## 21.5 Developer details

Provider, model, prompt version, schema version, IDs and raw typed payload may appear only in a collapsible developer/debug section protected from normal seller views.

---

# 22. Frontend commercial-showcase quality

Complete the current frontend flow rather than designing disconnected mock screens.

Required behavior:

1. No raw JSON as the default view.
2. Clear loading states for each async stage.
3. Show current processing stage and elapsed time.
4. Retry only the failed operation.
5. Preserve previous completed artifacts after a downstream failure.
6. Display safe provider error messages.
7. Stable URLs for Product, Creative DNA, PatternKit, ViralKit, Campaign Pack and Preflight.
8. Refresh must preserve state.
9. Empty states must teach the next action.
10. Mobile-friendly Campaign Pack and revision message.
11. Copy-to-clipboard for creator message.
12. Export Campaign Pack using the persisted structured version.
13. Evidence click seeks the video to the correct timestamp.
14. Draft 1 versus Draft 2 comparison.
15. Do not show “prediction”, “guaranteed performance” or “viral score” language where the system only measures structure.

The showcase path should feel like one connected product:

```text
Upload reference
→ see Creative DNA
→ create PatternKit
→ create ViralKit
→ choose concept
→ send Campaign Pack
→ upload UGC
→ receive actionable Preflight
```

---

# 23. Structured-output validation and repair

For every OpenAI structured operation:

1. Generate JSON Schema from the exact Pydantic output model.
2. Use strict Structured Outputs.
3. Parse into the Pydantic model.
4. Run domain validators.
5. Validate evidence IDs against the supplied evidence catalog.
6. Validate source IDs and versions.
7. Validate timestamps against asset duration.
8. Validate product facts against Product Context.
9. Validate required concept count and diversity.
10. Validate no prohibited claim is introduced.

If schema or domain validation fails:

- perform at most one repair call;
- send only a compact validation-error summary, original typed context and invalid output;
- use the same output schema;
- persist the repair attempt count;
- never repair by deleting required evidence or converting unknown into a guess;
- fail safely after the repair limit.

Normalized errors:

```text
OPENAI_NOT_CONFIGURED
OPENAI_UNAUTHORIZED
OPENAI_MODEL_NOT_AVAILABLE
OPENAI_RATE_LIMITED
OPENAI_TIMEOUT
OPENAI_REFUSED
OPENAI_INCOMPLETE
OPENAI_OUTPUT_INVALID
OPENAI_EVIDENCE_INVALID
OPENAI_DOMAIN_VALIDATION_FAILED
```

Do not expose raw OpenAI response bodies to the client.

---

# 24. Provenance and model runs

Every live call must persist:

```text
provider=openai
endpoint family=responses or audio_transcriptions
model
operation
prompt name
prompt version
schema version
input hash
request ID
provider request ID
status
attempt count
repair attempt count
latency
usage details
safe error
created/completed timestamps
```

Connect every run to the created artifact.

Do not store binary frame data in model-run summaries.

Store only safe input summaries such as:

```text
asset IDs
frame count
transcript segment count
Product Context version
source artifact IDs
```

---

# 25. Privacy and security

Required:

1. `store=false` for OpenAI responses by default.
2. API key is a secret type.
3. No API key in frontend code.
4. No complete prompt payload in ordinary logs.
5. No full model response in ordinary logs.
6. No signed media URL persistence.
7. Redact seller PII from safe error metadata.
8. Workspace isolation applies before any model request.
9. Do not send an asset to OpenAI until the user/workspace has analysis authorization metadata.
10. AI derivative generation permission remains separate from analysis permission.
11. Provide deletion documentation for locally stored model inputs/outputs.
12. Document that third-party provider retention and regional controls must be reviewed before unsupervised production use.

Add a data-flow section to the runbook:

```text
seller upload
→ Viraldy private storage
→ derived audio/frames/text
→ OpenAI request
→ typed response
→ Viraldy persistence
```

---

# 26. Cost and latency controls

Implement configurable controls:

```env
OPENAI_MAX_FRAMES_PER_VIDEO=12
OPENAI_MAX_FRAME_LONG_EDGE=1280
OPENAI_IMAGE_DETAIL=auto
OPENAI_MAX_TRANSCRIPT_CHARS=50000
OPENAI_MAX_OUTPUT_TOKENS=16000
OPENAI_REQUEST_TIMEOUT_SECONDS=180
OPENAI_MAX_RETRIES=2
OPENAI_MAX_PARALLEL_REQUESTS_PER_WORKSPACE=2
```

Requirements:

1. Select representative frames by scene and evidence coverage, not only fixed intervals.
2. Never remove frames required by exact evidence references.
3. Avoid resending identical product context across unnecessary requests.
4. Cache only exact deterministic request hashes including:

```text
operation
model
prompt version
schema version
input hash
```

5. Do not reuse a result after any source version changes.
6. Record token/usage data when available.
7. Expose safe aggregate cost-estimation fields to internal admins, not normal sellers.
8. Never fake cost when the provider does not report sufficient usage.

---

# 27. Golden commercial scenarios

The live OpenAI path must be tested against the three Golden Output domains.

## 27.1 TikTok Shop US — Mini garment steamer

Expected personalization dimensions:

```text
college student or travel buyer context
wrinkled-shirt problem
product reveal timing
same-fabric demo continuity
visible result
product-tag CTA
required fabric-result disclosure
shipping and offer accuracy
```

Expected Preflight behavior:

- late product appearance is detected;
- missing disclosure is not ignored;
- steam visibility alone is not treated as same-fabric proof;
- creator tone and valid CTA are preserved as strengths;
- revision message is friendly and concrete.

## 27.2 POD — Personalized Dog Mom crewneck

Expected personalization dimensions:

```text
recipient
occasion
pet name
breed/design variant
personalization reveal
physical product versus mockup
ordering clarity
production/delivery constraints
```

Expected hard blocker:

```text
Expected personalization: Milo
Observed personalization: Miles
→ reject or revise until the correct personalized product is filmed
```

Do not soften exact personalization mismatch into an optional improvement.

## 27.3 Dropshipping — Rechargeable mini bag sealer

Expected personalization dimensions:

```text
supported bag types
product-in-use
a visible sealed result
trust mechanism
compatibility limits
shipping language
universal airtight claim risk
```

Expected claim behavior:

```text
“makes every bag completely airtight”
→ unsupported universal claim
```

A safe replacement may describe the creator's specific supported use case, but must not invent compatibility.

---

# 28. OpenAI live qualification script

Create:

```text
apps/backend/scripts/qualify_openai.py
```

Supported commands:

```bash
uv run python scripts/qualify_openai.py --check-config
uv run python scripts/qualify_openai.py --operation media_observation
uv run python scripts/qualify_openai.py --operation pattern_kit
uv run python scripts/qualify_openai.py --operation viral_kit
uv run python scripts/qualify_openai.py --full-flow --case tiktok-shop
uv run python scripts/qualify_openai.py --full-flow --case pod
uv run python scripts/qualify_openai.py --full-flow --case dropshipping
uv run python scripts/qualify_openai.py --full-flow --all-cases --write-report
```

Requirements:

- never print the key;
- print safe model and operation information;
- create a unique qualification workspace;
- use real HTTP/API/service boundaries where practical;
- record model runs;
- validate output contracts;
- validate evidence lineage;
- write JSON and Markdown reports;
- optionally delete the qualification workspace at the end;
- exit nonzero on a failed required gate.

Report path:

```text
evaluation/reports/openai/<timestamp>/
├── qualification.json
├── qualification.md
├── outputs/
└── failures/
```

Do not commit live seller data or provider outputs containing private data.

---

# 29. Evaluation metrics and commercial showcase gates

## 29.1 Hard technical gates

Required:

```text
100% Pydantic-valid final outputs
100% valid source/version references
100% valid evidence IDs
100% timestamps inside media duration
0 silent fixture fallbacks
0 leaked API keys or signed URLs
exactly 3 ViralKit concepts
all required hard blockers enforced
```

## 29.2 Semantic gates on the Golden Dataset

Required minimum targets before calling the OpenAI path showcase-ready:

```text
hard-blocker recall >= 0.90
false hard-blocker rate <= 0.10
action-label agreement >= 0.80
critical product-fact hallucinations = 0
required-disclosure false satisfaction = 0
personalization mismatch misses = 0
generic-output rate <= 0.05
creator-message usefulness reviewer score >= 4/5
Campaign Pack usability reviewer score >= 4/5
```

Record sample size and confidence. Do not present small-sample results as universal model accuracy.

## 29.3 Generic-output detector

Add evaluation checks that flag output when:

- product name is omitted despite being supplied;
- buyer/objective is omitted despite being supplied;
- recommendations could apply unchanged to unrelated products;
- output contains vague phrases without evidence;
- all three ViralKit concepts differ only in wording;
- creator message says only “stronger hook”, “clearer CTA” or similar generic advice.

## 29.4 Friendly-output review rubric

Reviewer scores 1–5:

```text
product specificity
evidence clarity
actionability
tone
creator usability
seller decision clarity
visual scannability
```

Persist reviewer scores through the existing feedback/evaluation foundation.

---

# 30. Automated tests

Add or update tests for:

## 30.1 Provider tests

```text
Responses API request shape
system/developer/user separation
strict JSON schema inclusion
store=false
image input encoding
usage parsing
refusal handling
incomplete handling
rate-limit retry
timeout retry
401 mapping
model-unavailable mapping
one repair attempt only
no fixture fallback
secret redaction
```

Use mocked OpenAI SDK responses. CI must not require a real API key.

## 30.2 Prompt registry tests

```text
every operation has a registered prompt
prompt versions are unique and nonempty
schema version matches operation output
canonical system prompt is included
no provider code contains inline domain prompt text
```

## 30.3 Domain semantic tests

```text
no invented product facts
unknown remains unknown
buyer and creator personas remain separate
PatternKit does not claim winning without performance evidence
ViralKit has exactly three concepts
pairwise concept diversity passes
POD personalization mismatch is hard blocker
universal dropshipping claim is blocked
missing disclosure is not satisfied
spoken hook is not automatically required overlay
product tag is not inferred from generic CTA
```

## 30.4 Presentation tests

```text
seller summary mentions product and objective
creator revision message preserves strengths
creator revision message includes exact required fixes
no internal jargon in creator view
no raw provider metadata in seller view
locale separation works
```

## 30.5 E2E tests

Keep fixture and mock E2E.

Add an opt-in live test marker:

```text
pytest -m openai_live
```

It must skip cleanly when no key is provided.

Never run live API tests automatically on forks or untrusted pull requests.

---

# 31. CI

Add GitHub Actions or complete existing CI with:

```text
backend Ruff
backend full mypy
backend pytest
migration zero-to-head
frontend lint
frontend build
fixture E2E
mock-provider E2E
secret scan
prompt-registry tests
OpenAI provider contract tests with mocks
```

Do not place a real OpenAI key in ordinary CI.

An optional manually dispatched live qualification workflow may use a protected repository secret and environment approval.

The audit must distinguish:

```text
mock contract passed
live OpenAI qualification passed
```

Do not call mock success live success.

---

# 32. Migration policy

Prefer no migration when existing model-run and artifact tables support the required fields.

If new fields are necessary:

- add one clean Alembic migration;
- preserve existing rows;
- provide explicit defaults;
- verify zero-to-head and current-head upgrade;
- add migration tests;
- document downgrade limitations.

Do not store prompt bodies redundantly in every artifact row. Store prompt version and a content hash; keep canonical prompt source under version control.

---

# 33. Documentation

Create or update:

```text
docs/runbooks/OPENAI_PROVIDER.md
docs/runbooks/AI_PROMPTS_AND_VERSIONING.md
docs/runbooks/OPENAI_LIVE_QUALIFICATION.md
apps/backend/README.md
.env.openai.example
```

The OpenAI runbook must include:

1. Create/copy environment file.
2. Fill `OPENAI_API_KEY`.
3. Start infrastructure.
4. Run migrations.
5. Start API, worker and beat.
6. Run `--check-config`.
7. Run one operation.
8. Run the full Golden flow.
9. Inspect model runs and evaluation report.
10. Common errors and fixes.
11. How to override models.
12. How to return to fixture/mock.
13. Data/privacy notes.
14. How the same canonical prompts will later be used with Dola/Seed.

Do not document an unverified model as guaranteed available to every account. Explain the model override path.

---

# 34. Implementation milestones

## Milestone O1 — Baseline and architecture audit

Deliver:

- current provider call map;
- current inline prompt inventory;
- current operation/schema map;
- compatibility plan;
- no-code audit commit.

## Milestone O2 — Native OpenAI provider

Deliver:

- official SDK dependency;
- Responses API structured generation;
- audio transcription;
- provider router;
- safe errors;
- usage/provenance;
- mocked tests.

## Milestone O3 — Canonical prompts

Deliver:

- system prompt V2;
- operation prompts;
- registry;
- prompt metadata;
- examples;
- prompt tests.

## Milestone O4 — Domain quality integration

Deliver:

- evidence validation;
- product-fact validation;
- concept diversity validation;
- structured repair;
- generic-output detector;
- domain semantic tests.

## Milestone O5 — Friendly presentation and frontend

Deliver:

- presentation DTOs;
- seller summaries;
- creator messages;
- PatternKit/ViralKit cards;
- Preflight decision view;
- draft comparison;
- frontend tests/build.

## Milestone O6 — Qualification and evaluation

Deliver:

- live qualification script;
- Golden case runner;
- JSON/Markdown reports;
- opt-in live test marker;
- runbook.

## Milestone O7 — Release gate

Deliver:

- full tests;
- CI;
- fixture/mock regression;
- live OpenAI qualification evidence when a real key is available;
- audit;
- PR;
- release tag.

---

# 35. Full acceptance flow

The feature is complete only when this sequence works through real application boundaries:

```text
1. Authenticate
2. Create workspace
3. Create fully populated Product Context
4. Upload reference video
5. Process audio, frames, OCR and scenes
6. Run OpenAI media observation
7. Create Creative DNA
8. Create PatternKit
9. Create ViralKit
10. Verify exactly three distinct concepts
11. Select one concept
12. Generate Creative Campaign Pack
13. Export or view creator brief
14. Upload UGC draft
15. Run deterministic TikTok score
16. Run exact Campaign Pack Preflight
17. Generate friendly seller decision summary
18. Generate friendly creator revision message
19. Record recommendation action
20. Upload revised UGC version
21. Compare Draft 1 and Draft 2
22. Rerun Preflight
23. Record feedback and events
24. Query model-run provenance
25. Delete qualification workspace and verify storage cleanup
```

The flow must pass in:

```text
fixture
mock
openai live
```

Live is required for the final commercial-showcase claim, but it may be documented as pending when no real key is available. Do not fabricate live evidence.

---

# 36. Definition of Done

All applicable boxes must be checked truthfully:

```text
[ ] Native OpenAI provider uses the official SDK
[ ] Responses API is used for structured text/vision operations
[ ] Strict JSON Schema output is enforced
[ ] Audio transcription supports timed segments
[ ] Only OPENAI_API_KEY must be filled in the OpenAI example config
[ ] Safe model defaults exist and are overridable
[ ] Canonical system prompt is versioned
[ ] Every operation prompt is versioned and registered
[ ] No business service contains large inline prompt text
[ ] Product facts cannot be fabricated silently
[ ] Evidence IDs and timestamps are validated
[ ] PatternKit remains evidence-backed and non-predictive
[ ] ViralKit returns exactly three meaningfully distinct concepts
[ ] Campaign Pack is product-specific and creator-friendly
[ ] Spoken and overlay requirements remain separate
[ ] Numeric scoring remains deterministic
[ ] Preflight enforces exact hard requirements
[ ] Seller summary is friendly and product-specific
[ ] Creator revision message is respectful and actionable
[ ] POD personalization mismatch is handled correctly
[ ] Dropshipping universal claims are handled correctly
[ ] TikTok Shop product-tag and disclosure rules are handled correctly
[ ] OpenAI refusal/incomplete/error states fail safely
[ ] At most one schema-repair attempt is allowed
[ ] Live mode never falls back to fixture/mock
[ ] Provider/model/prompt/schema/usage provenance is persisted
[ ] No API key, signed URL or private payload leaks into logs
[ ] Frontend presents structured commercial-quality views
[ ] Golden Dataset semantic gates pass
[ ] Fixture E2E passes
[ ] Mock-provider E2E passes
[ ] OpenAI live qualification passes, or is explicitly marked pending due to missing key
[ ] CI passes
[ ] Documentation is complete
[ ] Release audit is complete
```

---

# 37. Final deliverables

Provide:

1. Branch name.
2. Final commit SHA.
3. PR URL.
4. Release tag.
5. Changed files grouped by milestone.
6. Prompt registry table.
7. Operation-to-model routing table.
8. Environment-variable table.
9. Exact test commands and results.
10. CI links/status.
11. Fixture/mock E2E evidence.
12. Live OpenAI qualification evidence, if executed.
13. Golden evaluation metrics.
14. Screenshots or screen-recording checklist for the showcase flow.
15. Known limitations.
16. Cost/latency observations without unsupported claims.
17. Data/privacy notes.
18. Dola/Seed migration notes.
19. Final audit file:

```text
VIRALDY_OPENAI_PRODUCTION_INTELLIGENCE_AUDIT.md
```

The final audit must distinguish among:

```text
implemented
mock-verified
live-qualified
seller-validated
```

Do not combine these into one unsupported “production-ready” claim.

---

# 38. Permissible completion statement

Use this statement only when source code, tests, CI and live qualification support it:

> Viraldy’s OpenAI intelligence path is implemented and live-qualified for supervised commercial demos and private-beta pilots. Outputs are schema-valid, product-grounded, evidence-linked and rendered as seller- and creator-friendly decisions. This does not constitute a guarantee of virality, GMV, ROAS or unsupervised production accuracy.

If live qualification has not been run, use:

> Viraldy’s OpenAI intelligence path is implemented and mock-verified. Live qualification requires a valid OpenAI API key and must be completed before customer demonstrations using real model output.

---

# 39. Final instruction to Codex

Do not stop after creating prompt constants or an OpenAI client.

Complete the connected product behavior:

```text
provider
+ canonical prompts
+ strict contracts
+ evidence validation
+ friendly presentation
+ frontend workflow
+ evaluation
+ live qualification
+ audit
```

Use `VIRALDY_GOLDEN_OUTPUT_REFERENCE_AND_ACCEPTANCE_EXAMPLES.md` as the authoritative semantic example set.

Do not replace product-specific outputs with generic AI copy.

Do not claim success without exact test evidence.
