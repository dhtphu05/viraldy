"""Atomic metadata mutations, independent of a running paid generation operation."""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any, Literal
from uuid import UUID, uuid4

from sqlalchemy import select

from viraldy.shared.errors.base import AppError, ConflictError

from .budget_ledger import initialize_budget
from .models import SmartRemakeOperationModel
from .project_contracts import (
    SmartRemakeBudgetPatch,
    SmartRemakeRequirementsPatch,
    SmartRemakeRightsPatch,
    SmartRemakeRightsReviewRequest,
)
from .project_policy import (
    context_with_requirements,
    context_with_rights,
    context_with_rights_review,
    stable_hash,
)
from .repair_media import now_iso

if TYPE_CHECKING:
    from .repair_service import RepairService

MetadataKind = Literal["requirements", "rights", "budget", "rights_review"]
MetadataRequest = (
    SmartRemakeRequirementsPatch
    | SmartRemakeRightsPatch
    | SmartRemakeBudgetPatch
    | SmartRemakeRightsReviewRequest
)


async def patch_metadata(
    repair: RepairService,
    project_id: UUID,
    actor_id: UUID,
    request: MetadataRequest,
    *,
    kind: MetadataKind,
) -> dict[str, Any]:
    """Commit metadata + revision + completed idempotency receipt in one short transaction."""
    repository, session = repair.repository, repair.repository.session
    payload = request.model_dump(mode="json", exclude={"idempotencyKey"})
    request_hash = stable_hash({"kind": kind, "actorId": str(actor_id), "request": payload})
    row = await repository.project(repair.workspace_id, project_id, lock=True)
    try:
        previous = (
            await session.execute(
                select(SmartRemakeOperationModel).where(
                    SmartRemakeOperationModel.project_id == project_id,
                    SmartRemakeOperationModel.idempotency_key == request.idempotencyKey,
                )
            )
        ).scalar_one_or_none()
        if previous:
            if previous.request_hash != request_hash:
                raise ConflictError(
                    "SMART_REMAKE_IDEMPOTENCY_CONFLICT",
                    "This key belongs to another metadata request.",
                )
            await session.commit()
            return {
                "project": await repair.present(row),
                "operationId": str(previous.id),
                "status": previous.status,
            }
        if row.revision != request.expectedRevision:
            raise ConflictError(
                "SMART_REMAKE_REVISION_CONFLICT", "The project has changed. Refresh first."
            )
        context = row.context_json
        p0 = context.get("p0", {})
        if not p0.get("inputHash"):
            raise AppError(
                "SMART_REMAKE_INTAKE_REQUIRED", "Create an owned intake before editing policy.", 403
            )
        if p0.get("status") in {"suspended", "deleted"} or p0.get("deletion", {}).get(
            "status"
        ) not in (None, "none", "cancelled"):
            raise AppError(
                "SMART_REMAKE_USE_STOPPED", "Stopped project assets cannot be resumed here.", 403
            )
        # A consent/rights revocation and budget reduction must remain possible while
        # generation runs. Requirements/reviews wait so they cannot race its content snapshot.
        if kind in {"requirements", "rights_review"} and await repository.running(project_id):
            raise ConflictError(
                "SMART_REMAKE_OPERATION_BUSY", "Wait for the current content operation."
            )
        if kind == "requirements" and isinstance(request, SmartRemakeRequirementsPatch):
            updated = context_with_requirements(context, request.requirements)
            old_snapshot = p0.get("requirements")
        elif kind == "rights" and isinstance(request, SmartRemakeRightsPatch):
            updated = context_with_rights(context, request.rights, actor_id=actor_id)
            old_snapshot = p0.get("rights")
        elif kind == "rights_review" and isinstance(request, SmartRemakeRightsReviewRequest):
            updated = context_with_rights_review(
                context, actor_id=actor_id, evidence_note=request.evidenceNote
            )
            old_snapshot = p0.get("rights")
        elif kind == "budget" and isinstance(request, SmartRemakeBudgetPatch):
            updated = copy.deepcopy(context)
            old_snapshot = p0.get("budgetPolicy")
        else:
            raise AppError(
                "SMART_REMAKE_METADATA_INVALID", "Request does not match the metadata action."
            )
        operation_id, completed_at = uuid4(), now_iso()
        audit = {
            "operationId": str(operation_id),
            "kind": kind,
            "actorId": str(actor_id),
            "changedAt": completed_at,
            "previous": copy.deepcopy(old_snapshot),
        }
        updated["p0"]["metadataHistory"] = [*updated["p0"].get("metadataHistory", []), audit]
        row.context_json = updated
        row.revision += 1
        row.state_json = {**copy.deepcopy(row.state_json), "revision": row.revision}
        operation = SmartRemakeOperationModel(
            id=operation_id,
            project_id=project_id,
            idempotency_key=request.idempotencyKey,
            request_hash=request_hash,
            status="completed",
            result_json={
                "kind": f"metadata_{kind}",
                "actorId": str(actor_id),
                "completedAt": completed_at,
                "revision": row.revision,
                "request": payload,
            },
        )
        session.add(operation)
        if kind == "budget" and isinstance(request, SmartRemakeBudgetPatch):
            # This helper locks the same row, validates exposure and commits the staged
            # operation + revision with the budget. Validation failure rolls everything back.
            await initialize_budget(
                session, repair.workspace_id, project_id, request.budget.model_dump(mode="json")
            )
        else:
            await session.commit()
    except Exception:
        await session.rollback()
        raise
    return {
        "project": await repair.present(row),
        "operationId": str(operation.id),
        "status": "completed",
    }
