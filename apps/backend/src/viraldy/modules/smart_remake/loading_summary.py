"""One optional, independently accounted video observation while the full compiler runs."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from starlette.concurrency import run_in_threadpool

from .analysis_progress import publish_quick_summary
from .budget_ledger import fail_attempt, is_unlimited_policy, unknown_attempt
from .budget_models import SmartRemakeAttemptModel
from .budgeted_analysis import LedgerGeminiClient
from .engine.config import get_gemini_model
from .engine.gemini_client import HttpGeminiClient
from .engine.schemas import UploadedMedia
from .quick_preview_media import prepare_quick_preview
from .repair_repository import RepairRepository
from .source_audio import SourceAudioObservation, normalize_source_audio, source_audio_prompt

logger = logging.getLogger(__name__)
SUMMARY_MARKER = "SMART_REMAKE_LOADING_SUMMARY_V1"
_RECEIPT_SETTLEMENTS: set[asyncio.Task[None]] = set()


class SummaryObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(min_length=1, max_length=40)
    detail: str = Field(min_length=1, max_length=300)


class SourceLoadingSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str = Field(min_length=1, max_length=500)
    observations: list[SummaryObservation] = Field(max_length=3)
    sourceAudio: SourceAudioObservation | None = None

    @field_validator("sourceAudio", mode="before")
    @classmethod
    def optional_audio(cls, value: Any) -> dict[str, Any] | None:
        return normalize_source_audio(value)


def summary_prompt(
    duration: float, *, sampled_frames: bool = False, has_audio: bool = True
) -> tuple[str, str]:
    return (
        SUMMARY_MARKER + "\nBạn chỉ quan sát video nguồn, không viết kịch bản và không tạo video. "
        'Trả JSON ngắn bằng tiếng Việt: {"summary":"...","observations":['
        '{"label":"Hành động","detail":"..."}]}. '
        "Tóm tắt tối đa hai câu, tối đa ba nhận định về chủ thể, hành động hoặc cách quay "
        "thực sự nhìn thấy. Không đoán nhận diện sản phẩm đích, thương hiệu, số cảnh, "
        "mốc thời gian hay chi tiết không quan sát được. "
        + (source_audio_prompt(transcript_limit=600) if has_audio else
           "Không có âm thanh trong tư liệu gửi cho lượt đọc nhanh này. "
           "Không suy diễn lời thoại, nhạc, nhịp âm thanh hoặc trả sourceAudio.")
        + " Không thêm trường JSON khác ngoài summary, observations và sourceAudio.",
        (
            f"Quan sát sáu khung hình lấy mẫu theo thứ tự từ video nguồn {duration:g} giây. "
            "Đây chỉ là các thời điểm lấy mẫu, không phải toàn bộ cảnh hay chuyển động. "
            "Chỉ nhận xét chi tiết nhìn thấy; không suy diễn sự liên tục giữa các ảnh. "
            if sampled_frames else
            f"Quan sát bản xem nhanh độ phân giải thấp của toàn bộ video nguồn {duration:g} giây. "
        ) + "Cho người dùng biết nội dung đã quan sát trong lúc phân tích chi tiết tiếp tục.",
    )


def _failure_reason(error: Exception) -> Literal["timeout", "invalid_response", "unavailable"]:
    current: BaseException | None = error
    for _ in range(5):
        if current is None:
            break
        if isinstance(current, TimeoutError | httpx.TimeoutException):
            return "timeout"
        if isinstance(current, ValueError | ValidationError):
            return "invalid_response"
        if getattr(current, "code", None) == "SMART_REMAKE_GEMINI_OUTPUT_TRUNCATED":
            return "invalid_response"
        current = current.__cause__
    return "unavailable"


async def _publish(
    factory: async_sessionmaker[AsyncSession],
    workspace_id: UUID,
    project_id: UUID,
    operation_id: UUID,
    value: dict[str, Any],
) -> None:
    async with factory() as session:
        operation = await RepairRepository(session).operation(
            workspace_id, project_id, operation_id
        )
        await publish_quick_summary(session, operation, value)


async def _settle_cancelled_summary(
    factory: async_sessionmaker[AsyncSession],
    workspace_id: UUID,
    project_id: UUID,
    operation_id: UUID,
) -> None:
    async with factory() as session:
        attempt = await session.scalar(
            select(SmartRemakeAttemptModel).where(
                SmartRemakeAttemptModel.workspace_id == workspace_id,
                SmartRemakeAttemptModel.project_id == project_id,
                SmartRemakeAttemptModel.idempotency_key
                == f"{operation_id}:analysis:loading_summary:0",
                SmartRemakeAttemptModel.stage == "analysis",
                SmartRemakeAttemptModel.purpose == "loading_summary",
            )
        )
        if attempt is None or attempt.status in {"completed", "failed"}:
            return
        if attempt.status == "reserved":
            await fail_attempt(
                session,
                workspace_id,
                project_id,
                attempt.id,
                definitely_not_submitted=True,
                error={"code": "LOADING_SUMMARY_CANCELLED", "httpAttempted": False},
            )
        else:
            await unknown_attempt(
                session,
                workspace_id,
                project_id,
                attempt.id,
                error={"code": "LOADING_SUMMARY_CANCELLED"},
            )


async def _run_summary(
    factory: async_sessionmaker[AsyncSession],
    workspace_id: UUID,
    project_id: UUID,
    operation_id: UUID,
    actor_id: UUID | None,
    source: UploadedMedia,
    duration: float,
    mode: str,
) -> None:
    try:
        async with factory() as session:
            repository = RepairRepository(session)
            project = await repository.project(workspace_id, project_id)
            operation = await repository.operation(workspace_id, project_id, operation_id)
            # The current app uses unlimited policies. Preserve all mandatory-call
            # headroom for older finite budgets rather than spending it on loading UI.
            if mode in {"fixture", "mock"} or not is_unlimited_policy(
                project.context_json.get("p0", {}).get("budgetPolicy")
            ):
                await publish_quick_summary(session, operation, {"status": "unavailable"})
                return
            if not await publish_quick_summary(session, operation, {"status": "pending"}):
                return
            preview = await run_in_threadpool(prepare_quick_preview, source, duration)
            # The main compiler may finish during local media preparation. Reuse
            # the operation lock before reserving the sole optional model call.
            if not await publish_quick_summary(session, operation, {"status": "pending"}):
                return
            # 2.5 Flash explicitly supports disabling thinking; other configured
            # models receive no unsupported hint and no automatic model fallback.
            thinking = 0 if get_gemini_model() == "gemini-2.5-flash" else None
            client = HttpGeminiClient(
                max_attempts=1,
                repair_json=False,
                max_output_tokens=1280,
                timeout_seconds=30,
                thinking_budget=thinking,
            )
            ledger = LedgerGeminiClient(
                session,
                workspace_id,
                project_id,
                operation_id,
                actor_id,
                purpose="loading_summary",
                attempt_namespace="loading_summary",
                client=client,
                metadata={"preview": preview.metadata},
                profile={
                    "maxOutputTokens": 1280,
                    "timeoutSeconds": 30,
                    **({"thinkingBudget": thinking} if thinking is not None else {}),
                },
            )
            system, prompt = summary_prompt(
                duration, sampled_frames=preview.kind == "sampled_frames",
                has_audio=preview.has_audio,
            )
            result = await ledger.generate_json(
                system_instruction=system,
                prompt=prompt,
                media=[
                    {"bytes": item.bytes, "mime_type": item.mime_type} for item in preview.media
                ],
            )
            summary = SourceLoadingSummary.model_validate(result).model_dump(exclude_none=True)
            if not preview.has_audio:
                summary.pop("sourceAudio", None)
            await publish_quick_summary(session, operation, {"status": "completed", **summary})
    except asyncio.CancelledError:
        # Cancellation can arrive after HTTP submission. Reopen the session after
        # rollback/close and retain uncertainty; never refund a submitted request.
        await _settle_cancelled_summary(factory, workspace_id, project_id, operation_id)
        raise
    except Exception as exc:
        logger.warning("loading_summary_unavailable: %s", type(exc).__name__)
        try:
            await _publish(
                factory, workspace_id, project_id, operation_id,
                {"status": "unavailable", "reason": _failure_reason(exc)},
            )
        except Exception as publish_error:
            logger.warning("loading_summary_status_unavailable: %s", type(publish_error).__name__)


def start_loading_summary(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    project_id: UUID,
    operation_id: UUID,
    actor_id: UUID | None,
    source: UploadedMedia,
    duration: float,
    mode: str,
) -> asyncio.Task[None] | None:
    bind = getattr(session, "bind", None)
    if not isinstance(bind, AsyncEngine):
        return None
    factory = async_sessionmaker(bind, expire_on_commit=False)
    return asyncio.create_task(
        _run_summary(
            factory,
            workspace_id,
            project_id,
            operation_id,
            actor_id,
            source,
            duration,
            mode,
        )
    )


async def finish_loading_summary(task: asyncio.Task[None] | None) -> None:
    if task is None:
        return
    if not task.done():
        task.cancel()
        _RECEIPT_SETTLEMENTS.add(task)
        task.add_done_callback(_receipt_settled)
    # Do not cancel again on expiry: the first cancellation may already be
    # recording an uncertain bill. Keep that local settlement alive independently.
    done, _ = await asyncio.wait({task}, timeout=1)
    if done:
        await asyncio.gather(task, return_exceptions=True)


def _receipt_settled(task: asyncio.Task[None]) -> None:
    _RECEIPT_SETTLEMENTS.discard(task)
    if not task.cancelled() and (error := task.exception()) is not None:
        logger.warning("loading_summary_settlement_unavailable: %s", type(error).__name__)
