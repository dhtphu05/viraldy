from __future__ import annotations

from collections.abc import AsyncIterator
from typing import cast
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.api.dependencies.auth import get_current_user
from viraldy.modules.ugc_review.router import router
from viraldy.platform.auth.current_user import CurrentUser
from viraldy.platform.database.session import get_async_session


def test_router_exposes_workspace_scoped_review_flow() -> None:
    routes = {(route.path, method) for route in router.routes for method in route.methods or []}

    assert ("/workspaces/{workspace_id}/ugc-reviews", "POST") in routes
    assert ("/workspaces/{workspace_id}/ugc-reviews/{review_id}/status", "GET") in routes
    assert ("/workspaces/{workspace_id}/ugc-reviews/{review_id}", "GET") in routes
    assert (
        "/workspaces/{workspace_id}/ugc-reviews/{review_id}/recommendations/"
        "{recommendation_id}/actions",
        "POST",
    ) in routes
    assert ("/workspaces/{workspace_id}/ugc-reviews/{review_id}/revisions", "POST") in routes
    assert (
        "/workspaces/{workspace_id}/ugc-reviews/{review_id}/comparisons/latest",
        "GET",
    ) in routes


def test_openapi_preserves_strict_flat_multipart_contract() -> None:
    app = FastAPI()
    app.include_router(router)
    schema = app.openapi()
    request_body = schema["paths"]["/workspaces/{workspace_id}/ugc-reviews"]["post"][
        "requestBody"
    ]
    form_schema = request_body["content"]["multipart/form-data"]["schema"]
    component_name = form_schema["$ref"].rsplit("/", 1)[-1]
    properties = schema["components"]["schemas"][component_name]["properties"]

    assert set(properties) >= {
        "asset_id",
        "asset_version_id",
        "commerce_domain",
        "intended_use",
        "creator_brief",
        "video_file",
    }
    assert properties["intended_use"]["enum"] == [
        "organic",
        "affiliate",
        "paid_candidate",
        "spark_candidate",
        "unknown",
    ]


def test_invalid_multipart_form_returns_422_instead_of_500() -> None:
    app = FastAPI()
    app.include_router(router)

    async def fake_session() -> AsyncIterator[AsyncSession]:
        yield cast(AsyncSession, object())

    async def fake_current_user() -> CurrentUser:
        return CurrentUser(
            id=uuid4(),
            external_auth_id="test-user",
            email="test@example.com",
            display_name="Test User",
            status="active",
        )

    app.dependency_overrides[get_async_session] = fake_session
    app.dependency_overrides[get_current_user] = fake_current_user
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        f"/workspaces/{uuid4()}/ugc-reviews",
        data={
            "asset_id": str(uuid4()),
            "asset_version_id": str(uuid4()),
            "intended_use": "guaranteed_roas",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "literal_error"
