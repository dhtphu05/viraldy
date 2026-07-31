from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr

from viraldy.modules.ai_gateway.providers.base import (
    ProviderEndpointFamily,
    StructuredGenerationResult,
)
from viraldy.modules.ai_gateway.usage import ProviderUsage
from viraldy.modules.creative_dna.contracts import CreativeDnaV1
from viraldy.modules.creative_dna.provider import (
    LiveCreativeDnaProvider,
    build_creative_dna_evidence_catalog,
    build_creative_dna_output_validator,
)
from viraldy.modules.creative_dna.service import (
    SyncCreativeDnaBuilder,
    _build_creative_dna,
    _evidence_by_type,
)
from viraldy.modules.media_analysis.models import EvidenceItemModel
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError


class FakeSession:
    def __init__(self) -> None:
        self.commit_count = 0

    def commit(self) -> None:
        self.commit_count += 1


class FakeDnaRepository:
    def __init__(self, session: object) -> None:
        del session
        self.created: list[dict[str, object]] = []
        self.existing: object | None = None

    def for_processing_job(
        self,
        workspace_id: UUID,
        asset_version_id: UUID,
        processing_job_id: UUID,
    ) -> object | None:
        del workspace_id, asset_version_id, processing_job_id
        return self.existing

    def create(self, **kwargs: object) -> object:
        self.created.append(kwargs)
        return SimpleNamespace(
            id=kwargs.get("dna_version_id", uuid4()),
            primary_model_run_id=kwargs.get("primary_model_run_id"),
            processing_job_id=kwargs.get("processing_job_id"),
            dna_json=kwargs["dna_json"],
            analysis_mode=kwargs["analysis_mode"],
        )


class FakeModelRunRepository:
    def __init__(self, session: object) -> None:
        del session
        self.created: list[dict[str, object]] = []
        self.completed: list[dict[str, object]] = []
        self.failed: list[dict[str, object]] = []
        self.run = SimpleNamespace(id=uuid4(), attempt=1, status="running")

    def create_running(self, **kwargs: object) -> object:
        self.created.append(kwargs)
        return self.run

    def complete(self, run: object, output_summary: dict[str, object], **kwargs: object) -> object:
        self.completed.append({"run": run, "output_summary": output_summary, **kwargs})
        self.run.status = "completed"
        return run

    def fail(
        self,
        run: object,
        code: str,
        message: str,
        **kwargs: object,
    ) -> object:
        self.failed.append({"run": run, "code": code, "message": message, **kwargs})
        self.run.status = "failed"
        return run


def test_native_creative_dna_uses_structured_operation_and_strict_validator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    asset_id = uuid4()
    asset_version_id = uuid4()
    model_run_id = uuid4()
    evidence = _evidence(workspace_id, asset_version_id)
    expected = _dna(evidence)
    captured: dict[str, object] = {}

    def execute(
        settings: Settings,
        context: object,
        output_model: type[object],
        **kwargs: object,
    ) -> StructuredGenerationResult:
        del settings
        captured["context"] = context
        captured["output_model"] = output_model
        validator = cast(Any, kwargs["output_validator"])
        validator(expected)
        return StructuredGenerationResult(
            parsed_output=expected,
            provider="openai",
            endpoint_family=ProviderEndpointFamily.RESPONSES,
            model="gpt-5",
            provider_request_id="req_native",
            http_status=200,
            latency_ms=25,
            usage=ProviderUsage(input_tokens=100, output_tokens=200, total_tokens=300),
            response_status="completed",
            repair_attempt_count=1,
        )

    monkeypatch.setattr(
        "viraldy.modules.creative_dna.provider.execute_structured_operation",
        execute,
    )
    settings = Settings(
        ai_mode="live",
        ai_provider="openai",
        openai_api_key=SecretStr("test-key"),
        openai_text_model="gpt-5",
    )

    execution = LiveCreativeDnaProvider(settings).build_with_metadata(
        workspace_id=workspace_id,
        actor_user_id=uuid4(),
        asset_id=asset_id,
        asset_version_id=asset_version_id,
        reference_id=uuid4(),
        evidence=evidence,
        model_run_id=model_run_id,
        media_duration_ms=5_000,
        product_context=None,
        product_context_version=None,
    )

    context = cast(Any, captured["context"])
    assert context.operation.value == "creative_dna_build"
    assert context.request_id == str(model_run_id)
    assert context.source_artifact_ids == [asset_id]
    assert context.source_version_ids == [asset_version_id]
    assert captured["output_model"] is CreativeDnaV1
    assert execution.output == expected
    assert execution.provider_request_id == "req_native"
    assert execution.repair_attempt_count == 1
    assert execution.usage_json["total_tokens"] == 300


def test_compatible_creative_dna_path_uses_structured_executor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    asset_id = uuid4()
    asset_version_id = uuid4()
    evidence = _evidence(workspace_id, asset_version_id)
    expected = _dna(evidence)
    captured: dict[str, object] = {}

    def execute(
        settings: Settings,
        context: object,
        output_model: type[object],
        **kwargs: object,
    ) -> StructuredGenerationResult:
        del settings
        captured["context"] = context
        captured["output_model"] = output_model
        validator = cast(Any, kwargs["output_validator"])
        validator(expected)
        return StructuredGenerationResult(
            parsed_output=expected,
            provider="openai_compatible",
            endpoint_family=ProviderEndpointFamily.CHAT_COMPLETIONS,
            model="mock-text",
            provider_request_id="req_compatible",
            http_status=200,
            latency_ms=12,
            usage=ProviderUsage(
                input_tokens=50,
                output_tokens=75,
                total_tokens=125,
            ),
            response_status="completed",
            repair_attempt_count=1,
        )

    monkeypatch.setattr(
        "viraldy.modules.creative_dna.provider.execute_structured_operation",
        execute,
    )
    settings = Settings(
        ai_mode="mock",
        ai_provider="openai_compatible",
        ai_base_url="http://mock.test/v1",
        ai_text_model="mock-text",
    )

    execution = LiveCreativeDnaProvider(settings).build_with_metadata(
        workspace_id=workspace_id,
        actor_user_id=None,
        asset_id=asset_id,
        asset_version_id=asset_version_id,
        reference_id=None,
        evidence=evidence,
        model_run_id=uuid4(),
        media_duration_ms=5_000,
        product_context=None,
        product_context_version=None,
    )

    context = cast(Any, captured["context"])
    assert context.operation.value == "creative_dna_build"
    assert captured["output_model"] is CreativeDnaV1
    assert execution.output == expected
    assert execution.provider_request_id == "req_compatible"
    assert execution.usage_json["total_tokens"] == 125
    assert execution.repair_attempt_count == 1


def test_creative_dna_validator_rejects_foreign_evidence_and_fabricated_timestamps() -> None:
    workspace_id = uuid4()
    asset_version_id = uuid4()
    evidence = _evidence(workspace_id, asset_version_id)
    expected = _dna(evidence)
    validator = build_creative_dna_output_validator(evidence, media_duration_ms=5_000)

    foreign_payload = expected.model_dump(mode="json")
    foreign_payload["opening"]["hook_text"]["evidence_ids"] = [str(uuid4())]
    with pytest.raises(ValueError, match="outside the supplied catalog"):
        validator(CreativeDnaV1.model_validate(foreign_payload))

    timestamp_payload = expected.model_dump(mode="json")
    timestamp_payload["product"]["first_appearance_ms"]["value"] = 4_999
    timestamp_payload["product"]["first_appearance_ms"]["status"] = "observed"
    timestamp_payload["product"]["first_appearance_ms"]["evidence_ids"] = [
        str(evidence[1].id)
    ]
    with pytest.raises(ValueError, match="timestamp"):
        validator(CreativeDnaV1.model_validate(timestamp_payload))


def test_creative_dna_validator_accepts_grounded_derived_durations() -> None:
    workspace_id = uuid4()
    asset_version_id = uuid4()
    evidence = _evidence(workspace_id, asset_version_id)
    payload = _dna(evidence).model_dump(mode="json")
    payload["product"]["total_visible_ms"]["value"] = 3_400
    payload["product"]["total_visible_ms"]["status"] = "inferred"
    payload["product"]["total_visible_ms"]["evidence_ids"] = [
        str(evidence[1].id)
    ]
    validator = build_creative_dna_output_validator(
        evidence,
        media_duration_ms=5_000,
    )

    validator(CreativeDnaV1.model_validate(payload))

    payload["product"]["total_visible_ms"]["value"] = 5_001
    with pytest.raises(ValueError, match="duration beyond media duration"):
        validator(CreativeDnaV1.model_validate(payload))


def test_creative_dna_validator_rejects_negative_time_values() -> None:
    workspace_id = uuid4()
    asset_version_id = uuid4()
    evidence = _evidence(workspace_id, asset_version_id)
    payload = _dna(evidence).model_dump(mode="json")
    payload["product"]["total_visible_ms"]["value"] = -1
    validator = build_creative_dna_output_validator(
        evidence,
        media_duration_ms=5_000,
    )

    with pytest.raises(ValueError, match="non-negative integers"):
        validator(CreativeDnaV1.model_validate(payload))


def test_creative_dna_catalog_rejects_wrong_source_version() -> None:
    workspace_id = uuid4()
    expected_version_id = uuid4()
    evidence = _evidence(workspace_id, uuid4())

    with pytest.raises(AppError) as exc_info:
        build_creative_dna_evidence_catalog(
            evidence,
            workspace_id=workspace_id,
            asset_id=uuid4(),
            asset_version_id=expected_version_id,
            media_duration_ms=5_000,
        )

    assert exc_info.value.code == "CREATIVE_DNA_EVIDENCE_INVALID"


def test_ai_builder_persists_dedicated_completed_model_run_and_links_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    asset_id = uuid4()
    asset_version_id = uuid4()
    processing_job_id = uuid4()
    evidence = _evidence(workspace_id, asset_version_id)
    expected = _dna(evidence)
    session = FakeSession()
    dna_repo = FakeDnaRepository(session)
    model_repo = FakeModelRunRepository(session)

    monkeypatch.setattr(
        "viraldy.modules.creative_dna.service.SyncCreativeDnaRepository",
        lambda _: dna_repo,
    )
    monkeypatch.setattr(
        "viraldy.modules.creative_dna.service.SyncAiModelRunRepository",
        lambda _: model_repo,
    )
    monkeypatch.setattr(
        "viraldy.modules.creative_dna.service.LiveCreativeDnaProvider",
        lambda _: _SuccessfulProvider(expected),
    )
    settings = Settings(
        ai_mode="live",
        ai_provider="openai",
        openai_api_key=SecretStr("test-key"),
        openai_text_model="gpt-5",
    )

    dna = SyncCreativeDnaBuilder(cast(Any, session), settings).build(
        workspace_id,
        asset_version_id,
        uuid4(),
        evidence,
        "live",
        asset_id=asset_id,
        processing_job_id=processing_job_id,
        actor_user_id=uuid4(),
        product_id=None,
        media_duration_ms=5_000,
        attempt_count=2,
    )

    created_run = model_repo.created[0]
    assert created_run["operation"] == "creative_dna_build"
    assert created_run["subject_type"] == "creative_dna_version"
    assert created_run["prompt_name"] == "creative_dna_extraction"
    assert created_run["schema_version"] == "creative_dna_v1"
    assert created_run["attempt_count"] == 2
    assert model_repo.run.attempt == 2
    assert model_repo.completed[0]["provider_request_id"] == "req_success"
    assert model_repo.completed[0]["repair_attempt_count"] == 1
    assert dna.primary_model_run_id == model_repo.run.id
    assert dna.processing_job_id == processing_job_id
    assert dna_repo.created[0]["primary_model_run_id"] == model_repo.run.id
    assert session.commit_count == 2


def test_ai_builder_persists_failed_model_run_and_never_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    asset_id = uuid4()
    asset_version_id = uuid4()
    evidence = _evidence(workspace_id, asset_version_id)
    session = FakeSession()
    dna_repo = FakeDnaRepository(session)
    model_repo = FakeModelRunRepository(session)

    monkeypatch.setattr(
        "viraldy.modules.creative_dna.service.SyncCreativeDnaRepository",
        lambda _: dna_repo,
    )
    monkeypatch.setattr(
        "viraldy.modules.creative_dna.service.SyncAiModelRunRepository",
        lambda _: model_repo,
    )
    monkeypatch.setattr(
        "viraldy.modules.creative_dna.service.LiveCreativeDnaProvider",
        lambda _: _FailingProvider(),
    )
    settings = Settings(
        ai_mode="live",
        ai_provider="openai",
        openai_api_key=SecretStr("test-key"),
        openai_text_model="gpt-5",
    )

    with pytest.raises(AppError, match="provider refused"):
        SyncCreativeDnaBuilder(cast(Any, session), settings).build(
            workspace_id,
            asset_version_id,
            None,
            evidence,
            "live",
            asset_id=asset_id,
            processing_job_id=uuid4(),
            actor_user_id=None,
            product_id=None,
            media_duration_ms=5_000,
            attempt_count=1,
        )

    assert dna_repo.created == []
    assert model_repo.completed == []
    assert model_repo.failed[0]["code"] == "OPENAI_REFUSED"
    assert model_repo.failed[0]["provider_request_id"] == "req_failed"
    assert model_repo.failed[0]["repair_attempt_count"] == 1
    assert session.commit_count == 2


def test_fixture_builder_stays_deterministic_and_creates_no_model_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    asset_version_id = uuid4()
    evidence = _evidence(workspace_id, asset_version_id)
    session = FakeSession()
    dna_repo = FakeDnaRepository(session)

    monkeypatch.setattr(
        "viraldy.modules.creative_dna.service.SyncCreativeDnaRepository",
        lambda _: dna_repo,
    )

    dna = SyncCreativeDnaBuilder(
        cast(Any, session),
        Settings(ai_mode="fixture"),
    ).build(
        workspace_id,
        asset_version_id,
        None,
        evidence,
        "fixture",
    )

    assert dna.primary_model_run_id is None
    assert dna_repo.created[0]["model_version"] == "fixture_creative_dna_v1"
    assert session.commit_count == 0


def test_builder_retry_reuses_completed_version_for_same_processing_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    asset_version_id = uuid4()
    processing_job_id = uuid4()
    evidence = _evidence(workspace_id, asset_version_id)
    session = FakeSession()
    dna_repo = FakeDnaRepository(session)
    existing = SimpleNamespace(
        id=uuid4(),
        primary_model_run_id=uuid4(),
        processing_job_id=processing_job_id,
    )
    dna_repo.existing = existing

    monkeypatch.setattr(
        "viraldy.modules.creative_dna.service.SyncCreativeDnaRepository",
        lambda _: dna_repo,
    )
    monkeypatch.setattr(
        "viraldy.modules.creative_dna.service.LiveCreativeDnaProvider",
        lambda _: pytest.fail("provider must not run for a completed processing job"),
    )

    result = SyncCreativeDnaBuilder(
        cast(Any, session),
        Settings(ai_mode="live", ai_provider="openai", openai_api_key=SecretStr("test-key")),
    ).build(
        workspace_id,
        asset_version_id,
        None,
        evidence,
        "live",
        asset_id=uuid4(),
        processing_job_id=processing_job_id,
    )

    assert result is existing
    assert dna_repo.created == []
    assert session.commit_count == 0


class _SuccessfulProvider:
    def __init__(self, output: CreativeDnaV1) -> None:
        self._output = output

    def build_with_metadata(self, **kwargs: object) -> object:
        del kwargs
        return SimpleNamespace(
            output=self._output,
            provider_request_id="req_success",
            http_status=200,
            latency_ms=20,
            usage_json={"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
            repair_attempt_count=1,
        )


class _FailingProvider:
    def build_with_metadata(self, **kwargs: object) -> object:
        del kwargs
        raise AppError(
            "OPENAI_REFUSED",
            "provider refused",
            details={
                "http_status": 422,
                "provider_request_id": "req_failed",
                "repair_attempt_count": 1,
            },
        )


def _evidence(workspace_id: UUID, asset_version_id: UUID) -> list[EvidenceItemModel]:
    return [
        EvidenceItemModel(
            id=uuid4(),
            workspace_id=workspace_id,
            asset_version_id=asset_version_id,
            analysis_run_type="creative_dna_build",
            evidence_type="hook_signal",
            evidence_schema_version="evidence_v1",
            start_ms=0,
            end_ms=1_000,
            value_json={
                "hook_type": "result_first",
                "spoken_text": "See the observed result first.",
                "visual_description": "The result is visible before the demonstration.",
                "confidence": 0.9,
            },
            confidence=Decimal("0.9"),
            source="vision",
        ),
        EvidenceItemModel(
            id=uuid4(),
            workspace_id=workspace_id,
            asset_version_id=asset_version_id,
            analysis_run_type="creative_dna_build",
            evidence_type="product_visibility_summary",
            evidence_schema_version="evidence_v1",
            start_ms=500,
            end_ms=4_000,
            value_json={
                "first_appearance_ms": 500,
                "total_visible_ms": 3_500,
                "screen_time_ratio": 0.7,
                "clear_close_up_present": True,
                "usage_present": True,
                "confidence": 0.85,
            },
            confidence=Decimal("0.85"),
            source="vision",
        ),
        EvidenceItemModel(
            id=uuid4(),
            workspace_id=workspace_id,
            asset_version_id=asset_version_id,
            analysis_run_type="creative_dna_build",
            evidence_type="demo_summary",
            evidence_schema_version="evidence_v1",
            start_ms=1_000,
            end_ms=3_500,
            value_json={
                "detected": True,
                "demo_type": "usage",
                "mechanism_clarity": "clear",
                "before_state_visible": True,
                "after_state_visible": True,
                "confidence": 0.88,
            },
            confidence=Decimal("0.88"),
            source="vision",
        ),
    ]


def _dna(evidence: list[EvidenceItemModel]) -> CreativeDnaV1:
    return _build_creative_dna(_evidence_by_type(evidence))
