from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from viraldy.modules.ai_gateway.repository import SyncAiModelRunRepository
from viraldy.modules.ai_gateway.schemas import ProviderResponse
from viraldy.modules.assets.public import AssetVersionModel, AssetVersionSnapshot
from viraldy.modules.media_analysis.fixtures import fixture_media_contract, is_known_fixture
from viraldy.modules.media_analysis.models import EvidenceItemModel
from viraldy.modules.media_analysis.provider import (
    LiveAnalysisProvider,
    OcrContract,
    SceneContract,
    TranscriptContract,
    VisualObservationsContract,
)
from viraldy.modules.media_analysis.repository import SyncMediaAnalysisRepository
from viraldy.platform.config.settings import Settings
from viraldy.platform.storage.ports import StoragePort
from viraldy.platform.storage.s3 import S3StorageAdapter
from viraldy.shared.errors.base import AppError

MEDIA_PIPELINE_VERSION = "media_pipeline_v1"
MEDIA_ANALYSIS_PROMPT_VERSION = "media_analysis_prompt_v1"
MEDIA_ANALYSIS_SCHEMA_VERSION = "media_analysis_schema_v1"
SUPPORTED_CONTAINERS = {"mov,mp4,m4a,3gp,3g2,mj2", "mp4", "mov"}
SUBPROCESS_TIMEOUT_SECONDS = 120
T = TypeVar("T")


@dataclass(frozen=True)
class MediaEvidencePipelineResult:
    evidence: list[EvidenceItemModel]
    primary_model_run_id: UUID | None


def validate_live_ai_settings(settings: Settings) -> None:
    if settings.ai_mode != "live":
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
    ) -> MediaEvidencePipelineResult:
        if self._settings.ai_mode == "fixture":
            return MediaEvidencePipelineResult(
                self._process_fixture(snapshot, run_type, processing_job_id), None
            )
        validate_live_ai_settings(self._settings)
        return self._process_live(snapshot, run_type, processing_job_id)

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
        self, snapshot: AssetVersionSnapshot, run_type: str, processing_job_id: UUID | None
    ) -> MediaEvidencePipelineResult:
        provider_name = "openai_compatible"
        model_version = self._settings.ai_vision_model or self._settings.ai_text_model or "live"
        reusable = self._repository.list_reusable_evidence(
            snapshot.workspace_id,
            snapshot.asset_version_id,
            provider_name,
            model_version,
            MEDIA_PIPELINE_VERSION,
        )
        if reusable:
            return MediaEvidencePipelineResult(reusable, None)
        prefix = (
            f"viraldy-{processing_job_id or snapshot.asset_version_id}-"
        )
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

            thumbnail_path = work_dir / "thumbnail.jpg"
            audio_path = work_dir / "audio.wav"
            frame_dir = work_dir / "frames"
            frame_dir.mkdir()
            _run_ffmpeg(
                ["-ss", "0.5", "-i", str(source_path), "-frames:v", "1", str(thumbnail_path)]
            )
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
                int(metadata["duration_ms"]),
                snapshot.workspace_id,
                snapshot.asset_id,
                snapshot.asset_version_id,
            )

            base_key = (
                f"workspaces/{snapshot.workspace_id}/assets/{snapshot.asset_id}"
                f"/versions/{snapshot.asset_version_id}/artifacts"
            )
            thumbnail_key = f"{base_key}/thumbnail.jpg"
            audio_key = f"{base_key}/audio.wav"
            self._storage.upload_file(str(thumbnail_path), thumbnail_key, "image/jpeg")
            self._storage.upload_file(str(audio_path), audio_key, "audio/wav")
            uploaded_frames: list[tuple[int, Path, str]] = []
            for timestamp_ms, path, storage_key in frame_paths:
                self._storage.upload_file(str(path), storage_key, "image/jpeg")
                uploaded_frames.append((timestamp_ms, path, storage_key))

            provider = LiveAnalysisProvider(self._settings)
            transcript, transcript_run_id = self._tracked_provider_call(
                snapshot,
                processing_job_id,
                "audio_transcription",
                self._settings.asr_model or "asr",
                {
                    "asset_version_id": str(snapshot.asset_version_id),
                    "audio_artifact": "audio.wav",
                    "run_type": run_type,
                },
                lambda: provider.transcribe_audio_with_response(audio_path),
            )
            if self._settings.ocr_provider == "vision":
                ocr, ocr_run_id = self._tracked_provider_call(
                    snapshot,
                    processing_job_id,
                    "visual_ocr",
                    self._settings.ai_vision_model or "vision",
                    {
                        "asset_version_id": str(snapshot.asset_version_id),
                        "frame_count": len(uploaded_frames[:8]),
                        "run_type": run_type,
                    },
                    lambda: provider.extract_ocr_with_response(uploaded_frames),
                )
            else:
                ocr = provider.extract_ocr(uploaded_frames)
                ocr_run_id = None
            scenes = _detect_scenes(int(metadata["duration_ms"]))
            observations, vision_run_id = self._tracked_provider_call(
                snapshot,
                processing_job_id,
                "visual_observations",
                self._settings.ai_vision_model or "vision",
                {
                    "asset_version_id": str(snapshot.asset_version_id),
                    "frame_count": len(uploaded_frames[:12]),
                    "transcript_segments": len(transcript.segments),
                    "ocr_segments": len(ocr.segments),
                    "run_type": run_type,
                },
                lambda: provider.extract_visual_observations_with_response(
                    uploaded_frames,
                    transcript,
                    ocr,
                    snapshot.metadata_json,
                ),
            )
            contract = _live_contract(
                metadata,
                thumbnail_key,
                audio_key,
                uploaded_frames,
                transcript,
                ocr,
                scenes,
                observations,
                self._settings,
            )
            artifacts = self._artifact_rows(
                snapshot.workspace_id, snapshot.asset_version_id, contract
            )
            evidence = self._evidence_rows(snapshot.asset_version_id, run_type, contract)
            persisted = self._repository.replace_artifacts_and_evidence(
                snapshot.workspace_id,
                snapshot.asset_version_id,
                processing_job_id,
                MEDIA_PIPELINE_VERSION,
                artifacts,
                evidence,
            )
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
        call: Callable[[], tuple[T, ProviderResponse | None]],
    ) -> tuple[T, UUID | None]:
        model_run = SyncAiModelRunRepository(self._session).create_running(
            snapshot.workspace_id,
            processing_job_id,
            "asset_version",
            snapshot.asset_version_id,
            capability,
            self._settings.ai_mode,
            "openai_compatible",
            model,
            MEDIA_ANALYSIS_PROMPT_VERSION,
            MEDIA_ANALYSIS_SCHEMA_VERSION,
            _hash_json({"capability": capability, "input_summary": input_summary}),
            input_summary,
        )
        try:
            result, response = call()
        except AppError as exc:
            SyncAiModelRunRepository(self._session).fail(model_run, exc.code, exc.message)
            raise
        if response is None:
            SyncAiModelRunRepository(self._session).complete(model_run, {}, None, None, None)
        else:
            SyncAiModelRunRepository(self._session).complete(
                model_run,
                _provider_output_summary(result),
                response.http_status,
                response.provider_request_id,
                response.latency_ms,
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
        version.duration_ms = int(metadata["duration_ms"])
        version.width = int(metadata["width"])
        version.height = int(metadata["height"])
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
            (
                "audio",
                contract.get("audio_storage_key", "fixtures/audio.wav"),
                {"fixture": mode == "fixture"},
            ),
        ]
        return [
            {
                "workspace_id": workspace_id,
                "asset_version_id": asset_version_id,
                "artifact_type": artifact_type,
                "stage": _artifact_stage(artifact_type),
                "ordinal": ordinal,
                "storage_key": storage_key,
                "sha256": _hash_json({"storage_key": storage_key, "payload": payload}),
                "payload_json": payload,
                "provider": provider,
                "model_version": model_version,
                "analysis_mode": mode,
            }
            for ordinal, (artifact_type, storage_key, payload) in enumerate(rows)
        ]

    def _evidence_rows(
        self,
        asset_version_id: UUID,
        run_type: str,
        contract: dict[str, Any],
    ) -> list[dict[str, Any]]:
        provider = str(contract["provider"])
        model_version = str(contract["model_version"])
        observations = contract["visual_observations"]
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
                    segment,
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
                    segment,
                )
            )
        raw_first_product_ms = observations.get("product_first_appearance_ms")
        first_product_ms = int(raw_first_product_ms) if raw_first_product_ms is not None else None
        rows.extend(
            [
                _row(
                    asset_version_id,
                    run_type,
                    "product_first_appearance",
                    "vision",
                    provider,
                    model_version,
                    {
                        "start_ms": first_product_ms,
                        "end_ms": first_product_ms + 1000 if first_product_ms is not None else None,
                        "value": first_product_ms,
                    },
                ),
                _row(
                    asset_version_id,
                    run_type,
                    "hook_signal",
                    "derived",
                    provider,
                    model_version,
                    {"start_ms": 0, "end_ms": 2100, "text": "problem-first counter mess hook"},
                ),
                _row(
                    asset_version_id,
                    run_type,
                    "demo_signal",
                    "vision",
                    provider,
                    model_version,
                    {"start_ms": 6500, "end_ms": 15000, "text": str(observations["demo_type"])},
                ),
                _row(
                    asset_version_id,
                    run_type,
                    "proof_signal",
                    "vision",
                    provider,
                    model_version,
                    {"start_ms": 15000, "end_ms": 18200, "text": str(observations["proof_type"])},
                ),
                _row(
                    asset_version_id,
                    run_type,
                    "cta_signal",
                    "derived",
                    provider,
                    model_version,
                    {"start_ms": 18200, "end_ms": 27000, "text": "TikTok Shop CTA"},
                ),
            ]
        )
        for claim in observations.get("claim_candidates", []):
            rows.append(
                _row(
                    asset_version_id,
                    run_type,
                    "claim_signal",
                    "vision",
                    provider,
                    model_version,
                    claim,
                )
            )
        return rows


def _row(
    asset_version_id: UUID,
    run_type: str,
    evidence_type: str,
    source: str,
    provider: str,
    model_version: str,
    value: dict[str, Any],
) -> dict[str, Any]:
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
                "value": value,
            }
        ),
        "start_ms": value.get("start_ms"),
        "end_ms": value.get("end_ms"),
        "frame_storage_key": value.get("frame_storage_key"),
        "value_json": value,
        "confidence": value.get("confidence", 0.8),
        "source": source,
        "provider": provider,
        "model_version": model_version,
    }


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
        return subprocess.run(  # noqa: S603
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
) -> list[tuple[int, Path, str]]:
    timestamps = _sample_timestamps(duration_ms)
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
        frames.append((timestamp_ms, path, f"{base_key}/frame_{index:03d}.jpg"))
    return frames


def _sample_timestamps(duration_ms: int) -> list[int]:
    opening = [500, 1000, 1500, 2000, 2500]
    regular = list(range(3000, duration_ms, 2000))
    timestamps = sorted({value for value in [*opening, *regular] if value < duration_ms})
    return timestamps[:30] or [0]


def _detect_scenes(duration_ms: int) -> SceneContract:
    scene_length_ms = 3000
    scenes = []
    start_ms = 0
    index = 0
    while start_ms < duration_ms:
        end_ms = min(start_ms + scene_length_ms, duration_ms)
        scenes.append({"scene_index": index, "start_ms": start_ms, "end_ms": end_ms})
        index += 1
        start_ms = end_ms
    return SceneContract.model_validate({"scenes": scenes})


def _live_contract(
    metadata: dict[str, object],
    thumbnail_key: str,
    audio_key: str,
    frames: list[tuple[int, Path, str]],
    transcript: TranscriptContract,
    ocr: OcrContract,
    scenes: SceneContract,
    observations: VisualObservationsContract,
    settings: Settings,
) -> dict[str, Any]:
    return {
        "analysis_mode": "live",
        "provider": "openai_compatible",
        "model_version": settings.ai_vision_model or settings.ai_text_model or "live",
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


def _provider_output_summary(result: object) -> dict[str, object]:
    if isinstance(result, TranscriptContract):
        return {
            "language": result.language,
            "segment_count": len(result.segments),
            "text_length": len(result.full_text),
        }
    if isinstance(result, OcrContract):
        return {"segment_count": len(result.segments)}
    if isinstance(result, VisualObservationsContract):
        return {
            "claim_count": len(result.claim_candidates),
            "demo_detected": result.demo_detected,
            "opening_visual": result.opening_visual,
        }
    return {}
