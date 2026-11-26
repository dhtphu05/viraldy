from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from tests.unit.test_smart_remake_generation_progress import fixture, image
from tests.unit.test_smart_remake_project_library import routes as _routes
from tests.unit.test_smart_remake_project_library import stored as _stored
from viraldy.modules.smart_remake import project_library as module
from viraldy.modules.smart_remake.budget_models import SmartRemakeAttemptModel
from viraldy.modules.smart_remake.models import SmartRemakeOperationModel

routes = _routes
stored = _stored


def activity_rows(stored, operations, attempts=()):
    execute = stored.db.execute.side_effect

    def read(statement):
        entity = statement.column_descriptions[0].get("entity")
        values = None
        if entity is SmartRemakeOperationModel:
            values = operations
        elif entity is SmartRemakeAttemptModel:
            values = attempts
        if values is not None:
            return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: list(values)))
        return execute(statement)

    stored.db.execute.side_effect = read


@pytest.mark.asyncio
async def test_unfinished_optin_includes_owned_images_before_any_video_without_changing_default(
    stored,
):
    row, operation = fixture()
    image(row, operation, 0)
    identity = stored.add(
        row.workspace_id,
        state={
            **row.state_json,
            "finalStorageKey": None,
            "status": "incomplete",
            "provider": "kie",
        },
        context=row.context_json,
    )
    operation.project_id = identity
    activity_rows(stored, [operation])
    default = await module.list_project_library(
        stored.db,
        row.workspace_id,
        SimpleNamespace(ai_mode="live"),
        limit=24,
        offset=0,
    )
    assert default["items"] == []
    result = await module.list_project_library(
        stored.db,
        row.workspace_id,
        SimpleNamespace(ai_mode="live"),
        limit=24,
        offset=0,
        include_unfinished=True,
    )
    item = result["items"][0]
    assert item["id"] == str(identity)
    assert item["videos"] == [] and item["finalVideoUrl"] == ""
    assert item["activity"]["kind"] == "render"
    assert item["activity"]["stage"] == "preparing_image"
    assert item["activity"]["plannedVideoCount"] == 2
    assert item["activity"]["submittedVideoCount"] == 0
    assert item["activity"]["completedImageCount"] == 1
    assert item.get("downloadUrl") is None


@pytest.mark.asyncio
async def test_unfinished_optin_keeps_workspace_and_rights_filters_and_does_not_open_a_service(
    stored, monkeypatch
):
    workspace = uuid4()
    visible = stored.add(workspace, state={"finalStorageKey": None, "status": "draft"})
    stored.add(uuid4(), state={"finalStorageKey": None})
    stored.add(workspace, state={"finalStorageKey": None}, context={"p0": {"status": "deleted"}})
    stored.add(
        workspace,
        state={"finalStorageKey": None},
        context={"p0": {"rights": {"product": {"revoked": True}}}},
    )
    activity_rows(stored, [])
    result = await module.list_project_library(
        stored.db,
        workspace,
        SimpleNamespace(ai_mode="live"),
        limit=24,
        offset=0,
        include_unfinished=True,
    )
    assert [item["id"] for item in result["items"]] == [str(visible)]
    assert result["total"] == 1
    assert result["items"][0]["activity"]["status"] == "not_started"


@pytest.mark.asyncio
async def test_active_operation_wins_over_newer_metadata_and_foreign_rows_are_not_projected(stored):
    row, operation = fixture()
    identity = stored.add(
        row.workspace_id,
        state={
            **row.state_json,
            "finalStorageKey": None,
            "status": "incomplete",
            "provider": "kie",
        },
        context=row.context_json,
    )
    operation.project_id = identity
    metadata = SimpleNamespace(
        id=uuid4(),
        project_id=identity,
        status="completed",
        created_at=operation.created_at,
        result_json={"kind": "context"},
    )
    foreign = SimpleNamespace(
        id=uuid4(),
        project_id=uuid4(),
        status="running",
        created_at=operation.created_at,
        result_json={"kind": "render", "errorCode": "PRIVATE_OTHER_PROJECT"},
    )
    activity_rows(stored, [metadata, foreign, operation])
    result = await module.list_project_library(
        stored.db,
        row.workspace_id,
        SimpleNamespace(ai_mode="live"),
        limit=24,
        offset=0,
        include_unfinished=True,
    )
    assert result["items"][0]["activity"]["operationId"] == str(operation.id)
    assert "PRIVATE_OTHER_PROJECT" not in str(result)


@pytest.mark.asyncio
async def test_collection_route_explicit_unfinished_optin_preserves_read_permission(routes):
    response = await routes.client.get(f"{routes.base}?includeUnfinished=true")
    assert response.status_code == 200
    assert routes.listing.await_args.kwargs["include_unfinished"] is True
    routes.authorize.assert_awaited_once()
