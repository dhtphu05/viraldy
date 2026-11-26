from __future__ import annotations

import array
import hashlib
import subprocess
from types import SimpleNamespace
from uuid import uuid4

import pytest

from viraldy.modules.smart_remake.engine.media_binaries import ffmpeg_path
from viraldy.modules.smart_remake.repair_service import RepairService


@pytest.mark.asyncio
async def test_real_assembly_preserves_second_scene_audio_after_silent_first_scene(tmp_path):
    media = {}
    for index in range(2):
        path = tmp_path / f"scene-{index}.mp4"
        args = [ffmpeg_path(), "-y", "-f", "lavfi", "-i", "color=red:s=90x160:r=24:d=8"]
        if index:
            args += ["-f", "lavfi", "-i", "sine=frequency=440:duration=8"]
        args += [
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(path),
        ]
        subprocess.run(args, check=True, capture_output=True, timeout=60)  # noqa: S603 - fixed local fixture inputs
        media[str(index)] = path.read_bytes()

    class Media:
        async def read(self, key):
            return media[key]

    scenes = [
        {
            "id": str(uuid4()),
            "index": index,
            "activeVersionId": str(index),
            "versions": [
                {
                    "id": str(index),
                    "storageKey": str(index),
                    "mediaHash": hashlib.sha256(media[str(index)]).hexdigest(),
                    "technicalCheck": {"status": "passed"},
                }
            ],
        }
        for index in range(2)
    ]
    original_hashes = [hashlib.sha256(data).hexdigest() for data in media.values()]
    service = RepairService(None, Media(), uuid4())
    output, check = await service._compose(
        SimpleNamespace(
            context_json={
                "projectName": "audio-regression",
                "audioRequired": False,
            }
        ),
        {"scenes": scenes, "targetDuration": 16},
    )
    assert check["status"] == "passed"
    assert [hashlib.sha256(data).hexdigest() for data in media.values()] == original_hashes
    target = tmp_path / "final.mp4"
    target.write_bytes(output)
    decoded = subprocess.run(  # noqa: S603 - fixed argv and generated local fixture path
        [
            ffmpeg_path(),
            "-v",
            "error",
            "-ss",
            "9",
            "-t",
            "1",
            "-i",
            str(target),
            "-f",
            "s16le",
            "-ac",
            "1",
            "-ar",
            "8000",
            "pipe:1",
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )  # noqa: S603
    samples = array.array("h", decoded.stdout)
    assert samples and max(abs(sample) for sample in samples) > 500
