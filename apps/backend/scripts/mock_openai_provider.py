from __future__ import annotations

import asyncio
import json
import os
from typing import Annotated, Any

import uvicorn
from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse

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
    return JSONResponse(
        {
            "language": "en",
            "text": "My counter was always a mess until this rack gave me space back.",
            "segments": [
                {"start": 0.0, "end": 2.1, "text": "My counter was always a mess."},
                {"start": 6.5, "end": 9.2, "text": "This rack gave me space back."},
                {"start": 18.2, "end": 20.0, "text": "I linked it in my TikTok Shop."},
            ],
        }
    )


@app.post("/v1/chat/completions")
async def chat_completions(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
):
    _require_auth_shape(authorization)
    failure = os.getenv("MOCK_AI_FAILURE", "")
    if failure == "malformed_json":
        return PlainTextResponse("{not-json", media_type="application/json")
    await _maybe_fail(failure)
    body = await request.json()
    if not body.get("model") or not isinstance(body.get("messages"), list):
        raise HTTPException(status_code=400, detail="model and messages are required")
    prompt = _prompt_text(body["messages"])
    content = (
        _adaptation_payload() if "Adapt this Creative DNA" in prompt else _vision_payload(prompt)
    )
    if failure == "missing_field":
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


def _vision_payload(prompt: str) -> dict[str, Any]:
    if "Extract readable on-screen text" in prompt:
        return {
            "segments": [
                {
                    "start_ms": 0,
                    "end_ms": 2100,
                    "text": "My counter was always a mess",
                    "confidence": 0.92,
                    "frame_storage_key": "mock/frame_000.jpg",
                }
            ]
        }
    return {
        "product_first_appearance_ms": 1200,
        "face_present_opening": True,
        "opening_visual": "messy kitchen counter",
        "demo_detected": True,
        "demo_type": "before_after",
        "close_up_present": True,
        "cta_visual_detected": True,
        "proof_type": "visual_result",
        "creator_style": "authentic_review",
        "claim_candidates": [
            {"text": "gave me space back", "risk": "low", "timestamp_ms": 9200}
        ],
    }


def _adaptation_payload() -> dict[str, Any]:
    return {
        "keep": [
            {
                "element": "problem_first_structure",
                "reason": "The opening shows the buyer pain immediately.",
                "evidence_ids": [],
            }
        ],
        "change": [
            {
                "element": "product_context",
                "reason": "Swap the reference product for the target product.",
                "evidence_ids": [],
            }
        ],
        "avoid": [
            {
                "element": "unsupported_claims",
                "reason": "Do not predict viral, sales, or GMV performance.",
                "evidence_ids": [],
            }
        ],
        "concepts": [
            _concept("concept_1", "Small counter reset", "small_space_convenience"),
            _concept("concept_2", "Morning routine fix", "faster_daily_routine"),
            _concept("concept_3", "Rental-friendly upgrade", "no_damage_home_upgrade"),
        ],
    }


def _concept(concept_id: str, name: str, angle: str) -> dict[str, Any]:
    return {
        "id": concept_id,
        "name": name,
        "angle": angle,
        "buyer_persona": "US apartment renter",
        "creator_persona": "home organizer",
        "hook": "This fixed my tiny kitchen problem",
        "opening_visual": "crowded counter before shot",
        "demo_sequence": ["show clutter", "show product", "demo use", "show result"],
        "proof": "before_after",
        "cta": "Linked in my TikTok Shop",
        "risks": [],
        "test_hypothesis": "Test whether visible space gain drives saves and clicks.",
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("MOCK_AI_PORT", "8787")))
