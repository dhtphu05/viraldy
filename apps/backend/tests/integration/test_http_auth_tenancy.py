from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer  # type: ignore[import-untyped]

from alembic import command
from alembic.config import Config
from viraldy.api.dependencies.auth import get_token_verifier
from viraldy.modules.ai_gateway.models import AiModelRunModel
from viraldy.modules.assets.models import AssetModel, AssetVersionModel
from viraldy.modules.campaign_packs.models import (
    CampaignPackModel,
    CampaignPackVersionModel,
)
from viraldy.modules.creative_dna.models import CreativeDnaVersionModel
from viraldy.modules.identity.models import UserModel
from viraldy.modules.identity.public import get_or_create_current_user
from viraldy.modules.jobs.models import ProcessingJobModel
from viraldy.modules.pattern_kits.models import PatternKitModel
from viraldy.modules.preflight.models import PreflightRunModel
from viraldy.modules.product_events.models import ProductEventModel
from viraldy.modules.recommendations.models import RecommendationModel
from viraldy.modules.reference_boards.models import ReferenceBoardModel
from viraldy.modules.references.models import ReferenceModel
from viraldy.modules.viral_kits.models import ViralKitModel
from viraldy.platform.auth.token_verifier import VerifiedToken
from viraldy.platform.clock.utc import utc_now
from viraldy.platform.config.settings import get_settings
from viraldy.platform.database.session import get_async_session
from viraldy.platform.storage.ports import ObjectMetadata, PresignedUpload
from viraldy.shared.errors.base import UnauthorizedError

BACKEND_DIR = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class DatabaseUrls:
    sync: str
    async_: str


@dataclass(frozen=True)
class ForeignResourceIds:
    asset: UUID
    reference: UUID
    creative_dna: UUID
    pattern_kit: UUID
    viral_kit: UUID
    campaign_pack: UUID
    preflight_run: UUID
    recommendation: UUID
    job: UUID
    model_run: UUID


class MappingTokenVerifier:
    def __init__(self) -> None:
        self._tokens = {
            "alpha-token": VerifiedToken(
                external_auth_id="integration-alpha",
                email="alpha@example.com",
                display_name="Alpha",
            ),
            "beta-token": VerifiedToken(
                external_auth_id="integration-beta",
                email="beta@example.com",
                display_name="Beta",
            ),
        }

    async def verify(self, token: str) -> VerifiedToken:
        verified = self._tokens.get(token)
        if verified is None:
            raise UnauthorizedError()
        return verified


class MemoryStorage:
    def __init__(self) -> None:
        self._metadata: dict[str, ObjectMetadata] = {}
        self.last_upload_key: str | None = None

    def create_presigned_upload(self, key: str, content_type: str) -> PresignedUpload:
        self.last_upload_key = key
        return PresignedUpload(
            url=f"http://storage.test/{key}",
            method="PUT",
            required_headers={"Content-Type": content_type},
            expires_at=utc_now() + timedelta(minutes=5),
        )

    def store_last_upload(self, size_bytes: int, content_type: str = "video/mp4") -> None:
        assert self.last_upload_key is not None
        self._metadata[self.last_upload_key] = ObjectMetadata(
            size_bytes=size_bytes,
            content_type=content_type,
            checksum_sha256=f"{size_bytes:064x}",
        )

    def object_exists(self, key: str) -> bool:
        return key in self._metadata

    def get_object_metadata(self, key: str) -> ObjectMetadata:
        return self._metadata[key]


@pytest.fixture(scope="module")
def migrated_postgres() -> Iterator[DatabaseUrls]:
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
        yield DatabaseUrls(sync=sync_url, async_=async_url)

    _restore_environment("DATABASE_SYNC_URL", previous_sync)
    _restore_environment("DATABASE_URL", previous_async)
    get_settings.cache_clear()


def _restore_environment(name: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _assert_error(response: httpx.Response, status_code: int, code: str) -> None:
    assert response.status_code == status_code
    body = response.json()
    assert body["data"] is None
    assert body["error"]["code"] == code
    assert body["meta"]["request_id"]


async def _seed_foreign_resources(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    product_id: UUID,
    user_id: UUID,
) -> ForeignResourceIds:
    asset = AssetModel(
        workspace_id=workspace_id,
        product_id=product_id,
        asset_type="ugc",
        status="uploaded",
        current_version_id=None,
        created_by_user_id=user_id,
        metadata_json={},
    )
    session.add(asset)
    await session.flush()
    asset_version = AssetVersionModel(
        asset_id=asset.id,
        version_number=1,
        storage_key=f"test/{workspace_id}/{asset.id}/source.mp4",
        original_filename="foreign.mp4",
        declared_mime_type="video/mp4",
        detected_mime_type="video/mp4",
        size_bytes=8,
        checksum_sha256="0" * 64,
        metadata_json={},
        validation_status="uploaded",
    )
    session.add(asset_version)
    await session.flush()
    asset.current_version_id = asset_version.id

    board = ReferenceBoardModel(
        workspace_id=workspace_id,
        product_id=product_id,
        name="Foreign board",
        description=None,
        board_type="creative_research",
        status="active",
        created_by_user_id=user_id,
    )
    session.add(board)
    await session.flush()
    reference = ReferenceModel(
        workspace_id=workspace_id,
        board_id=board.id,
        product_id=product_id,
        asset_id=asset.id,
        source_platform="tiktok",
        source_url=None,
        title="Foreign reference",
        notes=None,
        status="ready",
        created_by_user_id=user_id,
    )
    session.add(reference)

    creative_dna = CreativeDnaVersionModel(
        workspace_id=workspace_id,
        reference_id=None,
        asset_version_id=asset_version.id,
        version_number=1,
        status="completed",
        schema_version="creative_dna_v1",
        dna_json={},
        confidence="low",
        analysis_mode="fixture",
        pipeline_version="media_pipeline_v1",
        taxonomy_version="integration-test-v1",
    )
    pattern_kit = PatternKitModel(
        workspace_id=workspace_id,
        name="Foreign PatternKit",
        kind="single_asset_abstraction",
        scope="workspace_private",
        status="candidate",
        primary_category=None,
        target_platforms_json=[],
        target_markets_json=[],
        objectives_json=[],
        latest_version=1,
        created_by_user_id=user_id,
    )
    viral_kit = ViralKitModel(
        workspace_id=workspace_id,
        product_id=product_id,
        name="Foreign ViralKit",
        objective="tiktok_shop_affiliate_test",
        platform="tiktok_shop",
        target_market="US",
        status="draft",
        latest_version=1,
        selected_concept_id=None,
        created_by_user_id=user_id,
    )
    campaign_pack = CampaignPackModel(
        workspace_id=workspace_id,
        product_id=product_id,
        adaptation_run_id=None,
        status="draft",
        current_version_id=None,
        created_by_user_id=user_id,
    )
    session.add_all([creative_dna, pattern_kit, viral_kit, campaign_pack])
    await session.flush()

    campaign_pack_version = CampaignPackVersionModel(
        campaign_pack_id=campaign_pack.id,
        version_number=1,
        brief_json={},
        brief_schema_version="campaign_pack_brief_v1",
        product_snapshot_json=None,
        compiled_requirements_json={},
        requirements_schema_version="compiled_requirements_v2",
        change_note=None,
        created_by_user_id=user_id,
    )
    session.add(campaign_pack_version)
    await session.flush()
    campaign_pack.current_version_id = campaign_pack_version.id

    preflight_run = PreflightRunModel(
        workspace_id=workspace_id,
        ugc_asset_version_id=asset_version.id,
        campaign_pack_version_id=campaign_pack_version.id,
        status="completed",
        structural_score=0,
        brief_alignment_score=0,
        preflight_score=0,
        confidence="low",
        action_label="revise",
        dimension_scores_json={},
        brief_alignment_json={},
        strengths_json=[],
        blockers_json=[],
        fixes_json=[],
        revision_message="",
        evidence_ids_json=[],
        schema_version="ugc_preflight_v2",
        product_snapshot_json=None,
        requirements_snapshot_json=None,
        analysis_mode="fixture",
        pipeline_version="media_pipeline_v1",
        rubric_version="ugc_preflight_rubric_v2",
        rule_version="ugc_preflight_rules_v2",
    )
    session.add(preflight_run)
    await session.flush()
    recommendation = RecommendationModel(
        workspace_id=workspace_id,
        subject_type="preflight_run",
        subject_id=preflight_run.id,
        recommendation_type="revision",
        action="Revise",
        confidence="low",
        reasoning="Integration test fixture.",
        evidence_json={},
        assumptions_json=[],
        payload_schema_version="recommendation_v2",
    )
    job = ProcessingJobModel(
        workspace_id=workspace_id,
        subject_type="asset",
        subject_id=asset.id,
        job_type="process_asset",
        queue_name="default",
        status="succeeded",
        progress=100,
        attempt_count=1,
        max_attempts=3,
        idempotency_key=f"foreign-{uuid4()}",
        input_json={},
        output_json={},
    )
    model_run = AiModelRunModel(
        workspace_id=workspace_id,
        processing_job_id=None,
        subject_type="pattern_kit",
        subject_id=pattern_kit.id,
        capability="pattern_kit_extract",
        operation="pattern_kit_extract",
        analysis_mode="fixture",
        provider="fixture",
        model="fixture_pattern_kit_v1",
        prompt_version="pattern_kit_extraction_v1",
        response_schema_version="pattern_kit_v1",
        schema_version="pattern_kit_v1",
        status="completed",
        attempt=1,
        attempt_count=1,
        request_hash="a" * 64,
        input_hash="a" * 64,
        input_summary_json={"source_count": 1},
        output_summary_json={"sequence_count": 3},
        usage_json={},
        started_at=utc_now(),
        completed_at=utc_now(),
    )
    session.add_all([recommendation, job, model_run])
    await session.commit()
    return ForeignResourceIds(
        asset=asset.id,
        reference=reference.id,
        creative_dna=creative_dna.id,
        pattern_kit=pattern_kit.id,
        viral_kit=viral_kit.id,
        campaign_pack=campaign_pack.id,
        preflight_run=preflight_run.id,
        recommendation=recommendation.id,
        job=job.id,
        model_run=model_run.id,
    )


def _pattern_kit_create_payload(source_id: UUID) -> dict[str, object]:
    return {
        "name": "Tenant isolation pattern",
        "kind": "single_asset_abstraction",
        "scope": "workspace_private",
        "source_creative_dna_version_ids": [str(source_id)],
        "primary_category": "home_organization",
        "target_platforms": ["tiktok_shop"],
        "target_markets": ["US"],
        "objectives": ["affiliate"],
        "extraction_mode": "ai_assisted",
    }


async def _assert_foreign_kit_mutations_are_hidden(
    client: httpx.AsyncClient,
    *,
    workspace_id: str,
    foreign: ForeignResourceIds,
) -> None:
    headers = _auth("alpha-token")
    pattern_base = f"/api/v1/workspaces/{workspace_id}/pattern-kits/{foreign.pattern_kit}"
    viral_base = f"/api/v1/workspaces/{workspace_id}/viral-kits/{foreign.viral_kit}"
    requests = (
        (
            client.post(
                f"{pattern_base}/versions",
                headers=headers,
                json={"change_reason": "Foreign version must stay hidden."},
            ),
            "PATTERN_KIT_NOT_FOUND",
        ),
        (
            client.post(
                f"{pattern_base}/actions",
                headers=headers,
                json={"action": "reviewed", "reason": "Foreign action must stay hidden."},
            ),
            "PATTERN_KIT_NOT_FOUND",
        ),
        (
            client.post(
                f"{pattern_base}/feedback",
                headers=headers,
                json={
                    "field_path": "opening.hook_mechanism",
                    "feedback_type": "partial",
                },
            ),
            "PATTERN_KIT_NOT_FOUND",
        ),
        (
            client.delete(pattern_base, headers=headers),
            "DELETION_RESOURCE_NOT_FOUND",
        ),
        (
            client.post(
                f"{viral_base}/versions",
                headers=headers,
                json={"change_reason": "Foreign version must stay hidden."},
            ),
            "VIRAL_KIT_NOT_FOUND",
        ),
        (
            client.post(
                f"{viral_base}/concept-actions",
                headers=headers,
                json={
                    "concept_id": "concept-1",
                    "action": "selected",
                    "reason": "Foreign action must stay hidden.",
                },
            ),
            "VIRAL_KIT_NOT_FOUND",
        ),
        (
            client.post(
                f"{viral_base}/concepts/concept-1/campaign-pack",
                headers=headers,
                json={},
            ),
            "VIRAL_KIT_NOT_FOUND",
        ),
        (
            client.post(
                f"{viral_base}/feedback",
                headers=headers,
                json={"field_path": "concepts.0.name", "feedback_type": "partial"},
            ),
            "VIRAL_KIT_NOT_FOUND",
        ),
        (
            client.delete(viral_base, headers=headers),
            "DELETION_RESOURCE_NOT_FOUND",
        ),
    )
    for pending_response, error_code in requests:
        _assert_error(await pending_response, 404, error_code)

    _assert_error(
        await client.post(
            f"/api/v1/workspaces/{workspace_id}/viral-kits",
            headers=headers,
            json={
                "product_id": str(foreign.campaign_pack),
                "expected_product_context_version": 1,
                "pattern_kit_version_ids": [str(uuid4())],
                "objective": "tiktok_shop_affiliate_test",
                "platform": "tiktok_shop",
                "target_market": "US",
                "concept_count": 3,
            },
        ),
        404,
        "PRODUCT_NOT_FOUND",
    )


@pytest.mark.asyncio
async def test_http_auth_rbac_and_tenant_isolation(
    migrated_postgres: DatabaseUrls,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.assets.router as assets_router
    from viraldy.api.main import create_app

    engine = create_async_engine(migrated_postgres.async_)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    verifier = MappingTokenVerifier()
    storage = MemoryStorage()
    monkeypatch.setattr(assets_router, "S3StorageAdapter", lambda _: storage)
    app = create_app()

    async def test_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_async_session] = test_session
    app.dependency_overrides[get_token_verifier] = lambda: verifier
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)

    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            _assert_error(await client.get("/api/v1/me"), 401, "UNAUTHENTICATED")
            _assert_error(
                await client.get(
                    "/api/v1/me",
                    headers={"Authorization": "Basic not-a-bearer-token"},
                ),
                401,
                "UNAUTHENTICATED",
            )
            _assert_error(
                await client.get("/api/v1/me", headers=_auth("invalid-token")),
                401,
                "UNAUTHENTICATED",
            )

            alpha = (await client.get("/api/v1/me", headers=_auth("alpha-token"))).json()["data"]
            repeated_alpha = (await client.get("/api/v1/me", headers=_auth("alpha-token"))).json()[
                "data"
            ]
            beta = (await client.get("/api/v1/me", headers=_auth("beta-token"))).json()["data"]
            assert repeated_alpha["id"] == alpha["id"]

            workspace_alpha = (
                await client.post(
                    "/api/v1/workspaces",
                    headers=_auth("alpha-token"),
                    json={"name": "Alpha Workspace", "slug": f"alpha-{uuid4()}"},
                )
            ).json()["data"]
            workspace_beta = (
                await client.post(
                    "/api/v1/workspaces",
                    headers=_auth("beta-token"),
                    json={"name": "Beta Workspace", "slug": f"beta-{uuid4()}"},
                )
            ).json()["data"]

            product_alpha_response = await client.post(
                f"/api/v1/workspaces/{workspace_alpha['id']}/products",
                headers=_auth("alpha-token"),
                json={"name": "Alpha Product"},
            )
            assert product_alpha_response.status_code == 201
            product_alpha = product_alpha_response.json()["data"]
            product_beta_response = await client.post(
                f"/api/v1/workspaces/{workspace_beta['id']}/products",
                headers=_auth("beta-token"),
                json={"name": "Beta Product"},
            )
            assert product_beta_response.status_code == 201
            product_beta = product_beta_response.json()["data"]

            foreign_product = await client.get(
                f"/api/v1/workspaces/{workspace_alpha['id']}/products/{product_beta['id']}",
                headers=_auth("alpha-token"),
            )
            _assert_error(foreign_product, 404, "PRODUCT_NOT_FOUND")
            async with session_factory() as session:
                foreign = await _seed_foreign_resources(
                    session,
                    workspace_id=UUID(workspace_beta["id"]),
                    product_id=UUID(product_beta["id"]),
                    user_id=UUID(beta["id"]),
                )
            foreign_resource_paths = {
                f"/api/v1/workspaces/{workspace_alpha['id']}/assets/{foreign.asset}": (
                    "ASSET_NOT_FOUND"
                ),
                f"/api/v1/workspaces/{workspace_alpha['id']}/assets/"
                f"{foreign.asset}/versions": "ASSET_NOT_FOUND",
                f"/api/v1/workspaces/{workspace_alpha['id']}/references/{foreign.reference}": (
                    "REFERENCE_NOT_FOUND"
                ),
                f"/api/v1/workspaces/{workspace_alpha['id']}/creative-dna/"
                f"{foreign.creative_dna}": "CREATIVE_DNA_NOT_FOUND",
                f"/api/v1/workspaces/{workspace_alpha['id']}/pattern-kits/"
                f"{foreign.pattern_kit}": "PATTERN_KIT_NOT_FOUND",
                f"/api/v1/workspaces/{workspace_alpha['id']}/viral-kits/"
                f"{foreign.viral_kit}": "VIRAL_KIT_NOT_FOUND",
                f"/api/v1/workspaces/{workspace_alpha['id']}/campaign-packs/"
                f"{foreign.campaign_pack}": "CAMPAIGN_PACK_NOT_FOUND",
                f"/api/v1/workspaces/{workspace_alpha['id']}/preflight-runs/"
                f"{foreign.preflight_run}": "PREFLIGHT_RUN_NOT_FOUND",
                f"/api/v1/workspaces/{workspace_alpha['id']}/recommendations/"
                f"{foreign.recommendation}": "RECOMMENDATION_NOT_FOUND",
                f"/api/v1/workspaces/{workspace_alpha['id']}/jobs/{foreign.job}": "JOB_NOT_FOUND",
                f"/api/v1/workspaces/{workspace_alpha['id']}/model-runs/"
                f"{foreign.model_run}": "MODEL_RUN_NOT_FOUND",
            }
            for path, code in foreign_resource_paths.items():
                _assert_error(
                    await client.get(path, headers=_auth("alpha-token")),
                    404,
                    code,
                )
            filtered_patterns = await client.get(
                f"/api/v1/workspaces/{workspace_alpha['id']}/pattern-kits"
                f"?source_creative_dna_version_id={foreign.creative_dna}",
                headers=_auth("alpha-token"),
            )
            assert filtered_patterns.status_code == 200
            assert filtered_patterns.json()["data"] == []
            filtered_viral_kits = await client.get(
                f"/api/v1/workspaces/{workspace_alpha['id']}/viral-kits"
                f"?product_id={product_beta['id']}",
                headers=_auth("alpha-token"),
            )
            assert filtered_viral_kits.status_code == 200
            assert filtered_viral_kits.json()["data"] == []
            _assert_error(
                await client.post(
                    f"/api/v1/workspaces/{workspace_alpha['id']}/campaign-packs/"
                    f"{foreign.campaign_pack}/exports",
                    headers=_auth("alpha-token"),
                    json={"format": "json"},
                ),
                404,
                "CAMPAIGN_PACK_NOT_FOUND",
            )
            model_runs = await client.get(
                f"/api/v1/workspaces/{workspace_beta['id']}/model-runs"
                f"?subject_id={foreign.pattern_kit}",
                headers=_auth("beta-token"),
            )
            assert model_runs.status_code == 200
            assert [run["id"] for run in model_runs.json()["data"]] == [str(foreign.model_run)]
            assert "error_message" not in model_runs.json()["data"][0]

            _assert_error(
                await client.post(
                    f"/api/v1/workspaces/{workspace_alpha['id']}/pattern-kits",
                    headers=_auth("alpha-token"),
                    json=_pattern_kit_create_payload(foreign.creative_dna),
                ),
                404,
                "CREATIVE_DNA_NOT_FOUND",
            )
            await _assert_foreign_kit_mutations_are_hidden(
                client,
                workspace_id=workspace_alpha["id"],
                foreign=foreign,
            )
            async with session_factory() as session:
                deletable_pattern = PatternKitModel(
                    workspace_id=UUID(workspace_alpha["id"]),
                    name="Disposable PatternKit",
                    kind="single_asset_abstraction",
                    scope="workspace_private",
                    status="candidate",
                    primary_category="home_organization",
                    target_platforms_json=["tiktok_shop"],
                    target_markets_json=["US"],
                    objectives_json=["affiliate"],
                    latest_version=1,
                    created_by_user_id=UUID(alpha["id"]),
                )
                session.add(deletable_pattern)
                await session.commit()
                deletable_pattern_id = deletable_pattern.id
            assert (
                await client.delete(
                    f"/api/v1/workspaces/{workspace_alpha['id']}/pattern-kits/"
                    f"{deletable_pattern_id}",
                    headers=_auth("alpha-token"),
                )
            ).status_code == 204
            _assert_error(
                await client.get(
                    f"/api/v1/workspaces/{workspace_alpha['id']}/pattern-kits/"
                    f"{deletable_pattern_id}",
                    headers=_auth("alpha-token"),
                ),
                404,
                "PATTERN_KIT_NOT_FOUND",
            )
            async with session_factory() as session:
                deletable_viral = ViralKitModel(
                    workspace_id=UUID(workspace_alpha["id"]),
                    product_id=UUID(product_alpha["id"]),
                    name="Disposable ViralKit",
                    objective="tiktok_shop_affiliate_test",
                    platform="tiktok_shop",
                    target_market="US",
                    status="draft",
                    latest_version=1,
                    selected_concept_id=None,
                    created_by_user_id=UUID(alpha["id"]),
                )
                session.add(deletable_viral)
                await session.commit()
                deletable_viral_id = deletable_viral.id
            assert (
                await client.delete(
                    f"/api/v1/workspaces/{workspace_alpha['id']}/viral-kits/"
                    f"{deletable_viral_id}",
                    headers=_auth("alpha-token"),
                )
            ).status_code == 204
            _assert_error(
                await client.get(
                    f"/api/v1/workspaces/{workspace_alpha['id']}/viral-kits/"
                    f"{deletable_viral_id}",
                    headers=_auth("alpha-token"),
                ),
                404,
                "VIRAL_KIT_NOT_FOUND",
            )

            initial_upload_response = await client.post(
                f"/api/v1/workspaces/{workspace_alpha['id']}/assets/upload-sessions",
                headers=_auth("alpha-token"),
                json={
                    "filename": "ugc-draft.mp4",
                    "declared_mime_type": "video/mp4",
                    "declared_size_bytes": 8,
                    "asset_type": "ugc",
                    "product_id": product_alpha["id"],
                },
            )
            assert initial_upload_response.status_code == 201
            initial_upload = initial_upload_response.json()["data"]
            assert initial_upload["version_number"] == 1
            pending_revision = await client.post(
                f"/api/v1/workspaces/{workspace_alpha['id']}/assets/"
                f"{initial_upload['asset_id']}/versions/upload-sessions",
                headers=_auth("alpha-token"),
                json={
                    "filename": "too-early.mp4",
                    "declared_mime_type": "video/mp4",
                    "declared_size_bytes": 8,
                },
            )
            _assert_error(pending_revision, 400, "ASSET_NOT_READY")
            storage.store_last_upload(8)
            initial_complete = await client.post(
                f"/api/v1/workspaces/{workspace_alpha['id']}/assets/"
                f"{initial_upload['asset_id']}/complete-upload",
                headers=_auth("alpha-token"),
            )
            assert initial_complete.status_code == 200
            repeated_initial_complete = await client.post(
                f"/api/v1/workspaces/{workspace_alpha['id']}/assets/"
                f"{initial_upload['asset_id']}/complete-upload",
                headers=_auth("alpha-token"),
            )
            assert repeated_initial_complete.status_code == 200
            initial_as_revision = await client.post(
                f"/api/v1/workspaces/{workspace_alpha['id']}/assets/"
                f"{initial_upload['asset_id']}/versions/{initial_upload['asset_version_id']}"
                "/complete-upload",
                headers=_auth("alpha-token"),
            )
            _assert_error(initial_as_revision, 400, "ASSET_REVISION_REQUIRED")

            revision_two_response = await client.post(
                f"/api/v1/workspaces/{workspace_alpha['id']}/assets/"
                f"{initial_upload['asset_id']}/versions/upload-sessions",
                headers=_auth("alpha-token"),
                json={
                    "filename": "ugc-revision.mp4",
                    "declared_mime_type": "video/mp4",
                    "declared_size_bytes": 9,
                },
            )
            assert revision_two_response.status_code == 201
            revision_two = revision_two_response.json()["data"]
            assert revision_two["version_number"] == 2
            storage.store_last_upload(9)
            revision_three_response = await client.post(
                f"/api/v1/workspaces/{workspace_alpha['id']}/assets/"
                f"{initial_upload['asset_id']}/versions/upload-sessions",
                headers=_auth("alpha-token"),
                json={
                    "filename": "ugc-revision-latest.mp4",
                    "declared_mime_type": "video/mp4",
                    "declared_size_bytes": 10,
                },
            )
            assert revision_three_response.status_code == 201
            revision_three = revision_three_response.json()["data"]
            assert revision_three["version_number"] == 3
            storage.store_last_upload(10)

            revision_three_path = (
                f"/api/v1/workspaces/{workspace_alpha['id']}/assets/"
                f"{initial_upload['asset_id']}/versions/{revision_three['asset_version_id']}"
                "/complete-upload"
            )
            revision_three_complete = await client.post(
                revision_three_path,
                headers=_auth("alpha-token"),
            )
            assert revision_three_complete.status_code == 200
            assert revision_three_complete.json()["data"]["is_current"] is True
            repeated_revision_three = await client.post(
                revision_three_path,
                headers=_auth("alpha-token"),
            )
            assert repeated_revision_three.status_code == 200
            assert repeated_revision_three.json()["data"]["is_current"] is True

            revision_two_path = (
                f"/api/v1/workspaces/{workspace_alpha['id']}/assets/"
                f"{initial_upload['asset_id']}/versions/{revision_two['asset_version_id']}"
                "/complete-upload"
            )
            revision_two_complete = await client.post(
                revision_two_path,
                headers=_auth("alpha-token"),
            )
            assert revision_two_complete.status_code == 200
            assert revision_two_complete.json()["data"]["is_current"] is False
            assert (
                await client.post(revision_two_path, headers=_auth("alpha-token"))
            ).status_code == 200

            versions_response = await client.get(
                f"/api/v1/workspaces/{workspace_alpha['id']}/assets/"
                f"{initial_upload['asset_id']}/versions",
                headers=_auth("alpha-token"),
            )
            assert versions_response.status_code == 200
            versions = versions_response.json()["data"]
            assert [version["version_number"] for version in versions] == [3, 2, 1]
            assert [version["is_current"] for version in versions] == [True, False, False]

            upload_events = (
                await client.get(
                    f"/api/v1/workspaces/{workspace_alpha['id']}/events?limit=100",
                    headers=_auth("alpha-token"),
                )
            ).json()["data"]
            assert sum(event["event_type"] == "ugc_uploaded" for event in upload_events) == 1
            assert sum(event["event_type"] == "revision_uploaded" for event in upload_events) == 2

            reference_upload_response = await client.post(
                f"/api/v1/workspaces/{workspace_alpha['id']}/assets/upload-sessions",
                headers=_auth("alpha-token"),
                json={
                    "filename": "reference-source.mp4",
                    "declared_mime_type": "video/mp4",
                    "declared_size_bytes": 8,
                    "asset_type": "reference",
                    "product_id": product_alpha["id"],
                },
            )
            assert reference_upload_response.status_code == 201
            reference_upload = reference_upload_response.json()["data"]
            storage.store_last_upload(8)
            assert (
                await client.post(
                    f"/api/v1/workspaces/{workspace_alpha['id']}/assets/"
                    f"{reference_upload['asset_id']}/complete-upload",
                    headers=_auth("alpha-token"),
                )
            ).status_code == 200
            _assert_error(
                await client.post(
                    f"/api/v1/workspaces/{workspace_alpha['id']}/assets/"
                    f"{reference_upload['asset_id']}/versions/upload-sessions",
                    headers=_auth("alpha-token"),
                    json={
                        "filename": "reference-replacement.mp4",
                        "declared_mime_type": "video/mp4",
                        "declared_size_bytes": 8,
                    },
                ),
                400,
                "ASSET_REVISION_NOT_SUPPORTED",
            )

            opaque_id = uuid4()
            protected_paths = (
                f"/api/v1/workspaces/{workspace_beta['id']}/products/{opaque_id}",
                f"/api/v1/workspaces/{workspace_beta['id']}/assets/{opaque_id}",
                f"/api/v1/workspaces/{workspace_beta['id']}/references/{opaque_id}",
                f"/api/v1/workspaces/{workspace_beta['id']}/creative-dna/{opaque_id}",
                f"/api/v1/workspaces/{workspace_beta['id']}/pattern-kits/{opaque_id}",
                f"/api/v1/workspaces/{workspace_beta['id']}/viral-kits/{opaque_id}",
                f"/api/v1/workspaces/{workspace_beta['id']}/campaign-packs/{opaque_id}",
                f"/api/v1/workspaces/{workspace_beta['id']}/preflight-runs/{opaque_id}",
                f"/api/v1/workspaces/{workspace_beta['id']}/recommendations/{opaque_id}",
                f"/api/v1/workspaces/{workspace_beta['id']}/feedback",
                f"/api/v1/workspaces/{workspace_beta['id']}/events",
                f"/api/v1/workspaces/{workspace_beta['id']}/jobs/{opaque_id}",
                f"/api/v1/workspaces/{workspace_beta['id']}/model-runs/{opaque_id}",
            )
            for path in protected_paths:
                _assert_error(
                    await client.get(path, headers=_auth("alpha-token")),
                    403,
                    "FORBIDDEN",
                )

            add_viewer = await client.post(
                f"/api/v1/workspaces/{workspace_alpha['id']}/members",
                headers=_auth("alpha-token"),
                json={"email": beta["email"], "role": "viewer"},
            )
            assert add_viewer.status_code == 201

            viewer_read = await client.get(
                f"/api/v1/workspaces/{workspace_alpha['id']}/products",
                headers=_auth("beta-token"),
            )
            assert viewer_read.status_code == 200
            assert (
                await client.get(
                    f"/api/v1/workspaces/{workspace_alpha['id']}/pattern-kits",
                    headers=_auth("beta-token"),
                )
            ).status_code == 200
            assert (
                await client.get(
                    f"/api/v1/workspaces/{workspace_alpha['id']}/viral-kits",
                    headers=_auth("beta-token"),
                )
            ).status_code == 200
            viewer_write = await client.post(
                f"/api/v1/workspaces/{workspace_alpha['id']}/products",
                headers=_auth("beta-token"),
                json={"name": "Viewer Must Not Create"},
            )
            _assert_error(viewer_write, 403, "FORBIDDEN")
            _assert_error(
                await client.post(
                    f"/api/v1/workspaces/{workspace_alpha['id']}/products/crawl-preview",
                    headers=_auth("beta-token"),
                    json={"url": "https://www.amazon.com/dp/B0TEST1234"},
                ),
                403,
                "FORBIDDEN",
            )
            _assert_error(
                await client.post(
                    f"/api/v1/workspaces/{workspace_alpha['id']}/pattern-kits",
                    headers=_auth("beta-token"),
                    json=_pattern_kit_create_payload(uuid4()),
                ),
                403,
                "FORBIDDEN",
            )
            _assert_error(
                await client.post(
                    f"/api/v1/workspaces/{workspace_alpha['id']}/viral-kits",
                    headers=_auth("beta-token"),
                    json={
                        "product_id": product_alpha["id"],
                        "expected_product_context_version": 1,
                        "pattern_kit_version_ids": [str(uuid4())],
                        "objective": "tiktok_shop_affiliate_test",
                        "platform": "tiktok_shop",
                        "target_market": "US",
                        "concept_count": 3,
                    },
                ),
                403,
                "FORBIDDEN",
            )
            _assert_error(
                await client.get(
                    f"/api/v1/workspaces/{workspace_alpha['id']}/model-runs",
                    headers=_auth("beta-token"),
                ),
                403,
                "FORBIDDEN",
            )
            viewer_members = await client.get(
                f"/api/v1/workspaces/{workspace_alpha['id']}/members",
                headers=_auth("beta-token"),
            )
            _assert_error(viewer_members, 403, "FORBIDDEN")

            async with session_factory() as session:
                await session.execute(
                    update(UserModel)
                    .where(UserModel.id == UUID(beta["id"]))
                    .values(status="suspended")
                )
                await session.commit()
            _assert_error(
                await client.get("/api/v1/me", headers=_auth("beta-token")),
                403,
                "USER_SUSPENDED",
            )

        async with session_factory() as session:
            provisioned_count = await session.scalar(
                select(func.count())
                .select_from(UserModel)
                .where(UserModel.external_auth_id.in_(["integration-alpha", "integration-beta"]))
            )
            assert provisioned_count == 2
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest.mark.asyncio
async def test_concurrent_user_provisioning_is_idempotent(
    migrated_postgres: DatabaseUrls,
) -> None:
    engine = create_async_engine(migrated_postgres.async_)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    external_auth_id = f"concurrent-{uuid4()}"
    verified = VerifiedToken(
        external_auth_id=external_auth_id,
        email="concurrent@example.com",
        display_name="Concurrent User",
    )

    async def provision() -> UUID:
        async with session_factory() as session:
            return (await get_or_create_current_user(session, verified)).id

    try:
        user_ids = await asyncio.gather(provision(), provision())
        assert user_ids[0] == user_ids[1]

        async with session_factory() as session:
            count = await session.scalar(
                select(func.count())
                .select_from(UserModel)
                .where(UserModel.external_auth_id == external_auth_id)
            )
            assert count == 1
            signup_count = await session.scalar(
                select(func.count())
                .select_from(ProductEventModel)
                .where(
                    ProductEventModel.event_type == "user_signed_up",
                    ProductEventModel.subject_id == user_ids[0],
                )
            )
            assert signup_count == 1
    finally:
        await engine.dispose()
