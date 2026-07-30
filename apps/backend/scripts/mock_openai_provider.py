from __future__ import annotations

import ast
import asyncio
import json
import os
import re
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

import uvicorn
from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.responses import Response

from viraldy.modules.creative_dna.contracts import CreativeDnaV1
from viraldy.modules.pattern_kits.contracts import PatternKitV1
from viraldy.modules.pattern_kits.provider import (
    PatternEvidenceInput,
    PatternSourceInput,
    build_fixture_pattern_kit,
)
from viraldy.modules.pattern_kits.public import PatternKitVersionSnapshot
from viraldy.modules.pattern_kits.schemas import CreatePatternKitRequest
from viraldy.modules.products.public import ProductContextSnapshot
from viraldy.modules.viral_kits.contracts import ViralKitPatternMatchV1
from viraldy.modules.viral_kits.provider import build_fixture_viral_kit
from viraldy.modules.viral_kits.schemas import CreateViralKitRequest

app = FastAPI(title="Viraldy Mock OpenAI-Compatible Provider")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/audio/transcriptions")
async def transcriptions(
    file: Annotated[UploadFile, File()],
    model: Annotated[str, Form()],
    authorization: Annotated[str | None, Header()] = None,
) -> JSONResponse:
    _require_auth_shape(authorization)
    await _maybe_fail()
    content = await file.read()
    if not content or not model:
        raise HTTPException(status_code=400, detail="file and model are required")
    if os.getenv("MOCK_AI_SCENARIO", "").strip() == "no_speech":
        return JSONResponse({"language": "en", "text": "", "segments": []})
    return JSONResponse(
        {
            "language": "en",
            "text": "This solved a daily problem once I showed it in use. "
            "I linked the product in my TikTok Shop.",
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "This solved a daily problem."},
                {"start": 1.2, "end": 2.5, "text": "I showed it in use."},
                {"start": 3.0, "end": 3.8, "text": "I linked the product in my TikTok Shop."},
            ],
        }
    )


@app.post("/v1/chat/completions")
async def chat_completions(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> Response:
    _require_auth_shape(authorization)
    failure = os.getenv("MOCK_AI_FAILURE", "")
    if failure == "malformed_json":
        return PlainTextResponse("{not-json", media_type="application/json")
    await _maybe_fail(failure)
    body = await request.json()
    if not body.get("model") or not isinstance(body.get("messages"), list):
        raise HTTPException(status_code=400, detail="model and messages are required")
    prompt = _prompt_text(body["messages"])
    content = _response_payload(prompt)
    if failure == "missing_field":
        if "concepts" in content:
            content.pop("concepts")
        elif "duration_ms" in content:
            content.pop("duration_ms")
        else:
            content.pop(next(iter(content)))
    return JSONResponse(
        {
            "id": "mock-chatcmpl-viraldy",
            "object": "chat.completion",
            "choices": [
                {"index": 0, "message": {"role": "assistant", "content": json.dumps(content)}}
            ],
        },
        headers={"openai-request-id": "mock-request-viraldy"},
    )


def _require_auth_shape(value: str | None) -> None:
    if not value or not value.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")


async def _maybe_fail(failure: str | None = None) -> None:
    mode = failure if failure is not None else os.getenv("MOCK_AI_FAILURE", "")
    if mode == "timeout":
        await asyncio.sleep(3600)
    if mode == "429":
        raise HTTPException(status_code=429, detail="mock rate limit")
    if mode == "500":
        raise HTTPException(status_code=500, detail="mock server error")


def _prompt_text(messages: list[Any]) -> str:
    parts: list[str] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            parts.extend(
                str(item.get("text"))
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            )
    return "\n".join(parts)


def _response_payload(prompt: str) -> dict[str, Any]:
    if "Extract a PatternKitV1" in prompt:
        return _pattern_kit_payload(prompt)
    if "Compose a ViralKitV1" in prompt:
        return _viral_kit_payload(prompt)
    if "Adapt this Creative DNA" in prompt:
        return _adaptation_payload()
    return _vision_payload(prompt)


def _pattern_kit_payload(prompt: str) -> dict[str, Any]:
    request = CreatePatternKitRequest.model_validate(
        _literal_section(prompt, "Request: ", "\nSources:")
    )
    raw_sources = _literal_section(prompt, "Sources: ")
    sources: list[PatternSourceInput] = []
    for raw_source in raw_sources:
        asset_version_id = UUID(str(raw_source["asset_version_id"]))
        evidence_by_id = {
            UUID(str(item["evidence_id"])): PatternEvidenceInput(
                id=UUID(str(item["evidence_id"])),
                asset_version_id=asset_version_id,
                evidence_type=str(item["evidence_type"]),
                source=str(item["source"]),
                start_ms=item.get("start_ms"),
                end_ms=item.get("end_ms"),
                value_json={},
                confidence=0.8,
            )
            for item in raw_source["evidence"]
        }
        sources.append(
            PatternSourceInput(
                creative_dna_version_id=UUID(str(raw_source["creative_dna_version_id"])),
                asset_version_id=asset_version_id,
                taxonomy_version=str(raw_source["taxonomy_version"]),
                dna=CreativeDnaV1.model_validate(raw_source["dna"]),
                evidence_by_id=evidence_by_id,
            )
        )
    pattern = build_fixture_pattern_kit(
        pattern_kit_id=UUID(_line_value(prompt, "Pattern kit ID")),
        workspace_id=UUID(_line_value(prompt, "Workspace ID")),
        version=int(_line_value(prompt, "Version")),
        created_by=UUID(_line_value(prompt, "Created by")),
        created_at=datetime.fromisoformat(_line_value(prompt, "Created at")),
        request=request,
        sources=sources,
        model_run_id=UUID(_line_value(prompt, "Model run ID")),
    )
    pattern = pattern.model_copy(
        update={
            "source": pattern.source.model_copy(update={"extraction_mode": "ai_assisted"}),
        }
    )
    return pattern.model_dump(mode="json")


def _viral_kit_payload(prompt: str) -> dict[str, Any]:
    request = CreateViralKitRequest.model_validate(
        _literal_section(prompt, "Request: ", "\nProduct snapshot:")
    )
    product = ProductContextSnapshot.model_validate(
        _literal_section(prompt, "Product snapshot: ", "\nPattern matches:")
    )
    matches = [
        ViralKitPatternMatchV1.model_validate(item)
        for item in _literal_section(prompt, "Pattern matches: ", "\nPattern payloads:")
    ]
    patterns = [
        PatternKitVersionSnapshot(
            pattern_kit_id=UUID(str(item["pattern_kit_id"])),
            pattern_kit_version_id=UUID(str(item["pattern_kit_version_id"])),
            workspace_id=UUID(_line_value(prompt, "Workspace ID")),
            version=int(item["version"]),
            status=str(item["status"]),
            pattern=PatternKitV1.model_validate(item["pattern"]),
        )
        for item in _literal_section(prompt, "Pattern payloads: ")
    ]
    viral_kit = build_fixture_viral_kit(
        viral_kit_id=UUID(_line_value(prompt, "Viral kit ID")),
        workspace_id=UUID(_line_value(prompt, "Workspace ID")),
        version=int(_line_value(prompt, "Version")),
        created_by=UUID(_line_value(prompt, "Created by")),
        created_at=datetime.fromisoformat(_line_value(prompt, "Created at")),
        request=request,
        product=product,
        patterns=patterns,
        pattern_matches=matches,
        model_run_id=UUID(_line_value(prompt, "Model run ID")),
    )
    return viral_kit.model_dump(mode="json")


def _line_value(prompt: str, label: str) -> str:
    match = re.search(rf"^{re.escape(label)}:\s*(.+)$", prompt, flags=re.MULTILINE)
    if match is None:
        raise HTTPException(status_code=400, detail=f"missing prompt field: {label}")
    return match.group(1).strip()


def _literal_section(prompt: str, start: str, end: str | None = None) -> Any:
    try:
        raw = prompt.split(start, 1)[1]
        if end is not None:
            raw = raw.split(end, 1)[0]
        return ast.literal_eval(raw.strip())
    except (IndexError, SyntaxError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"invalid prompt section: {start}") from exc


def _vision_payload(prompt: str) -> dict[str, Any]:
    if "Extract readable on-screen text" in prompt:
        return {
            "segments": [
                {
                    "start_ms": 0,
                    "end_ms": 1000,
                    "text": _scenario(prompt)["overlay"],
                    "confidence": 0.92,
                    "frame_storage_key": "mock/frame_000.jpg",
                }
            ]
        }
    duration_ms = _duration_ms(prompt)
    return _observation_bundle(duration_ms, _scenario(prompt))


def _duration_ms(prompt: str) -> int:
    match = re.search(r"Duration_ms:\s*(\d+)", prompt)
    return int(match.group(1)) if match else 4000


def _scenario(prompt: str) -> dict[str, Any]:
    scenario_id = os.getenv("MOCK_AI_SCENARIO", "").strip() or _category_from_prompt(prompt)
    scenarios = _scenarios()
    return scenarios.get(scenario_id, scenarios["home_organization"])


def _category_from_prompt(prompt: str) -> str:
    for pattern in (r"'category':\s*'([^']+)'", r'"category":\s*"([^"]+)"'):
        match = re.search(pattern, prompt)
        if match:
            return match.group(1)
    return "home_organization"


def _scenarios() -> dict[str, dict[str, Any]]:
    return {
        "home_organization": {
            "category": "home_organization",
            "hook_type": "problem_first",
            "spoken": "This fixed the cluttered counter problem.",
            "overlay": "Counter clutter fix",
            "visual": "crowded counter before product use",
            "pain": "limited counter space",
            "product_first_ms": 900,
            "demo_type": "before_after",
            "demo_action": "show rack creating visible counter space",
            "proof_type": "before_after",
            "proof": "visible counter space result after product use",
            "creator_persona": "home organizer",
            "delivery": "authentic_review",
            "claim": "created more usable counter space",
            "claim_category": "performance",
            "claim_risk": "low",
            "cta": True,
            "offer": False,
            "product_present": True,
            "product_match_confidence": 0.82,
        },
        "beauty_tool": {
            "category": "beauty_tool",
            "hook_type": "result_first",
            "spoken": "Here is the smoother finish after the tool pass.",
            "overlay": "Smoother finish check",
            "visual": "beauty tool close-up beside finished look",
            "pain": "uneven styling finish",
            "product_first_ms": 800,
            "demo_type": "usage",
            "demo_action": "show the beauty tool moving through one visible section",
            "proof_type": "visual_result",
            "proof": "side-by-side finished section shown on camera",
            "creator_persona": "beauty reviewer",
            "delivery": "faceless_demo",
            "claim": "smoother-looking finish",
            "claim_category": "performance",
            "claim_risk": "low",
            "cta": True,
            "offer": True,
            "product_present": True,
            "product_match_confidence": 0.82,
        },
        "pod_personalized_gift": {
            "category": "pod_personalized_gift",
            "hook_type": "curiosity",
            "spoken": "I checked the custom name reveal before gifting it.",
            "overlay": "Custom name reveal",
            "visual": "personalized gift reveal with visible custom detail",
            "pain": "generic gifts feel impersonal",
            "product_first_ms": 700,
            "demo_type": "unboxing",
            "demo_action": "show the custom print detail and packaging reveal",
            "proof_type": "visual_result",
            "proof": "customized name detail is readable on the item",
            "creator_persona": "gift shopper",
            "delivery": "storytelling",
            "claim": "personalized detail is visible",
            "claim_category": "other",
            "claim_risk": "low",
            "cta": True,
            "offer": False,
            "product_present": True,
            "product_match_confidence": 0.82,
        },
        "pet_accessory": {
            "category": "pet_accessory",
            "hook_type": "problem_first",
            "spoken": "This made the pet walk setup easier to handle.",
            "overlay": "Walk setup check",
            "visual": "pet accessory shown attached and in use",
            "pain": "messy pet-walk setup",
            "product_first_ms": 900,
            "demo_type": "usage",
            "demo_action": "show the pet accessory attached and used during setup",
            "proof_type": "demonstration",
            "proof": "accessory remains visible while being used",
            "creator_persona": "pet owner",
            "delivery": "demonstration",
            "claim": "easier setup for the walk",
            "claim_category": "performance",
            "claim_risk": "low",
            "cta": True,
            "offer": False,
            "product_present": True,
            "product_match_confidence": 0.82,
        },
        "fashion_accessory": {
            "category": "fashion_accessory",
            "hook_type": "testimonial",
            "spoken": "I tried the accessory with two outfits before deciding.",
            "overlay": "Two outfit check",
            "visual": "fashion accessory shown in close-up and worn",
            "pain": "hard to style one accessory with different outfits",
            "product_first_ms": 800,
            "demo_type": "comparison",
            "demo_action": "show the accessory worn with two outfit contexts",
            "proof_type": "comparison",
            "proof": "two outfit looks are shown with the accessory visible",
            "creator_persona": "style reviewer",
            "delivery": "testimonial",
            "claim": "works with two outfit styles shown",
            "claim_category": "other",
            "claim_risk": "low",
            "cta": True,
            "offer": True,
            "product_present": True,
            "product_match_confidence": 0.82,
        },
        "late_product_reveal": {
            "category": "beauty_tool",
            "hook_type": "curiosity",
            "spoken": "Wait for the tool reveal before judging the result.",
            "overlay": "Wait for the reveal",
            "visual": "result shown before product appears",
            "pain": "unclear product setup",
            "product_first_ms": 5200,
            "demo_type": "usage",
            "demo_action": "show product only after the opening result",
            "proof_type": "visual_result",
            "proof": "result is visible before the product reveal",
            "creator_persona": "beauty reviewer",
            "delivery": "faceless_demo",
            "claim": "visible result",
            "claim_category": "performance",
            "claim_risk": "low",
            "cta": True,
            "offer": False,
            "product_present": True,
            "product_match_confidence": 0.82,
        },
        "missing_cta": {
            "category": "pet_accessory",
            "hook_type": "problem_first",
            "spoken": "This made the pet setup easier.",
            "overlay": "Pet setup check",
            "visual": "pet accessory demo without shopping cue",
            "pain": "messy pet setup",
            "product_first_ms": 900,
            "demo_type": "usage",
            "demo_action": "show accessory in use",
            "proof_type": "demonstration",
            "proof": "visible product use without CTA",
            "creator_persona": "pet owner",
            "delivery": "demonstration",
            "claim": "easier setup",
            "claim_category": "performance",
            "claim_risk": "low",
            "cta": False,
            "offer": False,
            "product_present": True,
            "product_match_confidence": 0.82,
        },
        "no_offer": {
            "category": "pod_personalized_gift",
            "hook_type": "curiosity",
            "spoken": "I checked the custom detail before gifting it.",
            "overlay": "Custom detail check",
            "visual": "personalized gift shown without any offer cue",
            "pain": "generic gifts feel impersonal",
            "product_first_ms": 700,
            "demo_type": "unboxing",
            "demo_action": "show the custom detail and package reveal",
            "proof_type": "visual_result",
            "proof": "custom detail is readable on the item",
            "creator_persona": "gift shopper",
            "delivery": "storytelling",
            "claim": "personalized detail is visible",
            "claim_category": "other",
            "claim_risk": "low",
            "cta": True,
            "offer": False,
            "product_present": True,
            "product_match_confidence": 0.82,
        },
        "no_speech": {
            "category": "fashion_accessory",
            "hook_type": "product_first",
            "spoken": None,
            "overlay": "Two outfit check",
            "visual": "silent fashion accessory demo with heavy overlay text",
            "pain": "style uncertainty",
            "product_first_ms": 700,
            "demo_type": "comparison",
            "demo_action": "show accessory with two outfits using text overlays",
            "proof_type": "comparison",
            "proof": "two outfit looks are shown with the accessory visible",
            "creator_persona": "style reviewer",
            "delivery": "faceless_demo",
            "claim": "works with two outfit styles shown",
            "claim_category": "other",
            "claim_risk": "low",
            "cta": True,
            "offer": False,
            "product_present": True,
            "product_match_confidence": 0.82,
        },
        "brief_mismatch": {
            "category": "pet_accessory",
            "hook_type": "problem_first",
            "spoken": "This accessory setup is shown for a different item.",
            "overlay": "Different item check",
            "visual": "unrelated accessory shown instead of the briefed product",
            "pain": "briefed product is not represented",
            "product_first_ms": 900,
            "demo_type": "usage",
            "demo_action": "show a different accessory being used",
            "proof_type": "demonstration",
            "proof": "visible use exists but product match is weak",
            "creator_persona": "pet owner",
            "delivery": "demonstration",
            "claim": "easier setup",
            "claim_category": "performance",
            "claim_risk": "low",
            "cta": True,
            "offer": False,
            "product_present": True,
            "product_match_confidence": 0.2,
        },
        "product_absent": {
            "category": "fashion_accessory",
            "hook_type": "story_open",
            "spoken": "I talked about the accessory but never showed it clearly.",
            "overlay": "Accessory story",
            "visual": "creator talking without visible product",
            "pain": "style uncertainty",
            "product_first_ms": None,
            "demo_type": "none",
            "demo_action": "",
            "proof_type": "none",
            "proof": "",
            "creator_persona": "style reviewer",
            "delivery": "storytelling",
            "claim": "best accessory ever",
            "claim_category": "superlative",
            "claim_risk": "medium",
            "cta": False,
            "offer": False,
            "product_present": False,
            "product_match_confidence": None,
        },
        "high_risk_claim": {
            "category": "beauty_tool",
            "hook_type": "result_first",
            "spoken": "This guarantees perfect skin instantly.",
            "overlay": "Guaranteed perfect skin",
            "visual": "beauty tool shown with unsupported result claim",
            "pain": "skin texture concern",
            "product_first_ms": 900,
            "demo_type": "usage",
            "demo_action": "show beauty tool briefly touching skin",
            "proof_type": "testimonial",
            "proof": "creator makes a result claim without support",
            "creator_persona": "beauty reviewer",
            "delivery": "sales_pitch",
            "claim": "guarantees perfect skin instantly",
            "claim_category": "health",
            "claim_risk": "high",
            "cta": True,
            "offer": True,
            "product_present": True,
            "product_match_confidence": 0.82,
        },
    }


def _observation_bundle(duration_ms: int, scenario: dict[str, Any]) -> dict[str, Any]:
    product_present = bool(scenario["product_present"])
    duration_ms = max(0, int(duration_ms))
    product_first = (
        _bounded_start(int(scenario["product_first_ms"] or 0), duration_ms, 900)
        if product_present
        else None
    )
    product_start = int(product_first or 0)
    product_start, product_end = _bounded_range(product_start, product_start + 900, duration_ms)
    cta_start = max(0, min(max(duration_ms - 800, 0), 3200))
    cta_start, cta_end = _bounded_range(cta_start, cta_start + 700, duration_ms)
    demo_steps = []
    if product_present:
        demo_start, demo_end = _bounded_range(
            product_start + 300, product_start + 2100, duration_ms
        )
        demo_steps.append(
            {
                "observation_id": f"mock_{scenario['category']}_demo_step_001",
                "step_index": 1,
                "time_range": {"start_ms": demo_start, "end_ms": demo_end},
                "action": scenario["demo_action"],
                "product_visible": True,
                "mechanism_visible": True,
                "result_visible": True,
                "confidence": 0.86,
                "frame_storage_keys": ["mock/frame_002.jpg"],
            }
        )
    product_appearances = []
    if product_present:
        product_appearances.append(
            {
                "observation_id": f"mock_{scenario['category']}_product_appearance_001",
                "time_range": {"start_ms": product_start, "end_ms": product_end},
                "visibility": "clear" if product_start <= 3000 else "partial",
                "shot_type": "close_up" if product_start <= 3000 else "medium",
                "usage_visible": True,
                "product_match_confidence": scenario["product_match_confidence"],
                "confidence": 0.88,
                "frame_storage_keys": ["mock/frame_001.jpg"],
            }
        )
    proof_moments = []
    if product_present and scenario["proof_type"] != "none":
        proof_start, proof_end = _bounded_range(
            product_start + 1600, product_start + 2500, duration_ms
        )
        proof_moments.append(
            {
                "observation_id": f"mock_{scenario['category']}_proof_001",
                "time_range": {"start_ms": proof_start, "end_ms": proof_end},
                "proof_type": scenario["proof_type"],
                "description": scenario["proof"],
                "verifiability": "observable",
                "confidence": 0.84,
                "frame_storage_keys": ["mock/frame_002.jpg"],
            }
        )
    return {
        "schema_version": "media_observation_v1",
        "duration_ms": duration_ms,
        "hooks": [
            {
                "observation_id": f"mock_{scenario['category']}_hook_001",
                "time_range": {"start_ms": 0, "end_ms": min(1000, duration_ms)},
                "hook_type": scenario["hook_type"],
                "spoken_text": scenario["spoken"],
                "overlay_text": scenario["overlay"],
                "visual_description": scenario["visual"],
                "buyer_pain": scenario["pain"],
                "clarity": "clear",
                "face_present": True,
                "product_present": product_start == 0 if product_present else False,
                "confidence": 0.9,
                "frame_storage_keys": ["mock/frame_000.jpg"],
            }
        ],
        "product_appearances": product_appearances,
        "product_visibility": {
            "first_appearance_ms": product_first,
            "total_visible_ms": min(2500, duration_ms) if product_present else None,
            "screen_time_ratio": round(min(2500, duration_ms) / max(duration_ms, 1), 2)
            if product_present
            else None,
            "clear_close_up_present": product_present and product_start <= 3000,
            "usage_present": product_present,
        },
        "demo": {
            "detected": product_present,
            "demo_type": scenario["demo_type"],
            "steps": demo_steps,
            "before_state_visible": scenario["demo_type"] == "before_after",
            "after_state_visible": product_present,
            "mechanism_clarity": "clear" if product_present else "unknown",
            "continuity": "edited_but_clear" if product_present else "unknown",
            "confidence": 0.87 if product_present else 0,
        },
        "proof_moments": proof_moments,
        "ctas": [
            {
                "observation_id": f"mock_{scenario['category']}_cta_001",
                "time_range": {"start_ms": cta_start, "end_ms": cta_end},
                "modality": "spoken",
                "cta_type": "link_in_shop",
                "text": "I linked the product in my TikTok Shop.",
                "product_tag_visible": True,
                "confidence": 0.86,
                "frame_storage_keys": ["mock/frame_003.jpg"],
            }
        ]
        if scenario["cta"]
        else [],
        "offers": [
            {
                "observation_id": f"mock_{scenario['category']}_offer_001",
                "time_range": {"start_ms": cta_start - 600, "end_ms": cta_start},
                "offer_type": "value_statement",
                "text": "The current shop offer is shown near the product tag.",
                "price_text": None,
                "confidence": 0.78,
                "frame_storage_keys": ["mock/frame_003.jpg"],
            }
        ]
        if scenario["offer"] and cta_start >= 600
        else [],
        "creator": {
            "face_present": True,
            "speaking_present": scenario["spoken"] is not None,
            "delivery_style": scenario["delivery"],
            "creator_persona": scenario["creator_persona"],
            "emotion": "relieved",
            "pacing": "fast",
            "sales_language_intensity": "high"
            if scenario["claim_risk"] in {"high", "critical"}
            else "low",
            "authenticity_cues": ["first-person context"]
            + (["visible product use"] if product_present else []),
            "confidence": 0.82,
        },
        "editing": {
            "cut_count": 4,
            "average_shot_duration_ms": 900,
            "first_three_second_cut_count": 3,
            "pattern_interrupts": [],
            "dead_air_ranges": [],
            "caption_density": "medium",
            "visual_pacing": "fast",
            "transition_types": ["jump_cut"],
            "confidence": 0.78,
        },
        "claims": [
            {
                "observation_id": f"mock_{scenario['category']}_claim_001",
                "time_range": _time_range(1200, 2500, duration_ms),
                "text": scenario["claim"],
                "source": "spoken",
                "category": scenario["claim_category"],
                "risk": scenario["claim_risk"],
                "qualification_present": False,
                "confidence": 0.8,
                "frame_storage_keys": [],
            }
        ],
        "platform": {
            "aspect_ratio": "9:16",
            "vertical": True,
            "native_signals": ["first_person", "jump_cuts"],
            "shop_signals": ["tiktok_shop_mention"],
            "caption_style": ["short_overlay"],
            "visual_safe_zone_risk": False,
            "confidence": 0.86,
        },
        "uncertainties": [],
    }


def _bounded_start(start_ms: int, duration_ms: int, preferred_window_ms: int) -> int:
    if duration_ms <= 0:
        return 0
    latest_start = max(0, duration_ms - preferred_window_ms)
    return max(0, min(start_ms, latest_start))


def _bounded_range(start_ms: int, end_ms: int, duration_ms: int) -> tuple[int, int]:
    bounded_start = max(0, min(start_ms, duration_ms))
    bounded_end = max(bounded_start, min(end_ms, duration_ms))
    return bounded_start, bounded_end


def _time_range(start_ms: int, end_ms: int, duration_ms: int) -> dict[str, int]:
    bounded_start, bounded_end = _bounded_range(start_ms, end_ms, duration_ms)
    return {"start_ms": bounded_start, "end_ms": bounded_end}


def _adaptation_payload() -> dict[str, Any]:
    return {
        "schema_version": "adaptation_v2",
        "guidance": [
            {
                "element_type": "opening",
                "source_path": "creative_dna.opening",
                "action": "keep",
                "reason": "The opening shows the buyer pain immediately.",
                "evidence_ids": [],
                "product_context_refs": ["creative.primary_angles"],
                "risk_codes": [],
            },
            {
                "element_type": "product_context",
                "source_path": "product_context.identity",
                "action": "change",
                "reason": "Swap the reference product for the target product.",
                "evidence_ids": [],
                "product_context_refs": ["identity.name", "identity.category"],
                "risk_codes": [],
            },
            {
                "element_type": "claims",
                "source_path": "product_context.governance",
                "action": "avoid",
                "reason": "Do not predict viral, sales, or GMV performance.",
                "evidence_ids": [],
                "product_context_refs": ["governance.claims"],
                "risk_codes": ["UNSUPPORTED_CLAIM"],
            },
        ],
        "concepts": [
            _concept(
                "concept_1",
                "Result opener",
                "result_first",
                "visible before/after outcome",
                "authentic_review",
            ),
            _concept(
                "concept_2",
                "Problem to demo",
                "problem_first",
                "step-by-step use",
                "demonstration",
            ),
            _concept(
                "concept_3",
                "Proof-led review",
                "proof_first",
                "observable proof setup",
                "testimonial",
            ),
        ],
        "uncertainties": [],
    }


def _concept(
    concept_id: str,
    name: str,
    strategic_axis: str,
    demo_mechanism: str,
    delivery_style: str,
) -> dict[str, Any]:
    return {
        "id": concept_id,
        "name": name,
        "strategic_axis": strategic_axis,
        "angle": "product-specific observed use case",
        "buyer_persona_id": None,
        "buyer_persona_label": "documented buyer persona",
        "buyer_pain": "documented buyer pain",
        "desired_outcome": "documented product outcome",
        "creator_persona": "category creator",
        "delivery_style": delivery_style,
        "hook_options": ["Show the product context before making the claim."],
        "opening_visual": "show the actual product context",
        "demo_mechanism": demo_mechanism,
        "demo_sequence": ["show product", demo_mechanism, "show observable result"],
        "proof_mechanism": "observable result",
        "offer_framing": None if concept_id != "concept_3" else "optional value statement",
        "cta_strategy": "Keep CTA factual and use product tag when required.",
        "claim_guardrails": ["avoid unsupported claims"],
        "must_show": ["product visible", "demo in use", "observable result"],
        "risks": [],
        "test_hypothesis": "Test whether this ordering improves clarity without adding claims.",
        "source_evidence_ids": [],
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("MOCK_AI_PORT", "8787")))
