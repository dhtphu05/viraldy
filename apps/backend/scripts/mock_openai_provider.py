from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, cast
from uuid import UUID

import uvicorn
from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.responses import Response

from viraldy.modules.creative_dna.contracts import CreativeDnaV1
from viraldy.modules.creative_dna.service import (
    _build_creative_dna,
    _evidence_by_type,
)
from viraldy.modules.media_analysis.models import EvidenceItemModel
from viraldy.modules.pattern_kits.contracts import PatternKitV1
from viraldy.modules.pattern_kits.provider import (
    PatternEvidenceInput,
    PatternSourceInput,
    build_fixture_pattern_kit,
)
from viraldy.modules.pattern_kits.public import PatternKitVersionSnapshot
from viraldy.modules.pattern_kits.schemas import CreatePatternKitRequest
from viraldy.modules.presentations.contracts import (
    CreatorRevisionInputV2,
    SellerDecisionInputV1,
)
from viraldy.modules.presentations.service import (
    build_deterministic_creator_message,
    build_deterministic_seller_summary,
)
from viraldy.modules.products.public import ProductContextSnapshot
from viraldy.modules.viral_kits.contracts import (
    ViralKitPatternMatchV1,
    ViralKitV1,
)
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
    viraldy_source_filename: Annotated[str | None, Form()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> JSONResponse:
    _require_auth_shape(authorization)
    await _maybe_fail()
    content = await file.read()
    if not content or not model:
        raise HTTPException(status_code=400, detail="file and model are required")
    if os.getenv("MOCK_AI_SCENARIO", "").strip() == "no_speech":
        return JSONResponse({"language": "en", "text": "", "segments": []})
    scenario = _transcription_scenario(viraldy_source_filename)
    transcript = str(scenario.get("transcript") or "").strip()
    if transcript:
        return JSONResponse(
            {
                "language": "en",
                "text": transcript,
                "segments": [
                    {"start": 0.0, "end": 3.8, "text": transcript},
                ],
            }
        )
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


def _transcription_scenario(source_filename: str | None) -> dict[str, Any]:
    filename = (source_filename or "").casefold()
    scenario_key = ""
    if "home_travel_steamer" in filename:
        scenario_key = "home_travel_appliance"
    elif "pod_dog_mom_crewneck" in filename:
        scenario_key = "pod_personalized_apparel"
    elif "dropshipping_bag_sealer" in filename:
        scenario_key = "kitchen_gadget"
    if scenario_key and ("revision" in filename or "draft-2" in filename):
        scenario_key = f"{scenario_key}:revision"
    return _scenarios().get(scenario_key, {})


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
    operation, context = _operation_context(prompt)
    if operation == "pattern_kit_extract":
        return _pattern_kit_payload(prompt)
    if operation == "creative_dna_build":
        return _creative_dna_payload(context)
    if operation == "viral_kit_compose":
        return _viral_kit_payload(prompt)
    if operation == "campaign_pack_generate":
        return _campaign_pack_payload(context)
    if operation == "adaptation_generate" or "Adapt this Creative DNA" in prompt:
        return _adaptation_payload(context)
    if operation == "seller_decision_summary":
        return _seller_summary_payload(context)
    if operation == "revision_message_generate":
        return _creator_revision_payload(context)
    return _vision_payload(prompt)


def _campaign_pack_payload(context: dict[str, Any]) -> dict[str, Any]:
    payload = _required_mapping(context, "operation_payload")
    baseline = payload.get("deterministic_requirement_baseline")
    if baseline is None:
        baseline = payload.get("protected_campaign_baseline")
    if not isinstance(baseline, dict):
        raise HTTPException(
            status_code=400,
            detail="campaign pack request is missing its protected baseline",
        )
    return cast(dict[str, Any], baseline)


def _pattern_kit_payload(prompt: str) -> dict[str, Any]:
    _, context = _operation_context(prompt)
    payload = _required_mapping(context, "operation_payload")
    request = CreatePatternKitRequest.model_validate(payload.get("request"))
    raw_sources = _required_list(payload, "sources")
    sources: list[PatternSourceInput] = []
    for raw_source in raw_sources:
        if not isinstance(raw_source, dict):
            raise HTTPException(status_code=400, detail="invalid PatternKit source")
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
        pattern_kit_id=UUID(str(payload["pattern_kit_id"])),
        workspace_id=UUID(str(context["workspace_id"])),
        version=int(payload["version"]),
        created_by=UUID(str(context["actor_user_id"])),
        created_at=datetime.fromisoformat(str(payload["created_at"])),
        request=request,
        sources=sources,
        model_run_id=UUID(str(payload["model_run_id"])),
    )
    pattern = pattern.model_copy(
        update={
            "source": pattern.source.model_copy(update={"extraction_mode": "ai_assisted"}),
        }
    )
    semantic_summary = _mock_pattern_summary(request.primary_category)
    if semantic_summary is not None:
        pattern = pattern.model_copy(
            update={
                "summary": semantic_summary,
            }
        )
    return pattern.model_dump(mode="json")


def _viral_kit_payload(prompt: str) -> dict[str, Any]:
    _, context = _operation_context(prompt)
    payload = _required_mapping(context, "operation_payload")
    request = CreateViralKitRequest.model_validate(payload.get("request"))
    product = ProductContextSnapshot.model_validate(_required_mapping(payload, "product_snapshot"))
    matches = [
        ViralKitPatternMatchV1.model_validate(item)
        for item in _required_list(payload, "pattern_matches")
    ]
    patterns = [
        PatternKitVersionSnapshot(
            pattern_kit_id=UUID(str(item["pattern_kit_id"])),
            pattern_kit_version_id=UUID(str(item["pattern_kit_version_id"])),
            workspace_id=UUID(str(context["workspace_id"])),
            version=int(item["version"]),
            status=str(item["status"]),
            pattern=PatternKitV1.model_validate(item["pattern"]),
        )
        for item in _required_list(payload, "pattern_payloads")
        if isinstance(item, dict)
    ]
    viral_kit = build_fixture_viral_kit(
        viral_kit_id=UUID(str(payload["viral_kit_id"])),
        workspace_id=UUID(str(context["workspace_id"])),
        version=int(payload["version"]),
        created_by=UUID(str(context["actor_user_id"])),
        created_at=datetime.fromisoformat(str(payload["created_at"])),
        request=request,
        product=product,
        patterns=patterns,
        pattern_matches=matches,
        model_run_id=UUID(str(payload["model_run_id"])),
    )
    return _specialize_mock_viral_kit(viral_kit).model_dump(mode="json")


def _mock_pattern_summary(category: str | None) -> str | None:
    summaries = {
        "home_travel_appliance": (
            "Deadline rescue with a fast product reveal and observable " "same-garment proof."
        ),
        "pod_personalized_apparel": (
            "Dog-mom identity hook, readable personalization reveal, emotional "
            "gift payoff, and clear ordering inputs."
        ),
        "kitchen_gadget": (
            "Snack-spill interruption, one-handed sealing demo, visible seal "
            "proof, and claim-safe trust cue."
        ),
    }
    return summaries.get(category or "")


def _specialize_mock_viral_kit(viral_kit: ViralKitV1) -> ViralKitV1:
    category = viral_kit.product.snapshot_json.identity.category
    specs = _domain_concept_specs(
        category,
        viral_kit.product.snapshot_json.identity.name,
    )
    if specs is None:
        return viral_kit
    concepts = []
    for concept, spec in zip(viral_kit.concepts, specs, strict=True):
        hook = concept.hook.model_copy(
            update={
                "hook_type": spec["hook_type"],
                "spoken_text": spec["spoken_hook"],
                "overlay_text": spec["overlay_hook"],
                "opening_visual": spec["opening_visual"],
                "buyer_pain": spec["buyer_pain"],
            }
        )
        concepts.append(
            concept.model_copy(
                update={
                    "name": spec["name"],
                    "strategic_axis": spec["strategic_axis"],
                    "diversity_axes": spec["diversity_axes"],
                    "buyer_persona_id": spec["buyer_persona_id"],
                    "buyer_persona_label": spec["buyer_persona_label"],
                    "buyer_pain": spec["buyer_pain"],
                    "desired_outcome": spec["desired_outcome"],
                    "creative_angle": spec["creative_angle"],
                    "hook": hook,
                    "opening_visual": spec["opening_visual"],
                    "narrative_structure": spec["narrative_structure"],
                    "creator_persona": spec["creator_persona"],
                    "delivery_style": spec["delivery_style"],
                    "demo_mechanism": spec["demo_mechanism"],
                    "proof_mechanism": spec["proof_mechanism"],
                    "overlays": [spec["overlay_hook"]],
                    "spoken_lines": [spec["spoken_hook"]],
                    "test_hypothesis": spec["test_hypothesis"],
                    "expected_learning": spec["expected_learning"],
                }
            )
        )
    matrix = viral_kit.test_matrix.model_copy(
        update={
            "concepts": [
                cell.model_copy(
                    update={
                        "hypothesis": concept.test_hypothesis,
                        "changed_axes": concept.diversity_axes,
                    }
                )
                for cell, concept in zip(
                    viral_kit.test_matrix.concepts,
                    concepts,
                    strict=True,
                )
            ]
        }
    )
    return ViralKitV1.model_validate(
        viral_kit.model_copy(
            update={
                "concepts": concepts,
                "test_matrix": matrix,
            }
        )
    )


def _domain_concept_specs(
    category: str,
    product_name: str,
) -> list[dict[str, Any]] | None:
    if category == "home_travel_appliance":
        return [
            _concept_spec(
                name="Late for class rescue",
                axis="student_deadline_pressure",
                buyer_id="college_student",
                buyer="College student in a dorm",
                pain="A wrinkled shirt minutes before class",
                outcome="A visibly smoother same shirt",
                creator="US college lifestyle creator",
                hook="I had ten minutes before class and this shirt was still wrinkled.",
                overlay="Deadline shirt rescue",
                opening="Open on the deadline, reveal the steamer immediately.",
                narrative="deadline -> fast product reveal -> same-shirt demo -> proof -> CTA",
                demo=f"Use {product_name} on the same shirt shown in the opening.",
                proof="Keep the same fabric visible before and after steaming.",
            ),
            _concept_spec(
                name="Carry-on clothing rescue",
                axis="traveler_carry_on_utility",
                buyer_id="frequent_traveler",
                buyer="Frequent traveler using carry-on luggage",
                pain="Unreliable hotel ironing setup",
                outcome="A compact garment-care routine",
                creator="US travel packing creator",
                hook="This is why I stopped relying on hotel irons.",
                overlay="Carry-on clothing rescue",
                opening="Show a wrinkled carry-on shirt beside the compact steamer.",
                narrative="travel problem -> product reveal -> hotel-room demo -> proof -> CTA",
                demo=f"Demonstrate {product_name} in a carry-on clothing setup.",
                proof="Show the treated section beside the untreated section.",
            ),
            _concept_spec(
                name="Small-space iron alternative",
                axis="apartment_space_saving",
                buyer_id="small_space_renter",
                buyer="Apartment renter with limited storage",
                pain="No room for an ironing board",
                outcome="A drawer-sized clothing-care setup",
                creator="Small-apartment lifestyle creator",
                hook="I do not have space for an ironing board.",
                overlay="No ironing board setup",
                opening="Show the small drawer, then the product and wrinkled shirt.",
                narrative="space constraint -> compact reveal -> garment demo -> proof -> CTA",
                demo=f"Show {product_name} replacing the board setup for one shirt.",
                proof="Keep the garment and treated area continuous on camera.",
            ),
        ]
    if category == "pod_personalized_apparel":
        return [
            _concept_spec(
                name="Dog mom identity",
                axis="self_purchase_identity",
                buyer_id="dog_mom_self_purchase",
                buyer="Self-purchase dog owner",
                pain="Generic pet apparel feels impersonal",
                outcome="A readable crewneck tied to her dog",
                creator="Dog-owner lifestyle creator",
                hook="Tell me you are a dog mom without telling me.",
                overlay="Made for this dog mom",
                opening="Open on the dog-mom identity, then reveal the readable pet name.",
                narrative="identity hook -> personalization reveal -> reaction -> ordering cue",
                demo="Show the physical garment and readable personalized name.",
                proof="Hold on the actual name, recipient, and design variant.",
            ),
            _concept_spec(
                name="Personalized gift reaction",
                axis="recipient_emotional_payoff",
                buyer_id="personalized_gift_buyer",
                buyer="Friend or partner buying a personalized gift",
                pain="Generic gifts lack emotional relevance",
                outcome="A correct gift with a genuine recipient reaction",
                creator="Gifting lifestyle creator",
                hook="Her reaction started when she read her dog's name.",
                overlay="A gift made for her dog",
                opening="Lead with the wrapped gift and recipient reaction.",
                narrative="gift setup -> name reveal -> emotional payoff -> ordering clarity",
                demo="Reveal the physical personalized crewneck to the recipient.",
                proof="Show the readable name and authentic gift reaction together.",
            ),
            _concept_spec(
                name="How personalization works",
                axis="ordering_clarity",
                buyer_id="product_aware_custom_shopper",
                buyer="Product-aware shopper checking custom inputs",
                pain="Concern that personalization or spelling could be wrong",
                outcome="Confidence in the submitted pet name and design",
                creator="Practical tutorial creator",
                hook="Here is exactly what you submit before ordering.",
                overlay="Input, preview, verify",
                opening="Show the pet-name input next to the delivered garment.",
                narrative="input -> preview -> physical product -> spelling check -> CTA",
                demo="Walk through pet name, recipient, and design inputs.",
                proof="Compare the submitted fields with the readable physical crewneck.",
            ),
        ]
    if category == "kitchen_gadget":
        return [
            _concept_spec(
                name="Dorm snack fix",
                axis="student_portability",
                buyer_id="college_student",
                buyer="College student carrying opened snacks",
                pain="Opened snacks spill inside a backpack",
                outcome="A compact supported-bag sealing routine",
                creator="Dorm lifestyle creator",
                hook="I was tired of chips spilling inside my backpack.",
                overlay="Dorm snack fix",
                opening="Interrupt the spill, then show the one-handed sealer.",
                narrative="mess -> one-handed demo -> visible seal proof -> trust cue",
                demo=f"Use {product_name} one-handed on a supported snack bag.",
                proof="Show the visible seal line without claiming universal airtightness.",
            ),
            _concept_spec(
                name="Family pantry routine",
                axis="household_organization",
                buyer_id="family_pantry_parent",
                buyer="Parent organizing opened snack bags",
                pain="Loose clips and opened bags clutter the pantry",
                outcome="A repeatable claim-safe pantry routine",
                creator="Family organization creator",
                hook="My pantry had more clips than snacks.",
                overlay="One pantry routine",
                opening="Show the clip clutter and a supported bag.",
                narrative="pantry problem -> product demo -> seal inspection -> storage",
                demo=f"Demonstrate {product_name} on one supported pantry bag.",
                proof="Inspect the visible seal and state bag compatibility limits.",
            ),
            _concept_spec(
                name="Travel packing utility",
                axis="carry_on_utility",
                buyer_id="traveler",
                buyer="Traveler packing supported snack bags",
                pain="Bag clips take space and detach in luggage",
                outcome="A compact packing method for supported bags",
                creator="Travel packing creator",
                hook="This is how I keep loose bag clips out of my carry-on.",
                overlay="Compact packing utility",
                opening="Show the carry-on packing problem before the sealing step.",
                narrative="packing problem -> compact demo -> visible seal -> trust cue",
                demo=f"Use {product_name} on a supported travel snack bag.",
                proof="Show the sealed edge and avoid leak-proof guarantees.",
            ),
        ]
    return None


def _concept_spec(
    *,
    name: str,
    axis: str,
    buyer_id: str,
    buyer: str,
    pain: str,
    outcome: str,
    creator: str,
    hook: str,
    overlay: str,
    opening: str,
    narrative: str,
    demo: str,
    proof: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "strategic_axis": axis,
        "diversity_axes": [
            "buyer_persona",
            "hook_mechanism",
            "narrative_structure",
        ],
        "buyer_persona_id": buyer_id,
        "buyer_persona_label": buyer,
        "buyer_pain": pain,
        "desired_outcome": outcome,
        "creative_angle": axis.replace("_", " "),
        "hook_type": axis,
        "spoken_hook": hook,
        "overlay_hook": overlay,
        "opening_visual": opening,
        "narrative_structure": narrative,
        "creator_persona": creator,
        "delivery_style": "authentic_review",
        "demo_mechanism": demo,
        "proof_mechanism": proof,
        "test_hypothesis": (
            f"Test whether the {axis.replace('_', ' ')} framing improves qualified "
            "creative signal."
        ),
        "expected_learning": (f"Learn whether {axis.replace('_', ' ')} fits this buyer context."),
    }


def _operation_context(prompt: str) -> tuple[str, dict[str, Any]]:
    for raw_line in reversed(prompt.splitlines()):
        candidate = raw_line.strip()
        if not candidate.startswith("{"):
            continue
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and parsed.get("operation") is not None:
            return str(parsed["operation"]), parsed
    raw_context = prompt.rsplit("\n\n", 1)[-1].strip()
    try:
        context = json.loads(raw_context)
    except json.JSONDecodeError:
        return "", {}
    if not isinstance(context, dict):
        return "", {}
    operation = context.get("operation")
    return (str(operation) if operation is not None else ""), context


def _creative_dna_payload(context: dict[str, Any]) -> dict[str, Any]:
    workspace_id = UUID(str(context["workspace_id"]))
    evidence_items: list[EvidenceItemModel] = []
    for raw in _required_list(context, "evidence_catalog"):
        if not isinstance(raw, dict):
            raise HTTPException(
                status_code=400,
                detail="invalid Creative DNA evidence item",
            )
        confidence = raw.get("confidence")
        evidence_items.append(
            EvidenceItemModel(
                id=UUID(str(raw["evidence_id"])),
                workspace_id=workspace_id,
                asset_version_id=UUID(str(raw["source_version_id"])),
                processing_job_id=None,
                stage="building_creative_dna",
                analysis_run_type="creative_dna_build",
                analysis_run_id=None,
                evidence_type=str(raw["evidence_type"]),
                evidence_schema_version="evidence_v1",
                observation_id=raw.get("observation_id"),
                identity_hash=None,
                start_ms=raw.get("start_ms"),
                end_ms=raw.get("end_ms"),
                frame_storage_key=None,
                value_json=_required_mapping(raw, "value"),
                confidence=(
                    Decimal(str(confidence)) if isinstance(confidence, int | float) else None
                ),
                source=str(raw["source"]),
                provider="mock",
                model_version="mock-creative-dna",
                pipeline_version="media_pipeline_v1",
            )
        )
    dna = _build_creative_dna(_evidence_by_type(evidence_items))
    return dna.model_dump(mode="json")


def _required_mapping(value: dict[str, Any], field: str) -> dict[str, Any]:
    nested = value.get(field)
    if not isinstance(nested, dict):
        raise HTTPException(status_code=400, detail=f"invalid prompt field: {field}")
    return nested


def _required_list(value: dict[str, Any], field: str) -> list[Any]:
    nested = value.get(field)
    if not isinstance(nested, list):
        raise HTTPException(status_code=400, detail=f"invalid prompt field: {field}")
    return nested


def _vision_payload(prompt: str) -> dict[str, Any]:
    frame_keys = _frame_storage_keys(prompt)
    if "Extract readable on-screen text" in prompt:
        scenario = _scenario(prompt)
        return {
            "segments": [
                {
                    "start_ms": scenario.get("ocr_start_ms", 0),
                    "end_ms": scenario.get("ocr_end_ms", 1000),
                    "text": scenario.get("ocr_text") or scenario["overlay"],
                    "confidence": 0.92,
                    "frame_storage_key": frame_keys[0] if frame_keys else None,
                }
            ]
        }
    duration_ms = _duration_ms(prompt)
    return _observation_bundle(duration_ms, _scenario(prompt), frame_keys)


def _duration_ms(prompt: str) -> int:
    match = re.search(r"(?:Duration_ms:\s*|\"duration_ms\":)(\d+)", prompt)
    return int(match.group(1)) if match else 4000


def _frame_storage_keys(prompt: str) -> list[str]:
    matches = re.findall(r"storage_key=([^,\s]+)", prompt)
    return list(dict.fromkeys(matches))


def _scenario(prompt: str) -> dict[str, Any]:
    scenario_id = os.getenv("MOCK_AI_SCENARIO", "").strip() or _category_from_prompt(prompt)
    scenarios = _scenarios()
    source_filename = _source_filename(prompt)
    if "revision" in source_filename.casefold():
        revision_id = f"{scenario_id}:revision"
        if revision_id in scenarios:
            scenario_id = revision_id
    return scenarios.get(scenario_id, scenarios["home_organization"])


def _category_from_prompt(prompt: str) -> str:
    for pattern in (r"'category':\s*'([^']+)'", r'"category":\s*"([^"]+)"'):
        match = re.search(pattern, prompt)
        if match:
            return match.group(1)
    return "home_organization"


def _source_filename(prompt: str) -> str:
    for pattern in (
        r'"source_filename":\s*"([^"]+)"',
        r"Source filename:\s*([^\n]+)",
    ):
        match = re.search(pattern, prompt)
        if match:
            return match.group(1)
    return ""


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
        "pod_personalized_apparel": {
            "category": "pod_personalized_apparel",
            "hook_type": "curiosity",
            "spoken": "Tell me you are a dog mom without telling me.",
            "overlay": "Made for this dog mom",
            "transcript": (
                "Tell me you are a dog mom without telling me. "
                "Show Personalized Dog Mom Crewneck clearly in the first product moment. "
                "Show readable personalization on the physical crewneck. "
                "Include the TikTok Shop product tag only after product context is clear. "
                "Use a factual TikTok Shop product-tag CTA after the product is shown."
            ),
            "ocr_text": (
                "Personalized Dog Mom Crewneck. Pet name: Miles. "
                "Recipient: Dog Mom. Design variant: Golden Retriever. "
                "Made for this dog mom. Physical crewneck. Product tag."
            ),
            "ocr_start_ms": 7200,
            "ocr_end_ms": 9600,
            "visual": "physical personalized crewneck reveal with readable custom detail",
            "pain": "generic pet apparel feels impersonal",
            "product_first_ms": 700,
            "demo_type": "unboxing",
            "demo_action": "show the physical garment and readable personalized name",
            "proof_type": "visual_result",
            "proof": "readable personalization on physical crewneck",
            "creator_persona": "dog mom lifestyle creator",
            "delivery": "storytelling",
            "claim": "personalized detail is visible on the physical sample",
            "claim_category": "other",
            "claim_risk": "low",
            "cta": True,
            "offer": False,
            "product_present": True,
            "product_match_confidence": 0.9,
        },
        "pod_personalized_apparel:revision": {
            "category": "pod_personalized_apparel",
            "hook_type": "curiosity",
            "spoken": "Tell me you are a dog mom without telling me.",
            "overlay": "Made for this dog mom",
            "transcript": (
                "Tell me you are a dog mom without telling me. "
                "Show Personalized Dog Mom Crewneck clearly in the first product moment. "
                "Show readable personalization on the physical crewneck. "
                "Include the TikTok Shop product tag only after product context is clear. "
                "Use a factual TikTok Shop product-tag CTA after the product is shown."
            ),
            "ocr_text": (
                "Personalized Dog Mom Crewneck. Pet name: Milo. "
                "Recipient: Dog Mom. Design variant: Golden Retriever. "
                "Made for this dog mom. Physical crewneck. Product tag."
            ),
            "ocr_start_ms": 4000,
            "ocr_end_ms": 10000,
            "visual": "correct physical crewneck with readable personalization",
            "pain": "personalization must match the approved order",
            "product_first_ms": 700,
            "demo_type": "result_reveal",
            "demo_action": "show the physical garment and readable personalized name",
            "proof_type": "visual_result",
            "proof": "readable personalization on physical crewneck",
            "creator_persona": "dog mom lifestyle creator",
            "delivery": "storytelling",
            "claim": "personalized detail is visible on the physical sample",
            "claim_category": "other",
            "claim_risk": "low",
            "cta": True,
            "offer": False,
            "product_present": True,
            "product_match_confidence": 0.9,
        },
        "home_travel_appliance": {
            "category": "home_travel_appliance",
            "hook_type": "problem_first",
            "spoken": "I had ten minutes before class and this shirt was still wrinkled.",
            "overlay": "Deadline shirt rescue",
            "transcript": (
                "I had ten minutes before class and this shirt was still wrinkled. "
                "Show SwiftPress Mini Garment Steamer clearly in the first product moment. "
                "Show the same-item before and after result. "
                "Include the TikTok Shop product tag only after product context is clear. "
                "Use a factual TikTok Shop product-tag CTA after the product is shown."
            ),
            "ocr_text": (
                "Wrinkled blue shirt. SwiftPress Mini Garment Steamer. "
                "Steam is visible. Deadline shirt rescue. Product tag."
            ),
            "ocr_start_ms": 0,
            "ocr_end_ms": 4200,
            "visual": "wrinkled shirt shown before a late steamer reveal",
            "pain": "wrinkled shirt before class",
            "product_first_ms": 4200,
            "demo_type": "usage",
            "demo_action": "show steam on a blue shirt without returning to the same area",
            "proof_type": "visual_result",
            "proof": "steam is visible but same-shirt before and after proof is absent",
            "creator_persona": "college lifestyle creator",
            "delivery": "demonstration",
            "claim": "steam is visible on the demonstrated shirt",
            "claim_category": "other",
            "claim_risk": "low",
            "cta": True,
            "offer": False,
            "product_present": True,
            "product_match_confidence": 0.9,
        },
        "home_travel_appliance:revision": {
            "category": "home_travel_appliance",
            "hook_type": "problem_first",
            "spoken": "I had ten minutes before class and this shirt was still wrinkled.",
            "overlay": "Deadline shirt rescue",
            "transcript": (
                "I had ten minutes before class and this shirt was still wrinkled. "
                "Show SwiftPress Mini Garment Steamer clearly in the first product moment. "
                "Show the same-item before and after result. "
                "Results vary by fabric type. "
                "Include the TikTok Shop product tag only after product context is clear. "
                "Use a factual TikTok Shop product-tag CTA after the product is shown."
            ),
            "ocr_text": (
                "SwiftPress Mini Garment Steamer. BEFORE same blue shirt. "
                "AFTER same blue shirt. Deadline shirt rescue. "
                "Results vary by fabric type. Product tag."
            ),
            "ocr_start_ms": 0,
            "ocr_end_ms": 18000,
            "visual": "steamer and same blue shirt shown through before, use, and after",
            "pain": "wrinkled shirt before class",
            "product_first_ms": 1400,
            "demo_type": "before_after",
            "demo_action": "show the same shirt before steaming during use and after",
            "proof_type": "before_after",
            "proof": "same-item before and after result on the same blue shirt",
            "creator_persona": "college lifestyle creator",
            "delivery": "demonstration",
            "claim": "the demonstrated shirt looks smoother after steaming",
            "claim_category": "performance",
            "claim_risk": "low",
            "cta": True,
            "offer": False,
            "product_present": True,
            "product_match_confidence": 0.9,
        },
        "kitchen_gadget": {
            "category": "kitchen_gadget",
            "hook_type": "problem_first",
            "spoken": "This makes every bag completely airtight.",
            "overlay": "Dorm snack fix",
            "transcript": (
                "I was tired of chips spilling inside my backpack. "
                "Show Rechargeable Mini Bag Sealer clearly in the first product moment. "
                "Show the visible result on the demonstrated bag. "
                "Include the TikTok Shop product tag only after product context is clear. "
                "Use a factual TikTok Shop product-tag CTA after the product is shown."
            ),
            "ocr_text": (
                "Rechargeable Mini Bag Sealer. This makes every bag completely airtight. "
                "Visible seal line. Dorm snack fix. Product tag."
            ),
            "ocr_start_ms": 8900,
            "ocr_end_ms": 10400,
            "visual": "one-handed sealing demo on one supported snack bag",
            "pain": "opened snack bags spill or go stale",
            "product_first_ms": 1100,
            "demo_type": "usage",
            "demo_action": "show one-handed sealing on the specific supported snack bag",
            "proof_type": "visual_result",
            "proof": "visible seal line on the demonstrated snack bag",
            "creator_persona": "student creator",
            "delivery": "demonstration",
            "claim": "This makes every bag completely airtight.",
            "claim_category": "guarantee",
            "claim_risk": "high",
            "cta": True,
            "offer": False,
            "product_present": True,
            "product_match_confidence": 0.9,
        },
        "kitchen_gadget:revision": {
            "category": "kitchen_gadget",
            "hook_type": "problem_first",
            "spoken": "I was tired of chips spilling inside my backpack.",
            "overlay": "Dorm snack fix",
            "transcript": (
                "I was tired of chips spilling inside my backpack. "
                "Show Rechargeable Mini Bag Sealer clearly in the first product moment. "
                "Show the visible result on the demonstrated bag. "
                "Include the TikTok Shop product tag only after product context is clear. "
                "Use a factual TikTok Shop product-tag CTA after the product is shown."
            ),
            "ocr_text": (
                "Rechargeable Mini Bag Sealer. Supported snack bag. "
                "Visible seal line. Dorm snack fix. Product tag."
            ),
            "ocr_start_ms": 0,
            "ocr_end_ms": 12000,
            "visual": "one-handed sealing demo with a visible seal line",
            "pain": "opened snack bags spill or go stale",
            "product_first_ms": 1100,
            "demo_type": "usage",
            "demo_action": "show one-handed sealing on the specific supported snack bag",
            "proof_type": "visual_result",
            "proof": "visible seal line on the demonstrated snack bag",
            "creator_persona": "student creator",
            "delivery": "demonstration",
            "claim": "I use it to reseal supported snack bags after opening.",
            "claim_category": "other",
            "claim_risk": "low",
            "cta": True,
            "offer": False,
            "product_present": True,
            "product_match_confidence": 0.9,
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


def _observation_bundle(
    duration_ms: int,
    scenario: dict[str, Any],
    frame_storage_keys: list[str] | None = None,
) -> dict[str, Any]:
    available_frames = frame_storage_keys or []

    def frame(index: int) -> list[str]:
        if not available_frames:
            return []
        return [available_frames[min(index, len(available_frames) - 1)]]

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
                "frame_storage_keys": frame(2),
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
                "frame_storage_keys": frame(1),
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
                "frame_storage_keys": frame(2),
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
                "frame_storage_keys": frame(0),
            }
        ],
        "on_screen_text": [
            {
                "observation_id": f"mock_{scenario['category']}_on_screen_text_001",
                "time_range": {
                    "start_ms": max(
                        0,
                        min(int(scenario.get("ocr_start_ms", 0)), duration_ms),
                    ),
                    "end_ms": max(
                        0,
                        min(int(scenario.get("ocr_end_ms", 1000)), duration_ms),
                    ),
                },
                "text": scenario.get("ocr_text") or scenario["overlay"],
                "text_role": "personalization"
                if "personalized" in str(scenario.get("ocr_text", "")).casefold()
                else "caption",
                "confidence": 0.92,
                "frame_storage_keys": frame(1),
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
                "cta_type": "product_tag",
                "text": "I linked the product in my TikTok Shop.",
                "spoken_text": "I linked the product in my TikTok Shop.",
                "overlay_text": "Product tag",
                "product_tag_visible": True,
                "confidence": 0.86,
                "frame_storage_keys": frame(3),
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
                "frame_storage_keys": frame(3),
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


def _adaptation_payload(context: dict[str, Any]) -> dict[str, Any]:
    product_context = _required_mapping(context, "product_context")
    identity = _required_mapping(product_context, "identity")
    product_name = str(identity["name"])
    governance = _required_mapping(product_context, "governance")
    guardrails = [
        str(claim["text"])
        for claim in _required_list(governance, "claims")
        if isinstance(claim, dict) and claim.get("rule_type") == "prohibited"
    ]
    guardrails.extend(str(item) for item in _required_list(governance, "prohibited_content"))
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
                f"{product_name} result opener",
                "result_first",
                "visible before/after outcome",
                "authentic_review",
                product_name,
                guardrails,
            ),
            _concept(
                "concept_2",
                f"{product_name} problem to demo",
                "problem_first",
                "step-by-step use",
                "demonstration",
                product_name,
                guardrails,
            ),
            _concept(
                "concept_3",
                f"{product_name} proof-led review",
                "proof_first",
                "observable proof setup",
                "testimonial",
                product_name,
                guardrails,
            ),
        ],
        "uncertainties": [],
    }


def _seller_summary_payload(context: dict[str, Any]) -> dict[str, Any]:
    operation_payload = _required_mapping(context, "operation_payload")
    input_data = SellerDecisionInputV1.model_validate(operation_payload.get("presentation_input"))
    return build_deterministic_seller_summary(input_data).model_dump(mode="json")


def _creator_revision_payload(context: dict[str, Any]) -> dict[str, Any]:
    operation_payload = _required_mapping(context, "operation_payload")
    input_data = CreatorRevisionInputV2.model_validate(operation_payload.get("presentation_input"))
    return build_deterministic_creator_message(input_data).model_dump(mode="json")


def _concept(
    concept_id: str,
    name: str,
    strategic_axis: str,
    demo_mechanism: str,
    delivery_style: str,
    product_name: str,
    guardrails: list[str],
) -> dict[str, Any]:
    return {
        "id": concept_id,
        "name": name,
        "strategic_axis": strategic_axis,
        "angle": f"product-specific observed use case for {product_name}",
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
        "claim_guardrails": guardrails,
        "must_show": ["product visible", "demo in use", "observable result"],
        "risks": [],
        "test_hypothesis": "Test whether this ordering improves clarity without adding claims.",
        "source_evidence_ids": [],
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("MOCK_AI_PORT", "8787")))
