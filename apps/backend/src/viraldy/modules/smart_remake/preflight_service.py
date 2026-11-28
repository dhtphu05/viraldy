"""Describe a proposed action without uploads, reservations or provider clients."""

from __future__ import annotations

import math
import os
from datetime import UTC, datetime
from decimal import ROUND_CEILING, Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError

from .budget_ledger import usd_amount
from .budget_models import SmartRemakeAttemptModel
from .generation_recovery import (
    attempt_needs_reconciliation,
    is_authorized_unconfirmed_replacement,
)
from .models import SmartRemakeOperationModel
from .preflight_contracts import (
    PreflightBlocker,
    PreflightBudget,
    PreflightCalls,
    PreflightRequest,
    PreflightResponse,
    PreflightScope,
)
from .project_contracts import SmartRemakeBudgetPolicy
from .project_policy import stable_hash
from .repair_repository import RepairRepository

STAGES = ("analysis", "image", "video", "inspection")


def _block(code: str, message: str, action: str = "refresh") -> PreflightBlocker:
    return PreflightBlocker.model_validate(
        {"code": f"SMART_REMAKE_{code}", "message": message, "action": action}
    )


def _authorized_operation_replacement(
    operation: Any, row: Any, attempts: list[Any], action: str | None,
) -> bool:
    if (
        row is None or operation.status != "failed"
        or getattr(operation, "project_id", None) != row.id
        or operation.result_json.get("kind") not in {"render", "repair"}
        or operation.result_json.get("kind") != action
    ):
        return False
    unresolved = [
        attempt for attempt in attempts
        if getattr(attempt, "project_id", None) == row.id
        and getattr(attempt, "workspace_id", None) == getattr(row, "workspace_id", None)
        and (attempt.metadata_json or {}).get("operationId") == str(operation.id)
        and (attempt_needs_reconciliation(attempt)
             or is_authorized_unconfirmed_replacement(attempt))
    ]
    return bool(unresolved) and all(is_authorized_unconfirmed_replacement(a) for a in unresolved)


def _pending(
    operations: list[Any], context: dict[str, Any], *, row: Any = None,
    attempts: list[Any] | None = None, action: str | None = None,
) -> bool:
    for operation in operations:
        result = operation.result_json or {}
        if _authorized_operation_replacement(operation, row, attempts or [], action):
            continue
        if operation.status == "running" or result.get("needsReconciliation"):
            return True
        # Terminal operations can retain submission markers. The ledger below
        # still fences any noncompleted attempt without a settled amount.
        if operation.status == "completed" or (
            operation.status == "failed" and result.get("needsReconciliation") is False
        ):
            continue
        if result.get("phase") == "invoking":
            return True
        for task in result.get("tasks", {}).values():
            if task.get("status") in {"submitting", "submission_unknown", "unknown"}:
                return True
            if task.get("status") == "submitted" and operation.status != "failed":
                return True
        for image in result.get("images", {}).values():
            if image.get("status") in {"submitting", "unknown"}:
                return True
    return False


def _scene(state: dict[str, Any], identity: str | None) -> dict[str, Any] | None:
    return next((scene for scene in state.get("scenes", []) if scene["id"] == identity), None)


def _version(scene: dict[str, Any] | None, identity: str | None) -> dict[str, Any] | None:
    return next(
        (version for version in (scene or {}).get("versions", []) if version["id"] == identity),
        None,
    )


def _inspection_count(
    request: PreflightRequest, state: dict[str, Any], context: dict[str, Any]
) -> tuple[int, int]:
    subject = request.subject
    assert subject is not None
    if subject.kind == "image":
        return 1, 0
    if subject.kind == "assembly":
        assembly = next(
            (
                item
                for item in context.get("p0", {}).get("assemblies", {}).get("records", [])
                if item["id"] == subject.assemblyId
            ),
            None,
        )
        count = len((assembly or {}).get("timeline", {}).get("items", []))
        return max(0, 2 * count - 1), count
    if not _version(_scene(state, subject.sceneId), subject.versionId):
        return 0, 0
    items = (state.get("draftTimeline") or {}).get("items", [])
    index = next(
        (i for i, item in enumerate(items) if item.get("renderUnitId") == subject.sceneId), None
    )
    adjacent = items[max(0, index - 1) : index + 2] if index is not None else []
    neighbors = {
        (item.get("renderUnitId"), item.get("versionId"))
        for item in adjacent
        if item.get("renderUnitId") != subject.sceneId
        and _version(_scene(state, item.get("renderUnitId")), item.get("versionId"))
    }
    return 1 + len(neighbors), 1


def _scope(
    request: PreflightRequest, row: Any | None, blockers: list[PreflightBlocker]
) -> tuple[PreflightScope, PreflightCalls]:
    state, context = (row.state_json, row.context_json) if row is not None else ({}, {})
    plan = context.get("renderPlan") or state.get("renderPlan") or {}
    scenes = state.get("scenes", [])
    groups = plan.get("groups") or [{"renderUnitIds": [scene["id"]]} for scene in scenes]
    duration = state.get("targetDuration") or context.get("p0", {}).get("targetDuration")
    analyzing = request.action in {"analyze", "reanalyze"}
    if analyzing and request.targetDuration is not None:
        duration = request.targetDuration
    source_map = context.get("sourceSceneMap") or state.get("sourceSceneMap") or {}
    sources = source_map.get("scenes", [])
    source_start = source_map.get("sourceStartFrame", 0)
    if analyzing:
        if request.analysisScope == "full_source":
            source_start = 0
            probe = context.get("sourceProbe") or {}
            source_end = context.get("sourceFrameCount") or source_map.get("sourceFrameCount")
            if not source_end:
                seconds = probe.get("videoDurationSeconds") or probe.get("durationSeconds")
                seconds = seconds or request.sourceDurationSeconds
                source_end = round(seconds * 24) if seconds else None
        elif request.referenceStartFrame is not None:
            source_start = request.referenceStartFrame
        if request.analysisScope != "full_source":
            source_end = source_start + int(duration or request.targetDuration or 0) * 24
    else:
        source_end = max((scene["endFrame"] for scene in sources), default=source_start)
    scope = PreflightScope(
        targetDuration=float(duration or request.targetDuration or 0),
        sceneCount=len(sources) if source_map.get("timingMode") == "fit_target" else len(scenes),
        groupCount=len(groups),
        imageCount=0,
        sourceStartFrame=source_start if analyzing or sources else None,
        sourceEndFrame=source_end if analyzing or sources else None,
        analysisScope=request.analysisScope if analyzing else None,
    )
    calls = PreflightCalls()
    if analyzing:
        owned_duration = context.get("p0", {}).get("targetDuration")
        if owned_duration is not None and duration != owned_duration:
            blockers.append(
                _block(
                    "INTAKE_DURATION_CHANGED",
                    "Thêm lại video mẫu để tạo dự án với thời lượng mới.",
                    "new_project",
                )
            )
        scope = scope.model_copy(update={"sceneCount": 0, "groupCount": 0})
        # Source + optional cut semantics + product lock, plus one loading summary.
        calls = PreflightCalls(analysis=4, total=4)
    elif request.action == "inspect":
        assert request.subject is not None
        count, scene_count = _inspection_count(request, state, context)
        if count == 0:
            blockers.append(
                _block(
                    "INSPECTION_SUBJECT_NOT_FOUND",
                    "Đối tượng kiểm tra không còn trong dự án. Hãy làm mới.",
                )
            )
        scope = scope.model_copy(
            update={
                "sceneCount": scene_count,
                "groupCount": 0,
                "imageCount": int(request.subject.kind == "image"),
            }
        )
        calls = PreflightCalls(inspection=count, total=count)
    elif not plan or not scenes:
        blockers.append(_block("PLAN_REQUIRED", "Cần cập nhật kịch bản trước khi tạo video."))
    elif (
        request.action == "render"
        and state.get("schemaVersion") == 2
        and not any(block.action == "reconcile" for block in blockers)
        and (
            plan.get("groupingPolicy") != "fixed_provider_windows"
            or duration not in {8, 12, 16}
            or (duration == 12 and (plan.get("videoModel") != "wan/3-0-video"
                                   or plan.get("audioRequired") is not True))
            or len(groups) != (2 if duration == 12 else duration // 8)
            or any(
                group.get("rawDurationFrames") != (144 if duration == 12 else 192)
                or group.get("targetDurationFrames") != (144 if duration == 12 else 192)
                for group in groups
            )
        )
    ):
        blockers.append(_block(
            "PROVIDER_PLAN_UPDATE_REQUIRED",
            "Cập nhật kịch bản để dùng đầy đủ các clip theo thời lượng đã chọn.",
        ))
    elif request.action == "repair":
        scene = _scene(state, request.sceneId)
        if scene is None or scene.get("activeVersionId") != request.baseVersionId:
            blockers.append(_block("VERSION_CONFLICT", "Cảnh đã thay đổi. Hãy làm mới lựa chọn."))
        elif not request.baseVersionId or not _version(scene, request.baseVersionId):
            blockers.append(_block(
                "BASE_VERSION_REQUIRED", "Cảnh chưa có video để sửa. Hãy tạo video trước.",
            ))
        elif request.repairIntent is not None:
            from .repair_intent import repair_base_scene

            try:
                repair_base_scene(row, scene)
            except (AppError, KeyError, ValueError, TypeError):
                blockers.append(_block(
                    "EXPECTATIONS_REQUIRED",
                    "Cần cập nhật kịch bản trước khi sửa cảnh với đầy đủ thông tin tham chiếu.",
                ))
        unit: dict[str, Any] = next(
            (unit for unit in plan.get("units", []) if unit["id"] == request.sceneId), {}
        )
        image_count = 2 if plan.get("imageModel") else 0
        scope = scope.model_copy(
            update={
                "sceneCount": 1,
                "groupCount": 1,
                "imageCount": image_count,
                "sceneId": request.sceneId,
                "baseVersionId": request.baseVersionId,
                "targetDuration": unit.get(
                    "rawDurationFrames", (scene or {}).get("rawDurationFrames", 192)
                )
                / 24,
            }
        )
        calls = PreflightCalls(
            analysis=int(request.repairIntent is not None),
            image=image_count, video=1,
            total=1 + image_count + int(request.repairIntent is not None),
        )
    else:
        image_count = 2 * len(groups) if plan.get("imageModel") else 0
        scope = scope.model_copy(update={"imageCount": image_count})
        calls = PreflightCalls(
            image=image_count,
            video=len(groups),
            total=len(groups) + image_count,
        )
    return scope, calls


def _budget(
    calls: PreflightCalls,
    row: Any | None,
    attempts: list[Any],
    *,
    mode: str,
    bounds: dict[str, str | None],
    now: datetime,
    blockers: list[PreflightBlocker],
    unlimited: bool = False,
) -> PreflightBudget | None:
    if unlimited:
        return _unlimited_costs(calls, attempts, mode=mode, bounds=bounds)
    additional = Decimal(0)
    if mode not in {"fixture", "mock"}:
        try:
            for stage in STAGES:
                count = getattr(calls, stage)
                if count:
                    ceiling = usd_amount(bounds.get(stage))
                    if ceiling <= 0:
                        raise ValueError("A positive stage ceiling is required.")
                    additional += ceiling * count
        except (AppError, ValueError):
            blockers.append(
                _block(
                    "COST_BOUND_REQUIRED",
                    "Dịch vụ chưa có đủ giới hạn chi phí. Vui lòng kiểm tra cấu hình.",
                    "configure",
                )
            )
            return None
    policy = row.context_json.get("p0", {}).get("budgetPolicy", {}) if row else {}
    elapsed = 0
    if policy.get("startedAt"):
        try:
            started = datetime.fromisoformat(policy["startedAt"])
            elapsed = max(0, math.ceil((now - started).total_seconds()))
        except (TypeError, ValueError):
            blockers.append(_block("BUDGET_INVALID", "Thông tin thời gian phiên không hợp lệ."))
            return None
    duration = elapsed + 1800
    attempts_count = len(attempts) + calls.total
    if duration > 86400 or attempts_count > 1000:
        blockers.append(
            _block(
                "BUDGET_SESSION_EXHAUSTED",
                "Phiên này đã đạt giới hạn. Hãy bắt đầu dự án mới.",
                "new_project",
            )
        )
        return None
    known = sum((a.actual_usd for a in attempts if a.actual_usd is not None), Decimal(0))
    reserved = sum((a.estimated_usd for a in attempts if a.actual_usd is None), Decimal(0))
    # Approval contracts accept six decimals; round UP so a valid policy covers every cent.
    minimum = (
        max(Decimal("0.01"), known + reserved + additional)
        .quantize(Decimal("0.000001"), rounding=ROUND_CEILING)
        .normalize()
    )
    recommended_cap = (
        max(usd_amount(policy.get("capUsd", "0")), minimum)
        .quantize(Decimal("0.000001"), rounding=ROUND_CEILING)
        .normalize()
    )
    return PreflightBudget(
        knownActualUsd=format(known, "f"),
        reservedUsd=format(reserved, "f"),
        exposureUsd=format(known + reserved, "f"),
        additionalReservationUsd=format(additional, "f"),
        minimumCapUsd=format(minimum, "f"),
        minimumMaxAttempts=max(1, attempts_count),
        minimumDurationSeconds=duration,
        recommended=SmartRemakeBudgetPolicy(
            capUsd=format(recommended_cap, "f"),
            maxAttempts=max(policy.get("maxAttempts", 1), attempts_count, 1),
            maxDurationSeconds=max(
                policy.get("maxDurationSeconds", 0), min(86400, math.ceil(duration / 60) * 60 + 60)
            ),
        ),
    )


def _unlimited_costs(
    calls: PreflightCalls,
    attempts: list[Any],
    *,
    mode: str,
    bounds: dict[str, str | None],
) -> PreflightBudget:
    """Report costs without turning an unpriced or long-running action into a grant gate."""
    known = sum((a.actual_usd for a in attempts if a.actual_usd is not None), Decimal(0))
    unknown = sum(
        a.actual_usd is None
        and (getattr(a, "metadata_json", {}) or {}).get("costEstimate", {}).get("status")
        == "unknown"
        for a in attempts
    )
    reserved = sum((a.estimated_usd for a in attempts if a.actual_usd is None), Decimal(0))
    additional: Decimal | None = Decimal(0)
    if mode not in {"fixture", "mock"}:
        for stage in STAGES:
            count = getattr(calls, stage)
            if not count:
                continue
            try:
                ceiling = usd_amount(bounds.get(stage))
                if ceiling <= 0:
                    raise ValueError("Unknown estimate")
            except (AppError, ValueError):
                additional = None
                break
            additional += count * ceiling
    return PreflightBudget(
        knownActualUsd=format(known, "f"),
        reservedUsd=None if unknown else format(reserved, "f"),
        exposureUsd=None if unknown else format(known + reserved, "f"),
        additionalReservationUsd=format(additional, "f") if additional is not None else None,
        minimumCapUsd=None, minimumMaxAttempts=None, minimumDurationSeconds=None,
        unknownCostAttempts=unknown,
        recommended=SmartRemakeBudgetPolicy(mode="unlimited"),
    )


def calculate_preflight(
    request: PreflightRequest,
    *,
    mode: str,
    bounds: dict[str, str | None],
    row: Any | None = None,
    attempts: list[Any] | None = None,
    operations: list[Any] | None = None,
    now: datetime | None = None,
) -> PreflightResponse:
    rows, operations = attempts or [], operations or []
    blockers: list[PreflightBlocker] = []
    context = row.context_json if row else {}
    if row is not None and row.revision != request.expectedRevision:
        blockers.append(
            _block("REVISION_CONFLICT", "Dự án đã thay đổi. Hãy làm mới trước khi tiếp tục.")
        )
    if _pending(operations, context, row=row, attempts=rows, action=request.action) or any(
        attempt_needs_reconciliation(a) for a in rows
    ):
        blockers.append(
            _block(
                "ATTEMPT_RECONCILIATION_REQUIRED",
                "Tác vụ trước đang chạy hoặc chưa rõ kết quả. Hãy kiểm tra trạng thái.",
                "reconcile",
            )
        )
    scope, calls = _scope(request, row, blockers)
    budget = _budget(
        calls, row, rows, mode=mode, bounds=bounds, now=now or datetime.now(UTC), blockers=blockers,
        unlimited=request.budgetMode == "unlimited" or (
            request.budgetMode is None
            and context.get("p0", {}).get("budgetPolicy", {}).get("mode") == "unlimited"
        ),
    )
    fingerprint = {
        "request": request.model_dump(mode="json", exclude_none=True),
        "mode": mode,
        "state": row.state_json if row else None,
        "context": context,
        "revision": row.revision if row else None,
        "bounds": {stage: bounds.get(stage) for stage in STAGES if getattr(calls, stage)},
        "attempts": [
            {
                "id": str(a.id),
                "status": a.status,
                "stage": a.stage,
                "actual": str(a.actual_usd) if a.actual_usd is not None else None,
                "reserved": str(a.estimated_usd),
            }
            for a in rows
        ],
        "operations": [{"status": op.status, "result": op.result_json} for op in operations],
    }
    return PreflightResponse(
        action=request.action,
        projectId=str(row.id) if row else None,
        revision=row.revision if row else None,
        contextHash=stable_hash(fingerprint),
        mode=mode,
        scope=scope,
        calls=calls,
        budget=budget,
        blockers=blockers,
    )


async def preflight_action(
    session: AsyncSession, settings: Settings, workspace_id: UUID, request: PreflightRequest
) -> PreflightResponse:
    row, attempts, operations = None, [], []
    if request.projectId:
        project_id = UUID(request.projectId)
        row = await RepairRepository(session).project(workspace_id, project_id)
        attempts = list(
            (
                await session.scalars(
                    select(SmartRemakeAttemptModel)
                    .where(
                        SmartRemakeAttemptModel.project_id == project_id,
                        SmartRemakeAttemptModel.workspace_id == workspace_id,
                    )
                    .order_by(SmartRemakeAttemptModel.created_at, SmartRemakeAttemptModel.id)
                )
            ).all()
        )
        operations = list(
            (
                await session.scalars(
                    select(SmartRemakeOperationModel)
                    .where(
                        SmartRemakeOperationModel.project_id == project_id,
                    )
                    .order_by(SmartRemakeOperationModel.created_at, SmartRemakeOperationModel.id)
                )
            ).all()
        )
    return calculate_preflight(
        request,
        mode=settings.ai_mode.strip().lower(),
        row=row,
        attempts=attempts,
        operations=operations,
        bounds={stage: os.getenv(f"SMART_REMAKE_P0_MAX_{stage.upper()}_USD") for stage in STAGES},
    )
