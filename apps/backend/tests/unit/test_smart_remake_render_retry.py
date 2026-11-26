"""A confirmed render retry preserves the seller's existing creative edits."""

from __future__ import annotations

import copy
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from tests.smart_remake_expectations import install_expectations
from tests.unit.test_smart_remake_timeline_runtime import Media, Repo, project
from viraldy.modules.smart_remake import kie_workflow, service, timeline_service
from viraldy.modules.smart_remake.engine.prompt_edits import scene_edit_directions
from viraldy.modules.smart_remake.repair_service import RepairService


async def test_explicit_initial_render_retry_with_unchanged_prompts_preserves_snapshot(monkeypatch):
    row = project((192,))
    row.context_json["renderPlan"]["groupingPolicy"] = "fixed_provider_windows"
    row.context_json.update(productMimeType="image/png", referenceAnalysis={})
    row.state_json["scenes"][0].update(activeVersionId=None, versions=[])
    row.state_json["draftTimeline"]["items"][0]["versionId"] = None
    install_expectations(row.context_json, state=row.state_json, source_bytes=b"clip",
                         product_bytes=b"clip")
    repo = Repo(row)
    repair = RepairService(repo, Media(), row.workspace_id)
    monkeypatch.setattr(kie_workflow, "_service", lambda *args: repair)
    monkeypatch.setattr(service, "require_kie_renderer", lambda *args: None)
    # This regression isolates persisted prompt mutation; manifest validity has
    # separate tests and the real-HTTP grouped workflow covers the complete plan.
    monkeypatch.setattr(timeline_service, "validate_manifest", lambda *args: None)
    queue = AsyncMock(return_value=SimpleNamespace(id=uuid4()))
    monkeypatch.setattr(timeline_service, "_queue", queue)
    monkeypatch.setattr(kie_workflow, "_render_response", AsyncMock(return_value={}))
    settings = SimpleNamespace(ai_mode="fixture")
    drafts = [{"prompt": "Show the observed bottle slowly", "imagePrompt": "i", "videoPrompt": "v"}]
    await timeline_service.enqueue_timeline_render(
        object(), settings, row.workspace_id, row.id, 1, "initial", prompt_drafts=drafts,
    )
    first = repo.operations["initial"]
    original_scene = copy.deepcopy(row.context_json["sceneMap"]["scenes"][0])
    original_expectations = copy.deepcopy(row.context_json["generationExpectations"])
    original_hash = row.context_json["expectationsHash"]
    assert scene_edit_directions(original_scene)
    first.status = "failed"
    await timeline_service.enqueue_timeline_render(
        object(), settings, row.workspace_id, row.id, 2, "confirmed-retry", prompt_drafts=drafts,
    )
    assert row.context_json["sceneMap"]["scenes"][0] == original_scene
    assert row.context_json["generationExpectations"] == original_expectations
    assert row.context_json["expectationsHash"] == original_hash
    assert repo.operations["confirmed-retry"].result_json["expectationsHash"] == original_hash
    assert queue.await_count == 2
