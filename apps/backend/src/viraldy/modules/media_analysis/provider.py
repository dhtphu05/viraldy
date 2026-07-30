from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from viraldy.modules.ai_gateway.public import OpenAICompatibleClient, extract_message_json
from viraldy.modules.ai_gateway.schemas import ProviderResponse
from viraldy.modules.media_analysis.contracts import MediaObservationBundleV1
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


class LiveAnalysisProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = OpenAICompatibleClient(settings)

    def transcribe_audio(self, audio_path: Path) -> TranscriptContract:
        return self.transcribe_audio_with_response(audio_path)[0]

    def transcribe_audio_with_response(
        self, audio_path: Path
    ) -> tuple[TranscriptContract, ProviderResponse | None]:
        if self._settings.asr_provider != "openai_compatible":
            return TranscriptContract(segments=[], full_text=""), None
        if not self._settings.asr_model:
            raise AppError(
                "AI_PROVIDER_NOT_CONFIGURED", "Live ASR requires ASR_MODEL.", status_code=503
            )
        response = self._client.transcribe(
            audio_path,
            {
                "model": self._settings.asr_model,
                "response_format": "verbose_json",
                "timestamp_granularities[]": "segment",
            },
        )
        payload = response.payload
        segments = [
            {
                "start_ms": round(float(segment.get("start", 0)) * 1000),
                "end_ms": round(float(segment.get("end", 0)) * 1000),
                "text": str(segment.get("text", "")).strip(),
            }
            for segment in payload.get("segments", [])
            if str(segment.get("text", "")).strip()
        ]
        contract = TranscriptContract(
            language=str(payload.get("language") or "en"),
            segments=segments,
            full_text=str(payload.get("text") or " ".join(item["text"] for item in segments)),
        )
        return contract, response

    def extract_ocr(
        self,
        frame_paths: list[tuple[int, Path, str]],
        product_context: dict[str, object] | None = None,
    ) -> OcrContract:
        return self.extract_ocr_with_response(frame_paths, product_context)[0]

    def extract_ocr_with_response(
        self,
        frame_paths: list[tuple[int, Path, str]],
        product_context: dict[str, object] | None = None,
    ) -> tuple[OcrContract, ProviderResponse | None]:
        if self._settings.ocr_provider != "vision":
            return OcrContract(), None
        context_json = json.dumps(product_context or {}, sort_keys=True)
        payload, response = self._vision_json_with_response(
            prompt=(
                "Extract readable on-screen text from these TikTok/UGC frames. "
                'Return JSON: {"segments":[{"start_ms":number,"end_ms":number,'
                '"text":"...","confidence":0..1,"frame_storage_key":"..."}]}. '
                "Use only visible text. Product context is supplied only to disambiguate the "
                "mock/local scenario and must not be used to invent OCR text."
                f"\nProduct context: {context_json}"
            ),
            frame_paths=frame_paths[:8],
            schema_name="OcrContract",
            schema_model=OcrContract,
        )
        return _validate_contract(OcrContract, payload, "OCR_OUTPUT_INVALID"), response

    def extract_visual_observations(
        self,
        frame_paths: list[tuple[int, Path, str]],
        transcript: TranscriptContract,
        ocr: OcrContract,
        product_context: dict[str, object] | None,
        duration_ms: int,
    ) -> MediaObservationBundleV1:
        return self.extract_visual_observations_with_response(
            frame_paths, transcript, ocr, product_context, duration_ms
        )[0]

    def extract_visual_observations_with_response(
        self,
        frame_paths: list[tuple[int, Path, str]],
        transcript: TranscriptContract,
        ocr: OcrContract,
        product_context: dict[str, object] | None,
        duration_ms: int,
    ) -> tuple[MediaObservationBundleV1, ProviderResponse]:
        payload, response = self._vision_json_with_response(
            prompt=(
                "Analyze the creative structure from frames, transcript, OCR, metadata, and "
                "product context. Return JSON matching MediaObservationBundleV1 exactly. "
                "Use only supplied frames, transcript, OCR, metadata, and product context. "
                "Return unknown when evidence is insufficient. Do not infer hidden events. "
                "Do not create timestamps that are not supported by frame, transcript, or OCR "
                "timing. Do not return a score or predict virality, orders, sales, or GMV. "
                "Every observation must have a stable observation_id, confidence in 0..1, and "
                "frame_storage_keys when frame evidence supports it. Use empty arrays when no CTA, "
                "offer, claim, proof, hook, or product appearance is detected."
                f"\nRequired schema_version: media_observation_v1"
                f"\nDuration_ms: {duration_ms}"
                f"\nTranscript: {transcript.model_dump(mode='json')}"
                f"\nOCR: {ocr.model_dump(mode='json')}"
                f"\nProduct context: {product_context or {}}"
            ),
            frame_paths=frame_paths[:12],
            schema_name="MediaObservationBundleV1",
            schema_model=MediaObservationBundleV1,
        )
        contract = _validate_contract(
            MediaObservationBundleV1, payload, "MEDIA_OBSERVATION_INVALID"
        )
        return contract, response

    def _vision_json(
        self,
        prompt: str,
        frame_paths: list[tuple[int, Path, str]],
    ) -> dict[str, Any]:
        return self._vision_json_with_response(prompt, frame_paths)[0]

    def _vision_json_with_response(
        self,
        prompt: str,
        frame_paths: list[tuple[int, Path, str]],
        schema_name: str | None = None,
        schema_model: type[BaseModel] | None = None,
    ) -> tuple[dict[str, Any], ProviderResponse]:
        if not self._settings.ai_vision_model:
            raise AppError(
                "AI_PROVIDER_NOT_CONFIGURED",
                "Live vision extraction requires AI_VISION_MODEL.",
                status_code=503,
            )
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
        payload: dict[str, Any] = {
            "model": self._settings.ai_vision_model,
            "messages": [{"role": "user", "content": content}],
            "response_format": _response_format(self._settings, schema_name, schema_model),
        }
        if self._settings.ai_max_output_tokens is not None:
            payload["max_tokens"] = self._settings.ai_max_output_tokens
        response = self._client.chat_json(payload)
        return extract_message_json(response), response


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


def _response_format(
    settings: Settings,
    schema_name: str | None,
    schema_model: type[BaseModel] | None,
) -> dict[str, object]:
    if not settings.ai_supports_json_schema or schema_name is None or schema_model is None:
        return {"type": "json_object"}
    return {
        "type": "json_schema",
        "json_schema": {
            "name": schema_name,
            "schema": schema_model.model_json_schema(),
            "strict": True,
        },
    }
