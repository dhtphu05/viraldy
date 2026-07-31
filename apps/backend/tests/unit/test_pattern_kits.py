from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import date
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from openai.lib._pydantic import to_strict_json_schema
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.ai_gateway.public import StructuredOutputValidationError
from viraldy.modules.creative_dna.contracts import CreativeDnaV1
from viraldy.modules.creative_dna.models import CreativeDnaVersionModel
from viraldy.modules.creative_dna.service import _build_creative_dna, _evidence_by_type
from viraldy.modules.feedback.models import FeedbackItemModel
from viraldy.modules.feedback.public import FieldFeedbackV1
from viraldy.modules.media_analysis.public import EvidenceItemModel
from viraldy.modules.pattern_kits.contracts import (
    PatternEvidenceRefV1,
    PatternKitV1,
    PatternMetricSummaryV1,
    PatternPerformanceSummaryV1,
)
from viraldy.modules.pattern_kits.models import (
    PatternKitActionModel,
    PatternKitModel,
    PatternKitVersionModel,
)
from viraldy.modules.pattern_kits.performance import validate_supported_performance
from viraldy.modules.pattern_kits.provider import (
    PatternEvidenceInput,
    PatternSourceInput,
    _native_output_validator,
    build_fixture_pattern_kit,
)
from viraldy.modules.pattern_kits.schemas import (
    CreatePatternKitFeedbackRequest,
    CreatePatternKitRequest,
    CreatePatternKitVersionRequest,
    PatternKitActionRequest,
)
from viraldy.modules.pattern_kits.service import PatternKitService, _source_payloads
from viraldy.platform.clock.utc import utc_now
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError, ConflictError


def test_pattern_kit_openai_schema_uses_items_for_reveal_window() -> None:
    schema = to_strict_json_schema(PatternKitV1)

    reveal_window = schema["$defs"]["ProductRevealPatternV1"]["properties"][
        "first_appearance_window_ms"
    ]

    assert reveal_window["type"] == "array"
    assert reveal_window["minItems"] == 2
    assert reveal_window["maxItems"] == 2
    assert reveal_window["items"]["anyOf"] == [
        {"type": "integer"},
        {"type": "null"},
    ]
    assert "prefixItems" not in reveal_window


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


def test_native_pattern_validator_rejects_evidence_outside_catalog() -> None:
    workspace_id = uuid4()
    dna, evidence = _dna_model(workspace_id)
    source = _source_input(dna, evidence)
    request = _create_request([dna.id], kind="single_asset_abstraction")
    pattern = build_fixture_pattern_kit(
        pattern_kit_id=uuid4(),
        workspace_id=workspace_id,
        version=1,
        created_by=uuid4(),
        created_at=utc_now(),
        request=request,
        sources=[source],
        model_run_id=uuid4(),
    )
    payload = pattern.model_dump(mode="json")
    payload["opening"]["evidence_refs"][0]["evidence_id"] = str(uuid4())  # type: ignore[index]
    invalid = PatternKitV1.model_validate(payload)
    validator = _native_output_validator(
        pattern.id,
        workspace_id,
        1,
        request,
        _source_payloads([source]),
    )

    with pytest.raises(ValueError, match="outside the request"):
        validator(invalid)


def test_native_pattern_validator_returns_a_safe_repair_reason() -> None:
    workspace_id = uuid4()
    dna, evidence = _dna_model(workspace_id)
    source = _source_input(dna, evidence)
    request = _create_request([dna.id], kind="single_asset_abstraction")
    pattern = build_fixture_pattern_kit(
        pattern_kit_id=uuid4(),
        workspace_id=workspace_id,
        version=1,
        created_by=uuid4(),
        created_at=utc_now(),
        request=request,
        sources=[source],
        model_run_id=uuid4(),
    )
    invalid = pattern.model_copy(update={"status": "reviewed"})
    validator = _native_output_validator(
        pattern.id,
        workspace_id,
        1,
        request,
        _source_payloads([source]),
    )

    with pytest.raises(StructuredOutputValidationError) as exc_info:
        validator(invalid)

    assert exc_info.value.issue.summary == "New PatternKits must start as candidate."


def test_pattern_source_payload_catalogs_exact_paths_by_evidence_id() -> None:
    workspace_id = uuid4()
    dna, evidence = _dna_model(workspace_id)

    payload = _source_payloads([_source_input(dna, evidence)])[0]
    feature_paths = cast(dict[str, list[str]], payload["evidence_feature_paths"])

    assert "opening.primary_hook_type" in feature_paths[str(evidence[0].id)]
    assert "product.first_appearance_ms" in feature_paths[str(evidence[1].id)]
    assert "demo.demo_type" in feature_paths[str(evidence[2].id)]


class FakeCreativeDnaRepository:
    def __init__(self, models: dict[UUID, CreativeDnaVersionModel]) -> None:
        self.models = models

    async def get(
        self,
        workspace_id: UUID,
        dna_version_id: UUID,
    ) -> CreativeDnaVersionModel | None:
        model = self.models.get(dna_version_id)
        if model is None or model.workspace_id != workspace_id:
            return None
        return model


class FakeEvidenceQueries:
    def __init__(self, evidence_by_asset_version: dict[UUID, list[FakeEvidence]]) -> None:
        self.evidence_by_asset_version = evidence_by_asset_version

    async def list_for_asset_version(
        self,
        workspace_id: UUID,
        asset_version_id: UUID,
    ) -> list[EvidenceItemModel]:
        return cast(list[EvidenceItemModel], self.evidence_by_asset_version[asset_version_id])


class FakePatternKitRepository:
    def __init__(self) -> None:
        self.kit: PatternKitModel | None = None
        self.version: PatternKitVersionModel | None = None
        self.source_rows: list[tuple[UUID, UUID]] = []
        self.evidence_links: list[tuple[UUID, str]] = []
        self.actions: list[PatternKitActionModel] = []
        self.versions: list[PatternKitVersionModel] = []

    async def create_kit_with_version(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        pattern: PatternKitV1,
        source_rows: list[tuple[UUID, UUID]],
        evidence_links: list[tuple[UUID, str]],
    ) -> tuple[PatternKitModel, PatternKitVersionModel]:
        self.source_rows = source_rows
        self.evidence_links = evidence_links
        now = utc_now()
        self.kit = PatternKitModel(
            id=pattern.id,
            workspace_id=workspace_id,
            name=pattern.name,
            kind=pattern.kind,
            scope=pattern.scope,
            status=pattern.status,
            primary_category=pattern.applicability.suitable_categories[0],
            target_platforms_json=list(pattern.applicability.platforms),
            target_markets_json=list(pattern.applicability.markets),
            objectives_json=list(pattern.applicability.objectives),
            latest_version=pattern.version,
            created_by_user_id=user_id,
            created_at=now,
            updated_at=now,
            archived_at=None,
        )
        self.version = PatternKitVersionModel(
            id=uuid4(),
            pattern_kit_id=pattern.id,
            workspace_id=workspace_id,
            version=pattern.version,
            parent_version=None,
            change_reason=None,
            schema_version=pattern.schema_version,
            pattern_json=pattern.model_dump(mode="json"),
            overall_confidence=pattern.overall_confidence,
            model_run_id=pattern.provenance.model_run_id,
            created_by_user_id=user_id,
            created_at=now,
        )
        self.versions.append(self.version)
        return self.kit, self.version

    async def get_kit(self, workspace_id: UUID, pattern_kit_id: UUID) -> PatternKitModel | None:
        if self.kit is None:
            return None
        if self.kit.workspace_id == workspace_id and self.kit.id == pattern_kit_id:
            return self.kit
        return None

    async def get_latest_version(
        self,
        workspace_id: UUID,
        pattern_kit_id: UUID,
    ) -> PatternKitVersionModel | None:
        if self.version is None:
            return None
        if (
            self.version.workspace_id == workspace_id
            and self.version.pattern_kit_id == pattern_kit_id
        ):
            return self.version
        return None

    async def record_action(
        self,
        *,
        kit: PatternKitModel,
        version: int,
        action: str,
        reason: str | None,
        actor_user_id: UUID,
    ) -> PatternKitActionModel:
        kit.status = action if action != "restored" else "candidate"
        action_model = PatternKitActionModel(
            id=uuid4(),
            workspace_id=kit.workspace_id,
            pattern_kit_id=kit.id,
            version=version,
            action=action,
            reason=reason,
            actor_user_id=actor_user_id,
            created_at=utc_now(),
        )
        self.actions.append(action_model)
        return action_model

    async def create_version(
        self,
        *,
        kit: PatternKitModel,
        user_id: UUID,
        pattern: PatternKitV1,
        parent_version: int,
        change_reason: str,
        source_rows: list[tuple[UUID, UUID]],
        evidence_links: list[tuple[UUID, str]],
    ) -> PatternKitVersionModel:
        now = utc_now()
        kit.latest_version = parent_version + 1
        kit.status = pattern.status
        self.source_rows = source_rows
        self.evidence_links = evidence_links
        self.version = PatternKitVersionModel(
            id=uuid4(),
            pattern_kit_id=kit.id,
            workspace_id=kit.workspace_id,
            version=pattern.version,
            parent_version=parent_version,
            change_reason=change_reason,
            schema_version=pattern.schema_version,
            pattern_json=pattern.model_dump(mode="json"),
            overall_confidence=pattern.overall_confidence,
            model_run_id=pattern.provenance.model_run_id,
            created_by_user_id=user_id,
            created_at=now,
        )
        self.versions.append(self.version)
        return self.version


class FakeProductEventPublisher:
    def __init__(self, session: FakeSession) -> None:
        self.session = session
        self.records: list[dict[str, object]] = []

    async def record(self, **kwargs: object) -> None:
        self.records.append(kwargs)


class FakeFeedbackWriter:
    def __init__(self) -> None:
        self.feedback: FeedbackItemModel | None = None

    async def record(
        self,
        *,
        workspace_id: UUID,
        created_by_user_id: UUID,
        feedback: FieldFeedbackV1,
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
            created_at=utc_now(),
        )
        self.feedback = item
        return item


def setup_function() -> None:
    FakeAiModelRunRepository.created = []
    FakeAiModelRunRepository.completed = []
    FakeAiModelRunRepository.failed = []


def test_pattern_kit_request_rejects_duplicate_sources() -> None:
    source_id = uuid4()

    with pytest.raises(ValidationError):
        CreatePatternKitRequest(
            name="Problem fast reveal",
            kind="multi_asset_cluster",
            source_creative_dna_version_ids=[source_id, source_id],
            primary_category="home_organization",
            target_platforms=["tiktok_shop"],
            target_markets=["US"],
            objectives=["affiliate"],
        )


def test_fixture_pattern_kit_is_evidence_grounded_without_performance_claims() -> None:
    workspace_id = uuid4()
    user_id = uuid4()
    dna_model, evidence = _dna_model(workspace_id)
    source = _source_input(dna_model, evidence)
    pattern = build_fixture_pattern_kit(
        pattern_kit_id=uuid4(),
        workspace_id=workspace_id,
        version=1,
        created_by=user_id,
        created_at=utc_now(),
        request=_create_request([dna_model.id], kind="single_asset_abstraction"),
        sources=[source],
        model_run_id=uuid4(),
    )
    payload = pattern.model_dump(mode="json")

    assert pattern.source.creative_dna_version_ids == [dna_model.id]
    assert pattern.provenance.taxonomy_version == dna_model.taxonomy_version
    assert pattern.performance_summary.evidence_status == "none"
    assert pattern.opening.evidence_refs
    assert pattern.sequence[0].order == 1
    assert "winning" not in str(payload).lower()


def test_multi_source_conflict_is_retained_as_uncertainty() -> None:
    workspace_id = uuid4()
    dna_a, evidence_a = _dna_model(workspace_id)
    dna_b, evidence_b = _dna_model(workspace_id)
    dna_b.dna_json = copy.deepcopy(dna_b.dna_json)
    opening = cast(dict[str, object], dna_b.dna_json["opening"])
    primary_hook = cast(dict[str, object], opening["primary_hook_type"])
    primary_hook["value"] = "result_first"

    pattern = build_fixture_pattern_kit(
        pattern_kit_id=uuid4(),
        workspace_id=workspace_id,
        version=1,
        created_by=uuid4(),
        created_at=utc_now(),
        request=_create_request([dna_a.id, dna_b.id]),
        sources=[
            _source_input(dna_a, evidence_a),
            _source_input(dna_b, evidence_b),
        ],
        model_run_id=uuid4(),
    )

    assert any("opening.primary_hook_type" in uncertainty for uncertainty in pattern.uncertainties)


def test_pattern_kit_contract_rejects_non_contiguous_sequence() -> None:
    workspace_id = uuid4()
    dna_model, evidence = _dna_model(workspace_id)
    pattern = build_fixture_pattern_kit(
        pattern_kit_id=uuid4(),
        workspace_id=workspace_id,
        version=1,
        created_by=uuid4(),
        created_at=utc_now(),
        request=_create_request([dna_model.id], kind="single_asset_abstraction"),
        sources=[_source_input(dna_model, evidence)],
        model_run_id=uuid4(),
    )
    payload = pattern.model_dump(mode="json")
    payload["sequence"][0]["order"] = 2

    with pytest.raises(ValidationError):
        PatternKitV1.model_validate(payload)


def test_pattern_evidence_rejects_inverted_timing() -> None:
    with pytest.raises(ValidationError, match="end_ms"):
        PatternEvidenceRefV1(
            creative_dna_version_id=uuid4(),
            asset_version_id=uuid4(),
            evidence_id=uuid4(),
            feature_path="opening.hook_text",
            source_type="vision",
            start_ms=2000,
            end_ms=1000,
            observation_summary="Observed hook timing.",
            confidence=0.8,
        )


def test_performance_summary_rejects_directional_without_sample_caveat() -> None:
    with pytest.raises(ValidationError, match="sample-size caveat"):
        PatternPerformanceSummaryV1(
            evidence_status="directional",
            asset_count=2,
            campaign_count=1,
            date_range_start=date(2026, 1, 1),
            date_range_end=date(2026, 1, 31),
            metrics=[
                PatternMetricSummaryV1(
                    metric_name="hook_rate",
                    sample_size=2,
                    median=0.31,
                    source="workspace_campaign_export",
                )
            ],
            caveats=["Correlation does not establish causation."],
            confidence="low",
        )


def test_performance_summary_rejects_invalid_date_range() -> None:
    with pytest.raises(ValidationError, match="date range"):
        PatternPerformanceSummaryV1(
            evidence_status="directional",
            asset_count=2,
            campaign_count=1,
            date_range_start=date(2026, 2, 1),
            date_range_end=date(2026, 1, 1),
            metrics=[
                PatternMetricSummaryV1(
                    metric_name="hook_rate",
                    sample_size=2,
                    median=0.31,
                    source="workspace_campaign_export",
                )
            ],
            caveats=[
                "Small sample size; treat this result as directional.",
                "Correlation does not establish causation.",
            ],
            confidence="low",
        )


def test_supported_performance_uses_configured_minimum_samples() -> None:
    summary = PatternPerformanceSummaryV1(
        evidence_status="supported",
        asset_count=9,
        campaign_count=3,
        date_range_start=date(2026, 1, 1),
        date_range_end=date(2026, 1, 31),
        metrics=[
            PatternMetricSummaryV1(
                metric_name="hook_rate",
                sample_size=9,
                median=0.31,
                source="workspace_campaign_export",
            )
        ],
        caveats=["Observed correlation does not establish causation."],
        confidence="medium",
    )

    with pytest.raises(AppError, match="PATTERN_KIT_PERFORMANCE_UNSUPPORTED"):
        validate_supported_performance(
            summary,
            Settings(
                pattern_performance_supported_min_asset_count=10,
                pattern_performance_supported_min_campaign_count=3,
                pattern_performance_supported_min_metric_sample_size=10,
            ),
        )

    validate_supported_performance(
        summary.model_copy(
            update={
                "asset_count": 10,
                "metrics": [summary.metrics[0].model_copy(update={"sample_size": 10})],
            }
        ),
        Settings(
            pattern_performance_supported_min_asset_count=10,
            pattern_performance_supported_min_campaign_count=3,
            pattern_performance_supported_min_metric_sample_size=10,
        ),
    )


def test_pattern_kit_contract_rejects_winner_claim_without_performance() -> None:
    workspace_id = uuid4()
    dna_model, evidence = _dna_model(workspace_id)
    pattern = build_fixture_pattern_kit(
        pattern_kit_id=uuid4(),
        workspace_id=workspace_id,
        version=1,
        created_by=uuid4(),
        created_at=utc_now(),
        request=_create_request([dna_model.id], kind="single_asset_abstraction"),
        sources=[_source_input(dna_model, evidence)],
        model_run_id=uuid4(),
    )
    payload = pattern.model_dump(mode="json")
    payload["summary"] = "Winning hook structure for this category."

    with pytest.raises(ValidationError, match="winning"):
        PatternKitV1.model_validate(payload)


@pytest.mark.asyncio
async def test_pattern_kit_service_persists_fixture_pattern_and_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.pattern_kits.service as service_module

    workspace_id = uuid4()
    user_id = uuid4()
    dna_a, evidence_a = _dna_model(workspace_id)
    dna_b, evidence_b = _dna_model(workspace_id)
    repository = FakePatternKitRepository()
    events = FakeProductEventPublisher(FakeSession())
    monkeypatch.setattr(service_module, "PatternKitRepository", lambda _: repository)
    monkeypatch.setattr(
        service_module,
        "CreativeDnaRepository",
        lambda _: FakeCreativeDnaRepository({dna_a.id: dna_a, dna_b.id: dna_b}),
    )
    monkeypatch.setattr(
        service_module,
        "EvidenceQueries",
        lambda _: FakeEvidenceQueries(
            {
                dna_a.asset_version_id: evidence_a,
                dna_b.asset_version_id: evidence_b,
            }
        ),
    )
    monkeypatch.setattr(service_module, "AiModelRunRepository", FakeAiModelRunRepository)
    monkeypatch.setattr(service_module, "ProductEventPublisher", lambda _: events)

    detail = await PatternKitService(
        cast(AsyncSession, FakeSession()),
        Settings(ai_mode="fixture"),
    ).create(
        workspace_id=workspace_id,
        user_id=user_id,
        data=_create_request([dna_a.id, dna_b.id]),
    )

    assert detail.kit.status == "candidate"
    assert detail.latest_version.pattern.source.source_asset_count == 2
    assert repository.evidence_links
    assert FakeAiModelRunRepository.completed
    assert events.records[0]["event_type"] == "pattern_kit_created"


@pytest.mark.asyncio
async def test_pattern_kit_service_fails_when_evidence_does_not_resolve(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.pattern_kits.service as service_module

    workspace_id = uuid4()
    dna, _evidence = _dna_model(workspace_id)
    monkeypatch.setattr(
        service_module,
        "PatternKitRepository",
        lambda _: FakePatternKitRepository(),
    )
    monkeypatch.setattr(
        service_module,
        "CreativeDnaRepository",
        lambda _: FakeCreativeDnaRepository({dna.id: dna}),
    )
    monkeypatch.setattr(
        service_module,
        "EvidenceQueries",
        lambda _: FakeEvidenceQueries({dna.asset_version_id: []}),
    )
    monkeypatch.setattr(service_module, "AiModelRunRepository", FakeAiModelRunRepository)
    monkeypatch.setattr(
        service_module,
        "ProductEventPublisher",
        lambda _: FakeProductEventPublisher(FakeSession()),
    )

    with pytest.raises(AppError, match="PATTERN_KIT_EVIDENCE_INVALID"):
        await PatternKitService(
            cast(AsyncSession, FakeSession()),
            Settings(ai_mode="fixture"),
        ).create(
            workspace_id=workspace_id,
            user_id=uuid4(),
            data=_create_request([dna.id], kind="single_asset_abstraction"),
        )

    assert FakeAiModelRunRepository.failed


@pytest.mark.asyncio
async def test_pattern_kit_service_hides_cross_workspace_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.pattern_kits.service as service_module

    workspace_id = uuid4()
    foreign_dna, foreign_evidence = _dna_model(uuid4())
    monkeypatch.setattr(
        service_module,
        "CreativeDnaRepository",
        lambda _: FakeCreativeDnaRepository({foreign_dna.id: foreign_dna}),
    )
    monkeypatch.setattr(
        service_module,
        "EvidenceQueries",
        lambda _: FakeEvidenceQueries({foreign_dna.asset_version_id: foreign_evidence}),
    )

    with pytest.raises(AppError, match="CREATIVE_DNA_NOT_FOUND"):
        await PatternKitService(
            cast(AsyncSession, FakeSession()),
            Settings(ai_mode="fixture"),
        ).create(
            workspace_id=workspace_id,
            user_id=uuid4(),
            data=_create_request(
                [foreign_dna.id],
                kind="single_asset_abstraction",
            ),
        )


@pytest.mark.asyncio
async def test_user_version_is_append_only_and_emits_version_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.pattern_kits.service as service_module

    workspace_id = uuid4()
    user_id = uuid4()
    dna, evidence = _dna_model(workspace_id)
    pattern = build_fixture_pattern_kit(
        pattern_kit_id=uuid4(),
        workspace_id=workspace_id,
        version=1,
        created_by=user_id,
        created_at=utc_now(),
        request=_create_request([dna.id], kind="single_asset_abstraction"),
        sources=[_source_input(dna, evidence)],
        model_run_id=uuid4(),
    )
    repository = FakePatternKitRepository()
    await repository.create_kit_with_version(
        workspace_id=workspace_id,
        user_id=user_id,
        pattern=pattern,
        source_rows=[(dna.id, dna.asset_version_id)],
        evidence_links=[(pattern.opening.evidence_refs[0].evidence_id, "opening.hook_text")],
    )
    original_payload = copy.deepcopy(repository.versions[0].pattern_json)
    edited_pattern = pattern.model_copy(update={"summary": "Human-refined structural summary."})
    events = FakeProductEventPublisher(FakeSession())
    monkeypatch.setattr(service_module, "PatternKitRepository", lambda _: repository)
    monkeypatch.setattr(
        service_module,
        "CreativeDnaRepository",
        lambda _: FakeCreativeDnaRepository({dna.id: dna}),
    )
    monkeypatch.setattr(
        service_module,
        "EvidenceQueries",
        lambda _: FakeEvidenceQueries({dna.asset_version_id: evidence}),
    )
    monkeypatch.setattr(service_module, "ProductEventPublisher", lambda _: events)

    created = await PatternKitService(
        cast(AsyncSession, FakeSession()),
        Settings(ai_mode="fixture"),
    ).create_version(
        workspace_id=workspace_id,
        pattern_kit_id=pattern.id,
        user_id=user_id,
        data=CreatePatternKitVersionRequest(
            change_reason="Clarify the reusable structure.",
            pattern=edited_pattern,
        ),
    )

    assert created.version == 2
    assert created.parent_version == 1
    assert created.change_reason == "Clarify the reusable structure."
    assert created.pattern.summary == "Human-refined structural summary."
    assert repository.versions[0].pattern_json == original_payload
    assert events.records[0]["event_type"] == "pattern_kit_version_created"


@pytest.mark.asyncio
async def test_user_version_rejects_exact_source_script(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.pattern_kits.service as service_module

    workspace_id = uuid4()
    user_id = uuid4()
    dna, evidence = _dna_model(workspace_id)
    pattern = build_fixture_pattern_kit(
        pattern_kit_id=uuid4(),
        workspace_id=workspace_id,
        version=1,
        created_by=user_id,
        created_at=utc_now(),
        request=_create_request([dna.id], kind="single_asset_abstraction"),
        sources=[_source_input(dna, evidence)],
        model_run_id=uuid4(),
    )
    repository = FakePatternKitRepository()
    await repository.create_kit_with_version(
        workspace_id=workspace_id,
        user_id=user_id,
        pattern=pattern,
        source_rows=[(dna.id, dna.asset_version_id)],
        evidence_links=[(pattern.opening.evidence_refs[0].evidence_id, "opening.hook_text")],
    )
    copied = pattern.model_copy(
        update={"summary": "My counter was always a mess before this setup."}
    )
    monkeypatch.setattr(service_module, "PatternKitRepository", lambda _: repository)
    monkeypatch.setattr(
        service_module,
        "CreativeDnaRepository",
        lambda _: FakeCreativeDnaRepository({dna.id: dna}),
    )
    monkeypatch.setattr(
        service_module,
        "EvidenceQueries",
        lambda _: FakeEvidenceQueries({dna.asset_version_id: evidence}),
    )

    with pytest.raises(AppError, match="PATTERN_KIT_CONFLICT"):
        await PatternKitService(
            cast(AsyncSession, FakeSession()),
            Settings(ai_mode="fixture"),
        ).create_version(
            workspace_id=workspace_id,
            pattern_kit_id=pattern.id,
            user_id=user_id,
            data=CreatePatternKitVersionRequest(
                change_reason="Do not copy source wording.",
                pattern=copied,
            ),
        )


@pytest.mark.asyncio
async def test_user_version_cannot_self_certify_supported_performance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.pattern_kits.service as service_module

    workspace_id = uuid4()
    user_id = uuid4()
    dna, evidence = _dna_model(workspace_id)
    pattern = build_fixture_pattern_kit(
        pattern_kit_id=uuid4(),
        workspace_id=workspace_id,
        version=1,
        created_by=user_id,
        created_at=utc_now(),
        request=_create_request([dna.id], kind="single_asset_abstraction"),
        sources=[_source_input(dna, evidence)],
        model_run_id=uuid4(),
    )
    repository = FakePatternKitRepository()
    await repository.create_kit_with_version(
        workspace_id=workspace_id,
        user_id=user_id,
        pattern=pattern,
        source_rows=[(dna.id, dna.asset_version_id)],
        evidence_links=[(pattern.opening.evidence_refs[0].evidence_id, "opening.hook_text")],
    )
    fabricated = pattern.model_copy(
        update={
            "performance_summary": PatternPerformanceSummaryV1(
                evidence_status="supported",
                asset_count=10,
                campaign_count=3,
                date_range_start=date(2026, 1, 1),
                date_range_end=date(2026, 1, 31),
                metrics=[
                    PatternMetricSummaryV1(
                        metric_name="hook_rate",
                        sample_size=10,
                        median=0.42,
                        source="user_supplied",
                    )
                ],
                caveats=["Observed correlation does not establish causation."],
                confidence="medium",
            )
        }
    )
    monkeypatch.setattr(service_module, "PatternKitRepository", lambda _: repository)
    monkeypatch.setattr(
        service_module,
        "CreativeDnaRepository",
        lambda _: FakeCreativeDnaRepository({dna.id: dna}),
    )
    monkeypatch.setattr(
        service_module,
        "EvidenceQueries",
        lambda _: FakeEvidenceQueries({dna.asset_version_id: evidence}),
    )

    with pytest.raises(AppError, match="PATTERN_KIT_PERFORMANCE_IMMUTABLE"):
        await PatternKitService(
            cast(AsyncSession, FakeSession()),
            Settings(ai_mode="fixture"),
        ).create_version(
            workspace_id=workspace_id,
            pattern_kit_id=pattern.id,
            user_id=user_id,
            data=CreatePatternKitVersionRequest(
                change_reason="Claim unsupported performance.",
                pattern=fabricated,
            ),
        )


@pytest.mark.asyncio
async def test_pattern_kit_action_transition_emits_review_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.pattern_kits.service as service_module

    workspace_id = uuid4()
    user_id = uuid4()
    dna, evidence = _dna_model(workspace_id)
    pattern = build_fixture_pattern_kit(
        pattern_kit_id=uuid4(),
        workspace_id=workspace_id,
        version=1,
        created_by=user_id,
        created_at=utc_now(),
        request=_create_request([dna.id], kind="single_asset_abstraction"),
        sources=[_source_input(dna, evidence)],
        model_run_id=uuid4(),
    )
    repository = FakePatternKitRepository()
    await repository.create_kit_with_version(
        workspace_id=workspace_id,
        user_id=user_id,
        pattern=pattern,
        source_rows=[(dna.id, dna.asset_version_id)],
        evidence_links=[(pattern.opening.evidence_refs[0].evidence_id, "opening.hook_text")],
    )
    events = FakeProductEventPublisher(FakeSession())
    monkeypatch.setattr(service_module, "PatternKitRepository", lambda _: repository)
    monkeypatch.setattr(service_module, "ProductEventPublisher", lambda _: events)

    service = PatternKitService(
        cast(AsyncSession, FakeSession()),
        Settings(ai_mode="fixture"),
    )
    action = await service.record_action(
        workspace_id=workspace_id,
        pattern_kit_id=pattern.id,
        user_id=user_id,
        data=PatternKitActionRequest(action="reviewed", reason="Looks reusable."),
    )

    assert action.action == "reviewed"
    assert repository.kit is not None
    assert repository.kit.status == "reviewed"
    assert events.records[0]["event_type"] == "pattern_kit_reviewed"

    await service.record_action(
        workspace_id=workspace_id,
        pattern_kit_id=pattern.id,
        user_id=user_id,
        data=PatternKitActionRequest(
            action="validated",
            reason="Human reviewer validated the pattern.",
        ),
    )
    await service.record_action(
        workspace_id=workspace_id,
        pattern_kit_id=pattern.id,
        user_id=user_id,
        data=PatternKitActionRequest(action="archived", reason="Retired after test."),
    )

    assert repository.kit.status == "archived"
    assert [event["event_type"] for event in events.records] == [
        "pattern_kit_reviewed",
        "pattern_kit_validated",
    ]


@pytest.mark.asyncio
async def test_pattern_kit_action_rejects_validate_before_review(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.pattern_kits.service as service_module

    workspace_id = uuid4()
    user_id = uuid4()
    dna, evidence = _dna_model(workspace_id)
    pattern = build_fixture_pattern_kit(
        pattern_kit_id=uuid4(),
        workspace_id=workspace_id,
        version=1,
        created_by=user_id,
        created_at=utc_now(),
        request=_create_request([dna.id], kind="single_asset_abstraction"),
        sources=[_source_input(dna, evidence)],
        model_run_id=uuid4(),
    )
    repository = FakePatternKitRepository()
    await repository.create_kit_with_version(
        workspace_id=workspace_id,
        user_id=user_id,
        pattern=pattern,
        source_rows=[(dna.id, dna.asset_version_id)],
        evidence_links=[(pattern.opening.evidence_refs[0].evidence_id, "opening.hook_text")],
    )
    monkeypatch.setattr(service_module, "PatternKitRepository", lambda _: repository)

    with pytest.raises(ConflictError, match="PATTERN_KIT_STATE_CONFLICT"):
        await PatternKitService(
            cast(AsyncSession, FakeSession()),
            Settings(ai_mode="fixture"),
        ).record_action(
            workspace_id=workspace_id,
            pattern_kit_id=pattern.id,
            user_id=user_id,
            data=PatternKitActionRequest(action="validated", reason="Human validation."),
        )


@pytest.mark.asyncio
async def test_workspace_learned_pattern_requires_promotion_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.pattern_kits.service as service_module

    workspace_id = uuid4()
    user_id = uuid4()
    dna, evidence = _dna_model(workspace_id)
    pattern = build_fixture_pattern_kit(
        pattern_kit_id=uuid4(),
        workspace_id=workspace_id,
        version=1,
        created_by=user_id,
        created_at=utc_now(),
        request=_create_request([dna.id], kind="workspace_learned_pattern"),
        sources=[_source_input(dna, evidence)],
        model_run_id=uuid4(),
    )
    repository = FakePatternKitRepository()
    await repository.create_kit_with_version(
        workspace_id=workspace_id,
        user_id=user_id,
        pattern=pattern,
        source_rows=[(dna.id, dna.asset_version_id)],
        evidence_links=[(pattern.opening.evidence_refs[0].evidence_id, "opening.hook_text")],
    )
    monkeypatch.setattr(service_module, "PatternKitRepository", lambda _: repository)

    with pytest.raises(AppError, match="PATTERN_KIT_PROMOTION_EVIDENCE_REQUIRED"):
        await PatternKitService(
            cast(AsyncSession, FakeSession()),
            Settings(ai_mode="fixture"),
        ).record_action(
            workspace_id=workspace_id,
            pattern_kit_id=pattern.id,
            user_id=user_id,
            data=PatternKitActionRequest(action="reviewed"),
        )


@pytest.mark.asyncio
async def test_pattern_kit_feedback_uses_path_subject_and_latest_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import viraldy.modules.pattern_kits.service as service_module

    workspace_id = uuid4()
    user_id = uuid4()
    dna, evidence = _dna_model(workspace_id)
    pattern = build_fixture_pattern_kit(
        pattern_kit_id=uuid4(),
        workspace_id=workspace_id,
        version=1,
        created_by=user_id,
        created_at=utc_now(),
        request=_create_request([dna.id], kind="single_asset_abstraction"),
        sources=[_source_input(dna, evidence)],
        model_run_id=uuid4(),
    )
    repository = FakePatternKitRepository()
    await repository.create_kit_with_version(
        workspace_id=workspace_id,
        user_id=user_id,
        pattern=pattern,
        source_rows=[(dna.id, dna.asset_version_id)],
        evidence_links=[(pattern.opening.evidence_refs[0].evidence_id, "opening.hook_text")],
    )
    feedback_writer = FakeFeedbackWriter()
    session = FakeSession()
    monkeypatch.setattr(service_module, "PatternKitRepository", lambda _: repository)
    monkeypatch.setattr(service_module, "FeedbackWriter", lambda _: feedback_writer)

    feedback = await PatternKitService(
        cast(AsyncSession, session),
        Settings(ai_mode="fixture"),
    ).create_feedback(
        workspace_id=workspace_id,
        pattern_kit_id=pattern.id,
        user_id=user_id,
        data=CreatePatternKitFeedbackRequest(
            field_path="opening.hook_mechanism",
            feedback_type="partial",
            ai_value_json="problem_first",
            user_value_json="problem-result contrast",
            comment="Make it less generic.",
        ),
    )

    assert feedback.subject_type == "pattern_kit"
    assert feedback.subject_id == pattern.id
    assert feedback.subject_version == repository.kit.latest_version
    assert feedback_writer.feedback is not None
    assert session.commits == 1
    assert session.refreshed == [feedback_writer.feedback]


def _create_request(
    source_ids: list[UUID],
    kind: str = "multi_asset_cluster",
) -> CreatePatternKitRequest:
    return CreatePatternKitRequest(
        name="Problem fast reveal transformation",
        kind=kind,
        scope="workspace_private",
        source_creative_dna_version_ids=source_ids,
        primary_category="home_organization",
        target_platforms=["tiktok_shop"],
        target_markets=["US"],
        objectives=["affiliate", "organic_test"],
        extraction_mode="ai_assisted",
    )


def _dna_model(
    workspace_id: UUID,
) -> tuple[CreativeDnaVersionModel, list[FakeEvidence]]:
    asset_version_id = uuid4()
    evidence = [
        FakeEvidence(
            "hook_signal",
            {
                "hook_type": "problem_first",
                "spoken_text": "My counter was always a mess before this setup.",
                "overlay_text": "Counter reset",
                "visual_description": "messy surface shown before product appears",
                "buyer_pain": "limited counter space",
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
    return (
        CreativeDnaVersionModel(
            id=uuid4(),
            workspace_id=workspace_id,
            reference_id=uuid4(),
            asset_version_id=asset_version_id,
            version_number=1,
            status="completed",
            schema_version=dna.schema_version,
            dna_json=dna.model_dump(mode="json"),
            confidence=dna.overall_confidence,
            analysis_mode="fixture",
            taxonomy_version="creative_dna_taxonomy_v1",
            model_version="fixture_creative_dna_v1",
            prompt_version="creative_dna_extraction_v1",
            created_at=utc_now(),
        ),
        evidence,
    )


def _source_input(
    dna_model: CreativeDnaVersionModel,
    evidence: list[FakeEvidence],
) -> PatternSourceInput:
    return PatternSourceInput(
        creative_dna_version_id=dna_model.id,
        asset_version_id=dna_model.asset_version_id,
        taxonomy_version=dna_model.taxonomy_version,
        dna=CreativeDnaV1.model_validate(dna_model.dna_json),
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
