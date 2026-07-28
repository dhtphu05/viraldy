from __future__ import annotations

from copy import deepcopy
from typing import Any

KNOWN_FIXTURE_CHECKSUMS = {
    "viraldy-demo-reference-v1",
    "viraldy-demo-ugc-fixable-v1",
    "viraldy-demo-quick-v1",
}


def is_known_fixture(checksum: str | None, metadata: dict[str, object] | None = None) -> bool:
    if checksum in KNOWN_FIXTURE_CHECKSUMS:
        return True
    return str((metadata or {}).get("fixture_id", "")) in KNOWN_FIXTURE_CHECKSUMS


def fixture_media_contract(
    checksum: str | None, metadata: dict[str, object] | None = None
) -> dict[str, Any]:
    fixture_id = (
        checksum if checksum in KNOWN_FIXTURE_CHECKSUMS else str((metadata or {}).get("fixture_id"))
    )
    if fixture_id not in KNOWN_FIXTURE_CHECKSUMS:
        raise ValueError("unsupported_fixture")

    late_reveal = fixture_id == "viraldy-demo-ugc-fixable-v1"
    first_product_ms = 6100 if late_reveal else 2400
    cta_ms = 24800 if late_reveal else 18200

    return deepcopy(
        {
            "analysis_mode": "fixture",
            "provider": "fixture",
            "model_version": "fixture_media_v1",
            "metadata": {
                "duration_ms": 28000,
                "container": "mp4",
                "video_codec": "h264",
                "audio_codec": "aac",
                "width": 1080,
                "height": 1920,
                "fps": 30,
                "video_stream_count": 1,
                "audio_stream_count": 1,
            },
            "transcript": {
                "language": "en",
                "segments": [
                    {"start_ms": 0, "end_ms": 2100, "text": "My counter was always a mess."},
                    {
                        "start_ms": first_product_ms,
                        "end_ms": first_product_ms + 1800,
                        "text": "This rack gave me half my counter back.",
                    },
                    {
                        "start_ms": cta_ms,
                        "end_ms": 27000,
                        "text": "It is linked in my TikTok Shop.",
                    },
                ],
                "full_text": (
                    "My counter was always a mess. This rack gave me half my counter back. "
                    "It is linked in my TikTok Shop."
                ),
            },
            "ocr": {
                "segments": [
                    {
                        "start_ms": 300,
                        "end_ms": 1800,
                        "text": "I did not know I needed this",
                        "confidence": 0.91,
                        "frame_storage_key": "fixtures/opening.jpg",
                    },
                    {
                        "start_ms": cta_ms,
                        "end_ms": 27000,
                        "text": "TikTok Shop",
                        "confidence": 0.95,
                        "frame_storage_key": "fixtures/cta.jpg",
                    },
                ]
            },
            "sampled_frames": {
                "frames": [
                    {"timestamp_ms": 500, "storage_key": "fixtures/opening.jpg"},
                    {"timestamp_ms": first_product_ms, "storage_key": "fixtures/product.jpg"},
                    {"timestamp_ms": 11200, "storage_key": "fixtures/demo.jpg"},
                    {"timestamp_ms": cta_ms, "storage_key": "fixtures/cta.jpg"},
                ]
            },
            "scene_boundaries": {
                "scenes": [
                    {"scene_index": 0, "start_ms": 0, "end_ms": first_product_ms},
                    {"scene_index": 1, "start_ms": first_product_ms, "end_ms": 15000},
                    {"scene_index": 2, "start_ms": 15000, "end_ms": 28000},
                ]
            },
            "visual_observations": {
                "product_first_appearance_ms": first_product_ms,
                "face_present_opening": True,
                "opening_visual": "messy kitchen counter",
                "demo_detected": True,
                "demo_type": "before_after",
                "close_up_present": not late_reveal,
                "cta_visual_detected": True,
                "proof_type": "visual_before_after",
                "creator_style": "home_organizer",
                "claim_candidates": [
                    {
                        "text": "best ever",
                        "risk": "medium",
                        "timestamp_ms": 14200,
                    }
                ]
                if late_reveal
                else [],
            },
        }
    )
