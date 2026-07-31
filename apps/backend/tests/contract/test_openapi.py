from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from viraldy.api.main import app

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


def _operations(schema: dict[str, Any]) -> Iterator[tuple[str, str, dict[str, Any]]]:
    for path, path_item in schema["paths"].items():
        for method, operation in path_item.items():
            if method in HTTP_METHODS:
                yield path, method, operation


def _referenced_request_schemas(schema: dict[str, Any]) -> set[str]:
    components = schema["components"]["schemas"]
    pending: list[str] = []
    visited: set[str] = set()

    def collect_refs(node: object) -> None:
        if isinstance(node, dict):
            reference = node.get("$ref")
            if isinstance(reference, str):
                pending.append(reference.rsplit("/", 1)[-1])
            for value in node.values():
                collect_refs(value)
        elif isinstance(node, list):
            for value in node:
                collect_refs(value)

    for _, _, operation in _operations(schema):
        request_schema = (
            operation.get("requestBody", {})
            .get("content", {})
            .get("application/json", {})
            .get("schema", {})
        )
        collect_refs(request_schema)

    while pending:
        schema_name = pending.pop()
        if schema_name in visited or schema_name not in components:
            continue
        visited.add(schema_name)
        collect_refs(components[schema_name])
    return visited


def test_openapi_generation_contains_foundation_routes() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    assert "/api/v1/workspaces" in paths
    assert "/api/v1/workspaces/{workspace_id}/assets/upload-sessions" in paths
    assert "/api/v1/workspaces/{workspace_id}/assets/{asset_id}/process" in paths
    assert "/api/v1/workspaces/{workspace_id}/jobs/{job_id}" in paths
    assert "/api/v1/workspaces/{workspace_id}/model-runs" in paths
    assert "/api/v1/workspaces/{workspace_id}/model-runs/{model_run_id}" in paths
    assert "/api/v1/workspaces/{workspace_id}/generation/storyboards" in paths
    assert "/api/v1/workspaces/{workspace_id}/generation/concept-video-previews" in paths
    assert "/api/v1/workspaces/{workspace_id}/generation/runs/{generation_run_id}" in paths


def test_response_envelope_schema_is_registered() -> None:
    schema = app.openapi()
    assert "Envelope" in schema["components"]["schemas"]


def test_openapi_contains_asset_revision_routes() -> None:
    paths = app.openapi()["paths"]

    assert "/api/v1/workspaces/{workspace_id}/assets/{asset_id}/versions/upload-sessions" in paths
    assert (
        "/api/v1/workspaces/{workspace_id}/assets/{asset_id}/versions/"
        "{asset_version_id}/complete-upload" in paths
    )
    assert "/api/v1/workspaces/{workspace_id}/assets/{asset_id}/versions" in paths


def test_openapi_contains_private_beta_health_routes() -> None:
    paths = app.openapi()["paths"]

    assert "/health/live" in paths
    assert "/health/ready" in paths
    assert "/health/dependencies" in paths
    assert "/health/worker" in paths


def test_openapi_contains_audited_hard_deletion_routes() -> None:
    paths = app.openapi()["paths"]

    assert "/api/v1/workspaces/{workspace_id}/deletions" in paths
    assert "/api/v1/workspaces/{workspace_id}/deletions/{resource_type}/{resource_id}" in paths
    assert "/api/v1/workspaces/{workspace_id}/deletions/retention" in paths
    direct_delete_paths = (
        "/api/v1/workspaces/{workspace_id}",
        "/api/v1/workspaces/{workspace_id}/products/{product_id}",
        "/api/v1/workspaces/{workspace_id}/assets/{asset_id}",
        "/api/v1/workspaces/{workspace_id}/references/{reference_id}",
        "/api/v1/workspaces/{workspace_id}/creative-dna/{dna_version_id}",
        "/api/v1/workspaces/{workspace_id}/pattern-kits/{pattern_kit_id}",
        "/api/v1/workspaces/{workspace_id}/viral-kits/{viral_kit_id}",
        "/api/v1/workspaces/{workspace_id}/campaign-packs/{campaign_pack_id}",
    )
    assert all("delete" in paths[path] for path in direct_delete_paths)


def test_openapi_contains_campaign_pack_export_route() -> None:
    paths = app.openapi()["paths"]

    export_path = "/api/v1/workspaces/{workspace_id}/campaign-packs/{campaign_pack_id}/exports"
    assert "post" in paths[export_path]


def test_openapi_has_professional_api_and_tag_metadata() -> None:
    schema = app.openapi()
    info = schema["info"]

    assert info["title"] == "Viraldy API"
    assert len(info["summary"]) >= 40
    assert len(info["description"]) >= 500
    assert "Authorization: Bearer" in info["description"]
    assert "Frontend quick start" in info["description"]
    assert schema["servers"][0]["url"] == "/"

    declared_tags = {tag["name"]: tag for tag in schema["tags"]}
    operation_tags = {
        tag
        for _, _, operation in _operations(schema)
        for tag in operation.get("tags", [])
    }
    assert operation_tags <= declared_tags.keys()
    assert all(len(declared_tags[tag]["description"]) >= 80 for tag in operation_tags)


def test_every_operation_is_documented_and_has_stable_identity() -> None:
    schema = app.openapi()
    operation_ids: list[str] = []

    for path, _, operation in _operations(schema):
        operation_ids.append(operation["operationId"])
        assert len(operation["summary"]) >= 8
        assert len(operation["description"]) >= 180
        assert "Frontend" in operation["description"]
        assert operation["tags"]
        assert "422" in operation["responses"]
        assert "500" in operation["responses"]

        authorization_parameters = [
            parameter
            for parameter in operation.get("parameters", [])
            if parameter["name"].lower() == "authorization"
        ]
        assert authorization_parameters == []
        if path in PUBLIC_PATHS:
            assert operation["security"] == []
        else:
            assert operation["security"] == [{"BearerAuth": []}]
            assert "401" in operation["responses"]
            assert "403" in operation["responses"]

    assert len(operation_ids) == len(set(operation_ids))


def test_parameters_are_frontend_friendly() -> None:
    schema = app.openapi()

    for _, _, operation in _operations(schema):
        for parameter in operation.get("parameters", []):
            assert len(parameter["description"]) >= 25
            parameter_schema = parameter["schema"]
            has_input_hint = any(
                key in parameter for key in ("example", "examples")
            ) or any(
                key in parameter_schema
                for key in ("example", "examples", "default", "enum")
            )
            assert has_input_hint, parameter


def test_json_request_bodies_have_copy_ready_examples() -> None:
    schema = app.openapi()
    request_body_count = 0

    for _, _, operation in _operations(schema):
        request_body = operation.get("requestBody")
        if request_body is None:
            continue
        json_content = request_body.get("content", {}).get("application/json")
        if json_content is None:
            continue
        request_body_count += 1
        assert len(request_body["description"]) >= 60
        frontend_example = json_content["examples"]["frontendExample"]
        assert len(frontend_example["summary"]) >= 10
        assert len(frontend_example["description"]) >= 40
        assert isinstance(frontend_example["value"], dict)
        assert frontend_example["value"]

    assert request_body_count >= 30


def test_request_schema_fields_have_descriptions_and_examples() -> None:
    schema = app.openapi()
    components = schema["components"]["schemas"]
    request_schemas = _referenced_request_schemas(schema)

    assert len(request_schemas) >= 30
    for schema_name in request_schemas:
        for field_name, field_schema in components[schema_name].get("properties", {}).items():
            assert len(field_schema["description"]) >= 25, f"{schema_name}.{field_name}"
            assert "example" in field_schema or "examples" in field_schema, (
                f"{schema_name}.{field_name}"
            )


def test_standard_error_contracts_are_reusable_components() -> None:
    schema = app.openapi()
    security_schemes = schema["components"]["securitySchemes"]
    responses = schema["components"]["responses"]

    assert security_schemes["BearerAuth"]["type"] == "http"
    assert security_schemes["BearerAuth"]["scheme"] == "bearer"
    assert security_schemes["BearerAuth"]["bearerFormat"] == "JWT"
    assert {
        "UnauthorizedError",
        "ForbiddenError",
        "NotFoundError",
        "ConflictError",
        "ValidationError",
        "InternalServerError",
    } <= responses.keys()
