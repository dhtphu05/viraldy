# OpenAI Production Intelligence Baseline

Date: 2026-07-31
Branch: `release/openai-production-intelligence-showcase`
Code baseline: `origin/main@2f2e818`
Frontend preservation commit: `953f2d8`

## Purpose

This is the Milestone O1 evidence record for
`VIRALDY_OPENAI_NATIVE_PRODUCTION_INTELLIGENCE_SHOWCASE_GOAL.md`.

The semantic authority for this implementation is
`VIRALDY_GOLDEN_OUTPUT_REFERENCE_AND_ACCEPTANCE_EXAMPLES_V0_9.md`, as explicitly
confirmed by the project owner. Existing Pydantic domain contracts remain the
code-level source of truth.

No live OpenAI request was made during this audit. `OPENAI_API_KEY` is configured
in `apps/backend/.env`, but the current settings object reads `AI_API_KEY`; the
existing provider path therefore does not consume the configured OpenAI key.
The key value was not read, printed, logged, or committed.

## Verified Baseline

| Gate | Result |
| --- | --- |
| Backend Ruff | Pass |
| Backend mypy strict | Pass across 226 source files |
| Backend pytest | 167 passed |
| Backend coverage | 75.76%, configured minimum 70% |
| Frontend lint | Pass with 9 existing Fast Refresh warnings |
| Frontend production build | Pass |
| Frontend browser QA | Pass at desktop and 390x844 mobile widths |
| Live OpenAI qualification | Not run |

## Current Provider Call Map

| Domain path | Current provider behavior | Main entry points |
| --- | --- | --- |
| Media ASR | Direct OpenAI-compatible HTTP multipart request to `/audio/transcriptions`; returns timed segments when configured | `modules/media_analysis/provider.py`, `modules/ai_gateway/http_client.py` |
| Media OCR and visual observation | Direct OpenAI-compatible Chat Completions request with inline prompts and frame data URLs | `modules/media_analysis/provider.py` |
| Creative DNA | Deterministic construction from persisted evidence; no dedicated native provider call | `modules/creative_dna/service.py`, `worker/tasks/process_asset.py` |
| PatternKit | Fixture builder or direct OpenAI-compatible Chat Completions request with an inline user prompt | `modules/pattern_kits/provider.py`, `modules/pattern_kits/service.py` |
| ViralKit | Fixture builder or direct OpenAI-compatible Chat Completions request with an inline user prompt | `modules/viral_kits/provider.py`, `modules/viral_kits/service.py` |
| Adaptation | Fixture builder or direct OpenAI-compatible Chat Completions request with an inline user prompt | `modules/adaptations/provider.py`, `modules/adaptations/service.py` |
| Campaign Pack | Deterministically compiled from an adaptation concept; no Campaign Pack model call | `modules/campaign_packs/service.py`, `modules/campaign_packs/requirements.py` |
| TikTok score | Deterministic rubric and evidence matching | `modules/tiktok_scorer/scorer.py` |
| Campaign Pack Preflight | Deterministic exact requirement matching and action selection | `modules/preflight/matchers.py`, `modules/preflight/service.py` |
| Seller recommendation | Deterministic recommendation created from score/preflight | `modules/recommendations/service.py` |
| Creator revision message | Deterministic string assembly inside Preflight; no registered model call | `modules/preflight/service.py` |
| Storyboard/video preview generation | Provider-neutral fixture or custom HTTP `/media/generations`; explicitly outside native OpenAI text intelligence | `modules/generation/provider.py` |

Business services select concrete live providers directly. Provider selection is
not centralized, and `AI_PROVIDER` is not routed through a typed provider
factory.

Media analysis and generation use durable worker jobs. PatternKit, ViralKit, and
adaptation currently make synchronous provider calls from request services with
`processing_job_id=None`; those services also discard HTTP status, provider
request ID, latency, and usage when completing their model-run records.

## Current Prompt Inventory

`modules/ai_gateway/prompts.py` contains names and V1 version constants only.
The semantic prompt bodies are inline in:

- `modules/media_analysis/provider.py` for OCR and media observation;
- `modules/pattern_kits/provider.py` for PatternKit extraction;
- `modules/viral_kits/provider.py` for ViralKit composition;
- `modules/adaptations/provider.py` for adaptation generation.

There is no canonical Viraldy system prompt, no typed `PromptPackage`, no
operation registry that contains prompt text and examples, and no versioned
prompt package for seller summaries or revision messages.

## Current Operation And Schema Map

| Operation | Registered input/output | Prompt | Schema |
| --- | --- | --- | --- |
| `media_observation` | Asset IDs to created artifact/evidence IDs | `media_observation_v1` | `media_observation_v1` |
| `creative_dna_build` | Evidence IDs to Creative DNA version ID | `creative_dna_extraction_v1` | `creative_dna_v1` |
| `pattern_kit_extract` | Creative DNA version IDs to PatternKit/version IDs | `pattern_kit_extraction_v1` | `pattern_kit_v1` |
| `viral_kit_compose` | Product/pattern versions to ViralKit/version and three concept IDs | `viral_kit_composer_v1` | `viral_kit_v1` |
| `adaptation_generate` | Product/Creative DNA versions to adaptation run ID | `adaptation_generation_v1` | `adaptation_v2` |
| `campaign_pack_generate` | ViralKit concept to Campaign Pack/version IDs | `campaign_pack_generation_v1` | `campaign_pack_brief_v1` |
| `revision_message_generate` | Preflight blockers to message and referenced codes | `revision_message_v1` | `revision_message_v1` |
| `storyboard_image_generate` | Generation brief to artifact IDs | `storyboard_image_generation_v1` | `storyboard_image_v1` |
| `concept_video_preview_generate` | Generation brief to artifact IDs | `concept_video_preview_generation_v1` | `concept_video_preview_v1` |

The operation registry is useful for routing metadata, but its output contracts
describe persisted IDs rather than the exact structured model response for
several domain operations. Native structured generation must use each existing
domain Pydantic output model, then let the service persist the validated result.

## Current Persistence And Provenance

`ai_model_runs` already stores:

- workspace, job, subject, capability, and operation;
- mode, provider, model, prompt version, and schema versions;
- request and input hashes;
- safe input/output summaries;
- attempt count, latency, HTTP status, provider request ID;
- usage JSON, optional estimated cost, safe error, and timestamps.

The table does not have first-class fields for:

- prompt name;
- endpoint family (`responses` or `audio_transcriptions`);
- repair attempt count.

Artifact lineage exists in adaptation, PatternKit, ViralKit, Campaign Pack, media
evidence, and feedback modules. A single additive migration is justified for the
three missing model-run fields; raw prompts, full responses, frames, signed URLs,
and secrets must remain outside model-run summaries.

## Existing Strengths To Preserve

- Modular-monolith ownership and workspace-scoped repositories.
- Strict Pydantic domain contracts with `extra="forbid"` in critical outputs.
- Immutable Product Context and artifact version snapshots.
- Evidence IDs and timed media artifacts.
- Deterministic TikTok scoring and exact Campaign Pack Preflight.
- Three-concept and diversity validation in adaptation/ViralKit contracts.
- Product-governance, disclosure, and prohibited-claim structures.
- Durable processing jobs and existing model-run records.
- Fixture and mock full-flow smoke runners with isolated workspace cleanup.
- Deterministic PatternKit/ViralKit evaluation and JSON/Markdown reporting.

The OpenAI adapter must not replace deterministic scoring, exact matching,
workspace authorization, or persisted typed artifacts.

## Gaps Against The Showcase Goal

1. There is no official OpenAI Python SDK dependency or native Responses API adapter.
2. `OPENAI_API_KEY` and documented OpenAI defaults are not represented in settings.
3. Live business paths call the compatible client directly and use Chat Completions.
4. Prompt bodies are inline and there is no canonical V2 system prompt registry.
5. Strict schema support is optional and can fall back to legacy JSON mode.
6. Refusal, incomplete, cancelled, and model-unavailable states are not normalized.
7. Retry behavior lacks exponential jitter and central policy.
8. Usage and provider metadata are discarded by several service paths.
9. There is no bounded structured-output repair path.
10. Evidence, timestamp, product-fact, prohibited-claim, and generic-output validation are not centralized for model outputs.
11. Campaign Pack and creator revision operations have no native model integration.
12. Seller/creator presentation DTOs and connected frontend API state are incomplete.
13. Golden V0.9 does not yet exist as executable three-domain qualification fixtures.
14. There is no `qualify_openai.py`, live report format, or `openai_live` marker.
15. Current health output reports only a binary configuration check, not qualification state.
16. There is no keyless provider-contract CI workflow or frontend E2E suite.
17. The connected `/mvp` route skips PatternKit and ViralKit and moves from Creative DNA directly to the legacy adaptation path.
18. Creative Library, campaign authoring, UGC review, dashboard, products, and performance remain seeded Zustand demo surfaces rather than backend-backed showcase screens.
19. The main UGC review screen and connected `/mvp` Preflight use different data sources and revision-message implementations.

## Compatibility Plan

1. Add an official-SDK `OpenAINativeProvider` behind a provider-neutral protocol.
2. Keep `OpenAICompatibleClient` for mock and future compatible providers.
3. Route by explicit `AI_MODE` and `AI_PROVIDER`; never infer from base URLs.
4. Add `OPENAI_*` settings with safe defaults and operation-specific model resolution.
5. Preserve current `AI_*` settings only for the compatible provider during migration.
6. Move domain prompt text into immutable, versioned prompt packages.
7. Use exact domain Pydantic models for strict Responses API parsing.
8. Run domain and lineage validators before persistence, with at most one repair.
9. Extend `ai_model_runs` additively for prompt name, endpoint family, and repair count.
10. Keep scoring and Preflight matching deterministic; use the model for typed observation, composition, and friendly presentation.
11. Add presentation endpoints without replacing canonical persisted payloads.
12. Turn Golden V0.9 scenarios into deterministic fixtures and code-based semantic gates.
13. Keep CI keyless; isolate real API calls behind an opt-in marker and qualification script.
14. Run fixture, mock, and then real-key live qualification as separate evidence classes.
15. Extend the existing connected `/mvp` query and polling path through PatternKit and ViralKit before replacing seeded product routes.
16. Keep demo-only Zustand routes isolated until each can move to the same envelope-aware backend client without mixed sources of truth.

## Release Evidence Policy

The implementation may be described as:

- `implemented` only when the code path and contracts exist;
- `mock-verified` only after deterministic and mocked-provider gates pass;
- `live-qualified` only after a real-key run writes passing qualification reports;
- `seller-validated` only after documented human seller review.

At this baseline, only the existing private-beta fixture/mock foundation is
verified. The new native OpenAI showcase path is not yet implemented or
live-qualified.
