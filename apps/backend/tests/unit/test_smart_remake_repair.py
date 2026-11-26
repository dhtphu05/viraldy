from __future__ import annotations

import hashlib

import pytest
from pydantic import ValidationError

from viraldy.modules.smart_remake.engine.unifically_adapter import build_unifically_video_input
from viraldy.modules.smart_remake.repair_media import technical_check
from viraldy.modules.smart_remake.repair_schemas import AcceptSceneVersion, RepairSceneRequest
from viraldy.platform.storage.s3 import S3StorageAdapter


def test_repair_rejects_arbitrary_media_urls_and_blank_prompts() -> None:
    payload = {
        "baseVersionId": "8b924f9b-0140-4ad5-a3bd-203322962b45",
        "expectedRevision": 1,
        "prompt": "scene",
        "imagePrompt": "image",
        "videoPrompt": "video",
        "idempotencyKey": "test-repair",
    }
    with pytest.raises(ValidationError):
        RepairSceneRequest.model_validate({**payload, "videoUrl": "http://127.0.0.1"})
    with pytest.raises(ValidationError):
        RepairSceneRequest.model_validate({**payload, "videoPrompt": "   "})


def test_accept_requires_internal_version_and_revision() -> None:
    with pytest.raises(ValidationError):
        AcceptSceneVersion.model_validate(
            {
                "sceneId": "https://example.test/scene.mp4",
                "versionId": "video",
                "expectedRevision": 0,
                "idempotencyKey": "accept",
            }
        )


def test_technical_check_is_bound_to_media_and_rejects_wrong_duration() -> None:
    media = b"a scene clip"
    check = technical_check(
        media,
        expected_duration=8,
        audio_required=False,
        probe=lambda _: {
            "hasVideo": True,
            "hasAudio": False,
            "width": 720,
            "height": 1280,
            "durationSeconds": 16,
        },
    )
    assert check["status"] == "failed"
    assert check["mediaHash"] == hashlib.sha256(media).hexdigest()
    assert any("duration" in item.lower() for item in check["findings"])


def test_technical_check_does_not_claim_semantic_quality() -> None:
    check = technical_check(
        b"clip",
        expected_duration=8,
        audio_required=False,
        probe=lambda _: {
            "hasVideo": True,
            "hasAudio": False,
            "width": 720,
            "height": 1280,
            "durationSeconds": 8,
        },
    )
    assert check["status"] == "passed"
    assert check["coverage"] == ["video_stream", "dimensions", "duration"]
    assert "product" not in str(check)


def test_probe_failure_never_passes() -> None:
    def failing_probe(_: bytes) -> dict:
        raise ValueError("cannot decode")

    check = technical_check(b"bad", expected_duration=8, audio_required=False, probe=failing_probe)
    assert check["status"] == "failed"


@pytest.mark.parametrize("segment_count", [1, 2])
def test_edited_prompt_reaches_provider_with_identity_and_segment_lock(segment_count) -> None:
    scene = {
        "prompt": "UNIQUE SCENE TEXT",
        "originalPrompt": "original scene text",
        "imagePrompt": "UNIQUE IMAGE TEXT",
        "originalImagePrompt": "original image text",
        "videoPrompt": "UNIQUE EDITED SCENE DIRECTION",
        "promptEdited": True,
        "sourceSegment": {
            "segmentCount": segment_count,
            "segmentOrder": segment_count,
            "sourceTimeRange": {"startSecond": 8, "endSecond": 16},
        },
        "shotPlan": {},
    }
    payload = build_unifically_video_input(
        scene=scene,
        product_image_url="https://storage.test/product.png",
        product_lock={
            "productName": "Authoritative Product",
            "mustPreserve": ["exact shape"],
            "productReference": {"characterName": "Authoritative Product"},
        },
    )
    assert "UNIQUE EDITED SCENE DIRECTION" in payload["prompt"]
    assert "UNIQUE SCENE TEXT" in payload["prompt"]
    assert "UNIQUE IMAGE TEXT" in payload["prompt"]
    assert "STRICT PRODUCT IDENTITY LOCK" in payload["prompt"]
    assert "exact shape" in payload["prompt"]
    assert "FINAL SOURCE SEGMENT EXECUTION" in payload["prompt"]
    assert payload["duration"] == 8
    assert payload["reference_image_urls"] == ["https://storage.test/product.png"]


def test_attachment_presigning_sanitizes_filename_without_changing_existing_downloads() -> None:
    from types import SimpleNamespace

    calls = []

    class Client:
        def generate_presigned_url(self, **kwargs):
            calls.append(kwargs)
            return "https://storage.test/signed"

    adapter = S3StorageAdapter.__new__(S3StorageAdapter)
    adapter._client = Client()
    adapter._settings = SimpleNamespace(s3_bucket="bucket", s3_presigned_expiry_seconds=300)
    adapter.create_presigned_download("owned-key")
    adapter.create_presigned_download("owned-key", filename='scene"\r\nheader.mp4')
    assert calls[0]["Params"] == {"Bucket": "bucket", "Key": "owned-key"}
    disposition = calls[1]["Params"]["ResponseContentDisposition"]
    assert disposition == 'attachment; filename="scene___header.mp4"'
