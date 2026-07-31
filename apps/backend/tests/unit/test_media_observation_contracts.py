from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from viraldy.modules.media_analysis.contracts import MediaObservationBundleV1
from viraldy.modules.media_analysis.provider import (
    OcrContract,
    SceneContract,
    TranscriptContract,
    _native_media_output_validator,
)
from viraldy.modules.media_analysis.service import (
    SyncMediaEvidencePipeline,
    _cleanup_uploaded_objects_on_failure,
    _live_contract,
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
