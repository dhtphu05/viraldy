from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from uuid import uuid4

from sqlalchemy.orm import Session

from viraldy.modules.assets.public import AssetVersionSnapshot
from viraldy.modules.domain_intelligence import public as domain_public
from viraldy.modules.domain_intelligence.public import (
    NormalizedEvidenceBundle,
    UGCRecommendation,
    UGCReviewResult,
)
from viraldy.modules.jobs.models import ProcessingJobModel
from viraldy.modules.ugc_review import public as ugc_public
from viraldy.worker.tasks import process_asset as worker


def test_ugc_review_worker_reuses_media_pipeline_and_persists_recommendation_result(
    monkeypatch,
) -> None:
    workspace_id = uuid4()
    asset_id = uuid4()
    asset_version_id = uuid4()
    job = ProcessingJobModel(
        id=uuid4(),
        workspace_id=workspace_id,
        subject_type="asset_version",
        subject_id=asset_version_id,
        job_type="ugc_review_v1",
        queue_name="default",
        status="running",
        progress=10,
        stage="loading_job",
        attempt_count=1,
        max_attempts=3,
        input_json={
            "asset_id": str(asset_id),
            "asset_version_id": str(asset_version_id),
            "request_context": {"commerce_domain": "dropshipping"},
        },
    )
    loaded = AssetVersionSnapshot(
        asset_id=asset_id,
        asset_version_id=asset_version_id,
        workspace_id=workspace_id,
        product_id=None,
        storage_key="workspace/asset/source.mp4",
        original_filename="draft.mp4",
        declared_mime_type="video/mp4",
        detected_mime_type="video/mp4",
        size_bytes=100,
        checksum_sha256="a" * 64,
        metadata_json={"duration_ms": 12_000},
    )
    primary_model_run_id = uuid4()
    calls: dict[str, object] = {}

    def fake_process_media(*_args, **_kwargs):
        calls["run_type"] = _args[-1]
        return loaded, [SimpleNamespace(id=uuid4())], primary_model_run_id

    evidence_bundle = NormalizedEvidenceBundle(
        coverage={"visual_observations": True},
        strengths=["Keep the clear product close-up."],
    )
    result = UGCReviewResult(
        review_id=str(job.id),
        headline="Strong draft",
        summary="Keep the close-up and confirm shipping language.",
        recommended_next_action="confirm_information",
        overall_confidence="medium",
        strengths_to_keep=["Keep the clear product close-up."],
        fix_first=[],
        improvements=[],
        confirmations=[],
        creator_revision_message="Keep the clear close-up.",
        policy_pack_version="v1",
        analysis_provenance={"pipeline": "media_pipeline_v1"},
        created_at=datetime.now(UTC).isoformat(),
    )

    class FakeDomainQueries:
        def __init__(self, _session) -> None:
            pass

        def select_rules(self, context, evidence):
            calls["context"] = context
            calls["evidence"] = evidence
            return []

        def status(self):
            return SimpleNamespace(version="v1")

    class FakeReviewRepository:
        def __init__(self, _session) -> None:
            pass

        def persist_result(self, **values):
            calls["persisted"] = values

    class FakeJobRepository:
        def __init__(self) -> None:
            self.stages: list[str] = []

        def update_progress(self, _job, _progress, stage):
            self.stages.append(stage)

    class FakeSession:
        def commit(self) -> None:
            pass

    monkeypatch.setattr(worker, "_process_media", fake_process_media)
    monkeypatch.setattr(domain_public, "adapt_media_evidence", lambda _items: evidence_bundle)
    monkeypatch.setattr(domain_public, "SyncDomainIntelligenceQueries", FakeDomainQueries)
    def fake_evaluate_review(**values):
        calls["evaluation_provenance"] = values["analysis_provenance"]
        return result

    monkeypatch.setattr(domain_public, "evaluate_review", fake_evaluate_review)
    monkeypatch.setattr(ugc_public, "SyncUGCReviewRepository", FakeReviewRepository)
    job_repository = FakeJobRepository()

    output = worker._review_ugc_asset(
        job,
        cast(object, job_repository),
        cast(object, SimpleNamespace()),
        cast(Session, FakeSession()),
    )

    assert calls["run_type"] == "ugc_review_v1"
    assert calls["evidence"] == evidence_bundle
    assert calls["context"].commerce_domain == "dropshipping"
    assert calls["persisted"]["processing_job_id"] == job.id
    assert calls["persisted"]["asset_version_id"] == asset_version_id
    assert calls["evaluation_provenance"] == {
        "analysis_mode": "fixture",
        "primary_model_run_id": str(primary_model_run_id),
    }
    assert job_repository.stages == [
        "selecting_policies",
        "evaluating_review",
        "persisting_results",
    ]
    assert output["review_id"] == str(job.id)
    assert output["policy_pack_version"] == "v1"
    assert output["primary_model_run_id"] == str(primary_model_run_id)


def test_execution_brief_keeps_deterministic_result_when_live_synthesis_fails(
    monkeypatch,
) -> None:
    job = ProcessingJobModel(
        id=uuid4(),
        workspace_id=uuid4(),
        subject_type="asset_version",
        subject_id=uuid4(),
        job_type="ugc_review_v1",
        queue_name="default",
        status="running",
        progress=80,
        stage="evaluating_review",
        attempt_count=1,
        max_attempts=3,
    )
    recommendation = UGCRecommendation(
        id="recommendation-1",
        group="fix_first",
        title="Deterministic title",
        reason="Evidence-backed reason.",
        why_it_matters="This is required before publishing.",
        owner="editor",
        confidence="high",
        task_kind="video_edit_required",
        priority="fix_before_publish",
    )
    result = UGCReviewResult(
        review_id=str(job.id),
        headline="Review ready",
        summary="One edit is required.",
        recommended_next_action="revise",
        overall_confidence="high",
        strengths_to_keep=["Keep the natural opening."],
        fix_first=[recommendation],
        creator_revision_message="Keep the opening.",
        policy_pack_version="v1",
        created_at=datetime.now(UTC).isoformat(),
    )
    loaded = AssetVersionSnapshot(
        asset_id=uuid4(),
        asset_version_id=job.subject_id,
        workspace_id=job.workspace_id,
        product_id=None,
        storage_key="workspace/asset/source.mp4",
        original_filename="draft.mp4",
        declared_mime_type="video/mp4",
        detected_mime_type="video/mp4",
        size_bytes=100,
        checksum_sha256="a" * 64,
        metadata_json={},
    )
    calls: dict[str, object] = {}

    class FakeModelRuns:
        def __init__(self, _session) -> None:
            pass

        def create_running(self, **_values):
            return SimpleNamespace(id=uuid4())

        def fail(self, _run, code, _message, **_values):
            calls["failure_code"] = code

    class LiveSettings:
        ai_mode = "live"
        ai_provider = "openai"

        def resolve_openai_model(self, _operation):
            return "gpt-test"

    monkeypatch.setattr(
        "viraldy.modules.ai_gateway.repository.SyncAiModelRunRepository", FakeModelRuns
    )
    monkeypatch.setattr(
        "viraldy.modules.ai_gateway.execution.execute_structured_operation",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(Exception("invalid provider output")),
    )
    monkeypatch.setattr(
        "viraldy.modules.ai_gateway.prompt_packages.get_prompt_package",
        lambda _operation: SimpleNamespace(
            prompt_version="ugc_execution_brief_v1",
            output_schema_version="ugc_execution_brief_synthesis_v1",
            prompt_name="ugc_execution_brief",
        ),
    )

    enriched = worker._enrich_ugc_execution_brief(
        job=job,
        loaded=loaded,
        context=domain_public.UGCReviewContext(),
        evidence_bundle=NormalizedEvidenceBundle(),
        result=result,
        settings=LiveSettings(),
        session=cast(Session, SimpleNamespace(commit=lambda: None)),
    )

    assert enriched.fix_first[0].title == "Deterministic title"
    synthesis = enriched.analysis_provenance["execution_brief_synthesis"]
    assert synthesis["status"] == "fallback"
    assert synthesis["reason"] == "invalid_output"
    assert isinstance(synthesis["model_run_id"], str)
    assert calls["failure_code"] == "UGC_EXECUTION_BRIEF_INVALID"
