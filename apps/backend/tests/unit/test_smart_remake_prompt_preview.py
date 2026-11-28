"""The script-review preview uses final KIE prose without paid work or persistence."""

import copy
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from tests.unit.test_provider_group_planning import context
from tests.unit.test_smart_remake_grouped_workflow import grouped  # noqa: F401


def row_and_repository():
    data = context(count=2)
    workspace, project = uuid4(), uuid4()
    row = SimpleNamespace(
        id=project,
        workspace_id=workspace,
        revision=3,
        context_json=data,
        state_json={
            "revision": 3,
            "scenes": [{"id": u["id"]} for u in data["renderPlan"]["units"]],
            "renderPlan": copy.deepcopy(data["renderPlan"]),
        },
    )
    repo = SimpleNamespace(
        project=AsyncMock(return_value=row),
        session=SimpleNamespace(commit=AsyncMock(side_effect=AssertionError("No writes"))),
    )
    return row, repo


async def test_saved_script_preview_preserves_state_and_returns_every_provider_clip():
    from viraldy.modules.smart_remake.generation_prompt_preview import (
        GenerationPromptPreviewRequest,
        preview_generation_prompts,
    )

    row, repo = row_and_repository()
    before = copy.deepcopy(row.context_json)
    result = await preview_generation_prompts(
        repo, row.workspace_id, row.id, GenerationPromptPreviewRequest(expectedRevision=3)
    )
    assert result["projectId"] == str(row.id) and result["revision"] == 3
    assert len(result["groups"]) == 1
    assert "Move the seller bottle naturally." in result["groups"][0]["prompt"]
    assert "Keep every source scene." in result["groups"][0]["prompt"]
    assert "https://" not in result["groups"][0]["prompt"]
    assert row.context_json == before
    repo.session.commit.assert_not_awaited()


async def test_local_unsaved_scene_edits_and_requirements_are_previewed_without_saving():
    from viraldy.modules.smart_remake.generation_prompt_preview import (
        GenerationPromptPreviewRequest,
        preview_generation_prompts,
    )

    row, repo = row_and_repository()
    before = copy.deepcopy(row.context_json)
    drafts = [
        {
            "renderUnitId": u["id"],
            **{key: scene[key] for key in ("prompt", "imagePrompt", "videoPrompt")},
        }
        for u, scene in zip(
            row.context_json["renderPlan"]["units"],
            row.context_json["sceneMap"]["scenes"],
            strict=True,
        )
    ]
    drafts[0]["videoPrompt"] = "LOCAL DRAFT: rotate the bottle clockwise."
    request = GenerationPromptPreviewRequest(
        expectedRevision=3,
        scenePrompts=drafts,
        requirements={"intent": "LOCAL REQUIREMENT: preserve the lid", "keep": ["blue color"]},
    )
    result = await preview_generation_prompts(repo, row.workspace_id, row.id, request)
    assert "LOCAL DRAFT: rotate the bottle clockwise." in result["groups"][0]["prompt"]
    assert "LOCAL REQUIREMENT: preserve the lid" in result["groups"][0]["prompt"]
    assert row.context_json == before


@pytest.mark.parametrize("change", ["revision", "workspace", "deleted", "ordering"])
async def test_preview_rejects_stale_or_foreign_script_bindings(change):
    from viraldy.modules.smart_remake.generation_prompt_preview import (
        GenerationPromptPreviewRequest,
        preview_generation_prompts,
    )
    from viraldy.shared.errors.base import AppError

    row, repo = row_and_repository()
    workspace = row.workspace_id
    drafts = [
        {
            "renderUnitId": u["id"],
            **{key: scene[key] for key in ("prompt", "imagePrompt", "videoPrompt")},
        }
        for u, scene in zip(
            row.context_json["renderPlan"]["units"],
            row.context_json["sceneMap"]["scenes"],
            strict=True,
        )
    ]
    revision = 2 if change == "revision" else 3
    if change == "workspace":
        workspace = uuid4()
    elif change == "deleted":
        row.context_json["p0"]["status"] = "deleted"
    elif change == "ordering":
        drafts.reverse()
    with pytest.raises(AppError):
        await preview_generation_prompts(
            repo,
            workspace,
            row.id,
            GenerationPromptPreviewRequest(expectedRevision=revision, scenePrompts=drafts),
        )


@pytest.mark.parametrize("model", ["veo3_lite", "wan/3-0-video"])
@pytest.mark.parametrize("edited", [False, True])
async def test_preview_prompt_matches_the_final_workflow_request_byte_for_byte(
    model,
    edited,
    monkeypatch,
    grouped,  # noqa: F811
):
    from viraldy.modules.smart_remake.generation_expectations import (
        build_generation_expectations,
        expectations_hash,
    )
    from viraldy.modules.smart_remake.generation_prompt_preview import (
        GenerationPromptPreviewRequest,
        preview_generation_prompts,
    )
    from viraldy.modules.smart_remake.scene_prompt_drafts import apply_scene_prompt_drafts

    grouped.row.revision = 1
    grouped.row.context_json["renderPlan"]["videoModel"] = model
    grouped.row.state_json["renderPlan"] = copy.deepcopy(grouped.row.context_json["renderPlan"])
    # Use the actual pure provider adapter, rather than the transport test's short prompt stub.
    from viraldy.modules.smart_remake import kie_workflow
    from viraldy.modules.smart_remake.engine import kie_adapter

    kie_adapter.build_kie_group_request = grouped.real_adapter
    # This transport fixture has no persisted intake; policy is covered at the API boundary.
    monkeypatch.setattr(kie_workflow, "require_generation_policy", AsyncMock())
    payload = GenerationPromptPreviewRequest(expectedRevision=1)
    if edited:
        drafts = [
            {
                "renderUnitId": unit["id"],
                **{key: scene[key] for key in ("prompt", "imagePrompt", "videoPrompt")},
            }
            for unit, scene in zip(
                grouped.row.context_json["renderPlan"]["units"],
                grouped.row.context_json["sceneMap"]["scenes"],
                strict=True,
            )
        ]
        drafts[0]["videoPrompt"] = "  Rotate the bottle clockwise and keep the lid visible.\n"
        payload = GenerationPromptPreviewRequest(
            expectedRevision=1,
            scenePrompts=drafts,
            requirements={"intent": "Preserve the label", "keep": ["blue lid"]},
        )
    planned = await preview_generation_prompts(
        grouped.repair.repository,
        grouped.row.workspace_id,
        grouped.row.id,
        payload,
    )
    assert grouped.client.uploads == [] and grouped.client.submits == [] and grouped.images == []
    if edited:
        # Mirror submission's normalization and expectation refresh after saving requirements.
        state = {
            **grouped.row.state_json,
            "renderPlan": copy.deepcopy(grouped.row.context_json["renderPlan"]),
        }
        data, state = apply_scene_prompt_drafts(
            grouped.row.context_json,
            state,
            [draft.model_dump(exclude={"renderUnitId"}) for draft in payload.scenePrompts],
        )
        data["p0"] = {
            **data.get("p0", {}),
            "requirements": payload.requirements.model_dump(mode="json"),
        }
        snapshot = build_generation_expectations(data)
        data.update(generationExpectations=snapshot, expectationsHash=expectations_hash(snapshot))
        grouped.row.context_json, grouped.row.state_json = data, state
        assert "Rotate the bottle clockwise" in planned["groups"][0]["prompt"]
        assert "Preserve the label" in planned["groups"][0]["prompt"]
    await grouped.runner._freeze_plan(grouped.row, grouped.op)
    actual = [
        (await grouped.runner._request(grouped.row, grouped.op, 0, group))[0]
        for group in grouped.groups
    ]
    assert [value["prompt"] for value in planned["groups"]] == [
        request["input"]["prompt"] for request in actual
    ]
    assert [value["model"] for value in planned["groups"]] == [
        request["model"] for request in actual
    ]


async def test_scene_prompt_whitespace_is_not_changed_or_labeled_as_a_new_edit():
    from viraldy.modules.smart_remake.generation_prompt_preview import (
        GenerationPromptPreviewRequest,
        preview_generation_prompts,
    )

    row, repo = row_and_repository()
    scene = row.context_json["sceneMap"]["scenes"][0]
    scene["videoPrompt"] = "  " + scene["videoPrompt"] + "\n"
    baseline = await preview_generation_prompts(
        repo, row.workspace_id, row.id, GenerationPromptPreviewRequest(expectedRevision=3)
    )
    drafts = [
        {
            "renderUnitId": u["id"],
            **{key: scene[key] for key in ("prompt", "imagePrompt", "videoPrompt")},
        }
        for u, scene in zip(
            row.context_json["renderPlan"]["units"],
            row.context_json["sceneMap"]["scenes"],
            strict=True,
        )
    ]
    current = await preview_generation_prompts(
        repo,
        row.workspace_id,
        row.id,
        GenerationPromptPreviewRequest(expectedRevision=3, scenePrompts=drafts),
    )
    assert current == baseline
    assert row.context_json["sceneMap"]["scenes"][0]["videoPrompt"].startswith("  ")


async def test_preview_http_is_authorized_and_never_constructs_media_or_commits(monkeypatch):
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from viraldy.api.dependencies.auth import get_current_user
    from viraldy.api.middleware.errors import app_error_handler
    from viraldy.modules.smart_remake import generation_media_router
    from viraldy.platform.database.session import get_async_session
    from viraldy.shared.errors.base import AppError, ForbiddenError

    row, repo = row_and_repository()
    permission = AsyncMock()
    monkeypatch.setattr(generation_media_router, "require_workspace_permission", permission)
    monkeypatch.setattr(generation_media_router, "RepairRepository", lambda db: repo)
    monkeypatch.setattr(
        generation_media_router,
        "service_for",
        lambda *args: (_ for _ in ()).throw(AssertionError("No media service")),
    )
    app = FastAPI()
    app.include_router(
        generation_media_router.router, prefix="/workspaces/{workspace_id}/smart-remake"
    )
    app.add_exception_handler(AppError, app_error_handler)

    async def session():
        yield SimpleNamespace()

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4())
    app.dependency_overrides[get_async_session] = session
    path = (
        f"/workspaces/{row.workspace_id}/smart-remake/projects/{row.id}/generation/prompt-preview"
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        reply = await client.post(path, json={"expectedRevision": 3})
        assert reply.status_code == 200
        assert reply.json()["data"]["groups"][0]["prompt"]
        too_long = await client.post(
            path,
            json={
                "expectedRevision": 3,
                "requirements": {
                    "intent": "Keep the bottle",
                    "keep": ["x" * 1999] * 40,
                },
            },
        )
        assert too_long.status_code == 422
        assert "x" * 1999 not in too_long.text
        repo.project.reset_mock()
        permission.side_effect = ForbiddenError()
        denied = await client.post(path, json={"expectedRevision": 3})
        assert denied.status_code == 403
        repo.project.assert_not_awaited()
    repo.session.commit.assert_not_awaited()
