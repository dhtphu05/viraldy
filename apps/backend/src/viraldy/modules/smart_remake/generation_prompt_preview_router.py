"""Read-only, workspace-authorized previews of current KIE script directions."""

from uuid import UUID

from fastapi import APIRouter, Depends

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession, require_workspace_permission
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.platform.auth.policy import Permission
from viraldy.shared.errors.base import AppError

from .engine.errors import SmartRemakeError
from .generation_prompt_preview import GenerationPromptPreviewRequest, preview_generation_prompts
from .repair_repository import RepairRepository

router = APIRouter()


@router.post("/projects/{project_id}/generation/prompt-preview", response_model=Envelope)
async def preview_project_generation_prompts(
    workspace_id: UUID,
    project_id: UUID,
    payload: GenerationPromptPreviewRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await require_workspace_permission(workspace_id, Permission.WORKSPACE_READ, current_user, db)
    try:
        result = await preview_generation_prompts(
            RepairRepository(db), workspace_id, project_id, payload
        )
    except SmartRemakeError as exc:
        raise AppError(
            code="SMART_REMAKE_PROMPT_PREVIEW_INVALID",
            message="The current script does not meet the video provider's prompt requirements.",
            status_code=422,
        ) from exc
    return success(result, request_id)
