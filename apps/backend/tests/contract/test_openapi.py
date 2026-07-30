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
