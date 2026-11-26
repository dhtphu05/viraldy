# Chat B — Smart Remake P0

Status: **OFFLINE_QUALIFIED — LIVE_PILOT_SETUP_PENDING**. Ngày: **25/11/2026**.

B1–B5 đã triển khai và nghiệm thu offline qua API/worker/media thật, chỉ giả lập physical provider boundaries. **Chưa ghi `READY_FOR_LIVE_PILOT` hoặc `LIVE_VERIFIED`.** Người dùng chưa có KIE key và chọn để giới hạn trống/không giới hạn trong gói chuẩn bị; phiên này không gọi trả phí. Contract runtime hiện vẫn yêu cầu budget hữu hạn và server exposure bounds. Không tự bỏ budget guards hoặc bịa cap.

Contract: **p0-lifecycle-v1**, checker **smart-remake-inspection-p0-v1.1**, provenance **smart_remake_provenance_v1**, normalized capture **smart_remake_capture_v1**. Additive clock mapping v1 của A đã tích hợp.

## Baseline và ownership

Baseline `feat/assets` / `b68d34d`, giữ toàn bộ tracked/untracked WIP. Baseline frontend: **522 tests và typecheck đạt**, chưa có coverage/browser qualification. Chỉ Chat B cập nhật file này.

B thay đổi `modules/smart_remake/inspection/` mới và tests riêng; frontend Smart Remake/shared API; backend evaluation, `evaluation/smart_remake/`, script eval và browser helpers/tests mới. Backend router/lifecycle/models/migrations/jobs/workers/storage/config, common handoff và runbook backend thuộc A. Creative Library WIP giữ nguyên. Không reset/clean/stash/checkout/worktree/stage/commit/push.

## B1–B5

| Task | Kết quả | Phạm vi nghiệm thu |
| --- | --- | --- |
| B1 | IMPLEMENTED / VERIFIED | Public typed Inspector, strict Pydantic, bốn trạng thái, exact hashes/clock/range/context/neighbor validators |
| B2 | IMPLEMENTED / VERIFIED OFFLINE | Conditioning image, raw logical scenes, selected ranges, continuity và actual final MP4; original references; bounded sampled observations |
| B3 | IMPLEMENTED / VERIFIED | Owned intake trước compile, wizard hiện có, requirements/rights/budget, Inspector/reviews, candidate/compare, restore, checked export, reload/deletion controls |
| B4 | IMPLEMENTED / VERIFIED | Manifest, versioned runtime capture, validator, provider-free replay/report, blinded rubric/ratings và missingness accounting |
| B5 | OFFLINE VERIFIED | True browser/API/Celery/PostgreSQL/Redis/MinIO/FFmpeg journeys và recovery; live setup gate còn pending |

### Inspector public boundary — CONTRACT_READY

`inspection/public.py` giao sớm `inspect_subject(subject, media, references, constraints, invoke_model)` và `validate_report_binding`; hỗ trợ positional hoặc A keyword arguments. A resolve authorized immutable bytes, truyền snapshot và callback có ledger, persist reports và quyết định release. B không tạo provider client, hidden retry hoặc ghi lifecycle DB.

- Frame nguyên trên 24 fps, khoảng `[inFrame,outFrame)`. Report bind project, scene/version hoặc assembly, media/manifest/constraints hashes và neighbor versions/ranges. Hash sai, thiếu evidence, exclusive-end vượt một frame và stale contexts bị từ chối.
- Original source/product/optional character được đối chiếu trực tiếp. Character N/A chỉ khi không được yêu cầu; không dùng ảnh AI trung gian thay reference gốc.
- Mỗi cảnh logic tối đa sáu output frames và ba source anchors; ưu tiên endpoints và known action anchors. Điểm nối kiểm tra riêng trên actual media. Report giữ đúng frames đã decode/quan sát, không suy correspondence source→output.
- Additive `observationAnchors:[{mediaId,mediaHash,timebase,frame}]`, default `[]`. Sai binding fail preflight; marker hợp lệ vượt capacity hoặc decode thiếu trả explicit insufficient-evidence với zero model calls. Chuẩn bị observations trước model invocation. A hiện chưa cấp markers nên default tương thích.
- Không có findings/observations/profile, thiếu coverage, che khuất, audio claim không có evidence, temporal action chưa đủ quan sát hoặc checker lỗi không thành pass. VLM đề xuất findings; deterministic rules quyết định hard blocking. Semantic uncertainty cần review đúng policy.

### Seller workflow và bốn clocks

Giữ `prepare → plan → result`, timeline/player/repair hiện có. `POST /projects` không gọi AI, lưu owned project ID rồi mới compile. Mutations dùng revision/idempotency theo M1; reload chỉ đọc/poll và phục hồi đúng phase. Metadata canonical bỏ JSONB key order/server-only fields; thay inputs/yêu cầu buộc compile lại, không tái dùng stale analysis.

Requirements giữ/thay/cấm/claims; optional character reference; quyền từng asset, consent/attribution/disclosure; cap nhập bởi người dùng. Budget/progress và estimated/actual/unknown lấy từ server. Không có cap mặc định. Có sửa quyền/cap, ngừng dùng/xóa và dependency status.

Inspector hiển thị expected/observed/evidence/uncertainty/coverage/freshness. Source/raw-group/final seek đúng media ID/hash/range. Scene-local dùng virtual descriptor và **frozen report-specific mapping** sang authorized raw bytes; kiểm tra report/context/manifest/scene/version/range/24fps. Missing/ambiguous binding fail closed. Không phát raw URL trực tiếp ở local offset, không dùng draft mới để sửa historical mapping. Nút `Trong cảnh` không tạo finding mới.

“Dùng đoạn này” là selection, tách content/release approval. Candidate chưa tự active; comparison đồng bộ offset với một audio stream. Restore dùng endpoint riêng. Thay trim/version/constraints/neighbor làm checks/approval stale theo server. Export chỉ dùng checked export response; `finalVideoUrl` chỉ preview, không fallback tải.

## Kiểm chứng cuối

| Check | Kết quả |
| --- | --- |
| Frontend regression | **625/625 tests**, 62 files |
| Frontend declared nine-path coverage | **85.35% statements, 83.91% branches, 87.36% functions, 86.91% lines**; tất cả aggregate gates ≥80% |
| B Inspector + evidence backend | **109 tests**, **93.63% coverage**, 1429 statements; coverage gate ≥80% |
| Typecheck / build | `pnpm typecheck` và `pnpm build` đạt; chỉ còn chunk-size warning nền |
| Scoped static checks | Frontend ESLint, backend Ruff, mypy **17 source files**, scoped `git diff --check` đạt |
| Main browser suite | **6/6 đạt, 199.12 s**; actual API/worker/storage/media, fake physical providers |
| Player follow-up browser | **1/1 pass8 đạt, 80.00 s**, sau fix nhãn khi chưa có metadata |
| Recovery browser suite | **3/3 đạt, 82.74 s**; affected cleanup rerun đạt với unraisable warnings thành errors |
| Browser safety/media | **11/11 đạt, 3.86 s** |
| Independent reviews | Exact A→B wire mapping, historical/shared-raw isolation, replay binding và evidence UI không còn critical/high/material P2 được báo |

Coverage frontend công bố gồm `remake-intake.ts`, `use-remake-policy.ts`, `shared/api/smart-remake.ts`, `remake-inspection.ts`, `remake-preview.ts`, `remake-project-inputs.tsx`, `remake-inspector.tsx`, `remake-project-controls.tsx`, và full existing `remake-player.tsx`. Existing player riêng đạt 58.54% statements; không tuyên bố từng file ≥80%. Full existing studio orchestration không nằm trong aggregate coverage này; analysis signature, intake/reload và async recovery có regressions riêng. Không tuyên bố full repo lint/backend suite sạch; lint nền ngoài scope giữ nguyên.

Browser acceptance đã thực hiện:

- Pass8, repair16 và blocked: intake→compile→render→trim→compose→inspect→repair riêng một cảnh→retrim/reinspect→human review→approve/checked export→readonly reload→restore; stale export bị backend từ chối.
- `2+6`, `3+5+4+4`, actual labeled MP4 **192/384 frames**, audio trim; exact hashes/ranges; all four clocks; historical scene-local offset giữ nguyên sau replacement/retrim; cảnh tốt giữ hash kể cả shared raw group. VFR normalization và exclusive-end vượt một frame có actual FFmpeg Inspector tests riêng.
- Double Generate, worker stop/restart, unknown receipt không resubmit; duplicate Celery delivery; two-tab revision conflict; MinIO raw mất giữa queued compose giữ assembly cũ và recover bằng exact bytes; signed preview URL hết hạn 200→403→refresh/playback không tạo AI call.
- Missing rights và exhausted budget bị chặn trước provider; free intake zero provider calls. Semantic review và rights review đi UI/API, không sửa DB để qua gate.
- 390/768/1280/1440 px, keyboard/focus restore, reduced motion, CSS reflow và **native Chromium page zoom 200%** (`chrome.tabs.setZoom`, inner width 1280→640, DPR 1→2, CSS zoom 1). Native screenshots full physical viewport **1280×813**; không tràn ngang. Comparison chỉ một audio stream.

Single-frame evidence giữ tĩnh, Play disabled, seek đúng observed frame. Preview nhiều frame có end guards best effort: compositor/JavaScript stall có thể hiển thị thoáng qua frame ngoài range. Không tuyên bố browser preview hard-clipped; actual FFmpeg trim/compose/export vẫn enforce exclusive bounds. Bounded derivative cần thiết nếu sau này yêu cầu playback tuyệt đối không hiển thị frame ngoài range.

### Commands

Chạy frontend tại `apps/web`:

```sh
pnpm test --coverage \
  --coverage.include=src/features/smart-remake/lib/remake-intake.ts \
  --coverage.include=src/features/smart-remake/lib/use-remake-policy.ts \
  --coverage.include=src/shared/api/smart-remake.ts \
  --coverage.include=src/features/smart-remake/lib/remake-inspection.ts \
  --coverage.include=src/features/smart-remake/components/remake-project-inputs.tsx \
  --coverage.include=src/features/smart-remake/components/remake-inspector.tsx \
  --coverage.include=src/features/smart-remake/components/remake-project-controls.tsx \
  --coverage.include=src/features/smart-remake/components/remake-player.tsx \
  --coverage.include=src/features/smart-remake/lib/remake-preview.ts \
  --coverage.thresholds.lines=80 --coverage.thresholds.statements=80 \
  --coverage.thresholds.functions=80 --coverage.thresholds.branches=80
pnpm typecheck
pnpm build
```

Chạy backend tại `apps/backend` (browser/build tuần tự; các stack dùng DB/containers riêng):

```sh
COVERAGE_FILE=/tmp/viraldy-p0-b.coverage uv run pytest -o addopts='' \
  tests/unit/test_p0_inspection*.py tests/unit/test_p0_evidence*.py \
  --cov=viraldy.modules.smart_remake.inspection \
  --cov=viraldy.evaluation.smart_remake \
  --cov-report=term-missing --cov-report=json:/tmp/viraldy-p0-b-coverage.json \
  --cov-fail-under=80 -q
uv run mypy --follow-imports=silent \
  src/viraldy/modules/smart_remake/inspection src/viraldy/evaluation/smart_remake
RUN_P0_SMART_REMAKE_BROWSER=1 uv run pytest -o addopts='' \
  tests/e2e/test_smart_remake_browser.py --no-cov -q -s
RUN_P0_SMART_REMAKE_BROWSER=1 uv run pytest -o addopts='' \
  tests/e2e/test_smart_remake_recovery.py --no-cov -q -s
uv run pytest -o addopts='' tests/integration/test_smart_remake_evidence_browser_runtime.py --no-cov -q
```

Scoped Ruff đã chạy trên B production/owned tests/scripts; ESLint trên Smart Remake P0 route/hooks/helpers/components/API và Vitest config đã sửa. Logs cuối: `/tmp/viraldy-p0-b-final-{web-tests,backend-tests,web-lint,build}.log`; web coverage `/tmp/viraldy-p0-b-web-coverage/coverage-summary.json`. Coverage backend dùng file B riêng, không ghi đè A.

GitNexus impact đã chạy trước sửa symbols. `compileSmartRemake` HIGH (2 direct callers, studio analysis), polling helper HIGH (3 direct callers, studio polling) đã cảnh báo trước sửa và có regression analysis/async recovery. PlayerSession LOW (1 direct caller), project type MEDIUM được báo trước tích hợp mapping. New B modules chưa indexed trả UNKNOWN, không diễn giải thành zero risk. Không commit nên không dùng detect_changes để nhận toàn WIP chung là diff B.

## Evidence và replay

Harness giữ inputs→all attempts→clips/selected ranges→assemblies→inspections/reviews/release→ratings. Explicit `RuntimeCaptureContext` case/run/variant/version join đã được A chấp thuận; kiểm tra input roles/hashes/project/manifest và giữ missing versions/nulls. `run.mode` là authoritative execution field; server config hoặc client context không nâng provider giả thành live. Các browser captures đều **mock**, kể cả khi cấu hình server là live/unverified.

Retain failed/cancelled/unknown attempts và mọi repair cost; shared attempt IDs dedupe theo lineage. Actual USD chưa biết giữ unknown, không đổi thành 0. Blinded human ratings/rubric có validator; chưa có labels thì false-positive/false-negative và chất lượng đều **unmeasured**. Zero accepted denominator không tạo cost-per-accepted giả. Replay không import/gọi provider và sinh report ổn định.

Gói bền, Git ignored: [Chat B qualification artifacts](/Users/mac/Desktop/Viraldy/artifacts/smart-remake-p0/chat-b-qualification-20261125/README.md), **170 files / 22,304,480 bytes**. [verification.json](/Users/mac/Desktop/Viraldy/artifacts/smart-remake-p0/chat-b-qualification-20261125/verification.json) ghi **7 bundles validate thành công**, mỗi bundle replay hai lần, JSON/Markdown khớp retained bytes. Media paths relative, không rebase; original public payloads và media giữ nguyên hash. Profiles/cookies/traces/service logs không lưu trong package.

| Package dưới qualification root | Kết quả |
| --- | --- |
| `pass8/` | Final mock accepted, 14 attempts |
| `repair16/` | Same-project needs_repair23→accepted32; unique attempts dedupe32, không cộng thành55 |
| `unknown-receipt/` | Mock unknown, 9 attempts, không assembly, runtime needs_reconciliation |
| `pilot-inputs/` | Self-authored input-only, 5 assets / 2 planned cases, zero capture/output/provider calls |
| `checkpoints/*-xn9oo57d/` | Ba mock checkpoints trước, byte-for-byte retained |
| `browser-source/msejjqvd/` và `browser-qa/` | Full final capture payloads/media, native200%, scene-local/history/static-frame proof và post-fix pass8 supplement |

Tổng final ba mock packages **55 unique attempts**, toàn bộ actual costs unknown; workflow human review không phải independent quality ratings. Pilot intended `mode:live` chỉ là ý định tương lai với zero captures: `cap_usd=null`, `authorized=false`, disclosure pending. User preference no USD/attempt/time limits và chưa có KIE key đã ghi trong notes; không có câu hỏi cap nào đang chờ trong phiên này. Scope quyền chỉ chuẩn bị/internal conditional provider pilot; không suy real-person consent hoặc publishing rights.

Replay ví dụ từ `apps/backend`:

```sh
uv run python scripts/evaluate_smart_remake.py validate ../../artifacts/smart-remake-p0/chat-b-qualification-20261125/repair16/bundle.json
uv run python scripts/evaluate_smart_remake.py replay ../../artifacts/smart-remake-p0/chat-b-qualification-20261125/repair16/bundle.json --output-dir /tmp/remake-replay-review
```

Runbook B: [PILOT_RUNBOOK.md](/Users/mac/Desktop/Viraldy/evaluation/smart_remake/PILOT_RUNBOOK.md). Official **20×3 + 8×3** giữ nguyên, B0/B1/B2/ablation definitions pending. Không chạy batch84 hoặc dùng dev fixtures kết luận benchmark chính thức.

## Dependency với A và readiness còn lại

Đã đọc A tại final checkpoint: **READY_FOR_LIVE_PILOT — Chat A code/prepared offline**, **Live execution: BLOCKED**. Lifecycle routes/workers/budgeted callback/authorized media/provenance và frozen clock projections đã có; các production UI paths dùng API thật. Genuine physical execution provenance refinement đã integrated và đạt offline tests. B giữ strict run-mode/receipt guards; trạng thái chuẩn bị code của A không tự bỏ các live setup gates.

Phần offline B không còn dependency implementation mở; A đã chốt code/prepared offline. Để B ghi `READY_FOR_LIVE_PILOT` theo điều kiện cap cụ thể của kế hoạch, còn live credentials/config/server exposure bounds, disclosure cùng budget policy phù hợp lựa chọn người dùng. Chế độ unlimited chưa có trong strict M1 runtime; phiên này không nới contract của A. Không cần tư liệu seller thật để hoàn tất chuẩn bị: bộ self-authored đã có. Chưa gọi paid APIs, chưa có receipts/output/human ratings live; `LIVE_VERIFIED` còn là mốc riêng sau này.
