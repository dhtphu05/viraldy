from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.ai_gateway.public import (
    DECISION_SUMMARY_PROMPT_NAME,
    REVISION_MESSAGE_PROMPT_NAME,
    AiModelRunModel,
    AiModelRunRepository,
    AiOperationName,
    StructuredGenerationResult,
    ViraldyOperationContextV1,
    execute_structured_operation,
    get_prompt_package,
)
from viraldy.modules.campaign_packs.contracts import CampaignPackBriefV1
from viraldy.modules.campaign_packs.repository import CampaignPackRepository
from viraldy.modules.preflight.models import PreflightRunModel
from viraldy.modules.preflight.repository import PreflightRepository
from viraldy.modules.presentations.contracts import (
    CreatorRevisionInputV2,
    CreatorRevisionMessageV2,
    GeneratePresentationRequestV1,
    PreflightPresentationBundleV1,
    PresentationBlockerV1,
    PresentationFixV1,
    SellerDecisionInputV1,
    SellerDecisionSummaryV1,
)
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError, NotFoundError

_ACTION_LABEL_EN = {
    "revise": "Revise before paid use",
    "ready_for_organic": "Ready for organic posting",
    "small_paid_test": "Structurally ready for a small paid test",
    "reject_or_reshoot": "Reshoot before use",
}
_ACTION_LABEL_VI = {
    "revise": "Can chinh sua truoc khi chay paid",
    "ready_for_organic": "San sang dang organic",
    "small_paid_test": "Du dieu kien cau truc cho mot paid test nho",
    "reject_or_reshoot": "Can quay lai truoc khi su dung",
}
_COMMERCIAL_GUARDRAIL_EN = (
    "This decision evaluates structural and brief readiness. It does not guarantee "
    "virality, GMV, ROAS, conversion, policy approval, or sales."
)
_COMMERCIAL_GUARDRAIL_VI = (
    "Quyet dinh nay danh gia muc do san sang ve cau truc va brief. Day khong phai "
    "cam ket ve viral, GMV, ROAS, chuyen doi, phe duyet chinh sach hoac doanh so."
)


class PreflightPresentationService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._preflight = PreflightRepository(session)
        self._campaign_packs = CampaignPackRepository(session)
        self._model_runs = AiModelRunRepository(session)

    async def generate(
        self,
        *,
        workspace_id: UUID,
        preflight_run_id: UUID,
        actor_user_id: UUID,
        request: GeneratePresentationRequestV1,
    ) -> PreflightPresentationBundleV1:
        run = await self._preflight.get(workspace_id, preflight_run_id)
        if run is None:
            raise NotFoundError("PREFLIGHT_NOT_FOUND", "Preflight run was not found.")
        if run.status != "completed":
            raise AppError(
                "PREFLIGHT_NOT_COMPLETED",
                "Presentation is available after Preflight completes.",
                status_code=409,
            )
        cached = _cached_bundle(run, request)
        if cached is not None:
            return cached

        campaign_pack_version = await self._campaign_packs.get_version_in_workspace(
            workspace_id,
            run.campaign_pack_version_id,
        )
        if campaign_pack_version is None:
            raise NotFoundError(
                "CAMPAIGN_PACK_VERSION_NOT_FOUND",
                "Campaign Pack version was not found.",
            )
        brief = CampaignPackBriefV1.model_validate(campaign_pack_version.brief_json)
        seller_input = _seller_input(run, brief, request)
        creator_input = _creator_input(run, brief)

        seller_summary = build_deterministic_seller_summary(seller_input)
        creator_revision = (
            build_deterministic_creator_message(creator_input)
            if creator_input is not None
            else None
        )
        sources: dict[
            str,
            str,
        ] = {
            "seller_summary": "deterministic",
            "creator_revision": "deterministic",
        }
        model_run_ids: list[UUID] = []

        if self._settings.ai_mode in {"mock", "live"}:
            seller_summary, seller_source, seller_run_id = (
                await self._generate_openai_seller_summary(
                    workspace_id=workspace_id,
                    actor_user_id=actor_user_id,
                    run=run,
                    brief=brief,
                    input_data=seller_input,
                    fallback=seller_summary,
                )
            )
            sources["seller_summary"] = seller_source
            model_run_ids.append(seller_run_id)
            if creator_input is not None and creator_revision is not None:
                creator_revision, creator_source, creator_run_id = (
                    await self._generate_openai_creator_revision(
                        workspace_id=workspace_id,
                        actor_user_id=actor_user_id,
                        run=run,
                        brief=brief,
                        input_data=creator_input,
                        fallback=creator_revision,
                    )
                )
                sources["creator_revision"] = creator_source
                model_run_ids.append(creator_run_id)

        run.seller_summary_json = seller_summary.model_dump(mode="json")
        run.creator_revision_json = (
            creator_revision.model_dump(mode="json")
            if creator_revision is not None
            else None
        )
        if creator_revision is not None:
            run.revision_message = creator_revision.message
        run.presentation_model_run_ids_json = [
            str(model_run_id) for model_run_id in model_run_ids
        ]
        run.presentation_source_json = dict(sources)
        await self._session.flush()
        await self._session.commit()
        return PreflightPresentationBundleV1(
            preflight_run_id=run.id,
            seller_summary=seller_summary,
            creator_revision=creator_revision,
            sources=sources,
            model_run_ids=model_run_ids,
        )

    async def _generate_openai_seller_summary(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
        run: PreflightRunModel,
        brief: CampaignPackBriefV1,
        input_data: SellerDecisionInputV1,
        fallback: SellerDecisionSummaryV1,
    ) -> tuple[
        SellerDecisionSummaryV1,
        str,
        UUID,
    ]:
        operation = AiOperationName.SELLER_DECISION_SUMMARY
        prompt = get_prompt_package(operation)
        model_run = await self._create_presentation_model_run(
            workspace_id=workspace_id,
            run=run,
            operation=operation,
            prompt_name=DECISION_SUMMARY_PROMPT_NAME,
            prompt_version=prompt.prompt_version,
            schema_version=prompt.output_schema_version,
            input_summary={
                "preflight_run_id": str(run.id),
                "product_name": input_data.product_name,
                "action_label": input_data.action_label,
                "locale": input_data.locale,
            },
        )
        context = _presentation_context(
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            run=run,
            brief=brief,
            operation=operation,
            model_run_id=model_run.id,
            payload=input_data.model_dump(mode="json"),
        )
        try:
            result = execute_structured_operation(
                self._settings,
                context,
                SellerDecisionSummaryV1,
                output_validator=_seller_summary_validator(input_data),
            )
        except AppError as exc:
            await _fail_presentation_model_run(self._model_runs, model_run, exc)
            return fallback, "deterministic_fallback", model_run.id
        summary = SellerDecisionSummaryV1.model_validate(result.parsed_output)
        await _complete_presentation_model_run(
            self._model_runs,
            model_run,
            result,
            {
                "locale": summary.locale,
                "strength_count": len(summary.strengths_to_keep),
                "blocker_count": len(summary.blockers_to_fix),
                "next_action_count": len(summary.next_actions),
            },
        )
        return summary, _provider_source(self._settings), model_run.id

    async def _generate_openai_creator_revision(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
        run: PreflightRunModel,
        brief: CampaignPackBriefV1,
        input_data: CreatorRevisionInputV2,
        fallback: CreatorRevisionMessageV2,
    ) -> tuple[
        CreatorRevisionMessageV2,
        str,
        UUID,
    ]:
        operation = AiOperationName.REVISION_MESSAGE_GENERATE
        prompt = get_prompt_package(operation)
        model_run = await self._create_presentation_model_run(
            workspace_id=workspace_id,
            run=run,
            operation=operation,
            prompt_name=REVISION_MESSAGE_PROMPT_NAME,
            prompt_version=prompt.prompt_version,
            schema_version=prompt.output_schema_version,
            input_summary={
                "preflight_run_id": str(run.id),
                "product_name": input_data.product_name,
                "blocker_codes": input_data.allowed_blocker_codes,
            },
        )
        context = _presentation_context(
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            run=run,
            brief=brief,
            operation=operation,
            model_run_id=model_run.id,
            payload=input_data.model_dump(mode="json"),
        )
        try:
            result = execute_structured_operation(
                self._settings,
                context,
                CreatorRevisionMessageV2,
                output_validator=_creator_revision_validator(input_data),
            )
        except AppError as exc:
            await _fail_presentation_model_run(self._model_runs, model_run, exc)
            return fallback, "deterministic_fallback", model_run.id
        revision = CreatorRevisionMessageV2.model_validate(result.parsed_output)
        await _complete_presentation_model_run(
            self._model_runs,
            model_run,
            result,
            {
                "strength_count": len(revision.strengths_to_preserve),
                "required_change_count": len(revision.required_changes),
                "referenced_blocker_count": len(
                    revision.referenced_blocker_codes
                ),
            },
        )
        return revision, _provider_source(self._settings), model_run.id

    async def _create_presentation_model_run(
        self,
        *,
        workspace_id: UUID,
        run: PreflightRunModel,
        operation: AiOperationName,
        prompt_name: str,
        prompt_version: str,
        schema_version: str,
        input_summary: dict[str, object],
    ) -> AiModelRunModel:
        input_hash = _hash_json(input_summary)
        return await self._model_runs.create_running(
            workspace_id=workspace_id,
            processing_job_id=run.processing_job_id,
            subject_type="preflight_run",
            subject_id=run.id,
            capability=operation.value,
            operation=operation.value,
            analysis_mode=self._settings.ai_mode,
            provider=self._settings.ai_provider,
            model=self._settings.resolve_openai_model(operation.value),
            prompt_version=prompt_version,
            response_schema_version=schema_version,
            schema_version=schema_version,
            request_hash=input_hash,
            input_hash=input_hash,
            input_summary=input_summary,
            endpoint_family=(
                "responses"
                if self._settings.ai_provider == "openai"
                else "chat_completions"
            ),
            prompt_name=prompt_name,
        )


def build_deterministic_seller_summary(
    input_data: SellerDecisionInputV1,
) -> SellerDecisionSummaryV1:
    if input_data.locale == "vi-VN":
        return _build_vi_summary(input_data)
    return _build_en_summary(input_data)


def _provider_source(settings: Settings) -> str:
    return "openai" if settings.ai_mode == "live" else "mock"


def build_deterministic_creator_message(
    input_data: CreatorRevisionInputV2,
) -> CreatorRevisionMessageV2:
    strengths = [_sentence(value) for value in input_data.strengths_to_preserve[:2]]
    opening = _join_phrases(strengths)
    requested_changes = [_creator_change_sentence(change) for change in input_data.required_changes]
    changes = _join_phrases(requested_changes)
    resubmission = _sentence(input_data.resubmission_request)
    message = (
        f"{opening} Please {changes[0].lower() + changes[1:] if changes else changes} "
        f"{resubmission}"
    ).strip()
    return CreatorRevisionMessageV2(
        message=message,
        strengths_to_preserve=list(input_data.strengths_to_preserve),
        required_changes=list(input_data.required_changes),
        referenced_blocker_codes=[change.code for change in input_data.required_changes],
        resubmission_request=input_data.resubmission_request,
        locale=input_data.locale,
    )


def _build_en_summary(input_data: SellerDecisionInputV1) -> SellerDecisionSummaryV1:
    action = _ACTION_LABEL_EN[input_data.action_label]
    objective = (
        f" for the objective '{input_data.objective}'" if input_data.objective else ""
    )
    blockers = [blocker.message for blocker in input_data.blockers]
    why = (
        f"{input_data.product_name} has {len(blockers)} blocking requirement(s){objective}."
        if blockers
        else f"{input_data.product_name} satisfies the current hard requirements{objective}."
    )
    next_actions = [fix.instruction for fix in input_data.fixes]
    next_actions.append(input_data.next_action)
    return SellerDecisionSummaryV1(
        headline=f"{action}: {input_data.product_name}",
        one_sentence_decision=(
            f"{action} with a final readiness score of {input_data.final_score}/100."
        ),
        why_this_matters=why,
        strengths_to_keep=list(input_data.strengths),
        blockers_to_fix=blockers,
        next_actions=_deduplicate(next_actions),
        confidence_explanation=(
            f"Confidence is {input_data.confidence}; the structural score is "
            f"{input_data.structural_score}/100 and brief alignment is "
            f"{input_data.brief_alignment_score}/100."
        ),
        commercial_guardrail=_COMMERCIAL_GUARDRAIL_EN,
        locale=input_data.locale,
    )


def _build_vi_summary(input_data: SellerDecisionInputV1) -> SellerDecisionSummaryV1:
    action = _ACTION_LABEL_VI[input_data.action_label]
    objective = f" cho muc tieu '{input_data.objective}'" if input_data.objective else ""
    blockers = [blocker.message for blocker in input_data.blockers]
    why = (
        f"{input_data.product_name} con {len(blockers)} yeu cau bat buoc chua dat{objective}."
        if blockers
        else f"{input_data.product_name} da dat cac yeu cau bat buoc hien tai{objective}."
    )
    next_actions = [fix.instruction for fix in input_data.fixes]
    next_actions.append(input_data.next_action)
    return SellerDecisionSummaryV1(
        headline=f"{action}: {input_data.product_name}",
        one_sentence_decision=(
            f"{action}, voi diem san sang cuoi cung {input_data.final_score}/100."
        ),
        why_this_matters=why,
        strengths_to_keep=list(input_data.strengths),
        blockers_to_fix=blockers,
        next_actions=_deduplicate(next_actions),
        confidence_explanation=(
            f"Do tin cay: {input_data.confidence}; diem cau truc "
            f"{input_data.structural_score}/100 va diem bam sat brief "
            f"{input_data.brief_alignment_score}/100."
        ),
        commercial_guardrail=_COMMERCIAL_GUARDRAIL_VI,
        locale=input_data.locale,
    )


def _creator_change_sentence(change: object) -> str:
    from viraldy.modules.presentations.contracts import PresentationFixV1

    validated = PresentationFixV1.model_validate(change)
    instruction = validated.instruction.strip().rstrip(".")
    if validated.required_text:
        instruction = f'{instruction} using the exact text "{validated.required_text}"'
    if validated.target_start_ms is not None and validated.target_end_ms is not None:
        instruction = (
            f"{instruction} between {_seconds(validated.target_start_ms)} and "
            f"{_seconds(validated.target_end_ms)}"
        )
    elif validated.target_end_ms is not None:
        instruction = f"{instruction} by {_seconds(validated.target_end_ms)}"
    return _sentence(instruction)


def _seconds(value_ms: int) -> str:
    return f"{value_ms / 1000:g} seconds"


def _sentence(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        return stripped
    return stripped if stripped[-1] in ".!?" else f"{stripped}."


def _join_phrases(values: list[str]) -> str:
    cleaned = [value for value in values if value]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    return " ".join(cleaned)


def _deduplicate(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value.strip()))


def _cached_bundle(
    run: PreflightRunModel,
    request: GeneratePresentationRequestV1,
) -> PreflightPresentationBundleV1 | None:
    if request.force_regenerate or run.seller_summary_json is None:
        return None
    seller_summary = SellerDecisionSummaryV1.model_validate(run.seller_summary_json)
    if seller_summary.locale != request.seller_locale:
        return None
    creator_revision = (
        CreatorRevisionMessageV2.model_validate(run.creator_revision_json)
        if run.creator_revision_json is not None
        else None
    )
    return PreflightPresentationBundleV1(
        preflight_run_id=run.id,
        seller_summary=seller_summary,
        creator_revision=creator_revision,
        sources={
            key: value
            for key, value in run.presentation_source_json.items()
            if isinstance(value, str)
            and value
            in {"openai", "mock", "deterministic", "deterministic_fallback"}
        },
        model_run_ids=[
            UUID(str(value)) for value in run.presentation_model_run_ids_json
        ],
    )


def _seller_input(
    run: PreflightRunModel,
    brief: CampaignPackBriefV1,
    request: GeneratePresentationRequestV1,
) -> SellerDecisionInputV1:
    return SellerDecisionInputV1(
        product_name=brief.product_snapshot.identity.name,
        objective=brief.objective.objective_type,
        action_label=_presentation_action(run.action_label),
        final_score=round(float(run.preflight_score)),
        structural_score=round(float(run.structural_score)),
        brief_alignment_score=round(float(run.brief_alignment_score)),
        confidence=(
            run.confidence
            if run.confidence in {"low", "medium", "high"}
            else "low"
        ),
        strengths=_strength_messages(run),
        blockers=[
            PresentationBlockerV1(
                code=str(blocker.get("code") or "UNSPECIFIED_REQUIREMENT"),
                message=str(
                    blocker.get("message")
                    or "A persisted requirement needs revision."
                ),
            )
            for blocker in _object_list(run.blockers_json)
        ],
        fixes=[
            PresentationFixV1(
                code=str(fix.get("code") or f"FIX_{index}"),
                instruction=str(
                    fix.get("instruction") or "Apply the persisted required fix."
                ),
            )
            for index, fix in enumerate(_object_list(run.fixes_json), start=1)
        ],
        next_action=_next_action(run.action_label),
        locale=request.seller_locale,
    )


def _creator_input(
    run: PreflightRunModel,
    brief: CampaignPackBriefV1,
) -> CreatorRevisionInputV2 | None:
    blockers = _object_list(run.blockers_json)
    fixes = _object_list(run.fixes_json)
    if not blockers and not fixes:
        return None
    changes: list[PresentationFixV1] = []
    allowed_codes: list[str] = []
    for index, blocker in enumerate(blockers):
        code = str(blocker.get("code") or f"REQUIRED_CHANGE_{index + 1}")
        remediation_code = blocker.get("remediation_code")
        matching_fix = next(
            (
                fix
                for fix in fixes
                if fix.get("code") in {code, remediation_code}
            ),
            fixes[index] if index < len(fixes) else None,
        )
        instruction = (
            str(matching_fix.get("instruction"))
            if matching_fix is not None and matching_fix.get("instruction")
            else str(
                blocker.get("message")
                or "Apply the required correction shown in Preflight."
            )
        )
        changes.append(
            PresentationFixV1(
                code=code,
                instruction=instruction,
                required_text=_required_text_for(code, brief),
                target_end_ms=_target_end_for(code, brief),
            )
        )
        allowed_codes.append(code)
    if not blockers:
        for index, fix in enumerate(fixes, start=1):
            code = str(fix.get("code") or f"REQUIRED_CHANGE_{index}")
            changes.append(
                PresentationFixV1(
                    code=code,
                    instruction=str(
                        fix.get("instruction")
                        or "Apply the required correction shown in Preflight."
                    ),
                    required_text=_required_text_for(code, brief),
                    target_end_ms=_target_end_for(code, brief),
                )
            )
            allowed_codes.append(code)
    strengths = _strength_messages(run)
    if not strengths:
        strengths = [
            f"The current {brief.product_snapshot.identity.name} delivery has "
            "useful elements worth preserving"
        ]
    return CreatorRevisionInputV2(
        product_name=brief.product_snapshot.identity.name,
        strengths_to_preserve=strengths[:5],
        required_changes=changes,
        allowed_blocker_codes=allowed_codes,
        resubmission_request=(
            "Please keep the current strengths, then upload the revised version "
            "for review."
        ),
    )


def _presentation_context(
    *,
    workspace_id: UUID,
    actor_user_id: UUID,
    run: PreflightRunModel,
    brief: CampaignPackBriefV1,
    operation: AiOperationName,
    model_run_id: UUID,
    payload: dict[str, object],
) -> ViraldyOperationContextV1:
    prompt = get_prompt_package(operation)
    return ViraldyOperationContextV1(
        operation=operation,
        request_id=str(model_run_id),
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        product_context=brief.product_snapshot,
        objective=brief.objective.objective_type,
        source_version_ids=[
            run.ugc_asset_version_id,
            run.campaign_pack_version_id,
        ],
        seller_constraints={
            "claim_guardrails": brief.claim_guardrails.model_dump(mode="json"),
            "rights_note": brief.rights_note.model_dump(mode="json"),
        },
        operation_payload={
            "preflight_run_id": str(run.id),
            "persisted_result": {
                "action_label": run.action_label,
                "structural_score": float(run.structural_score),
                "brief_alignment_score": float(run.brief_alignment_score),
                "final_score": float(run.preflight_score),
                "confidence": run.confidence,
                "strengths": run.strengths_json,
                "blockers": run.blockers_json,
                "fixes": run.fixes_json,
            },
            "presentation_input": payload,
        },
        schema_version=prompt.output_schema_version,
        prompt_version=prompt.prompt_version,
    )


def _seller_summary_validator(
    input_data: SellerDecisionInputV1,
) -> Callable[[BaseModel], None]:
    def validate(output: BaseModel) -> None:
        summary = SellerDecisionSummaryV1.model_validate(output)
        rendered = summary.model_dump_json().casefold()
        if input_data.product_name.casefold() not in rendered:
            raise ValueError("Seller summary omitted the actual product name.")
        if (
            input_data.objective
            and input_data.objective.casefold() not in rendered
        ):
            raise ValueError("Seller summary omitted the campaign objective.")
        if "viral-ready" in rendered:
            raise ValueError("Seller summary used prohibited hype language.")
        if not summary.next_actions[0].strip():
            raise ValueError("Seller summary first next action is not executable.")

    return validate


def _creator_revision_validator(
    input_data: CreatorRevisionInputV2,
) -> Callable[[BaseModel], None]:
    expected_codes = [change.code for change in input_data.required_changes]

    def validate(output: BaseModel) -> None:
        revision = CreatorRevisionMessageV2.model_validate(output)
        if revision.referenced_blocker_codes != expected_codes:
            raise ValueError("Creator message changed the supplied blocker codes.")
        observed_codes = [change.code for change in revision.required_changes]
        if observed_codes != expected_codes:
            raise ValueError("Creator message changed the required fix list.")
        rendered = revision.message.casefold()
        for banned in (
            "make it more viral",
            "make it catchier",
            "make it pop",
            "improve engagement",
            "make the hook stronger",
            "rubric",
            "blocker class",
            "schema",
            "confidence score",
        ):
            if banned in rendered:
                raise ValueError("Creator message contains vague or internal language.")
        for change in input_data.required_changes:
            if change.required_text and change.required_text not in revision.message:
                raise ValueError("Creator message omitted required exact text.")
        if (
            input_data.resubmission_request.rstrip(".").casefold()
            not in revision.message.rstrip(".").casefold()
        ):
            raise ValueError("Creator message omitted resubmission guidance.")

    return validate


async def _complete_presentation_model_run(
    repository: AiModelRunRepository,
    model_run: AiModelRunModel,
    result: StructuredGenerationResult,
    output_summary: dict[str, object],
) -> None:
    await repository.complete(
        model_run,
        output_summary,
        http_status=result.http_status,
        provider_request_id=result.provider_request_id,
        latency_ms=result.latency_ms,
        usage_json=result.usage.model_dump(mode="json"),
        repair_attempt_count=result.repair_attempt_count,
    )


async def _fail_presentation_model_run(
    repository: AiModelRunRepository,
    model_run: AiModelRunModel,
    error: AppError,
) -> None:
    http_status = error.details.get("http_status")
    provider_request_id = error.details.get("provider_request_id")
    repair_attempt_count = error.details.get("repair_attempt_count")
    await repository.fail(
        model_run,
        error.code,
        error.message,
        http_status=http_status if isinstance(http_status, int) else None,
        safe_error_message=error.message,
        provider_request_id=(
            provider_request_id if isinstance(provider_request_id, str) else None
        ),
        repair_attempt_count=(
            repair_attempt_count if isinstance(repair_attempt_count, int) else None
        ),
    )


def _strength_messages(run: PreflightRunModel) -> list[str]:
    return [
        str(item.get("message"))
        for item in _object_list(run.strengths_json)
        if item.get("message")
    ]


def _object_list(values: list[object]) -> list[dict[str, object]]:
    return [value for value in values if isinstance(value, dict)]


def _required_text_for(code: str, brief: CampaignPackBriefV1) -> str | None:
    if "DISCLOSURE" not in code.upper():
        return None
    return (
        brief.claim_guardrails.required_disclosures[0]
        if brief.claim_guardrails.required_disclosures
        else None
    )


def _target_end_for(code: str, brief: CampaignPackBriefV1) -> int | None:
    normalized = code.upper()
    if not any(term in normalized for term in ("PRODUCT", "REVEAL", "TIMING")):
        return None
    deadlines = [
        requirement.expected_before_ms
        for requirement in brief.must_show
        if requirement.requirement_type == "product"
        and requirement.expected_before_ms is not None
    ]
    return min(deadlines) if deadlines else None


def _presentation_action(value: str) -> str:
    return {
        "reject": "reject_or_reshoot",
        "reject_or_reshoot": "reject_or_reshoot",
        "revise": "revise",
        "organic_ready_or_small_paid_test": "small_paid_test",
        "spark_ready_pending_rights": "small_paid_test",
        "small_paid_test": "small_paid_test",
        "ready_for_organic": "ready_for_organic",
    }.get(value, "revise")


def _next_action(value: str) -> str:
    if value in {"spark_ready_pending_rights", "small_paid_test"}:
        return "Confirm usage and Spark rights, then run a limited paid test."
    if value in {"organic_ready_or_small_paid_test", "ready_for_organic"}:
        return "Approve organic posting and attach performance after the test window."
    if value in {"reject", "reject_or_reshoot"}:
        return "Reshoot the required scenes and rerun Preflight."
    return "Apply the required fixes, upload a revised version, and rerun Preflight."


def _hash_json(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
