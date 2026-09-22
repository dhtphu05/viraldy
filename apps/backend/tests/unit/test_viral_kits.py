from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.campaign_packs.contracts import CampaignPackBriefV1
from viraldy.modules.campaign_packs.public import CampaignPackCreationResult
from viraldy.modules.campaign_packs.requirements import CompiledRequirementsSnapshotV2
from viraldy.modules.campaign_packs.schemas import (
    CampaignPackResponse,
    CampaignPackVersionResponse,
)
from viraldy.modules.creative_dna.contracts import CreativeDnaV1
from viraldy.modules.creative_dna.service import _build_creative_dna, _evidence_by_type
from viraldy.modules.media_analysis.public import EvidenceItemModel
from viraldy.modules.pattern_kits.provider import (
    PatternEvidenceInput,
    PatternSourceInput,
    build_fixture_pattern_kit,
)
from viraldy.modules.pattern_kits.public import PatternKitVersionSnapshot
from viraldy.modules.pattern_kits.schemas import CreatePatternKitRequest
from viraldy.modules.products.contracts import (
    BuyerPersonaV1,
    ClaimRuleV1,
    CreativeContextV1,
    ProductBenefitV1,
    ProductContextV1,
    ProductFeatureV1,
    ProductGovernanceV1,
    ProductIdentityV1,
)
from viraldy.modules.products.public import ProductContextSnapshot
from viraldy.modules.viral_kits.contracts import CommercialConstraintsV1, ViralKitV1
from viraldy.modules.viral_kits.matcher import match_patterns
from viraldy.modules.viral_kits.models import (
    ViralKitConceptActionModel,
    ViralKitModel,
    ViralKitVersionModel,
)
from viraldy.modules.viral_kits.provider import (
    _native_output_validator,
    build_fixture_viral_kit,
    normalize_viral_kit_output,
)
from viraldy.modules.viral_kits.schemas import (
    CreateViralKitCampaignPackRequest,
    CreateViralKitRequest,
    CreateViralKitVersionRequest,
    ViralKitConceptActionRequest,
)
from viraldy.modules.viral_kits.service import ViralKitService
from viraldy.platform.clock.utc import utc_now
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError, ConflictError


@dataclass(slots=True)
class FakeEvidence:
    evidence_type: str
    value_json: dict[str, Any]
    asset_version_id: UUID
    id: UUID = field(default_factory=uuid4)
    start_ms: int | None = None
    end_ms: int | None = None
    confidence: float | None = 0.85
    source: str = "vision"


@dataclass(slots=True)
class FakeModelRun:
    id: UUID = field(default_factory=uuid4)


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.refreshed: list[object] = []

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, item: object) -> None:
        self.refreshed.append(item)


class FakeAiModelRunRepository:
    created: list[dict[str, object]] = []
    completed: list[tuple[UUID, dict[str, object]]] = []
    failed: list[tuple[UUID, str]] = []

    def __init__(self, session: FakeSession) -> None:
        self.session = session

    async def create_running(self, **kwargs: object) -> FakeModelRun:
        self.created.append(kwargs)
        return FakeModelRun()

    async def complete(
        self,
        run: FakeModelRun,
        output_summary: dict[str, object],
        http_status: int | None,
        provider_request_id: str | None,
        latency_ms: int | None,
    ) -> FakeModelRun:
        self.completed.append((run.id, output_summary))
        return run

    async def fail(
        self,
        run: FakeModelRun,
        code: str,
        message: str,
        **kwargs: object,
    ) -> FakeModelRun:
        self.failed.append((run.id, code))
        return run


def test_native_viral_kit_validator_repairs_dropped_required_disclosure() -> None:
    workspace_id = uuid4()
    product = _product_snapshot(workspace_id)
    pattern = _pattern_snapshot(workspace_id)
    request = _create_request(product.product_id, [pattern.pattern_kit_version_id])
    matches = match_patterns(
        product_context=product.product_context,
        patterns=[pattern],
        request=request,
    )
    viral_kit = build_fixture_viral_kit(
        viral_kit_id=uuid4(),
        workspace_id=workspace_id,
        version=1,
        created_by=uuid4(),
        created_at=utc_now(),
        request=request,
        product=product,
        patterns=[pattern],
        pattern_matches=matches,
        model_run_id=uuid4(),
    )
    payload = viral_kit.model_dump(mode="json")
    payload["concepts"][0]["required_disclosures"] = []  # type: ignore[index]
    invalid = ViralKitV1.model_validate(payload)
    validator = _native_output_validator(
        viral_kit.id,
        workspace_id,
        1,
        uuid4(),
        utc_now(),
        request,
        product.model_dump(mode="json"),
        [pattern.pattern_kit_version_id],
        uuid4(),
    )

    validator(invalid)


def test_normalize_viral_kit_preserves_required_concept_guardrails() -> None:
    workspace_id = uuid4()
    created_by = uuid4()
    model_run_id = uuid4()
    created_at = utc_now()
    product = _product_snapshot(workspace_id)
    pattern = _pattern_snapshot(workspace_id)
    request = _create_request(product.product_id, [pattern.pattern_kit_version_id])
    matches = match_patterns(
        product_context=product.product_context,
        patterns=[pattern],
        request=request,
    )
    viral_kit = build_fixture_viral_kit(
        viral_kit_id=uuid4(),
        workspace_id=workspace_id,
        version=1,
        created_by=created_by,
        created_at=created_at,
        request=request,
        product=product,
        patterns=[pattern],
        pattern_matches=matches,
        model_run_id=model_run_id,
    )
    payload = viral_kit.model_dump(mode="json")
    for concept in payload["concepts"]:
        concept["claims_to_avoid"] = []
        concept["required_disclosures"] = []

    normalized = normalize_viral_kit_output(
        payload,
        viral_kit_id=viral_kit.id,
        workspace_id=workspace_id,
        version=1,
        created_by=created_by,
        created_at=created_at,
        request=request,
        product_snapshot=product.model_dump(mode="json"),
        pattern_version_ids=[pattern.pattern_kit_version_id],
        model_run_id=model_run_id,
    )

    assert all("cure acne" in concept.claims_to_avoid for concept in normalized.concepts)
    assert all("#ad" in concept.required_disclosures for concept in normalized.concepts)


def test_normalize_viral_kit_separates_buyer_and_creator_persona() -> None:
    workspace_id = uuid4()
    created_by = uuid4()
    model_run_id = uuid4()
    created_at = utc_now()
    product = _product_snapshot(workspace_id)
    pattern = _pattern_snapshot(workspace_id)
    request = _create_request(product.product_id, [pattern.pattern_kit_version_id])
    matches = match_patterns(
        product_context=product.product_context,
        patterns=[pattern],
        request=request,
    )
    viral_kit = build_fixture_viral_kit(
        viral_kit_id=uuid4(),
        workspace_id=workspace_id,
        version=1,
        created_by=created_by,
        created_at=created_at,
        request=request,
        product=product,
        patterns=[pattern],
        pattern_matches=matches,
        model_run_id=model_run_id,
    )
    payload = viral_kit.model_dump(mode="json")
    for concept in payload["concepts"]:
        concept["creator_persona"] = concept["buyer_persona_label"]

    normalized = normalize_viral_kit_output(
        payload,
        viral_kit_id=viral_kit.id,
        workspace_id=workspace_id,
        version=1,
        created_by=created_by,
        created_at=created_at,
        request=request,
        product_snapshot=product.model_dump(mode="json"),
        pattern_version_ids=[pattern.pattern_kit_version_id],
        model_run_id=model_run_id,
    )

    assert all(
        concept.creator_persona.casefold() != concept.buyer_persona_label.casefold()
        for concept in normalized.concepts
    )


class FakeProductQueries:
    def __init__(self, product: ProductContextSnapshot | None) -> None:
        self.product = product

    async def get_product_context_snapshot(
        self,
        workspace_id: UUID,
        product_id: UUID,
    ) -> ProductContextSnapshot | None:
        if self.product is None:
            return None
        if self.product.workspace_id == workspace_id and self.product.product_id == product_id:
            return self.product
        return None


class FakePatternQueries:
    def __init__(self, patterns: dict[UUID, PatternKitVersionSnapshot]) -> None:
        self.patterns = patterns

    async def get_version_snapshot_by_id(
        self,
        workspace_id: UUID,
        pattern_kit_version_id: UUID,
    ) -> PatternKitVersionSnapshot:
        pattern = self.patterns[pattern_kit_version_id]
        assert pattern.workspace_id == workspace_id
        return pattern


class FakeViralKitRepository:
    def __init__(self) -> None:
        self.kit: ViralKitModel | None = None
        self.version: ViralKitVersionModel | None = None
        self.actions: list[ViralKitConceptActionModel] = []
        self.campaign_pack_links: list[tuple[UUID, str, UUID, UUID]] = []
        self.versions: list[ViralKitVersionModel] = []

    async def create_with_version(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        viral_kit: ViralKitV1,
    ) -> tuple[ViralKitModel, ViralKitVersionModel]:
        now = utc_now()
        self.kit = ViralKitModel(
            id=viral_kit.id,
            workspace_id=workspace_id,
            product_id=viral_kit.product.product_id,
            name=viral_kit.name,
            objective=viral_kit.objective,
            platform=viral_kit.platform,
            target_market=viral_kit.target_market,
            status=viral_kit.status,
            latest_version=viral_kit.version,
            selected_concept_id=viral_kit.selected_concept_id,
            created_by_user_id=user_id,
            created_at=now,
            updated_at=now,
            archived_at=None,
        )
        self.version = ViralKitVersionModel(
            id=uuid4(),
            viral_kit_id=viral_kit.id,
            workspace_id=workspace_id,
            version=viral_kit.version,
            parent_version=None,
            change_reason=None,
            schema_version=viral_kit.schema_version,
            product_context_version=viral_kit.product.product_context_version,
            product_snapshot_json=viral_kit.product.snapshot_json.model_dump(mode="json"),
            viral_kit_json=viral_kit.model_dump(mode="json"),
            model_run_id=viral_kit.provenance.model_run_id,
            created_by_user_id=user_id,
            created_at=now,
        )
        self.versions.append(self.version)
        return self.kit, self.version

    async def get_kit(self, workspace_id: UUID, viral_kit_id: UUID) -> ViralKitModel | None:
        if self.kit is None:
            return None
        if self.kit.workspace_id == workspace_id and self.kit.id == viral_kit_id:
            return self.kit
        return None

    async def get_latest_version(
        self,
        workspace_id: UUID,
        viral_kit_id: UUID,
    ) -> ViralKitVersionModel | None:
        if self.version is None:
            return None
        if self.version.workspace_id == workspace_id and self.version.viral_kit_id == viral_kit_id:
            return self.version
        return None

    async def record_concept_action(
        self,
        *,
        kit: ViralKitModel,
        concept_id: str,
        action: str,
        reason: str | None,
        actor_user_id: UUID,
    ) -> ViralKitConceptActionModel:
        if action == "selected":
            kit.selected_concept_id = concept_id
            kit.status = "concept_selected"
        row = ViralKitConceptActionModel(
            id=uuid4(),
            workspace_id=kit.workspace_id,
            viral_kit_id=kit.id,
            viral_kit_version=kit.latest_version,
            concept_id=concept_id,
            action=action,
            reason=reason,
            actor_user_id=actor_user_id,
            created_at=utc_now(),
        )
        self.actions.append(row)
        return row

    async def create_version(
        self,
        *,
        kit: ViralKitModel,
        user_id: UUID,
        viral_kit: ViralKitV1,
        parent_version: int,
        change_reason: str,
    ) -> ViralKitVersionModel:
        now = utc_now()
        kit.latest_version = parent_version + 1
        kit.status = viral_kit.status
        self.version = ViralKitVersionModel(
            id=uuid4(),
            viral_kit_id=kit.id,
            workspace_id=kit.workspace_id,
            version=viral_kit.version,
            parent_version=parent_version,
            change_reason=change_reason,
            schema_version=viral_kit.schema_version,
            product_context_version=viral_kit.product.product_context_version,
            product_snapshot_json=viral_kit.product.snapshot_json.model_dump(mode="json"),
            viral_kit_json=viral_kit.model_dump(mode="json"),
            model_run_id=viral_kit.provenance.model_run_id,
            created_by_user_id=user_id,
            created_at=now,
        )
        self.versions.append(self.version)
        return self.version

    async def record_campaign_pack_link(
        self,
        *,
        workspace_id: UUID,
        viral_kit_version_id: UUID,
        concept_id: str,
        campaign_pack_id: UUID,
        campaign_pack_version_id: UUID,
    ) -> None:
        self.campaign_pack_links.append(
            (viral_kit_version_id, concept_id, campaign_pack_id, campaign_pack_version_id)
        )


class FakeProductEventPublisher:
    def __init__(self, session: FakeSession) -> None:
        self.session = session
        self.records: list[dict[str, object]] = []

    async def record(self, **kwargs: object) -> None:
        self.records.append(kwargs)


class FakeCampaignPackCreator:
    def __init__(self) -> None:
        self.brief: CampaignPackBriefV1 | None = None

    async def create_from_brief(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        product_id: UUID,
        brief: CampaignPackBriefV1,
        source_model_run_id: UUID | None,
        source_prompt_version: str | None,
        source_schema_version: str | None,
    ) -> CampaignPackCreationResult:
        self.brief = brief
        pack_id = uuid4()
        version_id = uuid4()
        version = CampaignPackVersionResponse(
            id=version_id,
            campaign_pack_id=pack_id,
            version_number=1,
            brief_json=brief,
            brief_schema_version=brief.schema_version,
            product_snapshot_json=brief.product_snapshot,
            compiled_requirements_json=CompiledRequirementsSnapshotV2(requirements=[]),
            requirements_schema_version="compiled_requirements_v2",
            change_note="Initial generated brief",
            source_adaptation_run_id=None,
            source_model_run_id=source_model_run_id,
            source_prompt_version=source_prompt_version,
            source_schema_version=source_schema_version,
            created_at=utc_now(),
        )
        return CampaignPackCreationResult(
            campaign_pack_id=pack_id,
            campaign_pack_version_id=version_id,
            compiled_requirements_schema_version="compiled_requirements_v2",
            response=CampaignPackResponse(
                id=pack_id,
                workspace_id=workspace_id,
                product_id=product_id,
                adaptation_run_id=None,
                status="draft",
                current_version_id=version_id,
                created_at=utc_now(),
                updated_at=utc_now(),
                current_version=version,
            ),
        )


def setup_function() -> None:
    FakeAiModelRunRepository.created = []
    FakeAiModelRunRepository.completed = []
    FakeAiModelRunRepository.failed = []


def test_viral_kit_request_rejects_duplicate_pattern_versions() -> None:
    pattern_id = uuid4()

    with pytest.raises(ValidationError):
        CreateViralKitRequest(
            product_id=uuid4(),
            expected_product_context_version=1,
            pattern_kit_version_ids=[pattern_id, pattern_id],
            objective="tiktok_shop_affiliate_test",
            platform="tiktok_shop",
            target_market="US",
        )


def test_viral_kit_request_requires_exactly_three_concepts() -> None:
    with pytest.raises(ValidationError, match="exactly three"):
        CreateViralKitRequest(
            product_id=uuid4(),
            expected_product_context_version=1,
            pattern_kit_version_ids=[uuid4()],
            objective="tiktok_shop_affiliate_test",
            platform="tiktok_shop",
            target_market="US",
            concept_count=2,
        )


def test_fixture_viral_kit_is_product_grounded_and_diverse() -> None:
    workspace_id = uuid4()
    product = _product_snapshot(workspace_id)
    pattern = _pattern_snapshot(workspace_id)
    request = _create_request(product.product_id, [pattern.pattern_kit_version_id])
    matches = match_patterns(
        product_context=product.product_context,
        patterns=[pattern],
        request=request,
    )

    viral_kit = build_fixture_viral_kit(
        viral_kit_id=uuid4(),
        workspace_id=workspace_id,
        version=1,
        created_by=uuid4(),
        created_at=utc_now(),
        request=request,
        product=product,
        patterns=[pattern],
        pattern_matches=matches,
        model_run_id=uuid4(),
    )
    payload = viral_kit.model_dump(mode="json")

    assert matches[0].applicability_status == "matched"
    assert len(viral_kit.concepts) == 3
    assert viral_kit.product.product_context_version == 3
    assert {concept.strategic_axis for concept in viral_kit.concepts} == {
        "result_first",
        "problem_first",
        "proof_first",
    }
    assert all(
        concept.buyer_persona_label != concept.creator_persona for concept in viral_kit.concepts
    )
    assert all("cure acne" in concept.claims_to_avoid for concept in viral_kit.concepts)
    assert all("#ad" in concept.required_disclosures for concept in viral_kit.concepts)
    assert "guarantee" not in str(payload).lower()


def test_hard_category_conflict_requires_documented_override() -> None:
    workspace_id = uuid4()
    product = _product_snapshot(workspace_id)
    pattern = _pattern_snapshot(workspace_id)
    applicability = pattern.pattern.applicability.model_copy(
        update={
            "suitable_categories": [],
            "unsuitable_categories": [product.product_context.identity.category],
            "platforms": [],
            "markets": [],
            "objectives": [],
        }
    )
    conflicting_pattern = PatternKitVersionSnapshot(
        pattern_kit_id=pattern.pattern_kit_id,
        pattern_kit_version_id=pattern.pattern_kit_version_id,
        workspace_id=pattern.workspace_id,
        version=pattern.version,
        status=pattern.status,
        pattern=pattern.pattern.model_copy(update={"applicability": applicability}),
    )

    rejected = match_patterns(
        product_context=product.product_context,
        patterns=[conflicting_pattern],
        request=_create_request(
            product.product_id,
            [pattern.pattern_kit_version_id],
        ),
    )[0]
    overridden = match_patterns(
        product_context=product.product_context,
        patterns=[conflicting_pattern],
        request=_create_request(
            product.product_id,
            [pattern.pattern_kit_version_id],
        ).model_copy(update={"applicability_override_reason": "Human cross-category test."}),
    )[0]

    assert rejected.applicability_status == "rejected"
    assert overridden.applicability_status == "override"
    assert rejected.conflicts


def test_viral_kit_contract_rejects_near_duplicate_concepts() -> None:
    workspace_id = uuid4()
    product = _product_snapshot(workspace_id)
    pattern = _pattern_snapshot(workspace_id)
    request = _create_request(product.product_id, [pattern.pattern_kit_version_id])
    matches = match_patterns(
        product_context=product.product_context,
        patterns=[pattern],
        request=request,
    )
    viral_kit = build_fixture_viral_kit(
        viral_kit_id=uuid4(),
        workspace_id=workspace_id,
        version=1,
        created_by=uuid4(),
        created_at=utc_now(),
        request=request,
        product=product,
        patterns=[pattern],
        pattern_matches=matches,
        model_run_id=uuid4(),
    )
    payload = viral_kit.model_dump(mode="json")
    payload["concepts"][1] = payload["concepts"][0]
    payload["concepts"][1]["id"] = "concept_2"

    with pytest.raises(ValidationError):
        ViralKitV1.model_validate(payload)


@pytest.mark.asyncio
async def test_viral_kit_service_rejects_product_version_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.viral_kits.service as service_module

    workspace_id = uuid4()
    product = _product_snapshot(workspace_id)
    pattern = _pattern_snapshot(workspace_id)
    monkeypatch.setattr(service_module, "ProductQueries", lambda _: FakeProductQueries(product))
    monkeypatch.setattr(
        service_module,
        "PatternKitQueries",
        lambda _: FakePatternQueries({pattern.pattern_kit_version_id: pattern}),
    )

    with pytest.raises(ConflictError, match="VIRAL_KIT_PRODUCT_VERSION_CONFLICT"):
        await ViralKitService(
            cast(AsyncSession, FakeSession()),
            Settings(ai_mode="fixture"),
        ).create(
            workspace_id=workspace_id,
            user_id=uuid4(),
            data=_create_request(
                product.product_id,
                [pattern.pattern_kit_version_id],
                expected_version=2,
            ),
        )


@pytest.mark.asyncio
async def test_viral_kit_service_persists_fixture_and_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.viral_kits.service as service_module

    workspace_id = uuid4()
    product = _product_snapshot(workspace_id)
    pattern = _pattern_snapshot(workspace_id)
    repository = FakeViralKitRepository()
    events = FakeProductEventPublisher(FakeSession())
    monkeypatch.setattr(service_module, "ViralKitRepository", lambda _: repository)
    monkeypatch.setattr(service_module, "ProductQueries", lambda _: FakeProductQueries(product))
    monkeypatch.setattr(
        service_module,
        "PatternKitQueries",
        lambda _: FakePatternQueries({pattern.pattern_kit_version_id: pattern}),
    )
    monkeypatch.setattr(service_module, "AiModelRunRepository", FakeAiModelRunRepository)
    monkeypatch.setattr(service_module, "ProductEventPublisher", lambda _: events)

    detail = await ViralKitService(
        cast(AsyncSession, FakeSession()),
        Settings(ai_mode="fixture"),
    ).create(
        workspace_id=workspace_id,
        user_id=uuid4(),
        data=_create_request(product.product_id, [pattern.pattern_kit_version_id]),
    )

    assert detail.kit.status == "ready_for_review"
    assert len(detail.latest_version.viral_kit.concepts) == 3
    assert repository.version is not None
    assert repository.version.product_context_version == 3
    assert FakeAiModelRunRepository.completed
    assert events.records[0]["event_type"] == "viral_kit_created"


@pytest.mark.asyncio
async def test_user_viral_kit_version_is_append_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.viral_kits.service as service_module

    workspace_id = uuid4()
    user_id = uuid4()
    repository, viral_kit = await _seed_repository(workspace_id, user_id)
    original_payload = copy.deepcopy(repository.versions[0].viral_kit_json)
    original_snapshot = copy.deepcopy(repository.versions[0].product_snapshot_json)
    edited = viral_kit.model_copy(update={"name": "Human-refined ViralKit"})
    events = FakeProductEventPublisher(FakeSession())
    monkeypatch.setattr(service_module, "ViralKitRepository", lambda _: repository)
    monkeypatch.setattr(service_module, "ProductEventPublisher", lambda _: events)

    created = await ViralKitService(
        cast(AsyncSession, FakeSession()),
        Settings(ai_mode="fixture"),
    ).create_version(
        workspace_id=workspace_id,
        viral_kit_id=viral_kit.id,
        user_id=user_id,
        data=CreateViralKitVersionRequest(
            change_reason="Clarify the test strategy.",
            viral_kit=edited,
        ),
    )

    assert created.version == 2
    assert created.parent_version == 1
    assert created.change_reason == "Clarify the test strategy."
    assert created.viral_kit.name == "Human-refined ViralKit"
    assert repository.versions[0].viral_kit_json == original_payload
    assert repository.versions[0].product_snapshot_json == original_snapshot
    assert events.records[0]["event_type"] == "viral_kit_version_created"


@pytest.mark.asyncio
async def test_user_viral_kit_version_cannot_weaken_governance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.viral_kits.service as service_module

    workspace_id = uuid4()
    user_id = uuid4()
    repository, viral_kit = await _seed_repository(workspace_id, user_id)
    concepts = list(viral_kit.concepts)
    concepts[0] = concepts[0].model_copy(update={"claims_to_avoid": []})
    weakened = viral_kit.model_copy(update={"concepts": concepts})
    monkeypatch.setattr(service_module, "ViralKitRepository", lambda _: repository)

    with pytest.raises(AppError, match="VIRAL_KIT_GOVERNANCE_CONFLICT"):
        await ViralKitService(
            cast(AsyncSession, FakeSession()),
            Settings(ai_mode="fixture"),
        ).create_version(
            workspace_id=workspace_id,
            viral_kit_id=viral_kit.id,
            user_id=user_id,
            data=CreateViralKitVersionRequest(
                change_reason="Unsafe governance edit.",
                viral_kit=weakened,
            ),
        )


@pytest.mark.asyncio
async def test_user_viral_kit_version_cannot_replace_governance_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.viral_kits.service as service_module

    workspace_id = uuid4()
    user_id = uuid4()
    repository, viral_kit = await _seed_repository(workspace_id, user_id)
    weakened_constraints = viral_kit.constraints.model_copy(
        update={
            "governance": viral_kit.constraints.governance.model_copy(
                update={"prohibited_claims": [], "required_disclosures": []}
            )
        }
    )
    weakened = viral_kit.model_copy(update={"constraints": weakened_constraints})
    monkeypatch.setattr(service_module, "ViralKitRepository", lambda _: repository)

    with pytest.raises(AppError, match="VIRAL_KIT_GOVERNANCE_CONFLICT"):
        await ViralKitService(
            cast(AsyncSession, FakeSession()),
            Settings(ai_mode="fixture"),
        ).create_version(
            workspace_id=workspace_id,
            viral_kit_id=viral_kit.id,
            user_id=user_id,
            data=CreateViralKitVersionRequest(
                change_reason="Remove product governance.",
                viral_kit=weakened,
            ),
        )


@pytest.mark.asyncio
async def test_user_viral_kit_version_cannot_tamper_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.viral_kits.service as service_module

    workspace_id = uuid4()
    user_id = uuid4()
    repository, viral_kit = await _seed_repository(workspace_id, user_id)
    tampered = viral_kit.model_copy(
        update={
            "provenance": viral_kit.provenance.model_copy(
                update={
                    "pattern_kit_version_ids": [uuid4()],
                    "model_run_id": uuid4(),
                    "prompt_version": "spoofed_prompt",
                }
            )
        }
    )
    monkeypatch.setattr(service_module, "ViralKitRepository", lambda _: repository)

    with pytest.raises(AppError, match="VIRAL_KIT_PROVENANCE_CONFLICT"):
        await ViralKitService(
            cast(AsyncSession, FakeSession()),
            Settings(ai_mode="fixture"),
        ).create_version(
            workspace_id=workspace_id,
            viral_kit_id=viral_kit.id,
            user_id=user_id,
            data=CreateViralKitVersionRequest(
                change_reason="Spoof source lineage.",
                viral_kit=tampered,
            ),
        )


@pytest.mark.asyncio
async def test_user_viral_kit_version_cannot_replace_product_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.viral_kits.service as service_module

    workspace_id = uuid4()
    user_id = uuid4()
    repository, viral_kit = await _seed_repository(workspace_id, user_id)
    tampered = viral_kit.model_copy(
        update={"product": viral_kit.product.model_copy(update={"product_context_version": 999})}
    )
    monkeypatch.setattr(service_module, "ViralKitRepository", lambda _: repository)

    with pytest.raises(AppError, match="VIRAL_KIT_PRODUCT_SNAPSHOT_CONFLICT"):
        await ViralKitService(
            cast(AsyncSession, FakeSession()),
            Settings(ai_mode="fixture"),
        ).create_version(
            workspace_id=workspace_id,
            viral_kit_id=viral_kit.id,
            user_id=user_id,
            data=CreateViralKitVersionRequest(
                change_reason="Replace locked product snapshot.",
                viral_kit=tampered,
            ),
        )


@pytest.mark.asyncio
async def test_viral_kit_concept_selection_is_append_only_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.viral_kits.service as service_module

    workspace_id = uuid4()
    user_id = uuid4()
    repository, viral_kit = await _seed_repository(workspace_id, user_id)
    events = FakeProductEventPublisher(FakeSession())
    monkeypatch.setattr(service_module, "ViralKitRepository", lambda _: repository)
    monkeypatch.setattr(service_module, "ProductEventPublisher", lambda _: events)

    action = await ViralKitService(
        cast(AsyncSession, FakeSession()),
        Settings(ai_mode="fixture"),
    ).record_concept_action(
        workspace_id=workspace_id,
        viral_kit_id=viral_kit.id,
        user_id=user_id,
        data=ViralKitConceptActionRequest(
            concept_id="concept_1",
            action="selected",
            reason="Best fit for first creator batch.",
        ),
    )

    assert action.action == "selected"
    assert repository.kit is not None
    assert repository.kit.selected_concept_id == "concept_1"
    assert events.records[0]["event_type"] == "concept_selected"


@pytest.mark.asyncio
async def test_viral_kit_campaign_pack_creation_links_exact_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.viral_kits.service as service_module

    workspace_id = uuid4()
    user_id = uuid4()
    repository, viral_kit = await _seed_repository(workspace_id, user_id)
    creator = FakeCampaignPackCreator()
    events = FakeProductEventPublisher(FakeSession())
    monkeypatch.setattr(service_module, "ViralKitRepository", lambda _: repository)
    monkeypatch.setattr(service_module, "CampaignPackCreator", lambda _: creator)
    monkeypatch.setattr(service_module, "ProductEventPublisher", lambda _: events)

    result = await ViralKitService(
        cast(AsyncSession, FakeSession()),
        Settings(ai_mode="fixture"),
    ).create_campaign_pack_from_concept(
        workspace_id=workspace_id,
        viral_kit_id=viral_kit.id,
        user_id=user_id,
        concept_id="concept_1",
        data=CreateViralKitCampaignPackRequest(rights_note="Use internal creator."),
    )

    assert result.concept_id == "concept_1"
    assert repository.campaign_pack_links[0][0] == repository.version.id
    assert repository.actions[-1].action == "campaign_pack_created"
    assert creator.brief is not None
    assert creator.brief.source_viral_kit_id == viral_kit.id
    assert events.records[0]["event_type"] == "campaign_pack_created"


def _create_request(
    product_id: UUID,
    pattern_ids: list[UUID],
    expected_version: int = 3,
) -> CreateViralKitRequest:
    return CreateViralKitRequest(
        product_id=product_id,
        expected_product_context_version=expected_version,
        pattern_kit_version_ids=pattern_ids,
        objective="tiktok_shop_affiliate_test",
        platform="tiktok_shop",
        target_market="US",
        buyer_persona_id="busy_parent",
        commercial_constraints=CommercialConstraintsV1(product_tag_required=True),
        concept_count=3,
    )


def _product_snapshot(workspace_id: UUID) -> ProductContextSnapshot:
    product_id = uuid4()
    context = ProductContextV1(
        identity=ProductIdentityV1(
            name="Counter Shelf",
            category="home_organization",
            market="US",
            currency="USD",
        ),
        personas=[
            BuyerPersonaV1(
                id="busy_parent",
                label="busy parent",
                pain_points=["messy counter"],
                desired_outcomes=["clear counter space"],
                awareness_stage="problem_aware",
            )
        ],
        benefits=[
            ProductBenefitV1(
                id="space",
                label="more counter space",
                description="Keeps small items organized.",
                proof_available=["before and after view"],
                claim_strength="observed",
            )
        ],
        features=[
            ProductFeatureV1(
                id="stacked",
                label="stacked storage",
                visual_demo_possible=True,
                visual_cues=["counter before and after"],
            )
        ],
        creative=CreativeContextV1(
            primary_angles=["counter reset"],
            demonstration_mechanisms=["show clutter before, install shelf, show organized result"],
            available_proof=["before and after view"],
            creator_personas=["home organizer"],
            preferred_delivery_styles=["authentic_review"],
        ),
        governance=ProductGovernanceV1(
            claims=[
                ClaimRuleV1(
                    id="claim_1",
                    text="cure acne",
                    rule_type="prohibited",
                    severity="critical",
                )
            ],
            required_disclosures=["#ad"],
        ),
    )
    return ProductContextSnapshot(
        product_id=product_id,
        workspace_id=workspace_id,
        context_schema_version=context.schema_version,
        product_context_version=3,
        product_context=context,
    )


def _pattern_snapshot(workspace_id: UUID) -> PatternKitVersionSnapshot:
    asset_version_id = uuid4()
    evidence = [
        FakeEvidence(
            "hook_signal",
            {
                "hook_type": "problem_first",
                "spoken_text": "My counter was always a mess before this setup.",
                "overlay_text": "Counter reset",
                "visual_description": "messy counter shown first",
                "buyer_pain": "messy counter",
                "clarity": "clear",
                "confidence": 0.91,
            },
            asset_version_id=asset_version_id,
            start_ms=0,
            end_ms=1500,
        ),
        FakeEvidence(
            "product_visibility_summary",
            {
                "first_appearance_ms": 900,
                "total_visible_ms": 5200,
                "screen_time_ratio": 0.4,
                "clear_close_up_present": True,
                "usage_present": True,
            },
            asset_version_id=asset_version_id,
            source="derived",
        ),
        FakeEvidence(
            "demo_summary",
            {
                "detected": True,
                "demo_type": "before_after",
                "before_state_visible": True,
                "after_state_visible": True,
                "mechanism_clarity": "clear",
                "continuity": "continuous",
                "confidence": 0.89,
            },
            asset_version_id=asset_version_id,
        ),
    ]
    dna = _build_creative_dna(_evidence_by_type(cast(list[EvidenceItemModel], evidence)))
    source = PatternSourceInput(
        creative_dna_version_id=uuid4(),
        asset_version_id=asset_version_id,
        taxonomy_version="creative_dna_taxonomy_v1",
        dna=CreativeDnaV1.model_validate(dna.model_dump(mode="json")),
        evidence_by_id={
            item.id: PatternEvidenceInput(
                id=item.id,
                asset_version_id=item.asset_version_id,
                evidence_type=item.evidence_type,
                source=item.source,
                start_ms=item.start_ms,
                end_ms=item.end_ms,
                value_json=item.value_json,
                confidence=item.confidence,
            )
            for item in evidence
        },
    )
    pattern = build_fixture_pattern_kit(
        pattern_kit_id=uuid4(),
        workspace_id=workspace_id,
        version=1,
        created_by=uuid4(),
        created_at=utc_now(),
        request=CreatePatternKitRequest(
            name="Problem fast reveal transformation",
            kind="single_asset_abstraction",
            scope="workspace_private",
            source_creative_dna_version_ids=[source.creative_dna_version_id],
            primary_category="home_organization",
            target_platforms=["tiktok_shop"],
            target_markets=["US"],
            objectives=["tiktok_shop_affiliate_test"],
            extraction_mode="ai_assisted",
        ),
        sources=[source],
        model_run_id=uuid4(),
    )
    return PatternKitVersionSnapshot(
        pattern_kit_id=pattern.id,
        pattern_kit_version_id=uuid4(),
        workspace_id=workspace_id,
        version=1,
        status="reviewed",
        pattern=pattern,
    )


async def _seed_repository(
    workspace_id: UUID,
    user_id: UUID,
) -> tuple[FakeViralKitRepository, ViralKitV1]:
    product = _product_snapshot(workspace_id)
    pattern = _pattern_snapshot(workspace_id)
    request = _create_request(product.product_id, [pattern.pattern_kit_version_id])
    matches = match_patterns(
        product_context=product.product_context,
        patterns=[pattern],
        request=request,
    )
    viral_kit = build_fixture_viral_kit(
        viral_kit_id=uuid4(),
        workspace_id=workspace_id,
        version=1,
        created_by=user_id,
        created_at=utc_now(),
        request=request,
        product=product,
        patterns=[pattern],
        pattern_matches=matches,
        model_run_id=uuid4(),
    )
    repository = FakeViralKitRepository()
    await repository.create_with_version(
        workspace_id=workspace_id,
        user_id=user_id,
        viral_kit=viral_kit,
    )
    return repository, viral_kit
