from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.assets.public import AssetRepository
from viraldy.modules.campaign_packs.public import CampaignPackRepository
from viraldy.modules.creative_domain.schema_versions import (
    PREFLIGHT_RUBRIC_VERSION,
    PREFLIGHT_RULE_VERSION,
)
from viraldy.modules.jobs.public import get_existing_idempotent_job, request_mvp_job
from viraldy.modules.preflight.contracts import BriefAlignmentResultV2, RequirementEvaluationV2
from viraldy.modules.preflight.repository import PreflightRepository
from viraldy.modules.preflight.requirements import CompiledRequirementV1, compile_requirements
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
    compiled_requirements_json: dict[str, object] | None = None,
) -> dict[str, Any]:
    requirements = _requirements_from_snapshot(compiled_requirements_json)
    if not requirements:
        requirements = compile_requirements(brief_json)
    alignment = _brief_alignment(requirements, structural_result)
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
    requirements: list[CompiledRequirementV1], structural_result: dict[str, Any]
) -> dict[str, Any]:
    evaluations = [
        _evaluate_requirement(requirement, structural_result) for requirement in requirements
    ]
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
        },
        blockers=blockers,
        fixes=fixes,
    )
    return result.model_dump(mode="json")


def _requirements_from_snapshot(
    compiled_requirements_json: dict[str, object] | None,
) -> list[CompiledRequirementV1]:
    if not compiled_requirements_json:
        return []
    raw_requirements = compiled_requirements_json.get("requirements")
    if not isinstance(raw_requirements, list):
        raise AppError(
            "CAMPAIGN_PACK_REQUIREMENTS_INVALID",
            "Campaign Pack compiled requirements snapshot is invalid.",
        )
    try:
        return [CompiledRequirementV1.model_validate(item) for item in raw_requirements]
    except Exception as exc:
        raise AppError(
            "CAMPAIGN_PACK_REQUIREMENTS_INVALID",
            "Campaign Pack compiled requirements snapshot is invalid.",
        ) from exc


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


def _evaluate_requirement(
    requirement: CompiledRequirementV1,
    structural_result: dict[str, Any],
) -> RequirementEvaluationV2:
    if requirement.matcher_type == "product_visibility":
        return _dimension_requirement(
            requirement,
            structural_result,
            "product_visibility",
            "Product visibility must satisfy the Campaign Pack requirement.",
        )
    if requirement.matcher_type == "demo_presence":
        return _dimension_requirement(
            requirement,
            structural_result,
            "demo_clarity",
            "Demo clarity must satisfy the Campaign Pack requirement.",
        )
    if requirement.matcher_type == "proof_presence":
        return _dimension_requirement(
            requirement,
            structural_result,
            "proof_strength",
            "Proof must satisfy the Campaign Pack requirement.",
        )
    if requirement.matcher_type == "cta_presence":
        return _cta_requirement(requirement, structural_result)
    if requirement.matcher_type == "claim_safety":
        return _claim_requirement(requirement, structural_result)
    return RequirementEvaluationV2(
        requirement_id=requirement.id,
        status="unknown",
        score=40,
        confidence="low",
        reason="No deterministic matcher exists yet for this semantic scene requirement.",
        evidence_ids=[],
        expected=requirement.model_dump(mode="json"),
        observed={},
    )


def _dimension_requirement(
    requirement: CompiledRequirementV1,
    structural_result: dict[str, Any],
    dimension_name: str,
    reason: str,
) -> RequirementEvaluationV2:
    dimension = _dimension(structural_result, dimension_name)
    score = int(dimension.get("score", 0))
    status = _status_from_score(score)
    return RequirementEvaluationV2(
        requirement_id=requirement.id,
        status=status,
        score=score,
        confidence=str(dimension.get("confidence", "low")),  # type: ignore[arg-type]
        reason=reason,
        evidence_ids=[UUID(str(item)) for item in dimension.get("evidence_ids", [])],
        expected=requirement.model_dump(mode="json"),
        observed={"dimension": dimension_name, "score": score},
    )


def _cta_requirement(
    requirement: CompiledRequirementV1,
    structural_result: dict[str, Any],
) -> RequirementEvaluationV2:
    dimension = _dimension(structural_result, "cta_readiness")
    score = int(dimension.get("score", 0))
    product_tag_required = bool(requirement.matcher_config.get("product_tag_required"))
    product_tag_present = _signal_contribution(dimension, "product_tag_or_shop_cue") > 0
    if product_tag_required and not product_tag_present:
        status = "missing"
        score = min(score, 50)
    else:
        status = _status_from_score(score)
    return RequirementEvaluationV2(
        requirement_id=requirement.id,
        status=status,
        score=score,
        confidence=str(dimension.get("confidence", "low")),  # type: ignore[arg-type]
        reason="CTA requirement is evaluated from observed CTA type, timing, and shop cue signals.",
        evidence_ids=[UUID(str(item)) for item in dimension.get("evidence_ids", [])],
        expected=requirement.model_dump(mode="json"),
        observed={
            "dimension": "cta_readiness",
            "score": score,
            "product_tag_present": product_tag_present,
        },
    )


def _claim_requirement(
    requirement: CompiledRequirementV1,
    structural_result: dict[str, Any],
) -> RequirementEvaluationV2:
    dimension = _dimension(structural_result, "claim_safety")
    score = int(dimension.get("score", 0))
    status = "violated" if score < 80 else "satisfied"
    return RequirementEvaluationV2(
        requirement_id=requirement.id,
        status=status,
        score=score,
        confidence=str(dimension.get("confidence", "low")),  # type: ignore[arg-type]
        reason="Claim guardrail is evaluated from deterministic claim-safety penalties.",
        evidence_ids=[UUID(str(item)) for item in dimension.get("evidence_ids", [])],
        expected=requirement.model_dump(mode="json"),
        observed={"dimension": "claim_safety", "score": score},
    )


def _alignment_score(
    requirements: list[CompiledRequirementV1],
    evaluations: list[RequirementEvaluationV2],
) -> int:
    total_weight = sum(_requirement_weight(requirement) for requirement in requirements)
    weighted = sum(
        evaluation.score * _requirement_weight(requirement)
        for requirement, evaluation in zip(requirements, evaluations, strict=True)
    )
    return round(weighted / total_weight) if total_weight else 0


def _alignment_blockers(
    requirements: list[CompiledRequirementV1],
    evaluations: list[RequirementEvaluationV2],
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for requirement, evaluation in zip(requirements, evaluations, strict=True):
        if evaluation.status not in {"missing", "violated"}:
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
    requirements: list[CompiledRequirementV1],
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


def _status_from_score(score: int) -> str:
    if score >= 75:
        return "satisfied"
    if score >= 50:
        return "partial"
    return "missing"


def _requirement_weight(requirement: CompiledRequirementV1) -> float:
    return {"hard": 4.0, "high": 3.0, "medium": 2.0, "low": 1.0}[requirement.severity]


def _dimension(structural_result: dict[str, Any], name: str) -> dict[str, Any]:
    dimensions = structural_result.get("dimensions", {})
    value = dimensions.get(name, {}) if isinstance(dimensions, dict) else {}
    return value if isinstance(value, dict) else {}


def _signal_contribution(dimension: dict[str, Any], code: str) -> float:
    signals = dimension.get("signals", [])
    if not isinstance(signals, list):
        return 0
    for signal in signals:
        if isinstance(signal, dict) and signal.get("code") == code:
            contribution = signal.get("contribution")
            return float(contribution) if isinstance(contribution, int | float) else 0
    return 0
