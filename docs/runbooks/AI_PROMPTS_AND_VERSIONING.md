# AI Prompts And Versioning

Viraldy prompts are provider-neutral application assets. OpenAI, a future
Dola/Seed adapter, and deterministic evaluation must consume the same domain
policy and typed contracts; providers may translate transport, not rewrite the
intelligence rules.

## Source Of Truth

The current prompt system lives under:

```text
apps/backend/src/viraldy/modules/ai_gateway/
|- prompt_content/
|  |- system_v2.py
|  |- media_observation_v2.py
|  |- creative_dna_v2.py
|  |- pattern_kit_v2.py
|  |- viral_kit_v2.py
|  |- adaptation_v2.py
|  |- campaign_pack_v2.py
|  |- decision_summary_v1.py
|  |- revision_message_v2.py
|  |- storyboard_image_v1.py
|  |- concept_video_preview_v1.py
|  `- examples.py
|- prompt_packages.py
|- operations.py
|- context.py
`- execution.py
```

`prompt_packages.py` is the runtime registry. `prompts.py` is a compatibility
export surface, not a second registry. Schema constants are in
`creative_domain/schema_versions.py`.

The canonical system prompt is:

| Name | Version |
|---|---|
| `viraldy_creative_intelligence_system` | `viraldy_creative_intelligence_system_v2` |

Every registered package currently embeds the exact same system prompt. It
enforces evidence grounding, product personalization, TikTok Shop US/POD/
dropshipping constraints, uncertainty, non-predictive decisions, copyright
differentiation, and strict schema-only output.

## Registered Packages

The registry rejects duplicate operations or duplicate prompt versions at
import time. Packages are frozen Pydantic models.

| Operation | Prompt name | Prompt version | Output schema | Reasoning | Output tokens |
|---|---|---|---|---:|---:|
| `media_observation` | `media_observation` | `media_observation_v2` | `media_observation_v1` | medium | 6,000 |
| `creative_dna_build` | `creative_dna_extraction` | `creative_dna_extraction_v2` | `creative_dna_v1` | medium | 6,000 |
| `pattern_kit_extract` | `pattern_kit_extraction` | `pattern_kit_extraction_v2` | `pattern_kit_v1` | medium | 7,000 |
| `viral_kit_compose` | `viral_kit_composer` | `viral_kit_composer_v2` | `viral_kit_v1` | high | 10,000 |
| `adaptation_generate` | `adaptation_generation` | `adaptation_generation_v2` | `adaptation_v2` | high | 8,000 |
| `campaign_pack_generate` | `campaign_pack_generation` | `campaign_pack_generation_v2` | `campaign_pack_brief_v1` | medium | 10,000 |
| `seller_decision_summary` | `seller_decision_summary` | `seller_decision_summary_v1` | `seller_decision_summary_v1` | low | 2,000 |
| `revision_message_generate` | `revision_message` | `revision_message_v2` | `creator_revision_message_v2` | low | 2,000 |
| `storyboard_image_generate` | `storyboard_image_generation` | `storyboard_image_generation_v1` | `storyboard_image_v1` | provider-specific | provider-specific |
| `concept_video_preview_generate` | `concept_video_preview_generation` | `concept_video_preview_generation_v1` | `concept_video_preview_v1` | provider-specific | provider-specific |

Only the first eight operations are in the current OpenAI qualification
catalog. Storyboard/image and video preview use the separate generation
provider, are disabled by default, and must not be represented as native OpenAI
qualified.

Every package references these Golden examples by ID rather than embedding the
full examples:

```text
golden-v0.9:tiktok-shop-us:swiftpress-mini-garment-steamer
golden-v0.9:pod-us:personalized-dog-mom-crewneck
golden-v0.9:dropshipping-us:rechargeable-mini-bag-sealer
```

## Runtime Contract

Each `PromptPackage` contains:

```text
operation
prompt_name
prompt_version
system_prompt
developer_prompt
example_ids
output_schema_version
default_reasoning_effort
default_max_output_tokens
```

`execute_structured_operation` enforces the following boundary:

1. `ViraldyOperationContextV1.prompt_version` must equal the registered package.
2. `schema_version` must equal the package output schema.
3. Native execution requires `AI_MODE=live` and `AI_PROVIDER=openai`.
4. User context is stable JSON with sorted keys; signed URLs, secret-shaped
   fields, and binary data URLs are rejected.
5. Images are separate typed content parts.
6. The selected model comes from operation override then family fallback.
7. The exact Pydantic class is supplied as the strict response format.
8. Output passes Pydantic and optional domain/evidence validation.
9. At most one bounded repair attempt is allowed.

Operation package reasoning/token defaults currently take precedence over
`OPENAI_REASONING_EFFORT` and `OPENAI_MAX_OUTPUT_TOKENS`. Those environment
values are fallbacks, not universal overrides.

The live qualification semantic projection is separate from the operation
registry:

```text
prompt version: openai_semantic_qualification_v2
schema version: golden_semantic_output_v1
```

It exists only to project actual qualification outputs into the Golden
evaluation contract. It must not be treated as a production artifact prompt.

## Persistence And Reproduction

Application model runs persist:

```text
provider and endpoint family
model and operation
prompt name and prompt version
response/schema version
input and request hashes
request and provider request IDs
attempt and repair counts
status, latency, usage, and safe error
bounded input/output summaries
```

Domain artifacts also retain relevant source model-run and prompt/schema
references where their contracts expose them.

Current limitation: the database does not have a dedicated prompt-content hash
column, and request/input hashes are derived from operation input summaries or
stable context, not from the prompt body. Therefore `prompt_version` plus the
deployed Git SHA is the current prompt-body attestation. Do not claim that a
model-run row alone proves the exact prompt bytes. A future content-hash field
must be added with a migration and backfill policy rather than overloading the
input hash.

## Change Policy

Any semantic change requires a new prompt version, including changed grounding,
evidence, claim, decision, tone, localization, or output instructions. Whitespace
or comment-only source changes may keep the version only when rendered prompt
bytes and meaning are unchanged.

Use this sequence:

1. Identify the affected operation and output contract.
2. Add a new versioned prompt-content module; do not overwrite deployed
   semantics while keeping the old version string.
3. Bump the operation prompt-version constant.
4. Bump the canonical system version when the shared policy changes, and
   explicitly version every affected package.
5. Change the output schema version only when the typed response contract
   changes; preserve API/database compatibility or add a migration.
6. Update Golden fixtures/rubrics only when product semantics intentionally
   change, never to hide a model regression.
7. Run registry, execution, provider, and Golden semantic checks.
8. Run fixture/mock application smoke, then opt-in live contract and
   application qualification.
9. Record Git SHA, model routes, report path, and qualification state in the
   release evidence.

There is no environment variable that selects an older prompt version. Rollback
requires deploying code whose registry contains the previous package and
compatible schema. Model override is not prompt rollback.

## Verification Commands

From `apps/backend`:

```bash
uv run pytest \
  tests/unit/test_prompt_registry.py \
  tests/unit/test_ai_execution.py \
  tests/unit/test_ai_operation_context.py \
  --no-cov

uv run python scripts/qualify_openai.py --check-config
```

The tests verify registry completeness/immutability, unique nonempty versions,
canonical policy clauses, schema compatibility, Golden example IDs, stable
context serialization, and rejection of unregistered versions. The config
command prints safe operation/model/prompt/schema metadata and never the key; it
does not call OpenAI.

For release confidence, also run the full backend suite because model-run
persistence and domain validators live outside the prompt registry:

```bash
uv run pytest
```

## Dola/Seed Reuse

Dola/Seed migration must reuse:

- canonical system and operation prompt packages;
- `ViraldyOperationContextV1`;
- output Pydantic contracts and evidence validators;
- prompt/schema/model-run provenance;
- deterministic scoring and Preflight boundaries.

The provider adapter may translate roles, multimodal parts, structured-output
syntax, timestamps, usage, errors, and request IDs. It may not create a
Dola/Seed-specific domain prompt fork. If a provider cannot satisfy a required
capability, mark that operation unsupported and keep it unqualified.

`openai_compatible` currently targets OpenAI-style chat completions and
transcriptions. It is a compatibility starting point, not proof of BytePlus,
Dola, Seedream, or Seedance compatibility. Provider-specific contract tests,
real-key qualification, persisted application runs, and workspace cleanup are
required before changing that label.
