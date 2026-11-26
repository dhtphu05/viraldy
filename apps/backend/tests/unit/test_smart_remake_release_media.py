from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from viraldy.modules.smart_remake import export_media
from viraldy.modules.smart_remake.engine.media_binaries import ffmpeg_path
from viraldy.modules.smart_remake.engine.media_probe import probe_media_bytes
from viraldy.modules.smart_remake.timeline_media import probe_timeline_media
from viraldy.shared.errors.base import AppError


def _video(tmp_path: Path, *, frames=192, fps=24, dimensions="90x160", audio=True) -> bytes:
    target = tmp_path / f"fixture-{frames}-{fps}-{dimensions}-{audio}.mp4"
    argv = [
        ffmpeg_path(),
        "-v",
        "error",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=red:s={dimensions}:r={fps}",
    ]
    if audio:
        argv += ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000"]
    argv += [
        "-frames:v",
        str(frames),
        "-t",
        str(frames / fps),
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        str(target),
    ]
    subprocess.run(argv, check=True, capture_output=True, timeout=30)  # noqa: S603
    return target.read_bytes()


def _lower_frame(path: Path, frame: int) -> bytes:
    decoded = subprocess.run(  # noqa: S603 - fixed filter and generated fixture path
        [
            ffmpeg_path(),
            "-v",
            "error",
            "-i",
            str(path),
            "-vf",
            f"select=eq(n\\,{frame}),crop=90:40:0:120",
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "pipe:1",
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
    return decoded.stdout


@pytest.mark.parametrize(("frames", "audio"), [(192, True), (384, False)])
def test_real_export_burns_visible_label_and_preserves_technical_contract(tmp_path, frames, audio):
    source = _video(tmp_path, frames=frames, audio=audio)
    output, check = export_media.export_labeled_media(
        source, expected_frames=frames, audio_required=audio
    )
    info, dimensions = probe_timeline_media(output), probe_media_bytes(output)
    assert (info["frameCount"], info["decodedFrameCount"], info["fps"]) == (frames, frames, 24)
    assert info["hasAudio"] is audio
    assert (dimensions["width"], dimensions["height"]) == (90, 160)
    assert check["status"] == "passed"
    assert check["mediaHash"] == hashlib.sha256(output).hexdigest()
    assert check["frameCount"] == frames
    assert check["label"] == "AI-generated"
    assert check["policyVersion"] == "smart-remake-ai-label-v1"
    assert check["labelVerification"] == {
        "method": "decoded-overlay-template",
        "sampledFrames": [0, frames // 2, frames - 1],
        "verified": True,
    }
    original_path, labeled_path = tmp_path / "source.mp4", tmp_path / "labeled.mp4"
    original_path.write_bytes(source)
    labeled_path.write_bytes(output)
    for index in (0, frames // 2, frames - 1):
        before, after = _lower_frame(original_path, index), _lower_frame(labeled_path, index)
        changed = sum(abs(first - second) > 30 for first, second in zip(before, after, strict=True))
        assert changed > 300
        assert sum(min(after[i : i + 3]) > 180 for i in range(0, len(after), 3)) > 20


@pytest.mark.parametrize(
    "kwargs",
    [
        {"frames": 191},
        {"fps": 25},
        {"dimensions": "90x100"},
        {"dimensions": "90x158"},
        {"audio": False},
    ],
)
def test_export_rejects_media_that_does_not_match_reviewed_contract(tmp_path, kwargs):
    with pytest.raises(AppError, match="SMART_REMAKE_EXPORT_CHECK_FAILED"):
        export_media.export_labeled_media(
            _video(tmp_path, **kwargs), expected_frames=192, audio_required=True
        )


def test_export_rejects_unreadable_media():
    with pytest.raises(AppError, match="SMART_REMAKE_EXPORT_CHECK_FAILED"):
        export_media.export_labeled_media(
            b"not video", expected_frames=192, audio_required=False
        )


def test_export_rejects_unsupported_review_duration():
    with pytest.raises(AppError, match="SMART_REMAKE_EXPORT_CHECK_FAILED"):
        export_media.export_labeled_media(b"", expected_frames=24, audio_required=False)


def test_export_fails_closed_when_label_font_is_unavailable(tmp_path, monkeypatch):
    source = _video(tmp_path)
    monkeypatch.setattr(export_media, "FONT_CANDIDATES", [])
    with pytest.raises(AppError, match="SMART_REMAKE_AI_LABEL_UNAVAILABLE"):
        export_media.export_labeled_media(source, expected_frames=192, audio_required=True)


def test_export_fails_closed_if_encoder_outputs_unlabeled_media(tmp_path, monkeypatch):
    source = _video(tmp_path)
    run = subprocess.run

    def no_overlay(argv, **kwargs):
        if "-filter_complex" in argv:
            Path(argv[-1]).write_bytes(source)
            return subprocess.CompletedProcess(argv, 0, b"", b"")
        return run(argv, **kwargs)

    monkeypatch.setattr(export_media.subprocess, "run", no_overlay)
    with pytest.raises(AppError, match="SMART_REMAKE_AI_LABEL_VERIFICATION_FAILED"):
        export_media.export_labeled_media(source, expected_frames=192, audio_required=True)
