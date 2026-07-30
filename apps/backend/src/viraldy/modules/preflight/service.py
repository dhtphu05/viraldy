from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.assets.public import AssetRepository
from viraldy.modules.campaign_packs.public import (
    CampaignPackRepository,
    CompiledRequirementV2,
    compile_campaign_requirements,
    parse_compiled_requirements_snapshot,
)
from viraldy.modules.creative_domain.schema_versions import (
    PREFLIGHT_RUBRIC_VERSION,
    PREFLIGHT_RULE_VERSION,
)
from viraldy.modules.jobs.public import get_existing_idempotent_job, request_mvp_job
from viraldy.modules.media_analysis.public import EvidenceItemModel
from viraldy.modules.preflight.contracts import BriefAlignmentResultV2, RequirementEvaluationV2
from viraldy.modules.preflight.matchers import RequirementMatcherContext, evaluate_requirement
from viraldy.modules.preflight.repository import PreflightRepository
from viraldy.modules.preflight.schemas import (
    CreatePreflightRunRequest,
    CreatePreflightRunResponse,
    PreflightRunResponse,
)
from viraldy.modules.product_events.public import ProductEventPublisher
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
            self._session, workspace_id, "preflight_run", idempotency_key
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
            "preflight_run",
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

    async def get(
        self,
        workspace_id: UUID,
        preflight_run_id: UUID,
        user_id: UUID,
    ) -> PreflightRunResponse:
        run = await self._repository.get(workspace_id, preflight_run_id)
        if run is None:
            raise NotFoundError("PREFLIGHT_RUN_NOT_FOUND", "Preflight run was not found.")
        response = PreflightRunResponse.model_validate(run)
        await ProductEventPublisher(self._session).record(
            event_type="preflight_viewed",
            workspace_id=workspace_id,
            actor_user_id=user_id,
            subject_type="preflight_run",
            subject_id=run.id,
            payload_json={
                "campaign_pack_version_id": str(run.campaign_pack_version_id),
                "status": run.status,
                "action_label": run.action_label,
            },
        )
        await self._session.commit()
        return response


def calculate_preflight_result(
    structural_result: dict[str, Any],
    brief_json: dict[str, object],
    compiled_requirements_json: dict[str, object] | None = None,
    evidence: list[EvidenceItemModel] | None = None,
    product_snapshot_json: dict[str, object] | None = None,
    media_duration_ms: int | None = None,
) -> dict[str, Any]:
    requirements = _requirements_from_snapshot(compiled_requirements_json)
    if not requirements:
        requirements = compile_campaign_requirements(brief_json)
    alignment = _brief_alignment(
        requirements,
        structural_result,
        evidence or [],
        product_snapshot_json or _product_snapshot_from_brief(brief_json),
        media_duration_ms,
    )
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
        "revision_message": _revision_message(fixes, action),
        "evidence_ids": structural_result["evidence_ids"],
        "rubric_version": PREFLIGHT_RUBRIC_VERSION,
        "rule_version": PREFLIGHT_RULE_VERSION,
    }


def _brief_alignment(
    requirements: list[CompiledRequirementV2],
    structural_result: dict[str, Any],
    evidence: list[EvidenceItemModel],
    product_snapshot_json: dict[str, object] | None,
    media_duration_ms: int | None,
) -> dict[str, Any]:
    evaluations = [
        evaluate_requirement(
            RequirementMatcherContext(
                requirement=requirement,
                evidence=evidence,
                structural_result=structural_result,
                product_snapshot=product_snapshot_json,
                media_duration_ms=media_duration_ms,
            )
        )
        for requirement in requirements
    ]
    evaluations = _apply_group_minimums(requirements, evaluations)
    score = _alignment_score(requirements, evaluations)
    blockers = _alignment_blockers(requirements, evaluations)
    fixes = _alignment_fixes(requirements, evaluations)
    result = BriefAlignmentResultV2(
        score=score,
        confidence=_alignment_confidence(evaluations),
        requirements=evaluations,
        coverage={
            "total": len(evaluations),
            "satisfied": sum(1 for item in evaluations if item.status == "satisfied"),
            "partial": sum(1 for item in evaluations if item.status == "partial"),
            "missing": sum(1 for item in evaluations if item.status == "missing"),
            "violated": sum(1 for item in evaluations if item.status == "violated"),
            "unknown": sum(1 for item in evaluations if item.status == "unknown"),
            "not_applicable": sum(1 for item in evaluations if item.status == "not_applicable"),
        },
        blockers=blockers,
        fixes=fixes,
    )
    return result.model_dump(mode="json")


def _requirements_from_snapshot(
    compiled_requirements_json: dict[str, object] | None,
) -> list[CompiledRequirementV2]:
    if not compiled_requirements_json:
        return []
    raw_requirements = compiled_requirements_json.get("requirements")
    if not isinstance(raw_requirements, list):
        raise AppError(
            "CAMPAIGN_PACK_REQUIREMENTS_INVALID",
            "Campaign Pack compiled requirements snapshot is invalid.",
        )
    try:
        return parse_compiled_requirements_snapshot(compiled_requirements_json)
    except Exception as exc:
        raise AppError(
            "CAMPAIGN_PACK_REQUIREMENTS_INVALID",
            "Campaign Pack compiled requirements snapshot is invalid.",
        ) from exc


def _product_snapshot_from_brief(brief_json: dict[str, object]) -> dict[str, object] | None:
    product_snapshot = brief_json.get("product_snapshot")
    return product_snapshot if isinstance(product_snapshot, dict) else None


def _apply_group_minimums(
    requirements: list[CompiledRequirementV2],
    evaluations: list[RequirementEvaluationV2],
) -> list[RequirementEvaluationV2]:
    by_group: dict[str, list[tuple[CompiledRequirementV2, RequirementEvaluationV2]]] = {}
    for requirement, evaluation in zip(requirements, evaluations, strict=True):
        if requirement.requirement_group_id and requirement.minimum_satisfied:
            by_group.setdefault(requirement.requirement_group_id, []).append(
                (requirement, evaluation)
            )
    if not by_group:
        return evaluations
    updated = list(evaluations)
    for group_items in by_group.values():
        minimum = group_items[0][0].minimum_satisfied or 1
        satisfied_count = sum(
            1 for _, evaluation in group_items if evaluation.status == "satisfied"
        )
        if satisfied_count < minimum:
            continue
        for requirement, evaluation in group_items:
            if evaluation.status == "satisfied":
                continue
            index = requirements.index(requirement)
            updated[index] = RequirementEvaluationV2(
                requirement_id=evaluation.requirement_id,
                status="not_applicable",
                score=100,
                confidence=evaluation.confidence,
                reason="Optional requirement group minimum was satisfied by another alternative.",
                evidence_ids=evaluation.evidence_ids,
                expected=evaluation.expected,
                observed={
                    **evaluation.observed,
                    "requirement_group_id": requirement.requirement_group_id,
                    "minimum_satisfied": minimum,
                    "satisfied_count": satisfied_count,
                },
            )
    return updated


def _preflight_action(score: int, blockers: list[dict[str, Any]]) -> str:
    hard_codes = {
        "BRIEF_HARD_REQUIREMENT_MISSING",
        "BRIEF_PRODUCT_MISMATCH",
        "CRITICAL_PROHIBITED_CLAIM",
        "HIGH_RISK_UNSUPPORTED_CLAIM",
        "PRODUCT_NOT_VISIBLE",
        "PRODUCT_MISMATCH",
        "VISUAL_EVIDENCE_INSUFFICIENT",
    }
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


def _revision_message(fixes: list[dict[str, Any]], action: str) -> str:
    if action == "spark_ready_pending_rights":
        if not fixes:
            return (
                "This draft is structurally ready. Please confirm rights before Spark or paid "
                "usage."
            )
        instructions = [str(fix["instruction"]).rstrip(".") for fix in fixes[:2]]
        return (
            "This draft is structurally ready pending rights confirmation. Optional revision: "
            + "; and ".join(instructions)
            + "."
        )
    if not fixes:
        return "This draft is structurally ready. Please confirm rights before Spark or paid usage."
    instructions = [str(fix["instruction"]).rstrip(".") for fix in fixes[:3]]
    return "The demonstration is clear. Could you " + "; and ".join(instructions) + "?"


def _alignment_score(
    requirements: list[CompiledRequirementV2],
    evaluations: list[RequirementEvaluationV2],
) -> int:
    total_weight = sum(_requirement_weight(requirement) for requirement in requirements)
    weighted = sum(
        evaluation.score * _requirement_weight(requirement)
        for requirement, evaluation in zip(requirements, evaluations, strict=True)
    )
    return round(weighted / total_weight) if total_weight else 0


def _alignment_blockers(
    requirements: list[CompiledRequirementV2],
    evaluations: list[RequirementEvaluationV2],
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for requirement, evaluation in zip(requirements, evaluations, strict=True):
        if evaluation.status not in {"missing", "violated", "unknown"}:
            continue
        if evaluation.status == "unknown" and requirement.severity != "hard":
            continue
        code = (
            "BRIEF_HARD_REQUIREMENT_MISSING"
            if requirement.severity == "hard"
            else "MISSING_MUST_SHOW_SCENE"
        )
        blockers.append(
            {
                "code": code,
                "severity": "hard" if requirement.severity == "hard" else "high",
                "message": f"Brief requirement is {evaluation.status}: {requirement.description}",
                "evidence_ids": [str(item) for item in evaluation.evidence_ids],
                "remediation_code": requirement.matcher_type,
            }
        )
    return blockers


def _alignment_fixes(
    requirements: list[CompiledRequirementV2],
    evaluations: list[RequirementEvaluationV2],
) -> list[dict[str, Any]]:
    fixes: list[dict[str, Any]] = []
    for requirement, evaluation in zip(requirements, evaluations, strict=True):
        if evaluation.status not in {"missing", "violated", "partial", "unknown"}:
            continue
        fixes.append(
            {
                "code": "FIX_BRIEF_REQUIREMENT",
                "priority": len(fixes) + 1,
                "instruction": requirement.description,
                "why": evaluation.reason,
                "expected_impact_dimensions": [requirement.requirement_type],
                "evidence_ids": [str(item) for item in evaluation.evidence_ids],
            }
        )
    return fixes


def _alignment_confidence(evaluations: list[RequirementEvaluationV2]) -> str:
    if any(item.confidence == "low" for item in evaluations):
        return "low"
    if any(item.status in {"partial", "unknown", "not_applicable"} for item in evaluations):
        return "medium"
    return "high"


def _requirement_weight(requirement: CompiledRequirementV2) -> float:
    return {"hard": 4.0, "high": 3.0, "medium": 2.0, "low": 1.0}[requirement.severity]
