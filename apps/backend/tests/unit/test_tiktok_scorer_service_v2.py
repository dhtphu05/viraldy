from __future__ import annotations

from types import SimpleNamespace
from typing import cast
from uuid import UUID, uuid4

import pytest

from viraldy.modules.assets.public import AssetVersionReference
from viraldy.modules.tiktok_scorer.models import TikTokScoreRunModel
from viraldy.modules.tiktok_scorer.schemas import (
    CreateTikTokScoreRequest,
    RecordTikTokScorerOpenedRequest,
)
from viraldy.modules.tiktok_scorer.service import TikTokScoreService, _job_input
from viraldy.shared.errors.base import NotFoundError


class _DirectionLookup:
    def __init__(self, snapshot: object) -> None:
        self.snapshot = snapshot
        self.version_lookup_ids: list[UUID] = []
        self.kit_lookup_ids: list[UUID] = []

    async def get_version_snapshot_by_id(self, workspace_id: UUID, source_id: UUID) -> object:
        _ = workspace_id
        self.version_lookup_ids.append(source_id)
        raise NotFoundError("VIRAL_KIT_VERSION_NOT_FOUND")

    async def get_version_snapshot(self, workspace_id: UUID, source_id: UUID) -> object:
        _ = workspace_id
        self.kit_lookup_ids.append(source_id)
        return self.snapshot


async def test_direction_context_id_falls_back_from_version_id_to_kit_id(monkeypatch) -> None:
    source_id = uuid4()
    lookup = _DirectionLookup(SimpleNamespace(version=4))
    service = cast(TikTokScoreService, TikTokScoreService.__new__(TikTokScoreService))
    service._directions = lookup  # type: ignore[assignment]
    monkeypatch.setattr(
        "viraldy.modules.tiktok_scorer.service._direction_context",
        lambda snapshot: {"source_version": snapshot.version},
    )

    context, version, error = await service._load_direction_snapshot(uuid4(), source_id)

    assert context == {"source_version": 4}
    assert version == 4
    assert error is None
    assert lookup.version_lookup_ids == [source_id]
    assert lookup.kit_lookup_ids == [source_id]


def test_job_input_exposes_auxiliary_search_fields_at_top_level() -> None:
    run = TikTokScoreRunModel(
        id=uuid4(),
        workspace_id=uuid4(),
        asset_id=uuid4(),
        asset_version_id=uuid4(),
        status="queued",
        analysis_mode="fixture",
        rubric_version="rubric-v1",
        rule_version="rules-v1",
    )
    request = CreateTikTokScoreRequest(
        asset_version_id=run.asset_version_id,
        target_query="counter organizer",
        target_buyer_question="Will it fit?",
        selected_search_topic="small kitchen",
        content_gap_topic="rental kitchens",
    )

    payload = _job_input(run, "generic_structure", None, request)

    assert payload["target_query"] == "counter organizer"
    assert payload["target_buyer_question"] == "Will it fit?"
    assert payload["selected_search_topic"] == "small kitchen"
    assert payload["content_gap_topic"] == "rental kitchens"


@pytest.mark.asyncio
async def test_processed_asset_version_can_be_scored_again() -> None:
    workspace_id = uuid4()
    version = AssetVersionReference(
        asset_id=uuid4(),
        asset_version_id=uuid4(),
        workspace_id=workspace_id,
        product_id=uuid4(),
        original_filename="sofa-cover-ugc.mp4",
        checksum_sha256="c" * 64,
        validation_status="processed",
    )
    service = cast(TikTokScoreService, TikTokScoreService.__new__(TikTokScoreService))
    service._asset_queries = _AssetVersionLookup(version)  # type: ignore[assignment]

    resolved = await service._resolve_asset_version(
        workspace_id,
        CreateTikTokScoreRequest(asset_version_id=version.asset_version_id),
    )

    assert resolved == version


class _AssetVersionLookup:
    def __init__(self, version: AssetVersionReference) -> None:
        self.version = version

    async def get_version_reference(
        self,
        _workspace_id: UUID,
        _asset_version_id: UUID,
    ) -> AssetVersionReference:
        return self.version


def test_workspace_opened_event_contract_cannot_emit_other_events() -> None:
    event = RecordTikTokScorerOpenedRequest()

    assert event.event_type == "tiktok_scorer_opened"
