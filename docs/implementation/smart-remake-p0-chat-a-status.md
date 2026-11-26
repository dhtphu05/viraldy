# Chat A — Smart Remake P0

Status: **READY_FOR_LIVE_PILOT — Chat A code/prepared offline**. Live execution: **BLOCKED**. Contract: **p0-lifecycle-v1 / GenerationExpectations v1 / inspection-v1.2**. Ngày: 25/11/2026.

## GenerationExpectations upgrade — 25/11/2026

Đã nối snapshot v1 bất biến theo hash từ facts sản phẩm, yêu cầu seller, tư liệu và từng cảnh vào OpenAI, KIE và Inspector. Raw analysis giữ riêng; toàn bộ creative payload được sanitize và kiểm tra sau chỉnh sửa. Ảnh mở đầu giải mã từ nguồn đã kiểm hash theo absolute frame trên clock24fps, giữ độ phân giải/tỷ lệ nguồn; cache cũ không được tái dùng.

Cut detector và mốc cắt seller dùng tối đa một lượt semantic analysis bổ sung qua client ngân sách hiện có. Không nhân bản state của cảnh cha; thiếu ngữ nghĩa hoặc range sai dừng trước generation. Compiler2.1, conditioning-v2 và checker1.2/rubric-v2 làm hết hiệu lực cache/report theo chuẩn cũ.

Operation, clip, assembly/version/range, report, approval và export giữ binding mới. Yêu cầu/facts/frame/range đổi làm stale. Plan cũ cần cập nhật trước generation/repair; task cũ đã submit hoặc chưa rõ kết quả chỉ được đối soát. QA lịch sử chỉ dựng snapshot không trả phí khi đủ dữ liệu lịch sử và hash yêu cầu khớp; thiếu thì yêu cầu chuẩn bị/ghép lại. Restore tạo bản mới, giữ lịch sử nguyên vẹn.

Giữ **seller quyết định**: semantic failure/uncertainty được chấp nhận với lý do; technical/rights hard blocks giữ nguyên. Mọi free-text keep/replace/forbid trên video không tự PASS từ ảnh tĩnh. Opening PASS cần evidence của ảnh sinh, sản phẩm và đúng opening nguồn.

Qualification đợt này: **975 tests (903 unit +72 integration), coverage92,07% trên32 file thuộc phạm vi sửa**, không skip/lỗi; không phải coverage toàn repository. Hai file legacy riêng lẻ dưới80%: compile_service70,89%, source_shot_detector76,79%. [Kết quả và lệnh tái chạy](/Users/mac/Desktop/Viraldy/artifacts/smart-remake-p0/expectations-upgrade-20261125/final-backend.summary.json). Browser fixture dùng stack riêng, provider constructor giả và chặn mạng ngoài; không gọi generation trả phí và không chứng minh chất lượng model live.

A1–A5 đã triển khai và kiểm thử; readiness này áp dụng code và gói chuẩn bị offline. Checkpoint mới nhất: local runtime đã chạy, B đã offline-qualified; người dùng chỉ cho phép **một video KIE riêng, trần tổng0,50USD, không retry**, chưa chạy toàn bộ Smart Remake. Preflight KIE thiếu credit nên vẫn zero paid generation. Không tuyên bố LIVE_VERIFIED; chi tiết tại checkpoint cuối file.

Baseline: `feat/assets` / `b68d34d` cùng WIP hiện tại, bao gồm file chưa tracked. Chỉ thay đổi backend ownership A; giữ nguyên `inspection/`, frontend và eval harness của B.

| Task | Trạng thái | Công việc hiện tại |
| --- | --- | --- |
| A1 | READY | Owned intake trước analysis, requirements/quyền/consent, hash binding; PostgreSQL + actual HTTP đạt |
| A2 | READY | Atomic ledger cả bốn paid stages; no blind retries, unknown hold và rights-race tests đạt |
| A3 | READY | Immutable assembly/history/restore, trim/repair, giữ scene tốt/output cũ và revocation race đạt |
| A4 | READY | Checked export nhãn AI thực, fresh rights gate, immediate stop/deletion; actual API đạt |
| A5 | READY | B Inspector + authorized bytes + worker + frozen clock mappings + provenance; runbook/checker/media package có sẵn |

## Contract M1 đã khóa

- Workspace prefix/envelope giữ nguyên; `POST /projects` multipart: `metadata` JSON, `referenceVideo`, `productImage`, optional `characterImage`. Không gọi AI; trả `data.project` với ID/revision/phase intake. `metadata`: idempotencyKey, projectName, targetDuration (8/16), requirements, rights, budget.
- `requirements`: intent, keep[], replace[], forbid[], claims[], requiresCharacter; không thay input chỉ bằng prompt.
- `rights`: source/product/optional character declarations, mỗi record có basis/scope/evidenceNote/attribution/declared/revoked; optional characterConsent; providerDisclosureAcknowledged. Declaration được lưu như declaration, không tự xem là verified.
- `budget`: capUsd decimal string, maxAttempts, maxDurationSeconds. Server reservation bounds cấu hình riêng theo stage, không lấy dự toán client làm giá thật.
- `POST /compile` mode reference giữ form hiện tại, thêm ràng buộc live phải có owned projectId của intake. Plan sau compile giữ cùng projectId và tăng revision; GET trả thông tin ownership/requirements/rights/budget đầy đủ.
- Metadata canonical: `project.context_json.p0`. Assembly history: `p0.assemblies`; reports/reviews: `p0.inspections`; approval/export history: `p0.release`. UI nhận các projection top-level, không storage keys.
- Inspector reviews: reportId, findingId, decision `accept|reject`, reason; actor/time do server ghi. Hard failure không override được bằng review.
- Các endpoint/schema M1 chi tiết bên dưới đã khóa cho B; chưa coi phần này là BACKEND_INTEGRATED trước khi API/worker qualification xong.

## Phối hợp B

Đã tích hợp typed callback với `inspection/public.py`, API/worker/release và projection evidence. Actual API5 tests đạt trọn intake→worker→Inspector→approval/export→restore/deletion. B đã chạy offline browser/capture cho8s và repair16s; B vẫn tự chốt qualification frontend/browser. B không cần sửa router/worker/persistence của A.

## Kiểm chứng

Final A qualification: **755 tests đạt, coverage94.50% trên32 modules**, PostgreSQL/FFmpeg và API/worker thật, physical providers giả. **17 contract tests**, scoped Ruff và strict mypy31 source files đạt. Không paid calls/commit/push; không coi đây là toàn backend/repo suite hay kết quả live quality.

## M1 wire examples đã khóa (p0-lifecycle-v1)

Base `/workspaces/{workspace_id}/smart-remake`, envelope `data`. `POST /projects` trả `{project}`. Mọi mutation còn lại có `expectedRevision` (integer >=1), `idempotencyKey` (string); actor/time do server ghi.

- `POST /compile`: form hiện có, `timelineMode=reference`, `projectId`, `expectedRevision`, `idempotencyKey`, `targetDuration=8|16`, `aspectRatio=9:16`. Dùng media intake đã lưu; không cần upload lại. Giữ cùng projectId.
- `PATCH /projects/{id}/requirements`: `{expectedRevision,idempotencyKey,requirements:{intent,keep:[],replace:[],forbid:[],claims:[],requiresCharacter:false,characterReferencePolicy:"product_and_character"}}`.
- `PATCH /projects/{id}/rights`: `{expectedRevision,idempotencyKey,rights:{source:{basis:"owned",scope:"Remake and AI processing",declared:true,evidenceNote:"Self-authored input",attribution:null,revoked:false},product:{...},providerDisclosureAcknowledged:true}}`. Optional character declaration + `characterConsent:{consented:true,scope,evidenceNote,revoked:false}` khi có nhân vật. **Không gửi** `verified`, `verification`, `declaredBy/At` từ GET về mutation; strict API từ chối giả trạng thái xác minh.
- `PATCH /projects/{id}/budget`: `{expectedRevision,idempotencyKey,budget:{capUsd:"<explicit cap>",maxAttempts:20,maxDurationSeconds:1800}}`. Không giảm cap dưới exposure hiện tại.
- `POST /projects/{id}/rights/reviews`: `{expectedRevision,idempotencyKey,evidenceNote:"Human evidence review"}`. Ghi reviewed, không tự thành verified.
- `POST /projects/{id}/inspections`: `{expectedRevision,idempotencyKey,subject:{kind:"assembly",assemblyId}}`; hoặc `{kind:"scene",sceneId,versionId}`; hoặc `{kind:"image",imageRole:"product"|"character"}`. Queue durable, không chạy model inline.
- `POST /projects/{id}/inspection-reviews`: `{expectedRevision,idempotencyKey,reportId,findingId,decision:"accept"|"reject",reason}`. Hard failure không override.
- `POST /projects/{id}/approvals`: `{expectedRevision,idempotencyKey,assemblyId,reportId}`.
- `POST /projects/{id}/exports`: `{expectedRevision,idempotencyKey,assemblyId,approvalId}`. Trả `{project,operationId,status,downloadUrl,assemblyId,sourceMediaHash,exportMediaHash,...}` cho file có nhãn AI thực.
- `POST /projects/{id}/restore`: `{expectedRevision,idempotencyKey,assemblyId}`. Tạo assembly mới, cần Inspector/approval mới.
- `POST /projects/{id}/deletions`: `{expectedRevision,idempotencyKey,reason}`. Ngừng dùng ngay; shared/running/provider retention có trạng thái rõ.
- `GET /projects/{id}/provenance`: version `smart_remake_provenance_v1`; shape chi tiết sẽ khóa trước B4 integration.

Project projection: `phase`, `requirements`, `rights`, `constraintsHash`, `budget` summary (policy,attemptCount,unknownAttemptCount,estimatedUsd,knownActualUsd,actualUsd nullable,reservedUsd,exposureUsd,remainingUsd,status), `inspectionSummary:{status?,reason?,reports:[],reviews:[]}`, `assemblies:{activeAssemblyId,records:[],history:[]}`, `release:{activeApprovalId,approvals:[],exports:[]}`, `deletion`. Không trả storage keys/snapshots nội bộ. `/publish` chỉ private compose preview; P0 GET không cấp downloadUrl.

Error codes: `SMART_REMAKE_INTAKE_REQUIRED`, `SMART_REMAKE_INTAKE_REVISION_REQUIRED`, `SMART_REMAKE_INPUT_CHANGED`, `SMART_REMAKE_RIGHTS_REQUIRED`, `SMART_REMAKE_RIGHTS_EVIDENCE_REQUIRED`, `SMART_REMAKE_CHARACTER_CONSENT_REQUIRED`, `SMART_REMAKE_DISCLOSURE_REQUIRED`, `SMART_REMAKE_USE_STOPPED`, `SMART_REMAKE_REVISION_CONFLICT`, `SMART_REMAKE_IDEMPOTENCY_CONFLICT`, `SMART_REMAKE_OPERATION_BUSY`, `SMART_REMAKE_STAGE_BOUND_REQUIRED`, `SMART_REMAKE_MODEL_ATTEMPT_UNCERTAIN`, `SMART_REMAKE_ATTEMPT_RECONCILIATION_REQUIRED`, `SMART_REMAKE_INSPECTION_STALE|REPORT_INVALID|MEDIA_CHANGED|MEDIA_FORBIDDEN|HARD_BLOCK|UNAVAILABLE`. Exact budget/release codes follow their strict module guards.

## Checkpoints trước final qualification

Intake/policy/metadata 45 tests (96.54%); intake routes 14 HTTP tests; paid hooks 161 unit/regression (86.37% combined); immutable release helpers 48 tests (96.53%); Inspector bridge 27 tests (92.41%); analysis PG+HTTP 4 tests (96.59%). Các con số theo phạm vi riêng, có regression overlap; không cộng thành tổng toàn suite. Không paid calls hoặc commit/push.

## Quyết định pilot từ người dùng

Người dùng đã chọn: **Chuẩn bị pilot bằng media tự tạo; chưa gọi trả phí**. Chuẩn bị case self-authored/dev, quyền/hash rõ, kiểm thử API/worker/FFmpeg offline. Không đòi case seller thật để hoàn thành phần chuẩn bị; live paid run vẫn cần cap và server cost bounds cụ thể trước submit. `READY_FOR_LIVE_PILOT` chỉ mô tả code/pilot package được kiểm thử; không có kết quả `LIVE_VERIFIED` hoặc chất lượng live.

## Provenance v1 shape

`GET /projects/{id}/provenance` trả `{schemaVersion:"smart_remake_provenance_v1", project:{id,workspaceId,revision,status}, run:{caseId,runId,variant,configVersion,codeVersion,promptVersion}, inputs:[{role,assetId,mediaHash,mimeType,rights}], requirements,constraintsHash,policyHash,plan:{sourceSceneMap,renderPlan}, attempts:[{id,stage,purpose,status,provider,model,providerTaskId,requestHash,estimatedUsd,actualUsd,reservedUsd,costStatus,createdAt,submittedAt,completedAt,usage,receipt,error:{code}}], budget, scenes:[{id,activeVersionId,versions:[{id,mediaHash,technicalCheck,createdAt,renderGroupId,operationId,promptHash}]}], timeline, assemblies:{activeAssemblyId,records,history}, inspections:{reports,reviews}, release:{approvals,exports,activeApprovalId}, deletion, stageTimings:[{attemptId,stage,createdAt,submittedAt,completedAt}], failures:[{attemptId,stage,status,code}]}`. Thiếu versions/run metadata giữ null; actual chưa biết giữ null; không signedURL/objectkeys/providerpayload/secret/error text.

## M2 — BACKEND_INTEGRATED

Các route lifecycle đã mount vào router thật. `tests/integration/test_smart_remake_lifecycle_api.py`: **5 tests đạt** trên PostgreSQL isolated + FFmpeg, gồm intake→compile→render worker→compose→B Inspector→human review→approval→AI labeled export→restore→provenance→deletion. Chỉ fake physical Gemini/OpenAI/KIE/storage edges trong test; policy/reservation/jobs/fencing/typed Inspector không mock pass. Paid giả đều có committed ledger trước physical call. Chat B có thể chạy real API/browser; không chờ thêm backend mock.

Project thêm `inspectionSummary.currentReportIds` do server so snapshot/hash và active assembly; `inspectionMedia:[{mediaId,mediaHash,timebase,frameCount,url}]` authorized private previews cho source/product/character/raw/neighbor/final. Image clock=`image`; video clock=`source|raw_group|final`. Evidence phải match ID+hash+clock; lịch sử giữ nguyên. P0 phase=`intake|compiled|rendered`. Upload character thực tế phải xác nhận requiresCharacter=true trước paid/inspection/export, để tránh đánh N/A khi ảnh nhân vật được dùng; thiếu xác nhận trả `SMART_REMAKE_CHARACTER_POLICY_REQUIRED`.

Provider constructor seams dùng cho offline browser launcher: `budgeted_analysis.HttpGeminiClient` / `LedgerGeminiClient.client` (disable retries vẫn giữ), `engine.openai_images.OpenAIImageClient`, `engine.kie_client.KieClient` qua worker existing constructor; chỉ thay provider clients, giữ budget wrappers. Inspection `budgeted_analysis.inspection_invoke` trả mapping callback, bridge `_model_adapter` chuyển typed model request/result. Conditioning dùng `conditioning_inspection.inspection_invoke` nhưng vẫn phải đi real ledger khi fake physical Gemini.

Độc lập: 38 grouped/KIE/timeline PostgreSQL+FFmpeg regressions đạt; 31 budget/analysis/worker/readiness tests đạt 98.13%; 127 A3 scoped tests đạt 85.05%; release helpers/actions 65 unit+3 PG/FFmpeg đạt 94.59%; intake/API kết hợp 64 tests đạt93.91%. Không cộng các scope có overlap. Root regression/coverage/review đã đạt; còn chờ checkpoint browser của B để ghi readiness chung.

## Final A regression checkpoint

- **755 tests đạt trong169.30s, coverage94.50% trên32 modules /4003 statements**, 3 warnings deprecation422 từ middleware hiện có. `COVERAGE_FILE=/tmp/viraldy-p0-a.coverage`; lệnh coverage đầy đủ và module list tại [qualification](/Users/mac/Desktop/Viraldy/artifacts/smart-remake-p0/chat-a-prepared-20261125/qualification.md), machine-readable [qualification.json](/Users/mac/Desktop/Viraldy/artifacts/smart-remake-p0/chat-a-prepared-20261125/qualification.json) và [coverage.json](/Users/mac/Desktop/Viraldy/artifacts/smart-remake-p0/chat-a-prepared-20261125/coverage.json). Scope gồm unit prefixes `p0_lifecycle*`, `budget_ledger*`, `p0_rights*`, `release_policy*`, `p0_readiness`, `smart_remake*`; integration cùng prefixes A + `test_smart_remake_budget_ledger.py`/`smart_remake*`. Có PostgreSQL isolated, FFmpeg/FFprobe/Pillow và actual API/worker; chỉ physical provider giả. Không tuyên bố toàn backend/repo suite.
- **17 contract tests đạt**: `PYTEST_ADDOPTS=--no-cov make test-contract`. Đã sửa OpenAPI builder để tôn trọng schema examples cho USD string và conditional InspectionSubject. Target Make mặc định áp dụng coverage toàn backend cho contract-only nên dùng explicit no-cov; coverage chức năng đo riêng.
- Trong final coverage: timeline_compile93%, inspection presentation/router100%, new execution/mapping95%, các p0 modules còn lại92–100%. Full existing Gemini module70% do cả legacy retry/parser paths; helper+analysis assigned scope đo riêng96.79%, không tuyên bố từng file đạt80%.
- Scoped Ruff p0_*.py + timeline/router/repair + OpenAI/KIE clients/adapters + tests A đạt. Strict mypy kết hợp **31 source files đạt**. Full Gemini vẫn có Ruff S311/E501 và mypy no-any-return line61 từ baseline; giữ ngoài clean scoped claim, không sửa debt ngoài task. Scoped `git diff --check` đạt.
- Final GitNexus `detect_changes(scope=all)` phản ánh **toàn WIP chung A/B/nền**: 34 tracked changed files,299 mapped changed symbols,79 affected flows,risk critical. Không diễn giải đây là diff riêng A. `RepairService.present` CRITICAL2 direct/10 flows đã cảnh báo trước sửa; compile binding LOW1 direct/1 flow; HttpGeminiClient MEDIUM9 direct importers/17 affected symbols. New modules có impact UNKNOWN khi index chưa chứa symbol, đã trace callers và kiểm thử trực tiếp. Không commit/stage/push.

File ownership A đã thực hiện: new `p0_{contracts,intake,policy,metadata,budget,budget_models,analysis,paid,conditioning,assemblies,release,export_media,deletion,actions,execution,inspections,inspection_worker,inspection_mappings,worker,presentation,inspection_presentation,router,lifecycle_router,timeline_retention}.py`; integration hiện có trong `timeline_compile.py`, `timeline_service.py`, `repair_service.py`, `router.py`, `timeline_schemas.py`, `image_workflow.py`, `kie_workflow.py`, engine Gemini/OpenAI/KIE adapters; migration0024 và model/job/worker registration; tests prefixes A, legacy regressions cần cập nhật P0 fixtures; `scripts/check-smart-remake-readiness.py`, `.env.example` stage bounds và runbook. Giữ WIP nền và không sửa inspection/TypeScript/eval harness B.

Provenance additive v1: `planHistory:[{id,retiredAt,revision,plan,scenes,timeline}]` giữ cả candidate chưa ghép của plan cũ; metadata mode/model/prompt version chỉ có khi biết thực. Deletion inventory bao gồm plan cũ và thumbnail upload dở đã ghi nhận.

## Chuẩn bị pilot và cấu hình

Người dùng chọn media tự tạo, chưa gọi trả phí. Đã tạo/validate/replay bộ 3 case tự tạo: `/tmp/viraldy-p0-prepared.WftoQT/bundle.json`; report `/tmp/viraldy-p0-prepared.WftoQT/report/smart-remake-report.json` và `.md`. Đây là dev fixtures; không phải live result hay bộ BTC84. Lệnh tái tạo có trong [runbook](/Users/mac/Desktop/Viraldy/docs/runbooks/SMART_REMAKE_P0_PILOT.md).

Checker offline/readiness: 12 tests trong lượt riêng, bộ budget/analysis/worker/readiness kết hợp31 đạt98.13%. Cấu hình hiện tại paidExecution=blocked vì chưa có đầy đủ provider/storage/broker config và bốn server exposure bounds. Không in secret/signedURL, không gọi provider để kiểm tra config. Cần cung cấp bounds/cap và xác nhận case trước live paid run; việc này tách khỏi chuẩn bị offline đã được giao. Không commit/push.

## B4 metadata join — additive v1 approved

A chấp nhận **explicit case-manifest join** tại harness B cho caseId/runId/variant/code/config/prompt version và fixture-mode proof từ launcher kiểm soát physical providers. Ghép phải kiểm tra input roles/hashes/project/manifest; không ghi đoán vào runtime hoặc relabel fixture thành live. Không thêm client run-metadata mutation API cho P0.

Compile đã lưu `p0.runtime:{serverMode,executionMode}` tại fresh commit. Provenance v1 thêm `run.serverMode` (AI_MODE chuẩn hóa đã chụp) và `run.providerExecution`. `run.mode=fixture` chỉ khi executionMode=fixture; nếu đường provider được cấu hình live nhưng physical execution chưa xác minh thì mode=null/providerExecution=unverified. Server configuration không tự chứng minh provider thật. Thiếu version/case metadata giữ null; B nối manifest nhưng giữ missingness và server/runtime fields gốc.

Đã thêm regression zero-paid cho owned fixture/mock compile (không instantiate HTTP/Ledger client), route Inspector fixture/mock bị chặn trước queue. Worker defense cho fixture/mock đã đạt qualification. API offline qualification vẫn dùng AI_MODE=live với fake physical providers + ledger thật, phải capture là fixture/mock theo launcher proof.

## Final qualification follow-up

- Fixture/mock worker defense đã đạt 16 tests: chặn trước khởi tạo model/storage, giữ reconciliation cho attempt đã invoking; không gửi lại paid call khi restart trong offline mode.
- Đã chốt kiểm tra quyền sau submitted-marker commit, trước image/Veo POST; kiểm tra lại trước từng upload KIE reference. Ba regression test-first đạt; paid-owned suite 193 tests, coverage89.95%. Known-zero cancellation chỉ cho trusted local preflight chưa có task/usage/remote receipt; actual/unknown receipt vẫn giữ reservation. PostgreSQL cancellation/refusal tests đạt; review độc lập không thấy P1/P2.
- Broad checkpoint sau readiness/race fixes: **686 tests đạt, coverage95.55% trên26 modules A**, `COVERAGE_FILE=/tmp/viraldy-p0-a.coverage`; ba warnings422 deprecation. Scoped Ruff đạt; strict mypy27 source files đạt. Projection mapping bổ sung được kiểm thử riêng sau checkpoint này.
- B browser đã đạt full8s real API/worker/FFmpeg, MP4 192frames có nhãn AI, reload/restore và stale-approval block; capture/replay từ provenance/media thật giữ12 attempts, actual cost unknown và human ratings chưa đo. B đang chốt ma trận cuối, A không tuyên bố toàn P0 ready.
- `inspectionMappings` đã phát hành từ snapshot/report/assembly đóng băng cho scene_local↔raw_group và final↔raw_group: 19 mapping unit tests đạt95.08%, strict mypy/Ruff đạt, review độc lập không còn P1/P2. Không suy đoán source↔generated correspondence. Actual API5 tests đạt sau wiring; B nối affordance thật.
- Package fixture đã lưu bền tại `/Users/mac/Desktop/Viraldy/artifacts/smart-remake-p0/chat-a-prepared-20261125/bundle.json` (Git ignored); validate/replay bằng harness hiện tại đạt. Không thay package B hoặc quyền provider-use; đây là offline-only development cases.

## Inspector clock mapping — additive v1 contract locked

GET project bổ sung `inspectionMappings:[{from:{mediaId,mediaHash,timebase,inFrame,outFrame},to:{...},sceneId,versionId,assemblyId?,reportId?,contextHash?,manifestHash?}]`. Chỉ có mapping tuyến tính bằng độ dài trên24fps từ frozen assembly manifest hoặc range của persisted scene report; giữ binding riêng cho mỗi assembly/report/range, không dùng draft hiện tại để sửa lịch sử. Source evidence dùng source clock trực tiếp; không suy đoán source↔generated frame alignment.

`inspectionMedia` bổ sung virtual scene-local descriptor `{mediaId:"scene-local:<binding-hash>",mediaHash:<retained raw hash>,timebase:"scene_local",frameCount:<selected length>,url:<authorized raw URL>,playbackTimebase:"raw_group",playbackMediaId:<raw ID>,playbackMediaHash:<raw hash>}`. **URL chứa raw bytes**: UI phải resolve virtual evidence qua mapping sang playbackTimebase trước khi phát; không seek local0 trên rawURL. Virtual mediaId duy nhất theo snapshot+scene+version+range tránh nhầm offset khi dùng chung raw clip. Không có authorized raw descriptor/bounds/hash thì bỏ virtual descriptor và mapping không thể resolve. **Projection đã có trên server**; 16 mapping/presentation unit tests đạt, review độc lập không thấy P1/P2. API regression đang chạy lại cùng final provenance refinement.

Consumer phải chọn mapping đúng reportId/assemblyId + scene/version/range; không chuyển raw→scene_local theo raw hash đơn lẻ khi nhiều historical contexts dùng chung raw clip. Không cần scene_local descriptor trực tiếp từ Inspector: UI có thể cung cấp affordance từ mapping của report đang xem, giữ exact binding và không dựng finding mới.

## Genuine execution provenance — integrated

Execution evidence chỉ do physical HTTP clients tạo từ owned verified TLS response và receipt, qua internal typed boundary rồi bind attempt/provider/model/requestHash. Client JSON, intake metadata, AI_MODE và fake transport không được nâng thành live. `p0.runtime.compileOperationId` đã bind plan hiện tại với analysis operation thật (21 compile regressions đạt). Provenance classifier đã tích hợp: có thể phát `run.mode=live` cho run đủ bằng chứng, bound current compile; missing/mixed giữ null. Không cần B nới guard capture hoặc relabel offline E2E. Gemini/shared helper, OpenAI/KIE và provenance integration đã đạt offline tests; chưa gọi provider trả phí để tạo bằng chứng live.

Nominal witness dùng một intent duy nhất, physical-client identity + per-invocation reset ngăn fake client mượn proof cũ. Public receipt/task/request IDs dùng định dạng bounded identifier; monetary receipt validate USD riêng. ProviderResponseHash/TLS witness không tự xác nhận actual USD hoặc chất lượng. Metadata run thiếu vẫn giữ null và explicit case-manifest join đã phê duyệt ở trên.

Known KIE creation proof giữ qua polling cùng task; GET-only proof không nâng một fake/unknown creation thành live. HTTP rejection/invalid JSON/invalid media vẫn giữ physical-response proof nếu đã có; timeout chưa response không có proof, cost vẫn unknown. Public factory replacement trước import, subclass, replaced method, forged JSON và borrowed witness đều không nâng mode.

Kiểm chứng refinement: paid-owned211 tests90.29%; helper/analysis18 tests96.79%; release93 tests95.22%; mapping19 tests95.08%; review độc lập không còn P1/P2. Scopes overlap, không cộng. Actual API5 tests đạt với asserts mapping equal-length/authorized endpoints/virtual playback và fake physical execution giữ mode=null/providerExecution=unverified. Final broad32-module run đã đạt755 tests94.50% như trên.

## M3 — READY_FOR_LIVE_PILOT (A code/prepared offline)

Backend A1–A5 đã qua qualification, B có API/worker/Inspector thật để kiểm tra. Media/report/lệnh tái chạy được giữ trong [prepared package](/Users/mac/Desktop/Viraldy/artifacts/smart-remake-p0/chat-a-prepared-20261125/bundle.json), runbook tại [SMART_REMAKE_P0_PILOT.md](/Users/mac/Desktop/Viraldy/docs/runbooks/SMART_REMAKE_P0_PILOT.md). `readiness.json` giữ kết quả configuration_blocked/paidExecution=blocked, đúng yêu cầu chưa gọi trả phí.

Các giới hạn còn lại: thiếu private storage/broker config và bốn server exposure bounds; chưa có case/cap được giao chạy paid, provider model entitlement/real billing/semantic quality chưa xác minh. KIE credential đã được cấu hình/xác thực ở checkpoint dưới. Để trống giới hạn trong **gói chuẩn bị offline** không gỡ finite budget guards của runtime live. B5/frontend/browser và official BTC protocol/batch84 vẫn có checkpoint riêng; không coi toàn P0 đã READY hoặc LIVE_VERIFIED.

Deletion chỉ xác minh registered inventory; provider-side retention chưa kiểm chứng, signed links đã cấp có thể còn tới expiry/object deletion, hard termination giữa upload và inventory write có thể để lại orphan chưa đăng ký. Chi tiết vận hành nằm trong runbook. Không paid generation hoặc commit/stage/push; credential chỉ bổ sung khi người dùng giao riêng ở checkpoint KIE dưới.

## KIE configuration checkpoint — 25/11/2026

Theo yêu cầu mới, đã thêm KIE_API_KEY do người dùng cung cấp vào private `apps/backend/.env`, Git-ignored, mode0600; không ghi key vào source, skills, lockfile hoặc docs. Không sửa credential khác. API/worker/beat và Compose đã dùng envfile này; không cần thay KIE client/model pipeline.

Đã cài chính thức `kie-models` và `kie-chat-agents` cho Codex tại `.agents/skills/` bằng `skills@1.9.0`, khóa source/digest trong `skills-lock.json`; `skills list --agent codex` nhận cả hai, `node --check` CLI đạt. Hướng dẫn dotenv CLI ở runbook; giữ model provider hiện hành.

Đã kiểm tra local environment/KieClient nhận key và authenticated GET `https://api.kie.ai/api/v1/chat/credit`: HTTP200/provider code200, có credit. Chỉ đọc account metadata, zero generation tasks. 78 offline KIE/boundary/workflow/mode regression tests đạt. Checker P0 giờ đánh dấu KIE_API_KEY configured; các storage/broker/exposure-bound gaps còn giữ paidExecution=blocked. Không commit/push.

## Local runtime và pilot0,50USD — 25/11/2026

Người dùng đổi yêu cầu sang chạy thử thật bằng fixture chiếc chai, rồi chốt **chỉ một video, tổng tối đa0,50USD**. Sau khi được giải thích full pipeline còn OpenAI/Gemini chưa chứng minh nằm trong trần, người dùng chọn **một video KIE riêng; chưa coi là E2E Smart Remake**. Không nới contract hoặc hạ server bounds để ép full pipeline vào cap. Không có quyền chạy nhiều video, repair hoặc retry paid intent.

Runtime native đã lên: API `http://127.0.0.1:8000`, web `http://localhost:5173/smart-remake`, solo worker. Giữ PostgreSQL dev57432, nâng0023→0024 không reset; Redis riêng26379, MinIO19000 với bucket mới/private `viraldy-p0-live`. Backend.env giữ mode0600, có storage/broker và bốn operator bounds0,50/2,00/1,00/0,50USD cho analysis/image/video/inspection. API/worker đã restart; health/ready và health/worker đều200. Checker configuration_ready không phải live execution proof. OpenAI/Gemini list-models và KIE account đều authenticated; chưa gọi generate/analyze/inspect trả phí.

Bộ input-only tự tạo của B được giữ nguyên. Đã derive tám giây đầu của source16s thành192frames/24fps và ghi transform/hash riêng. Runner full lifecycle có zero-HTTP budget preflight, không thể chạy với cap0,50USD và các bounds hiện tại. Runner KIE riêng dùng schema/catalog hiện hành `veo-3-1` / `veo3_lite`, reference-to-video720p8s9:16, write-ahead marker và khóa một lần trước createTask; không thể dùng kết quả riêng này để nâng provenance Smart Remake thành live.

KIE preflight hiện báo **24credits**, cần **30credits** (catalog0,15USD) cho một video; thiếu6credits. Đã dừng trước upload/createTask: **zero generation tasks, chưa phát sinh phí generation**. Giá catalog không phải actual USD receipt. Authorization0,50USD/một video được giữ để tiếp tục sau khi đủ credit; không yêu cầu duyệt lại cùng phạm vi. Logs/private account/case/scripts/status nằm ngoài Git tại `/Users/mac/Desktop/Viraldy/artifacts/smart-remake-p0/live-pilot-20261125/`; không ghi key/token/signedURL vào docs. Chụp UI thật không submit paid actions; không dùng demo output làm live evidence.

## Policy page và modal xác nhận — 25/11/2026

Theo yêu cầu mới, trang công khai `/policies/media-rights` mô tả quyền tư liệu, đồng ý hình ảnh nhân vật, xử lý qua Gemini/OpenAI/KIE và kiểm tra đầu ra. Smart Remake dẫn sang trang này bằng tab mới; modal có hai checkbox mặc định bỏ trống. Lưu xác nhận không tự phân tích hoặc tạo video. Bằng chứng/giấy phép/ghi công chuyển thành mục tùy chọn; quyền nhân vật và ngân sách vẫn có gate riêng.

Contract bổ sung `attestation` phiên bản `smart-remake-media-rights-v1` và basis `attested` cho source/product. Server lưu actor, thời điểm và câu cam kết chuẩn với trạng thái declared; không coi đây là verified. Không tự bịa phạm vi, bằng chứng hoặc quyền sở hữu. Thiếu/thu hồi/sai phiên bản bị chặn; thay tư liệu yêu cầu xác nhận lại. Serializer bỏ trường attestation khi vắng mặt để giữ nguyên hash và replay của intake cũ. Không endpoint backend mới hoặc migration SQL.

Qualification: 1.008 tests backend/77 files và 397 tests frontend/32 files đạt; coverage ba module backend sửa100%, logic intake/modal/P0 frontend96,62% statements và91,79% branches. Mypy, typecheck, scoped Ruff/ESLint và web build đạt. Browser xác minh policy đọc được khi chưa đăng nhập, modal chưa tick không lưu, Escape trả focus đúng nút mở và giữ media. API/worker live đã restart; web ở `http://localhost:5175/smart-remake` vì5173 thuộc ứng dụng khác. Artifact: `artifacts/smart-remake-p0/policy-modal-20261125/verification.json`, kèm ảnh policy/modal. Không gọi AI trả phí, không tự xác nhận điều khoản thay người dùng, không commit/push; full live E2E chưa được chứng minh bởi đợt sửa này.


## Quy ước tên theo chức năng — 25/11/2026

Đã bỏ nhãn ưu tiên khỏi tên implementation: 24 module backend, 7 file frontend, 47 file test unit/integration và 10 file harness/readiness dùng tên chức năng. Ví dụ: `project_intake.py`, `budget_ledger.py`, `conditioning_inspection.py`, `project_lifecycle.py`, `remake-project-inputs.tsx`. Danh sách ánh xạ đầy đủ nằm trong `artifacts/smart-remake/naming-cleanup-20261125/*name-map*.json`. Các tên P0 trong phần lịch sử và kế hoạch vẫn thể hiện phạm vi giao việc lúc đó.

`context_json["p0"]`, biến môi trường ngân sách, định danh task và phiên bản contract/cache cũ được giữ nguyên để tương thích. Không migration, thay payload, gọi provider hoặc thay logic generation. `AGENTS.md` quy định tên implementation phải mô tả chức năng; nhãn ưu tiên thuộc tài liệu công việc.

Kiểm chứng: 1.008 backend tests/77 file và 564 frontend tests/44 file đạt; coverage contract backend 98,99%. Ruff/mypy đạt cho 24 module đổi tên; frontend scoped lint, typecheck và build đạt. Đối chiếu AST backend/frontend/harness và 110 so sánh serialization không ghi nhận thay đổi hành vi. Các cảnh báo lint có trước được ghi trong báo cáo, không sửa ngoài phạm vi. Đã restart API/worker riêng của dự án, kiểm tra readiness/worker HTTP 200 và màn intake trong browser. Không chạy lại browser E2E đầy đủ; collect được 9 browser/recovery cases với tên mới. Báo cáo: `artifacts/smart-remake/naming-cleanup-20261125/verification.json`.


## Xác nhận theo hành động Smart Remake — 26/11/2026

Đã triển khai Chọn tư liệu → Duyệt kịch bản → Xem & hoàn thiện. CTA không bị khóa vì thiếu ngân sách/quyền: tư liệu hợp lệ mở modal theo hành động; thiếu tư liệu có lỗi cạnh trường và focus vào nút chọn file. Cấu hình, chia nhóm và prompt nằm trong Nâng cao. CTA đổi sang Cập nhật kịch bản khi mốc cắt/nhóm hoặc contract cũ cần chuẩn bị lại.

Endpoint đọc `POST /api/v1/workspaces/{workspace_id}/smart-remake/preflight` kiểm tra quyền workspace và suy ra dự phòng từ plan/ledger/cấu hình server. Không upload, ghi DB, reserve hay tạo provider client. Modal phân biệt phí đã xác định với reservation chưa rõ phí; đề xuất trần dự án cộng dồn và cửa sổ tính từ startedAt. Chỉ snapshot requirements/rights/budget đã xác nhận được truyền xuyên suốt thực hiện. Confirm kiểm tra lại preflight; context/revision đổi phải xác nhận lại; tác vụ pending/uncertain chỉ đối soát. Giữ provider, compiler, GenerationExpectations, generation payload và SQL schema.

Nghiệm thu offline: **1.049 backend tests** và **614 frontend tests** đạt; coverage preflight93,95%, action gate/helpers94,23%, modal95,38% statements. Ruff/strict mypy backend mới, lint Smart Remake, whole-web typecheck và build đạt. Full-web lint còn393 lỗi định dạng/9 warnings ở các file nguyên vẹn so với baseline; không sửa ngoài phạm vi. Browser fixture qua phân tích, tạo clip, tạo lại cảnh, kiểm tra AI; mở/hủy cập nhật không submit. Ba bước không tràn ngang ở390/768/1280/1440px; footer mobile không che nội dung; Escape trả focus đúng nút mở.

Bằng chứng tại `artifacts/smart-remake/action-confirmation-20261125/verification.md` và `verification.json`, kèm ảnh ba bước/các modal, baseline/diff review và ledger fixture. Fixture dùng media tự tạo, fake physical providers và chặn mạng ngoài; actual USD chưa xác định vẫn giữ exposure. Đây không phải chất lượng model thật hoặc live paid E2E. API/worker runtime chính đã refresh an toàn (0 tác vụ active), health200, endpoint mới trả401 khi chưa đăng nhập; web tại http://localhost:5175/smart-remake. Không generation trả phí, migration hay commit/push trong đợt sửa.
