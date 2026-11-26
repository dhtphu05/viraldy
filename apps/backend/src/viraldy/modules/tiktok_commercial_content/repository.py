from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from viraldy.modules.tiktok_commercial_content.mapper import PROVIDER, SCHEMA_VERSION
from viraldy.modules.tiktok_commercial_content.models import (
    CreativeSourceLinkModel,
    ExternalSourceRecordModel,
)


class TikTokCommercialRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_source_record(
        self,
        *,
        workspace_id: UUID | None,
        entity_type: str,
        entity_id: str,
        raw_payload: dict[str, Any],
        fetched_at: datetime,
        request_context: dict[str, object],
        provider_log_id: str | None = None,
    ) -> ExternalSourceRecordModel:
        record = await self._session.scalar(
            select(ExternalSourceRecordModel).where(
                ExternalSourceRecordModel.provider == PROVIDER,
                ExternalSourceRecordModel.provider_entity_type == entity_type,
                ExternalSourceRecordModel.provider_entity_id == entity_id,
            )
        )
        content_hash = hashlib.sha256(
            json.dumps(raw_payload, sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest()
        if record is None:
            record = ExternalSourceRecordModel(
                workspace_id=workspace_id,
                provider=PROVIDER,
                provider_entity_type=entity_type,
                provider_entity_id=entity_id,
                raw_payload=raw_payload,
                schema_version=SCHEMA_VERSION,
                fetched_at=fetched_at,
                content_hash=content_hash,
                request_context=request_context,
                provider_log_id=provider_log_id,
            )
            self._session.add(record)
        else:
            record.raw_payload = raw_payload
            record.schema_version = SCHEMA_VERSION
            record.fetched_at = fetched_at
            record.content_hash = content_hash
            record.request_context = request_context
            record.provider_log_id = provider_log_id
            if workspace_id is not None and record.workspace_id is None:
                record.workspace_id = workspace_id
        await self._session.flush()
        return record

    async def get_source_record(self, source_id: UUID) -> ExternalSourceRecordModel | None:
        return cast(
            ExternalSourceRecordModel | None,
            await self._session.scalar(
                select(ExternalSourceRecordModel).where(ExternalSourceRecordModel.id == source_id)
            ),
        )

    async def link_asset(
        self,
        *,
        asset_id: UUID,
        entity_type: str,
        entity_id: str,
        source_url: str | None,
        source_metadata: dict[str, object],
        seen_at: datetime,
    ) -> CreativeSourceLinkModel:
        link = await self._session.scalar(
            select(CreativeSourceLinkModel).where(
                CreativeSourceLinkModel.provider == PROVIDER,
                CreativeSourceLinkModel.provider_entity_type == entity_type,
                CreativeSourceLinkModel.provider_entity_id == entity_id,
            )
        )
        if link is None:
            link = CreativeSourceLinkModel(
                creative_asset_id=asset_id,
                provider=PROVIDER,
                provider_entity_type=entity_type,
                provider_entity_id=entity_id,
                source_url=source_url,
                source_metadata=source_metadata,
                first_seen_at=seen_at,
                last_seen_at=seen_at,
            )
            self._session.add(link)
        else:
            link.source_url = source_url
            link.source_metadata = source_metadata
            link.last_seen_at = seen_at
        await self._session.flush()
        return link

    async def get_asset_id_for_source(self, entity_type: str, entity_id: str) -> UUID | None:
        return cast(
            UUID | None,
            await self._session.scalar(
                select(CreativeSourceLinkModel.creative_asset_id).where(
                    CreativeSourceLinkModel.provider == PROVIDER,
                    CreativeSourceLinkModel.provider_entity_type == entity_type,
                    CreativeSourceLinkModel.provider_entity_id == entity_id,
                )
            ),
        )


class SyncTikTokCommercialRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_source_record(self, source_id: UUID) -> ExternalSourceRecordModel | None:
        return self._session.get(ExternalSourceRecordModel, source_id)
