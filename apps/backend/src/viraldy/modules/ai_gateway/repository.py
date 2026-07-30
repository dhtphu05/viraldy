from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from viraldy.modules.ai_gateway.models import AiModelRunModel
from viraldy.platform.clock.utc import utc_now


class AiModelRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_running(
        self,
        workspace_id: UUID,
        processing_job_id: UUID | None,
        subject_type: str,
        subject_id: UUID,
        capability: str,
        analysis_mode: str,
        provider: str,
        model: str,
        prompt_version: str | None,
        response_schema_version: str,
        request_hash: str,
        input_summary: dict[str, object],
        *,
        operation: str | None = None,
        schema_version: str | None = None,
        input_hash: str | None = None,
        attempt_count: int = 1,
    ) -> AiModelRunModel:
        run = _run(
            workspace_id,
            processing_job_id,
            subject_type,
            subject_id,
            capability,
            analysis_mode,
            provider,
            model,
            prompt_version,
            response_schema_version,
            request_hash,
            input_summary,
            operation=operation,
            schema_version=schema_version,
            input_hash=input_hash,
            attempt_count=attempt_count,
        )
        self._session.add(run)
        await self._session.flush()
        return run

    async def complete(
        self,
        run: AiModelRunModel,
        output_summary: dict[str, object],
        http_status: int | None,
        provider_request_id: str | None,
        latency_ms: int | None,
        *,
        usage_json: dict[str, object] | None = None,
        estimated_cost: Decimal | None = None,
    ) -> AiModelRunModel:
        run.status = "completed"
        run.output_summary_json = output_summary
        if usage_json is not None:
            run.usage_json = usage_json
        if estimated_cost is not None:
            run.estimated_cost = estimated_cost
        run.http_status = http_status
        run.provider_request_id = provider_request_id
        run.latency_ms = latency_ms
        run.completed_at = utc_now()
        await self._session.flush()
        return run

    async def fail(
        self,
        run: AiModelRunModel,
        code: str,
        message: str,
        http_status: int | None = None,
        latency_ms: int | None = None,
        safe_error_message: str | None = None,
    ) -> AiModelRunModel:
        run.status = "failed"
        run.error_code = code
        run.error_message = message
        run.safe_error_message = safe_error_message or message
        run.http_status = http_status
        run.latency_ms = latency_ms
        run.completed_at = utc_now()
        await self._session.flush()
        return run


class SyncAiModelRunRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_running(
        self,
        workspace_id: UUID,
        processing_job_id: UUID | None,
        subject_type: str,
        subject_id: UUID,
        capability: str,
        analysis_mode: str,
        provider: str,
        model: str,
        prompt_version: str | None,
        response_schema_version: str,
        request_hash: str,
        input_summary: dict[str, object],
        *,
        operation: str | None = None,
        schema_version: str | None = None,
        input_hash: str | None = None,
        attempt_count: int = 1,
    ) -> AiModelRunModel:
        run = _run(
            workspace_id,
            processing_job_id,
            subject_type,
            subject_id,
            capability,
            analysis_mode,
            provider,
            model,
            prompt_version,
            response_schema_version,
            request_hash,
            input_summary,
            operation=operation,
            schema_version=schema_version,
            input_hash=input_hash,
            attempt_count=attempt_count,
        )
        self._session.add(run)
        self._session.flush()
        return run

    def complete(
        self,
        run: AiModelRunModel,
        output_summary: dict[str, object],
        http_status: int | None,
        provider_request_id: str | None,
        latency_ms: int | None,
        *,
        usage_json: dict[str, object] | None = None,
        estimated_cost: Decimal | None = None,
    ) -> AiModelRunModel:
        run.status = "completed"
        run.output_summary_json = output_summary
        if usage_json is not None:
            run.usage_json = usage_json
        if estimated_cost is not None:
            run.estimated_cost = estimated_cost
        run.http_status = http_status
        run.provider_request_id = provider_request_id
        run.latency_ms = latency_ms
        run.completed_at = utc_now()
        self._session.flush()
        return run

    def fail(
        self,
        run: AiModelRunModel,
        code: str,
        message: str,
        http_status: int | None = None,
        latency_ms: int | None = None,
        safe_error_message: str | None = None,
    ) -> AiModelRunModel:
        run.status = "failed"
        run.error_code = code
        run.error_message = message
        run.safe_error_message = safe_error_message or message
        run.http_status = http_status
        run.latency_ms = latency_ms
        run.completed_at = utc_now()
        self._session.flush()
        return run


def _run(
    workspace_id: UUID,
    processing_job_id: UUID | None,
    subject_type: str,
    subject_id: UUID,
    capability: str,
    analysis_mode: str,
    provider: str,
    model: str,
    prompt_version: str | None,
    response_schema_version: str,
    request_hash: str,
    input_summary: dict[str, object],
    *,
    operation: str | None = None,
    schema_version: str | None = None,
    input_hash: str | None = None,
    attempt_count: int = 1,
) -> AiModelRunModel:
    return AiModelRunModel(
        workspace_id=workspace_id,
        processing_job_id=processing_job_id,
        subject_type=subject_type,
        subject_id=subject_id,
        capability=capability,
        operation=operation or capability,
        analysis_mode=analysis_mode,
        provider=provider,
        model=model,
        prompt_version=prompt_version,
        response_schema_version=response_schema_version,
        schema_version=schema_version or response_schema_version,
        status="running",
        attempt=1,
        attempt_count=attempt_count,
        request_hash=request_hash,
        input_hash=input_hash or request_hash,
        input_summary_json=input_summary,
        output_summary_json={},
        usage_json={},
        started_at=utc_now(),
    )
