from __future__ import annotations

import shutil
import subprocess
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from PIL import Image
from pydantic import ValidationError

import viraldy.modules.media_analysis.service as media_service_module
from viraldy.modules.ai_gateway.providers.base import (
    AudioTranscriptionResult,
    ProviderEndpointFamily,
)
from viraldy.modules.ai_gateway.usage import ProviderUsage
from viraldy.modules.assets.public import AssetVersionSnapshot
from viraldy.modules.media_analysis.contracts import MediaObservationBundleV1
from viraldy.modules.media_analysis.provider import (
    OcrContract,
    SceneContract,
    TranscriptContract,
    _native_media_output_validator,
)
from viraldy.modules.media_analysis.service import (
    MEDIA_PIPELINE_VERSION,
    SyncMediaEvidencePipeline,
    _cleanup_uploaded_objects_on_failure,
    _detect_scenes,
    _live_contract,
    _media_analysis_request_hash,
    _representative_timestamps,
    _resize_frame,
    _sample_frames,
    validate_live_ai_settings,
)
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError


def test_media_observation_rejects_timestamps_outside_duration() -> None:
    payload = _minimal_bundle()
    payload["ctas"] = [
        {
            "observation_id": "cta_001",
            "time_range": {"start_ms": 900, "end_ms": 1400},
            "modality": "spoken",
            "cta_type": "shop_now",
            "text": "Shop now",
            "product_tag_visible": True,
            "confidence": 0.8,
            "frame_storage_keys": [],
        }
    ]

    with pytest.raises(ValidationError):
        MediaObservationBundleV1.model_validate(payload)


def test_media_observation_normalizes_first_appearance_summary() -> None:
    payload = _minimal_bundle()
    payload["product_appearances"] = [
        {
            "observation_id": "product_late",
            "time_range": {"start_ms": 700, "end_ms": 900},
            "visibility": "clear",
            "shot_type": "close_up",
            "usage_visible": False,
            "product_match_confidence": 0.8,
            "confidence": 0.8,
            "frame_storage_keys": [],
        },
        {
            "observation_id": "product_early",
            "time_range": {"start_ms": 300, "end_ms": 500},
            "visibility": "partial",
            "shot_type": "medium",
            "usage_visible": True,
            "product_match_confidence": 0.7,
            "confidence": 0.7,
            "frame_storage_keys": [],
        },
    ]
    payload["product_visibility"] = {
        "first_appearance_ms": 700,
        "total_visible_ms": 400,
        "screen_time_ratio": 0.4,
        "clear_close_up_present": True,
        "usage_present": True,
    }

    bundle = MediaObservationBundleV1.model_validate(payload)

    assert bundle.product_visibility.first_appearance_ms == 300


def test_native_openai_live_settings_do_not_require_legacy_ai_fields() -> None:
    settings = Settings(
        ai_mode="live",
        ai_provider="openai",
        openai_api_key="test-key",
    )

    validate_live_ai_settings(settings)


def test_openai_compatible_live_settings_still_require_legacy_ai_fields() -> None:
    settings = Settings(
        ai_mode="live",
        ai_provider="openai_compatible",
    )

    with pytest.raises(AppError, match="AI_BASE_URL"):
        validate_live_ai_settings(settings)


def test_live_contract_records_native_openai_provenance() -> None:
    settings = Settings(
        ai_mode="live",
        ai_provider="openai",
        openai_api_key="test-key",
        openai_vision_model="gpt-test",
    )

    contract = _live_contract(
        {"duration_ms": 1000},
        "thumbnail.jpg",
        None,
        [],
        TranscriptContract(),
        OcrContract(),
        SceneContract(scenes=[{"scene_index": 0, "start_ms": 0, "end_ms": 1000}]),
        MediaObservationBundleV1.model_validate(_minimal_bundle()),
        settings,
    )

    assert contract["provider"] == "openai"
    assert contract["model_version"] == "gpt-test"


def test_media_observation_rejects_demo_steps_when_demo_absent() -> None:
    payload = _minimal_bundle()
    payload["demo"]["steps"] = [
        {
            "observation_id": "demo_step_001",
            "step_index": 1,
            "time_range": {"start_ms": 100, "end_ms": 500},
            "action": "fake step",
            "product_visible": True,
            "mechanism_visible": True,
            "result_visible": False,
            "confidence": 0.7,
            "frame_storage_keys": [],
        }
    ]

    with pytest.raises(ValidationError):
        MediaObservationBundleV1.model_validate(payload)


def test_media_observation_preserves_timed_on_screen_text_as_evidence() -> None:
    payload = _minimal_bundle()
    payload["on_screen_text"] = [
        {
            "observation_id": "personalization_001",
            "time_range": {"start_ms": 200, "end_ms": 800},
            "text": "Pet name: Milo",
            "text_role": "personalization",
            "confidence": 0.94,
            "frame_storage_keys": ["workspace/frame-001.jpg"],
        }
    ]
    contract = {
        "provider": "openai",
        "model_version": "gpt-test",
        "transcript": {"segments": []},
        "ocr": {"segments": []},
        "visual_observations": payload,
    }
    pipeline = SyncMediaEvidencePipeline.__new__(SyncMediaEvidencePipeline)

    bundle = MediaObservationBundleV1.model_validate(payload)
    rows = pipeline._evidence_rows(uuid4(), "unit_test", contract)  # noqa: SLF001
    text_rows = [row for row in rows if row["evidence_type"] == "on_screen_text"]

    assert bundle.on_screen_text[0].text == "Pet name: Milo"
    assert len(text_rows) == 1
    assert text_rows[0]["start_ms"] == 200
    assert text_rows[0]["end_ms"] == 800
    assert text_rows[0]["value_json"]["text"] == "Pet name: Milo"
    assert text_rows[0]["value_json"]["text_role"] == "personalization"


def test_native_media_validator_rejects_changed_asset_duration() -> None:
    bundle = MediaObservationBundleV1.model_validate(_minimal_bundle())
    validator = _native_media_output_validator(2000, set())

    with pytest.raises(ValueError, match="duration changed"):
        validator(bundle)


def test_native_media_validator_rejects_unknown_frame_reference() -> None:
    payload = _minimal_bundle()
    payload["hooks"] = [
        {
            "observation_id": "hook_001",
            "time_range": {"start_ms": 0, "end_ms": 500},
            "hook_type": "problem_first",
            "visual_description": "A wrinkled shirt is shown.",
            "clarity": "clear",
            "confidence": 0.8,
            "frame_storage_keys": ["private/unknown-frame.jpg"],
        }
    ]
    bundle = MediaObservationBundleV1.model_validate(payload)
    validator = _native_media_output_validator(1000, {"private/frame-001.jpg"})

    with pytest.raises(ValueError, match="outside the request"):
        validator(bundle)


def test_evidence_rows_do_not_fabricate_absent_cta_demo_or_proof() -> None:
    contract = {
        "provider": "fixture",
        "model_version": "fixture_media_v1",
        "transcript": {"segments": []},
        "ocr": {"segments": []},
        "visual_observations": _minimal_bundle(),
    }
    pipeline = SyncMediaEvidencePipeline.__new__(SyncMediaEvidencePipeline)

    rows = pipeline._evidence_rows(uuid4(), "unit_test", contract)  # noqa: SLF001
    evidence_types = {row["evidence_type"] for row in rows}

    assert "cta_signal" not in evidence_types
    assert "demo_summary" not in evidence_types
    assert "demo_step" not in evidence_types
    assert "proof_signal" not in evidence_types
    assert "product_visibility_summary" in evidence_types


def test_probe_no_audio_mp4_reports_zero_audio_streams(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.skip("ffmpeg/ffprobe are required for no-audio media regression")
    video_path = tmp_path / "silent.mp4"
    subprocess.run(  # noqa: S603
        [
            ffmpeg,
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=320x568:d=1",
            "-an",
            "-pix_fmt",
            "yuv420p",
            str(video_path),
        ],
        check=True,
    )
    pipeline = SyncMediaEvidencePipeline.__new__(SyncMediaEvidencePipeline)
    pipeline._settings = SimpleNamespace(max_media_duration_seconds=60)  # noqa: SLF001

    metadata = pipeline.probe_local_file(video_path)

    assert metadata["audio_stream_count"] == 0
    assert metadata["audio_codec"] is None


def test_representative_timestamps_cover_scenes_and_required_evidence() -> None:
    scenes = SceneContract.model_validate(
        {
            "scenes": [
                {"scene_index": 0, "start_ms": 0, "end_ms": 2000},
                {"scene_index": 1, "start_ms": 2000, "end_ms": 8000},
                {"scene_index": 2, "start_ms": 8000, "end_ms": 12000},
            ]
        }
    )

    timestamps = _representative_timestamps(
        duration_ms=12000,
        scenes=scenes,
        max_frames=5,
        required_timestamps=(7500,),
    )

    assert 500 in timestamps
    assert 1000 in timestamps
    assert 5000 in timestamps
    assert 10000 in timestamps
    assert 7500 in timestamps
    assert len(timestamps) == 5


def test_media_cache_identity_invalidates_exact_prepared_inputs(tmp_path: Path) -> None:
    snapshot = AssetVersionSnapshot(
        asset_id=uuid4(),
        asset_version_id=uuid4(),
        workspace_id=uuid4(),
        product_id=uuid4(),
        storage_key="private/source.mp4",
        original_filename="source.mp4",
        declared_mime_type="video/mp4",
        detected_mime_type="video/mp4",
        size_bytes=1234,
        checksum_sha256="a" * 64,
        metadata_json={},
    )
    settings = Settings(
        _env_file=None,
        ai_mode="live",
        ai_provider="openai",
        openai_api_key="test-openai-key",
        openai_vision_model="gpt-media-a",
    )
    frame_path = tmp_path / "frame.jpg"
    audio_path = tmp_path / "audio.wav"
    frame_path.write_bytes(b"frame-a")
    audio_path.write_bytes(b"audio-a")
    scenes = SceneContract.model_validate(
        {"scenes": [{"scene_index": 0, "start_ms": 0, "end_ms": 1000}]}
    )
    common = {
        "product_context": {"product_id": str(snapshot.product_id), "title": "Steamer"},
        "metadata": {"duration_ms": 1000, "width": 720, "height": 1280},
        "scenes": scenes,
        "frame_paths": [(500, frame_path, "private/frame-000.jpg")],
        "audio_path": audio_path,
        "transcript": TranscriptContract(full_text="Observed product demo."),
        "ocr": OcrContract(segments=[]),
    }

    original = _media_analysis_request_hash(
        snapshot,
        settings,
        product_context_version=1,
        **common,
    )
    changed_source = _media_analysis_request_hash(
        replace(snapshot, asset_version_id=uuid4()),
        settings,
        product_context_version=1,
        **common,
    )
    changed_product = _media_analysis_request_hash(
        snapshot,
        settings,
        product_context_version=2,
        **common,
    )
    changed_model = _media_analysis_request_hash(
        snapshot,
        settings.model_copy(update={"openai_vision_model": "gpt-media-b"}),
        product_context_version=1,
        **common,
    )
    changed_scene = _media_analysis_request_hash(
        snapshot,
        settings,
        product_context_version=1,
        **{
            **common,
            "scenes": SceneContract.model_validate(
                {"scenes": [{"scene_index": 0, "start_ms": 0, "end_ms": 900}]}
            ),
        },
    )
    frame_path.write_bytes(b"frame-b")
    changed_frame = _media_analysis_request_hash(
        snapshot,
        settings,
        product_context_version=1,
        **common,
    )
    changed_transcript = _media_analysis_request_hash(
        snapshot,
        settings,
        product_context_version=1,
        **{
            **common,
            "transcript": TranscriptContract(full_text="Changed observed product demo."),
        },
    )
    bounded_settings = settings.model_copy(update={"openai_max_transcript_chars": 10})
    bounded_original = _media_analysis_request_hash(
        snapshot,
        bounded_settings,
        product_context_version=1,
        **{
            **common,
            "transcript": TranscriptContract(full_text="0123456789 alpha"),
        },
    )
    bounded_change_after_cutoff = _media_analysis_request_hash(
        snapshot,
        bounded_settings,
        product_context_version=1,
        **{
            **common,
            "transcript": TranscriptContract(full_text="0123456789 beta"),
        },
    )

    assert MEDIA_PIPELINE_VERSION == "media_pipeline_v2_scene_cost_controls"
    assert (
        len(
            {
                original,
                changed_source,
                changed_product,
                changed_model,
                changed_scene,
                changed_frame,
                changed_transcript,
            }
        )
        == 7
    )
    assert bounded_original == bounded_change_after_cutoff


def test_representative_timestamps_never_drop_required_evidence() -> None:
    scenes = SceneContract.model_validate(
        {"scenes": [{"scene_index": 0, "start_ms": 0, "end_ms": 10000}]}
    )
    required = (1000, 2000, 3000, 4000)

    timestamps = _representative_timestamps(
        duration_ms=10000,
        scenes=scenes,
        max_frames=2,
        required_timestamps=required,
    )

    assert set(required) <= set(timestamps)


def test_sample_frames_forwards_required_evidence_timestamps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(media_service_module, "_run_ffmpeg", lambda _args: None)
    monkeypatch.setattr(
        media_service_module,
        "_resize_frame",
        lambda _path, _max_long_edge: None,
    )
    frame_dir = tmp_path / "frames"
    frame_dir.mkdir()
    required = (1000, 2000, 3000)

    frames = _sample_frames(
        tmp_path / "source.mp4",
        frame_dir,
        duration_ms=10000,
        workspace_id=uuid4(),
        asset_id=uuid4(),
        asset_version_id=uuid4(),
        scenes=SceneContract.model_validate(
            {"scenes": [{"scene_index": 0, "start_ms": 0, "end_ms": 10000}]}
        ),
        max_frames=2,
        max_long_edge=1280,
        required_timestamps=required,
    )

    assert set(required) <= {timestamp_ms for timestamp_ms, _, _ in frames}


def test_tracked_native_media_run_persists_exact_provider_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = SimpleNamespace(id=uuid4())
    recorded: dict[str, object] = {}

    class RecordingRepository:
        def create_running(self, **kwargs: object) -> object:
            recorded["created"] = kwargs
            return run

        def update_identity(
            self,
            model_run: object,
            *,
            input_hash: str,
            request_hash: str,
        ) -> object:
            recorded["identity"] = (model_run, input_hash, request_hash)
            return model_run

        def complete(self, model_run: object, *args: object, **kwargs: object) -> object:
            recorded["completed"] = model_run
            return model_run

    repository = RecordingRepository()
    monkeypatch.setattr(
        media_service_module,
        "SyncAiModelRunRepository",
        lambda _session: repository,
    )
    pipeline = SyncMediaEvidencePipeline.__new__(SyncMediaEvidencePipeline)
    pipeline._session = object()  # type: ignore[assignment]  # noqa: SLF001
    pipeline._settings = Settings(  # noqa: SLF001
        _env_file=None,
        ai_mode="live",
        ai_provider="openai",
        openai_api_key="test-openai-key",
    )
    snapshot = AssetVersionSnapshot(
        asset_id=uuid4(),
        asset_version_id=uuid4(),
        workspace_id=uuid4(),
        product_id=None,
        storage_key="private/source.mp4",
        original_filename="source.mp4",
        declared_mime_type="video/mp4",
        detected_mime_type="video/mp4",
        size_bytes=1234,
        checksum_sha256="a" * 64,
        metadata_json={},
    )
    response = AudioTranscriptionResult(
        provider="openai",
        endpoint_family=ProviderEndpointFamily.AUDIO_TRANSCRIPTIONS,
        model="whisper-1",
        provider_request_id="provider-request",
        http_status=200,
        latency_ms=10,
        usage=ProviderUsage(input_tokens=10, output_tokens=2, total_tokens=12),
        language="en",
        duration_ms=1000,
        full_text="Grounded.",
        segments=[],
        input_hash="b" * 64,
        request_hash="c" * 64,
    )

    result, run_id = pipeline._tracked_provider_call(  # noqa: SLF001
        snapshot,
        None,
        "audio_transcription",
        "whisper-1",
        {"asset_version_id": str(snapshot.asset_version_id)},
        lambda: (TranscriptContract(full_text="Grounded."), response),
    )

    assert result.full_text == "Grounded."
    assert run_id == run.id
    assert recorded["identity"] == (run, "b" * 64, "c" * 64)
    assert recorded["completed"] is run


def test_failed_native_media_run_persists_exact_provider_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = SimpleNamespace(id=uuid4())
    recorded: dict[str, object] = {}

    class RecordingRepository:
        def create_running(self, **kwargs: object) -> object:
            return run

        def update_identity(
            self,
            model_run: object,
            *,
            input_hash: str,
            request_hash: str,
        ) -> object:
            recorded["identity"] = (model_run, input_hash, request_hash)
            return model_run

        def fail(
            self,
            model_run: object,
            code: str,
            message: str,
            **kwargs: object,
        ) -> object:
            recorded["failed"] = (model_run, code, message, kwargs)
            return model_run

    repository = RecordingRepository()
    monkeypatch.setattr(
        media_service_module,
        "SyncAiModelRunRepository",
        lambda _session: repository,
    )
    pipeline = SyncMediaEvidencePipeline.__new__(SyncMediaEvidencePipeline)
    pipeline._session = object()  # type: ignore[assignment]  # noqa: SLF001
    pipeline._settings = Settings(  # noqa: SLF001
        _env_file=None,
        ai_mode="live",
        ai_provider="openai",
        openai_api_key="test-openai-key",
    )
    snapshot = AssetVersionSnapshot(
        asset_id=uuid4(),
        asset_version_id=uuid4(),
        workspace_id=uuid4(),
        product_id=None,
        storage_key="private/source.mp4",
        original_filename="source.mp4",
        declared_mime_type="video/mp4",
        detected_mime_type="video/mp4",
        size_bytes=1234,
        checksum_sha256="a" * 64,
        metadata_json={},
    )

    def fail() -> tuple[TranscriptContract, None]:
        raise AppError(
            "OPENAI_TIMEOUT",
            "OpenAI timed out.",
            details={
                "input_hash": "d" * 64,
                "request_hash": "e" * 64,
            },
        )

    with pytest.raises(AppError, match="OpenAI timed out"):
        pipeline._tracked_provider_call(  # noqa: SLF001
            snapshot,
            None,
            "audio_transcription",
            "whisper-1",
            {"asset_version_id": str(snapshot.asset_version_id)},
            fail,
        )

    assert recorded["identity"] == (run, "d" * 64, "e" * 64)
    assert recorded["failed"][0] is run  # type: ignore[index]


def test_resize_frame_bounds_long_edge_without_upscaling(tmp_path: Path) -> None:
    large = tmp_path / "large.jpg"
    small = tmp_path / "small.jpg"
    Image.new("RGB", (2400, 1200), "white").save(large)
    Image.new("RGB", (320, 568), "white").save(small)

    _resize_frame(large, 1280)
    _resize_frame(small, 1280)

    with Image.open(large) as image:
        assert image.size == (1280, 640)
    with Image.open(small) as image:
        assert image.size == (320, 568)


def test_scene_detection_finds_visual_cut(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("ffmpeg is required for scene-detection regression")
    video_path = tmp_path / "scene-cut.mp4"
    subprocess.run(  # noqa: S603
        [
            ffmpeg,
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=320x568:d=1:r=24",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=320x568:d=1:r=24",
            "-filter_complex",
            "[0:v][1:v]concat=n=2:v=1:a=0",
            "-pix_fmt",
            "yuv420p",
            str(video_path),
        ],
        check=True,
    )

    scenes = _detect_scenes(video_path, 2000)

    assert len(scenes.scenes) >= 2
    assert any(700 <= scene.end_ms <= 1300 for scene in scenes.scenes[:-1])


def test_live_no_audio_contract_does_not_create_fake_audio_artifact() -> None:
    contract = {
        "analysis_mode": "live",
        "provider": "openai_compatible",
        "model_version": "live",
        "metadata": {"duration_ms": 1000, "checksum_sha256": "x"},
        "transcript": {"segments": [], "full_text": "", "language": "en"},
        "ocr": {"segments": []},
        "sampled_frames": {"frames": []},
        "scene_boundaries": {"scenes": []},
        "visual_observations": _minimal_bundle(),
        "thumbnail_storage_key": "thumb.jpg",
        "audio_storage_key": None,
    }
    pipeline = SyncMediaEvidencePipeline.__new__(SyncMediaEvidencePipeline)

    rows = pipeline._artifact_rows(uuid4(), uuid4(), contract)  # noqa: SLF001

    assert "audio" not in {row["artifact_type"] for row in rows}


def test_uploaded_artifact_guard_cleans_objects_only_after_failure() -> None:
    storage = _RecordingDeleteStorage()

    with pytest.raises(RuntimeError, match="provider failed"):
        with _cleanup_uploaded_objects_on_failure(storage) as uploaded_keys:
            uploaded_keys.extend(["frame-001.jpg", "audio.wav"])
            raise RuntimeError("provider failed")

    assert storage.deleted_keys == ["audio.wav", "frame-001.jpg"]

    with _cleanup_uploaded_objects_on_failure(storage) as uploaded_keys:
        uploaded_keys.append("successful-thumbnail.jpg")

    assert storage.deleted_keys == ["audio.wav", "frame-001.jpg"]


def test_evidence_rows_preserve_modal_text_offer_urgency_and_editing_ranges() -> None:
    bundle = _minimal_bundle()
    bundle["ctas"] = [
        {
            "observation_id": "cta_001",
            "time_range": {"start_ms": 500, "end_ms": 800},
            "modality": "mixed",
            "cta_type": "product_tag",
            "text": "Check the tag",
            "spoken_text": "Check the tag",
            "overlay_text": "Product tag",
            "product_tag_visible": True,
            "confidence": 0.8,
            "frame_storage_keys": [],
        }
    ]
    bundle["offers"] = [
        {
            "observation_id": "offer_001",
            "time_range": {"start_ms": 200, "end_ms": 400},
            "offer_type": "limited_time",
            "text": "Today only",
            "price_text": None,
            "discount_text": "20% off",
            "urgency_present": True,
            "confidence": 0.8,
            "frame_storage_keys": [],
        }
    ]
    bundle["editing"] = {
        **bundle["editing"],  # type: ignore[arg-type]
        "pattern_interrupts": [{"start_ms": 0, "end_ms": 100}],
        "dead_air_ranges": [{"start_ms": 900, "end_ms": 950}],
    }
    contract = {
        "provider": "fixture",
        "model_version": "fixture_media_v1",
        "transcript": {"segments": []},
        "ocr": {"segments": []},
        "visual_observations": bundle,
    }
    pipeline = SyncMediaEvidencePipeline.__new__(SyncMediaEvidencePipeline)

    rows = pipeline._evidence_rows(uuid4(), "unit_test", contract)  # noqa: SLF001
    by_type = {row["evidence_type"]: row["value_json"] for row in rows}

    assert by_type["cta_signal"]["spoken_text"] == "Check the tag"
    assert by_type["cta_signal"]["overlay_text"] == "Product tag"
    assert by_type["offer_signal"]["urgency_present"] is True
    assert by_type["offer_signal"]["discount_text"] == "20% off"
    assert by_type["editing_signal"]["pattern_interrupts"] == [{"start_ms": 0, "end_ms": 100}]
    assert by_type["editing_signal"]["dead_air_ranges"] == [{"start_ms": 900, "end_ms": 950}]


class _RecordingDeleteStorage:
    def __init__(self) -> None:
        self.deleted_keys: list[str] = []

    def delete_object(self, key: str) -> None:
        self.deleted_keys.append(key)


def _minimal_bundle() -> dict[str, object]:
    return {
        "schema_version": "media_observation_v1",
        "duration_ms": 1000,
        "hooks": [],
        "product_appearances": [],
        "product_visibility": {
            "first_appearance_ms": None,
            "total_visible_ms": None,
            "screen_time_ratio": None,
            "clear_close_up_present": False,
            "usage_present": False,
        },
        "demo": {
            "detected": False,
            "demo_type": "none",
            "steps": [],
            "before_state_visible": False,
            "after_state_visible": False,
            "mechanism_clarity": "unknown",
            "continuity": "unknown",
            "confidence": 0,
        },
        "proof_moments": [],
        "ctas": [],
        "offers": [],
        "creator": {
            "face_present": None,
            "speaking_present": None,
            "delivery_style": "unknown",
            "creator_persona": None,
            "emotion": "unknown",
            "pacing": "unknown",
            "sales_language_intensity": "unknown",
            "authenticity_cues": [],
            "confidence": 0,
        },
        "editing": {
            "cut_count": None,
            "average_shot_duration_ms": None,
            "first_three_second_cut_count": None,
            "pattern_interrupts": [],
            "dead_air_ranges": [],
            "caption_density": "unknown",
            "visual_pacing": "unknown",
            "transition_types": [],
            "confidence": 0,
        },
        "claims": [],
        "platform": {
            "aspect_ratio": None,
            "vertical": None,
            "native_signals": [],
            "shop_signals": [],
            "caption_style": [],
            "visual_safe_zone_risk": None,
            "confidence": 0,
        },
        "uncertainties": [],
    }
