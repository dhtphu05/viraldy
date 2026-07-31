from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from uuid import NAMESPACE_URL, UUID, uuid5

from viraldy.modules.media_analysis.public import EvidenceItemModel, MediaObservationBundleV1
from viraldy.modules.tiktok_scorer.contracts_v2 import (
    SafeZoneObservationV1,
    SceneInventoryV1,
    VideoSceneV1,
)


@dataclass(frozen=True, slots=True)
class _SceneSeed:
    observation_id: str
    start_ms: int
    end_ms: int
    summary: str
    confidence: float
    shot_type: str | None = None
    product_visible: bool | None = None
    product_match_confidence: float | None = None
    product_visibility_quality: str | None = None
    spoken_text: str | None = None
    overlay_texts: tuple[str, ...] = ()
    demo_step: str | None = None
    proof_role: str | None = None
    creator_present: bool | None = None
    reusable_for_edit: bool = False


def build_scene_inventory(
    *,
    asset_version_id: UUID,
    observations: MediaObservationBundleV1,
    evidence_ids_by_observation_id: Mapping[str, UUID],
    audio_available: bool | None,
    asr_coverage: float | None,
    ocr_coverage: float | None,
    extractor_versions: Mapping[str, str],
    platform_evidence_id: UUID | None = None,
) -> SceneInventoryV1:
    """Build a temporal inventory only from observations with persisted evidence lineage."""

    seeds = _scene_seeds(observations)
    linked_seeds = [seed for seed in seeds if seed.observation_id in evidence_ids_by_observation_id]
    scenes = [
        _to_scene(asset_version_id, seed, evidence_ids_by_observation_id[seed.observation_id])
        for seed in linked_seeds
    ]
    all_evidence_ids = list(dict.fromkeys(evidence_ids_by_observation_id.values()))
    if platform_evidence_id is not None and platform_evidence_id not in all_evidence_ids:
        all_evidence_ids.append(platform_evidence_id)
    confidences = [seed.confidence for seed in linked_seeds]
    missing_lineage = len(linked_seeds) != len(seeds)
    coverage_status = _coverage_status(
        has_scenes=bool(scenes),
        missing_lineage=missing_lineage,
        has_uncertainty=bool(observations.uncertainties),
    )
    safe_zone_observations = _safe_zone_observations(
        observations,
        platform_evidence_id,
    )
    return SceneInventoryV1(
        asset_version_id=asset_version_id,
        duration_ms=observations.duration_ms,
        audio_available=audio_available,
        scenes=scenes,
        asr_coverage=asr_coverage if audio_available is not False else None,
        ocr_coverage=ocr_coverage,
        product_appearance_ranges=[
            (item.time_range.start_ms, item.time_range.end_ms)
            for item in observations.product_appearances
            if item.observation_id in evidence_ids_by_observation_id
        ],
        cta_ranges=[
            (item.time_range.start_ms, item.time_range.end_ms)
            for item in observations.ctas
            if item.observation_id in evidence_ids_by_observation_id
        ],
        disclosure_ranges=[
            (item.time_range.start_ms, item.time_range.end_ms)
            for item in observations.on_screen_text
            if item.text_role == "disclosure"
            and item.observation_id in evidence_ids_by_observation_id
        ],
        safe_zone_observations=safe_zone_observations,
        continuity_group_ids=[],
        evidence_ids=all_evidence_ids,
        coverage_status=coverage_status,
        overall_confidence=_confidence_label(confidences),
        extractor_versions=dict(extractor_versions),
    )


def build_scene_inventory_from_evidence(
    *,
    asset_version_id: UUID,
    duration_ms: int | None,
    evidence: list[EvidenceItemModel],
    audio_available: bool | None,
    asr_coverage: float | None = None,
    ocr_coverage: float | None = None,
) -> SceneInventoryV1:
    """Build scenes from persisted evidence without inferring missing timestamps or content."""

    evidence_ids = list(dict.fromkeys(item.id for item in evidence))
    timed_items = [item for item in evidence if _valid_item_range(item, duration_ms)]
    scene_candidates = [_scene_from_evidence(asset_version_id, item) for item in timed_items]
    scenes: list[VideoSceneV1] = [scene for scene in scene_candidates if scene is not None]
    invalid_timed_item = any(
        (item.start_ms is not None or item.end_ms is not None)
        and not _valid_item_range(item, duration_ms)
        for item in evidence
    )
    confidence_values = [float(item.confidence) for item in evidence if item.confidence is not None]
    continuity_ids = list(
        dict.fromkeys(
            scene.continuity_group_id for scene in scenes if scene.continuity_group_id is not None
        )
    )
    product_ranges = [
        (item.start_ms, item.end_ms)
        for item in timed_items
        if item.evidence_type in {"product_appearance", "product_first_appearance"}
        and item.start_ms is not None
        and item.end_ms is not None
    ]
    cta_ranges = [
        (item.start_ms, item.end_ms)
        for item in timed_items
        if item.evidence_type == "cta_signal"
        and item.start_ms is not None
        and item.end_ms is not None
    ]
    disclosure_ranges = [
        (item.start_ms, item.end_ms)
        for item in timed_items
        if _is_disclosure(item) and item.start_ms is not None and item.end_ms is not None
    ]
    safe_zone = [
        SafeZoneObservationV1(
            time_range_ms=(item.start_ms, item.end_ms),
            status="risk" if item.value_json.get("visual_safe_zone_risk") else "safe",
            reason="Persisted media evidence reports the UI safe-zone observation.",
            evidence_ids=[item.id],
        )
        for item in timed_items
        if item.evidence_type == "platform_signal"
        and isinstance(item.value_json.get("visual_safe_zone_risk"), bool)
        and item.start_ms is not None
        and item.end_ms is not None
    ]
    coverage_status = (
        "insufficient"
        if duration_ms is None or not evidence
        else "partial"
        if invalid_timed_item or not scenes
        else "sufficient"
    )
    extractor_versions = {
        item.source: (
            getattr(item, "model_version", None) or getattr(item, "pipeline_version", "unknown")
        )
        for item in evidence
        if item.source
    }
    return SceneInventoryV1(
        asset_version_id=asset_version_id,
        duration_ms=duration_ms,
        audio_available=audio_available,
        scenes=scenes,
        asr_coverage=asr_coverage if audio_available is not False else None,
        ocr_coverage=ocr_coverage,
        product_appearance_ranges=product_ranges,
        cta_ranges=cta_ranges,
        disclosure_ranges=disclosure_ranges,
        safe_zone_observations=safe_zone,
        continuity_group_ids=continuity_ids,
        evidence_ids=evidence_ids,
        coverage_status=coverage_status,
        overall_confidence=_confidence_label(confidence_values),
        extractor_versions=extractor_versions,
    )


def _scene_seeds(observations: MediaObservationBundleV1) -> list[_SceneSeed]:
    seeds: list[_SceneSeed] = []
    for hook in observations.hooks:
        seeds.append(
            _SceneSeed(
                observation_id=hook.observation_id,
                start_ms=hook.time_range.start_ms,
                end_ms=hook.time_range.end_ms,
                summary=f"Observed {hook.hook_type.replace('_', ' ')} opening.",
                confidence=hook.confidence,
                product_visible=hook.product_present,
                spoken_text=hook.spoken_text,
                overlay_texts=(hook.overlay_text,) if hook.overlay_text else (),
                creator_present=hook.face_present,
            )
        )
    for text in observations.on_screen_text:
        seeds.append(
            _SceneSeed(
                observation_id=text.observation_id,
                start_ms=text.time_range.start_ms,
                end_ms=text.time_range.end_ms,
                summary=f"Observed {text.text_role.replace('_', ' ')} text.",
                confidence=text.confidence,
                overlay_texts=(text.text,),
                reusable_for_edit=True,
            )
        )
    for product in observations.product_appearances:
        seeds.append(
            _SceneSeed(
                observation_id=product.observation_id,
                start_ms=product.time_range.start_ms,
                end_ms=product.time_range.end_ms,
                summary="Observed product appearance.",
                confidence=product.confidence,
                shot_type=product.shot_type,
                product_visible=product.visibility in {"clear", "partial"},
                product_match_confidence=product.product_match_confidence,
                product_visibility_quality=product.visibility,
                reusable_for_edit=product.visibility == "clear",
            )
        )
    for step in observations.demo.steps:
        seeds.append(
            _SceneSeed(
                observation_id=step.observation_id,
                start_ms=step.time_range.start_ms,
                end_ms=step.time_range.end_ms,
                summary="Observed product demonstration step.",
                confidence=step.confidence,
                product_visible=step.product_visible,
                demo_step=step.action,
                proof_role="demonstration" if step.result_visible else None,
                reusable_for_edit=step.product_visible and step.mechanism_visible,
            )
        )
    for proof in observations.proof_moments:
        seeds.append(
            _SceneSeed(
                observation_id=proof.observation_id,
                start_ms=proof.time_range.start_ms,
                end_ms=proof.time_range.end_ms,
                summary="Observed proof moment.",
                confidence=proof.confidence,
                proof_role=proof.proof_type,
                reusable_for_edit=proof.verifiability == "observable",
            )
        )
    for cta in observations.ctas:
        seeds.append(
            _SceneSeed(
                observation_id=cta.observation_id,
                start_ms=cta.time_range.start_ms,
                end_ms=cta.time_range.end_ms,
                summary="Observed call to action.",
                confidence=cta.confidence,
                spoken_text=cta.spoken_text,
                overlay_texts=(cta.overlay_text,) if cta.overlay_text else (),
                reusable_for_edit=True,
            )
        )
    return seeds


def _to_scene(asset_version_id: UUID, seed: _SceneSeed, evidence_id: UUID) -> VideoSceneV1:
    return VideoSceneV1(
        scene_id=uuid5(
            NAMESPACE_URL,
            f"viraldy:tiktok-scene:{asset_version_id}:{seed.observation_id}",
        ),
        start_ms=seed.start_ms,
        end_ms=seed.end_ms,
        summary=seed.summary,
        shot_type=seed.shot_type,
        product_visible=seed.product_visible,
        product_match_confidence=seed.product_match_confidence,
        product_visibility_quality=seed.product_visibility_quality,
        spoken_text=seed.spoken_text,
        overlay_texts=list(seed.overlay_texts),
        demo_step=seed.demo_step,
        proof_role=seed.proof_role,
        creator_present=seed.creator_present,
        visual_quality="unknown",
        continuity_group_id=None,
        reusable_for_edit=seed.reusable_for_edit,
        evidence_ids=[evidence_id],
    )


def _safe_zone_observations(
    observations: MediaObservationBundleV1,
    platform_evidence_id: UUID | None,
) -> list[SafeZoneObservationV1]:
    if observations.platform.visual_safe_zone_risk is None or platform_evidence_id is None:
        return []
    return [
        SafeZoneObservationV1(
            time_range_ms=(0, observations.duration_ms),
            status="risk" if observations.platform.visual_safe_zone_risk else "safe",
            reason="The shared media analysis reported the frame-level UI safe-zone status.",
            evidence_ids=[platform_evidence_id],
        )
    ]


def _coverage_status(
    *,
    has_scenes: bool,
    missing_lineage: bool,
    has_uncertainty: bool,
) -> str:
    if not has_scenes:
        return "insufficient"
    if missing_lineage or has_uncertainty:
        return "partial"
    return "sufficient"


def _confidence_label(confidences: list[float]) -> str:
    if not confidences:
        return "low"
    average = sum(confidences) / len(confidences)
    if average >= 0.8:
        return "high"
    if average >= 0.55:
        return "medium"
    return "low"


def _valid_item_range(item: EvidenceItemModel, duration_ms: int | None) -> bool:
    if duration_ms is None or item.start_ms is None or item.end_ms is None:
        return False
    return 0 <= item.start_ms <= item.end_ms <= duration_ms


def _scene_from_evidence(
    asset_version_id: UUID,
    item: EvidenceItemModel,
) -> VideoSceneV1 | None:
    if item.start_ms is None or item.end_ms is None:
        return None
    value = item.value_json
    visual_quality = value.get("visual_quality")
    if visual_quality not in {"good", "usable", "dark", "blurry", "obscured", "unknown"}:
        visual_quality = "unknown"
    continuity_group_id = _uuid_or_none(value.get("continuity_group_id"))
    overlay_texts = _overlay_texts(item)
    return VideoSceneV1(
        scene_id=uuid5(
            NAMESPACE_URL,
            f"viraldy:tiktok-scene:{asset_version_id}:{item.id}",
        ),
        start_ms=item.start_ms,
        end_ms=item.end_ms,
        summary=_evidence_summary(item.evidence_type),
        shot_type=_optional_string(value.get("shot_type")),
        product_visible=_product_visible(item),
        product_match_confidence=_optional_float(value.get("product_match_confidence")),
        product_visibility_quality=_optional_string(value.get("visibility")),
        spoken_text=_spoken_text(item),
        overlay_texts=overlay_texts,
        demo_step=(
            _optional_string(value.get("action")) if item.evidence_type == "demo_step" else None
        ),
        proof_role=(
            _optional_string(value.get("proof_type"))
            if item.evidence_type == "proof_signal"
            else None
        ),
        creator_present=_optional_bool(value.get("face_present")),
        visual_quality=visual_quality,
        continuity_group_id=continuity_group_id,
        reusable_for_edit=_is_reusable(item, visual_quality),
        evidence_ids=[item.id],
    )


def _evidence_summary(evidence_type: str) -> str:
    labels = {
        "hook_signal": "Observed opening structure.",
        "on_screen_text": "Observed on-screen text.",
        "product_appearance": "Observed product appearance.",
        "product_first_appearance": "Observed product appearance.",
        "demo_step": "Observed product demonstration step.",
        "proof_signal": "Observed proof moment.",
        "cta_signal": "Observed call to action.",
        "offer_signal": "Observed value or offer statement.",
        "claim_signal": "Observed claim candidate.",
        "transcript_segment": "Observed transcript segment.",
        "platform_signal": "Observed platform-format signal.",
    }
    return labels.get(evidence_type, "Observed media evidence.")


def _product_visible(item: EvidenceItemModel) -> bool | None:
    value = item.value_json
    if item.evidence_type in {"product_appearance", "product_first_appearance"}:
        return value.get("visibility") in {"clear", "partial"}
    present = value.get("product_present")
    return present if isinstance(present, bool) else None


def _spoken_text(item: EvidenceItemModel) -> str | None:
    value = item.value_json
    for key in ("spoken_text", "text"):
        text = value.get(key)
        if (
            isinstance(text, str)
            and text.strip()
            and (key == "spoken_text" or item.evidence_type == "transcript_segment")
        ):
            return text.strip()
    return None


def _overlay_texts(item: EvidenceItemModel) -> list[str]:
    value = item.value_json
    values = [value.get("overlay_text")]
    if item.evidence_type == "on_screen_text":
        values.append(value.get("text"))
    return list(
        dict.fromkeys(text.strip() for text in values if isinstance(text, str) and text.strip())
    )


def _is_reusable(item: EvidenceItemModel, visual_quality: object) -> bool:
    if visual_quality in {"dark", "blurry", "obscured"}:
        return False
    if item.evidence_type in {"product_appearance", "product_first_appearance"}:
        return item.value_json.get("visibility") == "clear"
    if item.evidence_type == "proof_signal":
        return item.value_json.get("verifiability") == "observable"
    return item.evidence_type in {
        "hook_signal",
        "on_screen_text",
        "demo_step",
        "cta_signal",
        "offer_signal",
        "transcript_segment",
    }


def _is_disclosure(item: EvidenceItemModel) -> bool:
    return (
        item.evidence_type == "on_screen_text" and item.value_json.get("text_role") == "disclosure"
    )


def _optional_string(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _optional_float(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    result = float(value)
    return result if 0 <= result <= 1 else None


def _optional_bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _uuid_or_none(value: object) -> UUID | None:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        try:
            return UUID(value)
        except ValueError:
            return None
    return None


__all__ = ["build_scene_inventory", "build_scene_inventory_from_evidence"]
