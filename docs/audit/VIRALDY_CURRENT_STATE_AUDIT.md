# Viraldy Smart Remake — current-state technical audit

Audit date: **2026-11-24, Asia/Ho_Chi_Minh**. Repository: `/Users/mac/Desktop/Viraldy`. HEAD: `b68d34dc60c076a33ef3f9718b89e60d64047f39`.

## Executive assessment

Smart Remake has an implemented analysis → deterministic prompt compilation → provider generation → media assembly path. It also has a substantial **uncommitted scene-repair extension** with private scene retention, candidate versions, explicit candidate acceptance, revision checks, rollback through historical scene selection, and technical re-verification. This is a credible base for a complete seller workflow; it is not evidence that product replacement, motion preservation, or advertising quality is reliably achieved on real provider outputs.

The current Unifically execution uploads the **target product image**, supplies text derived from the reference analysis/shot plan, and requests a new eight-second clip. It does not submit the original video, original frames, or the previous generated clip to the video model. FlowKit requests image generation followed by video generation through its own project/scene API; its downstream model identity is not specified in these requests. The phrase “remake” therefore describes the intended result, not a demonstrated video-to-video editing operation. Source audio can separately be extracted and mixed into the final assembly. Evidence: `_render_with_unifically` at [render_orchestrator.py:367](../../apps/backend/src/viraldy/modules/smart_remake/engine/render_orchestrator.py#L367), `build_unifically_video_input` at [unifically_adapter.py:788](../../apps/backend/src/viraldy/modules/smart_remake/engine/unifically_adapter.py#L788), `_render_with_flowkit` at [render_orchestrator.py:225](../../apps/backend/src/viraldy/modules/smart_remake/engine/render_orchestrator.py#L225), music handling at [render_orchestrator.py:501](../../apps/backend/src/viraldy/modules/smart_remake/engine/render_orchestrator.py#L501).

The immediate priority is to finish and qualify the existing scene-repair vertical slice, make the render lifecycle recoverable and private, and establish reproducible evidence. Expanding into ten separate V2 modules before these foundations are verified would increase the number of unproven paths.

## Evidence scope and interpretation

- The audit inspects the **working tree**, including pre-existing modified and untracked files. At entry, `git status --short` had 52 entries: 22 modified tracked files and 30 untracked entries, one of which represented the new component directory. HEAD alone cannot reproduce this snapshot.
- Significant working-tree additions include migration `0023_smart_remake_scene_repair.py`, repair models/repository/service/media/schema files, prompt edits, the studio hook/components, and their tests. Their presence does not establish that migration 0023 has been applied or that this code is deployed.
- GitNexus indexed commit `f0635d56a9264a515272be5d0d3effd5e82af6bc` and reported **10 commits behind HEAD**. Graph queries/context were used for navigation; every material conclusion was checked against current source. No index rebuild was performed because this task permits documentation creation only.
- Existing design documents and the request's description of a previous report are leads, not proof. No original B0/B1/B2 results bundle was supplied with the request, and no matching reproducible Smart Remake experiment package was located in the inspected repository/local artifact surfaces.
- No production code or tests were edited, dependencies installed, paid generation initiated, migrations applied, or external resources changed. Real environment secret values and private infrastructure addresses are excluded from the reports.
- Narrow offline tests and an in-memory mocked defect reproduction were run. Deployment health, live provider availability, database migration state, production storage policies, and provider retention were not tested.

### Concurrent source changes during final verification

The workspace continued changing outside this audit. Hash comparison against the entry snapshot detected later edits to `smart-remake-render.ts`, its test, the shared Smart Remake API client/test, and the existing scene-repair implementation plan, plus a new `get_kie_api_key` configuration helper and `test_smart_remake_kie.py`. At the **2026-11-24 23:32:52 +07:00 observation**, the frontend had a `kieConfigured` preference and `provider="kie"` types, while the inspected backend service still allowed only fixture/Unifically/FlowKit and the Kie engine files imported by the new test were not yet present. This is unfinished integration evidence, not a verified fourth generation path. Later adapter work is outside that observed boundary; the [provider report](MODEL_PROVIDER_CAPABILITY_AUDIT.md) records this late delta separately.

The architecture/pipeline conclusions and 51-test run refer to the source actually inspected, with this late delta explicitly separated. Source links give exact locations from that inspection and may shift as concurrent work proceeds. These reports are not a frozen copy of the uncommitted source. The audit did not author or revert any of the concurrent source changes, and the new Kie tests were not included in the 51-test result. A reviewed commit or exported source snapshot is required to make the entire audit baseline reproducible.

Status terminology used throughout:

| Status | Meaning |
| --- | --- |
| Implemented runtime path | Source is connected to the application's normal execution path; this does not mean a production deployment or live quality was verified. |
| WIP implementation | Connected source exists in the pre-existing uncommitted working tree; integration/deployment remains unverified. |
| Partial | A useful subset exists, but the requested capability is incomplete. |
| Fixture/mock | Deterministic, simulated, or demonstration behavior; not a new provider-generated result. |
| Planned / not located | A proposal exists, or no executable implementation was found in the inspected scope. Absence is scoped, not proof about external systems. |
| Unknown | Required runtime state or underlying evidence was unavailable. |

## Deliverable map

| Request | Primary report |
| --- | --- |
| 1: repository, frontend/backend/queue/database/storage architecture | [Current architecture](VIRALDY_ARCHITECTURE_CURRENT.md) |
| 2: complete pipeline trace | [Smart Remake pipeline](SMART_REMAKE_PIPELINE_TRACE.md) |
| 3: exact provider requests and supported execution modes | [Model/provider audit](MODEL_PROVIDER_CAPABILITY_AUDIT.md) |
| 4: ProductLock, ReferenceAnalysis, MediaFacts, SceneMap, constraints | [Pipeline, contracts and constraints](SMART_REMAKE_PIPELINE_TRACE.md) |
| 5: output verification and Inspector integration | [Pipeline and verification](SMART_REMAKE_PIPELINE_TRACE.md) |
| 6: editing, selective repair, versions and assembly | [Pipeline and repair](SMART_REMAKE_PIPELINE_TRACE.md), [current UI](VIRALDY_ARCHITECTURE_CURRENT.md) |
| 7: B0/B1/B2, ablations, raw evidence and reproducibility | [Experiment evidence](EXPERIMENT_EVIDENCE_AUDIT.md) |
| 8: security, rights, consent, disclosure and release | [Security and rights](SECURITY_RIGHTS_AUDIT.md) |
| 9: product/frontend and cohesive workflow | [Architecture and UI](VIRALDY_ARCHITECTURE_CURRENT.md), [V2 priorities](VIRALDY_V2_GAP_ANALYSIS.md) |
| 10: prioritized gaps, dependencies and acceptance criteria | [V2 gap matrix](VIRALDY_V2_GAP_ANALYSIS.md) |

## What is implemented

### Analysis and compilation

The public API accepts a reference video and a product image or resolved product URL. Public compile supports eight or sixteen seconds and vertical 9:16. Internally, request/schema/render code also describes 24/32 seconds; those are not public compile options. The engine validates input media, calls Gemini to analyze the reference and target product separately, enriches shot boundaries with FFmpeg, normalizes timelines into eight-second render units, compiles scene prompts, and attaches local source-frame metadata. See `compile_request` at [service.py:87](../../apps/backend/src/viraldy/modules/smart_remake/service.py#L87), `_duration` at [service.py:75](../../apps/backend/src/viraldy/modules/smart_remake/service.py#L75), `compile_smart_remake` at [compile_service.py:72](../../apps/backend/src/viraldy/modules/smart_remake/engine/compile_service.py#L72), and `SceneMap` at [schemas.py:364](../../apps/backend/src/viraldy/modules/smart_remake/engine/schemas.py#L364).

ProductLock represents identity, usage, preserve/change/forbid text, and a product reference. ReferenceAnalysis represents source shots, motion beats, opening composition, subject presence, audio and creative structure. These are useful V2 inputs. They are mostly dictionaries in the active pipeline: the existence of Pydantic classes does not establish exhaustive validation of these nested runtime artifacts. No standalone `MediaFacts` contract was located; current media facts are the dictionary returned by FFprobe. See [schemas.py:111](../../apps/backend/src/viraldy/modules/smart_remake/engine/schemas.py#L111), [schemas.py:290](../../apps/backend/src/viraldy/modules/smart_remake/engine/schemas.py#L290), and `probe_media_file` at [media_probe.py:10](../../apps/backend/src/viraldy/modules/smart_remake/engine/media_probe.py#L10).

### Generation and media processing

Unifically and FlowKit clients, polling, selected retry behavior, FFmpeg concat, audio muxing and final storage are implemented. Reference-video request keys and banned generation request types are guarded. This is request-shape protection, not semantic proof that output follows the source. Source-frame extraction does not imply those frames reach the active generation request. See [guards.py:54](../../apps/backend/src/viraldy/modules/smart_remake/engine/guards.py#L54), [render_orchestrator.py:143](../../apps/backend/src/viraldy/modules/smart_remake/engine/render_orchestrator.py#L143), and the [provider capability matrix](MODEL_PROVIDER_CAPABILITY_AUDIT.md).

### Controlled repair, in the working tree

Non-fixture render now preflights private S3 storage, creates a workspace project/context snapshot, and captures scenes and the final video. Repair creates a new candidate for one eight-second render unit. Accept checks revision/parent/technical status, preserves the other selected scenes, checks stored scene hashes, reassembles, technically checks the assembly, and advances revision. Historical scene versions can be selected again. This is **scene history**, not an immutable history of every final video assembly. Evidence: [router.py:99](../../apps/backend/src/viraldy/modules/smart_remake/router.py#L99), `begin_render` at [repair_service.py:268](../../apps/backend/src/viraldy/modules/smart_remake/repair_service.py#L268), `repair` at [repair_service.py:403](../../apps/backend/src/viraldy/modules/smart_remake/repair_service.py#L403), `_compose` at [repair_service.py:584](../../apps/backend/src/viraldy/modules/smart_remake/repair_service.py#L584), and `accept` at [repair_service.py:641](../../apps/backend/src/viraldy/modules/smart_remake/repair_service.py#L641).

Repair uses new generation conditioned on the stored product and edited prompt; it does not edit the previous scene video. The stored repair unit is eight seconds and may contain several source shots. An individual source shot inside that unit cannot currently be independently replaced through this API.

### Frontend workflow

The current working tree already provides Prepare → Plan → Result, editable scene prompts, output playback, scene selection, candidate comparison, history/restore and download. A synchronized player can be reused for reference-versus-generated comparison, but the output screen currently compares current versus candidate versions. The video library is browser-local, not a server-side Product/Character/Rights Registry. See [smart-remake-route.tsx:49](../../apps/web/src/features/smart-remake/routes/smart-remake-route.tsx#L49), [use-remake-studio.ts:30](../../apps/web/src/features/smart-remake/lib/use-remake-studio.ts#L30), and [RemakeVersionReview](../../apps/web/src/features/smart-remake/components/remake-version-review.tsx#L10).

## V2 readiness by proposed component

| Proposed component | Current status | Reusable base | Gap that changes readiness |
| --- | --- | --- | --- |
| Remake Constraint Engine | Partial | ProductLock, reference semantics, normalized shot plan, sanitizer | No independently verifiable constraint instances, complete enforcement, or binding between analysis/product bytes/render request. |
| Adaptive Scene Routing | Partial | Creative strategy selection, exact/adaptive shot preservation | Current routing chooses prompt/structure strategy, not a measured per-scene choice among generation/edit/reuse methods. |
| Hybrid Multimodal Video Inspector | Technical subset only | FFprobe, hash checks, source cut detector, technical checker | No output product/character/motion/physical/claim verification pipeline or calibrated evidence. |
| Smart Editing Room | Substantial WIP | Current studio, scene candidates, comparison, accept, restore | Needs integration qualification, recoverability, reference persistence, immutable assembly manifests and findings. |
| Selective Scene Repair | Substantial WIP | Eight-second candidate regeneration, idempotency, checks, accept | No source-shot repair granularity; initial render task recovery incomplete; no semantic recheck. |
| Ad Multiplier | Not located in Smart Remake | Compile/render building blocks | No controlled variant plan, lineage, budgeted batch execution or variant evaluation. |
| Smart Export | Partial download | Presigned download, final assembly | No channel presets, policy gate, approval record or export manifest. |
| Product, Character and Rights Registry | Partial surrounding modules | Product/asset models, workspace access controls | Smart Remake accepts detached inputs; no linked rights/consent/versioned character identity. Product `characterName` is not a person registry. |
| Experiment Lab | Generic evaluation infrastructure only | Existing evaluation schemas/tests/scripts | No verified Smart Remake B0/B1/B2 implementation/evidence bundle, ratings or reproducible ablations. |
| Human Approval and Release Gate | Partial candidate acceptance | Explicit acceptance UI/API | Initial scenes activate automatically on technical pass; download does not require a recorded final human release decision. |

These rows are source-grounded in the linked specialist reports; they do not describe deployed feature flags or a completed V2 product.

## Material findings requiring improvement

1. **Private storage coexists with public output publication.** `_finalize_and_save_output` still invokes the legacy storage writer, which exposes local files through an unauthenticated static mount or returns a public R2 URL. Adding private repair storage does not remove this copy. See [render_orchestrator.py:517](../../apps/backend/src/viraldy/modules/smart_remake/engine/render_orchestrator.py#L517), [storage.py:15](../../apps/backend/src/viraldy/modules/smart_remake/engine/storage.py#L15), [storage.py:56](../../apps/backend/src/viraldy/modules/smart_remake/engine/storage.py#L56), and [main.py:87](../../apps/backend/src/viraldy/api/main.py#L87). External reachability depends on deployment, which was not tested.
2. **Initial render and regeneration have different recovery guarantees.** Initial `render_request` passes `on_scene_output` but not `on_task_submitted`. Repair regeneration does persist provider task metadata. A process failure after initial paid submission and before capture is therefore not covered by the repair reconciliation mechanism. Both operations still await provider work in the HTTP request rather than using the existing general Celery job lifecycle. See [service.py:231](../../apps/backend/src/viraldy/modules/smart_remake/service.py#L231), [repair_service.py:466](../../apps/backend/src/viraldy/modules/smart_remake/repair_service.py#L466), and [architecture](VIRALDY_ARCHITECTURE_CURRENT.md).
3. **Technical pass does not verify the remake.** WIP `technical_check` checks a video stream, aspect ratio, duration, optional audio stream and media hash. It cannot certify product identity, source structure, character consistency, motion, physical plausibility or claims. Initial scenes auto-activate when that technical check passes. See [repair_media.py:24](../../apps/backend/src/viraldy/modules/smart_remake/repair_media.py#L24) and [repair_service.py:378](../../apps/backend/src/viraldy/modules/smart_remake/repair_service.py#L378).
4. **Constraints are not a complete executable contract.** Preserve fields are truncated in prompt compression; arbitrary preserve/change/forbid lists are not independently checked against generated pixels. Client-submitted `compileResult` is parsed and coarsely checked without an owned, immutable compile artifact ID. See [prompt_compressor.py:269](../../apps/backend/src/viraldy/modules/smart_remake/engine/prompt_compressor.py#L269), [prompt_compressor.py:297](../../apps/backend/src/viraldy/modules/smart_remake/engine/prompt_compressor.py#L297), and [service.py:186](../../apps/backend/src/viraldy/modules/smart_remake/service.py#L186).
5. **A source-cut enrichment defect is reproducible offline.** `enrich_reference_analysis_with_detected_cuts` compares the length of an expansion dictionary against the old shot list. The normal expansion dictionary has four keys. With four existing shots and seven detected cuts, expansion contains eight shots but enrichment returns the original four. See [source_shot_detector.py:50](../../apps/backend/src/viraldy/modules/smart_remake/engine/source_shot_detector.py#L50) and [source_shot_detector.py:163](../../apps/backend/src/viraldy/modules/smart_remake/engine/source_shot_detector.py#L163). This was reproduced with a mocked detector and remains unfixed under the read-only audit scope.
6. **Rights, release and deletion controls do not cover this lifecycle end to end.** A rights check exists for a separate generation flow but is not invoked by Smart Remake. Smart Remake forms do not bind source/music/person consent records. WIP project foreign keys and static deletion ordering are not integrated; workspace deletion with retained projects may fail. See [generation/service.py:341](../../apps/backend/src/viraldy/modules/generation/service.py#L341), [smart_remake/router.py:39](../../apps/backend/src/viraldy/modules/smart_remake/router.py#L39), [models.py:19](../../apps/backend/src/viraldy/modules/smart_remake/models.py#L19), [deletion/policy.py:17](../../apps/backend/src/viraldy/modules/deletion/policy.py#L17), and [security report](SECURITY_RIGHTS_AUDIT.md).
7. **Quality and experimental claims remain unverified.** Fixtures, samples, synthetic metrics, generic evaluation contracts and local MP4s are not a linked Smart Remake trial record. No measured product fidelity, comparative success rate, repair savings or true cost/latency result is asserted by this audit. See [experiment evidence](EXPERIMENT_EVIDENCE_AUDIT.md).
8. **Incomplete-scene recovery has an activation dead end.** When two or more scene slots lack an active version, repair can create passing candidates, but `accept` selects only one candidate before `_compose` requires every other slot to be active. The failed assembly leaves all selections unchanged. An offline reproduction using existing in-memory test doubles returned `SMART_REMAKE_SCENE_MISSING`, unchanged revision and no storage writes. Support staged selection or atomic multi-slot acceptance before promising recovery from every partial render. See [repair_service.py:527](../../apps/backend/src/viraldy/modules/smart_remake/repair_service.py#L527), [repair_service.py:590](../../apps/backend/src/viraldy/modules/smart_remake/repair_service.py#L590), and [repair_service.py:670](../../apps/backend/src/viraldy/modules/smart_remake/repair_service.py#L670).
9. **A later failed check does not invalidate readiness.** `check` can mark an active scene version failed while preserving project `ready` status and the final output key. This is stale dependency/readiness state; it does not by itself prove the previously assembled final bytes are corrupt. Release/export policy must distinguish a last approved immutable assembly from a current selection whose verification has changed. See [repair_service.py:730](../../apps/backend/src/viraldy/modules/smart_remake/repair_service.py#L730).

## Verification performed

An existing backend virtual environment ran eight selected offline test modules: Smart Remake integration, scene outputs, repair, prompt edits, repair service, repair media, generic evaluation and TikTok evaluation. Result: **51 passed in 3.11 seconds**, exit 0. Coverage was disabled for this bounded audit run; no coverage percentage is inferred. The set uses fixture/fake providers and repositories; a local synthetic FFmpeg assembly test exercises real media processing. Separate mocked source-cut and in-memory incomplete-project reproductions confirm defects not prevented by those passing tests. Exact commands, test scope and evidence limits are recorded in [EXPERIMENT_EVIDENCE_AUDIT.md](EXPERIMENT_EVIDENCE_AUDIT.md).

Full build, all tests, database/storage integration, browser E2E, external endpoints and live generation were not run. Documentation links and line bounds and requested report coverage were checked. The entry/final hash comparison detected the concurrent source drift described above, so it does not certify that the wider working tree stayed unchanged. The audit's authored changes are the seven Markdown reports only. Passing offline software tests must not be reported as real generation quality or experiment results.

## Three highest-priority technical contributions

1. **A versioned, verifiable remake contract.** Reuse ProductLock/reference/shot plans, but give requirements stable IDs, scope, provenance, severity, preservation/replacement intent and explicit checkability. Persist owned input/artifact hashes and record every constraint dropped or softened for a provider. Correct the cut-count defect and exercise realistic shot counts before adding more routing.
2. **An Inspector tied to reproducible evidence.** Keep technical checks deterministic. Add time-localized product, structure and motion findings through CV/embeddings/multimodal review only after a labeled dataset and calibration plan exist. Store pass/fail/unknown separately and compare against blinded human ratings. Claim accuracy and consent need grounded records and human decisions, not a visual score.
3. **A durable repair and approval lifecycle.** Finish the existing scene candidate/accept workflow using persisted provider task receipts, private retained media, immutable assembly selections, safe recovery and a separate final release decision. Regenerate only the failed unit, reuse unchanged scene hashes, and recheck the new assembly.

These are engineering contributions proposed from observed gaps, not claims of research novelty or measured superiority over competitors.

## Recommended first implementation task

**Complete the existing two-scene render → retained project → single-scene repair → accept/restore → private download slice, beginning with initial-render task persistence and recovery.** Reuse the current repair models and existing job infrastructure; do not start a separate Editing Room application.

Acceptance should demonstrate, with fake providers first: a durable workspace-owned render ID returned before long work; initial provider task receipt persisted; interruption followed by reconciliation without duplicate generation where the provider state is known; explicit handling of the submit/receipt ambiguity window; an unchanged scene retaining its hash when another is repaired; failed/stale candidates preserving the current assembly; private access denied across workspaces and without authorization; migration and deletion coverage; and technical checks plus a recorded release decision before export. Then qualify the same slice with an explicitly authorized small real-provider evidence bundle. Detailed sequencing and acceptance criteria are in [VIRALDY_V2_GAP_ANALYSIS.md](VIRALDY_V2_GAP_ANALYSIS.md).

## Blockers and unresolved uncertainties

- The uncommitted repair/studio changes need a reproducible reviewed source snapshot. Deployment/migration status and private storage configuration are unknown.
- Source continued changing during final verification, including Kie frontend/config/test work. Its complete backend implementation, test outcome and payload/rights/recovery behavior must be audited after that work reaches a stable snapshot.
- FlowKit downstream model routing and provider-side image/video transformation are outside the inspected client. Unifically model aliases/configuration can be overridden; actual live model receipts are absent.
- No supplied raw experiment package establishes prior B0/B1/B2 numbers, rater agreement, failures, costs or provider-generated output lineage.
- Production exposure of static outputs, R2 bucket/CDN policies, provider retention/deletion and actual credentials/feature flags were not inspected live.
- Reference footage and product/person/music rights, external claims evidence and final release ownership are not established by the current Smart Remake request contract.
- Robust product/character/motion checks, acceptable quality thresholds and meaningful multilingual/category coverage require a labeled evaluation set and product decisions.

The current code, especially the uncommitted repair extension, is reusable. The next release should establish one private, recoverable, inspectable and reproducible workflow before widening scene strategies, variants and export destinations.
