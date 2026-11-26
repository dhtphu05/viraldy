# Smart Remake experiment evidence audit

Audit date: 2026-11-24 (Asia/Ho_Chi_Minh). Source snapshot: working tree based on `b68d34dc60c076a33ef3f9718b89e60d64047f39`, including pre-existing uncommitted scene-repair work. This report describes that working tree, not a deployed release. GitNexus was used for discovery; its index was reported stale by ten commits, so source files are authoritative.

Scope update: concurrent Kie/frontend/config/test changes appeared during final verification. Citations and the 51-test result describe the inspected source; the newly appearing Kie tests were not executed or counted. See [the source-drift boundary](VIRALDY_CURRENT_STATE_AUDIT.md#concurrent-source-changes-during-final-verification). Subsequent changes require a new qualification run against a stable source snapshot.

## Verdict and evidence boundary

**Smart Remake has inspectable implementation and passing local software tests, but the inspected checkout does not establish a reproducible B0/B1/B2 or component-ablation result.** No quality improvement, real-provider success rate, human preference, cost per accepted video, or live generation latency can be verified from the available experiment artifacts.

The request mentions an existing project report, but that report and its underlying experiment bundle were not supplied. Searches of the repository's `docs/`, `evaluation/`, backend scripts, implementation and tests did not locate authoritative definitions of B0/B1/B2, ablation configurations, a Smart Remake dataset manifest, raw human ratings, or linked benchmark results. This is an evidence gap in the inspected material, not proof that no external experiment has ever been run.

Only audit documentation was created. No production/test code was changed, dependencies installed, live provider requests initiated, database services started, or private credentials read for this audit. Selected offline tests executed using the existing virtual environment; their exact command and result are recorded below.

Status vocabulary:

- **Implemented:** executable production source exists; deployment and real-provider behavior still require operational evidence.
- **Partial:** useful production hooks exist but do not form a reproducible experiment.
- **Fixture/mock:** deterministic responses, supplied labels or fake adapters exercise software behavior.
- **Unavailable in inspected material:** a required artifact was not found or supplied; no numerical conclusion is justified.
- **Proposed:** acceptance criteria below describe future work and are not implemented experimental results.

## Evidence inventory

| Requested evidence | Status | Source and observed limitation |
| --- | --- | --- |
| B0/B1/B2 implementations | Unavailable in inspected material | No authoritative baseline definitions, run selectors or result tables were located in the searched source/docs/test areas. Existing provider routes must not be relabeled as B0/B1/B2 without a versioned specification. |
| Component ablations | Unavailable in inspected material | Compiler, ProductLock and provider adapters exist, but no one-component-at-a-time experiment matrix, paired run ledger or ablation result bundle was located. A product feature flag or provider switch is not by itself an ablation study. |
| Smart Remake dataset manifest | Unavailable in inspected material | No source-video/product-image/character-image manifest with hashes, rights, splits and expected constraints was found. The existing `EvaluationDatasetV1` contains PatternKit/ViralKit cases, not remake generation runs: [contracts.py:82](../../apps/backend/src/viraldy/evaluation/contracts.py#L82). |
| Captured provider task logs | Partial instrumentation; experimental captures unavailable | Runtime collects task IDs and can retain per-scene provider metadata; no exported task-status chronology joined to experiment/case/config IDs was found: [`_render_with_unifically`:385](../../apps/backend/src/viraldy/modules/smart_remake/engine/render_orchestrator.py#L385), [`RepairService.repair` task recording:466](../../apps/backend/src/viraldy/modules/smart_remake/repair_service.py#L466). |
| Raw human ratings | Unavailable in inspected material | Generic contracts accept scores, but no Smart Remake rating sheet with reviewer, rubric, blinded comparison assignment and exact output hash was located: [`human_usefulness_scores`:73](../../apps/backend/src/viraldy/evaluation/contracts.py#L73), [`ScorerHumanLabelsV1`:174](../../apps/backend/src/viraldy/evaluation/tiktok_scorer_contracts.py#L174). |
| Output videos | Local media present; experiment provenance unverified | Optional static sample/demo MP4s exist, including an explicitly selected demo result. No manifest joins those bytes to a paid provider task, model, prompt, source, product, run ID and rating. See local inventory below. |
| Success/failure records | Runtime capability plus fixture tests; benchmark ledger unavailable | Repair operations persist status/result JSON, and tests simulate partial failure and recovery. These are not a measured live-provider failure population: [models.py:28](../../apps/backend/src/viraldy/modules/smart_remake/models.py#L28), [test_smart_remake_scene_outputs.py:84](../../apps/backend/tests/unit/test_smart_remake_scene_outputs.py#L84). |
| Cost/token measurements | Partial reusable infrastructure elsewhere; Smart Remake run measurements unavailable | Generic `AiModelRunModel` supports usage and estimated cost. Smart Remake directly invokes Gemini/FlowKit/Unifically and the inspected flow does not populate that run ledger: [models.py:86](../../apps/backend/src/viraldy/modules/ai_gateway/models.py#L86), [gemini_client.py:207](../../apps/backend/src/viraldy/modules/smart_remake/engine/gemini_client.py#L207), [render_orchestrator.py:385](../../apps/backend/src/viraldy/modules/smart_remake/engine/render_orchestrator.py#L385). |
| Latency measurements | Unavailable for Smart Remake benchmark runs | Timeouts/polling deadlines exist; no captured per-stage or end-to-end remake latency distribution was found. Generic scorer evaluation can aggregate supplied latency values, which does not establish their provenance: [tiktok_scorer_contracts.py:189](../../apps/backend/src/viraldy/evaluation/tiktok_scorer_contracts.py#L189). |
| Fixture/mock tests | Implemented and selected tests executed | 51 selected tests passed, including actual local FFmpeg assembly of synthetic clips. All generation/provider behavior in these tests is deterministic or mocked. |

### Repository and ignored local artifact inventory

Default tracked/source searches were supplemented with an ignored-file inventory because generated outputs and optional media are explicitly ignored. As observed during this audit:

| Location | Local observation | Interpretation |
| --- | --- | --- |
| `evaluation/` | One file: `README.md` | Harness usage documentation; not an experiment result bundle. |
| `apps/backend/evaluation/reports/` | Directory absent | No local qualification report bundle available there. |
| `artifacts/`, `apps/web/artifacts/` | Directories absent | No local experiment artifact bundle available in those repository locations. |
| `apps/backend/outputs/` | 18 JPEGs, all under Smart Remake source-frame storage | Preprocessing residue; no generated MP4, run manifest, rating file or provider log in this directory at inspection time. Image contents were not interpreted as quality evidence. |
| `apps/web/public/demo-media/` | Six MP4s and eleven JPEGs | Static demo/library assets; no experiment provenance established. |
| `apps/web/public/smart-remake/` | Two MP4s, two WebP files and one extensionless filesystem file | Optional local sample assets; `02_After.mp4` is explicitly the frontend demo output and `binhnuoc.mp4` is loaded by the sample action. |
| `apps/web/public/product_ads/` | 75 MP4s | Optional local advertising reference/library media, not an identified set of generated B0/B1/B2 results. |

The ignore rules explain why these media are absent from an ordinary source inventory: [`.gitignore`:17](../../.gitignore#L17) and [`.gitignore`:22](../../.gitignore#L22). These counts describe one local checkout; ignored media are not portable repository fixtures. Build-output copies of static assets were excluded from evidence counts to avoid counting the same logical media twice.

The demo path is explicit: [`DEMO_OUTPUT_VIDEO`:16](../../apps/web/src/features/smart-remake/lib/smart-remake-render.ts#L16) and [`renderSmartRemakeVideo`:28](../../apps/web/src/features/smart-remake/lib/smart-remake-render.ts#L28) return the static MP4 only when `demo === true`. The sample source paths are in [`loadSample`:278](../../apps/web/src/features/smart-remake/lib/use-remake-studio.ts#L278). A playable “after” file, its filename, or a completed demo UI state does not establish that the current provider implementation produced it.

No deployment database, remote object store, external provider dashboard or external experiment archive was queried. Provider task IDs persisted in a deployment may therefore exist beyond this audit's evidence boundary.

## Existing evaluation infrastructure and its actual scope

### PatternKit/ViralKit captured-output evaluation

[`evaluation/README.md`:3](../../evaluation/README.md#L3) explicitly describes scoring captured PatternKit/ViralKit outputs without invoking a provider. [`scripts/run_evaluation.py::main`:13](../../apps/backend/scripts/run_evaluation.py#L13) reads a supplied JSON dataset, validates it, evaluates it, and writes JSON/Markdown reports.

[`evaluate_dataset`:32](../../apps/backend/src/viraldy/evaluation/harness.py#L32) deterministically scores sorted cases. Metrics include schema validity, evidence-reference resolution, supplied field/category judgments, concept separation, supplied grounding/constraint labels, compilation checks, and human-usefulness scores. [`render_json_report`:14](../../apps/backend/src/viraldy/evaluation/reporting.py#L14) sorts output keys; the CLI report determinism is covered by [test_evaluation.py:173](../../apps/backend/tests/unit/test_evaluation.py#L173).

Reusable strengths are typed contracts, stable case IDs, structured judgments, numerators/denominators, deterministic reports and offline replay. Limitations for Smart Remake:

- `mode` is a supplied `fixture`/`mock`/`live` label; [`EvaluationDatasetV1`:82](../../apps/backend/src/viraldy/evaluation/contracts.py#L82) does not require a provider request ID, model, media hash or signed provenance before accepting `live`.
- Inputs do not identify generated scene bytes or a reference/product pair. Grounding/constraint metrics consume supplied booleans, not visual inspection of generated MP4s.
- The raw human-score list contains no rater ID, annotation timestamp, output hash, rubric version or blindness assignment.
- [`_rate_metric`:208](../../apps/backend/src/viraldy/evaluation/harness.py#L208) and [`_score_metric`:229](../../apps/backend/src/viraldy/evaluation/harness.py#L229) report zero for an empty denominator. Preserve denominator visibility; future remake evaluation should represent absent judgments as **unmeasured**, not as measured zero-quality results.

### Golden cases and TikTok scorer evaluation

The three commercial Golden scenarios are explicitly enumerated by [`GOLDEN_SCENARIO_IDS`:8](../../apps/backend/src/viraldy/evaluation/golden/loader.py#L8). [`GoldenAssetV1`:42](../../apps/backend/src/viraldy/evaluation/golden/contracts.py#L42) describes duration, audio and observations rather than stored MP4 bytes. These are semantic/contract test descriptors, not a Smart Remake generation dataset.

The TikTok scorer fixture states `synthetic_only: true` and `claims_real_world_accuracy: false`: [tiktok_scorer_cases_v1.json:1](../../apps/backend/src/viraldy/evaluation/golden/fixtures/tiktok_scorer_cases_v1.json#L1). [`evaluate_tiktok_scorer_dataset`:44](../../apps/backend/src/viraldy/evaluation/tiktok_scorer_harness.py#L44) also includes limitations that synthetic evaluation does not establish real-world accuracy and missing human labels leave human metrics unmeasured.

The scorer contract has a useful explicit measured/unmeasured distinction: [`TikTokScorerMetricResultV1`:213](../../apps/backend/src/viraldy/evaluation/tiktok_scorer_contracts.py#L213). Reuse that semantics when designing remake evaluation.

**Do not copy test constants into product performance claims.** [test_tiktok_scorer_evaluation.py:192](../../apps/backend/tests/unit/test_tiktok_scorer_evaluation.py#L192) supplies `latency_ms=1250` and `cost_usd=0.042` and verifies aggregation. Those are synthetic test inputs, not measurements of the current scorer or Smart Remake.

### OpenAI qualification tooling

[`scripts/qualify_openai.py::main`:82](../../apps/backend/scripts/qualify_openai.py#L82) can inspect configuration or run selected operation/full-flow qualification, potentially using live provider settings or an application API. It was **not run** during this audit.

The operation registry covers media observation, Creative DNA, PatternKit, ViralKit, adaptation, Campaign Pack and seller/revision summaries; it does not include the Gemini/FlowKit/Unifically Smart Remake render path: [`OPERATION_ALIASES`:16](../../apps/backend/src/viraldy/evaluation/qualification/catalog.py#L16).

Reusable reporting contracts record mode, run ID, timestamps, model/prompt/schema versions, provider request IDs, gates, application evidence and confidence: [`OperationExecutionV1`:133](../../apps/backend/src/viraldy/evaluation/qualification/contracts.py#L133), [`QualificationReportV1`:181](../../apps/backend/src/viraldy/evaluation/qualification/contracts.py#L181). [`write_qualification_report`:44](../../apps/backend/src/viraldy/evaluation/qualification/reporting.py#L44) separates outputs, failures and best outputs and sanitizes reports.

[`DeterministicQualificationExecutor`:56](../../apps/backend/src/viraldy/evaluation/qualification/executors.py#L56) explicitly rejects `live` mode and builds fixture outputs; mock request IDs are synthetic. Its passing results cannot qualify Smart Remake live generation.

## Smart Remake provenance already available for reuse

The current repair work is useful infrastructure rather than a completed research result:

- [`RepairService.begin_render`:284](../../apps/backend/src/viraldy/modules/smart_remake/repair_service.py#L284) retains SceneMap, ProductLock, ReferenceAnalysis and product media storage context. These are logical snapshots, not a complete versioned experimental configuration.
- [`_new_version`:60](../../apps/backend/src/viraldy/modules/smart_remake/repair_service.py#L60) binds stored scene bytes to SHA-256, prompt snapshots, parent version, provider metadata, creation time and a technical check.
- [`capture_render_output`:338](../../apps/backend/src/viraldy/modules/smart_remake/repair_service.py#L338) persists raw scene outputs and checks final assembly before making it ready.
- `_render_with_unifically` emits provider request IDs on task submission and scene output: [render_orchestrator.py:385](../../apps/backend/src/viraldy/modules/smart_remake/engine/render_orchestrator.py#L385) and [render_orchestrator.py:432](../../apps/backend/src/viraldy/modules/smart_remake/engine/render_orchestrator.py#L432). Repair task recording persists those IDs for recovery: [repair_service.py:466](../../apps/backend/src/viraldy/modules/smart_remake/repair_service.py#L466).
- [`_stable_unifically_seed`:113](../../apps/backend/src/viraldy/modules/smart_remake/engine/render_orchestrator.py#L113) uses a configured seed or CRC32 of product bytes and ProductLock. Retry can remove the seed: [render_orchestrator.py:403](../../apps/backend/src/viraldy/modules/smart_remake/engine/render_orchestrator.py#L403). Experiments must record effective requests for each attempt; a stable seed does not prove byte-identical provider outputs.

Remaining provenance gaps include reference/product dataset membership, immutable model/prompt/compiler revisions, complete request/response snapshots, stage timestamps, all retries/failures and billing outcomes, and joins from ratings to exact media versions. Generic model-run cost/usage columns are reusable but their existence is not evidence that these direct Smart Remake calls populate them.

Technical validity is narrower than remake fidelity. [`technical_check`:24](../../apps/backend/src/viraldy/modules/smart_remake/repair_media.py#L24) checks a video stream, aspect ratio, duration and optionally audio. It does not score product identity, character identity, source structure/motion, physical plausibility, claim truth or seller usefulness. Its hash binding is suitable for attaching future semantic inspection and human ratings to the correct version.

Fixture render behavior is candid: [`render_request`:209](../../apps/backend/src/viraldy/modules/smart_remake/service.py#L209) returns empty provider request arrays, no final video, and `status: submitted` with a warning that no video provider was called. Do not count this response as a successful generated video.

## Offline verification executed

Working directory: `/Users/mac/Desktop/Viraldy/apps/backend`.

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest --no-cov -p no:cacheprovider -q tests/unit/test_smart_remake_integration.py tests/unit/test_smart_remake_scene_outputs.py tests/unit/test_smart_remake_repair.py tests/unit/test_smart_remake_prompt_edits.py tests/unit/test_smart_remake_repair_service.py tests/unit/test_smart_remake_repair_media.py tests/unit/test_evaluation.py tests/unit/test_tiktok_scorer_evaluation.py
```

Observed result: **exit code 0; 51 passed in 3.11s**. The 3.11-second figure is the test-suite duration, not provider inference or generation latency. No coverage percentage was measured: `--no-cov` intentionally overrides the repository-wide coverage defaults for this focused audit run, whose default threshold is 70% in [pyproject.toml:91](../../apps/backend/pyproject.toml#L91). This result does not establish 80% coverage or a full-suite pass.

Test source was inspected before execution; no project `conftest.py` was found outside excluded dependency/cache/Git directories. The selected tests inject fake providers, repositories, storage and probes rather than sending generation requests. Temporary synthetic datasets/reports and FFmpeg clips are local test artifacts, not additions to the experiment corpus.

| Test file | What the passing run establishes | What it cannot establish |
| --- | --- | --- |
| [test_smart_remake_integration.py:23](../../apps/backend/tests/unit/test_smart_remake_integration.py#L23) | Supported durations; deterministic compiler scene count; fixture shapes; reference-video payload guard; mocked product-link handoff; mocked HTTP timeout reporting. | Actual Gemini understanding, product extraction quality or generation. The test named `test_live_gemini_timeout...` replaces the HTTP client with a fake. |
| [test_smart_remake_scene_outputs.py:33](../../apps/backend/tests/unit/test_smart_remake_scene_outputs.py#L33) | Fake task IDs and bytes are retained per scene/final output; a simulated FlowKit partial failure retains the good scene; ambiguous server submission errors are not blindly resubmitted. | Provider task completion rates, network reliability, actual clip decodability or fidelity. |
| [test_smart_remake_repair.py:14](../../apps/backend/tests/unit/test_smart_remake_repair.py#L14) | Request/schema restrictions, hash-bound technical checks with supplied probe facts, prompt/identity/segment preservation and download filename sanitization. | Visual product identity or successful paid repair. |
| [test_smart_remake_prompt_edits.py:8](../../apps/backend/tests/unit/test_smart_remake_prompt_edits.py#L8) | Edited directions reach bounded prompts; extensive changes are rejected instead of silently truncated. | That a generation model obeys those directions. |
| [test_smart_remake_repair_service.py:90](../../apps/backend/tests/unit/test_smart_remake_repair_service.py#L90) | In-memory versions/revision/idempotency/recovery behavior under simulated success/failure; mocked checks and composition. | PostgreSQL transaction behavior, S3 retention, live provider reconciliation or human approval effectiveness in deployment. |
| [test_smart_remake_repair_media.py:16](../../apps/backend/tests/unit/test_smart_remake_repair_media.py#L16) | Actual local FFmpeg generates two synthetic eight-second scenes and assembly preserves audible second-scene content after a silent first scene. Input scene hashes remain unchanged. | Generated-video semantics, product/character continuity, reference motion or advertising quality. |
| [test_evaluation.py:37](../../apps/backend/tests/unit/test_evaluation.py#L37) | Fixture/mock/live labels parse; structured rubric arithmetic and deterministic offline report/CLI behavior. | Real-provider provenance or validity of human judgments supplied by a caller. |
| [test_tiktok_scorer_evaluation.py:22](../../apps/backend/tests/unit/test_tiktok_scorer_evaluation.py#L22) | Synthetic Golden labels, evidence/timestamp invariants and measured/unmeasured reporting work as asserted. | Generalization, real-world scorer accuracy or Smart Remake output fidelity. |

The PostgreSQL integration test was inventoried, not executed: [test_smart_remake_repair_persistence.py:21](../../apps/backend/tests/integration/test_smart_remake_repair_persistence.py#L21) starts a `postgres:16.6-alpine` testcontainer and upgrades/downgrades migrations. Browser E2E, application-service integration, live qualification, full backend/frontend suites and load tests were not executed for this report.

### Additional bounded reproduction: detected source cuts can be discarded

After the passing suite, a separate offline reproduction confirmed a structural-fidelity defect outside those selected assertions. [`enrich_reference_analysis_with_detected_cuts`:55](../../apps/backend/src/viraldy/modules/smart_remake/engine/source_shot_detector.py#L55) compares `len(expanded)` (the number of dictionary keys) against `len(source_shots)` instead of comparing the number of expanded shots. With four analyzed shots and seven measured cuts, the expansion contains eight shots in a four-key dictionary; the wrapper incorrectly returns the original four-shot analysis.

The following exact command ran from the same backend directory. `detect_source_cuts` is patched, so no media decoding, FFmpeg subprocess, network/provider request or file write occurs:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python - <<'PY'
from unittest.mock import patch
from viraldy.modules.smart_remake.engine.schemas import UploadedMedia
from viraldy.modules.smart_remake.engine.source_shot_detector import (
    enrich_reference_analysis_with_detected_cuts,
    expand_source_shots_to_cut_boundaries,
)
analysis = {
    'sourceShots': [
        {'startSecond': i * 2, 'endSecond': (i + 1) * 2, 'action': 'demo'}
        for i in range(4)
    ]
}
expanded = expand_source_shots_to_cut_boundaries(
    analysis, duration_seconds=8, cut_times=list(range(1, 8))
)
with patch(
    'viraldy.modules.smart_remake.engine.source_shot_detector.detect_source_cuts',
    return_value=(8, list(range(1, 8))),
):
    returned = enrich_reference_analysis_with_detected_cuts(
        analysis, UploadedMedia(bytes=b'not-read', mime_type='video/mp4')
    )
print({
    'analyzed_shots': len(analysis['sourceShots']),
    'expanded_dictionary_keys': len(expanded),
    'expanded_shots': len(expanded['sourceShots']),
    'returned_shots': len(returned['sourceShots']),
    'returned_original': returned is analysis,
})
PY
```

Observed result, exit code 0:

```text
{'analyzed_shots': 4, 'expanded_dictionary_keys': 4, 'expanded_shots': 8, 'returned_shots': 4, 'returned_original': True}
```

This is a reproduced implementation defect with simulated cut-detection output, not a measured frequency of failure on real videos. Correcting the comparison and adding a regression assertion are prerequisite implementation work before evaluating cut-aware versus ablated structural fidelity. Production code was left unchanged as requested.

### Additional bounded reproduction: two missing active scenes block recovery

A separate in-memory reproduction exercised the real [`RepairService.accept`:641](../../apps/backend/src/viraldy/modules/smart_remake/repair_service.py#L641) with both scene slots inactive and a technically passed candidate available for the second scene. `accept` sets the chosen candidate on a copied state, then requires successful assembly before persisting activation. [`_compose`:584](../../apps/backend/src/viraldy/modules/smart_remake/repair_service.py#L584) rejects the still-missing first scene, so neither slot becomes active and revision remains unchanged. The first accepted candidate cannot be saved while another slot is missing; generating inactive candidates for both slots does not resolve this dependency.

The exact command below ran from the backend directory, using existing `MemoryRepository`/`MemoryMedia` doubles. It was independently rerun with the same result. No provider call, media read/write or storage-object write occurs; `_compose` creates and removes a temporary directory before detecting the missing slot.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python - <<'PY'
import asyncio, runpy
from types import SimpleNamespace
from uuid import uuid4
from viraldy.modules.smart_remake.repair_service import RepairService
from viraldy.modules.smart_remake.repair_schemas import AcceptSceneVersion

async def run():
    fixtures = runpy.run_path('tests/unit/test_smart_remake_repair_service.py')
    repository, media = fixtures['MemoryRepository'](), fixtures['MemoryMedia']()
    workspace_id, project_id, first_id, second_id, version_id = [uuid4() for _ in range(5)]
    candidate = {'id':str(version_id),'parentVersionId':None,'usedByRevision':None,'technicalCheck':{'status':'passed'}}
    row=SimpleNamespace(id=project_id,workspace_id=workspace_id,revision=1,context_json={},state_json={'revision':1,'status':'incomplete','scenes':[{'id':str(first_id),'index':0,'activeVersionId':None,'versions':[]},{'id':str(second_id),'index':1,'activeVersionId':None,'versions':[candidate]}]})
    repository.rows[project_id]=row
    service=RepairService(repository,media,workspace_id)
    try:
        await service.accept(project_id,AcceptSceneVersion(sceneId=second_id,versionId=version_id,expectedRevision=1,idempotencyKey='audit-missing-slots'))
    except Exception as exc:
        print({'errorCode':getattr(exc,'code',type(exc).__name__),'revision':row.revision,'activeVersions':[s['activeVersionId'] for s in row.state_json['scenes']],'objectWrites':len(media.objects)})

asyncio.run(run())
PY
```

Observed result, exit code 0:

```text
{'errorCode': 'SMART_REMAKE_SCENE_MISSING', 'revision': 1, 'activeVersions': [None, None], 'objectWrites': 0}
```

This reproduces the recovery-state control flow without a real provider or persisted database; it does not measure how often multi-scene failure occurs. A future acceptance criterion is that a two-scene project with both active slots missing/invalid can stage and approve technically valid scene candidates, complete assembly, and become ready without regenerating an already approved valid scene. That regression case is separate from the 51 passing selected tests. No production fix was made.

## Reproducibility gaps and proposed acceptance criteria

The criteria below are recommended requirements for a first experiment bundle. They are not measured outcomes or existing baseline definitions.

| Priority | Gap / minimum change | Acceptance criteria |
| --- | --- | --- |
| P0 | Define B0/B1/B2 before comparing them | A versioned specification names the exact baseline behavior, model, adapter, prompt/compiler revisions and intended controlled differences. The runner rejects unknown variant IDs. Do not infer meanings for B0/B1/B2 from the request alone. |
| P0 | Create one rights-cleared, versioned paired dataset | Manifest links immutable source/product/optional-character hashes, media facts, consent/rights references, category, required substitutions/preservations, supported 8/16-second duration and split. Every planned case has valid input hashes and explicit expected constraints. |
| P0 | Capture one complete real-provider vertical slice, when authorized separately | Reference/product → analysis/lock → compiled scenes → each submitted task/attempt → raw clips → assembled video → technical inspection → human review are joined by case/run/scene/version IDs. Include a failure record if any stage fails; no simulated result is labeled live. |
| P0 | Add immutable run/attempt provenance | Record Git commit plus dirty-diff fingerprint, environment/runtime/FFmpeg versions, exact provider/model identifiers, effective sanitized payloads, prompt/schema/compiler versions, seeds including removed/replaced retry seeds, submission/poll/download/assembly timestamps, task IDs, retry reasons and artifact hashes. Preserve a replayable offline bundle. |
| P0 | Establish a human rubric independent of generation prompts | Record product fidelity, structural fidelity, character consistency when applicable, motion consistency, physical plausibility, advertising claims and seller usefulness separately. Ratings attach to exact output hashes, rubric versions, pseudonymous reviewers and annotation times; use blinded randomized paired comparisons and a declared disagreement/adjudication policy. Missing labels remain unmeasured. |
| P0 | Measure failure, cost and latency with complete denominators | Ledger contains every planned and attempted case, cancelled/failed/ambiguous tasks, downloads and repairs, not only accepted outputs. Separate queue time, analysis, generation, polling, transfer, assembly and inspection. Reconcile provider-reported/billed costs where available; distinguish estimate/actual/unknown, include retry/repair charges and report cost per accepted output without substituting zero for missing cost. |
| P1 | Run controlled paired ablations | Change one declared component at a time while preserving dataset, provider/model, effective duration/resolution and other configuration. Record multiple stochastic attempts where applicable; account explicitly for shared upstream artifacts and failed cases. Results report paired sample sizes, uncertainty and exclusions rather than only a selected average. |
| P1 | Implement deterministic offline recomputation | A documented command validates manifests and recomputes all aggregate tables from retained raw task records, machine checks and ratings without provider requests. Fixture/mock/live datasets cannot silently merge. Missing artifacts fail validation; published report hashes resolve to their inputs. |
| P1 | Add automated semantic inspection only after a labeled evaluation set exists | Product/structure/motion/character/physics/claim checks have separate evidence-backed metrics and calibrated pass/fail/unknown handling. Evaluate against held-out human judgments; a passing technical probe cannot stand in for visual fidelity. |
| P2 | Build Experiment Lab UI after the evidence contract is stable | UI shows provenance mode, variant/config differences, original/output/scene versions, ratings, failures, cost completeness and uncertainty. It can open the exact run artifacts and never presents static sample media or synthetic test scores as measured production performance. |

First task: define the experiment manifest/run contract and capture one complete **single-case, two-scene** evidence bundle using the existing scene-retention and hash/check hooks. Prepare and test its offline replay before any broad provider benchmark. A later explicitly authorized provider run can populate the real evidence; the present audit does not initiate it.

## Unresolved uncertainties

- The referenced earlier report, B0/B1/B2 definitions and original result spreadsheets/logs were not supplied; prior numerical claims remain unverified.
- No live deployment inventory was provided, so persisted provider tasks, object-store clips, deleted/expired assets and provider billing cannot be reconciled here.
- Optional local sample media have no inspected run provenance; their true origin and rights cannot be inferred from filenames or visual availability.
- Passing in-memory repair tests do not establish that the pre-existing repair migration is deployed or that PostgreSQL concurrency and object-store behavior pass in the target environment.
- Provider determinism and effective seed behavior, live retry billing, real error prevalence, human annotation reliability, and any generalization beyond synthetic descriptors remain unmeasured.
