from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from viraldy.modules.media_analysis.contracts import MediaObservationBundleV1
from viraldy.modules.media_analysis.service import SyncMediaEvidencePipeline


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
