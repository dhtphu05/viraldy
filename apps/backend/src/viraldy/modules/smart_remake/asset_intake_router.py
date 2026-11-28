"""JSON intake for completed direct uploads under the workspace policy boundary."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from viraldy.api.dependencies.auth import CurrentUserDep, DbSession
from viraldy.api.dependencies.request import get_request_id
from viraldy.api.responses.envelope import Envelope, success
from viraldy.modules.assets.public import AssetRepository
from viraldy.shared.errors.base import AppError

from .asset_intake import SmartRemakeAssetIntakeRequest, create_intake_from_assets
from .budget_ledger import initialize_budget
from .engine.errors import SmartRemakeError
from .intake_router import SettingsDep, authorize, service_for

router = APIRouter()


@router.post("/projects/from-assets", response_model=Envelope)
async def create_project_from_assets(
    workspace_id: UUID,
    payload: SmartRemakeAssetIntakeRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    settings: SettingsDep,
    request_id: str = Depends(get_request_id),
) -> Envelope:
    await authorize(workspace_id, current_user, db, settings)
    repair = service_for(db, settings, workspace_id)
    try:
        row = await create_intake_from_assets(
            AssetRepository(db),
            repair.repository,
            repair.media,
            workspace_id,
            current_user.id,
            payload,
        )
        # Preserve amended caps when the canonical intake returns an idempotent replay.
        row = await repair.repository.project(workspace_id, row.id, lock=True)
        policy = row.context_json["p0"]["budgetPolicy"]
        if not policy.get("startedAt"):
            await initialize_budget(db, workspace_id, row.id, policy)
        else:
            await db.commit()
    except AppError:
        raise
    except SmartRemakeError as exc:
        raise AppError(exc.code, "Input media is invalid.", 422) from exc
    except Exception as exc:
        raise AppError(
            "SMART_REMAKE_RETENTION_UNAVAILABLE", "Private input retention is unavailable.", 503
        ) from exc
    return success({"project": await repair.present(row)}, request_id)
