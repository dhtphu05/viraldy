from __future__ import annotations

import copy
import hashlib
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from tests.smart_remake_expectations import install_expectations
from tests.unit.test_smart_remake_grouped_plan import grouped_runtime as _grouped_fixture
from tests.unit.test_smart_remake_timeline_runtime import (
    frozen_media,
    request,
)
from tests.unit.test_smart_remake_timeline_runtime import (
    runtime as _runtime_fixture,
)
from viraldy.modules.smart_remake import kie_workflow
from viraldy.modules.smart_remake import timeline_service as module
from viraldy.modules.smart_remake.assembly_snapshots import content_hash
from viraldy.modules.smart_remake.project_policy import constraints_hash, policy_hash, stable_hash
from viraldy.modules.smart_remake.repair_schemas import PublishTimelineRequest
from viraldy.modules.smart_remake.timeline_planner import build_render_groups
from viraldy.shared.errors.base import AppError

runtime = _runtime_fixture
grouped_runtime = _grouped_fixture


def owned(row):
    media_hash = hashlib.sha256(b"clip").hexdigest()
    assets = {role: {"storageKey": role, "mediaHash": media_hash} for role in ("source", "product")}
    row.context_json["p0"] = {
        "inputHash": stable_hash({role: media_hash for role in assets}),
        "assets": assets,
        "requirements": {"intent": "keep action", "keep": ["action"]},
        "rights": {
            "providerDisclosureAcknowledged": True,
            **{
                role: {
                    "declared": True,
                    "basis": "owned",
                    "scope": "pilot",
                    "evidenceNote": "own media",
                }
                for role in assets
            },
        },
        "budgetPolicy": {"capUsd": "10", "maxAttempts": 20, "maxDurationSeconds": 1800},
        "assemblies": {
            "activeAssemblyId": "before",
            "records": [{"id": "before", "operationId": "before-op"}],
            "history": [],
        },
        "inspections": {"reports": [{"id": "old-report"}], "reviews": []},
        "release": {
            "activeApprovalId": "approval",
            "approvals": [{"id": "approval"}],
            "exports": [],
        },
    }
    for role in assets:
        row.context_json[f"{role}MediaHash"] = media_hash
    install_expectations(
        row.context_json, state=row.state_json, source_bytes=b"clip", product_bytes=b"clip"
    )
    row.state_json["assemblyCheck"] = {"status": "passed"}
    return row.context_json["p0"]


def assert_invalidated(row):
    p0 = row.context_json["p0"]
    assert p0["release"]["activeApprovalId"] is None
    assert p0["release"]["approvals"] == [{"id": "approval"}]
    assert p0["assemblies"]["records"] == [{"id": "before", "operationId": "before-op"}]
    assert p0["inspections"]["reports"] == [{"id": "old-report"}]
    assert p0["inspectionSummary"]["status"] == "stale"
    assert row.state_json["assemblyCheck"]["status"] == "stale"


async def test_trim_invalidates_current_release_and_checks_preserving_history(runtime):
    service, row, _ = runtime
    owned(row)
    await module.save_timeline(service, row.id, request(row))
    assert_invalidated(row)
    assert row.state_json["finalStorageKey"] == "old-output"


async def test_accept_invalidates_current_release_preserving_other_scene(runtime):
    service, row, repo = runtime
    owned(row)
    state = copy.deepcopy(row.state_json)
    scene = state["scenes"][0]
    candidate = {**scene["versions"][0], "id": str(uuid4())}
    scene["versions"].append(candidate)
    _, operation, _ = await repo.start(row.workspace_id, row.id, "accept", "hash")
    await module.accept_timeline_version(service, row, state, operation, scene, candidate)
    assert_invalidated(row)


async def test_group_retention_invalidates_release_and_replay_stays_unchanged(grouped_runtime):
    row, service, _, _ = grouped_runtime
    owned(row)
    group = row.state_json["renderPlan"]["groups"][0]
    await module.retain_timeline_group_clip(
        service, row, group, b"clip", {"providerRequestId": "task"}
    )
    assert_invalidated(row)
    before = copy.deepcopy(row.context_json)
    await module.retain_timeline_group_clip(
        service, row, group, b"clip", {"providerRequestId": "task"}
    )
    assert row.context_json == before


async def test_single_retention_invalidates_release(runtime, monkeypatch):
    service, row, repo = runtime
    owned(row)
    repo.save = AsyncMock(side_effect=lambda current, state: setattr(current, "state_json", state))
    monkeypatch.setattr(module, "probe_timeline_media", lambda _: {"frameCount": 192})
    monkeypatch.setattr(
        module,
        "_new_version",
        lambda *a, **k: {"id": str(uuid4()), "technicalCheck": {"status": "passed"}},
    )
    await module.retain_timeline_clip(service, row, 0, b"clip", {})
    assert_invalidated(row)


async def test_compose_records_exact_immutable_media_and_actor_snapshot(runtime, monkeypatch):
    service, row, repo = runtime
    p0 = owned(row)
    actor = uuid4()
    for item in row.state_json["draftTimeline"]["items"]:
        item["reviewed"] = True
    _, operation, _ = await repo.start(row.workspace_id, row.id, "compose", "hash")
    operation.result_json = {
        "kind": "compose",
        "expectedRevision": 1,
        "actorId": str(actor),
        "constraintsHash": constraints_hash(row.context_json),
        "policyHash": policy_hash(row.context_json),
        "timeline": copy.deepcopy(row.state_json["draftTimeline"]),
        "mediaManifest": frozen_media(row),
    }
    monkeypatch.setattr(
        module,
        "compose_timeline",
        AsyncMock(return_value=(b"final", {"status": "passed", "frameCount": 192})),
    )
    await module.TimelineWorkflow(service).execute(row.id, operation.id)
    records = row.context_json["p0"]["assemblies"]["records"]
    assert records[0] == p0["assemblies"]["records"][0]
    assembly = records[-1]
    assert assembly["mediaHash"] == hashlib.sha256(b"final").hexdigest()
    assert assembly["storageKey"] == "new-output"
    assert assembly["actorId"] == str(actor)
    assert assembly["operationId"] == str(operation.id)
    assert assembly["constraintsHash"] == constraints_hash(row.context_json)
    assert assembly["contextHash"] == content_hash(
        {
            "constraintsHash": constraints_hash(row.context_json),
            "manifestHash": assembly["manifestHash"],
            "policyHash": policy_hash(row.context_json),
        }
    )
    assert assembly["manifest"]["timeline"] == operation.result_json["timeline"]
    assert row.context_json["p0"]["release"]["activeApprovalId"] is None
    before = copy.deepcopy(row.context_json)
    await module.TimelineWorkflow(service).execute(row.id, operation.id)
    assert row.context_json == before


@pytest.mark.parametrize("stage", ["publish", "render"])
async def test_stopped_project_cannot_queue_or_read_media(runtime, monkeypatch, stage):
    service, row, repo = runtime
    owned(row)["deletion"] = {"status": "suspended"}
    service.media.read = AsyncMock(side_effect=AssertionError("must gate before media"))
    monkeypatch.setattr(kie_workflow, "_service", lambda *a: service)
    monkeypatch.setattr(module, "_queue", AsyncMock(side_effect=AssertionError("must not queue")))
    monkeypatch.setattr("viraldy.modules.smart_remake.service.require_kie_renderer", lambda _: None)
    with pytest.raises(AppError, match="SMART_REMAKE_USE_STOPPED"):
        if stage == "publish":
            await module.enqueue_publish(
                None,
                SimpleNamespace(ai_mode="live"),
                row.workspace_id,
                row.id,
                PublishTimelineRequest(expectedRevision=1, idempotencyKey="stop-publish"),
                actor_id=uuid4(),
            )
        else:
            await module.enqueue_timeline_render(
                None,
                SimpleNamespace(ai_mode="live"),
                row.workspace_id,
                row.id,
                1,
                "stop-render",
                actor_id=uuid4(),
            )
    service.media.read.assert_not_awaited()
    assert next(iter(repo.operations.values())).status == "failed"


@pytest.mark.parametrize("mode", ["live", " LIVE ", "staging", "production", "", "unexpected"])
async def test_live_legacy_render_fails_before_media_or_queue(runtime, monkeypatch, mode):
    service, row, _ = runtime
    monkeypatch.setattr(kie_workflow, "_service", lambda *a: service)
    monkeypatch.setattr("viraldy.modules.smart_remake.service.require_kie_renderer", lambda _: None)
    monkeypatch.setattr(module, "_queue", AsyncMock(side_effect=AssertionError("must not queue")))
    service.media.read = AsyncMock(side_effect=AssertionError("must gate before media"))
    with pytest.raises(AppError, match="SMART_REMAKE_INTAKE_REQUIRED"):
        await module.enqueue_timeline_render(
            None, SimpleNamespace(ai_mode=mode), row.workspace_id, row.id, 1, "legacy-render"
        )
    service.media.read.assert_not_awaited()


async def test_retention_releases_read_transaction_and_preserves_revocation(grouped_runtime):
    row, service, repo, media = grouped_runtime
    owned(row)
    repo.session = SimpleNamespace(commit=AsyncMock())
    original_put = media.put

    async def revoke_while_uploading(*args):
        repo.session.commit.assert_awaited_once()
        # Represents a committed metadata mutation on another DB connection.
        context = copy.deepcopy(row.context_json)
        context["p0"]["rights"]["product"]["revoked"] = True
        context["p0"]["deletion"] = {"status": "suspended"}
        row.context_json = context
        row.state_json = {**row.state_json, "revision": 2, "status": "suspended"}
        return await original_put(*args)

    media.put = revoke_while_uploading
    group = row.state_json["renderPlan"]["groups"][0]
    await module.retain_timeline_group_clip(
        service, row, group, b"clip", {"providerRequestId": "task"}
    )
    assert row.context_json["p0"]["rights"]["product"]["revoked"] is True
    assert row.context_json["p0"]["deletion"]["status"] == "suspended"
    assert row.state_json["status"] == "suspended"
    assert row.state_json["revision"] == 3
    assert all(scene["versions"] for scene in row.state_json["scenes"][:2])


async def test_compose_rechecks_revocation_before_retaining_preview(runtime, monkeypatch):
    service, row, repo = runtime
    owned(row)
    actor = str(uuid4())
    for item in row.state_json["draftTimeline"]["items"]:
        item["reviewed"] = True
    _, operation, _ = await repo.start(row.workspace_id, row.id, "compose-revoke", "hash")
    operation.result_json = {
        "kind": "compose",
        "expectedRevision": 1,
        "actorId": actor,
        "constraintsHash": constraints_hash(row.context_json),
        "policyHash": policy_hash(row.context_json),
        "timeline": copy.deepcopy(row.state_json["draftTimeline"]),
        "mediaManifest": frozen_media(row),
    }

    async def revoke(*args):
        row.context_json["p0"]["rights"]["product"]["revoked"] = True
        return b"final", {"status": "passed"}

    monkeypatch.setattr(module, "compose_timeline", revoke)
    service.media.put = AsyncMock(side_effect=AssertionError("revoked preview must not upload"))
    with pytest.raises(AppError, match="SMART_REMAKE_RIGHTS_REQUIRED"):
        await module.TimelineWorkflow(service).execute(row.id, operation.id)
    assert row.state_json["finalStorageKey"] == "old-output"
    service.media.put.assert_not_awaited()
    assert operation.status == "failed"


async def test_publish_freezes_actor_and_policy_and_does_not_approve(runtime, monkeypatch):
    service, row, repo = runtime
    owned(row)
    for item in row.state_json["draftTimeline"]["items"]:
        item["reviewed"] = True
    actor = uuid4()
    monkeypatch.setattr(kie_workflow, "_service", lambda *a: service)
    queue = AsyncMock()
    monkeypatch.setattr(module, "_queue", queue)
    payload = PublishTimelineRequest(expectedRevision=1, idempotencyKey="freeze")
    await module.enqueue_publish(
        None, SimpleNamespace(ai_mode="live"), row.workspace_id, row.id, payload, actor_id=actor
    )
    operation = repo.operations["freeze"]
    assert operation.result_json["actorId"] == str(actor)
    assert operation.result_json["constraintsHash"] == constraints_hash(row.context_json)
    assert operation.result_json["policyHash"] == policy_hash(row.context_json)
    assert row.context_json["p0"]["release"]["activeApprovalId"] == "approval"
    queue.assert_awaited_once()


async def test_retention_conflict_preserves_new_draft_and_keeps_orphan_for_cleanup(grouped_runtime):
    row, service, repo, media = grouped_runtime
    owned(row)
    original_put = media.put
    repo.save = AsyncMock(side_effect=lambda current, state: setattr(current, "state_json", state))

    async def edit_while_uploading(*args):
        state = copy.deepcopy(row.state_json)
        state["draftTimeline"]["items"][0]["reviewed"] = True
        state["revision"] += 1
        row.state_json = state
        return await original_put(*args)

    media.put = edit_while_uploading
    group = row.state_json["renderPlan"]["groups"][0]
    with pytest.raises(AppError, match="SMART_REMAKE_REVISION_CONFLICT"):
        await module.retain_timeline_group_clip(
            service, row, group, b"clip", {"providerRequestId": "task"}
        )
    assert row.state_json["draftTimeline"]["items"][0]["reviewed"] is True
    assert row.state_json["revision"] == 2
    assert row.context_json["p0"]["retainedMediaKeys"] == ["shared-clip-key"]
    assert not row.state_json["scenes"][0]["versions"]


async def test_concurrent_known_group_output_is_deduplicated_per_scene(grouped_runtime):
    row, service, repo, media = grouped_runtime
    owned(row)
    original_put = media.put
    group = row.state_json["renderPlan"]["groups"][0]
    metadata = {"providerRequestId": "task"}

    async def concurrent_retention(*args):
        media.put = original_put
        await module.retain_timeline_group_clip(service, row, group, b"clip", metadata)
        return await original_put(*args)

    media.put = concurrent_retention
    await module.retain_timeline_group_clip(service, row, group, b"clip", metadata)
    assert row.state_json["revision"] == 2
    assert all(len(scene["versions"]) == 1 for scene in row.state_json["scenes"][:2])


async def test_compose_upload_race_keeps_private_orphan_in_cleanup_inventory(runtime, monkeypatch):
    service, row, repo = runtime
    owned(row)
    for item in row.state_json["draftTimeline"]["items"]:
        item["reviewed"] = True
    _, operation, _ = await repo.start(row.workspace_id, row.id, "compose-upload-revoke", "hash")
    operation.result_json = {
        "kind": "compose",
        "expectedRevision": 1,
        "actorId": str(uuid4()),
        "constraintsHash": constraints_hash(row.context_json),
        "policyHash": policy_hash(row.context_json),
        "timeline": copy.deepcopy(row.state_json["draftTimeline"]),
        "mediaManifest": frozen_media(row),
    }
    monkeypatch.setattr(
        module, "compose_timeline", AsyncMock(return_value=(b"final", {"status": "passed"}))
    )

    async def revoke(*args):
        row.context_json["p0"]["rights"]["product"]["revoked"] = True
        return "private-orphan"

    service.media.put = revoke
    with pytest.raises(AppError, match="SMART_REMAKE_RIGHTS_REQUIRED"):
        await module.TimelineWorkflow(service).execute(row.id, operation.id)
    assert row.context_json["p0"]["retainedMediaKeys"] == ["private-orphan"]
    assert row.state_json["finalStorageKey"] == "old-output"
    assert operation.status == "failed"


def revoke_with_revision(row):
    context = copy.deepcopy(row.context_json)
    context["p0"]["rights"]["product"]["revoked"] = True
    row.context_json = context
    row.state_json = {**row.state_json, "revision": row.state_json["revision"] + 1}


async def test_trim_reloads_revision_after_media_read_and_preserves_revocation(
    runtime, monkeypatch
):
    service, row, _ = runtime
    owned(row)
    monkeypatch.setattr(
        module,
        "validate_selection_media",
        AsyncMock(side_effect=lambda *args: revoke_with_revision(row)),
    )
    with pytest.raises(AppError, match="SMART_REMAKE_REVISION_CONFLICT"):
        await module.save_timeline(service, row.id, request(row))
    assert row.context_json["p0"]["rights"]["product"]["revoked"] is True
    assert row.state_json["draftTimeline"]["items"][0]["inFrame"] == 0


async def test_publish_rechecks_policy_and_revision_after_clip_reads(runtime, monkeypatch):
    service, row, _ = runtime
    owned(row)
    for item in row.state_json["draftTimeline"]["items"]:
        item["reviewed"] = True
    monkeypatch.setattr(kie_workflow, "_service", lambda *a: service)
    monkeypatch.setattr(
        module,
        "validate_selection_media",
        AsyncMock(side_effect=lambda *args: revoke_with_revision(row)),
    )
    queue = AsyncMock()
    monkeypatch.setattr(module, "_queue", queue)
    with pytest.raises(AppError, match="SMART_REMAKE_(RIGHTS_REQUIRED|REVISION_CONFLICT)"):
        await module.enqueue_publish(
            None,
            SimpleNamespace(ai_mode="live"),
            row.workspace_id,
            row.id,
            PublishTimelineRequest(expectedRevision=1, idempotencyKey="revoke-during-read"),
            actor_id=uuid4(),
        )
    queue.assert_not_awaited()


async def test_render_rechecks_before_assigning_context_after_input_reads(runtime, monkeypatch):
    service, row, _ = runtime
    for plan in (row.context_json["renderPlan"], row.state_json["renderPlan"]):
        plan.update(
            groupingPolicy="fixed_provider_windows",
            groups=build_render_groups(plan["units"]),
            renderGroupBreaks=[],
            videoModel="veo3_lite",
            imageModel="gpt-image-2.6-sunburst",
            imageQuality="max",
            imageComplexity="high",
            imageSize="720x1280",
        )
    owned(row)
    for scene in row.state_json["scenes"]:
        scene.update(versions=[], activeVersionId=None)
    monkeypatch.setattr(kie_workflow, "_service", lambda *a: service)
    monkeypatch.setattr("viraldy.modules.smart_remake.service.require_kie_renderer", lambda _: None)
    monkeypatch.setattr(
        "viraldy.modules.smart_remake.service.require_openai_images", lambda _: None
    )
    calls = 0

    async def read(*args):
        nonlocal calls
        calls += 1
        if calls == 4:
            revoke_with_revision(row)
        return b"clip"

    service.media.read = read
    queue = AsyncMock()
    monkeypatch.setattr(module, "_queue", queue)
    with pytest.raises(AppError, match="SMART_REMAKE_(RIGHTS_REQUIRED|REVISION_CONFLICT)"):
        await module.enqueue_timeline_render(
            None,
            SimpleNamespace(ai_mode="live"),
            row.workspace_id,
            row.id,
            1,
            "render-read-race",
            actor_id=uuid4(),
        )
    queue.assert_not_awaited()
    assert row.context_json["p0"]["rights"]["product"]["revoked"] is True
