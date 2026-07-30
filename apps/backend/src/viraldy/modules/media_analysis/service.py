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
from viraldy.modules.creative_domain.schema_versions import EVIDENCE_SCHEMA_VERSION
from viraldy.modules.media_analysis.contracts import MediaObservationBundleV1, TimeRangeV1
from viraldy.modules.media_analysis.fixtures import fixture_media_contract, is_known_fixture
from viraldy.modules.media_analysis.models import EvidenceItemModel
from viraldy.modules.media_analysis.provider import (
    LiveAnalysisProvider,
    OcrContract,
    SceneContract,
    TranscriptContract,
)
from viraldy.modules.media_analysis.repository import SyncMediaAnalysisRepository
from viraldy.modules.products.public import SyncProductQueries
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
            has_audio = int(metadata.get("audio_stream_count") or 0) > 0

            thumbnail_path = work_dir / "thumbnail.jpg"
            audio_path = work_dir / "audio.wav"
            frame_dir = work_dir / "frames"
            frame_dir.mkdir()
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
            audio_key = f"{base_key}/audio.wav" if has_audio else None
            self._storage.upload_file(str(thumbnail_path), thumbnail_key, "image/jpeg")
            if has_audio and audio_key is not None:
                self._storage.upload_file(str(audio_path), audio_key, "audio/wav")
            uploaded_frames: list[tuple[int, Path, str]] = []
            for timestamp_ms, path, storage_key in frame_paths:
                self._storage.upload_file(str(path), storage_key, "image/jpeg")
                uploaded_frames.append((timestamp_ms, path, storage_key))

            provider = LiveAnalysisProvider(self._settings)
            if has_audio:
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
            else:
                transcript = TranscriptContract(segments=[], full_text="")
                transcript_run_id = None
            if self._settings.ocr_provider == "vision":
                product_context = self._product_context_json(snapshot)
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
                    lambda: provider.extract_ocr_with_response(uploaded_frames, product_context),
                )
            else:
                ocr = provider.extract_ocr(uploaded_frames, self._product_context_json(snapshot))
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
                    self._product_context_json(snapshot),
                    int(metadata["duration_ms"]),
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
        ]
        default_audio_key = "fixtures/audio.wav" if mode == "fixture" else None
        audio_key = contract.get("audio_storage_key", default_audio_key)
        if audio_key is not None:
            rows.append(("audio", audio_key, {"fixture": mode == "fixture"}))
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

    def _product_context_json(self, snapshot: AssetVersionSnapshot) -> dict[str, object] | None:
        if snapshot.product_id is None:
            return None
        product_snapshot = SyncProductQueries(self._session).get_product_context_snapshot(
            snapshot.workspace_id, snapshot.product_id
        )
        if product_snapshot is None:
            return None
        return product_snapshot.product_context.model_dump(mode="json")


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
        "frame_storage_key": _frame_storage_key(value),
        "value_json": value,
        "confidence": value.get("confidence"),
        "source": source,
        "provider": provider,
        "model_version": model_version,
        "evidence_schema_version": value.get("schema_version", EVIDENCE_SCHEMA_VERSION),
        "observation_id": value.get("observation_id"),
    }


def _time_fields(time_range: TimeRangeV1) -> dict[str, int]:
    return {"start_ms": time_range.start_ms, "end_ms": time_range.end_ms}


def _optional_time_fields(time_range: TimeRangeV1 | None) -> dict[str, int | None]:
    if time_range is None:
        return {"start_ms": None, "end_ms": None}
    return _time_fields(time_range)


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
    if isinstance(result, MediaObservationBundleV1):
        return {
            "claim_count": len(result.claims),
            "cta_count": len(result.ctas),
            "demo_detected": result.demo.detected,
            "hook_count": len(result.hooks),
            "product_appearance_count": len(result.product_appearances),
        }
    return {}
