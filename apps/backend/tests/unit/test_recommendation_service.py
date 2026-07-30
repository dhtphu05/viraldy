from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.recommendations.models import RecommendationModel
from viraldy.modules.recommendations.schemas import RecordRecommendationActionRequest
from viraldy.modules.recommendations.service import RecommendationService
from viraldy.shared.errors.base import AppError, NotFoundError


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class FakeRecommendationRepository:
    def __init__(self, session: FakeSession) -> None:
        self.session = session
        self.recorded: tuple[UUID, UUID, UUID, str, dict[str, object]] | None = None
        self.action_id = uuid4()

    async def list_recommendations(self, workspace_id: UUID) -> list[RecommendationModel]:
        return [self._build_recommendation(workspace_id, uuid4())]

    async def get_recommendation(
        self,
        workspace_id: UUID,
        recommendation_id: UUID,
    ) -> RecommendationModel | None:
        return self._build_recommendation(workspace_id, recommendation_id)

    def _build_recommendation(
        self,
        workspace_id: UUID,
        recommendation_id: UUID,
    ) -> RecommendationModel:
        return RecommendationModel(
            id=recommendation_id,
            workspace_id=workspace_id,
            subject_type="asset",
            subject_id=uuid4(),
            recommendation_type="creative_iteration",
            action="Try a stronger opening hook.",
            confidence="medium",
            reasoning="Foundation recommendation fixture.",
            evidence_json={},
            assumptions_json=[],
            model_version=None,
            rule_version="test",
            source_run_id=None,
            created_at=datetime.now(UTC),
        )

    async def record_action(
        self,
        workspace_id: UUID,
        recommendation_id: UUID,
        user_id: UUID,
        action_type: str,
        metadata_json: dict[str, object],
    ) -> UUID:
        self.recorded = (
            workspace_id,
            recommendation_id,
            user_id,
            action_type,
            metadata_json,
        )
        return self.action_id


class FakeProductEventPublisher:
    def __init__(self, session: FakeSession) -> None:
        self.session = session
        self.records: list[dict[str, object]] = []

    async def record(self, **kwargs: object) -> None:
        self.records.append(kwargs)


class MissingRecommendationRepository:
    def __init__(self, session: FakeSession) -> None:
        self.session = session

    async def get_recommendation(
        self,
        workspace_id: UUID,
        recommendation_id: UUID,
    ) -> RecommendationModel | None:
        return None


@pytest.mark.asyncio
async def test_recommendation_service_records_valid_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.recommendations.service as service_module

    session = FakeSession()
    repository = FakeRecommendationRepository(session)
    event_publisher = FakeProductEventPublisher(session)
    monkeypatch.setattr(service_module, "RecommendationRepository", lambda _: repository)
    monkeypatch.setattr(service_module, "ProductEventPublisher", lambda _: event_publisher)
    workspace_id = uuid4()
    recommendation_id = uuid4()
    user_id = uuid4()

    action = await RecommendationService(cast(AsyncSession, session)).record_action(
        workspace_id=workspace_id,
        recommendation_id=recommendation_id,
        user_id=user_id,
        data=RecordRecommendationActionRequest(
            action_type="accepted",
            metadata_json={"source": "unit-test"},
        ),
    )

    assert action.id == repository.action_id
    assert repository.recorded == (
        workspace_id,
        recommendation_id,
        user_id,
        "accepted",
        {"source": "unit-test"},
    )
    assert event_publisher.records == [
        {
            "event_type": "recommendation_accepted",
            "workspace_id": workspace_id,
            "actor_user_id": user_id,
            "subject_type": "recommendation",
            "subject_id": recommendation_id,
            "payload_json": {"action_id": str(repository.action_id)},
        }
    ]
    assert session.commits == 1


@pytest.mark.asyncio
async def test_recommendation_service_accepts_ignored_without_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.recommendations.service as service_module

    session = FakeSession()
    repository = FakeRecommendationRepository(session)
    event_publisher = FakeProductEventPublisher(session)
    monkeypatch.setattr(service_module, "RecommendationRepository", lambda _: repository)
    monkeypatch.setattr(service_module, "ProductEventPublisher", lambda _: event_publisher)

    await RecommendationService(cast(AsyncSession, session)).record_action(
        workspace_id=uuid4(),
        recommendation_id=uuid4(),
        user_id=uuid4(),
        data=RecordRecommendationActionRequest(action_type="ignored"),
    )

    assert repository.recorded is not None
    assert repository.recorded[3] == "ignored"
    assert event_publisher.records == []


@pytest.mark.asyncio
async def test_recommendation_service_lists_and_gets_recommendations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.recommendations.service as service_module

    session = FakeSession()
    repository = FakeRecommendationRepository(session)
    monkeypatch.setattr(service_module, "RecommendationRepository", lambda _: repository)
    service = RecommendationService(cast(AsyncSession, session))
    workspace_id = uuid4()
    recommendation_id = uuid4()

    recommendations = await service.list_recommendations(workspace_id)
    recommendation = await service.get_recommendation(workspace_id, recommendation_id)

    assert len(recommendations) == 1
    assert recommendations[0].workspace_id == workspace_id
    assert recommendation.id == recommendation_id


@pytest.mark.asyncio
async def test_recommendation_service_rejects_invalid_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.recommendations.service as service_module

    session = FakeSession()
    repository = FakeRecommendationRepository(session)
    monkeypatch.setattr(service_module, "RecommendationRepository", lambda _: repository)

    with pytest.raises(AppError, match="INVALID_RECOMMENDATION_ACTION"):
        await RecommendationService(cast(AsyncSession, session)).record_action(
            workspace_id=uuid4(),
            recommendation_id=uuid4(),
            user_id=uuid4(),
            data=RecordRecommendationActionRequest(action_type="dismissed"),
        )


@pytest.mark.asyncio
async def test_recommendation_service_raises_when_recommendation_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.recommendations.service as service_module

    session = FakeSession()
    monkeypatch.setattr(
        service_module,
        "RecommendationRepository",
        lambda _: MissingRecommendationRepository(session),
    )

    with pytest.raises(NotFoundError, match="RECOMMENDATION_NOT_FOUND"):
        await RecommendationService(cast(AsyncSession, session)).get_recommendation(
            workspace_id=uuid4(),
            recommendation_id=uuid4(),
        )
