from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from viraldy.modules.campaign_packs.models import CampaignPackModel, CampaignPackVersionModel
from viraldy.modules.campaign_packs.repository import CampaignPackRepository


class FakeAsyncSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.refreshed: list[object] = []

    def add(self, model: object) -> None:
        self.added.append(model)

    async def flush(self) -> None:
        now = datetime.now(UTC)
        for model in self.added:
            if isinstance(model, CampaignPackModel):
                model.id = model.id or uuid4()
                model.created_at = model.created_at or now
                model.updated_at = model.updated_at or now
            if isinstance(model, CampaignPackVersionModel):
                model.id = model.id or uuid4()
                model.created_at = model.created_at or now

    async def refresh(self, model: object) -> None:
        self.refreshed.append(model)


@pytest.mark.asyncio
async def test_create_refreshes_server_managed_fields_before_response_serialization() -> None:
    session = FakeAsyncSession()

    pack, version = await CampaignPackRepository(session).create(  # type: ignore[arg-type]
        workspace_id=uuid4(),
        user_id=uuid4(),
        product_id=uuid4(),
        adaptation_run_id=None,
        brief_json={"schema_version": "campaign_pack_brief_v2"},
        source_model_run_id=None,
        source_prompt_version=None,
        source_schema_version=None,
        product_snapshot_json={"schema_version": "product_context_v1"},
        compiled_requirements_json={"schema_version": "compiled_requirements_v2"},
        requirements_schema_version="compiled_requirements_v2",
    )

    assert session.refreshed == [pack, version]
    assert pack.current_version_id == version.id
