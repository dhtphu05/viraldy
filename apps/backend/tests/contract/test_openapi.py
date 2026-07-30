from __future__ import annotations

from viraldy.api.main import app


def test_openapi_generation_contains_foundation_routes() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    assert "/api/v1/workspaces" in paths
    assert "/api/v1/workspaces/{workspace_id}/assets/upload-sessions" in paths
    assert "/api/v1/workspaces/{workspace_id}/assets/{asset_id}/process" in paths
    assert "/api/v1/workspaces/{workspace_id}/jobs/{job_id}" in paths
    assert "/api/v1/workspaces/{workspace_id}/generation/storyboards" in paths
    assert "/api/v1/workspaces/{workspace_id}/generation/concept-video-previews" in paths
    assert "/api/v1/workspaces/{workspace_id}/generation/runs/{generation_run_id}" in paths


def test_response_envelope_schema_is_registered() -> None:
    schema = app.openapi()
    assert "Envelope" in schema["components"]["schemas"]


def test_openapi_contains_private_beta_health_routes() -> None:
    paths = app.openapi()["paths"]

    assert "/health/live" in paths
    assert "/health/ready" in paths
    assert "/health/dependencies" in paths
    assert "/health/worker" in paths


def test_openapi_contains_audited_hard_deletion_routes() -> None:
    paths = app.openapi()["paths"]

    assert "/api/v1/workspaces/{workspace_id}/deletions" in paths
    assert (
        "/api/v1/workspaces/{workspace_id}/deletions/{resource_type}/{resource_id}"
        in paths
    )
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
