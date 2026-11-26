"""Owned intake durability and concurrent replay against isolated PostgreSQL/storage."""

from __future__ import annotations

import asyncio
import copy
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.integration.test_smart_remake_kie_workflow import (
    kie_database_url as _kie_database_url,
)
from tests.unit.test_smart_remake_rights import image_upload, intake_payload, source_upload
from viraldy.modules.identity.models import UserModel
from viraldy.modules.smart_remake.models import SmartRemakeProjectModel
from viraldy.modules.smart_remake.project_intake import assert_input_binding, create_intake
from viraldy.modules.smart_remake.project_policy import assert_project_policy, context_with_rights
from viraldy.modules.smart_remake.repair_media import RepairMediaStore
from viraldy.modules.smart_remake.repair_repository import RepairRepository
from viraldy.modules.workspaces.models import WorkspaceModel
from viraldy.shared.errors.base import AppError, ConflictError, NotFoundError


@pytest.fixture(scope="module")
def rights_database_url():
    yield from _kie_database_url.__wrapped__()


class LocalStorage:
    def __init__(self):
        self.objects = {}

    def upload_file(self, source_path, key, content_type):
        self.objects[key] = (Path(source_path).read_bytes(), content_type)

    def download_object(self, key, destination_path):
        Path(destination_path).write_bytes(self.objects[key][0])

    def delete_object(self, key):
        self.objects.pop(key, None)


@pytest.mark.asyncio
async def test_concurrent_owned_intake_restarts_and_rights_revocation(rights_database_url):
    engine = create_async_engine(rights_database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    storage = LocalStorage()
    media = RepairMediaStore(storage)
    workspace, actor = uuid4(), uuid4()
    try:
        async with sessions() as session:
            session.add(
                UserModel(id=actor, external_auth_id=str(actor), email=f"{actor}@example.test")
            )
            await session.flush()
            session.add(
                WorkspaceModel(
                    id=workspace, name="Owned intake", slug=str(workspace), created_by_user_id=actor
                )
            )
            await session.commit()

        async def submit(payload):
            async with sessions() as session:
                return await create_intake(
                    RepairRepository(session),
                    media,
                    workspace,
                    actor,
                    payload,
                    source_upload(),
                    image_upload(),
                )

        first, repeated = await asyncio.gather(submit(intake_payload()), submit(intake_payload()))
        assert first.id == repeated.id
        assert len(storage.objects) == 2
        async with sessions() as session:
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(SmartRemakeProjectModel)
                    .where(SmartRemakeProjectModel.workspace_id == workspace)
                )
                == 1
            )
            repository = RepairRepository(session)
            row = await repository.project(workspace, first.id)
            await assert_input_binding(row, media)
            assert_project_policy(row, purpose="analysis")
            with pytest.raises(NotFoundError):
                await repository.project(uuid4(), row.id)
            rights = intake_payload().rights.model_copy(deep=True)
            rights.product.revoked = True
            row.context_json = context_with_rights(row.context_json, rights, actor_id=actor)
            await session.commit()
        # A different request with the same key does not replace private bytes or rights.
        with pytest.raises(ConflictError):
            await submit(intake_payload(projectName="Replaced intent"))
        assert len(storage.objects) == 2
        async with sessions() as session:
            row = await RepairRepository(session).project(workspace, first.id)
            with pytest.raises(AppError) as error:
                assert_project_policy(row, purpose="generation")
            assert error.value.code == "SMART_REMAKE_RIGHTS_REQUIRED"
            assert (
                copy.deepcopy(row.context_json["p0"]["assets"])
                == first.context_json["p0"]["assets"]
            )
    finally:
        await engine.dispose()
