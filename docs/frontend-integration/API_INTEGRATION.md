# Viraldy API Integration Guide

FastAPI OpenAPI là contract chính thức giữa backend và frontend. Backend sinh spec
từ code đang chạy và có thể export generated artifact tại
[`docs/api/openapi.json`](../api/openapi.json).

## Documentation URLs

Khi backend chạy tại `http://localhost:8000`:

| URL | Mục đích |
| --- | --- |
| `http://localhost:8000/docs` | Swagger UI để đọc contract và gửi request trực tiếp |
| `http://localhost:8000/redoc` | ReDoc để đọc tài liệu theo dạng reference |
| `http://localhost:8000/openapi.json` | OpenAPI 3.1 JSON của instance đang chạy |

Swagger UI đã bật:

- **Try it out** mặc định;
- lưu Bearer token trong phiên trình duyệt;
- hiển thị `operationId`, thời gian request và bộ lọc endpoint;
- payload mẫu `frontendExample` cho mọi JSON request body;
- mô tả, enum, constraint và example cho từng input.

## Frontend quick start

1. Chạy backend:

   ```bash
   cd apps/backend
   uv run uvicorn viraldy.api.main:app --reload --port 8000
   ```

2. Mở `/docs`, gọi `GET /api/v1/auth/config` để xác định auth mode.
3. Với local development, nhấn **Authorize**, nhập `local-test`, rồi đóng dialog.
   Swagger sẽ tự gửi `Authorization: Bearer local-test`; không nhập chữ `Bearer`
   trong dialog.
4. Gọi `GET /api/v1/workspaces` hoặc tạo workspace mới.
5. Thay UUID minh hoạ trong `frontendExample` bằng ID thật từ response bước trước.
6. Gửi request và xử lý kết quả theo HTTP status, `error.code` và
   `meta.request_id`.

## Response envelope

JSON success:

```json
{
  "data": {},
  "meta": {
    "request_id": "req_01J0FRONTENDDEMO",
    "pagination": null
  },
  "error": null
}
```

JSON error:

```json
{
  "data": null,
  "meta": {
    "request_id": "req_01J0FRONTENDDEMO"
  },
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed.",
    "details": {}
  }
}
```

Frontend phải điều khiển logic theo HTTP status và `error.code`, không so sánh
`error.message`. Gửi `meta.request_id` cho backend khi cần điều tra.

Các endpoint tải media có thể trả binary (ví dụ `video/mp4`) và các endpoint
`DELETE` thành công trả `204 No Content`; hai trường hợp này không có success
envelope JSON.

## Authentication and workspace authorization

- `401 Unauthorized`: thiếu token, token sai hoặc hết hạn.
- `403 Forbidden`: token hợp lệ nhưng user không có workspace permission.
- `404 Not Found`: tài nguyên không tồn tại hoặc không thuộc workspace hiện tại.

Production sử dụng OIDC access token. Không lưu token trong source code, log,
analytics event hoặc URL. Local token `local-test` chỉ dùng khi backend được cấu
hình ở local-test mode.

## Async jobs and idempotency

Các lệnh process, analyze, generation, scoring và preflight có thể trả
`202 Accepted`. Frontend cần:

1. lưu `job.id` từ `data`;
2. poll `GET /api/v1/workspaces/{workspace_id}/jobs/{job_id}`;
3. dừng khi trạng thái là `succeeded` hoặc `failed`;
4. hiển thị `safe_error_code`/`safe_error_message` khi thất bại.

Khi retry cùng một ý định, giữ nguyên `Idempotency-Key`. Chỉ tạo key mới khi
người dùng chủ động tạo một tác vụ mới.

## Using generated examples

Mọi `frontendExample` hợp lệ về JSON shape và format, nhưng UUID chỉ là placeholder.
Một request business hợp lệ vẫn cần:

- ID thuộc cùng workspace;
- resource ở đúng lifecycle state;
- user có permission tương ứng;
- version không stale;
- asset đã upload/validate;
- rights confirmation khi generation yêu cầu.

## Export and contract verification

Sau khi thêm hoặc sửa endpoint:

```bash
cd apps/backend
uv run pytest tests/contract/test_openapi.py -q
uv run python scripts/export_openapi.py
```

File `docs/api/openapi.json` đang được Git ignore vì là generated artifact. CI hoặc
frontend có thể chạy lệnh export từ cùng commit backend để validate contract, review
diff tạm thời hoặc tái sinh typed client.
