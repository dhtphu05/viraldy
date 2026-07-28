from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError


class TranscriptSegment(BaseModel):
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    text: str


class TranscriptContract(BaseModel):
    language: str = "en"
    segments: list[TranscriptSegment] = Field(default_factory=list)
    full_text: str = ""


class OcrSegment(BaseModel):
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    text: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    frame_storage_key: str | None = None


class OcrContract(BaseModel):
    segments: list[OcrSegment] = Field(default_factory=list)


class SceneItem(BaseModel):
    scene_index: int = Field(ge=0)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)


class SceneContract(BaseModel):
    scenes: list[SceneItem]


class ClaimCandidate(BaseModel):
    text: str
    risk: str
    timestamp_ms: int | None = Field(default=None, ge=0)


class VisualObservationsContract(BaseModel):
    product_first_appearance_ms: int | None = Field(default=None, ge=0)
    face_present_opening: bool = False
    opening_visual: str = "unknown"
    demo_detected: bool = False
    demo_type: str = "unknown"
    close_up_present: bool = False
    cta_visual_detected: bool = False
    proof_type: str = "unknown"
    creator_style: str = "unknown"
    claim_candidates: list[ClaimCandidate] = Field(default_factory=list)


class LiveAnalysisProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = (settings.ai_base_url or "").rstrip("/")
        self._api_key = settings.ai_api_key.get_secret_value() if settings.ai_api_key else ""

    def transcribe_audio(self, audio_path: Path) -> TranscriptContract:
        if self._settings.asr_provider != "openai_compatible":
            return TranscriptContract(segments=[], full_text="")
        if not self._settings.asr_model:
            raise AppError(
                "ASR_MODEL_NOT_CONFIGURED", "Live ASR requires ASR_MODEL.", status_code=503
            )
        import httpx

        with audio_path.open("rb") as audio_file:
            response = httpx.post(
                f"{self._base_url}/audio/transcriptions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                files={"file": (audio_path.name, audio_file, "audio/wav")},
                data={
                    "model": self._settings.asr_model,
                    "response_format": "verbose_json",
                    "timestamp_granularities[]": "segment",
                },
                timeout=self._settings.ai_request_timeout_seconds,
            )
        response.raise_for_status()
        payload = response.json()
        segments = [
            {
                "start_ms": round(float(segment.get("start", 0)) * 1000),
                "end_ms": round(float(segment.get("end", 0)) * 1000),
                "text": str(segment.get("text", "")).strip(),
            }
            for segment in payload.get("segments", [])
            if str(segment.get("text", "")).strip()
        ]
        return TranscriptContract(
            language=str(payload.get("language") or "en"),
            segments=segments,
            full_text=str(payload.get("text") or " ".join(item["text"] for item in segments)),
        )

    def extract_ocr(
        self,
        frame_paths: list[tuple[int, Path, str]],
    ) -> OcrContract:
        if self._settings.ocr_provider != "vision":
            return OcrContract()
        payload = self._vision_json(
            prompt=(
                "Extract readable on-screen text from these TikTok/UGC frames. "
                'Return JSON: {"segments":[{"start_ms":number,"end_ms":number,'
                '"text":"...","confidence":0..1,"frame_storage_key":"..."}]}. '
                "Use only visible text."
            ),
            frame_paths=frame_paths[:8],
        )
        return _validate_contract(OcrContract, payload, "OCR_OUTPUT_INVALID")

    def extract_visual_observations(
        self,
        frame_paths: list[tuple[int, Path, str]],
        transcript: TranscriptContract,
        ocr: OcrContract,
        product_context: dict[str, object] | None,
    ) -> VisualObservationsContract:
        payload = self._vision_json(
            prompt=(
                "Analyze the creative structure from frames, transcript, OCR, and product context. "
                "Return only JSON with keys: product_first_appearance_ms, face_present_opening, "
                "opening_visual, demo_detected, demo_type, close_up_present, cta_visual_detected, "
                "proof_type, creator_style, claim_candidates. Do not return a score."
                f"\nTranscript: {transcript.model_dump(mode='json')}"
                f"\nOCR: {ocr.model_dump(mode='json')}"
                f"\nProduct context: {product_context or {}}"
            ),
            frame_paths=frame_paths[:12],
        )
        return _validate_contract(
            VisualObservationsContract, payload, "VISUAL_OBSERVATIONS_INVALID"
        )

    def _vision_json(
        self,
        prompt: str,
        frame_paths: list[tuple[int, Path, str]],
    ) -> dict[str, Any]:
        if not self._settings.ai_vision_model:
            raise AppError(
                "AI_VISION_MODEL_NOT_CONFIGURED",
                "Live vision extraction requires AI_VISION_MODEL.",
                status_code=503,
            )
        import httpx

        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for timestamp_ms, path, storage_key in frame_paths:
            content.append(
                {
                    "type": "text",
                    "text": f"Frame timestamp_ms={timestamp_ms}, storage_key={storage_key}",
                }
            )
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{_b64(path)}"},
                }
            )
        response = httpx.post(
            f"{self._base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self._settings.ai_vision_model,
                "messages": [{"role": "user", "content": content}],
                "response_format": {"type": "json_object"},
            },
            timeout=self._settings.ai_request_timeout_seconds,
        )
        response.raise_for_status()
        text = response.json()["choices"][0]["message"]["content"]
        return json.loads(text)


def _validate_contract[T: BaseModel](model: type[T], payload: dict[str, Any], code: str) -> T:
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise AppError(
            code,
            "Live provider returned invalid structured output.",
            details={"errors": exc.errors()},
        ) from exc


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")
