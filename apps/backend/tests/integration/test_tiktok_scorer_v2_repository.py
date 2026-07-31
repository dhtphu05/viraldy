from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session
from testcontainers.postgres import PostgresContainer  # type: ignore[import-untyped]

from alembic import command
from alembic.config import Config
from viraldy.modules.assets.models import AssetModel, AssetVersionModel
from viraldy.modules.identity.models import UserModel
from viraldy.modules.jobs.repository import JobRepository
from viraldy.modules.jobs.schemas import JobResponse
from viraldy.modules.media_analysis.models import EvidenceItemModel
from viraldy.modules.products.contracts import build_minimal_product_context
from viraldy.modules.products.models import ProductModel
from viraldy.modules.tiktok_scorer.models import (
    TikTokFixActionEventModel,
    TikTokFixActionModel,
    TikTokScoreComparisonModel,
    TikTokScoreFindingModel,
    TikTokScoreRunModel,
)
from viraldy.modules.tiktok_scorer.repository import SyncTikTokScoreRepository
from viraldy.modules.tiktok_scorer.schemas import (
    CreateTikTokScoreRequest,
    CreateTikTokScoreRevisionRequest,
    RecordTikTokFixActionRequest,
)
from viraldy.modules.tiktok_scorer.service import TikTokScoreService
from viraldy.modules.workspaces.models import WorkspaceModel
from viraldy.platform.config.settings import get_settings
from viraldy.shared.errors.base import NotFoundError

BACKEND_DIR = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class _DatabaseUrls:
    sync: str
    async_: str


@pytest.fixture(scope="module")
def scorer_postgres() -> Iterator[_DatabaseUrls]:
    previous_sync = os.environ.get("DATABASE_SYNC_URL")
    previous_async = os.environ.get("DATABASE_URL")
    with PostgresContainer("postgres:16.6-alpine") as postgres:
        sync_url = postgres.get_connection_url().replace(
            "postgresql+psycopg2",
            "postgresql+psycopg",
        )
        async_url = sync_url.replace("postgresql+psycopg", "postgresql+asyncpg")
        os.environ["DATABASE_SYNC_URL"] = sync_url
        os.environ["DATABASE_URL"] = async_url
        get_settings.cache_clear()
        config = Config(str(BACKEND_DIR / "alembic.ini"))
        config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
        command.upgrade(config, "head")
        yield _DatabaseUrls(sync=sync_url, async_=async_url)

    _restore_environment("DATABASE_SYNC_URL", previous_sync)
    _restore_environment("DATABASE_URL", previous_async)
    get_settings.cache_clear()


def _restore_environment(name: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value


@pytest.mark.asyncio
async def test_score_service_persists_tenant_safe_revision_lifecycle(
    scorer_postgres: _DatabaseUrls,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.tiktok_scorer.service as scorer_service

    engine = create_async_engine(scorer_postgres.async_)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def request_job(
        session: AsyncSession,
        workspace_id: UUID,
        subject_type: str,
        subject_id: UUID,
        job_type: str,
        input_json: dict[str, object],
        idempotency_key: str | None,
    ) -> JobResponse:
        repository = JobRepository(session)
        existing = await repository.get_existing_idempotent(
            workspace_id,
            job_type,
            idempotency_key,
        )
        if existing is None:
            existing = await repository.create_mvp_job(
                workspace_id=workspace_id,
                subject_type=subject_type,
                subject_id=subject_id,
                job_type=job_type,
                input_json=input_json,
                idempotency_key=idempotency_key,
            )
        await session.commit()
        return JobResponse.model_validate(existing)

    monkeypatch.setattr(scorer_service, "request_mvp_job", request_job)

    try:
        async with factory() as session:
            user, alpha, beta, product, asset, version_one, version_two = await _seed_graph(session)
            service = TikTokScoreService(session, get_settings())
            create_request = CreateTikTokScoreRequest(
                asset_version_id=version_one.id,
                product_id=product.id,
                score_mode="product_aware",
                target_query="how to organize a small counter",
            )
            first = await service.create(
                alpha.id,
                create_request,
                "score-create-1",
                user.id,
            )
            retried = await service.create(
                alpha.id,
                create_request,
                "score-create-1",
                user.id,
            )

            assert retried.run_id == first.run_id
            assert retried.job_id == first.job_id
            assert first.score_run.product_context_snapshot_json is not None
            original_hash = first.score_run.product_context_snapshot_hash
            original_name = first.score_run.product_context_snapshot_json["product_context"][
                "identity"
            ]["name"]
            product.product_context_json = build_minimal_product_context(
                name="Changed after score creation",
                description=None,
                market="US",
            ).model_dump(mode="json")
            await session.commit()

            detail = await service.get(alpha.id, first.run_id)
            assert detail.job is not None
            assert detail.job.id == first.job_id
            assert detail.asset_filename == "draft-one.mp4"
            assert detail.asset_name == "draft-one.mp4"
            assert detail.product_name == original_name
            assert detail.revision_count == 0
            assert detail.comparison_ids == []
            assert detail.score_run.product_context_snapshot_hash == original_hash
            assert (
                detail.score_run.product_context_snapshot_json["product_context"]["identity"][
                    "name"
                ]
                == original_name
            )
            assert detail.evidence[0].frame_available is True
            assert "storage_key" not in detail.evidence[0].value_summary_json

            history = await service.list(alpha.id, search="draft-one")
            assert history.total == 1
            assert history.items[0].id == first.run_id
            assert history.items[0].asset_filename == "draft-one.mp4"
            assert history.items[0].asset_name == "draft-one.mp4"
            assert history.items[0].product_name == original_name
            product_history = await service.list(alpha.id, search="Counter organizer")
            assert product_history.total == 1
            assert product_history.items[0].id == first.run_id
            assert (await service.list(beta.id)).total == 0
            with pytest.raises(NotFoundError):
                await service.get(beta.id, first.run_id)

            run = await session.get(TikTokScoreRunModel, first.run_id)
            assert run is not None
            run.status = "completed"
            run.current_stage = "completed"
            run.scene_inventory_json = {"coverage_status": "partial"}
            fix = _fix_action(alpha.id, run.id)
            session.add(fix)
            await session.commit()

            partial_history = await service.list(alpha.id, status="partial_evidence")
            assert partial_history.total == 1
            assert partial_history.items[0].id == run.id
            assert partial_history.items[0].status == "completed"

            action = await service.record_fix_action(
                alpha.id,
                run.id,
                fix.id,
                RecordTikTokFixActionRequest(event_type="accepted"),
                user.id,
                "accept-fix-1",
            )
            action_retry = await service.record_fix_action(
                alpha.id,
                run.id,
                fix.id,
                RecordTikTokFixActionRequest(event_type="accepted"),
                user.id,
                "accept-fix-1",
            )
            assert action.event.id == action_retry.event.id
            assert action.fix_action.current_action_state == "accepted"

            revision_request = CreateTikTokScoreRevisionRequest(
                asset_version_id=version_two.id,
                accepted_fix_action_ids=[fix.id],
            )
            revision = await service.create_revision(
                alpha.id,
                run.id,
                revision_request,
                user.id,
                "score-revision-1",
            )
            revision_retry = await service.create_revision(
                alpha.id,
                run.id,
                revision_request,
                user.id,
                "score-revision-1",
            )
            assert revision_retry.run_id == revision.run_id
            assert revision_retry.comparison_id == revision.comparison_id
            assert revision.score_run.parent_score_run_id == run.id
            assert revision.score_run.product_context_snapshot_hash == original_hash
            comparison = await service.get_comparison(
                alpha.id,
                run.id,
                revision.comparison_id,
            )
            assert comparison.status == "pending"
            assert comparison.after_score_run_id == revision.run_id
            assert comparison.before_asset_version_id == version_one.id
            assert comparison.after_asset_version_id == version_two.id
            assert comparison.before_asset_filename == "draft-one.mp4"
            assert comparison.after_asset_filename == "draft-two.mp4"
            assert comparison.before_product_name == original_name
            assert comparison.after_product_name == original_name

            refreshed_parent = await service.get(alpha.id, run.id)
            assert refreshed_parent.revision_count == 1
            assert refreshed_parent.comparison_ids == [comparison.id]
            refreshed_revision = await service.get(alpha.id, revision.run_id)
            assert refreshed_revision.revision_count == 0
            assert refreshed_revision.comparison_ids == [comparison.id]

            revision_run = await session.get(TikTokScoreRunModel, revision.run_id)
            assert revision_run is not None
            revision_run.status = "completed"
            revision_run.current_stage = "completed"
            revision_run.scene_inventory_json = None
            revision_run.result_json = {
                "scene_inventory": {"coverage_status": "insufficient"}
            }
            await session.commit()
            partial_history = await service.list(alpha.id, status="partial_evidence")
            assert {item.id for item in partial_history.items} == {run.id, revision_run.id}

            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(TikTokScoreRunModel)
                    .where(TikTokScoreRunModel.workspace_id == alpha.id)
                )
                == 2
            )
            assert (
                await session.scalar(select(func.count()).select_from(TikTokScoreComparisonModel))
                == 1
            )
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(TikTokFixActionEventModel)
                    .where(TikTokFixActionEventModel.fix_action_id == fix.id)
                )
                == 1
            )
    finally:
        await engine.dispose()


def test_sync_persistence_flushes_findings_before_fix_actions(
    scorer_postgres: _DatabaseUrls,
) -> None:
    engine = create_engine(scorer_postgres.sync)
    try:
        with Session(engine) as session:
            user = UserModel(
                external_auth_id=f"scorer-sync-{uuid4()}",
                email="scorer-sync@example.com",
            )
            session.add(user)
            session.flush()
            workspace = WorkspaceModel(
                name="Sync Persistence",
                slug=f"sync-persistence-{uuid4()}",
                created_by_user_id=user.id,
            )
            session.add(workspace)
            session.flush()
            asset = AssetModel(
                workspace_id=workspace.id,
                asset_type="ugc",
                status="uploaded",
                created_by_user_id=user.id,
                metadata_json={},
            )
            session.add(asset)
            session.flush()
            version = AssetVersionModel(
                asset_id=asset.id,
                version_number=1,
                storage_key=f"workspaces/{workspace.id}/sofa-live.mp4",
                original_filename="sofa-live.mp4",
                declared_mime_type="video/mp4",
                detected_mime_type="video/mp4",
                size_bytes=100,
                checksum_sha256="c" * 64,
                metadata_json={},
                validation_status="uploaded",
            )
            session.add(version)
            session.flush()
            asset.current_version_id = version.id
            run = TikTokScoreRunModel(
                workspace_id=workspace.id,
                asset_id=asset.id,
                asset_version_id=version.id,
                status="processing",
                current_stage="persisting",
                analysis_mode="live",
                rubric_version="tiktok_diagnostic_v2",
                rule_version="tiktok_diagnostic_v2",
            )
            session.add(run)
            session.flush()

            finding_id = uuid4()
            fix_id = uuid4()
            SyncTikTokScoreRepository(session).persist_v2_result(
                run,
                {
                    "schema_version": "tiktok_score_v2",
                    "overall_score": 44,
                    "overall_confidence": "medium",
                    "creative_structure_decision": "blocked",
                    "dimensions": [],
                    "findings": [
                        {
                            "id": str(finding_id),
                            "code": "REQUIRED_DISCLOSURE_MISSING",
                            "rule_code": "FTC_REQUIRED_DISCLOSURE_MISSING",
                            "rule_class": "official_hard_rule",
                            "source_dimension": "claim_safety",
                            "severity": "hard",
                            "priority": "P0",
                            "applicability": "applicable",
                            "evidence_status": "sufficient",
                            "title": "A required disclosure is missing",
                            "reason": "Product Context requires clear disclosure.",
                            "expected": {"approved_disclosure_text": "Check size before ordering."},
                            "observed": {"disclosure_observed": False},
                            "evidence_ids": [],
                            "uncertainty": [],
                        }
                    ],
                    "required_fixes": [
                        {
                            "id": str(fix_id),
                            "code": "FIX_REQUIRED_DISCLOSURE_MISSING",
                            "source_finding_id": str(finding_id),
                            "source_finding_code": "REQUIRED_DISCLOSURE_MISSING",
                            "recommendation_class": "required_fix",
                            "basis": "official_rule",
                            "priority": "P0",
                            "severity": "hard",
                            "source_dimension": "claim_safety",
                            "owner_role": "editor",
                            "fix_type": "add_overlay",
                            "title": "Resolve a required disclosure is missing",
                            "why_it_matters": "Product Context requires clear disclosure.",
                            "expected": {"approved_disclosure_text": "Check size before ordering."},
                            "observed": {"disclosure_observed": False},
                            "evidence_ids": [],
                            "video_operations": [],
                            "instructions": ["Add the approved disclosure."],
                            "strengths_to_preserve": [],
                            "required_inputs": [],
                            "estimated_effort": "low",
                            "reshoot_required": False,
                            "completion_criteria": ["Disclosure is readable."],
                            "verification_method": "Review OCR evidence.",
                        }
                    ],
                    "strengths": [],
                    "evidence_ids": [],
                },
                model_version="openai-live-regression",
            )
            session.commit()

            assert (
                session.scalar(
                    select(func.count())
                    .select_from(TikTokScoreFindingModel)
                    .where(TikTokScoreFindingModel.id == finding_id)
                )
                == 1
            )
            action = session.get(TikTokFixActionModel, fix_id)
            assert action is not None
            assert action.finding_id == finding_id
    finally:
        engine.dispose()


async def _seed_graph(
    session: AsyncSession,
) -> tuple[
    UserModel,
    WorkspaceModel,
    WorkspaceModel,
    ProductModel,
    AssetModel,
    AssetVersionModel,
    AssetVersionModel,
]:
    user = UserModel(external_auth_id=f"scorer-{uuid4()}", email="scorer@example.com")
    session.add(user)
    await session.flush()
    alpha = WorkspaceModel(name="Alpha", slug=f"alpha-{uuid4()}", created_by_user_id=user.id)
    beta = WorkspaceModel(name="Beta", slug=f"beta-{uuid4()}", created_by_user_id=user.id)
    session.add_all([alpha, beta])
    await session.flush()
    product_context = build_minimal_product_context(
        name="Counter organizer",
        description="Organizes a small counter.",
        market="US",
    )
    product = ProductModel(
        workspace_id=alpha.id,
        name="Counter organizer",
        market="US",
        metadata_json={},
        product_context_json=product_context.model_dump(mode="json"),
        context_schema_version=product_context.schema_version,
        product_context_version=1,
        created_by_user_id=user.id,
    )
    session.add(product)
    await session.flush()
    asset = AssetModel(
        workspace_id=alpha.id,
        product_id=product.id,
        asset_type="ugc",
        status="uploaded",
        created_by_user_id=user.id,
        metadata_json={},
    )
    session.add(asset)
    await session.flush()
    version_one = AssetVersionModel(
        asset_id=asset.id,
        version_number=1,
        storage_key=f"workspaces/{alpha.id}/draft-one.mp4",
        original_filename="draft-one.mp4",
        declared_mime_type="video/mp4",
        detected_mime_type="video/mp4",
        size_bytes=100,
        checksum_sha256="a" * 64,
        metadata_json={},
        validation_status="uploaded",
    )
    version_two = AssetVersionModel(
        asset_id=asset.id,
        version_number=2,
        storage_key=f"workspaces/{alpha.id}/draft-two.mp4",
        original_filename="draft-two.mp4",
        declared_mime_type="video/mp4",
        detected_mime_type="video/mp4",
        size_bytes=110,
        checksum_sha256="b" * 64,
        metadata_json={},
        validation_status="uploaded",
    )
    session.add_all([version_one, version_two])
    await session.flush()
    asset.current_version_id = version_two.id
    session.add(
        EvidenceItemModel(
            workspace_id=alpha.id,
            asset_version_id=version_one.id,
            analysis_run_type="tiktok_score_run",
            evidence_type="on_screen_text",
            start_ms=0,
            end_ms=900,
            frame_storage_key=f"workspaces/{alpha.id}/private-frame.jpg",
            value_json={
                "text": "Small counter reset",
                "storage_key": f"workspaces/{alpha.id}/private-frame.jpg",
            },
            confidence=0.9,
            source="ocr",
        )
    )
    await session.commit()
    return user, alpha, beta, product, asset, version_one, version_two


def _fix_action(workspace_id: UUID, score_run_id: UUID) -> TikTokFixActionModel:
    return TikTokFixActionModel(
        workspace_id=workspace_id,
        score_run_id=score_run_id,
        code="MOVE_CLOSEUP_EARLIER",
        recommendation_class="required_fix",
        basis="video_diagnosis",
        priority="P1",
        severity="high",
        source_dimension="product_visibility",
        owner_role="editor",
        fix_type="trim_or_reorder",
        title="Move the existing product close-up earlier",
        why_it_matters="The selected profile needs earlier product grounding.",
        expected_json={"first_product_ms": 3000},
        observed_json={"first_product_ms": 5200},
        evidence_ids_json=[],
        video_operations_json=[],
        instructions_json=["Move the verified close-up before the story beat."],
        strengths_to_preserve_json=["Keep the natural creator delivery."],
        required_inputs_json=[],
        estimated_effort="low",
        reshoot_required=False,
        completion_criteria_json=["Product is grounded before 3000ms."],
        verification_method="Compare product appearance evidence after revision.",
        action_json={},
    )
