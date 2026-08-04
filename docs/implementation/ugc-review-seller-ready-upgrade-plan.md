# UGC Review seller-ready upgrade plan

Ngày ghi nhận: 2026-07-31

Tài liệu này lưu lại 6 hướng nâng cấp đã thống nhất để triển khai sau. Mục tiêu không phải làm hệ thống “chấm hay/dở” chung chung, mà biến output UGC Review thành danh sách việc có thể giao ngay cho seller, editor, hoặc creator.

## Bối cảnh

Trong lần smoke test với video thật `apps/web/public/demo-media/sofa-cover-ugc.mp4`, OpenAI transcription nhận được câu tiếng Hàn:

> 이 영상은 브랜드 협찬으로 제작되었습니다.

Nghĩa thực thi: video đã có disclosure dạng spoken sponsorship. Tuy nhiên backend chưa normalize transcript thành evidence `disclosure`, nên evaluator vẫn tạo recommendation kiểu “Add approved material-connection disclosure” với `evidence_count = 0`. Đây là dấu hiệu output còn quá generic và có thể sai dưới góc nhìn seller/domain expert/client/content marketing executive.

Expected mới:

- Nếu video có spoken disclosure nhưng chưa có visual/caption/publish disclosure, hệ thống không được nói “không có disclosure”.
- Recommendation phải chỉ rõ: ai làm, làm ở timestamp nào, sửa đoạn nào, copy chính xác là gì, xong khi nào được xem là đạt.
- UI phải hiển thị như task list để execute, không chỉ là card giải thích chung.

## 1. Tách rõ loại finding theo hành động thực thi

Không nên chỉ dựa vào 3 group hiện tại `fix_first`, `improve`, `confirm`, vì seller cần biết việc đó thuộc loại nào.

Giữ nguyên DB-level group hiện tại để tránh migration không cần thiết:

- `fix_first`
- `improve`
- `confirm`

Thêm classification ở recommendation payload:

- `video_edit_required`: cần editor/creator sửa video hoặc bản dựng.
- `publish_ops_required`: cần seller/operator kiểm tra lúc đăng bài.
- `seller_input_required`: cần seller cung cấp/chốt thông tin chưa biết.
- `keep`: điểm đang tốt, nên giữ.
- `do_not_change`: vùng không nên sửa vì đang đúng hoặc sẽ làm tăng rủi ro.

Field đề xuất trên `UGCRecommendation`:

```json
{
  "task_kind": "video_edit_required",
  "priority": "fix_before_publish",
  "owner": "editor"
}
```

Acceptance:

- Finding về video edit không bị trộn với publish metadata.
- Publish-time checklist không bị xem là creative failure.
- Seller nhìn vào là biết việc nào gửi editor, việc nào tự check trong TikTok Shop lúc publish.

## 2. Normalize transcript/disclosure evidence, gồm multilingual disclosure

Backend cần nhận diện disclosure không chỉ từ OCR/on-screen text mà cả transcript.

Các phrase cần nhận diện tối thiểu:

- English: `sponsored`, `paid partnership`, `ad`, `gifted`, `affiliate`
- Korean: `협찬`, `광고`, `스폰서`
- Vietnamese: `tài trợ`, `quảng cáo`, `được tặng`, `liên kết tiếp thị`

Với case sofa cover:

```json
{
  "evidence_type": "transcript_segment",
  "kind": "disclosure",
  "source": "transcript",
  "observed": "이 영상은 브랜드 협찬으로 제작되었습니다.",
  "value": {
    "present": true,
    "modality": "spoken",
    "language": "ko",
    "translation": "This video was made with brand sponsorship."
  }
}
```

Evaluator disclosure cần phân biệt:

- Không có disclosure evidence: tạo fix “Add material-connection disclosure”.
- Có spoken disclosure nhưng không có visible/caption/platform evidence: tạo task “Add visible/caption disclosure for target market”, không nói là disclosure absent.
- Có visible/caption/platform disclosure rõ: không tạo disclosure fix.

Acceptance:

- Transcript Korean sponsorship không bị bỏ qua.
- `analysis_coverage.transcript` đúng khi có transcript evidence.
- Recommendation disclosure luôn trích dẫn evidence transcript hoặc OCR nếu có.

## 3. Mỗi recommendation phải có owner, timestamp, exact action, exact copy, acceptance criteria

Recommendation hiện có `owner`, `instructions`, `completion_criteria`, nhưng nội dung vẫn có thể chung chung. Cần nâng thành execution brief rõ hơn.

Field đề xuất:

```json
{
  "owner": "editor",
  "time_range": {
    "start_ms": 0,
    "end_ms": 2500
  },
  "exact_action": "Add a persistent caption disclosure during the opening product shot.",
  "exact_copy": [
    "Brand sponsored",
    "Paid partnership"
  ],
  "acceptance_criteria": [
    "Disclosure is visible before any product benefit claim.",
    "Disclosure remains readable on mobile.",
    "Publish-time paid partnership setting is confirmed by seller/operator."
  ]
}
```

Rules:

- Nếu có timestamp evidence, dùng timestamp đó.
- Nếu không có timestamp nhưng task là publish ops, `time_range = null` và UI phải hiển thị “Publish-time”.
- `exact_copy` chỉ được đưa ra khi copy an toàn và cần thiết; nếu cần seller legal approval, ghi rõ “seller-approved disclosure copy required”.
- Không tạo claim/copy mới nếu evidence không support.

Acceptance:

- Không có recommendation actionable nào thiếu owner.
- `fix_first` và `improve` phải có `exact_action` hoặc instruction đầu đủ cụ thể.
- `fix_first` phải có acceptance criteria rõ.
- UI có thể render task mà không cần suy luận thêm.

## 4. Dùng OpenAI như bounded edit-brief synthesis sau deterministic facts

OpenAI không nên quyết định rule violation chính. Pipeline nên là:

1. Deterministic evaluator xác định facts, rule, evidence, risk, unknown state.
2. Optional bounded synthesis dùng OpenAI để viết lại thành brief dễ execute.
3. Validator chỉ cho phép OpenAI enrich copy, không cho thêm/xóa finding.

Boundaries bắt buộc:

- Không được thêm recommendation ID mới.
- Không được đổi `rule_code`, `mistake_code`, `group`, `owner`, `evidence`.
- Không được tham chiếu evidence ID không tồn tại.
- Không được tạo performance promise như “winning creative”, “guaranteed ROAS”, “predicted GMV”.
- Nếu provider fail hoặc output invalid, fallback deterministic vẫn phải usable.

Output OpenAI được phép enrich:

- `title`
- `reason`
- `exact_action`
- `exact_copy`
- `acceptance_criteria`
- `creator_revision_message`

Acceptance:

- Test có fake unsafe provider cố đổi rule/evidence thì output bị chặn.
- Provider failure không làm review fail.
- Provenance ghi rõ `execution_brief_provider`.

## 5. Frontend render seller task list thay vì generic recommendation cards

UI hiện đang render theo section generic:

- Fix first
- Improve
- Confirm

UI mới nên render theo cách seller thực thi:

- Fix before posting
- Confirm at publish
- Seller input required
- Optional improvements
- Keep unchanged

Mỗi task card cần hiện:

- Priority/status.
- Owner: seller/editor/creator.
- Timestamp hoặc “Publish-time”.
- Exact action.
- Exact copy nếu có.
- Acceptance criteria.
- Evidence chip có seek vào video nếu có timestamp.
- Nút action phù hợp:
  - video task: `Apply recommendation`, `Send to creator`, `Mark completed`
  - publish ops task: `Mark completed`, `Not applicable`
  - seller input task: `Mark completed`, `Ignore for now`

Không nên hiển thị publish ops task như một lỗi creative của video.

Acceptance:

- Seller nhìn một màn hình là biết phải giao việc gì.
- UI không cần đọc `reason` để hiểu task chính.
- Disclosure spoken/caption case hiện rõ evidence transcript và action cần thêm visual/caption nếu cần.

## 6. Thêm real-video regression fixture/test cho sofa cover

Cần commit fixture nhỏ đại diện cho output OpenAI từ video thật, không phụ thuộc `/tmp`.

File đề xuất:

```text
apps/backend/tests/fixtures/domain_intelligence/sofa_cover_openai_observations_v1.json
```

Fixture nên chứa tối thiểu:

- Transcript segment tiếng Hàn có `협찬`.
- Duration/timestamp opening.
- Product appearance/demo signals từ visual analysis.
- CTA/publish metadata unknown nếu applicable.

Test cần assert:

- Transcript disclosure được normalize thành `kind = "disclosure"`.
- Không còn false finding “no clear disclosure is visible” khi spoken disclosure tồn tại.
- Nếu chưa có visible/caption/platform disclosure, recommendation phải là task cụ thể để thêm visual/caption hoặc confirm publish setting.
- Output có `task_kind`, `owner`, `exact_action`, `exact_copy` hoặc note seller-approved copy, và `acceptance_criteria`.

Acceptance:

- Fixture chạy deterministic, không gọi OpenAI thật trong CI.
- Test tái hiện được gap đã thấy từ smoke test 2026-07-31.
- Regression fail nếu transcript disclosure bị bỏ qua lần nữa.

## File surface dự kiến khi triển khai

Backend:

- `apps/backend/src/viraldy/modules/domain_intelligence/schemas.py`
- `apps/backend/src/viraldy/modules/domain_intelligence/evidence_adapter.py`
- `apps/backend/src/viraldy/modules/domain_intelligence/deterministic_evaluator.py`
- `apps/backend/src/viraldy/modules/domain_intelligence/recommendation_mapper.py`
- `apps/backend/src/viraldy/modules/domain_intelligence/service.py`
- `apps/backend/src/viraldy/modules/domain_intelligence/message_renderer.py`
- `apps/backend/tests/unit/test_domain_intelligence.py`
- `apps/backend/tests/fixtures/domain_intelligence/sofa_cover_openai_observations_v1.json`

Frontend:

- `apps/web/src/features/ugc-review/types/ugc-review.ts`
- `apps/web/src/shared/api/ugc-reviews.ts`
- `apps/web/src/features/ugc-review/components/recommendation-groups.tsx`
- `apps/web/src/features/ugc-review/components/recommendation-section.tsx`
- `apps/web/src/features/ugc-review/components/recommendation-groups.test.ts`
- `apps/web/src/shared/api/ugc-reviews.test.ts`

## Verification plan khi implement

Chạy tối thiểu:

```bash
cd apps/backend
uv run pytest tests/unit/test_domain_intelligence.py tests/unit/test_ugc_review_schemas.py -q --no-cov

cd ../web
pnpm test -- --run src/shared/api/ugc-reviews.test.ts src/features/ugc-review/components/recommendation-groups.test.ts
pnpm build
```

Nếu thay đổi contract/API lớn hơn, chạy thêm:

```bash
cd apps/backend
uv run pytest -q --no-cov

cd ../web
pnpm test -- --run
pnpm typecheck
pnpm build
```

## Non-goals cho đợt nâng cấp này

- Không đổi DB enum/group nếu có thể tránh.
- Không để OpenAI quyết định rule violation chính.
- Không gọi OpenAI trong CI regression.
- Không tạo scoring/performance promise.
- Không biến mọi recommendation thành creative criticism; publish ops và seller input phải được tách riêng.
