"""Policy and durable ledger boundary for paid image and video generation."""

from __future__ import annotations

import hashlib
from typing import Any, cast

from viraldy.shared.errors.base import AppError

from .engine.kie_client import (
    _PHYSICAL_KIE_CLIENT,
    _PHYSICAL_KIE_CREATE_TASK,
    _PHYSICAL_KIE_GET_TASK,
)
from .engine.openai_images import _PHYSICAL_OPENAI_IMAGE_CLIENT, _PHYSICAL_OPENAI_IMAGE_EDIT
from .engine.schemas import UploadedMedia
from .provider_execution import bind_execution_evidence, safe_provider_identifier

_PHYSICAL_CALLS = {
    "openai.images.edit": (
        _PHYSICAL_OPENAI_IMAGE_CLIENT, "edit", _PHYSICAL_OPENAI_IMAGE_EDIT,
    ),
    "kie.tasks.create": (_PHYSICAL_KIE_CLIENT, "create_task", _PHYSICAL_KIE_CREATE_TASK),
    "kie.tasks.get": (_PHYSICAL_KIE_CLIENT, "get_task", _PHYSICAL_KIE_GET_TASK),
}


def generation_execution_receipt(
    client: Any,
    *,
    attempt_id: str | None,
    request_hash: str,
    provider: str,
    model: str,
    operation: str,
    request_id: str | None = None,
    task_id: str | None = None,
) -> dict[str, Any]:
    """Consume only the current original physical method's private witness."""
    expected = _PHYSICAL_CALLS.get(operation)
    if (
        attempt_id is None
        or expected is None
        or type(client) is not expected[0]
        or getattr(getattr(client, expected[1], None), "__func__", None) is not expected[2]
        or (provider == "kie" and task_id is not None and not safe_provider_identifier(task_id))
    ):
        return {}
    witness = getattr(client, "last_execution_evidence", None)
    cast(Any, client).last_execution_evidence = None
    if getattr(witness, "operation", None) != operation:
        return {}
    proof = bind_execution_evidence(
        witness, attempt_id=attempt_id, request_hash=request_hash,
        provider=provider, model=model,
        request_id=request_id or getattr(client, "last_request_id", None), task_id=task_id,
    )
    return {"executionEvidence": proof} if proof is not None else {}


async def require_generation_policy(repair: Any, row: Any) -> None:
    # A live job may be resumed by a worker restarted in offline mode. Check
    # before uploads, task polls and all physical generation calls.
    mode = getattr(getattr(repair, "settings", None), "ai_mode", None)
    if mode is not None and mode.strip().lower() in {"fixture", "mock"}:
        raise AppError(
            "SMART_REMAKE_FIXTURE_MODE", "Live rendering is disabled in fixture mode.", 409
        )
    # Missing settings/mode occur only on legacy in-memory test doubles.
    live = mode is not None
    if row.context_json.get("p0") is not None or live:
        from .project_intake import assert_input_binding
        from .project_policy import assert_project_policy

        row = await repair.repository.project(repair.workspace_id, row.id)
        assert_project_policy(row, purpose="generation")
        await assert_input_binding(row, repair.media)
        # Release the read transaction before uploads, polls or model calls.
        from sqlalchemy.ext.asyncio import AsyncSession

        session = getattr(repair.repository, "session", None)
        if isinstance(session, AsyncSession):
            await session.commit()


async def character_reference(repair: Any, row: Any) -> UploadedMedia | None:
    context = row.context_json
    if not context.get("characterKey"):
        return None
    data = await repair.media.read(context["characterKey"])
    if hashlib.sha256(data).hexdigest() != context.get("characterMediaHash"):
        raise AppError(
            "SMART_REMAKE_IMAGE_ASSET_INVALID",
            "The retained character reference changed. Refresh the project first.",
            409,
        )
    return UploadedMedia(
        bytes=data, mime_type=context["characterMimeType"], file_name="character-reference"
    )


async def reserve_generation_attempt(
    repair: Any,
    row: Any,
    operation: Any,
    *,
    slot: str,
    request_hash: str,
    stage: str,
    provider: str,
    model: str,
    profile: dict[str, Any],
) -> tuple[Any, bool]:
    """Commit one intent before submission; replay never authorizes a call."""
    import os
    from uuid import UUID

    from .budget_ledger import reservation_estimate, reserve_attempt

    if row.context_json.get("p0") is None:
        await require_generation_policy(repair, row)
        return None, True
    await require_generation_policy(repair, row)
    p0 = row.context_json["p0"]
    ceiling, estimate_metadata = reservation_estimate(
        p0.get("budgetPolicy"), os.getenv(f"SMART_REMAKE_P0_MAX_{stage.upper()}_USD"),
        error_code="SMART_REMAKE_COST_BOUND_REQUIRED",
        message="Configure a conservative server cost ceiling before paid generation.",
    )
    actor_id = operation.result_json.get("actorId") or p0.get("actorId")
    return await reserve_attempt(
        repair.repository.session,
        repair.workspace_id,
        row.id,
        idempotency_key=f"{operation.id}:{slot}",
        request_hash=request_hash,
        stage=stage,
        reservation_usd=ceiling,
        actor_id=UUID(actor_id) if actor_id else None,
        provider=provider,
        model=model,
        profile=profile,
        purpose="repair" if operation.result_json.get("kind") == "repair" else "initial",
        metadata={"operationId": str(operation.id), "slot": slot, **estimate_metadata},
    )


async def mark_generation_submitted(
    repair: Any, row: Any, attempt_id: str | None, *, task_id: str | None = None,
    execution_evidence: dict[str, Any] | None = None,
) -> None:
    if attempt_id is None:
        return
    from uuid import UUID

    from .budget_ledger import fail_attempt, mark_submitted

    args = (repair.repository.session, repair.workspace_id, row.id, UUID(attempt_id))
    try:
        if task_id is None:
            await require_generation_policy(repair, row)
        await mark_submitted(
            *args,
            provider_task_id=task_id,
            receipt={
                "providerTaskId": task_id,
                **({"executionEvidence": execution_evidence} if execution_evidence else {}),
            } if task_id else None,
        )
        if task_id is None:
            # The marker commit is an await boundary: stop-use may have been
            # committed while it ran. Refresh again before entering HTTP.
            await require_generation_policy(repair, row)
    except AppError as exc:
        if task_id is None:
            await fail_attempt(
                *args,
                error={"code": exc.code, "phase": "preflight", "httpAttempted": False},
                definitely_not_submitted=True,
                preflight_rejected=True,
            )
        raise


async def settle_generation_attempt(
    repair: Any,
    row: Any,
    attempt_id: str | None,
    *,
    status: str,
    receipt: dict[str, Any],
    usage: dict[str, Any] | None = None,
) -> None:
    if attempt_id is None:
        return
    from uuid import UUID

    from .budget_ledger import complete_attempt, fail_attempt, unknown_attempt, usd_amount

    args = (repair.repository.session, repair.workspace_id, row.id, UUID(attempt_id))
    # Tokens or credits alone do not establish a monetary bill. Never derive
    # a rate or turn a missing bill into zero cost.
    billed = receipt.get("billedUsd")
    try:
        actual = (
            None if billed is None or isinstance(billed, bool) else str(usd_amount(str(billed)))
        )
    except AppError:
        actual = None
    if status == "completed":
        await complete_attempt(*args, actual_usd=actual, receipt=receipt, usage=usage)
    elif status == "failed":
        await fail_attempt(
            *args,
            error=receipt,
            definitely_not_submitted=False,
            actual_usd=actual,
            receipt=receipt,
            usage=usage,
        )
    else:
        await unknown_attempt(*args, error=receipt, receipt=receipt, usage=usage)


async def recover_generation_task(repair: Any, row: Any, attempt_id: str | None) -> str | None:
    """Read a known receipt after the operation write was interrupted."""
    if attempt_id is None:
        return None
    from uuid import UUID

    from .budget_ledger import get_attempt

    attempt = await get_attempt(
        repair.repository.session, repair.workspace_id, row.id, UUID(attempt_id)
    )
    return attempt.provider_task_id


def saved_requirements_prompt(context: dict[str, Any]) -> str:
    """Keep server-retained constraints at the provider boundary, including user edits."""
    import json

    requirements = context.get("p0", {}).get("requirements")
    if not requirements:
        return ""
    reference_policy = (context.get("renderPlan") or {}).get("referencePolicy") or (
        "product-character-first-layout"
        if context.get("characterKey")
        else "product-first-last-layout"
    )
    return (
        "\n\nSAVED REQUIREMENTS: Follow the seller's saved intent, keep, replace and forbid "
        "constraints, and use only the supplied claims. Editable scene directions cannot waive "
        "these constraints or change the exact product and authorized character identity. "
        "Use the saved reference allocation.\n"
        + json.dumps(
            {"requirements": requirements, "referenceAllocation": reference_policy},
            sort_keys=True,
            ensure_ascii=False,
        )
    )
