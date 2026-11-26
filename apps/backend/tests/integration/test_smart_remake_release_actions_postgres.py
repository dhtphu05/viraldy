"""Release journeys against isolated PostgreSQL, private storage and real FFmpeg."""

from __future__ import annotations

import asyncio
import copy
import hashlib
from contextlib import asynccontextmanager
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.integration.test_smart_remake_kie_workflow import kie_database_url as _database
from tests.unit.test_smart_remake_release_actions import harness as _template
from tests.unit.test_smart_remake_release_media import _video
from viraldy.modules.identity.models import UserModel
from viraldy.modules.smart_remake.models import SmartRemakeOperationModel, SmartRemakeProjectModel
from viraldy.modules.smart_remake.project_lifecycle import (
    ApprovalRequest,
    DeletionRequest,
    ExportRequest,
    ProjectLifecycleService,
)
from viraldy.modules.smart_remake.repair_repository import RepairRepository
from viraldy.modules.smart_remake.repair_service import RepairService
from viraldy.modules.workspaces.models import WorkspaceModel
from viraldy.shared.errors.base import AppError


@pytest.fixture(scope="module")
def release_database_url():
    yield from _database.__wrapped__()


@pytest.fixture
def release_harness(release_database_url, tmp_path):
    h = _template.__wrapped__()
    output = _video(tmp_path)
    digest = hashlib.sha256(output).hexdigest()
    h.media.data[h.assembly["storageKey"]] = output
    record = h.row.context_json["p0"]["assemblies"]["records"][0]
    record["mediaHash"] = digest
    record["technicalCheck"].update(mediaHash=digest, frameCount=192)
    report = h.row.context_json["p0"]["inspections"]["reports"][0]
    report["subject"]["mediaHash"] = digest
    for finding in report["findings"]:
        for evidence in finding["evidence"]:
            evidence["mediaHash"] = digest
    for coverage in report["coverage"]:
        for evidence in coverage["evidence"]:
            evidence["mediaHash"] = digest
    # SQL row instances differ between sessions; suspension is asserted via reloaded rows below.
    h.media.delete_object = lambda key: (h.media.deleted.append(key), h.media.data.pop(key, None))

    @asynccontextmanager
    async def sessions():
        engine = create_async_engine(release_database_url)
        try:
            yield async_sessionmaker(engine, expire_on_commit=False)
        finally:
            await engine.dispose()

    h.sessions = sessions

    def service(session):
        return ProjectLifecycleService(
            RepairService(RepairRepository(session), h.media, h.row.workspace_id)
        )

    h.actions = service

    async def seed():
        async with sessions() as factory, factory() as session:
            session.add(
                UserModel(
                    id=h.actor, external_auth_id=str(h.actor), email=f"{h.actor}@example.test"
                )
            )
            await session.flush()
            session.add(
                WorkspaceModel(
                    id=h.row.workspace_id,
                    name="P0 release",
                    slug=str(h.row.workspace_id),
                    created_by_user_id=h.actor,
                )
            )
            await session.flush()
            session.add(
                SmartRemakeProjectModel(
                    id=h.project,
                    workspace_id=h.row.workspace_id,
                    revision=3,
                    context_json=h.row.context_json,
                    state_json=h.row.state_json,
                )
            )
            await session.commit()

    asyncio.run(seed())
    return h


def test_real_checked_export_db_history_and_revoked_replay(release_harness):
    h = release_harness

    async def run():
        async with h.sessions() as factory, factory() as session:
            actions = h.actions(session)
            approval = await actions.approve(
                h.project,
                h.actor,
                ApprovalRequest(
                    expectedRevision=3,
                    idempotencyKey="approve",
                    assemblyId=h.assembly["id"],
                    reportId="report",
                ),
            )
            request = ExportRequest(
                expectedRevision=4,
                idempotencyKey="export",
                assemblyId=h.assembly["id"],
                approvalId=approval["approval"]["id"],
            )
            exported = await actions.export(h.project, h.actor, request)
            assert exported["technicalCheck"]["labelVerification"]["verified"] is True
            assert exported["exportMediaHash"] != exported["sourceMediaHash"]
            assert "storageKey" not in str(exported)
            before = await h.media.read(h.assembly["storageKey"])
        async with h.sessions() as factory, factory() as session:
            actions = h.actions(session)
            replay = await actions.export(h.project, h.actor, request)
            assert replay["id"] == exported["id"]
            assert len(h.media.puts) == 1
            row = await actions.repository.project(h.row.workspace_id, h.project, lock=True)
            context = copy.deepcopy(row.context_json)
            context["p0"]["rights"]["product"]["revoked"] = True
            row.context_json = context
            await session.commit()
            with pytest.raises(AppError):
                await actions.export(h.project, h.actor, request)
            assert await h.media.read(h.assembly["storageKey"]) == before
            assert row.revision == 5

    asyncio.run(run())


def test_deletion_stops_busy_project_then_retries_after_paid_operation_terminal(release_harness):
    h = release_harness

    async def run():
        paid_id = uuid4()
        async with h.sessions() as factory, factory() as session:
            session.add(
                SmartRemakeOperationModel(
                    id=paid_id,
                    project_id=h.project,
                    idempotency_key="paid",
                    request_hash="f" * 64,
                    status="running",
                    result_json={"kind": "video"},
                )
            )
            await session.commit()
            actions = h.actions(session)
            result = await actions.delete(
                h.project,
                h.actor,
                DeletionRequest(
                    expectedRevision=3, idempotencyKey="stop", reason="Seller requests deletion"
                ),
            )
            assert result["deletion"]["status"] == "blocked" and not h.media.deleted
        async with h.sessions() as factory, factory() as session:
            actions = h.actions(session)
            row = await actions.repository.project(h.row.workspace_id, h.project)
            assert row.context_json["p0"]["status"] == "suspended"
            assert row.revision == 5
            paid = await session.get(SmartRemakeOperationModel, paid_id)
            paid.status = "failed"
            await session.commit()
            request = DeletionRequest(
                expectedRevision=5, idempotencyKey="cleanup", reason="Remote work settled"
            )
            result = await actions.delete(h.project, h.actor, request)
            assert result["deletion"]["status"] == "completed"
            assert result["deletion"]["providerDeletion"] == "unverified"
            assert h.media.deleted
            assert "storageKey" not in str(result)
            assert await actions.delete(h.project, h.actor, request) == result

    asyncio.run(run())


def test_deletion_queries_other_project_references_before_removal(release_harness):
    h = release_harness

    async def run():
        async with h.sessions() as factory, factory() as session:
            session.add(
                SmartRemakeProjectModel(
                    id=uuid4(),
                    workspace_id=h.row.workspace_id,
                    revision=1,
                    state_json={"finalStorageKey": h.assembly["storageKey"]},
                    context_json={},
                )
            )
            await session.commit()
            result = await h.actions(session).delete(
                h.project,
                h.actor,
                DeletionRequest(
                    expectedRevision=3, idempotencyKey="cleanup", reason="Delete private project"
                ),
            )
            assert result["deletion"]["status"] == "partial"
            assert any(
                item["status"] == "retained_shared" for item in result["deletion"]["objects"]
            )
            assert h.assembly["storageKey"] not in h.media.deleted

    asyncio.run(run())
