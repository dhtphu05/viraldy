# Smart Remake P0 — bàn giao cho hai cuộc trò chuyện Codex

Ngày: **25/11/2026**. Thực hiện theo [Viraldy Smart Remake trên Notion](https://app.notion.com/p/42342dfd177f8073b8d1ce5ab6b52208), snapshot trang cập nhật `2026-11-25T07:48:56.934Z`, được đọc đầy đủ trong lượt lập handoff.

Tài liệu này là **contract phối hợp và phân công cho SR-01…SR-10 của Notion**, cụ thể hóa [backlog V2](smart-remake-v2-task-breakdown.md). Không đổi mã SR của Notion thành mã V2 của backlog. Chỉ hai luồng thực thi chính; mỗi luồng có thể dùng subagent trong phạm vi file của mình.

## Mục tiêu bàn giao

Hoàn thiện P0 để chạy thử thực tế: seller đưa source/sản phẩm/nhân vật có quyền → xác nhận yêu cầu và timeline → tạo → chọn đoạn → ghép preview → kiểm tra → sửa riêng cảnh → kiểm tra lại → duyệt và tải đúng thành phẩm. Có giới hạn ngân sách, quyền/xóa dữ liệu, nhãn AI và evidence truy vết.

Phân biệt hai mốc: **Ready for live pilot** là code thật đã nối, offline E2E đạt, input có quyền và trần chi phí đã chuẩn bị; **Live verified** cần output/provider receipts thật cùng đánh giá của người. Hoàn tất code không tự chứng minh chất lượng AI. SR-10 ở mốc đầu phải có harness/capture/replay dùng được; chưa cần chạy toàn bộ 84 ca trước pilot nhỏ.

**Không thuộc P0:** Shot Builder/editor ảnh riêng, tạo biến thể hook/CTA, Brand Kit mới, caption/logo editor, thêm tỷ lệ xuất, voice, video-edit, upscale, dự báo doanh thu hoặc tự động đăng quảng cáo. Luồng GPT Image đã có tiếp tục hoạt động; kiểm tra ảnh điều kiện bên trong pipeline không mở rộng thành công cụ Shot Builder P1.

## 1. Baseline đã kiểm chứng

- Repo: `/Users/mac/Desktop/Viraldy`, branch `feat/assets`, HEAD `b68d34d`, kèm WIP tracked/untracked hiện tại. Có cả thay đổi Creative Library ngoài scope; không nhận các thay đổi đó vào task.
- Đã có KIE Veo Lite, direct OpenAI Images, grouping, Timeline v2, candidate/accept, trim và FFmpeg compose. Giữ lại, chỉ hoàn thiện phần thiếu.
- Cấu hình source hiện hành: `veo-3-1` / `input.model=veo3_lite`; ảnh `gpt-image-2.6-sunburst`, quality `max`, complexity `high`, PNG `720x1280`, `n=1`. Đã đối chiếu tài liệu [OpenAI](https://developers.openai.com/api/docs/guides/image-generation) và [KIE](https://docs.kie.ai/veo3-api/generate-veo-3-video/) ngày 25/11; quyền tài khoản và output live chưa được kiểm chứng. Không đổi profile của plan/job cũ.
- Source mới hơn phần Đợt 1 Fast/mỗi cảnh một task trên Notion. Làm theo ghi chú cập nhật Lite/OpenAI của trang; giữ grouping hiện có như phương án cần pilot, không coi ít call là đã tiết kiệm. `renderGroupBreaks` cho phép tạo riêng để đối chứng; không thêm provider video khác.
- Invariants: output 9:16, 24 fps, 192/384 frame; 1–4 cảnh nguồn, mỗi cảnh ≤192 frame. Cảnh, nhóm sinh và đoạn sử dụng là ba miền khác nhau; không tự gộp/bỏ cảnh logic hoặc thay tốc độ. Mỗi clip thô hiện yêu cầu tám giây, không mặc định hỗ trợ bốn giây.
- Kết quả nền: **323 unit tests** từ lượt trước, **34 integration tests** hiện có và **1 integration test migration mới** đạt. Integration dùng PostgreSQL Docker + FFmpeg/FFprobe thật, provider giả; không đo coverage trong các lượt `--no-cov`.
- Test migration mới: `apps/backend/tests/integration/test_smart_remake_migration_upgrade.py`; kiểm tra bảo toàn user/workspace/job/JSON qua `0022 → head → 0022 → head`. Downgrade xóa bảng feature theo thiết kế; không cam kết bảo toàn dữ liệu Smart Remake qua downgrade.
- Ruff và mypy đạt trên bảy file ảnh/KIE/schema/planner/compile được kiểm tra. Ruff toàn module Smart Remake còn **629 lỗi nền** ở cả code cũ; không tự format/refactor toàn module hoặc báo lint toàn repo đã sạch.
- GitNexus đã refresh trong lượt này. Trước sửa symbol vẫn phải chạy impact, báo direct callers/processes/risk và nêu HIGH/CRITICAL trước sửa; refresh lại nếu source đã đổi. Không suy “không có flow” là không có caller.

## 2. Hai workspace và quyền sở hữu

Mở **hai chat Codex Local cùng folder repo hiện tại**, dùng hai prompt liên kết ở cuối. Cách này giữ được WIP chưa commit và cho hai bên đọc handoff của nhau. Không tự tạo worktree từ HEAD: worktree đó sẽ thiếu baseline đang dùng. Nếu chuyển sang worktree về sau, phải mang đủ WIP/untracked qua một baseline có kiểm chứng trước.

| Phạm vi | Chat A — Runtime/API/policy | Chat B — Inspector/UI/evidence |
| --- | --- | --- |
| Backend hiện có trong `modules/smart_remake/` | Sở hữu toàn bộ, trừ thư mục `inspection/` mới | Chỉ đọc |
| `modules/smart_remake/inspection/` mới | Chỉ import/tích hợp public API | Sở hữu contract, core, provider adapter và tests |
| Router, schema lifecycle, DB models/migrations, jobs/worker/storage, gateway registration/config | Sở hữu các thay đổi cần cho P0 | Chỉ đọc; đề xuất trong handoff B |
| Frontend Smart Remake, `shared/api/smart-remake.ts`, `use-remake-studio.ts` | Chỉ đọc | Sở hữu toàn bộ TypeScript liên quan P0 |
| `evaluation/smart_remake/`, backend `evaluation/smart_remake/`, script eval/pilot mới | Cung cấp capture/ledger, không sửa harness B | Sở hữu manifest, validator, runner/replay/report |
| Tests mới | Prefix `test_p0_lifecycle*`, `test_p0_budget*`, `test_p0_rights*`, `test_p0_release*`; tests runtime hiện có | Prefix `test_p0_inspection*`, `test_p0_evidence*`; frontend và browser E2E mới |
| `.env.example`, Makefile, runbook backend, migration số kế tiếp | Sở hữu | Chỉ đọc; đề xuất biến/lệnh cần thêm |
| Handoff tiến độ | Tạo và cập nhật `smart-remake-p0-chat-a-status.md` | Tạo và cập nhật `smart-remake-p0-chat-b-status.md` |

Các đường dẫn không ghi đầy đủ ở bảng nằm dưới `apps/backend/src/viraldy/`, `apps/backend/tests/` hoặc `docs/implementation/` theo ngữ cảnh. Không tự sửa file ngoài ownership để “giúp tích hợp”; ghi yêu cầu vào status của mình rồi tiếp tục phần độc lập. A là integrator backend; B là integrator frontend. A sở hữu chỉnh sửa contract chung trong **tài liệu này** sau khi bắt đầu; B đề xuất thay đổi trong status B. Đổi contract phải kèm version, lý do, consumer bị ảnh hưởng và cập nhật tests; không đổi âm thầm.

## 3. Ma trận task bám P0 Notion

| Task | Owner | Deliverable / nghiệm thu | Trace Notion |
| --- | --- | --- | --- |
| A1 — Intake, yêu cầu và input | A; B làm form | Tạo owned intake trước paid analysis; snapshot yêu cầu giữ/thay/cấm/claims, source/product/optional character asset, quyền/consent và cap. Kiểm tra luồng nhân vật thật sự nhận ảnh khi case cần, không chỉ có tên trong prompt. | SR-01, 08 |
| A2 — Ngân sách và attempt ledger | A | Reserve atomic trước mọi paid call, limits/reconcile, usage/cost/timestamps/task IDs; đủ dữ liệu cho UI và evidence B. Unknown receipt không resubmit. | SR-07, 09, 10 |
| A3 — Lifecycle, scene repair và lịch sử | A | Giữ timeline/grouping/trim hiện có; immutable assemblies, restore, candidate chỉ áp dụng theo quyết định; invalidation checks/approval đúng phạm vi. | SR-02, 03, 04, 07 |
| A4 — Quyền, release/export và xóa | A | Backend chặn thiếu quyền/hard failures, duyệt đúng hash, label AI trong bản xuất, signed export qua gate, xóa/ngừng dùng theo dependency và báo giới hạn provider. | SR-06, 08 |
| A5 — Nối Inspector và vận hành | A | Đăng ký public API/worker B, resolve media có quyền, persist report/review, cấp budget wrapper cho VLM; runbook và readiness cho pilot. | SR-05, 06, 09, 10 |
| B1 — Contract/core Inspector | B | Typed input/report/finding, validate evidence, four-state results, reference/trim/neighbor binding; deterministic checks và fixtures trước. | SR-01, 05 |
| B2 — Inspector nội dung | B | API đa phương thức thật qua wrapper A, kiểm tra raw group/selected ranges/final MP4; product/character/action/structure/claims; đo coverage quan sát và uncertainty. | SR-05, 07 |
| B3 — Seller workflow | B | Form yêu cầu/quyền, source/current/candidate, evidence seek, trim vs content approval riêng, progress/budget, fix/restore/export gates và reload. | SR-01…09 UI |
| B4 — Harness và evidence | B | Case register, protocol version, blinded ratings, capture joins/replay/report; runnable dev pilot, preserved failures/costs. | SR-10, BTC-02 |
| B5 — E2E và live-pilot readiness | B điều phối; A sửa runtime | Ba ca đạt/cần sửa/bị chặn; hành trình thật qua API/worker/FFmpeg với fake providers; tài sản đủ quyền, live mode rõ ràng và budget cap sẵn sàng. | SR-01…10 |

Character là input tùy case, không được lấy chính sách consent từ prompt. Khi thêm character reference, A phải chốt phân bổ reference dưới giới hạn API và ghi trong plan/hash; không tự thêm ảnh thứ tư vào KIE hoặc bỏ ảnh sản phẩm. B kiểm tra fidelity/consent theo case có nhân vật; case không có nhân vật ghi N/A, không bịa điểm.

## 4. Contract chung v1 để bắt đầu song song

Đây là **contract cần triển khai**, không phải mô tả API đã có. Giữ response envelope/auth/workspace prefix hiện tại: `/workspaces/{workspace_id}/smart-remake`. UUID dạng string; timestamp UTC ISO; frame nguyên trên lưới 24 fps, khoảng `[inFrame,outFrame)`. Không nhận object key, URL hoặc timing có quyền quyết định từ client thay cho plan/media server đã lưu.

### Lifecycle và các endpoint tích hợp

GET project giữ các field v1/v2 đang có; bổ sung các nhóm `requirements`, `rights`, `budget`, `inspectionSummary`, `assemblies`, `release`. B quản lý TypeScript tương ứng; A quản lý wire response/backend validation. Mutations có `expectedRevision` và `idempotencyKey`; replay cùng key/payload trả kết quả cũ, khác payload trả conflict theo convention hiện có.

**Luồng đầu tiên phải có intake trước model:** `compile_timeline_request()` hiện phân tích source trước khi persist project. Chốt bổ sung `POST /projects` tạo draft **không gọi AI**: nhận input upload/owned asset refs cùng requirements ban đầu, rights/disclosure acknowledgement, budget cap và idempotencyKey; server lưu media private/hash và trả project ID/revision với phase intake. Không yêu cầu có SceneMap hoàn chỉnh ở phase này. B thực hiện prepare → tạo intake → gọi `/compile` bằng project ID đã sở hữu; A validate media/hash/quyền/cap và reserve analysis attempt trước mọi remote analysis. Payload compile không được thay input khác với intent đã duyệt. Requests live trực tiếp vào `/compile` thiếu intake hoặc không đủ quyền/ngân sách bị chặn trước provider; không để đường legacy trở thành bypass. Fixture/plan cũ giữ tương thích nhưng paid work mới phải qua gate. Quyền/budget chỉ lưu sau compile là không đạt SR-08/09.

| Interface cần hoàn thiện | Owner backend | Ý nghĩa |
| --- | --- | --- |
| POST `/projects` | A | Owned private intake và snapshots quyền/disclosure/cap trước lần analysis đầu; không gọi AI |
| PATCH `/projects/{id}/requirements` | A | Requirements và owned asset references đã xác nhận; thay đổi tạo context mới |
| PATCH `/projects/{id}/rights` | A | Nguồn/căn cứ/phạm vi/consent/attribution, trạng thái khai báo vs đã kiểm tra |
| PATCH `/projects/{id}/budget` | A | Trần tiền/lượt/thời gian theo policy; sửa cap không đổi intent đã submit |
| POST `/projects/{id}/inspections` | A gọi public module B | Queue inspect subject đã lưu; không nhận finding/QA conclusion do client tự cấp |
| POST `/projects/{id}/inspection-reviews` | A | Actor xác nhận/bác bỏ finding, có lý do và đúng report/context; không bỏ qua hard block |
| POST `/projects/{id}/restore` | A | Khôi phục assembly lịch sử bằng operation mới, giữ parent/history |
| POST `/projects/{id}/approvals` | A | Content/release approval cho đúng assembly và report context |
| POST `/projects/{id}/exports` | A | Kiểm tra lại release/rights, trả signed file AI-labeled của đúng assembly |
| POST `/projects/{id}/deletions` | A | Ngừng dùng/xóa có trạng thái, dependency và kết quả kiểm tra được |

Giữ `/publish` hiện có là **compose preview riêng tư**, không biến thành duyệt xuất. Cần compose trước để Inspector xem bản cuối. `RepairService.present()` hiện cấp `downloadUrl` trực tiếp: A phải nối/bỏ đường cấp export vượt gate này; B không chỉ thêm nút disabled rồi coi backend đã an toàn. Preview URLs phục vụ review theo quyền; không hứa ngăn người đã có quyền xem lưu bytes hoặc thu hồi file đã tải.

A ghi ví dụ request/response và error codes cụ thể vào status A tại checkpoint M1; B đối chiếu với bảng này. Nếu cần điều chỉnh endpoint do kiến trúc thực tế, A cập nhật contract trước, không tạo hai cách gọi khác nhau. B dùng typed fixtures/mocks trước khi server hoàn tất, và phải tháo mock ở đường live khi tích hợp.

### Inspector public API do B sở hữu

Module `modules/smart_remake/inspection/public.py` cung cấp async entry `inspect_subject(subject, media, references, constraints, invoke_model) → InspectionReport` và các typed contracts. `subject`/constraints do A lấy từ snapshot có quyền; bytes/reference server-owned được A resolve. `invoke_model` là callable do A cung cấp, bọc budget reservation, attempt receipt, usage và timeout. B không tạo một đường VLM live bỏ qua ledger, không giữ DB session xuyên remote call và không tự ghi vào lifecycle JSONB của A.

Report tối thiểu: `id`, `schemaVersion`, `subject`, `status`, `checkedAt`, `checkerVersion`, `rubricVersion`, `modelProfile`, `constraintsHash`, `manifestHash`, `coverage`, `findings`. Subject chứa `kind: image|scene|assembly`, `projectId`, scene/version hoặc assembly ID thích hợp, `mediaHash`, `range` khi có timeline và neighbor version IDs khi kiểm tra continuity. A kiểm tra lại binding trước lưu và trước release; B cung cấp validator dùng chung. Không dùng revision tăng theo progress thay cho hash của nội dung.

Finding tối thiểu: `id`, `requirementId`, `category`, `expected`, `observed`, `status`, `severity`, `evidence`, `suggestedAction`. Status report/finding: `passed|failed|needs_review|insufficient_evidence`. Evidence định danh media/hash và frame range trong **clock của media đó**, ảnh thì tham chiếu evidence asset có thật, không tạo timestamp giả. Source clock, raw-group clock, scene-local clock và final clock phải có mapping rõ cho UI.

LLM chỉ đề xuất findings; backend/rules quyết định `blocking`. Evidence vượt media, sai hash, không tồn tại hoặc không đủ coverage không được pass. Có che khuất hoặc model/checker lỗi phải thể hiện uncertainty; không có findings không tự đồng nghĩa đã kiểm tra đạt. Dùng ảnh sản phẩm/nhân vật gốc để đối chiếu, không chỉ ảnh AI trung gian. Kiểm tra ảnh conditioning theo constraints trong pipeline hiện có nếu dùng ảnh đó trước Veo, không thêm Shot Builder UI P1.

Gate offline ban đầu dùng hard checks và người duyệt trên fixtures/bộ có nhãn. Pilot live hiệu chỉnh semantic checker cho version tiếp theo, không tạo vòng phụ thuộc bắt offline E2E chờ kết quả pilot. B báo checker false positive/negative khi có nhãn; không tự đặt một “điểm chất lượng” thay quyết định người.

### Budget, provenance và release

- Budget/attempt: stage `analysis|image|video|inspection|compose`, purpose `initial|repair|recheck`, intent/request hash, provider receipt, status, timestamps; amount USD dùng decimal string hoặc null, `estimated|actual|unknown` riêng. Reservation chưa rõ billing giữ trạng thái cần đối soát; never unknown=0. Tính cả thất bại và sửa; poll/trim/compose không tạo request ảnh/video.
- Provenance A xuất cho B: case/run/variant/config/code/prompt/model versions, input hashes/rights, plan/group/scene IDs, all attempts và stage timings, raw clip hashes, versions/selected ranges, assembly hashes, inspection/review/release, cost và failures. B không phải đọc schema nội bộ operation JSON bằng suy đoán; A cung cấp adapter/export có version.
- Release bind: assembly ID + media/manifest/constraints hashes + inspection/rubric/policy context + actor/time. Đổi media/trim/constraints/neighbor liên quan làm stale các kết quả tương ứng; output cũ và lịch sử vẫn giữ. Unknown semantic cần review theo policy; hard technical/rights failure không vượt bằng “đã xem”. File xuất có nhãn AI thực trong media theo policy, không chỉ badge trong UI.
- Assets: nguồn/product/character/audio đều thuộc policy quyền; riêng tư theo workspace. Thu hồi/xóa phải kiểm tra shared clip/cache dependencies, jobs đang chạy và evidence retention; báo phần Viraldy đã xử lý, không tự tuyên bố provider đã xóa.

## 5. Checkpoint phối hợp

**M0 — Bắt đầu ngay:** A/B ghi baseline phạm vi mình và trạng thái `IN_PROGRESS` trong status riêng. Cả hai đọc contract này và status chat kia trước mỗi checkpoint. Không cần chờ bên kia mới làm tests/core độc lập.

**M1 — Contract có ví dụ:** B giao typed Inspector/public API và fixtures pass trước; A giao lifecycle/budget/provenance request/response examples. Hai bên ghi `CONTRACT_READY` vào status của mình. Nếu có khác biệt, bên sở hữu contract sửa và ghi version; bên còn lại tiếp tục task độc lập trong lúc chờ.

**M2 — Nối thật:** A tích hợp B vào route/worker/persistence/budget; B thay mock bằng API thật và hoàn thiện review/export. Không đánh dấu xong khi chỉ có stubs, fixtures hoặc màn hình. B chạy E2E sau khi đọc `BACKEND_INTEGRATED` của A; A sửa lỗi runtime, B sửa UI/Inspector/evidence trong ownership.

**M3 — Ready for live pilot:** có đủ checklist phần 6, report checks và runbook. A/B ghi `READY_FOR_LIVE_PILOT` cùng hạn chế còn lại vào status của mình. Cần cả hai đạt; một chat xong không có nghĩa toàn P0 xong. Chưa gọi paid generation chỉ vì test script có mode live; batch pilot cần input và trần chi phí được người dùng giao chạy cụ thể.

Status của mỗi chat ghi: contract version, task đang làm/đã nghiệm thu, file đã đổi, commands/results, yêu cầu phía kia và next independent task. Không ghi secrets hoặc signed URLs. Không polling liên tục; kiểm tra lại ở ranh giới task, tiến hành việc độc lập. Nếu không còn việc độc lập mà contract chưa có, báo rõ dependency còn thiếu, không dùng implementation giả để tuyên bố hoàn tất.

## 6. Nghiệm thu chung trước thử thực tế

| Nhóm | Checks bắt buộc |
| --- | --- |
| Media/timeline | `2+6` và `3+5+4+4`; 192/384 frame, audio cùng trim; VFR/khác fps, cuối clip hợp lệ và vượt một frame; 8 giây dùng toàn clip không slider giả; không stretch/freeze để bù |
| Lifecycle | Double Generate, duplicate delivery, timeout sau có thể accepted, restart, poll/download/store fail, hai tab revision conflict; không paid resubmit mù; giữ video cũ khi compose lỗi |
| Inspector | Product/character/action/structure theo yêu cầu; sai cut/thiếu footage; evidence đúng hash/timebase; trim bỏ mất hành động không pass; uncertainty/occlusion/checker failure; kiểm tra MP4 ghép cuối |
| Repair/restore | Candidate không tự active; thay một cảnh giữ hash cảnh tốt, kể cả raw clip chung; duyệt lại trim/checks đúng phạm vi; so sánh/restore đúng version |
| Rights/release | Intake không gọi AI; direct live compile thiếu intake/quyền/cap tạo zero provider calls; sai workspace, thiếu/thu hồi quyền, chưa duyệt hoặc stale approval bị backend chặn; UI “Dùng đoạn” khác duyệt nội dung; không cấp export bypass; nhãn AI trên file thật; deletion có bằng chứng |
| Budget/evidence | Concurrent reservation, unknown cost, all attempts/retries/fails; valid receipts/hashes; replay offline không gọi provider; report không biến missing/zero denominator thành số đo |
| Browser | 390/768/1280/1440 px, keyboard, zoom 200%, focus/reduced motion, không tràn ngang; reload giữa render/trim/compose, nguồn hết hạn, finding cũ, preview source/current/candidate |
| Demo/dev corpus | Ba ca có quyền: đạt, cần sửa, bị chặn; riêng ca không nhân vật và có nhân vật khi feature đó được dùng; fixture/mock/live phân biệt rõ |

Notion §9.1 hiện dùng kế hoạch **20 cặp × 3 = 60**, **8 cặp × 3 ablation = 24**; không dùng nhánh đề xuất cũ `6×4` cho cùng báo cáo. Định nghĩa cụ thể B0/B1/B2 và từng ablation vẫn cần được khóa từ hồ sơ: validator phải báo pending, không tự relabel provider routes. Điều này không chặn dev pilot nội bộ và hoàn thiện P0; chặn kết luận bộ BTC đã hoàn tất. Không chạy batch 84 trong hai chat này trước khi có protocol/budget chính thức.

## 7. Checks và cách chạy hai chat

Từ root: `make lint`, `make typecheck`, `make test-unit`, `make test-integration`, `make test-contract`, `make web-build`, `make web-lint`. Frontend tại `apps/web`: `pnpm test`, `pnpm typecheck`. Chạy scoped checks theo diff trước; không sửa 629 lint issues nền ngoài yêu cầu. Mọi skip/failure nền phải ghi rõ, không báo full-suite pass khi chỉ chạy scope.

Unit logic mới/thay đổi đạt coverage ≥80% với phạm vi công bố; backend default gate 70% không đủ để suy đạt 80%. Hai chat đặt `COVERAGE_FILE` riêng khi chạy coverage (ví dụ `/tmp/viraldy-p0-a.coverage` và `/tmp/viraldy-p0-b.coverage`) để không ghi đè nhau. Không chạy cùng lúc production frontend build vào cùng output directory; B sở hữu browser/build. A/B dùng DB/container test riêng và không migrate/delete DB đang phục vụ seller.

Giữ package manager và scripts hiện có. Đọc skills phù hợp, test trước sửa bug/hành vi mới, kiểm tra GitNexus trước sửa symbol, review độc lập trước bàn giao. Khi cần refresh index dùng `node .gitnexus/run.cjs analyze --index-only` để không ghi lại AGENTS/skills ngoài phạm vi. Không checkout/reset/stash/clean workspace, không commit/stage toàn bộ WIP hoặc push từ hai chat. Nếu có commit được giao riêng, chỉ stage file ownership và chạy `detect_changes` trước; phân biệt diff có sẵn với diff task.

Prompt dùng trực tiếp:

- [Chat A — Runtime, API và policy](smart-remake-p0-chat-a-prompt.md)
- [Chat B — Inspector, UI và evidence](smart-remake-p0-chat-b-prompt.md)

## M1/M2 implementation addendum — p0-lifecycle-v1

Contract cụ thể và examples chính thức nằm trong [status A](smart-remake-p0-chat-a-status.md#m1-wire-examples-đã-khóa-p0-lifecycle-v1). Bổ sung tương thích: rights review `POST /projects/{id}/rights/reviews`; provenance `GET /projects/{id}/provenance` version `smart_remake_provenance_v1`; project phases `intake|compiled|rendered`; `inspectionSummary.currentReportIds` và authorized `inspectionMedia` cung cấp evidence binding ID/hash/clock. Client không gửi verification/actor fields do server cấp. Đã nối actual API/worker/B Inspector với PostgreSQL/FFmpeg offline; xem M2 status A để chạy B browser. Người dùng xác nhận chuẩn bị pilot bằng media tự tạo và chưa gọi trả phí; mọi live execution vẫn cần trần/config cụ thể trước submit.

Clock mapping additive v1 đã khóa tại [status A](smart-remake-p0-chat-a-status.md#inspector-clock-mapping--additive-v1-contract-locked): `inspectionMappings` giữ range/binding đóng băng, virtual scene_local descriptors ghi rõ `playbackTimebase=raw_group`. UI phải map sang clock của bytes trước playback. Không suy đoán source-to-generated semantic correspondence. Readiness của A theo yêu cầu mới nhất là chuẩn bị/offline; config/cap thiếu giữ paidExecution blocked, không coi đây là quyền chạy trả phí hoặc LIVE_VERIFIED.
