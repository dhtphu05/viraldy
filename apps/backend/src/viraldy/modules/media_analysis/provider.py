from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypedDict, cast
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError

from viraldy.modules.ai_gateway.providers import (
    AiProviderError,
    AudioTranscriptionRequest,
    AudioTranscriptionResult,
    InputImagePart,
    OpenAINativeProvider,
    StructuredGenerationResult,
)
from viraldy.modules.ai_gateway.public import (
    AiOperationName,
    OpenAICompatibleClient,
    ViraldyOperationContextV1,
    execute_structured_operation,
    extract_message_json,
    get_prompt_package,
    provider_error_to_app_error,
)
from viraldy.modules.ai_gateway.request_identity import structured_request_hash
from viraldy.modules.ai_gateway.schemas import ProviderResponse
from viraldy.modules.media_analysis.contracts import MediaObservationBundleV1
from viraldy.modules.products.contracts import ProductContextV1
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError

type ProviderCallMetadata = ProviderResponse | StructuredGenerationResult | AudioTranscriptionResult


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


class _TranscriptSegmentPayload(TypedDict):
    start_ms: int
    end_ms: int
    text: str


class LiveAnalysisProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = OpenAICompatibleClient(settings)

    def transcribe_audio(self, audio_path: Path) -> TranscriptContract:
        return self.transcribe_audio_with_response(audio_path)[0]

    def transcribe_audio_with_response(
        self,
        audio_path: Path,
        *,
        request_id: str | None = None,
        workspace_id: UUID | None = None,
        source_filename: str | None = None,
    ) -> tuple[TranscriptContract, ProviderCallMetadata | None]:
        if self._settings.ai_provider == "openai":
            input_hash = _file_hash(audio_path)
            request_hash = structured_request_hash(
                operation="audio_transcription",
                model=self._settings.openai_transcription_model,
                prompt_version="audio_transcription_v1",
                schema_version="audio_transcript_v1",
                input_hash=input_hash,
            )
            request = AudioTranscriptionRequest(
                audio_path=audio_path,
                model=self._settings.openai_transcription_model,
                request_id=request_id or input_hash,
                input_hash=input_hash,
                request_hash=request_hash,
                workspace_id=workspace_id,
                response_format="verbose_json",
                timestamp_granularities=(
                    self._settings.openai_transcription_timestamp_granularities
                ),
            )
            try:
                result = OpenAINativeProvider(self._settings).transcribe_audio(request)
            except AiProviderError as exc:
                raise provider_error_to_app_error(
                    exc,
                    input_hash=input_hash,
                    request_hash=request_hash,
                ) from exc
            return (
                TranscriptContract(
                    language=result.language or "en",
                    segments=[
                        TranscriptSegment(
                            start_ms=segment.start_ms,
                            end_ms=segment.end_ms,
                            text=segment.text,
                        )
                        for segment in result.segments
                    ],
                    full_text=result.full_text,
                ),
                result,
            )
        if self._settings.asr_provider != "openai_compatible":
            return TranscriptContract(segments=[], full_text=""), None
        if not self._settings.asr_model:
            raise AppError(
                "AI_PROVIDER_NOT_CONFIGURED", "Live ASR requires ASR_MODEL.", status_code=503
            )
        request_data = {
            "model": self._settings.asr_model,
            "response_format": "verbose_json",
            "timestamp_granularities[]": "segment",
        }
        if self._settings.ai_mode == "mock" and source_filename:
            request_data["viraldy_source_filename"] = source_filename
        response = self._client.transcribe(
            audio_path,
            request_data,
        )
        payload = response.payload
        raw_segments = cast(list[dict[str, object]], payload.get("segments", []))
        segments: list[_TranscriptSegmentPayload] = [
            {
                "start_ms": round(float(cast(str | int | float, segment.get("start", 0))) * 1000),
                "end_ms": round(float(cast(str | int | float, segment.get("end", 0))) * 1000),
                "text": str(segment.get("text", "")).strip(),
            }
            for segment in raw_segments
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
        *,
        source_filename: str | None = None,
    ) -> OcrContract:
        return self.extract_ocr_with_response(
            frame_paths,
            product_context,
            source_filename=source_filename,
        )[0]

    def extract_ocr_with_response(
        self,
        frame_paths: list[tuple[int, Path, str]],
        product_context: dict[str, object] | None = None,
        *,
        source_filename: str | None = None,
    ) -> tuple[OcrContract, ProviderCallMetadata | None]:
        if self._settings.ai_provider == "openai":
            return OcrContract(), None
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
                f"\nSource filename: {source_filename or 'unknown'}"
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
        *,
        workspace_id: UUID | None = None,
        asset_id: UUID | None = None,
        asset_version_id: UUID | None = None,
        source_filename: str | None = None,
        request_id: str | None = None,
    ) -> tuple[MediaObservationBundleV1, ProviderCallMetadata]:
        if self._settings.ai_provider == "openai":
            if workspace_id is None or asset_id is None or asset_version_id is None:
                raise AppError(
                    "OPENAI_DOMAIN_VALIDATION_FAILED",
                    "Native media observation requires workspace and asset context.",
                )
            prompt = get_prompt_package(AiOperationName.MEDIA_OBSERVATION)
            selected_frames = frame_paths
            context = ViraldyOperationContextV1(
                operation=AiOperationName.MEDIA_OBSERVATION,
                request_id=request_id or str(asset_version_id),
                workspace_id=workspace_id,
                product_context=(
                    ProductContextV1.model_validate(product_context) if product_context else None
                ),
                source_artifact_ids=[asset_id],
                source_version_ids=[asset_version_id],
                operation_payload={
                    "asset_id": str(asset_id),
                    "asset_version_id": str(asset_version_id),
                    "source_filename": source_filename,
                    "duration_ms": duration_ms,
                    "frames": [
                        {
                            "timestamp_ms": timestamp_ms,
                            "frame_storage_key": storage_key,
                        }
                        for timestamp_ms, _, storage_key in selected_frames
                    ],
                    "transcript": bounded_transcript_payload(
                        transcript,
                        self._settings.openai_max_transcript_chars,
                    ),
                    "ocr": ocr.model_dump(mode="json"),
                },
                schema_version=prompt.output_schema_version,
                prompt_version=prompt.prompt_version,
            )
            result = execute_structured_operation(
                self._settings,
                context,
                MediaObservationBundleV1,
                image_parts=[
                    InputImagePart(
                        media_type="image/jpeg",
                        image_base64=_b64(path),
                        detail=self._settings.openai_image_detail,
                    )
                    for _, path, _ in selected_frames
                ],
                output_validator=_native_media_output_validator(
                    duration_ms,
                    {storage_key for _, _, storage_key in selected_frames},
                ),
            )
            return (
                MediaObservationBundleV1.model_validate(result.parsed_output),
                result,
            )
        prompt = get_prompt_package(AiOperationName.MEDIA_OBSERVATION)
        compatible_context = json.dumps(
            {
                "operation": AiOperationName.MEDIA_OBSERVATION.value,
                "workspace_id": str(workspace_id) if workspace_id else None,
                "asset_id": str(asset_id) if asset_id else None,
                "asset_version_id": str(asset_version_id) if asset_version_id else None,
                "source_filename": source_filename,
                "duration_ms": duration_ms,
                "frames": [
                    {
                        "timestamp_ms": timestamp_ms,
                        "frame_storage_key": storage_key,
                    }
                    for timestamp_ms, _, storage_key in frame_paths
                ],
                "transcript": bounded_transcript_payload(
                    transcript,
                    self._settings.openai_max_transcript_chars,
                ),
                "ocr": ocr.model_dump(mode="json"),
                "product_context": product_context,
                "schema_version": prompt.output_schema_version,
                "prompt_version": prompt.prompt_version,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        payload, response = self._vision_json_with_response(
            prompt=(
                f"{prompt.system_prompt}\n\n"
                f"{prompt.developer_prompt}\n\n"
                f"{compatible_context}"
            ),
            frame_paths=frame_paths[:12],
            schema_name="MediaObservationBundleV1",
            schema_model=MediaObservationBundleV1,
        )
        contract = _validate_contract(
            MediaObservationBundleV1, payload, "MEDIA_OBSERVATION_INVALID"
        )
        try:
            _native_media_output_validator(
                duration_ms,
                {storage_key for _, _, storage_key in frame_paths},
            )(contract)
        except ValueError as exc:
            raise AppError(
                "MEDIA_OBSERVATION_INVALID",
                "Live provider returned invalid media provenance.",
            ) from exc
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


def _native_media_output_validator(
    expected_duration_ms: int,
    allowed_frame_storage_keys: set[str],
) -> Callable[[BaseModel], None]:
    def validate(output: BaseModel) -> None:
        observations = MediaObservationBundleV1.model_validate(output)
        if observations.duration_ms != expected_duration_ms:
            raise ValueError("Media duration changed.")
        references = [
            *observations.hooks,
            *observations.product_appearances,
            *observations.demo.steps,
            *observations.proof_moments,
            *observations.ctas,
            *observations.offers,
            *observations.claims,
        ]
        referenced_keys = {
            storage_key for reference in references for storage_key in reference.frame_storage_keys
        }
        if not referenced_keys.issubset(allowed_frame_storage_keys):
            raise ValueError("Media observations reference frames outside the request.")

    return validate


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


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bounded_transcript_payload(
    transcript: TranscriptContract,
    max_chars: int,
) -> dict[str, object]:
    payload = transcript.model_dump(mode="json")
    full_text = transcript.full_text[:max_chars]
    payload["full_text"] = full_text
    used = 0
    bounded_segments: list[dict[str, object]] = []
    for segment in transcript.segments:
        remaining = max_chars - used
        if remaining <= 0:
            break
        text = segment.text[:remaining]
        bounded_segments.append(
            {
                "start_ms": segment.start_ms,
                "end_ms": segment.end_ms,
                "text": text,
            }
        )
        used += len(text)
    payload["segments"] = bounded_segments
    return payload


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
