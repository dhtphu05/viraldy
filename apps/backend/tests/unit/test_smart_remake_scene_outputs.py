from __future__ import annotations

import pytest

from viraldy.modules.smart_remake.engine import render_orchestrator as engine
from viraldy.modules.smart_remake.engine.errors import SmartRemakeError
from viraldy.modules.smart_remake.engine.schemas import RenderSmartRemakeInput, UploadedMedia


def render_input():
    return RenderSmartRemakeInput(
        productLock={"productReference": {"characterName": "Product"}},
        sceneMap={
            "targetDuration": 16,
            "sceneCount": 2,
            "scenes": [
                {
                    "displayOrder": index,
                    "prompt": "scene",
                    "imagePrompt": "image",
                    "videoPrompt": "video",
                }
                for index in range(2)
            ],
        },
        productImage=UploadedMedia(bytes=b"product", mime_type="image/png"),
        projectName="test",
        provider="unifically",
    )


@pytest.mark.asyncio
async def test_unifically_retains_each_raw_clip_and_final_output_with_provider_task_ids(
    monkeypatch,
):
    class Client:
        async def upload_file(self, media):
            return "https://provider.test/product"

        async def create_task(self, *, model, input_data):
            self.count = getattr(self, "count", 0) + 1
            return {"task_id": f"task-{self.count}"}

        async def get_task(self, task_id):
            return {
                "status": "completed",
                "output": {"video_url": f"https://provider.test/{task_id}"},
            }

        async def download_file(self, url):
            return url.encode()

    async def concat(**kwargs):
        assert len(kwargs["video_urls"]) == 2
        return b"final assembly"

    monkeypatch.setattr(
        engine, "save_smart_remake_output", lambda *args: (None, "https://owned.test/final")
    )
    outputs, tasks = [], []

    async def capture(index, data, metadata):
        outputs.append((index, data, metadata))

    async def task(metadata):
        tasks.append(metadata)

    result = await engine._render_with_unifically(
        render_input(),
        unifically=Client(),
        concat_urls=concat,
        probe=lambda _: {"hasVideo": True, "hasAudio": True, "audioDurationSeconds": 8},
        on_scene_output=capture,
        on_task_submitted=task,
    )
    assert result["status"] == "completed"
    assert [item[0] for item in outputs] == [0, 1, -1]
    assert outputs[0][1].endswith(b"task-1") and outputs[1][1].endswith(b"task-2")
    assert outputs[-1][1] == b"final assembly"
    assert [item["requestIds"] for item in tasks] == [["task-1"], ["task-2"]]


@pytest.mark.asyncio
async def test_flowkit_partial_failure_retains_good_scene_for_targeted_recovery(monkeypatch):
    prepared = {
        "projectId": "project",
        "videoId": "video",
        "scenes": [
            {"flowKitSceneId": "scene-0", "smartRemakeDisplayOrder": 0},
            {"flowKitSceneId": "scene-1", "smartRemakeDisplayOrder": 1},
        ],
    }

    async def prepare(**kwargs):
        return prepared

    monkeypatch.setattr(engine, "prepare_flowkit_job", prepare)

    class FlowKit:
        async def create_batch_requests(self, requests):
            prefix = "image" if requests[0]["type"] == "GENERATE_IMAGE" else "video"
            return [{"id": f"{prefix}-{index}"} for index in range(2)]

        async def get_request_status(self, request_id):
            return {"status": "failed" if request_id == "video-1" else "completed"}

        async def list_scenes(self, video_id):
            return [
                {
                    "id": "scene-0",
                    "display_order": 0,
                    "vertical_video_url": "https://provider.test/good",
                },
                {"id": "scene-1", "display_order": 1},
            ]

    async def fetch(url, index):
        assert url == "https://provider.test/good"
        return b"good raw scene"

    monkeypatch.setattr(
        "viraldy.modules.smart_remake.engine.concat._fetch_scene_video_bytes", fetch
    )
    outputs = []

    async def capture(index, data, metadata):
        outputs.append((index, data, metadata))

    with pytest.raises(SmartRemakeError, match="failed"):
        await engine._render_with_flowkit(
            render_input(), flowkit=FlowKit(), on_scene_output=capture
        )
    assert len(outputs) == 1
    assert outputs[0][0] == 0 and outputs[0][1] == b"good raw scene"


def test_unknown_submission_5xx_is_not_automatically_resubmitted():
    assert not engine._should_retry_unifically_video(
        SmartRemakeError("Upstream error", "UNIFICALLY_TASK_CREATE_FAILED", {"status": 502})
    )
