from __future__ import annotations

import array
import json
import math
import subprocess

import pytest

from viraldy.modules.smart_remake.engine.media_binaries import ffmpeg_path, ffprobe_path
from viraldy.modules.smart_remake.repair_media import technical_check
from viraldy.modules.smart_remake.timeline_media import _assemble, probe_timeline_media


@pytest.fixture(scope="module")
def voiced_clips(tmp_path_factory):
    folder = tmp_path_factory.mktemp("wan-audio-timeline")
    clips = []
    for index, (color, frequency) in enumerate((("red", 440), ("blue", 880))):
        path = folder / f"part-{index}.mp4"
        subprocess.run([  # noqa: S603 - fixed local fixture inputs and generated paths
            ffmpeg_path(), "-v", "error", "-y",
            "-f", "lavfi", "-i", f"color=c={color}:s=480x854:r=30:d=6",
            "-f", "lavfi", "-i", f"sine=frequency={frequency}:sample_rate=48000:duration=6",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", str(path),
        ], check=True, capture_output=True, timeout=60)
        clips.append(path.read_bytes())
    return clips


@pytest.mark.parametrize("fragmented", [False, True])
def test_two_six_second_clips_keep_audio_and_480p_when_assembled(
    voiced_clips, tmp_path, fragmented,
):
    if fragmented:
        clips = [clip for clip in voiced_clips for _ in range(12)]
        items = [dict(inFrame=start, outFrame=start + 12, targetDurationFrames=12)
                 for _ in voiced_clips for start in range(0, 144, 12)]
    else:
        clips = voiced_clips
        items = [dict(inFrame=0, outFrame=144, targetDurationFrames=144) for _ in voiced_clips]
    for clip in voiced_clips:
        assert probe_timeline_media(clip)["frameCount"] == 144
    output = _assemble(clips, items, resolution="480P")
    probe = probe_timeline_media(output)
    assert probe["frameCount"] == probe["decodedFrameCount"] == 288
    assert probe["fps"] == 24 and probe["hasAudio"]
    assert technical_check(output, expected_duration=12, audio_required=True)["status"] == "passed"
    path = tmp_path / "review.mp4"
    path.write_bytes(output)
    metadata = json.loads(subprocess.check_output([  # noqa: S603 - generated fixture path
        ffprobe_path(), "-v", "error", "-select_streams", "v:0", "-show_entries",
        "stream=width,height", "-of", "json", str(path),
    ]))
    assert metadata["streams"][0] == {"width": 480, "height": 854}
    for start in (1, 7):
        samples = array.array("h", subprocess.check_output([  # noqa: S603 - fixed decode arguments
            ffmpeg_path(), "-v", "error", "-ss", str(start), "-t", "1", "-i", str(path),
            "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "pipe:1",
        ]))
        rms = math.sqrt(sum(value * value for value in samples) / len(samples))
        assert rms > 500, "Each six-second window must retain audible source audio."
