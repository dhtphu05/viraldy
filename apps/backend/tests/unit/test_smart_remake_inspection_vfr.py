"""Actual VFR bytes use the canonical source clock and cannot pass as CFR output."""

from __future__ import annotations

import hashlib
import subprocess
from io import BytesIO

import pytest
from PIL import Image

from viraldy.modules.smart_remake.engine.media_binaries import ffmpeg_path
from viraldy.modules.smart_remake.inspection.contracts import ResolvedMedia
from viraldy.modules.smart_remake.inspection.media import technical_problem, video_observations
from viraldy.modules.smart_remake.timeline_media import probe_timeline_media


@pytest.fixture(scope="module")
def vfr_media(tmp_path_factory):
    path = tmp_path_factory.mktemp("p0-vfr") / "owned-vfr.mp4"
    subprocess.run(  # noqa: S603 - fixed executable, synthetic media and local paths
        [
            ffmpeg_path(),
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=red:size=90x160:rate=24:duration=8",
            "-vf",
            "drawbox=color=blue:t=fill:enable='gte(t,2)'," "select='if(lt(n,48),not(mod(n,2)),1)'",
            "-fps_mode",
            "vfr",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
    data = path.read_bytes()
    return ResolvedMedia(
        id="source",
        role="source",
        bytes=data,
        mediaHash=hashlib.sha256(data).hexdigest(),
        mimeType="video/mp4",
        frameCount=192,
        fps=24,
    )


def test_vfr_source_evidence_uses_canonical_frames_and_exclusive_end(vfr_media):
    info = probe_timeline_media(vfr_media.bytes)
    assert info["fps"] != 24 and info["decodedFrameCount"] < 192
    frames = [0, 23, 47, 48, 191]
    observations, images = video_observations(
        vfr_media, frames, timebase="source", max_long_edge=1280
    )
    assert [(item.inFrame, item.outFrame) for item in observations] == [
        (frame, frame + 1) for frame in frames
    ]
    for frame, image in zip(frames, images, strict=True):
        with Image.open(BytesIO(image.data)) as decoded:
            red, _, blue = decoded.convert("RGB").getpixel((45, 80))
        assert (red > 200 and blue < 20) if frame < 48 else (blue > 200 and red < 20)
    with pytest.raises(ValueError, match="valid canonical frame"):
        video_observations(vfr_media, [192], timebase="source", max_long_edge=1280)


def test_vfr_output_never_passes_the_exact_cfr_technical_requirement(vfr_media):
    problem = technical_problem(vfr_media, kind="assembly", retained_status="passed")
    assert problem and "24-fps" in problem
