from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.assets.public import AssetRepository
from viraldy.modules.campaign_packs.public import CampaignPackRepository
from viraldy.modules.jobs.public import get_existing_idempotent_job, request_mvp_job
from viraldy.modules.preflight.repository import PreflightRepository
from viraldy.modules.preflight.schemas import (
    CreatePreflightRunRequest,
    CreatePreflightRunResponse,
    PreflightRunResponse,
)
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError, NotFoundError


class PreflightService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._repository = PreflightRepository(session)
        self._assets = AssetRepository(session)
        self._packs = CampaignPackRepository(session)

    async def create(
        self,
        workspace_id: UUID,
        data: CreatePreflightRunRequest,
        idempotency_key: str | None,
    ) -> CreatePreflightRunResponse:
        asset = await self._assets.get(workspace_id, data.ugc_asset_id)
        if asset is None:
            raise NotFoundError("ASSET_NOT_FOUND", "UGC asset was not found.")
        version = await self._assets.get_current_version_in_workspace(
            workspace_id, data.ugc_asset_id
        )
        if version is None:
            raise AppError("ASSET_VERSION_NOT_FOUND", "Asset version was not found.")
        pack_version = await self._packs.get_version_in_workspace(
            workspace_id, data.campaign_pack_version_id
        )
        if pack_version is None:
            raise NotFoundError(
                "CAMPAIGN_PACK_VERSION_NOT_FOUND", "Campaign Pack version was not found."
            )
        existing_job = await get_existing_idempotent_job(
            self._session, workspace_id, "run_ugc_preflight", idempotency_key
        )
        if existing_job is not None:
            run = await self._repository.get(workspace_id, existing_job.subject_id)
            if run is None:
                raise AppError(
                    "IDEMPOTENT_PREFLIGHT_RUN_NOT_FOUND",
                    "Existing idempotent preflight run was not found.",
                )
            return CreatePreflightRunResponse(
                preflight_run=PreflightRunResponse.model_validate(run),
                job=existing_job,
            )
        run = await self._repository.create_pending(
            workspace_id, version.id, data.campaign_pack_version_id, self._settings.ai_mode
        )
        job = await request_mvp_job(
            self._session,
            workspace_id,
            "preflight_run",
            run.id,
            "run_ugc_preflight",
            {
                "preflight_run_id": str(run.id),
                "ugc_asset_id": str(data.ugc_asset_id),
                "ugc_asset_version_id": str(version.id),
                "campaign_pack_version_id": str(data.campaign_pack_version_id),
            },
            idempotency_key,
        )
        if job.subject_id != run.id:
            existing_run = await self._repository.get(workspace_id, job.subject_id)
            if existing_run is None:
                raise AppError(
                    "IDEMPOTENT_PREFLIGHT_RUN_NOT_FOUND",
                    "Existing idempotent preflight run was not found.",
                )
            run = existing_run
        return CreatePreflightRunResponse(
            preflight_run=PreflightRunResponse.model_validate(run),
            job=job,
        )

    async def get(self, workspace_id: UUID, preflight_run_id: UUID) -> PreflightRunResponse:
        run = await self._repository.get(workspace_id, preflight_run_id)
        if run is None:
            raise NotFoundError("PREFLIGHT_RUN_NOT_FOUND", "Preflight run was not found.")
        return PreflightRunResponse.model_validate(run)


def calculate_preflight_result(
    structural_result: dict[str, Any],
    brief_json: dict[str, object],
) -> dict[str, Any]:
    alignment = _brief_alignment(brief_json, structural_result)
    structural_score = int(structural_result["structural_score"])
    brief_score = int(alignment["score"])
    final_score = round((0.8 * structural_score) + (0.2 * brief_score))
    blockers = [*structural_result["blockers"], *alignment["blockers"]]
    action = _preflight_action(final_score, blockers)
    fixes = [*structural_result["fixes"], *alignment["fixes"]][:5]
    return {
        "preflight_score": final_score,
        "structural_score": structural_score,
        "brief_alignment_score": brief_score,
        "confidence": structural_result["confidence"],
        "action": action,
        "dimensions": structural_result["dimensions"],
        "brief_alignment": alignment,
        "strengths": structural_result["strengths"],
        "blockers": blockers,
        "fixes": fixes,
        "revision_message": _revision_message(fixes),
        "evidence_ids": structural_result["evidence_ids"],
        "rubric_version": "ugc_preflight_rubric_v1",
        "rule_version": "ugc_preflight_rules_v1",
    }


def _brief_alignment(
    brief_json: dict[str, object], structural_result: dict[str, Any]
) -> dict[str, Any]:
    dimensions = structural_result["dimensions"]
    product_score = dimensions["product_visibility"]["score"]
    demo_score = dimensions["demo_clarity"]["score"]
    cta_score = dimensions["cta_readiness"]["score"]
    claim_score = dimensions["claim_safety"]["score"]
    must_show = brief_json.get("must_show", [])
    must_show_score = 80 if isinstance(must_show, list) and len(must_show) >= 3 else 60
    score = round(
        (product_score * 0.25)
        + (demo_score * 0.25)
        + (cta_score * 0.2)
        + (claim_score * 0.15)
        + (must_show_score * 0.15)
    )
    blockers = []
    fixes = []
    if product_score < 50:
        blockers.append(
            {
                "code": "MISSING_MUST_SHOW_SCENE",
                "severity": "high",
                "message": "Brief requires an early product close-up.",
                "evidence_ids": dimensions["product_visibility"]["evidence_ids"],
            }
        )
        fixes.append(
            {
                "code": "MISSING_MUST_SHOW_SCENE",
                "priority": 1,
                "instruction": "Add the required product close-up within the first three seconds.",
                "why": "The Campaign Pack revision checklist requires this scene.",
                "evidence_ids": dimensions["product_visibility"]["evidence_ids"],
            }
        )
    return {
        "score": score,
        "dimensions": {"must_show": must_show_score},
        "blockers": blockers,
        "fixes": fixes,
    }


def _preflight_action(score: int, blockers: list[dict[str, Any]]) -> str:
    hard_codes = {"BRIEF_PRODUCT_MISMATCH", "HIGH_RISK_UNSUPPORTED_CLAIM"}
    if any(blocker.get("code") in hard_codes for blocker in blockers):
        return "reject"
    if blockers:
        return "revise"
    if score < 50:
        return "reject_or_reshoot"
    if score < 70:
        return "revise"
    if score < 85:
        return "organic_ready_or_small_paid_test"
    return "spark_ready_pending_rights"


def _revision_message(fixes: list[dict[str, Any]]) -> str:
    if not fixes:
        return "This draft is structurally ready. Please confirm rights before Spark or paid usage."
    instructions = [str(fix["instruction"]).rstrip(".") for fix in fixes[:3]]
    return "The demonstration is clear. Could you " + "; and ".join(instructions) + "?"
