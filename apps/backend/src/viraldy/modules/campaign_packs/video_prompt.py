from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from viraldy.modules.campaign_packs.contracts import CampaignPackBriefV1


class VideoGenerationPromptV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["video_generation_prompt_v1"] = "video_generation_prompt_v1"
    prompt_text: str = Field(min_length=1)
    aspect_ratio: Literal["9:16"] = "9:16"
    duration_seconds: int = Field(default=20, ge=1, le=60)
    source_concept_id: str = Field(min_length=1)


def build_video_generation_prompt(brief: CampaignPackBriefV1) -> VideoGenerationPromptV1:
    product = brief.product_snapshot
    identity = product.identity
    scenes = _scene_lines(brief)
    spoken_lines = _unique(
        [
            *(hook.spoken_text for hook in brief.hooks),
            *(scene.spoken_direction for scene in brief.storyboard),
            brief.cta.spoken,
        ]
    )
    overlays = _unique(
        [
            *(hook.overlay_text for hook in brief.hooks),
            *(scene.overlay_text for scene in brief.storyboard),
            *brief.text_overlays,
            brief.cta.overlay,
        ]
    )
    avoid_direction = _joined(
        [*brief.creator_direction.avoid_tones, *brief.dont],
        "overclaiming and unrelated visuals",
    )

    lines = [
        (
            "Generate one product-grounded vertical social commerce video using these locked "
            "production instructions."
        ),
        "",
        "FORMAT",
        "- 9:16 vertical video, 20 seconds, mobile-first framing.",
        (
            f"- Creator style: {brief.creator_direction.persona}; "
            f"{brief.creator_direction.delivery_style}."
        ),
        f"- Tone: {_joined(brief.creator_direction.tone, 'natural and product-focused')}.",
        (
            "- Keep motion physically plausible, cuts clean, and the product visually consistent "
            "across every shot."
        ),
        "",
        "PRODUCT LOCK",
        f"- Exact product: {identity.name}.",
        f"- Brand: {identity.brand or 'not specified; do not invent one'}.",
        f"- Category: {identity.category}.",
        (
            "- Variant: "
            f"{identity.variant or 'not specified; preserve the supplied product appearance'}."
        ),
        "- Do not invent product features, prices, results, or claims that are not written below.",
        "",
        "AUDIENCE AND OBJECTIVE",
        f"- Audience: {brief.audience.persona_label}.",
        f"- Buyer pain: {_joined(brief.audience.pain_points, 'not specified')}.",
        f"- Desired outcome: {_joined(brief.audience.desired_outcomes, brief.angle.promise)}.",
        (
            f"- Objective: {brief.objective.objective_type}; primary action: "
            f"{brief.objective.primary_action}."
        ),
        "",
        "CREATIVE DIRECTION",
        f"- Angle: {brief.angle.name}.",
        f"- Mechanism to demonstrate: {brief.angle.mechanism}.",
        f"- Emotional driver: {brief.angle.emotional_driver}.",
        *(_section("OPENING HOOK", _hook_lines(brief)) or []),
        *(_section("SCENE PLAN", scenes) or []),
        *(_section("EXACT SPOKEN DIRECTION", spoken_lines) or []),
        *(_section("ON-SCREEN TEXT", overlays) or []),
        *(_section("PROOF TO SHOW", brief.proof_direction) or []),
        *(_section("OFFER DIRECTION", brief.offer_direction) or []),
        "",
        "CTA",
        f"- Spoken: {brief.cta.spoken or 'No spoken CTA specified'}.",
        f"- On-screen: {brief.cta.overlay or 'No CTA overlay specified'}.",
        f"- Product tag: {'required' if brief.cta.product_tag_required else 'not required'}.",
        *(_section("MUST SHOW", [item.description for item in brief.must_show]) or []),
        "",
        "CLAIM AND COMPLIANCE LOCK",
        f"- Allowed claims: {_joined(brief.claim_guardrails.allowed, 'none supplied')}.",
        "- Claims allowed only with qualification: "
        f"{_joined(brief.claim_guardrails.allowed_with_qualification, 'none supplied')}.",
        f"- Prohibited claims: {_joined(brief.claim_guardrails.prohibited, 'none supplied')}.",
        (
            "- Required disclosures: "
            f"{_joined(brief.claim_guardrails.required_disclosures, 'none supplied')}."
        ),
        "",
        "NEGATIVE CONSTRAINTS",
        (
            "- No unsupported before-and-after result, fake testimonial, fabricated UI, price, "
            "discount, certification, or performance statistic."
        ),
        (
            "- Do not copy the reference creator's identity, exact wording, branding, or protected "
            "visual expression."
        ),
        f"- Avoid: {avoid_direction}.",
        (
            "- Do not add subtitles, logos, props, packaging details, or product capabilities "
            "unless explicitly specified."
        ),
        "",
        "FINAL OUTPUT",
        (
            "Return one coherent finished video following this scene order. Keep all visible "
            "product details stable and render only the specified spoken lines and on-screen text."
        ),
    ]
    prompt_text = "\n".join(line for line in lines if line is not None).strip()
    return VideoGenerationPromptV1(
        prompt_text=prompt_text,
        source_concept_id=brief.source_concept_id,
    )


def _hook_lines(brief: CampaignPackBriefV1) -> list[str]:
    return [
        " | ".join(
            part
            for part in (
                f"Visual: {hook.opening_visual}",
                f"Spoken: {hook.spoken_text}" if hook.spoken_text else None,
                f"Overlay: {hook.overlay_text}" if hook.overlay_text else None,
            )
            if part
        )
        for hook in brief.hooks
    ]


def _scene_lines(brief: CampaignPackBriefV1) -> list[str]:
    if brief.storyboard:
        return [
            " | ".join(
                part
                for part in (
                    f"Scene {scene.sequence} ({scene.shot_type}): {scene.instruction}",
                    "product visible" if scene.product_visibility_required else None,
                    f"spoken: {scene.spoken_direction}" if scene.spoken_direction else None,
                    f"overlay: {scene.overlay_text}" if scene.overlay_text else None,
                )
                if part
            )
            for scene in sorted(brief.storyboard, key=lambda item: item.sequence)
        ]
    return [
        f"Scene {beat.sequence} ({beat.beat_type}): {beat.instruction}"
        for beat in sorted(brief.script_beats, key=lambda item: item.sequence)
    ]


def _section(title: str, items: list[str]) -> list[str]:
    if not items:
        return []
    return ["", title, *(f"- {item}" for item in items)]


def _joined(items: list[str], fallback: str) -> str:
    values = _unique(items)
    return "; ".join(values) if values else fallback


def _unique(items: Sequence[str | None]) -> list[str]:
    return list(dict.fromkeys(item.strip() for item in items if item and item.strip()))
