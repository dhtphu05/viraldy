from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.assets.models import AssetModel, AssetVersionModel
from viraldy.modules.assets.repository import AssetRepository
from viraldy.modules.products.public import ProductQueries
from viraldy.modules.reference_boards.public import ReferenceBoardRepository
from viraldy.modules.references.models import ReferenceModel
from viraldy.modules.references.repository import ReferenceRepository
from viraldy.modules.tiktok_commercial_content import router, workflow_router
from viraldy.modules.tiktok_commercial_content.mapper import map_ad_result
from viraldy.modules.tiktok_commercial_content.models import MarketInsightSnapshotModel
from viraldy.modules.tiktok_commercial_content.schemas import (
    AttachProductRequest,
    SaveReferenceRequest,
)
from viraldy.modules.tiktok_commercial_content.service import TikTokCommercialContentService
from viraldy.modules.tiktok_commercial_content.workflow import MarketWorkflowService
from viraldy.modules.tiktok_commercial_content.workflow_schemas import SnapshotCreateRequest
from viraldy.platform.auth.current_user import CurrentUser
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError


@pytest.fixture
def session() -> Mock:
    return Mock(spec=AsyncSession)


@pytest.fixture
def user() -> CurrentUser:
    return CurrentUser(uuid4(), "privacy-test", "privacy@example.com", None, "active")


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        share_market_snapshot=True,
        tiktok_commercial_api_enabled=True,
        tiktok_market_intelligence=True,
    )


def _snapshot_request(**overrides: object) -> SnapshotCreateRequest:
    return SnapshotCreateRequest.model_validate(
        {
            "slug": "public-pattern",
            "snapshot_type": "creative_pattern",
            "title": "Observed public patterns",
            "date_range": {"min": "2026-01-01", "max": "2026-01-31"},
            "payload": {
                "pattern": "Product demonstration",
                "patterns": ["Product demonstration"],
                "observed_count": 12,
                "sample_size": 12,
                "family_count": 3,
                "limitations": ["Public reach alone does not prove outcomes."],
            },
            **overrides,
        }
    )


async def _create_snapshot(
    session: Mock, settings: Settings, user: CurrentUser, workspace_id: UUID
) -> MarketInsightSnapshotModel:
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(workflow_router, "require_workspace_permission", AsyncMock())
        await workflow_router.create_snapshot(
            workspace_id, _snapshot_request(), user, session, settings, "privacy-test"
        )
    row = session.add.call_args.args[0]
    row.id = uuid4()
    row.source_scope = "MARKET"
    session.get.return_value = row
    session.commit.reset_mock()
    return row  # type: ignore[no-any-return]


@pytest.mark.parametrize("foreign_user", [False, True])
async def test_snapshot_publication_rejects_foreign_workspace_or_creator(
    session: Mock, settings: Settings, user: CurrentUser, foreign_user: bool
) -> None:
    workspace_id = uuid4()
    row = await _create_snapshot(session, settings, user, workspace_id)
    caller = (
        CurrentUser(uuid4(), "other", "other@example.com", None, "active") if foreign_user else user
    )
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(workflow_router, "require_workspace_permission", AsyncMock())
        with pytest.raises(AppError) as error:
            await workflow_router.publish_snapshot(
                workspace_id if foreign_user else uuid4(),
                row.id,
                caller,
                session,
                settings,
                "privacy-test",
            )
    assert error.value.status_code == 404
    assert row.published_at is None
    session.commit.assert_not_awaited()


async def test_owner_can_publish_without_exposing_workspace_marker(
    session: Mock, settings: Settings, user: CurrentUser, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace_id = uuid4()
    row = await _create_snapshot(session, settings, user, workspace_id)
    monkeypatch.setattr(workflow_router, "require_workspace_permission", AsyncMock())
    response = await workflow_router.publish_snapshot(
        workspace_id, row.id, user, session, settings, "privacy-test"
    )
    assert response.data["payload"] == _snapshot_request().payload
    assert response.data["date_range"] == _snapshot_request().date_range
    assert str(workspace_id) not in str(response.data)
    assert row.published_at is not None


async def test_publication_rejects_unbound_legacy_draft(
    session: Mock, settings: Settings, user: CurrentUser, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _snapshot_request()
    row = MarketInsightSnapshotModel(
        id=uuid4(),
        created_by_user_id=user.id,
        payload_json=request.payload,
        date_range_json=request.date_range,
        source_scope="MARKET",
    )
    session.get.return_value = row
    monkeypatch.setattr(workflow_router, "require_workspace_permission", AsyncMock())
    with pytest.raises(AppError) as error:
        await workflow_router.publish_snapshot(
            uuid4(), row.id, user, session, settings, "privacy-test"
        )
    assert error.value.status_code == 404
    session.commit.assert_not_awaited()


async def test_publication_respects_disabled_snapshot_feature(
    session: Mock, settings: Settings, user: CurrentUser, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace_id = uuid4()
    row = await _create_snapshot(session, settings, user, workspace_id)
    monkeypatch.setattr(workflow_router, "require_workspace_permission", AsyncMock())
    with pytest.raises(AppError) as error:
        await workflow_router.publish_snapshot(
            workspace_id,
            row.id,
            user,
            session,
            settings.model_copy(update={"share_market_snapshot": False}),
            "privacy-test",
        )
    assert error.value.status_code == 503
    session.commit.assert_not_awaited()


@pytest.mark.parametrize(
    "payload",
    [
        {"access_token": "synthetic"},
        {"api_key": "synthetic"},
        {"client_secret": "synthetic"},
        {"internal_notes": "private"},
        {"unknown": "private"},
        {"patterns": [{"seller_notes": "private"}]},
        {"sample_size": "private"},
        {"observed_count": True},
    ],
)
async def test_snapshot_creation_rejects_unknown_private_and_untyped_payloads(
    session: Mock,
    settings: Settings,
    user: CurrentUser,
    payload: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(workflow_router, "require_workspace_permission", AsyncMock())
    with pytest.raises(AppError, match="workspace-private"):
        await workflow_router.create_snapshot(
            uuid4(), _snapshot_request(payload=payload), user, session, settings, "privacy-test"
        )
    session.add.assert_not_called()


@pytest.mark.parametrize("date_range", [{"api_key": "synthetic"}, {"min": "private notes"}])
async def test_snapshot_date_range_cannot_carry_private_fields_or_arbitrary_text(
    session: Mock,
    settings: Settings,
    user: CurrentUser,
    date_range: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(workflow_router, "require_workspace_permission", AsyncMock())
    with pytest.raises(AppError, match="workspace-private"):
        await workflow_router.create_snapshot(
            uuid4(),
            _snapshot_request(date_range=date_range),
            user,
            session,
            settings,
            "privacy-test",
        )
    session.add.assert_not_called()


@pytest.mark.parametrize("private_field", ["payload_json", "date_range_json"])
async def test_public_read_revalidates_existing_rows(session: Mock, private_field: str) -> None:
    request = _snapshot_request()
    row = MarketInsightSnapshotModel(
        id=uuid4(),
        slug=request.slug,
        snapshot_type=request.snapshot_type,
        title=request.title,
        source_scope="MARKET",
        payload_json=request.payload,
        date_range_json=request.date_range,
        published_at=datetime.now(UTC),
    )
    setattr(row, private_field, {"api_key": "synthetic"})
    session.scalar.return_value = row
    with pytest.raises(AppError):
        await workflow_router.public_snapshot(row.slug, session, "privacy-test")


def _market_asset() -> AssetModel:
    return AssetModel(
        id=uuid4(),
        workspace_id=None,
        product_id=None,
        asset_type="reference",
        status="metadata_only",
        current_version_id=uuid4(),
        metadata_json={},
        library_scope="MARKET",
        processing_status="NOT_ANALYZED",
    )


async def test_attach_product_updates_only_workspace_reference(
    session: Mock, user: CurrentUser, monkeypatch: pytest.MonkeyPatch
) -> None:
    asset, workspace_id, product_id = _market_asset(), uuid4(), uuid4()
    reference = ReferenceModel(id=uuid4(), workspace_id=workspace_id, product_id=None)
    other_reference = ReferenceModel(id=uuid4(), workspace_id=uuid4(), product_id=uuid4())
    other_product_id = other_reference.product_id
    monkeypatch.setattr(router, "require_workspace_permission", AsyncMock())
    monkeypatch.setattr(AssetRepository, "get_for_workspace", AsyncMock(return_value=asset))
    lookup = AsyncMock(return_value=reference)
    monkeypatch.setattr(ReferenceRepository, "get_by_asset", lookup)
    monkeypatch.setattr(ProductQueries, "exists_in_workspace", AsyncMock(return_value=True))
    await router.attach_product(
        workspace_id,
        asset.id,
        AttachProductRequest(product_id=product_id),
        user,
        session,
        "privacy-test",
    )
    assert asset.product_id is None
    assert reference.product_id == product_id
    assert other_reference.product_id == other_product_id
    lookup.assert_awaited_once_with(workspace_id, asset.id)


async def test_asset_detail_projects_workspace_reference_instead_of_global_product(
    session: Mock, user: CurrentUser, monkeypatch: pytest.MonkeyPatch
) -> None:
    asset, workspace_id, product_id = _market_asset(), uuid4(), uuid4()
    asset.product_id = uuid4()  # Simulate a legacy global association from another workspace.
    reference = ReferenceModel(id=uuid4(), workspace_id=workspace_id, product_id=product_id)
    monkeypatch.setattr(router, "require_workspace_permission", AsyncMock())
    monkeypatch.setattr(AssetRepository, "get_for_workspace", AsyncMock(return_value=asset))
    monkeypatch.setattr(ReferenceRepository, "get_by_asset", AsyncMock(return_value=reference))
    response = await router.get_asset(workspace_id, asset.id, user, session, "privacy-test")
    assert response.data["product_id"] == str(product_id)


async def test_intelligence_projects_workspace_reference_instead_of_global_product(
    session: Mock, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    asset, workspace_id, product_id = _market_asset(), uuid4(), uuid4()
    asset.product_id = uuid4()
    reference = ReferenceModel(id=uuid4(), workspace_id=workspace_id, product_id=product_id)
    monkeypatch.setattr(AssetRepository, "get_for_workspace", AsyncMock(return_value=asset))
    monkeypatch.setattr(
        AssetRepository, "get_current_version_in_workspace", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(ReferenceRepository, "get_by_asset", AsyncMock(return_value=reference))
    session.scalar.return_value = None
    session.scalars.return_value = []
    response = await MarketWorkflowService(session, settings).get_asset_intelligence(
        workspace_id, asset.id
    )
    assert response["asset"]["product_id"] == str(product_id)  # type: ignore[index]


async def test_save_reference_keeps_product_off_shared_market_asset(
    session: Mock, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    asset, workspace_id, product_id, source_id = _market_asset(), uuid4(), uuid4(), uuid4()
    service = TikTokCommercialContentService(session, settings)
    source = Mock(id=source_id, provider_entity_type="ad")
    monkeypatch.setattr(service._sources, "get_source_record", AsyncMock(return_value=source))
    monkeypatch.setattr(service._sources, "link_asset", AsyncMock())
    monkeypatch.setattr(
        service,
        "_get_ad_detail_raw",
        AsyncMock(return_value=map_ad_result(source_id, {"ad": {"id": "42"}})),
    )
    monkeypatch.setattr(ReferenceBoardRepository, "get", AsyncMock(return_value=Mock()))
    monkeypatch.setattr(ProductQueries, "exists_in_workspace", AsyncMock(return_value=True))
    monkeypatch.setattr(
        AssetRepository,
        "get_or_create_market_asset",
        AsyncMock(return_value=(asset, AssetVersionModel(id=asset.current_version_id))),
    )
    monkeypatch.setattr(ReferenceRepository, "get_by_asset", AsyncMock(return_value=None))
    create_reference = AsyncMock(return_value=ReferenceModel(id=uuid4()))
    monkeypatch.setattr(ReferenceRepository, "create", create_reference)
    await service.save_reference(
        workspace_id,
        uuid4(),
        source_id,
        SaveReferenceRequest(board_id=uuid4(), product_id=product_id),
    )
    assert asset.product_id is None
    assert create_reference.call_args.kwargs["workspace_id"] == workspace_id
    assert create_reference.call_args.kwargs["product_id"] == product_id
