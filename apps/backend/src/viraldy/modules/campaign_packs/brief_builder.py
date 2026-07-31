from __future__ import annotations

import re
from uuid import UUID

from viraldy.modules.campaign_packs.contracts import (
    CampaignAngleV1,
    CampaignAudienceV1,
    CampaignObjectiveV1,
    CampaignPackBriefV1,
    ClaimGuardrailsV1,
    CreatorDirectionV1,
    CtaDirectionV1,
    HookOptionV1,
    MustShowRequirementV1,
    RightsNoteV1,
    ScriptBeatV1,
    StoryboardSceneV1,
)
from viraldy.modules.products.contracts import ProductContextV1
from viraldy.shared.errors.base import AppError


def build_adaptation_campaign_pack_brief(
    objective: str,
    target_market: str,
    target_buyer: dict[str, object],
    product_snapshot_json: dict[str, object] | None,
    concept: dict[str, object],
    adaptation_run_id: UUID,
    concept_id: str,
) -> CampaignPackBriefV1:
    if not product_snapshot_json:
        raise AppError(
            "PRODUCT_CONTEXT_SNAPSHOT_REQUIRED",
            "Campaign Pack generation requires a typed product context snapshot.",
        )
    product_snapshot = ProductContextV1.model_validate(product_snapshot_json)
    hook_options = _list_of_text(concept.get("hook_options"))
    must_show = _list_of_text(concept.get("must_show"))
    demo_sequence = _list_of_text(concept.get("demo_sequence"))
    claim_guardrails = _list_of_text(concept.get("claim_guardrails"))
    allowed_claims = [
        claim.text for claim in product_snapshot.governance.claims if claim.rule_type == "allowed"
    ]
    qualified_claims = [
        claim.text
        for claim in product_snapshot.governance.claims
        if claim.rule_type == "allowed_with_qualification"
    ]
    prohibited_claims = [
        claim.text
        for claim in product_snapshot.governance.claims
        if claim.rule_type == "prohibited"
    ]
    required_disclosures = [
        claim.text
        for claim in product_snapshot.governance.claims
        if claim.rule_type == "required_disclosure"
    ]
    buyer_persona_id = _buyer_persona_id(product_snapshot, target_buyer, concept)
    buyer_persona_label = _buyer_persona_label(product_snapshot, target_buyer, concept)
    creator_persona = _creator_persona(product_snapshot, concept)
    pain = str(concept.get("buyer_pain") or target_buyer.get("pain") or "documented buyer pain")
    outcome = str(
        concept.get("desired_outcome")
        or target_buyer.get("desired_outcome")
        or "documented product outcome"
    )
    return CampaignPackBriefV1(
        product_snapshot=product_snapshot,
        objective=CampaignObjectiveV1(
            objective_type=objective,
            primary_action="create_ugc_revision",
            channel="tiktok_shop" if "shop" in objective.lower() else "unknown",
        ),
        audience=CampaignAudienceV1(
            persona_id=buyer_persona_id,
            persona_label=buyer_persona_label,
            pain_points=[pain],
            desired_outcomes=[outcome],
            objections=[],
            awareness_stage="unknown",
        ),
        angle=CampaignAngleV1(
            name=str(concept.get("angle") or product_snapshot.identity.name),
            promise=outcome,
            mechanism=str(concept.get("demo_mechanism") or "show product in use"),
            emotional_driver=pain,
        ),
        creator_direction=CreatorDirectionV1(
            persona=creator_persona,
            delivery_style=str(concept.get("delivery_style") or "authentic_review"),
            tone=["clear", "evidence-led"],
            avoid_tones=["overclaiming"],
            authenticity_notes=["show observed use, not performance predictions"],
        ),
        hooks=[
            HookOptionV1(
                id=f"hook_{index}",
                spoken_text=hook,
                opening_visual=str(concept.get("opening_visual") or "show product context"),
                hook_type=str(concept.get("strategic_axis") or "unknown"),
                target_time_ms=0,
                mandatory=index == 1,
            )
            for index, hook in enumerate(
                hook_options or [f"Show {product_snapshot.identity.name}"],
                start=1,
            )
        ],
        script_beats=[
            ScriptBeatV1(
                id=f"beat_{index}",
                sequence=index,
                beat_type="demo" if "demo" in beat.lower() else "scene",
                instruction=beat,
                required=True,
            )
            for index, beat in enumerate(
                demo_sequence or ["show product in use"],
                start=1,
            )
        ],
        storyboard=[
            StoryboardSceneV1(
                id=f"scene_{index}",
                sequence=index,
                instruction=scene,
                shot_type="close_up" if "close" in scene.lower() else "in_use",
                product_visibility_required=("product" in scene.lower() or "use" in scene.lower()),
                required=True,
            )
            for index, scene in enumerate(
                must_show or demo_sequence or ["product in use"],
                start=1,
            )
        ],
        must_show=[
            _must_show_requirement(text, index=index, concept_id=concept_id)
            for index, text in enumerate(
                must_show or ["product visible", "demo in use"],
                start=1,
            )
        ],
        talking_points=[pain, outcome],
        text_overlays=hook_options[:2],
        proof_direction=[str(concept.get("proof_mechanism") or "show observable result")],
        offer_direction=(
            [offer] if (offer := str(concept.get("offer_framing") or "").strip()) else []
        ),
        cta=CtaDirectionV1(
            spoken="Check the product tag if this campaign is for TikTok Shop.",
            overlay="Product tag",
            cta_type="product_tag",
            product_tag_required=True,
            required_before_ms=None,
        ),
        claim_guardrails=ClaimGuardrailsV1(
            allowed=_stable_unique(allowed_claims),
            allowed_with_qualification=_stable_unique(qualified_claims),
            prohibited=_stable_unique(
                [
                    *claim_guardrails,
                    *prohibited_claims,
                    *product_snapshot.governance.prohibited_content,
                ]
            ),
            required_disclosures=_stable_unique(
                [
                    *product_snapshot.governance.required_disclosures,
                    *required_disclosures,
                ]
            ),
        ),
        do=[
            "show product clearly",
            "show observable use",
            "keep claims evidence-backed",
        ],
        dont=[
            "copy the reference script exactly",
            "add unsupported performance claims",
        ],
        rights_note=RightsNoteV1(
            raw_footage_requested=_rights_request(product_snapshot, "raw footage"),
            editing_permission_requested=_rights_request(product_snapshot, "editing"),
            spark_authorization_requested=_rights_request(product_snapshot, "spark"),
            note=" ".join(product_snapshot.governance.rights_notes)
            or "Rights/Spark requests are informational and remain pending until authorized.",
        ),
        revision_checklist=[
            "Product appears clearly",
            "Demo shows product in use",
            "Proof or result is observable",
            "CTA/product tag is included when required",
            "No prohibited claim is included",
        ],
        source_adaptation_run_id=adaptation_run_id,
        source_concept_id=concept_id,
    )


def _list_of_text(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := str(item).strip())]


def _stable_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        key = normalized.casefold()
        if not normalized or key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def _rights_request(product: ProductContextV1, phrase: str) -> bool:
    return any(phrase in note.casefold() for note in product.governance.rights_notes)


def _requirement_type(text: str) -> str:
    lowered = text.lower()
    if "cta" in lowered or "shop" in lowered or "tag" in lowered:
        return "cta"
    if "demo" in lowered or "use" in lowered or "using" in lowered:
        return "demo"
    if "product" in lowered or "close-up" in lowered or "close up" in lowered:
        return "product"
    if "before" in lowered or "after" in lowered or "result" in lowered or "proof" in lowered:
        return "proof"
    if "offer" in lowered or "discount" in lowered or "price" in lowered:
        return "offer"
    if "claim" in lowered or "disclosure" in lowered:
        return "claim"
    if "overlay" in lowered or "caption" in lowered or "text" in lowered:
        return "overlay"
    if "creator" in lowered or "face" in lowered or "voice" in lowered:
        return "creator"
    return "scene"


def _must_show_requirement(
    text: str,
    *,
    index: int,
    concept_id: str,
) -> MustShowRequirementV1:
    requirement_type = _requirement_type(text)
    return MustShowRequirementV1(
        id=f"must_show_{index}",
        requirement_type=requirement_type,
        description=text,
        severity="hard" if "claim" in text.lower() else "high",
        expected_before_ms=_expected_before_ms(text, requirement_type),
        source_path=f"concepts[{concept_id}].must_show[{index - 1}]",
    )


def _expected_before_ms(text: str, requirement_type: str) -> int | None:
    match = re.search(
        r"\b(?:before|by|within)\s+(\d+(?:\.\d+)?)\s*(ms|milliseconds?|s|seconds?)\b",
        text,
        flags=re.IGNORECASE,
    )
    if match is not None:
        value = float(match.group(1))
        unit = match.group(2).casefold()
        return round(value * 1000) if unit in {"s", "second", "seconds"} else round(value)
    if requirement_type == "product" and "visible" in text.casefold():
        return 3000
    return None


def _buyer_persona_id(
    product_snapshot: ProductContextV1,
    target_buyer: dict[str, object],
    concept: dict[str, object],
) -> str | None:
    concept_id = concept.get("buyer_persona_id")
    if concept_id:
        return str(concept_id)
    if product_snapshot.personas:
        return product_snapshot.personas[0].id
    target_id = target_buyer.get("persona_id")
    return str(target_id) if target_id else None


def _buyer_persona_label(
    product_snapshot: ProductContextV1,
    target_buyer: dict[str, object],
    concept: dict[str, object],
) -> str:
    if label := str(concept.get("buyer_persona_label") or "").strip():
        return label
    if product_snapshot.personas:
        return product_snapshot.personas[0].label
    return str(target_buyer.get("persona") or "unspecified buyer")


def _creator_persona(
    product_snapshot: ProductContextV1,
    concept: dict[str, object],
) -> str:
    if persona := str(concept.get("creator_persona") or "").strip():
        return persona
    if product_snapshot.creative.creator_personas:
        return product_snapshot.creative.creator_personas[0]
    return "unspecified creator"
