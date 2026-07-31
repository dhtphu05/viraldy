from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from viraldy.modules.ai_gateway.models import AiModelRunModel
from viraldy.modules.ai_gateway.prompt_packages import (
    CREATIVE_DNA_PROMPT_NAME,
    CREATIVE_DNA_PROMPT_VERSION,
)
from viraldy.modules.ai_gateway.repository import SyncAiModelRunRepository
from viraldy.modules.creative_dna import taxonomy as creative_dna_taxonomy
from viraldy.modules.creative_dna.contracts import (
    ClaimDnaV1,
    CreativeDnaV1,
    CreatorDnaV1,
    CtaDnaV1,
    DemoDnaV1,
    EditingDnaV1,
    OfferDnaV1,
    OpeningDnaV1,
    PlatformDnaV1,
    ProductDnaV1,
    ProofDnaV1,
    ReusableMechanismV1,
    RiskDnaV1,
)
from viraldy.modules.creative_dna.models import CreativeDnaVersionModel
from viraldy.modules.creative_dna.provider import LiveCreativeDnaProvider
from viraldy.modules.creative_dna.repository import CreativeDnaRepository, SyncCreativeDnaRepository
from viraldy.modules.creative_dna.schemas import CreativeDnaVersionResponse
from viraldy.modules.creative_domain.schema_versions import CREATIVE_DNA_SCHEMA_VERSION
from viraldy.modules.media_analysis.public import EvidenceItemModel
from viraldy.modules.product_events.public import ProductEventPublisher
from viraldy.modules.products.public import SyncProductQueries
from viraldy.platform.config.settings import Settings, get_settings
from viraldy.shared.errors.base import AppError, NotFoundError


class CreativeDnaService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = CreativeDnaRepository(session)

    async def get(
        self,
        workspace_id: UUID,
        dna_version_id: UUID,
        user_id: UUID,
    ) -> CreativeDnaVersionResponse:
        dna = await self._repository.get(workspace_id, dna_version_id)
        if dna is None:
            raise NotFoundError("CREATIVE_DNA_NOT_FOUND", "Creative DNA version was not found.")
        response = CreativeDnaVersionResponse.model_validate(dna)
        await self._record_view(workspace_id, user_id, response)
        return response

    async def latest_for_reference(
        self,
        workspace_id: UUID,
        reference_id: UUID,
        user_id: UUID,
    ) -> CreativeDnaVersionResponse:
        dna = await self._repository.latest_for_reference(workspace_id, reference_id)
        if dna is None:
            raise NotFoundError("CREATIVE_DNA_NOT_FOUND", "Creative DNA version was not found.")
        response = CreativeDnaVersionResponse.model_validate(dna)
        await self._record_view(workspace_id, user_id, response)
        return response

    async def _record_view(
        self,
        workspace_id: UUID,
        user_id: UUID,
        dna: CreativeDnaVersionResponse,
    ) -> None:
        await ProductEventPublisher(self._session).record(
            event_type="creative_dna_viewed",
            workspace_id=workspace_id,
            actor_user_id=user_id,
            subject_type="creative_dna",
            subject_id=dna.id,
            payload_json={
                "reference_id": str(dna.reference_id) if dna.reference_id else None,
                "version_number": dna.version_number,
            },
        )
        await self._session.commit()


class SyncCreativeDnaBuilder:
    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._repository = SyncCreativeDnaRepository(session)

    def build(
        self,
        workspace_id: UUID,
        asset_version_id: UUID,
        reference_id: UUID | None,
        evidence: list[EvidenceItemModel],
        analysis_mode: str,
        *,
        asset_id: UUID | None = None,
        processing_job_id: UUID | None = None,
        actor_user_id: UUID | None = None,
        product_id: UUID | None = None,
        media_duration_ms: int | None = None,
        attempt_count: int = 1,
    ) -> CreativeDnaVersionModel:
        if processing_job_id is not None:
            existing = self._repository.for_processing_job(
                workspace_id,
                asset_version_id,
                processing_job_id,
            )
            if existing is not None:
                return existing
        if analysis_mode != self._settings.ai_mode:
            raise AppError(
                "CREATIVE_DNA_AI_MODE_INVALID",
                "Creative DNA analysis mode does not match configured AI mode.",
            )
        if analysis_mode != "fixture":
            if asset_id is None:
                raise AppError(
                    "CREATIVE_DNA_SOURCE_INVALID",
                    "AI Creative DNA requires a source asset ID.",
                )
            return self._build_with_ai(
                workspace_id=workspace_id,
                asset_id=asset_id,
                asset_version_id=asset_version_id,
                reference_id=reference_id,
                evidence=evidence,
                processing_job_id=processing_job_id,
                actor_user_id=actor_user_id,
                product_id=product_id,
                media_duration_ms=media_duration_ms,
                attempt_count=attempt_count,
            )
        evidence_by_type = _evidence_by_type(evidence)
        dna = _build_creative_dna(evidence_by_type)
        dna_json = dna.model_dump(mode="json")
        return self._repository.create(
            workspace_id=workspace_id,
            reference_id=reference_id,
            asset_version_id=asset_version_id,
            dna_json=dna_json,
            confidence=dna.overall_confidence,
            analysis_mode=analysis_mode,
            taxonomy_version=creative_dna_taxonomy.CREATIVE_DNA_TAXONOMY_VERSION,
            model_version="fixture_creative_dna_v1",
            prompt_version=creative_dna_taxonomy.CREATIVE_DNA_PROMPT_VERSION,
            processing_job_id=processing_job_id,
        )

    def _build_with_ai(
        self,
        *,
        workspace_id: UUID,
        asset_id: UUID,
        asset_version_id: UUID,
        reference_id: UUID | None,
        evidence: list[EvidenceItemModel],
        processing_job_id: UUID | None,
        actor_user_id: UUID | None,
        product_id: UUID | None,
        media_duration_ms: int | None,
        attempt_count: int,
    ) -> CreativeDnaVersionModel:
        product_snapshot = None
        if product_id is not None:
            product_snapshot = SyncProductQueries(self._session).get_product_context_snapshot(
                workspace_id,
                product_id,
            )
            if product_snapshot is None:
                raise AppError(
                    "CREATIVE_DNA_PRODUCT_CONTEXT_NOT_FOUND",
                    "Creative DNA source product context was not found.",
                )
        dna_version_id = uuid4()
        model_name = _creative_dna_model_name(self._settings)
        input_summary: dict[str, object] = {
            "asset_id": str(asset_id),
            "asset_version_id": str(asset_version_id),
            "creative_dna_version_id": str(dna_version_id),
            "evidence_count": len(evidence),
            "evidence_ids": [str(item.id) for item in evidence],
            "evidence_types": sorted({item.evidence_type for item in evidence}),
            "media_duration_ms": media_duration_ms,
            "product_context_version": (
                product_snapshot.product_context_version if product_snapshot else None
            ),
            "reference_id": str(reference_id) if reference_id else None,
        }
        request_hash = _hash_json(
            {
                "operation": "creative_dna_build",
                "prompt_version": CREATIVE_DNA_PROMPT_VERSION,
                "input": input_summary,
            }
        )
        model_repo = SyncAiModelRunRepository(self._session)
        model_run = model_repo.create_running(
            workspace_id=workspace_id,
            processing_job_id=processing_job_id,
            subject_type="creative_dna_version",
            subject_id=dna_version_id,
            capability="creative_dna_build",
            operation="creative_dna_build",
            analysis_mode=self._settings.ai_mode,
            provider=self._settings.ai_provider,
            model=model_name,
            prompt_version=CREATIVE_DNA_PROMPT_VERSION,
            response_schema_version=CREATIVE_DNA_SCHEMA_VERSION,
            schema_version=CREATIVE_DNA_SCHEMA_VERSION,
            request_hash=request_hash,
            input_hash=request_hash,
            input_summary=input_summary,
            attempt_count=max(1, attempt_count),
            endpoint_family=(
                "responses"
                if self._settings.ai_provider == "openai"
                else "chat_completions"
            ),
            prompt_name=CREATIVE_DNA_PROMPT_NAME,
        )
        model_run.attempt = max(1, attempt_count)
        self._session.commit()
        try:
            execution = LiveCreativeDnaProvider(self._settings).build_with_metadata(
                workspace_id=workspace_id,
                actor_user_id=actor_user_id,
                asset_id=asset_id,
                asset_version_id=asset_version_id,
                reference_id=reference_id,
                evidence=evidence,
                model_run_id=model_run.id,
                media_duration_ms=media_duration_ms,
                product_context=(
                    product_snapshot.product_context if product_snapshot else None
                ),
                product_context_version=(
                    product_snapshot.product_context_version if product_snapshot else None
                ),
            )
            dna = execution.output
            version = self._repository.create(
                workspace_id=workspace_id,
                reference_id=reference_id,
                asset_version_id=asset_version_id,
                dna_json=dna.model_dump(mode="json"),
                confidence=dna.overall_confidence,
                analysis_mode=self._settings.ai_mode,
                taxonomy_version=creative_dna_taxonomy.CREATIVE_DNA_TAXONOMY_VERSION,
                model_version=model_name,
                prompt_version=CREATIVE_DNA_PROMPT_VERSION,
                dna_version_id=dna_version_id,
                processing_job_id=processing_job_id,
                primary_model_run_id=model_run.id,
            )
            model_repo.complete(
                model_run,
                _creative_dna_output_summary(dna),
                http_status=execution.http_status,
                provider_request_id=execution.provider_request_id,
                latency_ms=execution.latency_ms,
                usage_json=execution.usage_json,
                repair_attempt_count=execution.repair_attempt_count,
            )
            self._session.commit()
            return version
        except AppError as exc:
            _fail_creative_dna_model_run(model_repo, model_run, exc)
            self._session.commit()
            raise
        except Exception:
            self._session.rollback()
            persisted_run = self._session.get(AiModelRunModel, model_run.id)
            if persisted_run is not None:
                model_repo.fail(
                    persisted_run,
                    "CREATIVE_DNA_BUILD_FAILED",
                    "Creative DNA build failed.",
                    safe_error_message="Creative DNA build failed.",
                )
                self._session.commit()
            raise


def _creative_dna_model_name(settings: Settings) -> str:
    if settings.ai_provider == "openai":
        return settings.resolve_openai_model("creative_dna_build")
    return settings.ai_text_model or "unconfigured"


def _creative_dna_output_summary(dna: CreativeDnaV1) -> dict[str, object]:
    return {
        "claim_count": len(dna.claims),
        "complete_section_count": sum(dna.completeness.model_dump().values()),
        "overall_confidence": dna.overall_confidence,
        "reusable_mechanism_count": len(dna.reusable_mechanisms),
        "risk_count": len(dna.risks),
        "uncertainty_count": len(dna.uncertainties),
    }


def _fail_creative_dna_model_run(
    repository: SyncAiModelRunRepository,
    model_run: AiModelRunModel,
    error: AppError,
) -> None:
    http_status = error.details.get("http_status")
    provider_request_id = error.details.get("provider_request_id")
    repair_attempt_count = error.details.get("repair_attempt_count")
    repository.fail(
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


def _hash_json(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _build_creative_dna(
    grouped: dict[str, list[EvidenceItemModel]],
) -> CreativeDnaV1:
    hook = _first(grouped, "hook_signal")
    product_summary = _first(grouped, "product_visibility_summary")
    product_appearances = grouped.get("product_appearance", []) + grouped.get(
        "product_first_appearance", []
    )
    demo_summary = _first(grouped, "demo_summary") or _first(grouped, "demo_signal")
    demo_steps = grouped.get("demo_step", [])
    proof_items = grouped.get("proof_signal", [])
    offer_items = grouped.get("offer_signal", [])
    cta_items = grouped.get("cta_signal", [])
    creator = _first(grouped, "creator_signal")
    editing = _first(grouped, "editing_signal")
    platform = _first(grouped, "platform_signal")
    claims = grouped.get("claim_signal", [])
    completeness = {
        "opening": hook is not None,
        "product": bool(product_appearances) or product_summary is not None,
        "demo": demo_summary is not None or bool(demo_steps),
        "proof": bool(proof_items),
        "cta": bool(cta_items),
        "creator": creator is not None,
        "editing": editing is not None,
        "platform": platform is not None,
    }
    dna = CreativeDnaV1(
        opening=_opening_dna(hook),
        product=_product_dna(product_summary, product_appearances),
        narrative=_narrative_dna(hook, demo_summary),
        demo=_demo_dna(demo_summary, demo_steps),
        proof=_proof_dna(proof_items),
        creator=_creator_dna(creator),
        editing=_editing_dna(editing),
        offer=_offer_dna(offer_items),
        cta=_cta_dna(cta_items),
        platform=_platform_dna(platform),
        claims=_claim_dna(claims),
        risks=_risk_dna(claims),
        reusable_mechanisms=_reusable_mechanisms(hook, demo_summary, proof_items),
        uncertainties=_uncertainties(completeness),
        completeness=completeness,
        overall_confidence=_overall_confidence(completeness, grouped),
    )
    return dna


def _opening_dna(hook: EvidenceItemModel | None) -> OpeningDnaV1:
    value = hook.value_json if hook else {}
    hook_text = value.get("spoken_text") or value.get("overlay_text") or value.get("text")
    first_three = "hook_present" if hook and (hook.start_ms or 0) <= 3000 else "unknown"
    return OpeningDnaV1(
        primary_hook_type=_observed(hook, value.get("hook_type")),
        hook_text=_observed(hook, hook_text),
        opening_visual=_observed(hook, value.get("visual_description")),
        buyer_pain=_observed(hook, value.get("buyer_pain")),
        face_present=_observed(hook, value.get("face_present")),
        product_present=_observed(hook, value.get("product_present")),
        first_three_second_structure=_observed(hook, first_three if hook else None),
        pattern_interrupts=_unknown(),
    )


def _product_dna(
    summary: EvidenceItemModel | None,
    appearances: list[EvidenceItemModel],
) -> ProductDnaV1:
    first_appearance = _first_product_ms(summary, appearances)
    appearance_values = [item.value_json for item in appearances]
    close_up = _first_bool(
        summary,
        "clear_close_up_present",
        any(item.get("shot_type") in {"hero", "close_up"} for item in appearance_values),
    )
    usage = _first_bool(
        summary,
        "usage_present",
        any(bool(item.get("usage_visible")) for item in appearance_values),
    )
    return ProductDnaV1(
        first_appearance_ms=_observed(summary or _first_item(appearances), first_appearance),
        total_visible_ms=_observed(summary, _value(summary, "total_visible_ms")),
        screen_time_ratio=_observed(summary, _value(summary, "screen_time_ratio")),
        close_up_present=_observed(summary or _first_item(appearances), close_up),
        hero_shot_present=_observed(
            _first_item(appearances),
            any(item.get("shot_type") == "hero" for item in appearance_values),
        ),
        usage_present=_observed(summary or _first_item(appearances), usage),
        product_match=_observed(
            _first_item(appearances),
            _value(_first_item(appearances), "product_match_confidence"),
        ),
        appearance_sequence=_observed(
            _first_item(appearances),
            [
                {
                    "start_ms": item.start_ms,
                    "end_ms": item.end_ms,
                    "visibility": item.value_json.get("visibility"),
                    "shot_type": item.value_json.get("shot_type"),
                }
                for item in appearances
            ]
            if appearances
            else None,
        ),
    )


def _narrative_dna(
    hook: EvidenceItemModel | None,
    demo: EvidenceItemModel | None,
) -> Any:
    value = hook.value_json if hook else {}
    structure = "hook_demo_result" if hook and demo else None
    return {
        "structure": _observed(hook or demo, structure),
        "angle": _unknown(),
        "buyer_pain": _observed(hook, value.get("buyer_pain")),
        "desired_outcome": _unknown(),
        "emotional_drivers": _unknown(),
        "awareness_stage": _unknown(),
    }


def _demo_dna(summary: EvidenceItemModel | None, steps: list[EvidenceItemModel]) -> DemoDnaV1:
    value = summary.value_json if summary else {}
    detected = bool(summary or steps)
    return DemoDnaV1(
        detected=_observed(summary or _first_item(steps), detected if detected else None),
        demo_type=_observed(summary, value.get("demo_type")),
        mechanism_clarity=_observed(summary, value.get("mechanism_clarity")),
        before_state_visible=_observed(summary, value.get("before_state_visible")),
        after_state_visible=_observed(summary, value.get("after_state_visible")),
        result_clarity=_observed(summary, "visible" if value.get("after_state_visible") else None),
        steps=_observed(
            _first_item(steps),
            [
                {
                    "step_index": step.value_json.get("step_index"),
                    "action": step.value_json.get("action"),
                    "start_ms": step.start_ms,
                    "end_ms": step.end_ms,
                }
                for step in steps
            ]
            if steps
            else None,
        ),
    )


def _proof_dna(items: list[EvidenceItemModel]) -> ProofDnaV1:
    first = _first_item(items)
    proof_types = [str(item.value_json.get("proof_type")) for item in items]
    verifiability = _value(first, "verifiability")
    strength = "high" if verifiability == "observable" else "medium" if items else None
    return ProofDnaV1(
        proof_types=_observed(first, proof_types if proof_types else None),
        strongest_proof=_observed(first, proof_types[0] if proof_types else None),
        verifiability=_observed(first, verifiability),
        proof_strength_label=_observed(first, strength),
    )


def _creator_dna(item: EvidenceItemModel | None) -> CreatorDnaV1:
    value = item.value_json if item else {}
    return CreatorDnaV1(
        face_present=_observed(item, value.get("face_present")),
        delivery_style=_observed(item, value.get("delivery_style")),
        creator_persona=_observed(item, value.get("creator_persona")),
        emotion=_observed(item, value.get("emotion")),
        pacing=_observed(item, value.get("pacing")),
        authenticity_cues=_observed(item, value.get("authenticity_cues")),
        sales_language_intensity=_observed(item, value.get("sales_language_intensity")),
    )


def _editing_dna(item: EvidenceItemModel | None) -> EditingDnaV1:
    value = item.value_json if item else {}
    pattern_interrupts = value.get("pattern_interrupts")
    dead_air_ranges = value.get("dead_air_ranges")
    return EditingDnaV1(
        cut_count=_observed(item, value.get("cut_count")),
        average_shot_duration_ms=_observed(item, value.get("average_shot_duration_ms")),
        first_three_second_cut_count=_observed(item, value.get("first_three_second_cut_count")),
        pacing=_observed(item, value.get("visual_pacing")),
        caption_density=_observed(item, value.get("caption_density")),
        pattern_interrupts=_observed(
            item, pattern_interrupts if isinstance(pattern_interrupts, list) else []
        ),
        dead_air_ranges=_observed(
            item, dead_air_ranges if isinstance(dead_air_ranges, list) else []
        ),
        dead_air_present=_observed(
            item, bool(dead_air_ranges) if isinstance(dead_air_ranges, list) else None
        ),
        transition_types=_observed(item, value.get("transition_types")),
    )


def _offer_dna(items: list[EvidenceItemModel]) -> OfferDnaV1:
    first = _first_item(items)
    offer_types = [str(item.value_json.get("offer_type")) for item in items]
    return OfferDnaV1(
        present=_observed(first, bool(items) if items else None),
        offer_types=_observed(first, offer_types if offer_types else None),
        price_text=_observed(first, _value(first, "price_text")),
        discount_text=_observed(first, _value(first, "discount_text") or _value(first, "text")),
        urgency_present=_observed(first, _value(first, "urgency_present")),
    )


def _cta_dna(items: list[EvidenceItemModel]) -> CtaDnaV1:
    first = _first_item(items)
    cta_types = [str(item.value_json.get("cta_type")) for item in items]
    spoken_text = _value(first, "spoken_text")
    if spoken_text is None and first and first.value_json.get("modality") in {"spoken", "mixed"}:
        spoken_text = _value(first, "text")
    overlay_text = _value(first, "overlay_text")
    if overlay_text is None and first and first.value_json.get("modality") in {"overlay", "mixed"}:
        overlay_text = _value(first, "text")
    return CtaDnaV1(
        present=_observed(first, bool(items) if items else None),
        cta_types=_observed(first, cta_types if cta_types else None),
        first_appearance_ms=_observed(first, first.start_ms if first else None),
        spoken_text=_observed(first, spoken_text),
        overlay_text=_observed(first, overlay_text),
        product_tag_visible=_observed(first, _value(first, "product_tag_visible")),
    )


def _platform_dna(item: EvidenceItemModel | None) -> PlatformDnaV1:
    value = item.value_json if item else {}
    return PlatformDnaV1(
        vertical=_observed(item, value.get("vertical")),
        native_signals=_observed(item, value.get("native_signals")),
        shop_signals=_observed(item, value.get("shop_signals")),
        safe_zone_risk=_observed(item, value.get("visual_safe_zone_risk")),
        format=_observed(item, value.get("aspect_ratio")),
    )


def _claim_dna(items: list[EvidenceItemModel]) -> list[ClaimDnaV1]:
    return [
        ClaimDnaV1(
            text=str(item.value_json.get("text") or ""),
            risk=str(item.value_json.get("risk") or "unknown"),
            category=str(item.value_json.get("category") or "unknown"),
            qualification_present=bool(item.value_json.get("qualification_present")),
            evidence_ids=[item.id],
        )
        for item in items
        if item.value_json.get("text")
    ]


def _risk_dna(items: list[EvidenceItemModel]) -> list[RiskDnaV1]:
    risks: list[RiskDnaV1] = []
    for item in items:
        risk = str(item.value_json.get("risk") or "unknown")
        if risk not in {"medium", "high", "critical"}:
            continue
        risks.append(
            RiskDnaV1(
                code=f"{risk.upper()}_RISK_CLAIM",
                severity=risk,
                message="Claim requires review against product governance before reuse.",
                evidence_ids=[item.id],
            )
        )
    return risks


def _reusable_mechanisms(
    hook: EvidenceItemModel | None,
    demo: EvidenceItemModel | None,
    proof_items: list[EvidenceItemModel],
) -> list[ReusableMechanismV1]:
    mechanisms: list[ReusableMechanismV1] = []
    if hook is not None:
        mechanisms.append(
            ReusableMechanismV1(
                mechanism_type="opening_hook",
                description=f"Opening uses {hook.value_json.get('hook_type') or 'observed'} hook.",
                evidence_ids=[hook.id],
            )
        )
    if demo is not None:
        mechanisms.append(
            ReusableMechanismV1(
                mechanism_type="demo_structure",
                description=(
                    f"Demo uses {demo.value_json.get('demo_type') or 'observed'} structure."
                ),
                evidence_ids=[demo.id],
            )
        )
    if proof_items:
        mechanisms.append(
            ReusableMechanismV1(
                mechanism_type="proof_moment",
                description="Proof moment is supported by observed evidence.",
                evidence_ids=[item.id for item in proof_items],
            )
        )
    return mechanisms


def _observed(item: EvidenceItemModel | None, value: object) -> dict[str, object]:
    if item is None:
        return _unknown()
    if value is None or value == "unknown":
        return {
            "value": None,
            "confidence": _confidence(item),
            "evidence_ids": [item.id],
            "status": "unknown",
        }
    return {
        "value": value,
        "confidence": _confidence(item),
        "evidence_ids": [item.id],
        "status": "observed",
    }


def _unknown() -> dict[str, object]:
    return {"value": None, "confidence": 0, "evidence_ids": [], "status": "unknown"}


def _confidence(item: EvidenceItemModel) -> float:
    raw = item.value_json.get("confidence")
    if isinstance(raw, int | float):
        return max(0, min(1, float(raw)))
    if item.confidence is None:
        return 0.5
    return max(0, min(1, float(item.confidence)))


def _value(item: EvidenceItemModel | None, key: str) -> object:
    return None if item is None else item.value_json.get(key)


def _first_bool(item: EvidenceItemModel | None, key: str, fallback: bool) -> bool | None:
    value = _value(item, key)
    return bool(value) if isinstance(value, bool) else fallback


def _first_item(items: list[EvidenceItemModel]) -> EvidenceItemModel | None:
    return items[0] if items else None


def _first(
    grouped: dict[str, list[EvidenceItemModel]], evidence_type: str
) -> EvidenceItemModel | None:
    return _first_item(grouped.get(evidence_type, []))


def _first_product_ms(
    summary: EvidenceItemModel | None,
    appearances: list[EvidenceItemModel],
) -> int | None:
    value = _value(summary, "first_appearance_ms")
    if isinstance(value, int | float):
        return int(value)
    starts = [item.start_ms for item in appearances if item.start_ms is not None]
    return min(starts) if starts else None


def _uncertainties(completeness: dict[str, bool]) -> list[str]:
    return [f"{name}_not_observed" for name, present in completeness.items() if not present]


def _overall_confidence(
    completeness: dict[str, bool],
    grouped: dict[str, list[EvidenceItemModel]],
) -> str:
    required = ["opening", "product", "demo", "proof"]
    missing = [name for name in required if not completeness.get(name)]
    if len(missing) >= 2:
        return "low"
    if missing:
        return "medium"
    confidences = [_confidence(item) for items in grouped.values() for item in items]
    if confidences and sum(confidences) / len(confidences) >= 0.75:
        return "high"
    return "medium"


def _evidence_by_type(evidence: list[EvidenceItemModel]) -> dict[str, list[EvidenceItemModel]]:
    grouped: dict[str, list[EvidenceItemModel]] = {}
    for item in evidence:
        grouped.setdefault(item.evidence_type, []).append(item)
    return grouped


def _ids(grouped: dict[str, list[EvidenceItemModel]], evidence_type: str) -> list[str]:
    return [str(item.id) for item in grouped.get(evidence_type, [])]


def _first_value(
    grouped: dict[str, list[EvidenceItemModel]],
    evidence_type: str,
    key: str,
    default: int,
) -> int:
    items = grouped.get(evidence_type, [])
    if not items:
        return default
    value = items[0].value_json.get(key)
    return int(value) if isinstance(value, int | float) else default
