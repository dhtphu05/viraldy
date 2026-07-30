from __future__ import annotations

import json
import re
import unicodedata

from viraldy.modules.campaign_packs.schemas import (
    CampaignPackExportFormat,
    CampaignPackExportResponse,
    CampaignPackVersionResponse,
)


def build_campaign_pack_export(
    version: CampaignPackVersionResponse,
    export_format: CampaignPackExportFormat,
) -> CampaignPackExportResponse:
    brief = version.brief_json
    basename = _slugify(brief.product_snapshot.identity.name) or "campaign-pack"
    extension = "json" if export_format == "json" else "txt"
    filename = f"{basename}-creator-brief-v{version.version_number}.{extension}"
    content = _json_content(version) if export_format == "json" else _text_content(version)
    return CampaignPackExportResponse(
        campaign_pack_id=version.campaign_pack_id,
        campaign_pack_version_id=version.id,
        version_number=version.version_number,
        format=export_format,
        filename=filename,
        content_type=(
            "application/json" if export_format == "json" else "text/plain; charset=utf-8"
        ),
        content=content,
    )


def _json_content(version: CampaignPackVersionResponse) -> str:
    payload = {
        "campaign_pack_id": str(version.campaign_pack_id),
        "campaign_pack_version_id": str(version.id),
        "version_number": version.version_number,
        "brief_schema_version": version.brief_schema_version,
        "brief": version.brief_json.model_dump(mode="json"),
        "product_snapshot": (
            version.product_snapshot_json.model_dump(mode="json")
            if version.product_snapshot_json
            else None
        ),
        "compiled_requirements": version.compiled_requirements_json.model_dump(mode="json"),
        "requirements_schema_version": version.requirements_schema_version,
        "change_note": version.change_note,
        "source": {
            "adaptation_run_id": (
                str(version.source_adaptation_run_id) if version.source_adaptation_run_id else None
            ),
            "model_run_id": (
                str(version.source_model_run_id) if version.source_model_run_id else None
            ),
            "prompt_version": version.source_prompt_version,
            "schema_version": version.source_schema_version,
        },
        "created_at": version.created_at.isoformat(),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def _text_content(version: CampaignPackVersionResponse) -> str:
    brief = version.brief_json
    lines = [
        f"{brief.product_snapshot.identity.name.upper()} - CREATOR BRIEF",
        "",
        "TRACEABILITY",
        f"Campaign Pack: {version.campaign_pack_id}",
        f"Campaign Pack version: {version.id}",
        f"Version number: {version.version_number}",
        f"Brief schema: {version.brief_schema_version}",
        f"Source concept: {brief.source_concept_id}",
        "",
        "OBJECTIVE",
        f"Type: {brief.objective.objective_type}",
        f"Primary action: {brief.objective.primary_action}",
        f"Channel: {brief.objective.channel}",
        "",
        "AUDIENCE",
        f"Persona: {brief.audience.persona_label}",
        *_bullets("Pain points", brief.audience.pain_points),
        *_bullets("Desired outcomes", brief.audience.desired_outcomes),
        *_bullets("Objections", brief.audience.objections),
        "",
        "ANGLE",
        f"Name: {brief.angle.name}",
        f"Promise: {brief.angle.promise}",
        f"Mechanism: {brief.angle.mechanism}",
        f"Emotional driver: {brief.angle.emotional_driver}",
        "",
        "CREATOR DIRECTION",
        f"Persona: {brief.creator_direction.persona}",
        f"Delivery style: {brief.creator_direction.delivery_style}",
        *_bullets("Tone", brief.creator_direction.tone),
        *_bullets("Avoid tones", brief.creator_direction.avoid_tones),
        *_bullets("Authenticity notes", brief.creator_direction.authenticity_notes),
        "",
        "HOOK OPTIONS",
        *[
            f"{index}. {hook.spoken_text or hook.overlay_text or hook.opening_visual}"
            for index, hook in enumerate(brief.hooks, start=1)
        ],
        "",
        "SCRIPT BEATS",
        *[
            f"{beat.sequence}. [{beat.beat_type}] {beat.instruction}"
            for beat in sorted(brief.script_beats, key=lambda item: item.sequence)
        ],
        "",
        "STORYBOARD",
        *[
            f"{scene.sequence}. [{scene.shot_type}] {scene.instruction}"
            for scene in sorted(brief.storyboard, key=lambda item: item.sequence)
        ],
        "",
        "MUST SHOW",
        *[f"- [{item.severity.upper()}] {item.description}" for item in brief.must_show],
        *_section("TALKING POINTS", brief.talking_points),
        *_section("TEXT OVERLAYS", brief.text_overlays),
        *_section("PROOF DIRECTION", brief.proof_direction),
        *_section("OFFER DIRECTION", brief.offer_direction),
        "",
        "CTA",
        f"Type: {brief.cta.cta_type}",
        f"Spoken: {brief.cta.spoken or 'Not specified'}",
        f"Overlay: {brief.cta.overlay or 'Not specified'}",
        f"Product tag required: {'yes' if brief.cta.product_tag_required else 'no'}",
        "",
        "CLAIM GUARDRAILS",
        *_bullets("Allowed", brief.claim_guardrails.allowed),
        *_bullets(
            "Allowed with qualification",
            brief.claim_guardrails.allowed_with_qualification,
        ),
        *_bullets("Prohibited", brief.claim_guardrails.prohibited),
        *_bullets(
            "Required disclosures",
            brief.claim_guardrails.required_disclosures,
        ),
        *_section("DO", brief.do),
        *_section("DO NOT", brief.dont),
        "",
        "RIGHTS",
        brief.rights_note.note,
        f"Raw footage requested: {'yes' if brief.rights_note.raw_footage_requested else 'no'}",
        (
            "Editing permission requested: "
            f"{'yes' if brief.rights_note.editing_permission_requested else 'no'}"
        ),
        (
            "Spark authorization requested: "
            f"{'yes' if brief.rights_note.spark_authorization_requested else 'no'}"
        ),
        *_section("REVISION CHECKLIST", brief.revision_checklist),
    ]
    return "\n".join(lines).strip() + "\n"


def _section(title: str, items: list[str]) -> list[str]:
    if not items:
        return []
    return ["", title, *[f"- {item}" for item in items]]


def _bullets(label: str, items: list[str]) -> list[str]:
    if not items:
        return [f"{label}: Not specified"]
    return [f"{label}:", *[f"- {item}" for item in items]]


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug[:80].rstrip("-")


__all__ = ["build_campaign_pack_export"]
