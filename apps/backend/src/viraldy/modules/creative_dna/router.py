from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession, require_workspace_permission
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.creative_dna.service import CreativeDnaService
from viraldy.platform.auth.policy import Permission

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["creative-dna"])


@router.get("/creative-dna/{dna_version_id}", response_model=Envelope)
async def get_dna(
    workspace_id: UUID,
    dna_version_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.READ, current_user, db)
    dna = await CreativeDnaService(db).get(workspace_id, dna_version_id)
    return success(dna.model_dump(mode="json"), request_id)


@router.get("/references/{reference_id}/creative-dna", response_model=Envelope)
async def latest_reference_dna(
    workspace_id: UUID,
    reference_id: UUID,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.READ, current_user, db)
    dna = await CreativeDnaService(db).latest_for_reference(workspace_id, reference_id)
    return success(dna.model_dump(mode="json"), request_id)
