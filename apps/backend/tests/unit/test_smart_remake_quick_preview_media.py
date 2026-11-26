"""Bounded preview payloads cover the whole source without paid model calls."""

from __future__ import annotations

import json
import subprocess
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from viraldy.modules.smart_remake import quick_preview_media as module
from viraldy.modules.smart_remake.engine.media_binaries import ffmpeg_path, ffprobe_path
from viraldy.modules.smart_remake.engine.schemas import UploadedMedia
from viraldy.shared.errors.base import AppError


@pytest.fixture(scope="module")
def source_clips(tmp_path_factory):
    root = tmp_path_factory.mktemp("quick-preview-inputs")
    result = {}
    for audio in (True, False):
        target = root / f"source-{audio}.mp4"
        args = [ffmpeg_path(), "-y", "-f", "lavfi", "-i", "testsrc2=size=360x640:rate=24"]
        if audio:
            args += ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100"]
        args += ["-t", "8", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "25"]
        if audio:
            args += ["-c:a", "aac"]
        args += [str(target)]
        subprocess.run(args, check=True, capture_output=True, timeout=20)  # noqa: S603
        result[audio] = UploadedMedia(bytes=target.read_bytes(), mime_type="video/mp4")
    return result


def probe(path: Path):
    result = subprocess.run(  # noqa: S603 - test-owned fixture only
        [ffprobe_path(), "-v", "error", "-show_streams", "-of", "json", str(path)],
        check=True, capture_output=True, timeout=5,
    )
    return json.loads(result.stdout)["streams"]


@pytest.mark.parametrize("has_audio", [True, False])
def test_whole_source_proxy_is_small_and_preserves_real_audio(source_clips, tmp_path, has_audio):
    source = source_clips[has_audio]
    preview = module.prepare_quick_preview(source, 8)
    assert preview.kind == "video_proxy" and preview.has_audio is has_audio
    assert preview.source_duration_seconds == 8
    assert len(preview.media) == 1 and len(preview.media[0].bytes) < 2 * 1024 * 1024
    assert preview.media[0].mime_type == "video/mp4" and preview.media[0].bytes != source.bytes
    target = tmp_path / "preview.mp4"
    target.write_bytes(preview.media[0].bytes)
    streams = probe(target)
    video = next(stream for stream in streams if stream["codec_type"] == "video")
    assert max(video["width"], video["height"]) <= 640
    assert video["avg_frame_rate"] == "2/1"
    assert float(video["duration"]) == pytest.approx(8, abs=.5)
    assert any(stream["codec_type"] == "audio" for stream in streams) is has_audio
    if has_audio:
        audio = next(stream for stream in streams if stream["codec_type"] == "audio")
        assert audio["sample_rate"] == "16000" and audio["channels"] == 1
        assert float(audio["duration"]) == pytest.approx(8, abs=.1)
    assert len(preview.metadata["sourceMediaHash"]) == 64
    assert "path" not in str(preview.metadata).lower()


def test_proxy_timeout_falls_back_to_ordered_sampled_frames_only(source_clips, monkeypatch):
    def fail(*args):
        raise subprocess.TimeoutExpired("ffmpeg", 8)

    monkeypatch.setattr(module, "_video_proxy", fail)
    preview = module.prepare_quick_preview(source_clips[True], 8)
    assert preview.kind == "sampled_frames" and preview.has_audio is False
    assert len(preview.media) == 6 and preview.source_duration_seconds == 8
    for media in preview.media:
        assert media.mime_type == "image/jpeg"
        with Image.open(BytesIO(media.bytes)) as frame:
            assert max(frame.size) <= 320 and frame.format == "JPEG"
    assert preview.metadata["sampleCount"] == 6
    assert sum(len(media.bytes) for media in preview.media) <= module.MAX_PREVIEW_BYTES


@pytest.mark.parametrize("duration", [0, -1, float("nan"), float("inf"), True])
def test_invalid_duration_is_rejected_before_media_processes(source_clips, monkeypatch, duration):
    calls = []
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **kw: calls.append(a))
    with pytest.raises(AppError):
        module.prepare_quick_preview(source_clips[True], duration)
    assert calls == []


@pytest.mark.parametrize("source", [
    UploadedMedia(bytes=b"", mime_type="video/mp4"),
    UploadedMedia(bytes=b"x", mime_type="text/plain"),
])
def test_invalid_media_is_rejected_without_model_or_network_io(source):
    with pytest.raises(AppError):
        module.prepare_quick_preview(source, 8)


def test_unreadable_source_never_passes_fake_media_to_provider():
    with pytest.raises(AppError):
        module.prepare_quick_preview(UploadedMedia(bytes=b"bad video", mime_type="video/mp4"), 8)


def test_oversized_proxy_uses_frames_without_silently_truncating(source_clips, monkeypatch):
    monkeypatch.setattr(module, "_video_proxy", lambda *a: b"x" * (module.MAX_PREVIEW_BYTES + 1))
    result = module.prepare_quick_preview(source_clips[True], 8)
    assert result.kind == "sampled_frames" and result.source_duration_seconds == 8
    assert not result.has_audio
