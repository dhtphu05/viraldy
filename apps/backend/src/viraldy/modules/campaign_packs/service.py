from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.adaptations.public import AdaptationRepository
from viraldy.modules.ai_gateway.public import ADAPTATION_SCHEMA_VERSION
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
from viraldy.modules.campaign_packs.repository import CampaignPackRepository
from viraldy.modules.campaign_packs.requirements import (
    compile_campaign_requirements,
    compiled_requirements_to_json,
)
from viraldy.modules.campaign_packs.schemas import (
    CampaignPackResponse,
    CampaignPackVersionResponse,
    CreateCampaignPackRequest,
    CreateCampaignPackVersionRequest,
    UpdateCampaignPackRequest,
)
from viraldy.modules.creative_domain.schema_versions import COMPILED_REQUIREMENTS_SCHEMA_VERSION
from viraldy.modules.products.contracts import ProductContextV1
from viraldy.shared.errors.base import AppError, NotFoundError


class CampaignPackService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = CampaignPackRepository(session)
        self._adaptations = AdaptationRepository(session)

    async def create(
        self,
        workspace_id: UUID,
        user_id: UUID,
        data: CreateCampaignPackRequest,
    ) -> CampaignPackResponse:
        adaptation = await self._adaptations.get(workspace_id, data.adaptation_run_id)
        if adaptation is None:
            raise NotFoundError("ADAPTATION_NOT_FOUND", "Adaptation run was not found.")
        concept = _find_concept(adaptation.result_json, data.concept_id)
        if concept is None:
            raise NotFoundError("ADAPTATION_CONCEPT_NOT_FOUND", "Adaptation concept was not found.")
        brief = _brief_from_concept(
            adaptation.objective,
            adaptation.target_market,
            adaptation.target_buyer_json,
            adaptation.product_snapshot_json,
            concept,
            adaptation.id,
            data.concept_id,
        )
        compiled = compile_campaign_requirements(brief.model_dump(mode="json"))
        pack, version = await self._repository.create(
            workspace_id,
            user_id,
            adaptation.product_id,
            adaptation.id,
            brief.model_dump(mode="json"),
            adaptation.primary_model_run_id,
            adaptation.prompt_version,
            ADAPTATION_SCHEMA_VERSION,
            brief.product_snapshot.model_dump(mode="json"),
            compiled_requirements_to_json(compiled),
            COMPILED_REQUIREMENTS_SCHEMA_VERSION,
        )
        await self._session.commit()
        await self._session.refresh(pack)
        await self._session.refresh(version)
        return _pack_response(pack, version)

    async def list(self, workspace_id: UUID) -> list[CampaignPackResponse]:
        packs = await self._repository.list(workspace_id)
        responses = []
        for pack in packs:
            version = (
                await self._repository.get_version(pack.current_version_id)
                if pack.current_version_id
                else None
            )
            responses.append(_pack_response(pack, version))
        return responses

    async def get(self, workspace_id: UUID, pack_id: UUID) -> CampaignPackResponse:
        pack = await self._repository.get(workspace_id, pack_id)
        if pack is None:
            raise NotFoundError("CAMPAIGN_PACK_NOT_FOUND", "Campaign Pack was not found.")
        version = (
            await self._repository.get_version(pack.current_version_id)
            if pack.current_version_id
            else None
        )
        return _pack_response(pack, version)

    async def update(
        self,
        workspace_id: UUID,
        pack_id: UUID,
        data: UpdateCampaignPackRequest,
    ) -> CampaignPackResponse:
        pack = await self._repository.get(workspace_id, pack_id)
        if pack is None:
            raise NotFoundError("CAMPAIGN_PACK_NOT_FOUND", "Campaign Pack was not found.")
        if data.status is not None:
            pack.status = data.status
        await self._session.commit()
        await self._session.refresh(pack)
        version = (
            await self._repository.get_version(pack.current_version_id)
            if pack.current_version_id
            else None
        )
        return _pack_response(pack, version)

    async def create_version(
        self,
        workspace_id: UUID,
        pack_id: UUID,
        user_id: UUID,
        data: CreateCampaignPackVersionRequest,
    ) -> CampaignPackVersionResponse:
        pack = await self._repository.get(workspace_id, pack_id)
        if pack is None:
            raise NotFoundError("CAMPAIGN_PACK_NOT_FOUND", "Campaign Pack was not found.")
        brief = data.brief
        compiled = compile_campaign_requirements(brief.model_dump(mode="json"))
        version = await self._repository.create_version(
            pack,
            user_id,
            brief.model_dump(mode="json"),
            data.change_note,
            brief.product_snapshot.model_dump(mode="json"),
            compiled_requirements_to_json(compiled),
            COMPILED_REQUIREMENTS_SCHEMA_VERSION,
        )
        await self._session.commit()
        await self._session.refresh(version)
        return CampaignPackVersionResponse.model_validate(version)

    async def list_versions(
        self, workspace_id: UUID, pack_id: UUID
    ) -> list[CampaignPackVersionResponse]:
        pack = await self._repository.get(workspace_id, pack_id)
        if pack is None:
            raise NotFoundError("CAMPAIGN_PACK_NOT_FOUND", "Campaign Pack was not found.")
        versions = await self._repository.list_versions(pack_id)
        return [CampaignPackVersionResponse.model_validate(version) for version in versions]


def _pack_response(pack, version) -> CampaignPackResponse:
    return CampaignPackResponse.model_validate(
        {
            "id": pack.id,
            "workspace_id": pack.workspace_id,
            "product_id": pack.product_id,
            "adaptation_run_id": pack.adaptation_run_id,
            "status": pack.status,
            "current_version_id": pack.current_version_id,
            "created_at": pack.created_at,
            "updated_at": pack.updated_at,
            "current_version": CampaignPackVersionResponse.model_validate(version)
            if version
            else None,
        }
    )


def _find_concept(result_json: dict[str, object], concept_id: str) -> dict[str, object] | None:
    concepts = result_json.get("concepts", [])
    if not isinstance(concepts, list):
        return None
    for concept in concepts:
        if isinstance(concept, dict) and concept.get("id") == concept_id:
            return concept
    return None


def _brief_from_concept(
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
                hook_options or [f"Show {product_snapshot.identity.name}"], start=1
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
            for index, beat in enumerate(demo_sequence or ["show product in use"], start=1)
        ],
        storyboard=[
            StoryboardSceneV1(
                id=f"scene_{index}",
                sequence=index,
                instruction=scene,
                shot_type="close_up" if "close" in scene.lower() else "in_use",
                product_visibility_required="product" in scene.lower() or "use" in scene.lower(),
                required=True,
            )
            for index, scene in enumerate(must_show or demo_sequence or ["product in use"], start=1)
        ],
        must_show=[
            MustShowRequirementV1(
                id=f"must_show_{index}",
                requirement_type=_requirement_type(text),
                description=text,
                severity="hard" if "claim" in text.lower() else "high",
                expected_before_ms=3000 if "product" in text.lower() else None,
                source_path=f"concepts[{concept_id}].must_show[{index - 1}]",
            )
            for index, text in enumerate(must_show or ["product visible", "demo in use"], start=1)
        ],
        talking_points=[pain, outcome],
        text_overlays=hook_options[:2],
        proof_direction=[str(concept.get("proof_mechanism") or "show observable result")],
        offer_direction=[text]
        if (text := str(concept.get("offer_framing") or "").strip())
        else [],
        cta=CtaDirectionV1(
            spoken="Check the product tag if this campaign is for TikTok Shop.",
            overlay="Product tag",
            cta_type="product_tag",
            product_tag_required=True,
            required_before_ms=None,
        ),
        claim_guardrails=ClaimGuardrailsV1(
            allowed=[],
            allowed_with_qualification=[],
            prohibited=claim_guardrails,
            required_disclosures=product_snapshot.governance.required_disclosures,
        ),
        do=["show product clearly", "show observable use", "keep claims evidence-backed"],
        dont=["copy the reference script exactly", "add unsupported performance claims"],
        rights_note=RightsNoteV1(
            note="Rights/Spark requests are informational and remain pending until authorized."
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


def _requirement_type(text: str) -> str:
    lowered = text.lower()
    if "cta" in lowered or "shop" in lowered or "tag" in lowered:
        return "cta"
    if "demo" in lowered or "use" in lowered or "using" in lowered:
        return "demo"
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
    if "product" in lowered or "close-up" in lowered or "close up" in lowered:
        return "product"
    return "scene"


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


def _creator_persona(product_snapshot: ProductContextV1, concept: dict[str, object]) -> str:
    if persona := str(concept.get("creator_persona") or "").strip():
        return persona
    if product_snapshot.creative.creator_personas:
        return product_snapshot.creative.creator_personas[0]
    return "unspecified creator"
