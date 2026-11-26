"""Metadata remains atomic and can revoke rights while paid generation is running."""

from __future__ import annotations

import asyncio
import copy
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.integration.test_smart_remake_kie_workflow import kie_database_url as _kie_database_url
from tests.unit.test_smart_remake_rights import (
    MemoryMedia,
    image_upload,
    intake_payload,
    source_upload,
)
from viraldy.modules.identity.models import UserModel
from viraldy.modules.smart_remake.budget_ledger import initialize_budget, reserve_attempt
from viraldy.modules.smart_remake.models import SmartRemakeOperationModel
from viraldy.modules.smart_remake.project_contracts import (
    SmartRemakeBudgetPatch,
    SmartRemakeRequirementsPatch,
    SmartRemakeRightsPatch,
    SmartRemakeRightsReviewRequest,
)
from viraldy.modules.smart_remake.project_intake import create_intake
from viraldy.modules.smart_remake.project_metadata import patch_metadata
from viraldy.modules.smart_remake.repair_repository import RepairRepository
from viraldy.modules.workspaces.models import WorkspaceModel
from viraldy.shared.errors.base import AppError, ConflictError


@pytest.fixture(scope="module")
def metadata_database_url():
    yield from _kie_database_url.__wrapped__()


@pytest.fixture
async def metadata(metadata_database_url):
    engine = create_async_engine(metadata_database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    actor, workspace = uuid4(), uuid4()
    media = MemoryMedia()
    async with sessions() as session:
        session.add(UserModel(id=actor, external_auth_id=str(actor), email=f"{actor}@example.test"))
        await session.flush()
        session.add(
            WorkspaceModel(
                id=workspace, slug=str(workspace), name="Metadata", created_by_user_id=actor
            )
        )
        await session.commit()
        row = await create_intake(
            RepairRepository(session),
            media,
            workspace,
            actor,
            intake_payload(),
            source_upload(),
            image_upload(),
        )
        await initialize_budget(session, workspace, row.id, intake_payload().budget.model_dump())
        project_id = row.id

    async def patch(request, kind, actor_id=actor):
        async with sessions() as session:
            repository = RepairRepository(session)

            async def present(row):
                return {
                    "id": str(row.id),
                    "revision": row.revision,
                    "p0": copy.deepcopy(row.context_json["p0"]),
                }

            repair = SimpleNamespace(repository=repository, workspace_id=workspace, present=present)
            return await patch_metadata(repair, project_id, actor_id, request, kind=kind)

    try:
        yield SimpleNamespace(
            sessions=sessions, actor=actor, workspace=workspace, project_id=project_id, patch=patch
        )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_rights_revocation_can_complete_while_generation_is_running(metadata):
    async with metadata.sessions() as session:
        running = SmartRemakeOperationModel(
            id=uuid4(),
            project_id=metadata.project_id,
            idempotency_key="paid-render",
            request_hash="a" * 64,
            status="running",
            result_json={"kind": "render"},
        )
        session.add(running)
        row = await RepairRepository(session).project(metadata.workspace, metadata.project_id)
        p0 = copy.deepcopy(row.context_json["p0"])
        p0["release"] = {"activeApprovalId": "approval", "approvals": [{"id": "approval"}]}
        row.context_json = {**row.context_json, "p0": p0}
        await session.commit()
    rights = intake_payload().rights.model_copy(deep=True)
    rights.product.revoked = True
    request = SmartRemakeRightsPatch(
        expectedRevision=1, idempotencyKey="revoke-rights", rights=rights
    )
    result = await metadata.patch(request, "rights")
    assert result["status"] == "completed"
    assert result["project"]["revision"] == 2
    assert result["project"]["p0"]["rights"]["product"]["revoked"]
    assert result["project"]["p0"]["release"]["activeApprovalId"] is None
    assert result["project"]["p0"]["release"]["approvals"] == [{"id": "approval"}]
    replay = await metadata.patch(request, "rights")
    assert replay["operationId"] == result["operationId"]
    assert replay["project"]["revision"] == 2
    async with metadata.sessions() as session:
        assert (await session.get(SmartRemakeOperationModel, running.id)).status == "running"
        completed = await session.get(SmartRemakeOperationModel, UUID(result["operationId"]))
        assert completed.result_json["actorId"] == str(metadata.actor)
        assert completed.result_json["completedAt"]


@pytest.mark.asyncio
async def test_metadata_idempotency_binds_actor_payload_and_kind(metadata):
    request = SmartRemakeRequirementsPatch(
        expectedRevision=1, idempotencyKey="metadata", requirements=intake_payload().requirements
    )
    first = await metadata.patch(request, "requirements")
    assert first["project"]["revision"] == 2
    with pytest.raises(ConflictError) as error:
        await metadata.patch(request, "requirements", actor_id=uuid4())
    assert error.value.code == "SMART_REMAKE_IDEMPOTENCY_CONFLICT"
    changed = request.model_copy(
        update={"requirements": request.requirements.model_copy(update={"intent": "Other"})}
    )
    with pytest.raises(ConflictError):
        await metadata.patch(changed, "requirements")
    wrong_kind = SmartRemakeRightsPatch(
        expectedRevision=1, idempotencyKey="metadata", rights=intake_payload().rights
    )
    with pytest.raises(ConflictError):
        await metadata.patch(wrong_kind, "rights")


@pytest.mark.asyncio
async def test_metadata_revisions_prevent_concurrent_lost_updates(metadata):
    requests = [
        SmartRemakeRequirementsPatch(
            expectedRevision=1,
            idempotencyKey=f"tab-{index}",
            requirements=intake_payload().requirements,
        )
        for index in range(2)
    ]
    results = await asyncio.gather(
        *(metadata.patch(r, "requirements") for r in requests), return_exceptions=True
    )
    assert sum(isinstance(result, dict) for result in results) == 1
    errors = [result for result in results if isinstance(result, ConflictError)]
    assert len(errors) == 1
    assert errors[0].code == "SMART_REMAKE_REVISION_CONFLICT"


@pytest.mark.asyncio
async def test_budget_metadata_rejects_cap_below_exposure_without_partial_revision(metadata):
    async with metadata.sessions() as session:
        await reserve_attempt(
            session,
            metadata.workspace,
            metadata.project_id,
            idempotency_key="attempt",
            request_hash="a" * 64,
            stage="video",
            reservation_usd="2.00",
            actor_id=metadata.actor,
            provider="kie",
            model="veo-lite",
        )
    request = SmartRemakeBudgetPatch(
        expectedRevision=1,
        idempotencyKey="too-small",
        budget=intake_payload(
            budget={"capUsd": "1.00", "maxAttempts": 12, "maxDurationSeconds": 1800}
        ).budget,
    )
    with pytest.raises(AppError) as error:
        await metadata.patch(request, "budget")
    assert error.value.code == "SMART_REMAKE_BUDGET_BELOW_EXPOSURE"
    async with metadata.sessions() as session:
        row = await RepairRepository(session).project(metadata.workspace, metadata.project_id)
        assert row.revision == 1
        assert row.context_json["p0"]["budgetPolicy"]["capUsd"] == "5.00"
        assert not (
            await session.scalars(
                select(SmartRemakeOperationModel).where(
                    SmartRemakeOperationModel.project_id == row.id
                )
            )
        ).all()
    valid = request.model_copy(
        update={"idempotencyKey": "cap-ok", "budget": intake_payload().budget}
    )
    result = await metadata.patch(valid, "budget")
    assert result["project"]["revision"] == 2
    assert result["project"]["p0"]["budgetPolicy"]["startedAt"]


@pytest.mark.asyncio
async def test_suspended_metadata_cannot_resume_and_rights_review_records_actor(metadata):
    review = SmartRemakeRightsReviewRequest(
        expectedRevision=1, idempotencyKey="review", evidenceNote="Reviewed asset license."
    )
    result = await metadata.patch(review, "rights_review")
    assert result["project"]["p0"]["rights"]["product"]["verification"]["status"] == "reviewed"
    async with metadata.sessions() as session:
        row = await RepairRepository(session).project(metadata.workspace, metadata.project_id)
        row.context_json = {
            **row.context_json,
            "p0": {**row.context_json["p0"], "status": "suspended"},
        }
        await session.commit()
    request = SmartRemakeRightsPatch(
        expectedRevision=2, idempotencyKey="resume", rights=intake_payload().rights
    )
    with pytest.raises(AppError) as error:
        await metadata.patch(request, "rights")
    assert error.value.code == "SMART_REMAKE_USE_STOPPED"
