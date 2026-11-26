"""P0 assembly lifecycle through PostgreSQL and real FFmpeg, without paid providers."""

from __future__ import annotations

import asyncio
import copy
import hashlib
from uuid import UUID, uuid4

from tests.integration.test_smart_remake_timeline import (
    timeline_database_url as _database_fixture,
)
from tests.integration.test_smart_remake_timeline import (
    timeline_harness as _harness_fixture,
)
from tests.integration.test_smart_remake_timeline import (
    timeline_media as _media_fixture,
)
from viraldy.modules.smart_remake.generation_expectations import (
    build_generation_expectations,
    expectations_hash,
)
from viraldy.modules.smart_remake.models import SmartRemakeOperationModel
from viraldy.modules.smart_remake.project_policy import stable_hash
from viraldy.modules.smart_remake.repair_schemas import PublishTimelineRequest, SaveTimelineRequest
from viraldy.modules.smart_remake.timeline_media import probe_timeline_media
from viraldy.modules.smart_remake.timeline_service import (
    TimelineWorkflow,
    enqueue_publish,
    retain_timeline_clip,
    save_timeline,
)

timeline_database_url = _database_fixture
timeline_media = _media_fixture
timeline_harness = _harness_fixture


def test_real_compose_keeps_immutable_versions_and_trim_invalidates_approval(
    timeline_harness, timeline_media
):
    harness = timeline_harness
    project_id = asyncio.run(harness.seed_project()).id
    actor = uuid4()

    async def journey():
        async with harness.sessions() as factory, factory() as session:
            service = harness.service(session, harness.settings, harness.workspace_id)
            row = await service.repository.project(harness.workspace_id, project_id)
            context = copy.deepcopy(row.context_json)
            assets = {
                role: {
                    "storageKey": context[f"{role}Key"],
                    "mediaHash": context[f"{role}MediaHash"],
                }
                for role in ("source", "product")
            }
            context["p0"] = {
                "inputHash": stable_hash(
                    {role: asset["mediaHash"] for role, asset in assets.items()}
                ),
                "assets": assets,
                "requirements": {"intent": "keep source action"},
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
            }
            context["generationExpectations"] = build_generation_expectations(context)
            context["expectationsHash"] = expectations_hash(context["generationExpectations"])
            row.context_json = context
            await session.commit()
            for index, clip in enumerate(timeline_media["clips"][:2]):
                await retain_timeline_clip(
                    service,
                    row,
                    index,
                    clip,
                    {
                        "providerRequestId": f"offline-{index}",
                        "generationExpectations": context["generationExpectations"],
                        "expectationsHash": context["expectationsHash"],
                    },
                )
            row = await service.repository.project(harness.workspace_id, project_id)
            items = [
                {
                    "renderUnitId": item["renderUnitId"],
                    "versionId": item["versionId"],
                    "inFrame": item["inFrame"],
                    "outFrame": item["outFrame"],
                    "reviewed": True,
                }
                for item in row.state_json["draftTimeline"]["items"]
            ]
            await save_timeline(
                service,
                project_id,
                SaveTimelineRequest(
                    expectedRevision=row.revision, idempotencyKey="review", items=items
                ),
            )
            payload = PublishTimelineRequest(
                expectedRevision=row.revision, idempotencyKey="compose"
            )
            result = await enqueue_publish(
                session, harness.settings, harness.workspace_id, project_id, payload, actor_id=actor
            )
            operation_id = UUID(result["operationId"])
            await TimelineWorkflow(service).execute(project_id, operation_id)
            row = await service.repository.project(harness.workspace_id, project_id)
            first = copy.deepcopy(row.context_json["p0"]["assemblies"]["records"][0])
            output = await harness.media.read(first["storageKey"])
            assert first["mediaHash"] == hashlib.sha256(output).hexdigest()
            assert probe_timeline_media(output)["frameCount"] == 192
            assert first["actorId"] == str(actor)
            assert first["technicalCheck"]["status"] == "passed"
            public = await service.present(row)
            assert public["finalVideoUrl"]
            assert "downloadUrl" not in public
            replay = await enqueue_publish(
                session, harness.settings, harness.workspace_id, project_id, payload, actor_id=actor
            )
            assert replay["operationId"] == str(operation_id)
            assert len(row.context_json["p0"]["assemblies"]["records"]) == 1
            context = copy.deepcopy(row.context_json)
            context["p0"]["release"].update(
                activeApprovalId="approval", approvals=[{"id": "approval"}]
            )
            row.context_json = context
            await session.commit()
            items[0].update(inFrame=24, outFrame=72)
            await save_timeline(
                service,
                project_id,
                SaveTimelineRequest(
                    expectedRevision=row.revision, idempotencyKey="trim", items=items
                ),
            )
            row = await service.repository.project(harness.workspace_id, project_id)
            assert row.context_json["p0"]["assemblies"]["records"] == [first]
            assert row.context_json["p0"]["release"]["activeApprovalId"] is None
            assert row.state_json["assemblyCheck"]["status"] == "stale"
            assert await harness.media.read(first["storageKey"]) == output
            operation = await session.get(SmartRemakeOperationModel, operation_id)
            assert operation.status == "completed"

    asyncio.run(journey())


def test_storage_upload_allows_independent_rights_revocation(timeline_harness, timeline_media):
    from viraldy.modules.smart_remake.timeline_service import retain_timeline_group_clip

    harness = timeline_harness
    project_id = asyncio.run(harness.seed_project(grouped=True)).id

    async def journey():
        async with harness.sessions() as factory, factory() as session:
            service = harness.service(session, harness.settings, harness.workspace_id)
            row = await service.repository.project(harness.workspace_id, project_id)
            context = copy.deepcopy(row.context_json)
            context["p0"] = {"rights": {"product": {"revoked": False}}}
            row.context_json = context
            await session.commit()
            original_put = harness.media.put
            initial_revision = row.revision

            async def revoke_during_put(*args):
                assert not session.in_transaction()
                async with factory() as other:
                    from viraldy.modules.smart_remake.repair_repository import RepairRepository

                    latest = await RepairRepository(other).project(
                        harness.workspace_id, project_id, lock=True
                    )
                    context = copy.deepcopy(latest.context_json)
                    context["p0"]["rights"]["product"]["revoked"] = True
                    context["p0"]["deletion"] = {"status": "suspended"}
                    latest.context_json = context
                    state = {
                        **latest.state_json,
                        "status": "suspended",
                        "revision": latest.revision + 1,
                    }
                    latest.state_json, latest.revision = state, state["revision"]
                    await other.commit()
                return await original_put(*args)

            harness.media.put = revoke_during_put
            group = row.state_json["renderPlan"]["groups"][0]
            await retain_timeline_group_clip(
                service,
                row,
                group,
                timeline_media["clips"][0],
                {"providerRequestId": "known-paid-output"},
            )
            latest = await service.repository.project(harness.workspace_id, project_id)
            assert latest.context_json["p0"]["rights"]["product"]["revoked"] is True
            assert latest.context_json["p0"]["deletion"]["status"] == "suspended"
            assert latest.state_json["status"] == "suspended"
            assert latest.state_json["phase"] == "rendered"
            assert latest.revision == initial_revision + 2
            assert all(scene["versions"] for scene in latest.state_json["scenes"])

    asyncio.run(journey())
