from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.adaptations.public import AdaptationRepository
from viraldy.modules.campaign_packs.repository import CampaignPackRepository
from viraldy.modules.campaign_packs.schemas import (
    CampaignPackResponse,
    CampaignPackVersionResponse,
    CreateCampaignPackRequest,
    CreateCampaignPackVersionRequest,
    UpdateCampaignPackRequest,
)
from viraldy.shared.errors.base import NotFoundError


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
        pack, version = await self._repository.create(
            workspace_id,
            user_id,
            adaptation.product_id,
            adaptation.id,
            _brief_from_concept(
                adaptation.objective,
                adaptation.target_market,
                adaptation.target_buyer_json,
                concept,
            ),
        )
        await self._session.commit()
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
        version = await self._repository.create_version(
            pack, user_id, data.brief_json, data.change_note
        )
        await self._session.commit()
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
    concept: dict[str, object],
) -> dict[str, object]:
    hook = str(concept.get("hook") or "This fixed my tiny kitchen problem")
    angle = str(concept.get("angle") or "small_space_convenience")
    persona = str(concept.get("buyer_persona") or target_buyer.get("persona") or "US buyer")
    return {
        "objective": objective,
        "target_market": target_market,
        "target_buyer": {
            "persona": persona,
            "pain": str(target_buyer.get("pain") or "limited counter space"),
            "desired_outcome": str(target_buyer.get("desired_outcome") or "faster organization"),
        },
        "core_angle": {"name": angle, "promise": "Create more usable counter space"},
        "creator_persona": {
            "type": str(concept.get("creator_persona") or "budget home organizer"),
            "delivery_style": "authentic_review",
        },
        "hooks": [
            hook,
            "I did not know this was the missing piece",
            "A tiny-kitchen fix I would buy again",
            "This made my counter feel twice as usable",
            "No-drill storage that actually looks clean",
        ],
        "scripts": [
            {
                "name": "Problem to result",
                "beats": [
                    "show clutter",
                    "introduce product",
                    "demo setup",
                    "show result",
                    "TikTok Shop CTA",
                ],
            },
            {
                "name": "Morning routine",
                "beats": [
                    "show rushed moment",
                    "use product",
                    "compare before/after",
                    "creator reaction",
                    "CTA",
                ],
            },
        ],
        "storyboard": [
            {"scene": 1, "instruction": str(concept.get("opening_visual") or "show the problem")},
            {"scene": 2, "instruction": "product close-up within first three seconds"},
            {"scene": 3, "instruction": "hands-on demo"},
            {"scene": 4, "instruction": "before/after result"},
            {"scene": 5, "instruction": "TikTok Shop CTA with product tag"},
        ],
        "must_show": [
            "product close-up",
            "before state",
            "demo in use",
            "after result",
            "TikTok Shop CTA",
        ],
        "text_overlays": ["I needed this sooner", "tiny kitchen reset", "linked in my TikTok Shop"],
        "talking_points": [
            "show the practical problem",
            "explain the mechanism",
            "show the result plainly",
        ],
        "cta": {
            "spoken": "I linked it in my TikTok Shop.",
            "overlay": "Shop the product tag",
            "product_tag_required": True,
        },
        "claims_allowed": ["helped organize my counter", "made the space easier to use"],
        "claims_to_avoid": ["best ever", "guaranteed results", "medical or safety claims"],
        "do": ["show the product early", "keep delivery natural", "show a real before/after"],
        "dont": [
            "copy another creator's exact script",
            "make unsupported claims",
            "hide the product until the end",
        ],
        "rights_request": {
            "raw_footage_requested": False,
            "editing_permission_requested": False,
            "usage_note": "Rights/Spark requests are informational for this MVP.",
        },
        "spark_request": {"request_authorization": False, "message": ""},
        "revision_checklist": [
            "Product appears within three seconds",
            "Demo shows the product in use",
            "Before/after result is clear",
            "CTA appears before the final moment",
            "No unsupported claims are included",
        ],
    }
