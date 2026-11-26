"""Durable reservations. Every mutation commits before callers may contact a provider.

Bounded policies reserve server-controlled ceilings. Unlimited policies retain costs and
unknown estimates without treating missing provider bills as zero cost.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.shared.errors.base import AppError, ConflictError, NotFoundError

from .budget_models import SmartRemakeAttemptModel as Attempt
from .generation_recovery import (
    authorized_unconfirmed_replacement_keys,
    is_authorized_unconfirmed_replacement,
    is_completed_analysis_response,
    is_known_image_rejection,
    is_known_video_rejection,
)
from .models import SmartRemakeOperationModel, SmartRemakeProjectModel

STAGES = frozenset({"analysis", "image", "video", "inspection", "compose"})
PURPOSES = frozenset({"initial", "repair", "recheck", "loading_summary"})


def usd_amount(value: Any) -> Decimal:
    try:
        if not isinstance(value, str | Decimal | int) or isinstance(value, bool):
            raise ValueError
        amount = Decimal(value)
        if (
            not amount.is_finite()
            or amount < 0
            or amount >= Decimal("10000000000")
            or amount != amount.quantize(Decimal("0.00000001"))
        ):
            raise ValueError
        return amount
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise AppError(
            "SMART_REMAKE_BUDGET_INVALID", "USD must be an exact nonnegative decimal."
        ) from exc


def normalize_policy(policy: dict[str, Any]) -> dict[str, Any]:
    if policy.get("mode") not in {None, "limited", "unlimited"}:
        raise AppError("SMART_REMAKE_BUDGET_INVALID", "Unsupported budget policy mode.")
    if is_unlimited_policy(policy):
        return {
            "mode": "unlimited",
            **({"startedAt": policy["startedAt"]} if policy.get("startedAt") else {}),
        }
    amount = usd_amount(policy.get("capUsd"))
    for name in ("maxAttempts", "maxDurationSeconds"):
        if type(policy.get(name)) is not int or not 0 < policy[name] <= 1_000_000:
            raise AppError("SMART_REMAKE_BUDGET_INVALID", f"A positive {name} is required.")
    if amount <= 0:
        raise AppError("SMART_REMAKE_BUDGET_INVALID", "A positive budget cap is required.")
    return {**policy, "capUsd": format(amount, "f")}


def is_unlimited_policy(policy: dict[str, Any] | None) -> bool:
    policy = policy or {}
    cap = policy.get("capUsd")
    return policy.get("mode") == "unlimited" or (
        policy.get("mode") is None and (cap is None or isinstance(cap, str) and not cap.strip())
    )


def reservation_estimate(
    policy: dict[str, Any] | None, raw_bound: str | None, *, error_code: str, message: str
) -> tuple[Decimal, dict[str, Any]]:
    """An unavailable estimate is explicit metadata, never a zero-cost claim."""
    unlimited = is_unlimited_policy(normalize_policy(policy or {}))
    if raw_bound and raw_bound.strip():
        try:
            amount = usd_amount(raw_bound)
        except AppError:
            if not unlimited:
                raise
        else:
            if amount > 0:
                return amount, {}
    if not unlimited:
        raise AppError(error_code, message, 409)
    return Decimal(0), {
        "costEstimate": {"status": "unknown", "reason": "server_price_unconfigured"}
    }


def _unknown_estimate(row: Attempt) -> bool:
    return bool((row.metadata_json or {}).get("costEstimate", {}).get("status") == "unknown")


async def _project(
    session: AsyncSession, workspace_id: UUID, project_id: UUID, *, lock: bool = False
) -> SmartRemakeProjectModel:
    statement = (
        select(SmartRemakeProjectModel)
        .where(
            SmartRemakeProjectModel.id == project_id,
            SmartRemakeProjectModel.workspace_id == workspace_id,
        )
        .execution_options(populate_existing=True)
    )
    if lock:
        statement = statement.with_for_update()
    project = (await session.execute(statement)).scalar_one_or_none()
    if project is None:
        raise NotFoundError("SMART_REMAKE_PROJECT_NOT_FOUND", "Smart Remake project was not found.")
    return project


async def _attempts(session: AsyncSession, project_id: UUID) -> list[Attempt]:
    return list(
        (
            await session.execute(
                select(Attempt)
                .where(Attempt.project_id == project_id)
                .order_by(Attempt.created_at, Attempt.id)
                .execution_options(populate_existing=True)
            )
        ).scalars()
    )


def _exposure(rows: list[Attempt]) -> Decimal:
    return sum(
        (row.actual_usd if row.actual_usd is not None else row.estimated_usd for row in rows),
        Decimal(0),
    )


async def initialize_budget(
    session: AsyncSession, workspace_id: UUID, project_id: UUID, policy: dict[str, Any]
) -> dict[str, Any]:
    normalized = normalize_policy(policy)
    project = await _project(session, workspace_id, project_id, lock=True)
    rows = await _attempts(session, project_id)
    if not is_unlimited_policy(normalized) and (
        any(_unknown_estimate(row) and row.actual_usd is None for row in rows)
        or _exposure(rows) > usd_amount(normalized["capUsd"])
        or len(rows) > normalized["maxAttempts"]
    ):
        await session.rollback()
        raise AppError(
            "SMART_REMAKE_BUDGET_BELOW_EXPOSURE", "Budget cannot exclude existing attempts."
        )
    p0 = project.context_json.get("p0", {})
    previous = p0.get("budgetPolicy", {})
    normalized = {
        **normalized,
        "startedAt": previous.get("startedAt", datetime.now(UTC).isoformat()),
    }
    project.context_json = {**project.context_json, "p0": {**p0, "budgetPolicy": normalized}}
    await session.commit()
    return normalized


async def _authorized_replacement_collision(
    session: AsyncSession, workspace_id: UUID, project_id: UUID, previous: Attempt,
    *, actor_id: UUID | None, idempotency_key: str, metadata: dict[str, Any] | None,
) -> bool:
    replacement_keys = authorized_unconfirmed_replacement_keys(previous)
    if not replacement_keys or actor_id != previous.actor_id:
        return False
    incoming = metadata or {}
    try:
        operation_id = UUID(incoming.get("operationId"))
    except (TypeError, ValueError, AttributeError):
        return False
    slot = incoming.get("slot")
    if (
        str(operation_id) == previous.metadata_json["operationId"]
        or not isinstance(slot, str)
        or idempotency_key != f"{operation_id}:{slot}"
    ):
        return False
    operation = SmartRemakeOperationModel
    owned = await session.scalar(
        select(operation.result_json)
        .join(SmartRemakeProjectModel, SmartRemakeProjectModel.id == operation.project_id)
        .where(
            operation.id == operation_id, operation.project_id == project_id,
            SmartRemakeProjectModel.workspace_id == workspace_id,
            operation.idempotency_key.in_(sorted(replacement_keys)),
            operation.status == "running",
            operation.result_json["actorId"].as_string() == str(actor_id),
            operation.result_json["kind"].as_string().in_(("render", "repair")),
        )
    )
    if not isinstance(owned, dict):
        return False
    if owned.get("kind") == "repair":
        return slot == previous.metadata_json.get("slot") == f"video:{owned.get('sceneIndex')}"
    if owned.get("kind") != "render" or not slot.startswith("video:group:"):
        return False
    try:
        group_id = str(UUID(slot.removeprefix("video:group:")))
    except ValueError:
        return False
    groups = (owned.get("renderPlan") or {}).get("groups")
    return (
        slot == f"video:group:{group_id}" and isinstance(groups, list)
        and any(isinstance(group, dict) and group.get("id") == group_id for group in groups)
    )


async def reserve_attempt(
    session: AsyncSession,
    workspace_id: UUID,
    project_id: UUID,
    *,
    idempotency_key: str,
    request_hash: str,
    stage: str,
    reservation_usd: str | Decimal,
    actor_id: UUID | None,
    provider: str,
    model: str,
    purpose: str = "initial",
    profile: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> tuple[Attempt, bool]:
    amount = usd_amount(reservation_usd)
    if (
        stage not in STAGES
        or purpose not in PURPOSES
        or not 0 < len(idempotency_key) <= 200
        or not 0 < len(request_hash) <= 64
        or not provider
        or not model
        or len(provider) > 100
        or len(model) > 200
    ):
        raise AppError("SMART_REMAKE_ATTEMPT_INVALID", "A valid priced attempt intent is required.")
    project = await _project(session, workspace_id, project_id, lock=True)
    rows = await _attempts(session, project_id)
    existing = next((row for row in rows if row.idempotency_key == idempotency_key), None)
    if existing:
        pricing_drift = is_unlimited_policy(existing.policy_json) or is_unlimited_policy(
            project.context_json.get("p0", {}).get("budgetPolicy")
        )
        existing_metadata = {
            key: value for key, value in existing.metadata_json.items()
            if key not in {"replacementAuthorization", "additionalReplacementAuthorizations"}
        }
        incoming_metadata = {
            key: value for key, value in (metadata or {}).items()
            if key not in {"replacementAuthorization", "additionalReplacementAuthorizations"}
        }
        if pricing_drift:
            existing_metadata = {
                key: value for key, value in existing_metadata.items() if key != "costEstimate"
            }
            incoming_metadata = {
                key: value for key, value in incoming_metadata.items() if key != "costEstimate"
            }
        matches = (
            existing.request_hash == request_hash
            and existing.stage == stage
            and existing.purpose == purpose
            and (existing.estimated_usd == amount or pricing_drift)
            and existing.provider == provider
            and existing.model == model
            and existing.profile_json == (profile or {})
            and existing_metadata == incoming_metadata
            and existing.actor_id == actor_id
        )
        await session.commit()
        if not matches:
            raise ConflictError(
                "SMART_REMAKE_IDEMPOTENCY_CONFLICT", "Key belongs to a different attempt."
            )
        return existing, False
    policy = normalize_policy(project.context_json.get("p0", {}).get("budgetPolicy") or {})
    unlimited = is_unlimited_policy(policy)
    unknown_estimate = (metadata or {}).get("costEstimate", {}).get("status") == "unknown"
    if amount == 0 and stage != "compose" and not (unlimited and unknown_estimate):
        await session.rollback()
        raise AppError(
            "SMART_REMAKE_ATTEMPT_INVALID", "A priced or explicitly unknown estimate is required."
        )
    if not policy.get("startedAt"):
        policy = {**policy, "startedAt": datetime.now(UTC).isoformat()}
        p0 = project.context_json.get("p0", {})
        project.context_json = {**project.context_json, "p0": {**p0, "budgetPolicy": policy}}
    if not unlimited and len(rows) >= policy["maxAttempts"]:
        await session.rollback()
        raise AppError("SMART_REMAKE_ATTEMPT_LIMIT", "Budget attempt limit has been reached.", 429)
    if not unlimited and (
        datetime.now(UTC) - datetime.fromisoformat(policy["startedAt"])
    ).total_seconds() >= policy["maxDurationSeconds"]:
        await session.rollback()
        raise AppError("SMART_REMAKE_BUDGET_EXPIRED", "Approved execution time has expired.", 409)
    if not unlimited and (
        any(_unknown_estimate(row) and row.actual_usd is None for row in rows)
        or _exposure(rows) + amount > usd_amount(policy["capUsd"])
    ):
        await session.rollback()
        raise AppError(
            "SMART_REMAKE_BUDGET_EXCEEDED", "Attempt exceeds approved budget exposure.", 429
        )
    uncertain = [
        row for row in rows if (
        (row.request_hash == request_hash or is_authorized_unconfirmed_replacement(row))
        and row.stage == stage
        and row.provider == provider
        and row.model == model
        and row.actual_usd is None
        and row.status != "completed"
        and not is_known_image_rejection(row)
        and not is_known_video_rejection(row)
        and not is_completed_analysis_response(row)
        )
    ]
    for previous in uncertain:
        if not await _authorized_replacement_collision(
            session, workspace_id, project_id, previous, actor_id=actor_id,
            idempotency_key=idempotency_key, metadata=metadata,
        ):
            await session.rollback()
            raise ConflictError(
                "SMART_REMAKE_ATTEMPT_RECONCILIATION_REQUIRED",
                "An uncertain attempt for these inputs must be reconciled "
                "before another submission.",
            )
    attempt = Attempt(
        project_id=project_id,
        workspace_id=workspace_id,
        actor_id=actor_id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        stage=stage,
        purpose=purpose,
        status="reserved",
        provider=provider,
        model=model,
        estimated_usd=amount,
        profile_json=profile or {},
        metadata_json=metadata or {},
        policy_json=policy,
        usage_json={},
        receipt_json={},
        error_json={},
    )
    session.add(attempt)
    await session.commit()
    return attempt, True


async def _locked_attempt(
    session: AsyncSession, workspace_id: UUID, project_id: UUID, attempt_id: UUID
) -> Attempt:
    await _project(session, workspace_id, project_id, lock=True)
    row = (
        await session.execute(
            select(Attempt)
            .where(
                Attempt.id == attempt_id,
                Attempt.project_id == project_id,
                Attempt.workspace_id == workspace_id,
            )
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if row is None:
        await session.rollback()
        raise NotFoundError("SMART_REMAKE_ATTEMPT_NOT_FOUND", "Attempt was not found.")
    return row


async def mark_submitted(
    session: AsyncSession,
    workspace_id: UUID,
    project_id: UUID,
    attempt_id: UUID,
    *,
    provider_task_id: str | None = None,
    receipt: dict[str, Any] | None = None,
) -> Attempt:
    row = await _locked_attempt(session, workspace_id, project_id, attempt_id)
    if row.provider_task_id and provider_task_id and row.provider_task_id != provider_task_id:
        await session.rollback()
        raise ConflictError("SMART_REMAKE_RECEIPT_CONFLICT", "Attempt has another provider task.")
    if row.status == "failed" and row.actual_usd == 0:
        await session.rollback()
        raise ConflictError("SMART_REMAKE_ATTEMPT_CLOSED", "Unsubmitted attempt is already closed.")
    row.provider_task_id = provider_task_id or row.provider_task_id
    row.submitted_at = row.submitted_at or datetime.now(UTC)
    if row.status == "reserved":
        row.status = "submitted"
    row.receipt_json = {**row.receipt_json, **(receipt or {})}
    await session.commit()
    return row


async def complete_attempt(
    session: AsyncSession,
    workspace_id: UUID,
    project_id: UUID,
    attempt_id: UUID,
    *,
    actual_usd: str | Decimal | None = None,
    receipt: dict[str, Any] | None = None,
    usage: dict[str, Any] | None = None,
) -> Attempt:
    row = await _locked_attempt(session, workspace_id, project_id, attempt_id)
    actual = None if actual_usd is None else usd_amount(actual_usd)
    if actual is not None and not receipt and row.stage != "compose":
        await session.rollback()
        raise AppError(
            "SMART_REMAKE_BILLED_RECEIPT_REQUIRED", "Billed amounts require provider evidence."
        )
    if row.actual_usd is not None and actual is not None and row.actual_usd != actual:
        await session.rollback()
        raise ConflictError(
            "SMART_REMAKE_RECEIPT_CONFLICT", "Attempt already has another billed amount."
        )
    row.actual_usd = row.actual_usd if actual is None else actual
    row.receipt_json = {**row.receipt_json, **(receipt or {})}
    row.usage_json = {**row.usage_json, **(usage or {})}
    row.status = "completed"
    row.completed_at = row.completed_at or datetime.now(UTC)
    await session.commit()
    return row


async def fail_attempt(
    session: AsyncSession,
    workspace_id: UUID,
    project_id: UUID,
    attempt_id: UUID,
    *,
    error: dict[str, Any] | None = None,
    definitely_not_submitted: bool = False,
    actual_usd: str | Decimal | None = None,
    receipt: dict[str, Any] | None = None,
    usage: dict[str, Any] | None = None,
    preflight_rejected: bool = False,
) -> Attempt:
    row = await _locked_attempt(session, workspace_id, project_id, attempt_id)
    if row.status == "completed":
        await session.commit()
        return row
    actual = None if actual_usd is None else usd_amount(actual_usd)
    if actual is not None and not receipt and row.stage != "compose":
        await session.rollback()
        raise AppError(
            "SMART_REMAKE_BILLED_RECEIPT_REQUIRED", "Billed amounts require provider evidence."
        )
    if row.actual_usd is not None and actual is not None and row.actual_usd != actual:
        await session.rollback()
        raise ConflictError(
            "SMART_REMAKE_RECEIPT_CONFLICT", "Attempt already has another billed amount."
        )
    if actual is not None:
        row.actual_usd = actual
    if definitely_not_submitted:
        # Wrappers mark local submission intent before their final policy read.
        # Explicit internal proof may cancel only a marker with no remote facts;
        # an intent hash is local metadata, never a provider/billing receipt.
        local_receipts = all(
            not value or (set(value) == {"intentHash"} and value["intentHash"] == row.request_hash)
            for value in (row.receipt_json, receipt or {})
        )
        no_remote_evidence = (
            local_receipts
            and not row.provider_task_id
            and not row.usage_json
            and not usage
            and row.actual_usd in (None, Decimal(0))
        )
        local_marker = (
            preflight_rejected
            and no_remote_evidence
            and (
                row.status == "submitted"
                and row.actual_usd is None
                or row.status == "failed"
                and row.actual_usd == 0
                and row.error_json.get("httpAttempted") is False
            )
        )
        if (
            not no_remote_evidence
            or (row.submitted_at and not local_marker)
            or (row.status not in {"reserved", "failed"} and not local_marker)
        ):
            await session.rollback()
            raise ConflictError(
                "SMART_REMAKE_BILLING_UNCERTAIN", "Submitted attempt cannot be refunded locally."
            )
        row.actual_usd = Decimal(0)
    row.status = "failed"
    row.error_json = {**row.error_json, **(error or {})}
    row.receipt_json = {**row.receipt_json, **(receipt or {})}
    row.usage_json = {**row.usage_json, **(usage or {})}
    row.completed_at = row.completed_at or datetime.now(UTC)
    await session.commit()
    return row


async def unknown_attempt(
    session: AsyncSession,
    workspace_id: UUID,
    project_id: UUID,
    attempt_id: UUID,
    *,
    error: dict[str, Any] | None = None,
    receipt: dict[str, Any] | None = None,
    usage: dict[str, Any] | None = None,
) -> Attempt:
    row = await _locked_attempt(session, workspace_id, project_id, attempt_id)
    if row.status not in {"completed", "failed"}:
        row.status = "unknown"
    row.error_json = {**row.error_json, **(error or {})}
    row.receipt_json = {**row.receipt_json, **(receipt or {})}
    row.usage_json = {**row.usage_json, **(usage or {})}
    await session.commit()
    return row


def present_attempt(row: Attempt) -> dict[str, Any]:
    unpriced = _unknown_estimate(row)
    return {
        "id": str(row.id),
        "workspaceId": str(row.workspace_id),
        "projectId": str(row.project_id),
        "actorId": str(row.actor_id) if row.actor_id else None,
        "idempotencyKey": row.idempotency_key,
        "requestHash": row.request_hash,
        "stage": row.stage,
        "purpose": row.purpose,
        "status": row.status,
        "provider": row.provider,
        "model": row.model,
        "profile": row.profile_json,
        "metadata": row.metadata_json,
        "policy": row.policy_json,
        "usage": row.usage_json,
        "receipt": row.receipt_json,
        "providerTaskId": row.provider_task_id,
        "estimatedUsd": None if unpriced else format(row.estimated_usd, "f"),
        "estimateStatus": "unknown" if unpriced else "known",
        "actualUsd": format(row.actual_usd, "f") if row.actual_usd is not None else None,
        "reservedUsd": (
            None if unpriced and row.actual_usd is None
            else format(row.estimated_usd if row.actual_usd is None else Decimal(0), "f")
        ),
        "costStatus": "unknown" if row.actual_usd is None else "actual",
        "error": row.error_json,
        "createdAt": row.created_at.isoformat(),
        "submittedAt": row.submitted_at.isoformat() if row.submitted_at else None,
        "completedAt": row.completed_at.isoformat() if row.completed_at else None,
    }


async def list_attempts(
    session: AsyncSession, workspace_id: UUID, project_id: UUID
) -> list[dict[str, Any]]:
    await _project(session, workspace_id, project_id)
    return [present_attempt(row) for row in await _attempts(session, project_id)]


async def get_attempt(
    session: AsyncSession, workspace_id: UUID, project_id: UUID, attempt_id: UUID
) -> Attempt:
    row = await _locked_attempt(session, workspace_id, project_id, attempt_id)
    await session.commit()
    return row


async def budget_summary(
    session: AsyncSession, workspace_id: UUID, project_id: UUID
) -> dict[str, Any]:
    project = await _project(session, workspace_id, project_id)
    rows = await _attempts(session, project_id)
    policy = project.context_json.get("p0", {}).get("budgetPolicy")
    known = sum((row.actual_usd for row in rows if row.actual_usd is not None), Decimal(0))
    reserved = sum((row.estimated_usd for row in rows if row.actual_usd is None), Decimal(0))
    unknown = sum(row.actual_usd is None for row in rows)
    unknown_estimates = sum(_unknown_estimate(row) for row in rows)
    unknown_reservations = any(
        _unknown_estimate(row) and row.actual_usd is None for row in rows
    )
    known_estimates = sum(
        (row.estimated_usd for row in rows if not _unknown_estimate(row)), Decimal(0)
    )
    return {
        "policy": policy,
        "attemptCount": len(rows),
        "unknownAttemptCount": unknown,
        "unknownEstimateAttemptCount": unknown_estimates,
        "knownEstimatedUsd": format(known_estimates, "f"),
        "knownExposureUsd": format(known + reserved, "f"),
        "estimatedUsd": None if unknown_estimates else format(known_estimates, "f"),
        "knownActualUsd": format(known, "f"),
        "actualUsd": None if unknown else format(known, "f"),
        "reservedUsd": None if unknown_reservations else format(reserved, "f"),
        "exposureUsd": None if unknown_reservations else format(known + reserved, "f"),
        "remainingUsd": format(
            max(Decimal(0), usd_amount(policy["capUsd"]) - known - reserved), "f"
        )
        if policy and not is_unlimited_policy(policy) and not unknown_reservations
        else None,
        "status": "needs_reconciliation" if unknown else "settled",
    }
