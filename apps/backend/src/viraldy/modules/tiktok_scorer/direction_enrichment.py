from __future__ import annotations

import hashlib
import json
from uuid import NAMESPACE_URL, UUID, uuid5

from viraldy.modules.tiktok_scorer.contracts_v2 import (
    CreativeDirectionContextV1,
    CreativeUpgradeSuggestionV1,
    TikTokScoreComputationV2,
)
from viraldy.modules.viral_kits.public import ViralKitVersionSnapshot


def build_optional_upgrade(
    context: CreativeDirectionContextV1,
    computation: TikTokScoreComputationV2,
) -> CreativeUpgradeSuggestionV1 | None:
    if not _is_compatible(context, computation):
        return None
    evidence_ids = [
        evidence_id
        for scene in computation.scene_inventory.scenes
        for evidence_id in scene.evidence_ids
    ]
    return CreativeUpgradeSuggestionV1(
        id=uuid5(
            NAMESPACE_URL,
            (
                "viraldy:tiktok-direction-upgrade:"
                f"{computation.asset_version_id}:{context.source_id}:"
                f"{context.source_version}:{context.concept_id}"
            ),
        ),
        source_type="viral_kit",
        source_id=context.source_id,
        source_version=context.source_version,
        concept_id=context.concept_id,
        affects_score=False,
        recommendation_class="optional_upgrade",
        title="Based on your selected Creative Direction",
        why_it_fits=(
            "The selected direction uses the same product snapshot and a compatible intended use."
        ),
        keep_from_current_video=list(context.keep),
        change_in_current_video=list(context.change),
        additional_footage_needed=[],
        suggested_hook_mechanism=context.hook_mechanism or None,
        suggested_narrative_sequence=list(context.narrative_sequence),
        suggested_demo_mechanism=context.demo_mechanism,
        suggested_proof_mechanism=context.proof_mechanism,
        suggested_cta_strategy=context.cta_strategy,
        claim_guardrails=[
            *[f"Allowed only when verified: {claim}" for claim in context.allowed_claims],
            *[f"Do not use: {claim}" for claim in context.prohibited_claims],
            *[f"Required disclosure: {item}" for item in context.required_disclosures],
        ],
        evidence_ids=list(dict.fromkeys(evidence_ids)),
        expected_learning=context.expected_learning,
    )


def creative_direction_context_from_viral_kit(
    snapshot: ViralKitVersionSnapshot,
    *,
    product_snapshot_hash: str | None = None,
) -> CreativeDirectionContextV1 | None:
    """Translate a selected concept using only the ViralKit public contract."""

    viral_kit = snapshot.viral_kit
    selected_id = viral_kit.selected_concept_id
    if selected_id is None or snapshot.status in {"archived", "failed"}:
        return None
    concept = next((item for item in viral_kit.concepts if item.id == selected_id), None)
    if concept is None:
        return None
    snapshot_hash = product_snapshot_hash or _hash_product_snapshot(
        viral_kit.product.snapshot_json.model_dump(mode="json")
    )
    return CreativeDirectionContextV1(
        source_type="viral_kit",
        source_id=snapshot.viral_kit_id,
        source_version=snapshot.version,
        source_status=snapshot.status,
        concept_id=_concept_uuid(snapshot.viral_kit_id, selected_id),
        concept_status="selected",
        product_snapshot_hash=snapshot_hash,
        objective=viral_kit.objective,
        market=viral_kit.target_market,
        buyer_context=viral_kit.buyer_context.model_dump(mode="json"),
        message_angle=concept.creative_angle,
        hook_mechanism=concept.hook.hook_type,
        narrative_sequence=[concept.narrative_structure],
        demo_mechanism=concept.demo_mechanism,
        proof_mechanism=concept.proof_mechanism,
        cta_strategy=concept.cta_strategy,
        keep=[item.rationale for item in viral_kit.adaptation_plan.keep],
        change=[item.rationale for item in viral_kit.adaptation_plan.change],
        avoid=[item.rationale for item in viral_kit.adaptation_plan.avoid],
        allowed_claims=[],
        prohibited_claims=list(
            dict.fromkeys(
                [
                    *viral_kit.constraints.governance.prohibited_claims,
                    *concept.claims_to_avoid,
                ]
            )
        ),
        required_disclosures=list(
            dict.fromkeys(
                [
                    *viral_kit.constraints.governance.required_disclosures,
                    *concept.required_disclosures,
                ]
            )
        ),
        expected_learning=concept.expected_learning,
    )


def _is_compatible(
    context: CreativeDirectionContextV1,
    computation: TikTokScoreComputationV2,
) -> bool:
    if computation.product_snapshot_hash is None:
        return False
    if context.product_snapshot_hash != computation.product_snapshot_hash:
        return False
    if context.concept_status == "rejected" or context.source_status in {"archived", "failed"}:
        return False
    if computation.direction_governance_conflicts:
        return False
    if context.market is not None:
        if computation.market is None or context.market.casefold() != computation.market.casefold():
            return False
    if context.objective is None:
        return True
    compatible_objectives = {
        "tiktok_organic": {"tiktok_shop_organic_test", "creative_refresh"},
        "tiktok_shop_affiliate": {"tiktok_shop_affiliate_test", "creative_refresh"},
        "ugc_paid_candidate": {"ugc_paid_asset", "small_paid_test", "creative_refresh"},
        "spark_candidate": {"spark_candidate", "small_paid_test", "creative_refresh"},
    }
    return context.objective in compatible_objectives[computation.intended_use]


def _concept_uuid(source_id: UUID, concept_id: str) -> UUID:
    try:
        return UUID(concept_id)
    except ValueError:
        return uuid5(NAMESPACE_URL, f"viraldy:viral-kit-concept:{source_id}:{concept_id}")


def _hash_product_snapshot(snapshot: dict[str, object]) -> str:
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "build_optional_upgrade",
    "creative_direction_context_from_viral_kit",
]
