from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from viraldy.modules.creative_dna.contracts import (
    ClaimDnaV1,
    CreativeDnaV1,
    CreatorDnaV1,
    CtaDnaV1,
    DemoDnaV1,
    EditingDnaV1,
    ObservedValueV1,
    OfferDnaV1,
    OpeningDnaV1,
    PlatformDnaV1,
    ProductDnaV1,
    ProofDnaV1,
    ReusableMechanismV1,
    RiskDnaV1,
)
from viraldy.modules.creative_dna.repository import CreativeDnaRepository, SyncCreativeDnaRepository
from viraldy.modules.creative_dna.schemas import CreativeDnaVersionResponse
from viraldy.modules.creative_dna.taxonomy import (
    CREATIVE_DNA_PROMPT_VERSION,
    CREATIVE_DNA_TAXONOMY_VERSION,
)
from viraldy.modules.media_analysis.public import EvidenceItemModel
from viraldy.shared.errors.base import NotFoundError


class CreativeDnaService:
    def __init__(self, session: AsyncSession) -> None:
        self._repository = CreativeDnaRepository(session)

    async def get(self, workspace_id: UUID, dna_version_id: UUID) -> CreativeDnaVersionResponse:
        dna = await self._repository.get(workspace_id, dna_version_id)
        if dna is None:
            raise NotFoundError("CREATIVE_DNA_NOT_FOUND", "Creative DNA version was not found.")
        return CreativeDnaVersionResponse.model_validate(dna)

    async def latest_for_reference(
        self, workspace_id: UUID, reference_id: UUID
    ) -> CreativeDnaVersionResponse:
        dna = await self._repository.latest_for_reference(workspace_id, reference_id)
        if dna is None:
            raise NotFoundError("CREATIVE_DNA_NOT_FOUND", "Creative DNA version was not found.")
        return CreativeDnaVersionResponse.model_validate(dna)


class SyncCreativeDnaBuilder:
    def __init__(self, session: Session) -> None:
        self._repository = SyncCreativeDnaRepository(session)

    def build(
        self,
        workspace_id: UUID,
        asset_version_id: UUID,
        reference_id: UUID | None,
        evidence: list[EvidenceItemModel],
        analysis_mode: str,
    ):
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
            taxonomy_version=CREATIVE_DNA_TAXONOMY_VERSION,
            model_version="fixture_creative_dna_v1" if analysis_mode == "fixture" else None,
            prompt_version=CREATIVE_DNA_PROMPT_VERSION,
        )


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
        "angle": _observed(hook, value.get("hook_type")),
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
    return EditingDnaV1(
        cut_count=_observed(item, value.get("cut_count")),
        average_shot_duration_ms=_observed(item, value.get("average_shot_duration_ms")),
        first_three_second_cut_count=_observed(item, value.get("first_three_second_cut_count")),
        pacing=_observed(item, value.get("visual_pacing")),
        caption_density=_observed(item, value.get("caption_density")),
        dead_air_present=_unknown(),
        transition_types=_observed(item, value.get("transition_types")),
    )


def _offer_dna(items: list[EvidenceItemModel]) -> OfferDnaV1:
    first = _first_item(items)
    offer_types = [str(item.value_json.get("offer_type")) for item in items]
    return OfferDnaV1(
        present=_observed(first, bool(items) if items else None),
        offer_types=_observed(first, offer_types if offer_types else None),
        price_text=_observed(first, _value(first, "price_text")),
        discount_text=_observed(first, _value(first, "text")),
        urgency_present=_unknown(),
    )


def _cta_dna(items: list[EvidenceItemModel]) -> CtaDnaV1:
    first = _first_item(items)
    cta_types = [str(item.value_json.get("cta_type")) for item in items]
    return CtaDnaV1(
        present=_observed(first, bool(items) if items else None),
        cta_types=_observed(first, cta_types if cta_types else None),
        first_appearance_ms=_observed(first, first.start_ms if first else None),
        spoken_text=_observed(first, _value(first, "text")),
        overlay_text=_unknown(),
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
                severity=risk,  # type: ignore[arg-type]
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


def _observed(item: EvidenceItemModel | None, value: object) -> ObservedValueV1:
    if item is None:
        return _unknown()
    if value is None or value == "unknown":
        return ObservedValueV1(
            value=None, confidence=_confidence(item), evidence_ids=[item.id], status="unknown"
        )
    return ObservedValueV1(
        value=value,
        confidence=_confidence(item),
        evidence_ids=[item.id],
        status="observed",
    )


def _unknown() -> ObservedValueV1:
    return ObservedValueV1(value=None, confidence=0, evidence_ids=[], status="unknown")


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
