from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.feedback.models import FeedbackItemModel
from viraldy.modules.feedback.schemas import CreateFeedbackRequest
from viraldy.modules.feedback.service import FeedbackService


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.refreshed: list[object] = []

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, item: object) -> None:
        self.refreshed.append(item)


class FakeFeedbackRepository:
    def __init__(self, session: FakeSession) -> None:
        self.session = session
        self.created: FeedbackItemModel | None = None
        self.list_args: dict[str, object] | None = None

    async def create(
        self,
        *,
        workspace_id: UUID,
        created_by_user_id: UUID,
        feedback: CreateFeedbackRequest,
    ) -> FeedbackItemModel:
        item = FeedbackItemModel(
            id=uuid4(),
            workspace_id=workspace_id,
            subject_type=feedback.subject_type,
            subject_id=feedback.subject_id,
            subject_version=feedback.subject_version,
            field_path=feedback.field_path,
            feedback_type=feedback.feedback_type,
            ai_value_json=feedback.ai_value_json,
            user_value_json=feedback.user_value_json,
            comment=feedback.comment,
            model_run_id=feedback.model_run_id,
            created_by_user_id=created_by_user_id,
            created_at=datetime.now(UTC),
        )
        self.created = item
        return item

    async def list_for_workspace(self, **kwargs: object) -> list[FeedbackItemModel]:
        self.list_args = kwargs
        return [self.created] if self.created is not None else []


class FakeProductEventPublisher:
    def __init__(self, session: FakeSession) -> None:
        self.session = session
        self.records: list[dict[str, object]] = []

    async def record(self, **kwargs: object) -> None:
        self.records.append(kwargs)


@pytest.mark.asyncio
async def test_feedback_service_records_field_correction_and_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.feedback.service as service_module

    session = FakeSession()
    repository = FakeFeedbackRepository(session)
    event_publisher = FakeProductEventPublisher(session)
    monkeypatch.setattr(service_module, "FeedbackRepository", lambda _: repository)
    monkeypatch.setattr(service_module, "ProductEventPublisher", lambda _: event_publisher)
    workspace_id = uuid4()
    user_id = uuid4()
    subject_id = uuid4()

    feedback = await FeedbackService(cast(AsyncSession, session)).create_feedback(
        workspace_id=workspace_id,
        user_id=user_id,
        data=CreateFeedbackRequest(
            subject_type="creative_dna",
            subject_id=subject_id,
            subject_version=2,
            field_path="opening.hook_text",
            feedback_type="incorrect",
            ai_value_json={"value": "old"},
            user_value_json={"value": "corrected"},
            comment="Human correction",
        ),
    )

    assert feedback.subject_id == subject_id
    assert repository.created is not None
    assert event_publisher.records == [
        {
            "event_type": "creative_dna_corrected",
            "workspace_id": workspace_id,
            "actor_user_id": user_id,
            "subject_type": "creative_dna",
            "subject_id": subject_id,
            "payload_json": {
                "subject_version": 2,
                "field_path": "opening.hook_text",
                "feedback_type": "incorrect",
            },
        }
    ]
    assert session.commits == 1
    assert session.refreshed == [repository.created]


@pytest.mark.asyncio
async def test_feedback_service_lists_workspace_feedback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.feedback.service as service_module

    session = FakeSession()
    repository = FakeFeedbackRepository(session)
    monkeypatch.setattr(service_module, "FeedbackRepository", lambda _: repository)
    workspace_id = uuid4()
    subject_id = uuid4()
    repository.created = FeedbackItemModel(
        id=uuid4(),
        workspace_id=workspace_id,
        subject_type="recommendation",
        subject_id=subject_id,
        subject_version=None,
        field_path="action",
        feedback_type="not_useful",
        ai_value_json="try this",
        user_value_json=None,
        comment=None,
        model_run_id=None,
        created_by_user_id=uuid4(),
        created_at=datetime.now(UTC),
    )

    items = await FeedbackService(cast(AsyncSession, session)).list_feedback(
        workspace_id=workspace_id,
        subject_type="recommendation",
        subject_id=subject_id,
        limit=25,
    )

    assert len(items) == 1
    assert repository.list_args == {
        "workspace_id": workspace_id,
        "subject_type": "recommendation",
        "subject_id": subject_id,
        "limit": 25,
    }


def test_feedback_request_rejects_unknown_subject() -> None:
    with pytest.raises(ValidationError):
        CreateFeedbackRequest(
            subject_type="asset",
            subject_id=uuid4(),
            field_path="foo",
            feedback_type="incorrect",
        )
