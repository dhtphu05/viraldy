from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess  # nosec B404
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, TypeVar, cast
from uuid import UUID

import structlog
from PIL import Image
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from viraldy.modules.ai_gateway.public import (
    MEDIA_OBSERVATION_PROMPT_NAME,
    MEDIA_OBSERVATION_PROMPT_VERSION,
    AiModelRunModel,
)
from viraldy.modules.ai_gateway.repository import SyncAiModelRunRepository
from viraldy.modules.ai_gateway.request_identity import (
    stable_json_hash,
    structured_request_hash,
)
from viraldy.modules.ai_gateway.usage import ProviderUsage
from viraldy.modules.ai_gateway.workspace_limiter import (
    WorkspaceConcurrencyBusy,
    WorkspaceLimiterUnavailable,
    redis_workspace_request_limiter,
)
from viraldy.modules.assets.public import AssetVersionModel, AssetVersionSnapshot
from viraldy.modules.creative_domain.schema_versions import (
    EVIDENCE_SCHEMA_VERSION,
    MEDIA_OBSERVATION_SCHEMA_VERSION,
)
from viraldy.modules.media_analysis.contracts import MediaObservationBundleV1, TimeRangeV1
from viraldy.modules.media_analysis.fixtures import fixture_media_contract, is_known_fixture
from viraldy.modules.media_analysis.json_safety import sanitize_postgres_json
from viraldy.modules.media_analysis.models import EvidenceItemModel
from viraldy.modules.media_analysis.provider import (
    LiveAnalysisProvider,
    OcrContract,
    ProviderCallMetadata,
    SceneContract,
    TranscriptContract,
    bounded_transcript_payload,
)
from viraldy.modules.media_analysis.repository import SyncMediaAnalysisRepository
from viraldy.modules.products.public import ProductContextSnapshot, SyncProductQueries
from viraldy.platform.config.settings import Settings
from viraldy.platform.storage.ports import StoragePort
from viraldy.platform.storage.s3 import S3StorageAdapter
from viraldy.shared.errors.base import AppError

MEDIA_PIPELINE_VERSION = "media_pipeline_v2_scene_cost_controls"
MEDIA_ANALYSIS_PROMPT_VERSION = "media_analysis_prompt_v1"
MEDIA_ANALYSIS_SCHEMA_VERSION = "media_analysis_schema_v1"
SUPPORTED_CONTAINERS = {"mov,mp4,m4a,3gp,3g2,mj2", "mp4", "mov"}
SUBPROCESS_TIMEOUT_SECONDS = 120
T = TypeVar("T")
logger = structlog.get_logger(__name__)


class _UseAssetProductContext:
    pass


_USE_ASSET_PRODUCT_CONTEXT = _UseAssetProductContext()


@dataclass(frozen=True)
class MediaEvidencePipelineResult:
    evidence: list[EvidenceItemModel]
    primary_model_run_id: UUID | None


@contextmanager
def _cleanup_uploaded_objects_on_failure(
    storage: StoragePort,
) -> Iterator[list[str]]:
    uploaded_keys: list[str] = []
    try:
        yield uploaded_keys
    except Exception:
        for object_key in reversed(uploaded_keys):
            try:
                storage.delete_object(object_key)
            except Exception:
                logger.exception(
                    "media_artifact_failure_cleanup_failed",
                    storage_key=object_key,
                )
        raise


def validate_live_ai_settings(settings: Settings) -> None:
    if settings.ai_mode != "live":
        return
    if settings.ai_provider == "openai":
        missing = []
        if not settings.openai_api_key:
            missing.append("OPENAI_API_KEY")
        if not settings.openai_text_model:
            missing.append("OPENAI_TEXT_MODEL")
        if not settings.openai_vision_model:
            missing.append("OPENAI_VISION_MODEL")
        if not settings.openai_transcription_model:
            missing.append("OPENAI_TRANSCRIPTION_MODEL")
        if missing:
            raise AppError(
                "AI_PROVIDER_NOT_CONFIGURED",
                f"Live OpenAI mode requires: {', '.join(missing)}.",
                status_code=503,
            )
        return

    missing = []
    if not settings.ai_base_url:
        missing.append("AI_BASE_URL")
    if not settings.ai_api_key:
        missing.append("AI_API_KEY")
    if not settings.ai_text_model:
        missing.append("AI_TEXT_MODEL")
    if not settings.ai_vision_model:
        missing.append("AI_VISION_MODEL")
    if missing:
        raise AppError(
            "AI_PROVIDER_NOT_CONFIGURED",
            f"Live AI mode requires: {', '.join(missing)}.",
            status_code=503,
        )


class SyncMediaEvidencePipeline:
    def __init__(
        self,
        session: Session,
        settings: Settings,
        storage: StoragePort | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._storage = storage or S3StorageAdapter(settings)
        self._repository = SyncMediaAnalysisRepository(session)

    def process(
        self,
        snapshot: AssetVersionSnapshot,
        run_type: str,
        processing_job_id: UUID | None = None,
    ) -> list[EvidenceItemModel]:
        return self.process_with_metadata(snapshot, run_type, processing_job_id).evidence

    def process_with_metadata(
        self,
        snapshot: AssetVersionSnapshot,
        run_type: str,
        processing_job_id: UUID | None = None,
        *,
        product_context_snapshot: (
            ProductContextSnapshot | None | _UseAssetProductContext
        ) = _USE_ASSET_PRODUCT_CONTEXT,
    ) -> MediaEvidencePipelineResult:
        if self._settings.ai_mode == "fixture":
            return MediaEvidencePipelineResult(
                self._process_fixture(snapshot, run_type, processing_job_id), None
            )
        validate_live_ai_settings(self._settings)
        return self._process_live(
            snapshot,
            run_type,
            processing_job_id,
            product_context_snapshot,
        )

    def _process_fixture(
        self, snapshot: AssetVersionSnapshot, run_type: str, processing_job_id: UUID | None
    ) -> list[EvidenceItemModel]:
        if not is_known_fixture(snapshot.checksum_sha256, snapshot.metadata_json):
            raise AppError(
                "UNSUPPORTED_FIXTURE_ASSET",
                (
                    "Fixture analysis only supports seeded demo assets. "
                    "Set AI_MODE=live for real media."
                ),
            )
        contract = fixture_media_contract(snapshot.checksum_sha256, snapshot.metadata_json)
        reusable = self._repository.list_reusable_evidence(
            snapshot.workspace_id,
            snapshot.asset_version_id,
            str(contract["provider"]),
            str(contract["model_version"]),
            MEDIA_PIPELINE_VERSION,
        )
        if reusable:
            return reusable
        self._update_version_metadata(snapshot.asset_version_id, contract["metadata"])
        artifacts = self._artifact_rows(snapshot.workspace_id, snapshot.asset_version_id, contract)
        evidence = self._evidence_rows(snapshot.asset_version_id, run_type, contract)
        return self._repository.replace_artifacts_and_evidence(
            snapshot.workspace_id,
            snapshot.asset_version_id,
            processing_job_id,
            MEDIA_PIPELINE_VERSION,
            artifacts,
            evidence,
        )

    def _process_live(
        self,
        snapshot: AssetVersionSnapshot,
        run_type: str,
        processing_job_id: UUID | None,
        product_context_snapshot: ProductContextSnapshot | None | _UseAssetProductContext,
    ) -> MediaEvidencePipelineResult:
        product_snapshot = self._resolve_product_context_snapshot(
            snapshot,
            product_context_snapshot,
        )
        analysis_snapshot = replace(
            snapshot,
            product_id=(product_snapshot.product_id if product_snapshot is not None else None),
        )
        claim_hash = _media_analysis_claim_hash(
            analysis_snapshot,
            self._settings,
            product_context_version=(
                product_snapshot.product_context_version if product_snapshot is not None else None
            ),
            product_context_hash=(
                _hash_json(product_snapshot.product_context.model_dump(mode="json"))
                if product_snapshot is not None
                else None
            ),
        )
        lease_seconds = (
            self._settings.openai_request_timeout_seconds
            * (self._settings.openai_max_retries + 1)
            * 4
            + 120
        )
        limiter = redis_workspace_request_limiter(self._settings.redis_url)
        try:
            with limiter.named_slot(
                (f"media-analysis:workspace:{snapshot.workspace_id}" f":request:{claim_hash}"),
                max_parallel=1,
                wait_timeout_seconds=min(
                    float(self._settings.job_stale_after_seconds),
                    lease_seconds,
                ),
                lease_seconds=lease_seconds,
            ):
                return self._process_live_claimed(
                    analysis_snapshot,
                    run_type,
                    processing_job_id,
                    product_snapshot,
                )
        except WorkspaceConcurrencyBusy as exc:
            raise AppError(
                "OPENAI_WORKSPACE_BUSY",
                "An identical media analysis is already in progress.",
                status_code=429,
            ) from exc
        except WorkspaceLimiterUnavailable as exc:
            raise AppError(
                "OPENAI_GUARDRAIL_UNAVAILABLE",
                "The media-analysis concurrency guardrail is unavailable; no request was sent.",
                status_code=503,
            ) from exc

    def _process_live_claimed(
        self,
        snapshot: AssetVersionSnapshot,
        run_type: str,
        processing_job_id: UUID | None,
        product_snapshot: ProductContextSnapshot | None,
    ) -> MediaEvidencePipelineResult:
        provider_name = self._settings.ai_provider
        model_version = (
            self._settings.resolve_openai_model("media_observation", vision=True)
            if provider_name == "openai"
            else self._settings.ai_vision_model or self._settings.ai_text_model or "live"
        )
        product_context = (
            product_snapshot.product_context.model_dump(mode="json")
            if product_snapshot is not None
            else None
        )
        prefix = f"viraldy-{processing_job_id or snapshot.asset_version_id}-"
        with tempfile.TemporaryDirectory(prefix=prefix) as temp_dir:
            work_dir = Path(temp_dir)
            source_path = work_dir / f"source{_extension(snapshot.original_filename)}"
            self._storage.download_object(snapshot.storage_key, str(source_path))
            if not source_path.exists() or source_path.stat().st_size <= 0:
                raise AppError("MEDIA_DOWNLOAD_FAILED", "Downloaded media object is empty.")
            if snapshot.size_bytes and source_path.stat().st_size != snapshot.size_bytes:
                raise AppError("MEDIA_DOWNLOAD_FAILED", "Downloaded media size did not match.")

            metadata = self.probe_local_file(source_path)
            self._update_version_metadata(snapshot.asset_version_id, metadata)
            duration_ms = int(cast(int, metadata["duration_ms"]))
            has_audio = int(cast(int, metadata.get("audio_stream_count") or 0)) > 0
            scenes = _detect_scenes(source_path, duration_ms)

            thumbnail_path = work_dir / "thumbnail.jpg"
            audio_path = work_dir / "audio.wav"
            frame_dir = work_dir / "frames"
            frame_dir.mkdir()
            required_timestamps = tuple(
                evidence.start_ms
                for evidence in self._repository.list_evidence(
                    snapshot.workspace_id,
                    snapshot.asset_version_id,
                )
                if evidence.frame_storage_key is not None and evidence.start_ms is not None
            )
            _run_ffmpeg(
                ["-ss", "0.5", "-i", str(source_path), "-frames:v", "1", str(thumbnail_path)]
            )
            if has_audio:
                _run_ffmpeg(
                    [
                        "-i",
                        str(source_path),
                        "-vn",
                        "-ac",
                        "1",
                        "-ar",
                        "16000",
                        "-y",
                        str(audio_path),
                    ]
                )
            frame_paths = _sample_frames(
                source_path,
                frame_dir,
                duration_ms,
                snapshot.workspace_id,
                snapshot.asset_id,
                snapshot.asset_version_id,
                scenes=scenes,
                max_frames=(
                    self._settings.openai_max_frames_per_video
                    if self._settings.ai_provider == "openai"
                    else 30
                ),
                max_long_edge=self._settings.openai_max_frame_long_edge,
                required_timestamps=required_timestamps,
            )
            persisted_inputs = self._repository.get_reusable_observation_inputs(
                snapshot.workspace_id,
                snapshot.asset_version_id,
                provider_name,
                model_version,
                MEDIA_PIPELINE_VERSION,
            )
            if persisted_inputs is not None:
                try:
                    cached_transcript = TranscriptContract.model_validate(persisted_inputs[0])
                    cached_ocr = OcrContract.model_validate(persisted_inputs[1])
                except ValidationError:
                    cached_transcript = None
                    cached_ocr = None
                if cached_transcript is not None and cached_ocr is not None:
                    cached_request_hash = _media_analysis_request_hash(
                        snapshot,
                        self._settings,
                        product_context_version=(
                            product_snapshot.product_context_version
                            if product_snapshot is not None
                            else None
                        ),
                        product_context=product_context,
                        metadata=metadata,
                        scenes=scenes,
                        frame_paths=frame_paths,
                        audio_path=audio_path if has_audio else None,
                        transcript=cached_transcript,
                        ocr=cached_ocr,
                    )
                    reusable = self._repository.list_reusable_evidence(
                        snapshot.workspace_id,
                        snapshot.asset_version_id,
                        provider_name,
                        model_version,
                        MEDIA_PIPELINE_VERSION,
                        cached_request_hash,
                    )
                    if reusable:
                        return MediaEvidencePipelineResult(reusable, None)

            provider = LiveAnalysisProvider(self._settings)
            if has_audio:
                transcript, transcript_run_id = self._tracked_provider_call(
                    snapshot,
                    processing_job_id,
                    "audio_transcription",
                    (
                        self._settings.openai_transcription_model
                        if self._settings.ai_provider == "openai"
                        else self._settings.asr_model or "asr"
                    ),
                    {
                        "asset_version_id": str(snapshot.asset_version_id),
                        "audio_artifact": "audio.wav",
                        "run_type": run_type,
                    },
                    lambda: provider.transcribe_audio_with_response(
                        audio_path,
                        request_id=str(processing_job_id or snapshot.asset_version_id),
                        workspace_id=snapshot.workspace_id,
                        source_filename=snapshot.original_filename,
                    ),
                )
            else:
                transcript = TranscriptContract(segments=[], full_text="")
                transcript_run_id = None
            if self._settings.ocr_provider == "vision" and self._settings.ai_provider != "openai":
                ocr, ocr_run_id = self._tracked_provider_call(
                    snapshot,
                    processing_job_id,
                    "visual_ocr",
                    self._settings.ai_vision_model or "vision",
                    {
                        "asset_version_id": str(snapshot.asset_version_id),
                        "frame_count": len(frame_paths[:8]),
                        "run_type": run_type,
                    },
                    lambda: provider.extract_ocr_with_response(
                        frame_paths,
                        product_context,
                        source_filename=snapshot.original_filename,
                    ),
                )
            else:
                ocr = provider.extract_ocr(
                    frame_paths,
                    product_context,
                    source_filename=snapshot.original_filename,
                )
                ocr_run_id = None

            analysis_request_hash = _media_analysis_request_hash(
                snapshot,
                self._settings,
                product_context_version=(
                    product_snapshot.product_context_version
                    if product_snapshot is not None
                    else None
                ),
                product_context=product_context,
                metadata=metadata,
                scenes=scenes,
                frame_paths=frame_paths,
                audio_path=audio_path if has_audio else None,
                transcript=transcript,
                ocr=ocr,
            )
            reusable = self._repository.list_reusable_evidence(
                snapshot.workspace_id,
                snapshot.asset_version_id,
                provider_name,
                model_version,
                MEDIA_PIPELINE_VERSION,
                analysis_request_hash,
            )
            if reusable:
                return MediaEvidencePipelineResult(reusable, None)

            observations, vision_run_id = self._tracked_provider_call(
                snapshot,
                processing_job_id,
                "visual_observations",
                (
                    self._settings.resolve_openai_model(
                        "media_observation",
                        vision=True,
                    )
                    if self._settings.ai_provider == "openai"
                    else self._settings.ai_vision_model or "vision"
                ),
                {
                    "asset_version_id": str(snapshot.asset_version_id),
                    "frame_count": len(frame_paths),
                    "transcript_segments": len(transcript.segments),
                    "ocr_segments": len(ocr.segments),
                    "run_type": run_type,
                },
                lambda: provider.extract_visual_observations_with_response(
                    frame_paths,
                    transcript,
                    ocr,
                    product_context,
                    int(cast(int, metadata["duration_ms"])),
                    workspace_id=snapshot.workspace_id,
                    asset_id=snapshot.asset_id,
                    asset_version_id=snapshot.asset_version_id,
                    source_filename=snapshot.original_filename,
                    request_id=str(processing_job_id or snapshot.asset_version_id),
                ),
            )
            base_key = (
                f"workspaces/{snapshot.workspace_id}/assets/{snapshot.asset_id}"
                f"/versions/{snapshot.asset_version_id}/artifacts"
            )
            thumbnail_key = f"{base_key}/thumbnail.jpg"
            audio_key = f"{base_key}/audio.wav" if has_audio else None
            with _cleanup_uploaded_objects_on_failure(self._storage) as uploaded_keys:
                uploaded_keys.append(thumbnail_key)
                self._storage.upload_file(str(thumbnail_path), thumbnail_key, "image/jpeg")
                if has_audio and audio_key is not None:
                    uploaded_keys.append(audio_key)
                    self._storage.upload_file(str(audio_path), audio_key, "audio/wav")
                for _, path, storage_key in frame_paths:
                    uploaded_keys.append(storage_key)
                    self._storage.upload_file(str(path), storage_key, "image/jpeg")
                contract = _live_contract(
                    metadata,
                    thumbnail_key,
                    audio_key,
                    frame_paths,
                    transcript,
                    ocr,
                    scenes,
                    observations,
                    self._settings,
                )
                artifacts = self._artifact_rows(
                    snapshot.workspace_id, snapshot.asset_version_id, contract
                )
                evidence = [
                    {**item, "analysis_request_hash": analysis_request_hash}
                    for item in self._evidence_rows(
                        snapshot.asset_version_id,
                        run_type,
                        contract,
                    )
                ]
                persisted = self._repository.replace_artifacts_and_evidence(
                    snapshot.workspace_id,
                    snapshot.asset_version_id,
                    processing_job_id,
                    MEDIA_PIPELINE_VERSION,
                    artifacts,
                    evidence,
                )
                self._session.commit()
                return MediaEvidencePipelineResult(
                    persisted, vision_run_id or ocr_run_id or transcript_run_id
                )

    def _tracked_provider_call(
        self,
        snapshot: AssetVersionSnapshot,
        processing_job_id: UUID | None,
        capability: str,
        model: str,
        input_summary: dict[str, object],
        call: Callable[[], tuple[T, ProviderCallMetadata | None]],
    ) -> tuple[T, UUID | None]:
        operation, prompt_name, prompt_version, schema_version, endpoint_family = (
            _tracked_operation_metadata(
                capability,
                native_openai=self._settings.ai_provider == "openai",
            )
        )
        model_run_repository = SyncAiModelRunRepository(self._session)
        model_run = model_run_repository.create_running(
            workspace_id=snapshot.workspace_id,
            processing_job_id=processing_job_id,
            subject_type="asset_version",
            subject_id=snapshot.asset_version_id,
            capability=capability,
            operation=operation,
            analysis_mode=self._settings.ai_mode,
            provider=self._settings.ai_provider,
            model=model,
            prompt_version=prompt_version,
            response_schema_version=schema_version,
            schema_version=schema_version,
            request_hash=_hash_json({"capability": capability, "input_summary": input_summary}),
            input_hash=_hash_json({"capability": capability, "input_summary": input_summary}),
            input_summary=input_summary,
            endpoint_family=endpoint_family,
            prompt_name=prompt_name,
        )
        try:
            result, response = call()
        except AppError as exc:
            error_input_hash = exc.details.get("input_hash")
            error_request_hash = exc.details.get("request_hash")
            if isinstance(error_input_hash, str) and isinstance(error_request_hash, str):
                model_run_repository.update_identity(
                    model_run,
                    input_hash=error_input_hash,
                    request_hash=error_request_hash,
                )
            _fail_tracked_model_run(self._session, model_run, exc)
            raise
        if response is None:
            model_run_repository.complete(model_run, {}, None, None, None)
        else:
            usage = getattr(response, "usage", None)
            repair_attempt_count = getattr(response, "repair_attempt_count", 0)
            response_input_hash = getattr(response, "input_hash", None)
            response_request_hash = getattr(response, "request_hash", None)
            if isinstance(response_input_hash, str) and isinstance(response_request_hash, str):
                model_run_repository.update_identity(
                    model_run,
                    input_hash=response_input_hash,
                    request_hash=response_request_hash,
                )
            model_run_repository.complete(
                model_run,
                _provider_output_summary(result),
                response.http_status,
                response.provider_request_id,
                response.latency_ms,
                usage_json=(
                    usage.model_dump(mode="json") if isinstance(usage, ProviderUsage) else None
                ),
                repair_attempt_count=(
                    repair_attempt_count if isinstance(repair_attempt_count, int) else 0
                ),
            )
        return result, model_run.id

    def probe_local_file(self, path: Path) -> dict[str, object]:
        ffprobe_path = shutil.which("ffprobe")
        if not ffprobe_path:
            raise AppError("FFPROBE_NOT_AVAILABLE", "ffprobe is required for live local probing.")
        result = _run_subprocess(
            [
                ffprobe_path,
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_streams",
                "-show_format",
                str(path),
            ],
            "FFPROBE_FAILED",
            "ffprobe could not inspect the uploaded media.",
        )
        payload = json.loads(result.stdout)
        streams = payload.get("streams", [])
        video_streams = [s for s in streams if s.get("codec_type") == "video"]
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
        if not video_streams:
            raise AppError("MEDIA_UNREADABLE", "No readable video stream exists.")
        first_video = video_streams[0]
        duration_seconds = float(payload.get("format", {}).get("duration") or 0)
        if duration_seconds <= 0:
            raise AppError("MEDIA_UNREADABLE", "Media duration is zero or unreadable.")
        if duration_seconds > self._settings.max_media_duration_seconds:
            raise AppError("MEDIA_TOO_LONG", "Media exceeds the local MVP duration limit.")
        container = payload.get("format", {}).get("format_name")
        if isinstance(container, str) and container not in SUPPORTED_CONTAINERS:
            raise AppError("MEDIA_UNREADABLE", "Media container is not supported.")
        width = first_video.get("width")
        height = first_video.get("height")
        if not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
            raise AppError("MEDIA_UNREADABLE", "Media dimensions are unreadable.")
        fps = _fps(first_video.get("avg_frame_rate"))
        if fps is not None and (fps <= 0 or fps > 240):
            raise AppError("MEDIA_UNREADABLE", "Media FPS is outside the supported range.")
        return {
            "duration_ms": round(duration_seconds * 1000),
            "container": container,
            "video_codec": first_video.get("codec_name"),
            "audio_codec": audio_streams[0].get("codec_name") if audio_streams else None,
            "width": width,
            "height": height,
            "fps": fps,
            "video_stream_count": len(video_streams),
            "audio_stream_count": len(audio_streams),
        }

    def _update_version_metadata(self, asset_version_id: UUID, metadata: dict[str, object]) -> None:
        version = self._session.execute(
            select(AssetVersionModel).where(AssetVersionModel.id == asset_version_id)
        ).scalar_one()
        version.duration_ms = int(cast(int, metadata["duration_ms"]))
        version.width = int(cast(int, metadata["width"]))
        version.height = int(cast(int, metadata["height"]))
        version.metadata_json = {**version.metadata_json, "media": metadata}
        version.validation_status = "processed"

    def _artifact_rows(
        self,
        workspace_id: UUID,
        asset_version_id: UUID,
        contract: dict[str, Any],
    ) -> list[dict[str, Any]]:
        provider = str(contract["provider"])
        mode = str(contract["analysis_mode"])
        model_version = str(contract["model_version"])
        rows = [
            ("video_metadata", None, contract["metadata"]),
            ("transcript", None, contract["transcript"]),
            ("ocr", None, contract["ocr"]),
            ("sampled_frames", None, contract["sampled_frames"]),
            ("scene_boundaries", None, contract["scene_boundaries"]),
            ("visual_observations", None, contract["visual_observations"]),
            (
                "artifact_manifest",
                None,
                {
                    "pipeline_version": MEDIA_PIPELINE_VERSION,
                    "asset_version_id": str(asset_version_id),
                    "input_checksum": contract["metadata"].get("checksum_sha256"),
                    "artifacts": [],
                },
            ),
            (
                "thumbnail",
                contract.get("thumbnail_storage_key", "fixtures/opening.jpg"),
                {"timestamp_ms": 500},
            ),
        ]
        default_audio_key = "fixtures/audio.wav" if mode == "fixture" else None
        audio_key = contract.get("audio_storage_key", default_audio_key)
        if audio_key is not None:
            rows.append(("audio", audio_key, {"fixture": mode == "fixture"}))
        artifact_rows: list[dict[str, Any]] = []
        for ordinal, (artifact_type, storage_key, payload) in enumerate(rows):
            safe_payload = sanitize_postgres_json(payload)
            artifact_rows.append(
                {
                "workspace_id": workspace_id,
                "asset_version_id": asset_version_id,
                "artifact_type": artifact_type,
                "stage": _artifact_stage(artifact_type),
                "ordinal": ordinal,
                "storage_key": storage_key,
                "sha256": _hash_json({"storage_key": storage_key, "payload": safe_payload}),
                "payload_json": safe_payload,
                "provider": provider,
                "model_version": model_version,
                "analysis_mode": mode,
                }
            )
        return artifact_rows

    def _evidence_rows(
        self,
        asset_version_id: UUID,
        run_type: str,
        contract: dict[str, Any],
    ) -> list[dict[str, Any]]:
        provider = str(contract["provider"])
        model_version = str(contract["model_version"])
        observations = MediaObservationBundleV1.model_validate(contract["visual_observations"])
        rows: list[dict[str, Any]] = []
        for segment in contract["transcript"]["segments"]:
            rows.append(
                _row(
                    asset_version_id,
                    run_type,
                    "transcript_segment",
                    "asr",
                    provider,
                    model_version,
                    {
                        "schema_version": EVIDENCE_SCHEMA_VERSION,
                        "evidence_type": "transcript_segment",
                        "observation_id": None,
                        "text": str(segment["text"]),
                        "start_ms": int(segment["start_ms"]),
                        "end_ms": int(segment["end_ms"]),
                    },
                )
            )
        for segment in contract["ocr"]["segments"]:
            rows.append(
                _row(
                    asset_version_id,
                    run_type,
                    "on_screen_text",
                    "ocr",
                    provider,
                    model_version,
                    {
                        "schema_version": EVIDENCE_SCHEMA_VERSION,
                        "evidence_type": "on_screen_text",
                        "observation_id": None,
                        "text": str(segment["text"]),
                        "start_ms": int(segment["start_ms"]),
                        "end_ms": int(segment["end_ms"]),
                        "frame_storage_key": segment.get("frame_storage_key"),
                        "confidence": segment.get("confidence"),
                    },
                )
            )
        for text_observation in observations.on_screen_text:
            rows.append(
                _row(
                    asset_version_id,
                    run_type,
                    "on_screen_text",
                    "vision",
                    provider,
                    model_version,
                    {
                        "schema_version": EVIDENCE_SCHEMA_VERSION,
                        "evidence_type": "on_screen_text",
                        "observation_id": text_observation.observation_id,
                        "text": text_observation.text,
                        "text_role": text_observation.text_role,
                        "confidence": text_observation.confidence,
                        **_time_fields(text_observation.time_range),
                        "frame_storage_key": (
                            text_observation.frame_storage_keys[0]
                            if text_observation.frame_storage_keys
                            else None
                        ),
                    },
                )
            )
        for hook in observations.hooks:
            rows.append(
                _row(
                    asset_version_id,
                    run_type,
                    "hook_signal",
                    "vision",
                    provider,
                    model_version,
                    {
                        "schema_version": EVIDENCE_SCHEMA_VERSION,
                        "evidence_type": "hook_signal",
                        "observation_id": hook.observation_id,
                        "hook_type": hook.hook_type,
                        "spoken_text": hook.spoken_text,
                        "overlay_text": hook.overlay_text,
                        "visual_description": hook.visual_description,
                        "buyer_pain": hook.buyer_pain,
                        "clarity": hook.clarity,
                        "confidence": hook.confidence,
                        **_time_fields(hook.time_range),
                        "frame_storage_keys": hook.frame_storage_keys,
                    },
                )
            )
        for appearance in observations.product_appearances:
            rows.append(
                _row(
                    asset_version_id,
                    run_type,
                    "product_appearance",
                    "vision",
                    provider,
                    model_version,
                    {
                        "schema_version": EVIDENCE_SCHEMA_VERSION,
                        "evidence_type": "product_appearance",
                        "observation_id": appearance.observation_id,
                        "visibility": appearance.visibility,
                        "shot_type": appearance.shot_type,
                        "usage_visible": appearance.usage_visible,
                        "product_match_confidence": appearance.product_match_confidence,
                        "confidence": appearance.confidence,
                        **_time_fields(appearance.time_range),
                        "frame_storage_keys": appearance.frame_storage_keys,
                    },
                )
            )
        rows.append(
            _row(
                asset_version_id,
                run_type,
                "product_visibility_summary",
                "derived",
                provider,
                model_version,
                {
                    "schema_version": EVIDENCE_SCHEMA_VERSION,
                    "evidence_type": "product_visibility_summary",
                    "observation_id": None,
                    **observations.product_visibility.model_dump(mode="json"),
                },
            )
        )
        if observations.demo.detected:
            rows.append(
                _row(
                    asset_version_id,
                    run_type,
                    "demo_summary",
                    "vision",
                    provider,
                    model_version,
                    {
                        "schema_version": EVIDENCE_SCHEMA_VERSION,
                        "evidence_type": "demo_summary",
                        "observation_id": None,
                        **observations.demo.model_dump(mode="json", exclude={"steps"}),
                    },
                )
            )
            for step in observations.demo.steps:
                rows.append(
                    _row(
                        asset_version_id,
                        run_type,
                        "demo_step",
                        "vision",
                        provider,
                        model_version,
                        {
                            "schema_version": EVIDENCE_SCHEMA_VERSION,
                            "evidence_type": "demo_step",
                            "observation_id": step.observation_id,
                            "step_index": step.step_index,
                            "action": step.action,
                            "product_visible": step.product_visible,
                            "mechanism_visible": step.mechanism_visible,
                            "result_visible": step.result_visible,
                            "confidence": step.confidence,
                            **_time_fields(step.time_range),
                            "frame_storage_keys": step.frame_storage_keys,
                        },
                    )
                )
        for proof in observations.proof_moments:
            rows.append(
                _row(
                    asset_version_id,
                    run_type,
                    "proof_signal",
                    "vision",
                    provider,
                    model_version,
                    {
                        "schema_version": EVIDENCE_SCHEMA_VERSION,
                        "evidence_type": "proof_signal",
                        "observation_id": proof.observation_id,
                        "proof_type": proof.proof_type,
                        "description": proof.description,
                        "verifiability": proof.verifiability,
                        "confidence": proof.confidence,
                        **_time_fields(proof.time_range),
                        "frame_storage_keys": proof.frame_storage_keys,
                    },
                )
            )
        for cta in observations.ctas:
            rows.append(
                _row(
                    asset_version_id,
                    run_type,
                    "cta_signal",
                    "vision",
                    provider,
                    model_version,
                    {
                        "schema_version": EVIDENCE_SCHEMA_VERSION,
                        "evidence_type": "cta_signal",
                        "observation_id": cta.observation_id,
                        "modality": cta.modality,
                        "cta_type": cta.cta_type,
                        "text": cta.text,
                        "spoken_text": cta.spoken_text,
                        "overlay_text": cta.overlay_text,
                        "product_tag_visible": cta.product_tag_visible,
                        "confidence": cta.confidence,
                        **_time_fields(cta.time_range),
                        "frame_storage_keys": cta.frame_storage_keys,
                    },
                )
            )
        for offer in observations.offers:
            rows.append(
                _row(
                    asset_version_id,
                    run_type,
                    "offer_signal",
                    "vision",
                    provider,
                    model_version,
                    {
                        "schema_version": EVIDENCE_SCHEMA_VERSION,
                        "evidence_type": "offer_signal",
                        "observation_id": offer.observation_id,
                        "offer_type": offer.offer_type,
                        "text": offer.text,
                        "price_text": offer.price_text,
                        "discount_text": offer.discount_text,
                        "urgency_present": offer.urgency_present,
                        "confidence": offer.confidence,
                        **_time_fields(offer.time_range),
                        "frame_storage_keys": offer.frame_storage_keys,
                    },
                )
            )
        rows.append(
            _row(
                asset_version_id,
                run_type,
                "creator_signal",
                "vision",
                provider,
                model_version,
                {
                    "schema_version": EVIDENCE_SCHEMA_VERSION,
                    "evidence_type": "creator_signal",
                    "observation_id": None,
                    **observations.creator.model_dump(mode="json"),
                },
            )
        )
        rows.append(
            _row(
                asset_version_id,
                run_type,
                "editing_signal",
                "derived",
                provider,
                model_version,
                {
                    "schema_version": EVIDENCE_SCHEMA_VERSION,
                    "evidence_type": "editing_signal",
                    "observation_id": None,
                    **observations.editing.model_dump(mode="json"),
                },
            )
        )
        for claim in observations.claims:
            rows.append(
                _row(
                    asset_version_id,
                    run_type,
                    "claim_signal",
                    "vision",
                    provider,
                    model_version,
                    {
                        "schema_version": EVIDENCE_SCHEMA_VERSION,
                        "evidence_type": "claim_signal",
                        "observation_id": claim.observation_id,
                        "text": claim.text,
                        "source": claim.source,
                        "category": claim.category,
                        "risk": claim.risk,
                        "qualification_present": claim.qualification_present,
                        "confidence": claim.confidence,
                        **_optional_time_fields(claim.time_range),
                        "frame_storage_keys": claim.frame_storage_keys,
                    },
                )
            )
        rows.append(
            _row(
                asset_version_id,
                run_type,
                "platform_signal",
                "derived",
                provider,
                model_version,
                {
                    "schema_version": EVIDENCE_SCHEMA_VERSION,
                    "evidence_type": "platform_signal",
                    "observation_id": None,
                    **observations.platform.model_dump(mode="json"),
                },
            )
        )
        return rows

    def _product_context_snapshot(
        self,
        snapshot: AssetVersionSnapshot,
    ) -> ProductContextSnapshot | None:
        if snapshot.product_id is None:
            return None
        return SyncProductQueries(self._session).get_product_context_snapshot(
            snapshot.workspace_id, snapshot.product_id
        )

    def _resolve_product_context_snapshot(
        self,
        snapshot: AssetVersionSnapshot,
        override: ProductContextSnapshot | None | _UseAssetProductContext,
    ) -> ProductContextSnapshot | None:
        if isinstance(override, _UseAssetProductContext):
            return self._product_context_snapshot(snapshot)
        return override


def _row(
    asset_version_id: UUID,
    run_type: str,
    evidence_type: str,
    source: str,
    provider: str,
    model_version: str,
    value: dict[str, Any],
) -> dict[str, Any]:
    safe_value = sanitize_postgres_json(value)
    return {
        "asset_version_id": asset_version_id,
        "analysis_run_type": run_type,
        "evidence_type": evidence_type,
        "stage": "extracting_evidence",
        "identity_hash": _hash_json(
            {
                "asset_version_id": str(asset_version_id),
                "run_type": run_type,
                "evidence_type": evidence_type,
                "source": source,
                "value": safe_value,
            }
        ),
        "start_ms": safe_value.get("start_ms"),
        "end_ms": safe_value.get("end_ms"),
        "frame_storage_key": _frame_storage_key(safe_value),
        "value_json": safe_value,
        "confidence": safe_value.get("confidence"),
        "source": source,
        "provider": provider,
        "model_version": model_version,
        "evidence_schema_version": safe_value.get("schema_version", EVIDENCE_SCHEMA_VERSION),
        "observation_id": safe_value.get("observation_id"),
    }


def _time_fields(time_range: TimeRangeV1) -> dict[str, int]:
    return {"start_ms": time_range.start_ms, "end_ms": time_range.end_ms}


def _optional_time_fields(time_range: TimeRangeV1 | None) -> dict[str, int | None]:
    if time_range is None:
        return {"start_ms": None, "end_ms": None}
    return {
        "start_ms": time_range.start_ms,
        "end_ms": time_range.end_ms,
    }


def _frame_storage_key(value: dict[str, Any]) -> object:
    frame_storage_key = value.get("frame_storage_key")
    if frame_storage_key:
        return frame_storage_key
    frame_storage_keys = value.get("frame_storage_keys")
    if isinstance(frame_storage_keys, list) and frame_storage_keys:
        return frame_storage_keys[0]
    return None


def _fps(value: object) -> float | None:
    if not isinstance(value, str) or "/" not in value:
        return None
    numerator, denominator = value.split("/", 1)
    try:
        den = float(denominator)
        return None if den == 0 else round(float(numerator) / den, 2)
    except ValueError:
        return None


def _extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return suffix if suffix in {".mp4", ".mov", ".qt"} else ".mp4"


def _media_analysis_request_hash(
    snapshot: AssetVersionSnapshot,
    settings: Settings,
    *,
    product_context_version: int | None,
    product_context: dict[str, object] | None,
    metadata: dict[str, object],
    scenes: SceneContract,
    frame_paths: list[tuple[int, Path, str]],
    audio_path: Path | None,
    transcript: TranscriptContract,
    ocr: OcrContract,
) -> str:
    model = (
        settings.resolve_openai_model("media_observation", vision=True)
        if settings.ai_provider == "openai"
        else settings.ai_vision_model or settings.ai_text_model or "live"
    )
    input_hash = stable_json_hash(
        {
            "source_artifact_id": str(snapshot.asset_id),
            "source_version_id": str(snapshot.asset_version_id),
            "source_checksum_sha256": snapshot.checksum_sha256,
            "source_size_bytes": snapshot.size_bytes,
            "product_id": str(snapshot.product_id) if snapshot.product_id else None,
            "product_context_version": product_context_version,
            "product_context": product_context,
            "pipeline_version": MEDIA_PIPELINE_VERSION,
            "media_metadata": metadata,
            "scene_boundaries": scenes.model_dump(mode="json"),
            "selected_frames": [
                {
                    "timestamp_ms": timestamp_ms,
                    "storage_key": storage_key,
                    "content_sha256": _file_sha256(path),
                }
                for timestamp_ms, path, storage_key in frame_paths
            ],
            "audio_content_sha256": (_file_sha256(audio_path) if audio_path is not None else None),
            "transcript": bounded_transcript_payload(
                transcript,
                settings.openai_max_transcript_chars,
            ),
            "ocr": ocr.model_dump(mode="json"),
            "transcription_provider": (
                "openai" if settings.ai_provider == "openai" else settings.asr_provider
            ),
            "transcription_model": (
                settings.openai_transcription_model
                if settings.ai_provider == "openai"
                else settings.asr_model
            ),
            "ocr_provider": settings.ocr_provider,
            "ocr_model": settings.ocr_model,
            "max_frames": (
                settings.openai_max_frames_per_video if settings.ai_provider == "openai" else 30
            ),
            "max_frame_long_edge": settings.openai_max_frame_long_edge,
            "image_detail": settings.openai_image_detail,
            "max_transcript_chars": settings.openai_max_transcript_chars,
        }
    )
    return structured_request_hash(
        operation="media_observation",
        model=model,
        prompt_version=(
            MEDIA_OBSERVATION_PROMPT_VERSION
            if settings.ai_provider == "openai"
            else MEDIA_ANALYSIS_PROMPT_VERSION
        ),
        schema_version=MEDIA_OBSERVATION_SCHEMA_VERSION,
        input_hash=input_hash,
    )


def _media_analysis_claim_hash(
    snapshot: AssetVersionSnapshot,
    settings: Settings,
    *,
    product_context_version: int | None,
    product_context_hash: str | None = None,
) -> str:
    return stable_json_hash(
        {
            "workspace_id": str(snapshot.workspace_id),
            "source_artifact_id": str(snapshot.asset_id),
            "source_version_id": str(snapshot.asset_version_id),
            "source_checksum_sha256": snapshot.checksum_sha256,
            "product_context_version": product_context_version,
            "product_context_hash": product_context_hash,
            "pipeline_version": MEDIA_PIPELINE_VERSION,
            "provider": settings.ai_provider,
            "vision_model": (
                settings.resolve_openai_model("media_observation", vision=True)
                if settings.ai_provider == "openai"
                else settings.ai_vision_model or settings.ai_text_model
            ),
            "transcription_model": (
                settings.openai_transcription_model
                if settings.ai_provider == "openai"
                else settings.asr_model
            ),
            "max_frames": (
                settings.openai_max_frames_per_video if settings.ai_provider == "openai" else 30
            ),
            "max_frame_long_edge": settings.openai_max_frame_long_edge,
            "image_detail": settings.openai_image_detail,
            "max_transcript_chars": settings.openai_max_transcript_chars,
        }
    )


def _run_ffmpeg(args: list[str]) -> None:
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise AppError("FFMPEG_NOT_AVAILABLE", "ffmpeg is required for live media processing.")
    _run_subprocess(
        [ffmpeg_path, "-v", "error", "-y", *args],
        "FFMPEG_FAILED",
        "ffmpeg could not process the uploaded media.",
    )


def _run_subprocess(
    args: list[str], error_code: str, message: str
) -> subprocess.CompletedProcess[str]:
    try:
        # Executables are resolved locally and callers build fixed argument lists.
        return subprocess.run(  # noqa: S603  # nosec B603
            args,
            check=True,
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise AppError(error_code, message, details={"stderr": "subprocess timeout"}) from exc
    except subprocess.CalledProcessError as exc:
        raise AppError(error_code, message, details={"stderr": exc.stderr[-1000:]}) from exc


def _sample_frames(
    source_path: Path,
    frame_dir: Path,
    duration_ms: int,
    workspace_id: UUID,
    asset_id: UUID,
    asset_version_id: UUID,
    *,
    scenes: SceneContract,
    max_frames: int,
    max_long_edge: int,
    required_timestamps: tuple[int, ...] = (),
) -> list[tuple[int, Path, str]]:
    timestamps = _representative_timestamps(
        duration_ms=duration_ms,
        scenes=scenes,
        max_frames=max_frames,
        required_timestamps=required_timestamps,
    )
    frames: list[tuple[int, Path, str]] = []
    base_key = (
        f"workspaces/{workspace_id}/assets/{asset_id}/versions/{asset_version_id}/artifacts/frames"
    )
    for index, timestamp_ms in enumerate(timestamps):
        path = frame_dir / f"frame_{index:03d}.jpg"
        _run_ffmpeg(
            [
                "-ss",
                f"{timestamp_ms / 1000:.3f}",
                "-i",
                str(source_path),
                "-frames:v",
                "1",
                str(path),
            ]
        )
        _resize_frame(path, max_long_edge)
        frames.append((timestamp_ms, path, f"{base_key}/frame_{index:03d}.jpg"))
    return frames


def _representative_timestamps(
    *,
    duration_ms: int,
    scenes: SceneContract,
    max_frames: int,
    required_timestamps: tuple[int, ...] = (),
) -> list[int]:
    if duration_ms <= 0:
        return [0]
    required = {timestamp for timestamp in required_timestamps if 0 <= timestamp < duration_ms}
    capacity = max(max_frames, len(required), 1)
    selected = set(required)

    def add_candidates(values: list[int]) -> None:
        available = capacity - len(selected)
        if available <= 0:
            return
        candidates = [
            value
            for value in dict.fromkeys(values)
            if 0 <= value < duration_ms and value not in selected
        ]
        selected.update(_evenly_select(candidates, available))

    add_candidates([min(500, duration_ms - 1)])
    add_candidates(
        [
            min(duration_ms - 1, scene.start_ms + (scene.end_ms - scene.start_ms) // 2)
            for scene in scenes.scenes
            if scene.end_ms > scene.start_ms
        ]
    )
    add_candidates(
        [
            min(duration_ms - 1, round(duration_ms * index / (max_frames + 1)))
            for index in range(1, max_frames + 1)
        ]
    )
    return sorted(selected) or [0]


def _evenly_select(values: list[int], limit: int) -> list[int]:
    if limit <= 0:
        return []
    if len(values) <= limit:
        return values
    if limit == 1:
        return [values[len(values) // 2]]
    return [values[round(index * (len(values) - 1) / (limit - 1))] for index in range(limit)]


def _resize_frame(path: Path, max_long_edge: int) -> None:
    with Image.open(path) as source:
        source.load()
        if max(source.size) <= max_long_edge:
            return
        frame = source.convert("RGB")
    frame.thumbnail((max_long_edge, max_long_edge), Image.Resampling.LANCZOS)
    frame.save(path, format="JPEG", quality=88, optimize=True)


def _detect_scenes(source_path: Path, duration_ms: int) -> SceneContract:
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        return _scene_contract(duration_ms, ())
    try:
        result = _run_subprocess(
            [
                ffmpeg_path,
                "-hide_banner",
                "-v",
                "info",
                "-i",
                str(source_path),
                "-filter:v",
                "select='gt(scene,0.30)',showinfo",
                "-an",
                "-f",
                "null",
                "-",
            ],
            "SCENE_DETECTION_FAILED",
            "ffmpeg could not detect scene boundaries.",
        )
    except AppError:
        logger.warning("scene_detection_fallback", source_path=source_path.name)
        return _scene_contract(duration_ms, ())
    changes = tuple(
        round(float(match.group(1)) * 1000)
        for match in re.finditer(r"pts_time:(\d+(?:\.\d+)?)", result.stderr)
    )
    return _scene_contract(duration_ms, changes)


def _scene_contract(
    duration_ms: int,
    changes: tuple[int, ...],
) -> SceneContract:
    boundaries = [0]
    for value in sorted(set(changes)):
        if 250 <= value <= duration_ms - 250 and value - boundaries[-1] >= 250:
            boundaries.append(value)
    boundaries.append(duration_ms)
    scenes = [
        {"scene_index": index, "start_ms": start_ms, "end_ms": end_ms}
        for index, (start_ms, end_ms) in enumerate(zip(boundaries, boundaries[1:], strict=False))
        if end_ms > start_ms
    ]
    return SceneContract.model_validate({"scenes": scenes})


def _live_contract(
    metadata: dict[str, object],
    thumbnail_key: str,
    audio_key: str | None,
    frames: list[tuple[int, Path, str]],
    transcript: TranscriptContract,
    ocr: OcrContract,
    scenes: SceneContract,
    observations: MediaObservationBundleV1,
    settings: Settings,
) -> dict[str, Any]:
    return {
        "analysis_mode": "live",
        "provider": settings.ai_provider,
        "model_version": (
            settings.resolve_openai_model("media_observation", vision=True)
            if settings.ai_provider == "openai"
            else settings.ai_vision_model or settings.ai_text_model or "live"
        ),
        "metadata": metadata,
        "transcript": transcript.model_dump(mode="json"),
        "ocr": ocr.model_dump(mode="json"),
        "sampled_frames": {
            "frames": [
                {"timestamp_ms": timestamp_ms, "storage_key": storage_key}
                for timestamp_ms, _, storage_key in frames
            ]
        },
        "scene_boundaries": scenes.model_dump(mode="json"),
        "visual_observations": observations.model_dump(mode="json"),
        "thumbnail_storage_key": thumbnail_key,
        "audio_storage_key": audio_key,
    }


def _artifact_stage(artifact_type: str) -> str:
    return {
        "video_metadata": "probing_media",
        "thumbnail": "creating_thumbnail",
        "audio": "extracting_audio",
        "sampled_frames": "sampling_frames",
        "transcript": "transcribing_audio",
        "ocr": "extracting_ocr",
        "scene_boundaries": "detecting_scenes",
        "visual_observations": "extracting_visual_evidence",
        "artifact_manifest": "persisting_results",
    }.get(artifact_type, "persisting_results")


def _hash_json(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tracked_operation_metadata(
    capability: str,
    *,
    native_openai: bool,
) -> tuple[str, str | None, str | None, str, str | None]:
    if native_openai and capability == "visual_observations":
        return (
            "media_observation",
            MEDIA_OBSERVATION_PROMPT_NAME,
            MEDIA_OBSERVATION_PROMPT_VERSION,
            MEDIA_OBSERVATION_SCHEMA_VERSION,
            "responses",
        )
    if native_openai and capability == "audio_transcription":
        return (
            "audio_transcription",
            "audio_transcription",
            "audio_transcription_v1",
            "transcript_v1",
            "audio_transcriptions",
        )
    if native_openai:
        return (
            capability,
            capability,
            f"{capability}_v1",
            f"{capability}_v1",
            "responses",
        )
    return (
        capability,
        capability,
        MEDIA_ANALYSIS_PROMPT_VERSION,
        MEDIA_ANALYSIS_SCHEMA_VERSION,
        ("audio_transcriptions" if capability == "audio_transcription" else "chat_completions"),
    )


def _fail_tracked_model_run(
    session: Session,
    model_run: AiModelRunModel,
    error: AppError,
) -> None:
    http_status = error.details.get("http_status")
    provider_request_id = error.details.get("provider_request_id")
    repair_attempt_count = error.details.get("repair_attempt_count")
    SyncAiModelRunRepository(session).fail(
        model_run,
        error.code,
        error.message,
        http_status=http_status if isinstance(http_status, int) else None,
        safe_error_message=error.message,
        provider_request_id=(provider_request_id if isinstance(provider_request_id, str) else None),
        repair_attempt_count=(
            repair_attempt_count if isinstance(repair_attempt_count, int) else None
        ),
    )


def _provider_output_summary(result: object) -> dict[str, object]:
    if isinstance(result, TranscriptContract):
        return {
            "language": result.language,
            "segment_count": len(result.segments),
            "text_length": len(result.full_text),
        }
    if isinstance(result, OcrContract):
        return {"segment_count": len(result.segments)}
    if isinstance(result, MediaObservationBundleV1):
        return {
            "claim_count": len(result.claims),
            "cta_count": len(result.ctas),
            "demo_detected": result.demo.detected,
            "hook_count": len(result.hooks),
            "product_appearance_count": len(result.product_appearances),
        }
    return {}
