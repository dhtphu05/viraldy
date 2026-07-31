from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
PUBLIC_PATHS = {
    "/health",
    "/ready",
    "/health/live",
    "/health/ready",
    "/health/dependencies",
    "/health/worker",
    "/api/v1/version",
    "/api/v1/ready",
    "/api/v1/system/ai-readiness",
    "/api/v1/auth/config",
}

API_SUMMARY = (
    "REST API quản trị toàn bộ vòng đời creative intelligence và campaign production."
)

API_DESCRIPTION = """
Viraldy API là contract chính thức giữa backend, frontend và các hệ thống tích hợp.
API quản lý workspace, product context, media assets, Creative DNA, Pattern Kit,
Viral Kit, Campaign Pack, generation, scoring và preflight.

## Frontend quick start

1. Mở `GET /api/v1/auth/config` để đọc chế độ xác thực của môi trường.
2. Trong local development, nhấn **Authorize** và nhập token `local-test`. Swagger UI
   tự gửi header `Authorization: Bearer local-test` cho các API cần đăng nhập.
3. Tạo hoặc lấy một workspace rồi thay các UUID mẫu trong request bằng ID thực tế.
4. Với tác vụ bất đồng bộ trả về `202`, lưu `job.id` và poll endpoint Jobs cho đến khi
   trạng thái là `succeeded` hoặc `failed`.
5. Gửi `Idempotency-Key` ổn định khi retry các lệnh xử lý/generation để tránh tạo tác
   vụ trùng.

## Quy ước response

Mọi JSON response sử dụng envelope `{ data, meta, error }`. Khi thành công, `data`
chứa payload nghiệp vụ và `error` bằng `null`. Khi thất bại, `error.code` là mã ổn
định để frontend ánh xạ hành vi/UI; `meta.request_id` dùng để đối soát log backend.
Các endpoint `DELETE` trả `204` sẽ không có response body.

## Xác thực và phân quyền

Production sử dụng OIDC Bearer token. Client gửi `Authorization: Bearer <token>`.
Ngoài xác thực người dùng, endpoint nằm dưới `/workspaces/{workspace_id}` còn kiểm
tra membership và permission theo vai trò. `401` nghĩa là token thiếu/không hợp lệ;
`403` nghĩa là đã đăng nhập nhưng không đủ quyền trong workspace.

## Giá trị mẫu

Các UUID, URL và nội dung trong **frontendExample** chỉ là dữ liệu minh hoạ hợp lệ về
format. Frontend cần thay chúng bằng ID từ response của bước trước. Ràng buộc
required, enum, độ dài và miền giá trị được thể hiện trực tiếp trên từng input.
""".strip()

SWAGGER_UI_PARAMETERS: dict[str, Any] = {
    "deepLinking": True,
    "displayOperationId": True,
    "displayRequestDuration": True,
    "docExpansion": "none",
    "filter": True,
    "persistAuthorization": True,
    "showExtensions": True,
    "showCommonExtensions": True,
    "tryItOutEnabled": True,
}

TAG_DEFINITIONS = [
    {
        "name": "health",
        "display_name": "Health & Operations",
        "description": (
            "Kiểm tra liveness, readiness và trạng thái các dependency vận hành. "
            "Dùng cho load balancer, Kubernetes probe, dashboard SRE và chẩn đoán local."
        ),
    },
    {
        "name": "system",
        "display_name": "System Information",
        "description": (
            "Thông tin phiên bản, readiness tương thích ngược và mức sẵn sàng của AI provider. "
            "Các endpoint này không yêu cầu Bearer token."
        ),
    },
    {
        "name": "identity",
        "display_name": "Identity & Authentication",
        "description": (
            "Đọc cấu hình xác thực an toàn cho client và hồ sơ người dùng hiện tại. "
            "Frontend nên gọi auth/config trước khi khởi tạo luồng đăng nhập."
        ),
    },
    {
        "name": "workspaces",
        "display_name": "Workspaces & Members",
        "description": (
            "Quản lý tenant workspace, thành viên và vai trò. Workspace là biên phân quyền "
            "và cô lập dữ liệu cho mọi tài nguyên nghiệp vụ phía sau."
        ),
    },
    {
        "name": "products",
        "display_name": "Products & Product Context",
        "description": (
            "Quản lý sản phẩm và product context có version: identity, persona, benefit, "
            "creative context, commercial context và governance guardrails."
        ),
    },
    {
        "name": "assets",
        "display_name": "Media Assets & Uploads",
        "description": (
            "Tạo upload session, xác nhận upload, quản lý revision và khởi chạy xử lý media. "
            "Luồng upload dùng pre-signed URL và tách khỏi API JSON."
        ),
    },
    {
        "name": "jobs",
        "display_name": "Background Jobs",
        "description": (
            "Theo dõi tác vụ bất đồng bộ, tiến độ, stage và lỗi an toàn. Frontend dùng nhóm "
            "này để poll sau các response `202 Accepted`."
        ),
    },
    {
        "name": "model-runs",
        "display_name": "AI Model Runs",
        "description": (
            "Tra cứu provenance của lần gọi model: operation, subject, provider/model, trạng thái "
            "và usage. Không dùng endpoint này để lộ prompt hoặc secret."
        ),
    },
    {
        "name": "recommendations",
        "display_name": "Recommendations",
        "description": (
            "Đọc recommendation có evidence/assumption và ghi nhận quyết định của người dùng. "
            "Action được lưu để audit và cải thiện chất lượng hệ thống."
        ),
    },
    {
        "name": "product-events",
        "display_name": "Product Events",
        "description": (
            "Dòng sự kiện nghiệp vụ theo workspace để frontend dựng activity feed và audit trail. "
            "Có thể lọc theo event type, subject type và giới hạn kết quả."
        ),
    },
    {
        "name": "feedback",
        "display_name": "Field-level Feedback",
        "description": (
            "Thu thập feedback có cấu trúc đến từng field của output AI, gồm giá trị AI, giá trị "
            "người dùng sửa, comment và model run liên quan."
        ),
    },
    {
        "name": "deletions",
        "display_name": "Deletion & Retention",
        "description": (
            "Thực hiện hard deletion có audit và cleanup theo retention policy. Đây là nhóm API "
            "nhạy cảm, yêu cầu quyền DATA_DELETE và cần xác nhận rõ trên UI."
        ),
    },
    {
        "name": "generation",
        "display_name": "Creative Generation",
        "description": (
            "Tạo storyboard hoặc concept-video preview từ Viral Kit concept và source assets. "
            "Tác vụ chạy bất đồng bộ, hỗ trợ idempotency và rights confirmation."
        ),
    },
    {
        "name": "media-analysis",
        "display_name": "Media Analysis",
        "description": (
            "Đọc kết quả phân tích media đã chuẩn hoá gồm observations, evidence và provenance. "
            "Kết quả là đầu vào cho Creative DNA và scoring."
        ),
    },
    {
        "name": "reference-boards",
        "display_name": "Reference Boards",
        "description": (
            "Tổ chức tài sản tham khảo thành board theo sản phẩm hoặc mục tiêu nghiên cứu. "
            "Board giúp nhóm creative quản lý phạm vi reference có chủ đích."
        ),
    },
    {
        "name": "references",
        "display_name": "Creative References",
        "description": (
            "Gắn asset vào reference board, lưu nguồn và khởi chạy phân tích reference. "
            "Reference là cầu nối giữa media asset và Creative DNA."
        ),
    },
    {
        "name": "creative-dna",
        "display_name": "Creative DNA",
        "description": (
            "Tra cứu hoặc xoá phiên bản Creative DNA được rút trích từ reference asset. "
            "Contract giữ evidence, confidence, taxonomy và provenance."
        ),
    },
    {
        "name": "pattern-kits",
        "display_name": "Pattern Kits",
        "description": (
            "Tổng hợp pattern có thể tái sử dụng từ một hoặc nhiều Creative DNA, quản lý version, "
            "review action, feedback và bộ lọc thư viện."
        ),
    },
    {
        "name": "viral-kits",
        "display_name": "Viral Kits",
        "description": (
            "Kết hợp Product Context và Pattern Kit để tạo ba concept có chủ đích, test matrix, "
            "guardrail, version, action và liên kết Campaign Pack."
        ),
    },
    {
        "name": "tiktok-scores",
        "display_name": "TikTok Structural Scores",
        "description": (
            "Chạy và đọc structural score cho UGC/TikTok asset. Kết quả giải thích strengths, "
            "blockers, fixes, evidence và confidence thay vì chỉ trả điểm số."
        ),
    },
    {
        "name": "adaptations",
        "display_name": "Pattern Adaptations",
        "description": (
            "Adapt Creative DNA/pattern vào product, buyer, market và constraint cụ thể. "
            "Output là đầu vào để biên soạn Campaign Pack."
        ),
    },
    {
        "name": "campaign-packs",
        "display_name": "Campaign Packs",
        "description": (
            "Quản lý creative brief thực thi, compiled requirements, version và export. "
            "Campaign Pack là contract bàn giao giữa seller, creative team và creator."
        ),
    },
    {
        "name": "preflight",
        "display_name": "UGC Preflight",
        "description": (
            "Đối chiếu UGC asset với Campaign Pack requirements trước khi publish/spend. "
            "Trả score, blockers, fixes và presentation cho seller/creator."
        ),
    },
]

OPENAPI_TAGS = [
    {"name": tag["name"], "description": tag["description"]} for tag in TAG_DEFINITIONS
]
TAG_DISPLAY_NAMES = {tag["name"]: tag["display_name"] for tag in TAG_DEFINITIONS}
TAG_DESCRIPTIONS = {tag["name"]: tag["description"] for tag in TAG_DEFINITIONS}

PARAMETER_DESCRIPTIONS = {
    "workspace_id": (
        "UUID của workspace đang thao tác. Lấy từ `GET /api/v1/workspaces`; "
        "người dùng phải là member có permission phù hợp."
    ),
    "member_id": "UUID của user/member cần đổi vai trò hoặc xoá khỏi workspace.",
    "product_id": "UUID của product trong cùng workspace; lấy từ API Products.",
    "asset_id": "UUID của media asset trong cùng workspace; không dùng asset_version_id.",
    "asset_version_id": "UUID của revision cụ thể của asset được trả từ upload session.",
    "job_id": "UUID của background job cần poll để cập nhật trạng thái và tiến độ.",
    "model_run_id": "UUID của AI model run cần tra cứu provenance và usage.",
    "recommendation_id": "UUID của recommendation cần đọc hoặc ghi nhận action.",
    "reference_id": "UUID của creative reference trong cùng workspace.",
    "board_id": "UUID của reference board chứa reference cần thao tác.",
    "dna_version_id": "UUID của Creative DNA version; lấy từ kết quả analyze reference.",
    "pattern_kit_id": "UUID của Pattern Kit; version được truyền riêng khi endpoint yêu cầu.",
    "viral_kit_id": "UUID của Viral Kit; version được truyền riêng khi endpoint yêu cầu.",
    "concept_id": "Business ID của concept trong Viral Kit, ví dụ `concept-01`.",
    "score_run_id": "UUID của TikTok structural score run cần tra cứu.",
    "adaptation_id": "UUID của adaptation run cần tra cứu.",
    "campaign_pack_id": "UUID của Campaign Pack trong workspace.",
    "preflight_run_id": "UUID của preflight run cần đọc hoặc tạo presentation.",
    "generation_run_id": "UUID của generation run bất đồng bộ cần tra cứu.",
    "resource_type": (
        "Loại tài nguyên được hard-delete. Chỉ dùng giá trị backend hỗ trợ và hiển thị "
        "bước xác nhận rõ ràng trên frontend."
    ),
    "resource_id": "UUID của tài nguyên cần hard-delete trong workspace.",
    "version": "Số version nghiệp vụ, bắt đầu từ 1; không phải UUID version row.",
    "limit": "Số bản ghi tối đa cần trả về; dùng giá trị nhỏ cho UI và tăng khi export.",
    "search": "Từ khoá tìm kiếm theo tên hoặc nội dung tóm tắt của tài nguyên.",
    "status": "Lọc theo trạng thái nghiệp vụ; bỏ trống để lấy mọi trạng thái được phép.",
    "kind": "Lọc Pattern Kit theo loại extraction/scope nghiệp vụ.",
    "category": "Lọc theo product/creative category chính.",
    "platform": "Lọc theo nền tảng phân phối mục tiêu, ví dụ `tiktok`.",
    "market": "Lọc theo market code, ví dụ `US` hoặc `VN`.",
    "target_market": "Lọc theo thị trường mục tiêu của Viral Kit.",
    "objective": "Lọc theo mục tiêu campaign/creative đã chuẩn hoá.",
    "created_by": "UUID của user tạo tài nguyên; bỏ trống để không lọc theo creator.",
    "source_creative_dna_version_id": "UUID Creative DNA version dùng làm nguồn Pattern Kit.",
    "subject_type": "Loại đối tượng nghiệp vụ cần lọc, ví dụ `viral_kit`.",
    "subject_id": "UUID của đối tượng nghiệp vụ cần lọc.",
    "operation": "Tên AI operation cần lọc, ví dụ `viral_kit_generate`.",
    "event_type": "Loại event trong activity stream, ví dụ `asset.processed`.",
    "product_id_query": "UUID product dùng để giới hạn reference board.",
    "Idempotency-Key": (
        "Khoá retry do client tạo. Giữ nguyên cho cùng một ý định và đổi khoá khi người dùng "
        "thực sự tạo tác vụ mới."
    ),
}

PARAMETER_EXAMPLES: dict[str, Any] = {
    "workspace_id": "11111111-1111-4111-8111-111111111111",
    "member_id": "12121212-1212-4121-8121-121212121212",
    "product_id": "22222222-2222-4222-8222-222222222222",
    "asset_id": "33333333-3333-4333-8333-333333333333",
    "asset_version_id": "34343434-3434-4343-8343-343434343434",
    "job_id": "44444444-4444-4444-8444-444444444444",
    "model_run_id": "45454545-4545-4454-8454-454545454545",
    "recommendation_id": "46464646-4646-4464-8464-464646464646",
    "reference_id": "55555555-5555-4555-8555-555555555555",
    "board_id": "56565656-5656-4565-8565-565656565656",
    "dna_version_id": "66666666-6666-4666-8666-666666666666",
    "pattern_kit_id": "77777777-7777-4777-8777-777777777777",
    "viral_kit_id": "88888888-8888-4888-8888-888888888888",
    "concept_id": "concept-01",
    "score_run_id": "89898989-8989-4898-8989-898989898989",
    "adaptation_id": "90909090-9090-4909-8909-909090909090",
    "campaign_pack_id": "99999999-9999-4999-8999-999999999999",
    "preflight_run_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    "generation_run_id": "abababab-abab-4bab-8bab-abababababab",
    "resource_type": "asset",
    "resource_id": "33333333-3333-4333-8333-333333333333",
    "version": 1,
    "limit": 50,
    "search": "summer launch",
    "status": "active",
    "kind": "single_asset",
    "category": "beauty",
    "platform": "tiktok",
    "market": "US",
    "target_market": "US",
    "objective": "conversion",
    "created_by": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
    "source_creative_dna_version_id": "66666666-6666-4666-8666-666666666666",
    "subject_type": "viral_kit",
    "subject_id": "88888888-8888-4888-8888-888888888888",
    "operation": "viral_kit_generate",
    "event_type": "asset.processed",
    "Idempotency-Key": "frontend-demo-20260731-001",
}

FIELD_DESCRIPTIONS = {
    "name": "Tên hiển thị ngắn gọn, dễ nhận biết trên giao diện quản trị.",
    "slug": "Định danh URL-friendly duy nhất, chỉ gồm chữ thường, số và dấu gạch nối.",
    "email": "Email thành viên cần mời; backend dùng email để liên kết identity.",
    "role": "Vai trò quyết định tập permission của thành viên trong workspace.",
    "description": "Mô tả nghiệp vụ giúp người dùng hiểu mục đích và phạm vi của tài nguyên.",
    "market": "Mã hoặc tên thị trường mục tiêu, ví dụ `US`, `VN` hoặc `United States`.",
    "target_market": "Thị trường mà concept/campaign sẽ được bản địa hoá và phân phối.",
    "external_source": "Tên hệ thống nguồn bên ngoài, ví dụ `shopify`; bỏ trống nếu tạo thủ công.",
    "external_id": "Định danh của product ở hệ thống nguồn; dùng để đồng bộ/idempotency.",
    "metadata_json": "Metadata mở rộng dạng JSON; không đặt secret hoặc dữ liệu nhạy cảm.",
    "product_context": (
        "Product Context có cấu trúc dùng làm nguồn sự thật cho persona, benefit, creative "
        "direction, commercial context và governance."
    ),
    "filename": "Tên file gốc có phần mở rộng, ví dụ `ugc-demo.mp4`.",
    "declared_mime_type": "MIME type do client khai báo; backend sẽ kiểm tra lại sau upload.",
    "declared_size_bytes": "Kích thước file theo byte trước khi upload; phải lớn hơn 0.",
    "asset_type": "Loại nghiệp vụ của asset, ví dụ `ugc_video`, `product_image` hoặc `reference`.",
    "objective": "Mục tiêu nghiệp vụ/creative đã chuẩn hoá cho tác vụ hiện tại.",
    "notes": "Ghi chú bổ sung cho reviewer hoặc người thực thi; không dùng để truyền secret.",
    "comment": "Nhận xét có ngữ cảnh của người dùng để reviewer hiểu lý do thay đổi.",
    "reason": "Lý do thực hiện action; nên đủ rõ để phục vụ audit và review.",
    "change_reason": "Lý do tạo version mới, mô tả thay đổi có chủ đích so với version trước.",
    "change_note": "Ghi chú thay đổi của Campaign Pack version mới.",
    "field_path": "Đường dẫn field được feedback, ví dụ `concepts[0].hook.spoken_text`.",
    "feedback_type": "Loại feedback có cấu trúc để backend phân loại và phân tích.",
    "ai_value_json": "Giá trị do AI tạo tại field được feedback; hỗ trợ audit before/after.",
    "user_value_json": "Giá trị người dùng mong muốn sau khi chỉnh sửa field.",
    "action": "Action nghiệp vụ cần ghi nhận; chọn một giá trị enum được hỗ trợ.",
    "action_type": "Loại quyết định của người dùng đối với recommendation.",
    "format": "Định dạng export; `json` cho tích hợp máy và `text` cho đọc/chia sẻ.",
    "rights_confirmed": (
        "Xác nhận caller có quyền sử dụng source assets cho generation; phải là `true` "
        "trước khi phát sinh nội dung."
    ),
    "rights_note": "Ghi chú quyền sử dụng, phạm vi chỉnh sửa và điều kiện phát hành.",
    "seller_locale": "Locale của seller presentation; hiện hỗ trợ `en-US` và `vi-VN`.",
    "force_regenerate": "Đặt `true` để bỏ qua kết quả presentation đã lưu và tạo lại.",
    "concept_count": "Số concept cần tạo. Viral Kit V1 yêu cầu chính xác 3 concept.",
    "expected_product_context_version": (
        "Version Product Context mà frontend đã đọc; chống ghi dựa trên dữ liệu cũ."
    ),
    "pattern_kit_version_ids": (
        "Danh sách UUID Pattern Kit version làm nguồn; không được trùng lặp."
    ),
    "source_creative_dna_version_ids": (
        "Danh sách UUID Creative DNA version dùng để rút trích Pattern Kit."
    ),
    "source_asset_ids": "Danh sách UUID source asset đã upload và có quyền sử dụng.",
    "ugc_asset_id": "UUID của UGC asset cần kiểm tra trước khi publish/spend.",
    "campaign_pack_version_id": "UUID Campaign Pack version làm brief chuẩn để đối chiếu.",
    "adaptation_run_id": "UUID adaptation run chứa concept đã adapt cho product/market.",
    "creative_dna_version_id": "UUID Creative DNA version làm nguồn cho adaptation.",
    "board_id": "UUID reference board sẽ chứa reference mới.",
    "asset_id": "UUID media asset nguồn trong cùng workspace.",
    "product_id": "UUID product trong cùng workspace; lấy từ API Products.",
    "model_run_id": "UUID AI model run liên quan, dùng cho provenance và audit.",
    "subject_id": "UUID đối tượng nghiệp vụ nhận feedback hoặc được lọc.",
    "subject_version": (
        "Version đối tượng tại thời điểm feedback; bỏ trống để dùng version hiện tại."
    ),
    "title": "Tiêu đề ngắn gọn để nhận biết reference trên UI.",
    "source_platform": "Nền tảng xuất xứ của reference, ví dụ `tiktok` hoặc `instagram`.",
    "source_url": "URL nguồn công khai của reference; không truyền URL chứa credential.",
    "primary_category": "Category chính dùng để tổ chức và đánh giá tính phù hợp của Pattern Kit.",
    "target_platforms": "Danh sách nền tảng mà pattern hướng tới, ví dụ `tiktok`.",
    "target_markets": "Danh sách thị trường mà pattern đã được đánh giá phù hợp.",
    "objectives": "Danh sách mục tiêu creative/campaign mà pattern hỗ trợ.",
    "review_notes": "Ghi chú cho reviewer về nguồn, giả định hoặc điểm cần xác minh.",
    "applicability_override_reason": (
        "Giải thích có audit khi người dùng chủ động override cảnh báo applicability."
    ),
    "buyer_persona_id": "Business ID của buyer persona trong Product Context.",
    "target_buyer": "Thông tin buyer bổ sung dạng JSON dùng cho adaptation.",
    "constraints": "Các constraint bổ sung dạng JSON, ví dụ claim, duration hoặc production.",
    "brief": "Campaign Pack brief hoàn chỉnh dùng để tạo một version bất biến mới.",
    "pattern": "Toàn bộ Pattern Kit contract đã chỉnh sửa; bỏ trống để backend tái sinh.",
    "viral_kit": "Toàn bộ Viral Kit contract đã chỉnh sửa; bỏ trống để backend tái sinh.",
}

FIELD_EXAMPLES: dict[str, Any] = {
    **PARAMETER_EXAMPLES,
    "name": "Summer Glow Launch",
    "slug": "summer-glow-launch",
    "email": "frontend.tester@example.com",
    "role": "member",
    "description": "Bộ sản phẩm skincare cho chiến dịch UGC mùa hè.",
    "filename": "ugc-demo.mp4",
    "declared_mime_type": "video/mp4",
    "declared_size_bytes": 8_388_608,
    "asset_type": "ugc_video",
    "external_source": "shopify",
    "external_id": "gid://shopify/Product/123456789",
    "metadata_json": {"campaign": "summer-2026", "source": "frontend-demo"},
    "source_platform": "tiktok",
    "source_url": "https://www.tiktok.com/@creator/video/1234567890",
    "title": "High-retention skincare demo",
    "notes": "Ưu tiên hook trực quan trong 3 giây đầu.",
    "comment": "Hook nên nêu pain point cụ thể hơn.",
    "reason": "Đã được reviewer xác minh với source evidence.",
    "change_reason": "Điều chỉnh hook sau vòng review đầu tiên.",
    "change_note": "Cập nhật CTA và claim guardrails.",
    "field_path": "concepts[0].hook.spoken_text",
    "feedback_type": "edit",
    "ai_value_json": "Bạn vẫn đang gặp tình trạng da khô?",
    "user_value_json": "Da khô dù đã dưỡng ẩm mỗi tối?",
    "action": "reviewed",
    "action_type": "accepted",
    "format": "json",
    "rights_confirmed": True,
    "rights_note": "Creator cho phép chỉnh sửa và chạy quảng cáo trong 90 ngày.",
    "seller_locale": "vi-VN",
    "force_regenerate": False,
    "concept_count": 3,
    "expected_product_context_version": 1,
    "primary_category": "beauty",
    "target_platforms": ["tiktok"],
    "target_markets": ["US"],
    "objectives": ["conversion"],
    "review_notes": "Nguồn đã được kiểm tra quyền sử dụng.",
    "applicability_override_reason": "Đã xác minh sản phẩm đáp ứng yêu cầu visual demo.",
    "buyer_persona_id": "persona-sensitive-skin",
    "target_buyer": {"persona": "busy professionals", "awareness_stage": "problem_aware"},
    "constraints": {"max_duration_ms": 30000, "prohibited_claims": ["guaranteed cure"]},
}

SPECIAL_PURPOSES = {
    "Live": "Xác nhận process API vẫn đang chạy mà không gọi dependency bên ngoài.",
    "Dependencies": "Kiểm tra tổng hợp PostgreSQL, Redis, object storage, worker và cấu hình AI.",
    "Worker": "Kiểm tra có Celery worker phản hồi để tiếp nhận background job hay không.",
    "Get Auth Config": "Trả cấu hình auth an toàn mà frontend cần để chọn local-test hoặc OIDC.",
    "Get Me": "Trả identity đã xác thực và hồ sơ user hiện tại để khởi tạo session UI.",
    "Create Upload Session": (
        "Khởi tạo asset, version đầu tiên và pre-signed URL để upload trực tiếp."
    ),
    "Complete Upload": "Xác nhận client đã upload xong để backend validate object và metadata.",
    "Create Revision Upload Session": (
        "Tạo revision mới và pre-signed URL cho một asset đã tồn tại."
    ),
    "Complete Revision Upload": "Xác nhận upload hoàn tất cho đúng asset revision được chỉ định.",
    "Process Asset": "Xếp hàng pipeline xử lý media cho current version của asset.",
    "Record Recommendation Action": "Lưu quyết định của user đối với recommendation để audit.",
    "Request Retention Cleanup": (
        "Khởi chạy cleanup dữ liệu hết hạn theo retention policy hiện hành."
    ),
    "Delete Workspace Data": "Hard-delete dữ liệu workspace có audit theo quyền DATA_DELETE.",
    "Delete Resource Data": "Hard-delete một tài nguyên được hỗ trợ cùng dữ liệu phụ thuộc.",
    "Create Storyboard": "Tạo storyboard bất đồng bộ từ Viral Kit concept và source assets.",
    "Create Concept Video Preview": (
        "Tạo concept-video preview bất đồng bộ để review trước sản xuất."
    ),
    "Analyze Reference": "Xếp hàng phân tích reference để tạo media observations và Creative DNA.",
    "Latest Reference Dna": "Lấy Creative DNA version mới nhất gắn với một reference.",
    "Record Pattern Kit Action": "Ghi nhận review/validation/lifecycle action cho Pattern Kit.",
    "Create Pattern Kit Feedback": "Gửi feedback cấp field cho một Pattern Kit version.",
    "Record Viral Kit Concept Action": "Chọn, loại hoặc ghi nhận quyết định đối với một concept.",
    "Create Campaign Pack From Viral Kit Concept": (
        "Biên soạn Campaign Pack từ concept đã chọn và liên kết provenance hai chiều."
    ),
    "Create Viral Kit Feedback": "Gửi feedback cấp field cho một Viral Kit version.",
    "Create Score": "Khởi chạy TikTok structural scoring cho asset và product context liên quan.",
    "Export Pack": "Xuất current Campaign Pack version theo định dạng máy hoặc văn bản.",
    "Create Preflight": "Khởi chạy đối chiếu UGC asset với Campaign Pack requirements.",
    "Generate Preflight Presentation": (
        "Tạo seller decision summary và creator revision message từ preflight result."
    ),
    "System Ai Readiness": "Trả trạng thái cấu hình AI an toàn, không tiết lộ API key hoặc secret.",
}


def configure_openapi(app: FastAPI) -> None:
    """Install a cached OpenAPI builder that enriches FastAPI's generated contract."""

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema is not None:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            openapi_version=app.openapi_version,
            summary=app.summary,
            description=app.description,
            routes=app.routes,
            webhooks=app.webhooks.routes,
            tags=app.openapi_tags,
            servers=app.servers,
            terms_of_service=app.terms_of_service,
            contact=app.contact,
            license_info=app.license_info,
            separate_input_output_schemas=app.separate_input_output_schemas,
        )
        app.openapi_schema = _enrich_openapi(schema)
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]


def _enrich_openapi(schema: dict[str, Any]) -> dict[str, Any]:
    components = schema.setdefault("components", {})
    schemas = components.setdefault("schemas", {})
    components["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "OIDC access token. Trong local development dùng token `local-test`. "
                "Chỉ nhập phần token, không nhập tiền tố `Bearer` trong hộp Authorize."
            ),
        }
    }
    _add_error_components(components)
    _enrich_schema_fields(schemas)
    for path, method, operation in _operations(schema):
        _enrich_operation(path, method, operation, schemas)
    return schema


def _operations(
    schema: dict[str, Any],
) -> Iterator[tuple[str, str, dict[str, Any]]]:
    for path, path_item in schema["paths"].items():
        for method, operation in path_item.items():
            if method in HTTP_METHODS:
                yield path, method, operation


def _enrich_operation(
    path: str,
    method: str,
    operation: dict[str, Any],
    schemas: dict[str, Any],
) -> None:
    tag = operation.get("tags", ["system"])[0]
    original_summary = operation.get("summary", operation["operationId"])
    display_name = TAG_DISPLAY_NAMES.get(tag, tag.replace("-", " ").title())
    operation["tags"] = [tag]
    operation["summary"] = f"{display_name} · {original_summary}"
    operation["description"] = _operation_description(
        path, method, original_summary, tag, "requestBody" in operation
    )

    parameters = [
        parameter
        for parameter in operation.get("parameters", [])
        if parameter["name"].lower() != "authorization"
    ]
    for parameter in parameters:
        _enrich_parameter(parameter)
    operation["parameters"] = parameters

    is_public = path in PUBLIC_PATHS
    operation["security"] = [] if is_public else [{"BearerAuth": []}]

    request_body = operation.get("requestBody")
    if request_body is not None:
        _enrich_request_body(request_body, operation["summary"], schemas)

    _enrich_responses(path, method, operation, is_public)


def _operation_description(
    path: str,
    method: str,
    summary: str,
    tag: str,
    has_body: bool,
) -> str:
    purpose = SPECIAL_PURPOSES.get(
        summary,
        (
            f"Thực hiện nghiệp vụ **{summary}** trong nhóm {TAG_DISPLAY_NAMES.get(tag, tag)}. "
            f"{TAG_DESCRIPTIONS.get(tag, '')}"
        ),
    )
    access = (
        "Endpoint công khai; không gửi Bearer token và không phụ thuộc workspace membership."
        if path in PUBLIC_PATHS
        else (
            "Yêu cầu Bearer token hợp lệ. Với tài nguyên workspace, backend tiếp tục kiểm tra "
            "membership và permission tương ứng trước khi đọc hoặc thay đổi dữ liệu."
        )
    )
    input_guidance = (
        "Frontend: mở **Example Value**, thay UUID mẫu bằng ID từ bước trước, giữ đúng enum và "
        "ràng buộc hiển thị trên từng field rồi gửi JSON."
        if has_body
        else (
            "Frontend: điền path/query/header parameter theo ví dụ; các bộ lọc không bắt buộc "
            "có thể bỏ trống thay vì gửi chuỗi rỗng."
        )
    )
    response_guidance = (
        "Response JSON theo envelope `{ data, meta, error }`; dùng `meta.request_id` khi cần "
        "đối soát. Frontend phải xử lý theo HTTP status và `error.code`, không parse message."
    )
    return "\n\n".join(
        (
            f"**Mục đích:** {purpose}",
            f"**Access:** {access}",
            f"**Frontend usage:** `{method.upper()} {path}`. {input_guidance}",
            f"**Kết quả:** {response_guidance}",
        )
    )


def _enrich_parameter(parameter: dict[str, Any]) -> None:
    name = parameter["name"]
    lookup_name = (
        "product_id_query"
        if name == "product_id" and parameter["in"] == "query"
        else name
    )
    description = PARAMETER_DESCRIPTIONS.get(lookup_name)
    if description is None:
        description = (
            f"Giá trị `{name}` truyền qua {parameter['in']}; tuân thủ kiểu dữ liệu, enum và "
            "ràng buộc được Swagger hiển thị."
        )
    parameter["description"] = description
    example = PARAMETER_EXAMPLES.get(name)
    if example is None:
        example = _example_from_schema(parameter.get("schema", {}), {}, field_name=name)
    parameter["example"] = example


def _enrich_request_body(
    request_body: dict[str, Any],
    operation_summary: str,
    schemas: dict[str, Any],
) -> None:
    request_body["description"] = (
        "JSON payload cho nghiệp vụ này. Các field có dấu `*` là bắt buộc; mở phần Schema để "
        "xem enum, min/max và mô tả. UUID trong ví dụ phải được thay bằng ID thực tế."
    )
    json_content = request_body.get("content", {}).get("application/json")
    if json_content is None:
        return
    body_schema = json_content.get("schema", {})
    value = _example_from_schema(
        body_schema,
        schemas,
        include_optional=True,
        max_depth=8,
    )
    json_content["examples"] = {
        "frontendExample": {
            "summary": f"Payload mẫu — {operation_summary}",
            "description": (
                "Có thể copy trực tiếp để test format. Hãy thay UUID bằng dữ liệu tạo từ "
                "workspace hiện tại trước khi gửi request."
            ),
            "value": value if isinstance(value, dict) and value else {"example": "replace-me"},
        }
    }


def _enrich_responses(
    path: str,
    method: str,
    operation: dict[str, Any],
    is_public: bool,
) -> None:
    responses = operation.setdefault("responses", {})
    success_descriptions = {
        "200": "Thành công. `data` chứa kết quả nghiệp vụ; `meta.request_id` dùng để đối soát.",
        "201": "Đã tạo tài nguyên mới thành công và trả representation trong response envelope.",
        "202": "Đã chấp nhận xử lý bất đồng bộ. Frontend dùng Job API để theo dõi tiến độ.",
        "204": "Đã xoá thành công. Response không có body.",
    }
    for status_code, response in responses.items():
        if status_code in success_descriptions and isinstance(response, dict):
            response["description"] = success_descriptions[status_code]

    responses["422"] = {"$ref": "#/components/responses/ValidationError"}
    responses["500"] = {"$ref": "#/components/responses/InternalServerError"}
    if not is_public:
        responses["401"] = {"$ref": "#/components/responses/UnauthorizedError"}
        responses["403"] = {"$ref": "#/components/responses/ForbiddenError"}
        if "{" in path:
            responses["404"] = {"$ref": "#/components/responses/NotFoundError"}
        if method in {"post", "patch", "delete"}:
            responses["409"] = {"$ref": "#/components/responses/ConflictError"}


def _enrich_schema_fields(schemas: dict[str, Any]) -> None:
    for schema_name, component_schema in schemas.items():
        properties = component_schema.get("properties", {})
        for field_name, field_schema in properties.items():
            description = field_schema.get("description")
            if not isinstance(description, str) or len(description) < 25:
                field_schema["description"] = _field_description(schema_name, field_name)
            if "example" not in field_schema and "examples" not in field_schema:
                field_schema["example"] = _example_from_schema(
                    field_schema,
                    schemas,
                    field_name=field_name,
                    max_depth=3,
                )


def _field_description(schema_name: str, field_name: str) -> str:
    documented = FIELD_DESCRIPTIONS.get(field_name)
    if documented is not None:
        return documented
    readable = field_name.replace("_json", "").replace("_", " ")
    if field_name.endswith("_ids"):
        return (
            f"Danh sách định danh UUID cho `{readable}`; các phần tử phải thuộc cùng workspace "
            "và không nên trùng lặp."
        )
    if field_name.endswith("_id"):
        return (
            f"Định danh UUID của `{readable}`; lấy từ response API tạo/đọc tài nguyên tương ứng."
        )
    if field_name.endswith("_at"):
        return f"Thời điểm `{readable}` theo ISO 8601 UTC, ví dụ `2026-07-31T09:30:00Z`."
    if field_name.endswith("_ms"):
        return f"Giá trị `{readable}` tính bằng millisecond; số 0 biểu thị đầu timeline."
    if field_name.endswith("_json"):
        return f"Payload JSON có cấu trúc cho `{readable}`; không chứa secret hoặc credential."
    if field_name.startswith("is_") or field_name.endswith(("_required", "_confirmed")):
        return f"Cờ boolean cho `{readable}`; gửi `true` hoặc `false`, không gửi chuỗi."
    return (
        f"Trường `{readable}` của contract `{schema_name}`; nhập đúng kiểu dữ liệu và "
        "ràng buộc Swagger hiển thị."
    )


def _example_from_schema(
    schema: dict[str, Any],
    schemas: dict[str, Any],
    *,
    field_name: str | None = None,
    include_optional: bool = False,
    depth: int = 0,
    max_depth: int = 5,
    seen: frozenset[str] = frozenset(),
) -> Any:
    if depth > max_depth:
        return {}
    if "const" in schema:
        return schema["const"]
    if schema.get("default") is not None:
        return schema["default"]
    enum = schema.get("enum")
    if isinstance(enum, list) and enum:
        return enum[0]

    reference = schema.get("$ref")
    if isinstance(reference, str):
        schema_name = reference.rsplit("/", 1)[-1]
        if schema_name in seen:
            return {}
        referenced = schemas.get(schema_name, {})
        return _example_from_schema(
            referenced,
            schemas,
            field_name=field_name,
            include_optional=include_optional,
            depth=depth + 1,
            max_depth=max_depth,
            seen=seen | {schema_name},
        )

    for union_key in ("anyOf", "oneOf"):
        options = schema.get(union_key)
        if isinstance(options, list):
            non_null = [option for option in options if option.get("type") != "null"]
            if non_null:
                return _example_from_schema(
                    non_null[0],
                    schemas,
                    field_name=field_name,
                    include_optional=include_optional,
                    depth=depth + 1,
                    max_depth=max_depth,
                    seen=seen,
                )

    all_of = schema.get("allOf")
    if isinstance(all_of, list):
        merged: dict[str, Any] = {}
        for option in all_of:
            example = _example_from_schema(
                option,
                schemas,
                field_name=field_name,
                include_optional=include_optional,
                depth=depth + 1,
                max_depth=max_depth,
                seen=seen,
            )
            if isinstance(example, dict):
                merged.update(example)
        return merged

    schema_type = schema.get("type")
    schema_format = schema.get("format")
    if schema_type == "string" and schema_format == "uuid":
        return PARAMETER_EXAMPLES.get(
            field_name or "",
            "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        )
    if field_name in FIELD_EXAMPLES:
        return FIELD_EXAMPLES[field_name]
    if schema_type == "string":
        if schema_format == "date-time":
            return "2026-07-31T09:30:00Z"
        if schema_format == "date":
            return "2026-07-31"
        if schema_format in {"uri", "url"}:
            return "https://example.com/resource"
        if schema_format == "email":
            return "frontend.tester@example.com"
        return _string_example(field_name)
    if schema_type == "integer":
        minimum = schema.get("minimum", schema.get("exclusiveMinimum", 0))
        return max(1, int(minimum or 0))
    if schema_type == "number":
        minimum = float(schema.get("minimum", 0))
        maximum = schema.get("maximum")
        return min(0.85, float(maximum)) if maximum is not None else max(0.85, minimum)
    if schema_type == "boolean":
        return False
    if schema_type == "array":
        item_example = _example_from_schema(
            schema.get("items", {}),
            schemas,
            field_name=_singular(field_name),
            depth=depth + 1,
            max_depth=max_depth,
            seen=seen,
        )
        return [item_example]
    if schema_type == "object" or "properties" in schema:
        required = set(schema.get("required", []))
        result: dict[str, Any] = {}
        for property_name, property_schema in schema.get("properties", {}).items():
            if property_name not in required and not include_optional:
                continue
            result[property_name] = _example_from_schema(
                property_schema,
                schemas,
                field_name=property_name,
                include_optional=False,
                depth=depth + 1,
                max_depth=max_depth,
                seen=seen,
            )
        if result:
            return result
        if schema.get("additionalProperties"):
            return {"key": "value"}
        return {}
    if schema_type == "null":
        return None
    return _string_example(field_name)


def _string_example(field_name: str | None) -> str:
    readable = (field_name or "value").replace("_", "-")
    return f"example-{readable}"


def _singular(field_name: str | None) -> str | None:
    if field_name is None:
        return None
    if field_name.endswith("_ids"):
        return f"{field_name[:-4]}_id"
    if field_name.endswith("ies"):
        return f"{field_name[:-3]}y"
    if field_name.endswith("s"):
        return field_name[:-1]
    return field_name


def _add_error_components(components: dict[str, Any]) -> None:
    schemas = components.setdefault("schemas", {})
    schemas.update(
        {
            "ApiError": {
                "type": "object",
                "required": ["code", "message", "details"],
                "description": "Lỗi nghiệp vụ an toàn, ổn định để frontend xử lý.",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Mã lỗi máy đọc; frontend nên switch theo giá trị này.",
                        "example": "VALIDATION_ERROR",
                    },
                    "message": {
                        "type": "string",
                        "description": "Thông báo an toàn cho người dùng, không chứa stack trace.",
                        "example": "Request validation failed.",
                    },
                    "details": {
                        "type": "object",
                        "description": "Chi tiết bổ sung theo loại lỗi, có thể là object rỗng.",
                        "additionalProperties": True,
                        "example": {"field": "name", "reason": "Field is required."},
                    },
                },
            },
            "ErrorResponseMeta": {
                "type": "object",
                "required": ["request_id"],
                "properties": {
                    "request_id": {
                        "type": "string",
                        "description": "Correlation ID để đối soát request với backend logs.",
                        "example": "req_01J0FRONTENDDEMO",
                    }
                },
            },
            "ErrorEnvelope": {
                "type": "object",
                "required": ["data", "meta", "error"],
                "description": "Response envelope chuẩn khi request thất bại.",
                "properties": {
                    "data": {
                        "type": "null",
                        "description": "Luôn là `null` khi response có lỗi.",
                        "example": None,
                    },
                    "meta": {"$ref": "#/components/schemas/ErrorResponseMeta"},
                    "error": {"$ref": "#/components/schemas/ApiError"},
                },
            },
        }
    )

    errors = {
        "UnauthorizedError": (
            "Thiếu Bearer token hoặc token không hợp lệ.",
            "UNAUTHENTICATED",
            "Unauthenticated.",
        ),
        "ForbiddenError": (
            "Đã xác thực nhưng không đủ permission trong workspace.",
            "FORBIDDEN",
            "Forbidden.",
        ),
        "NotFoundError": (
            "Không tìm thấy tài nguyên trong phạm vi workspace.",
            "RESOURCE_NOT_FOUND",
            "Resource was not found.",
        ),
        "ConflictError": (
            "Request xung đột với version, state hoặc idempotency hiện tại.",
            "RESOURCE_CONFLICT",
            "Resource state conflict.",
        ),
        "ValidationError": (
            "Payload, path hoặc query parameter không qua validation.",
            "VALIDATION_ERROR",
            "Request validation failed.",
        ),
        "InternalServerError": (
            "Lỗi ngoài dự kiến; dùng request_id để backend điều tra.",
            "INTERNAL_ERROR",
            "Internal server error.",
        ),
    }
    components["responses"] = {
        name: {
            "description": description,
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorEnvelope"},
                    "examples": {
                        "standardError": {
                            "summary": description,
                            "value": {
                                "data": None,
                                "meta": {"request_id": "req_01J0FRONTENDDEMO"},
                                "error": {
                                    "code": code,
                                    "message": message,
                                    "details": {},
                                },
                            },
                        }
                    },
                }
            },
        }
        for name, (description, code, message) in errors.items()
    }
