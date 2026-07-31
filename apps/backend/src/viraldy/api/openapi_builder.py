from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from viraldy.api.openapi_metadata import (
    FIELD_DESCRIPTIONS,
    FIELD_EXAMPLES,
    HTTP_METHODS,
    PARAMETER_DESCRIPTIONS,
    PARAMETER_EXAMPLES,
    PUBLIC_PATHS,
    SPECIAL_PURPOSES,
    TAG_DESCRIPTIONS,
    TAG_DISPLAY_NAMES,
)


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
        "Trả binary `video/mp4` với cache header; lỗi vẫn dùng JSON error envelope chuẩn."
        if path.startswith("/outputs/renders/")
        else (
            "Response JSON theo envelope `{ data, meta, error }`; dùng `meta.request_id` khi cần "
            "đối soát. Frontend phải xử lý theo HTTP status và `error.code`, không parse message."
        )
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
    if path.startswith("/outputs/renders/") and isinstance(responses.get("200"), dict):
        responses["200"] = {
            "description": "Review clip MP4. Có thể dùng trực tiếp làm `src` của video player.",
            "content": {"video/mp4": {"schema": {"type": "string", "format": "binary"}}},
            "headers": {
                "Cache-Control": {
                    "description": "Chính sách cache public của review clip.",
                    "schema": {"type": "string", "example": "public, max-age=3600"},
                }
            },
        }

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
        documented_example = FIELD_EXAMPLES[field_name]
        if _matches_schema_type(documented_example, schema_type, schema):
            return documented_example
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
            if property_name not in required and _is_structured_schema(property_schema, schemas):
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


def _is_structured_schema(
    schema: dict[str, Any],
    schemas: dict[str, Any],
    seen: frozenset[str] = frozenset(),
) -> bool:
    reference = schema.get("$ref")
    if isinstance(reference, str):
        schema_name = reference.rsplit("/", 1)[-1]
        if schema_name in seen:
            return True
        return _is_structured_schema(
            schemas.get(schema_name, {}),
            schemas,
            seen | {schema_name},
        )
    for union_key in ("anyOf", "oneOf"):
        options = schema.get(union_key)
        if isinstance(options, list):
            return any(
                _is_structured_schema(option, schemas, seen)
                for option in options
                if option.get("type") != "null"
            )
    if schema.get("type") == "array":
        return _is_structured_schema(schema.get("items", {}), schemas, seen)
    return bool(schema.get("properties"))


def _matches_schema_type(value: Any, schema_type: object, schema: dict[str, Any]) -> bool:
    if schema.get("properties"):
        return False
    if schema_type == "string":
        return isinstance(value, str)
    if schema_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if schema_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if schema_type == "boolean":
        return isinstance(value, bool)
    if schema_type == "array":
        return isinstance(value, list)
    if schema_type == "object":
        return isinstance(value, dict)
    return True


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
