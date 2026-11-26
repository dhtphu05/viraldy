"""A policy receipt survives SQL JSON persistence and revocation remains fail closed."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.integration import test_smart_remake_rights_persistence as persistence
from tests.integration.test_smart_remake_rights_persistence import LocalStorage
from tests.unit.test_smart_remake_rights import image_upload, intake_payload, source_upload
from tests.unit.test_smart_remake_rights_attestation import STATEMENT, attested_rights
from viraldy.modules.identity.models import UserModel
from viraldy.modules.smart_remake.project_intake import assert_input_binding, create_intake
from viraldy.modules.smart_remake.project_policy import assert_project_policy, context_with_rights
from viraldy.modules.smart_remake.project_presentation import project_policy_fields
from viraldy.modules.smart_remake.repair_media import RepairMediaStore
from viraldy.modules.smart_remake.repair_repository import RepairRepository
from viraldy.modules.workspaces.models import WorkspaceModel
from viraldy.shared.errors.base import AppError

rights_database_url = persistence.rights_database_url


@pytest.mark.asyncio
async def test_attested_rights_receipt_persists_with_owned_media_and_public_projection(
    rights_database_url,
):
    engine = create_async_engine(rights_database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    storage = LocalStorage()
    media = RepairMediaStore(storage)
    actor, workspace = uuid4(), uuid4()
    rights = attested_rights()
    try:
        async with sessions() as session:
            session.add(
                UserModel(id=actor, external_auth_id=str(actor), email=f"{actor}@example.test")
            )
            await session.flush()
            session.add(
                WorkspaceModel(
                    id=workspace,
                    name="Attested",
                    slug=str(workspace),
                    created_by_user_id=actor,
                )
            )
            await session.commit()
            row = await create_intake(
                RepairRepository(session),
                media,
                workspace,
                actor,
                intake_payload(rights=rights.model_dump()),
                source_upload(),
                image_upload(),
            )
            project_id = row.id
            input_hash = row.context_json["p0"]["inputHash"]
            receipt = row.context_json["p0"]["rights"]["attestation"]
        async with sessions() as session:
            row = await RepairRepository(session).project(workspace, project_id)
            assert row.context_json["p0"]["rights"]["attestation"] == receipt
            assert receipt["acceptedBy"] == str(actor)
            assert receipt["statement"] == STATEMENT
            assert receipt["acceptedAt"]
            assert row.context_json["p0"]["inputHash"] == input_hash
            await assert_input_binding(row, media)
            assert_project_policy(row, purpose="analysis")
            public_rights = project_policy_fields(row.context_json)["rights"]
            assert public_rights["attestation"] == receipt
            assert public_rights["source"]["verification"]["status"] == "declared"
            rights.attestation.revoked = True
            row.context_json = context_with_rights(row.context_json, rights, actor_id=actor)
            await session.commit()
        async with sessions() as session:
            row = await RepairRepository(session).project(workspace, project_id)
            with pytest.raises(AppError) as error:
                assert_project_policy(row, purpose="generation")
            assert error.value.code == "SMART_REMAKE_RIGHTS_ATTESTATION_REQUIRED"
            assert row.context_json["p0"]["inputHash"] == input_hash
    finally:
        await engine.dispose()
