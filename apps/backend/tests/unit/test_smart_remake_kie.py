from __future__ import annotations

import json
import socket
from collections.abc import Callable

import httpcore
import httpx
import pytest

from viraldy.modules.smart_remake.engine.errors import SmartRemakeError
from viraldy.modules.smart_remake.engine.kie_adapter import build_kie_video_request
from viraldy.modules.smart_remake.engine.kie_client import KieClient
from viraldy.modules.smart_remake.engine.kie_polling import wait_for_kie_task
from viraldy.modules.smart_remake.engine.schemas import UploadedMedia

VIDEO_URL = "https://8.8.8.8/output.mp4"
IMAGE_URL = "https://8.8.8.8/product.jpg"


def request_input() -> dict:
    return build_kie_video_request(
        scene={"videoPrompt": "Show the product turning on the desk."},
        product_image_url=IMAGE_URL,
    )["input"]


def client_for(handler: Callable) -> KieClient:
    return KieClient(
        api_key="test-key", http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )


def envelope(data: object, *, code: int = 200) -> httpx.Response:
    return httpx.Response(200, json={"code": code, "msg": "provider response", "data": data})


def test_adapter_builds_native_kie_request_and_preserves_product_shots_and_edits() -> None:
    scene = {
        "promptEdited": True,
        "prompt": "SCENE EDIT",
        "imagePrompt": "VISUAL EDIT",
        "videoPrompt": "MOTION EDIT",
        "shotPlan": {
            "targetDuration": 8,
            "shots": [
                {"startSecond": 0, "endSecond": 4, "action": "wipe left", "stateAfter": "clean"},
                {"startSecond": 4, "endSecond": 8, "action": "reveal result"},
            ],
        },
    }
    payload = build_kie_video_request(
        scene=scene,
        product_image_url=IMAGE_URL,
        product_lock={"productName": "Pink Cup", "mustPreserve": ["pink handle"]},
        reference_analysis={"audioPlan": {"mode": "native", "language": "Vietnamese"}},
    )
    data = payload["input"]
    assert payload["model"] == "veo-3-1"
    assert data["model"] == "veo3_lite"
    assert data["generation_type"] == "REFERENCE_2_VIDEO"
    assert data["aspect_ratio"] == "9:16" and data["duration"] == 8
    assert data["image_urls"] == [IMAGE_URL]
    assert data["resolution"] == "720p" and data["enable_translation"] is False
    assert all(
        s in data["prompt"]
        for s in [
            "SCENE EDIT",
            "VISUAL EDIT",
            "MOTION EDIT",
            "Pink Cup",
            "pink handle",
            "wipe left",
            "reveal result",
            "Vietnamese",
        ]
    )
    assert "@Image1" not in data["prompt"]
    assert "reference_image_urls" not in data


def test_adapter_does_not_truncate_long_user_changes() -> None:
    with pytest.raises(SmartRemakeError, match="focused"):
        build_kie_video_request(
            scene={"promptEdited": True, "videoPrompt": "new directions " * 500},
            product_image_url=IMAGE_URL,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("duration", [8, 16])
async def test_compiler_scene_units_fit_native_kie_requests(duration: int) -> None:
    from viraldy.modules.smart_remake.engine.compiler import (
        compile_smart_remake_scene_map_with_diagnostics,
    )
    from viraldy.modules.smart_remake.fixture import FixtureGeminiClient

    fixture = FixtureGeminiClient()
    analysis = await fixture.generate_json(system_instruction="", prompt=f"analyze {duration}")
    product = await fixture.generate_json(system_instruction="", prompt="product lock")
    compiled = compile_smart_remake_scene_map_with_diagnostics(
        {
            "mode": "smart_remake",
            "targetDuration": duration,
            "aspectRatio": "9:16",
            "language": "Vietnamese",
            "referenceAnalysis": analysis,
            "productLock": product,
        }
    )
    scenes = compiled["sceneMap"]["scenes"]
    assert len(scenes) == duration // 8
    for scene in scenes:
        data = build_kie_video_request(
            scene=scene,
            product_image_url=IMAGE_URL,
            product_lock=product,
            reference_analysis=analysis,
        )["input"]
        assert data["duration"] == 8 and "Target Product" in data["prompt"]
        assert all(shot["action"] in data["prompt"] for shot in scene["shotPlan"]["shots"])


@pytest.mark.parametrize(
    "url", ["file:///tmp/a", "http://127.0.0.1/a", "https://user:pw@8.8.8.8/a"]
)
def test_adapter_rejects_non_public_product_images(url: str) -> None:
    with pytest.raises(SmartRemakeError):
        build_kie_video_request(scene={"videoPrompt": "demo"}, product_image_url=url)


@pytest.mark.asyncio
async def test_upload_and_create_use_official_endpoints_and_authorization() -> None:
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req)
        assert req.headers["authorization"] == "Bearer test-key"
        if "file-stream-upload" in str(req.url):
            assert req.url.host == "kieai.redpandaai.co"
            assert b'name="file"' in req.content
            assert b'name="uploadPath"' in req.content
            return envelope({"success": True, "downloadUrl": IMAGE_URL})
        assert str(req.url) == "https://api.kie.ai/api/v1/jobs/createTask"
        assert json.loads(req.content) == {"model": "veo-3-1", "input": request_input()}
        return envelope({"taskId": "task-1"})

    client = client_for(handler)
    assert (
        await client.upload_file(UploadedMedia(bytes=b"image", mime_type="image/jpeg")) == IMAGE_URL
    )
    assert await client.create_task(model="veo-3-1", input_data=request_input()) == {
        "task_id": "task-1",
        "status": "queued",
    }
    assert len(calls) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "code, expected",
    [
        (401, "KIE_AUTH_FAILED"),
        (402, "KIE_CREDITS_EXHAUSTED"),
        (429, "KIE_RATE_LIMITED"),
        (422, "KIE_VALIDATION_FAILED"),
    ],
)
async def test_http_200_error_envelope_is_rejected(code: int, expected: str) -> None:
    client = client_for(lambda req: envelope(None, code=code))
    with pytest.raises(SmartRemakeError) as exc:
        await client.create_task(model="veo-3-1", input_data=request_input())
    assert exc.value.code == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(503, json={"code": 503}),
        httpx.Response(200, text="not JSON"),
        envelope({}),
        httpx.Response(200, json={"data": {"taskId": "x"}}),
    ],
)
async def test_ambiguous_paid_submit_is_never_retried(response: httpx.Response) -> None:
    calls = []
    client = client_for(lambda req: calls.append(req) or response)
    with pytest.raises(SmartRemakeError) as exc:
        await client.create_task(model="veo-3-1", input_data=request_input())
    assert exc.value.code == "KIE_SUBMISSION_UNCERTAIN"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_submit_timeout_is_uncertain_and_contains_no_key_or_prompt() -> None:
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req)
        raise httpx.ReadTimeout("untrusted error test-key", request=req)

    with pytest.raises(SmartRemakeError) as exc:
        await client_for(handler).create_task(model="veo-3-1", input_data=request_input())
    assert exc.value.code == "KIE_SUBMISSION_UNCERTAIN" and len(calls) == 1
    assert "test-key" not in str(exc.value.details)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "result",
    [
        {"resultUrls": [VIDEO_URL]},
        {"data": {"result_urls": [VIDEO_URL], "origin_urls": ["https://8.8.4.4/original.mp4"]}},
    ],
)
async def test_success_normalizes_documented_result_layouts(result: dict) -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.method == "GET" and req.url.params["taskId"] == "task-1"
        return envelope(
            {
                "taskId": "task-1",
                "model": "veo-3-1",
                "state": "success",
                "resultJson": json.dumps(result),
            }
        )

    result = await client_for(handler).get_task("task-1")
    assert result["status"] == "completed" and result["output"]["video_url"] == VIDEO_URL


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "state, expected",
    [
        ("waiting", "queued"),
        ("queuing", "queued"),
        ("generating", "processing"),
        ("fail", "failed"),
    ],
)
async def test_status_normalizes_known_states(state: str, expected: str) -> None:
    client = client_for(
        lambda req: envelope({"taskId": "task-1", "state": state, "failMsg": "generation rejected"})
    )
    task = await client.get_task("task-1")
    assert task["status"] == expected
    if state == "fail":
        assert task["error_message"] == "generation rejected"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data",
    [
        {"taskId": "task-1", "state": "unknown"},
        {"taskId": "other-task", "state": "waiting"},
        {"taskId": "task-1", "model": "other-model", "state": "waiting"},
        {"taskId": "task-1", "state": "success", "resultJson": "garbage"},
        {"taskId": "task-1", "state": "success", "resultJson": "{}"},
        {"taskId": "task-1", "state": "success", "resultJson": '{"resultUrls":[]}'},
        {
            "taskId": "task-1",
            "state": "success",
            "resultJson": '{"resultUrls":["http://127.0.0.1/a"]}',
        },
    ],
)
async def test_unknown_or_unsafe_status_fails_closed(data: dict) -> None:
    with pytest.raises(SmartRemakeError) as exc:
        await client_for(lambda req: envelope(data)).get_task("task-1")
    assert exc.value.code in {"KIE_INVALID_RESPONSE", "KIE_UNSAFE_MEDIA_URL"}


@pytest.mark.asyncio
async def test_download_never_sends_credentials_and_validates_redirects() -> None:
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req)
        assert "authorization" not in req.headers
        return httpx.Response(302, headers={"location": "http://169.254.169.254/secrets"})

    with pytest.raises(SmartRemakeError) as exc:
        await client_for(handler).download_file(VIDEO_URL)
    assert exc.value.code == "KIE_UNSAFE_MEDIA_URL" and len(calls) == 1


@pytest.mark.asyncio
async def test_download_returns_video_bytes() -> None:
    client = client_for(
        lambda req: httpx.Response(200, content=b"mp4-video", headers={"content-type": "video/mp4"})
    )
    assert await client.download_file(VIDEO_URL) == b"mp4-video"


@pytest.mark.asyncio
async def test_download_strips_default_client_credentials_and_auth() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        assert "authorization" not in req.headers and "cookie" not in req.headers
        return httpx.Response(200, content=b"video", headers={"content-type": "video/mp4"})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        headers={"Authorization": "Bearer do-not-leak", "Cookie": "session=secret"},
        auth=("private-user", "private-password"),
    ) as http_client:
        client = KieClient(api_key="test-key", http_client=http_client)
        assert await client.download_file(VIDEO_URL) == b"video"


@pytest.mark.asyncio
async def test_download_pins_the_single_vetted_resolution_and_preserves_https_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolutions = []

    def resolver(host: str, port: int, **_: object) -> list:
        resolutions.append(host)
        address = "8.8.8.8" if len(resolutions) == 1 else "127.0.0.1"
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port))]

    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.host == "8.8.8.8"
        assert req.headers["host"] == "media.example:8443"
        assert req.extensions["sni_hostname"] == "media.example"
        return httpx.Response(200, content=b"video", headers={"content-type": "video/mp4"})

    monkeypatch.setattr(socket, "getaddrinfo", resolver)
    assert await client_for(handler).download_file("https://media.example:8443/video") == b"video"
    assert resolutions == ["media.example"]


@pytest.mark.asyncio
async def test_download_revalidates_and_pins_relative_redirect_to_original_hostname(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolutions = []
    requests = []

    def resolver(host: str, port: int, **_: object) -> list:
        resolutions.append(host)
        address = "8.8.8.8" if len(resolutions) == 1 else "8.8.4.4"
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port))]

    def handler(req: httpx.Request) -> httpx.Response:
        requests.append(req)
        assert req.headers["host"] == "media.example"
        assert req.extensions["sni_hostname"] == "media.example"
        if len(requests) == 1:
            assert req.url.host == "8.8.8.8"
            return httpx.Response(302, headers={"location": "../final.mp4"})
        assert req.url.host == "8.8.4.4" and req.url.path == "/final.mp4"
        return httpx.Response(200, content=b"video", headers={"content-type": "video/mp4"})

    monkeypatch.setattr(socket, "getaddrinfo", resolver)
    assert (
        await client_for(handler).download_file("https://media.example/start/file.mp4") == b"video"
    )
    assert resolutions == ["media.example", "media.example"]


@pytest.mark.asyncio
async def test_download_rejects_mixed_public_and_private_dns_before_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port)),
        ],
    )
    requests = []
    with pytest.raises(SmartRemakeError) as exc:
        await client_for(lambda req: requests.append(req) or httpx.Response(200)).download_file(
            "https://media.example/video",
        )
    assert exc.value.code == "KIE_UNSAFE_MEDIA_URL" and requests == []


@pytest.mark.asyncio
async def test_httpcore_connects_to_vetted_ip_and_verifies_original_tls_hostname(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connections = []
    tls_names = []
    written = []

    class Stream(httpcore.AsyncNetworkStream):
        async def read(self, max_bytes: int, timeout: float | None = None) -> bytes:
            return b"HTTP/1.1 200 OK\r\nContent-Type: video/mp4\r\nContent-Length: 5\r\n\r\nvideo"

        async def write(self, buffer: bytes, timeout: float | None = None) -> None:
            written.append(buffer)

        async def aclose(self) -> None:
            pass

        async def start_tls(
            self,
            ssl_context: object,
            server_hostname: str | None = None,
            timeout: float | None = None,
        ) -> Stream:
            tls_names.append(server_hostname)
            return self

        def get_extra_info(self, info: str) -> None:
            return None

    class Backend(httpcore.AsyncNetworkBackend):
        async def connect_tcp(self, host: str, port: int, **kwargs: object) -> Stream:
            connections.append((host, port))
            return Stream()

    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port)),
        ],
    )
    transport = httpx.AsyncHTTPTransport(trust_env=False)
    transport._pool = httpcore.AsyncConnectionPool(network_backend=Backend())
    async with httpx.AsyncClient(transport=transport, trust_env=False) as http_client:
        client = KieClient(api_key="not-real", http_client=http_client)
        assert await client.download_file("https://media.example/video") == b"video"
    assert connections == [("8.8.8.8", 443)]
    assert tls_names == ["media.example"]
    assert b"host: media.example\r\n" in b"".join(written).lower()
    assert b"authorization" not in b"".join(written).lower()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [httpx.Response(404), httpx.Response(200, text="html"), httpx.Response(200, content=b"")],
)
async def test_download_rejects_failed_empty_or_non_video_response(
    response: httpx.Response,
) -> None:
    with pytest.raises(SmartRemakeError) as exc:
        await client_for(lambda req: response).download_file(VIDEO_URL)
    assert exc.value.code == "KIE_OUTPUT_DOWNLOAD_FAILED"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "media",
    [
        UploadedMedia(bytes=b"x", mime_type="video/mp4"),
        UploadedMedia(bytes=b"", mime_type="image/png"),
        UploadedMedia(bytes=b"x" * (10 * 1024 * 1024 + 1), mime_type="image/jpeg"),
    ],
)
async def test_upload_rejects_invalid_images_before_network(media: UploadedMedia) -> None:
    calls = []
    with pytest.raises(SmartRemakeError):
        await client_for(lambda req: calls.append(req) or envelope({})).upload_file(media)
    assert calls == []


@pytest.mark.asyncio
async def test_poller_returns_completion_after_processing() -> None:
    states = iter(
        [
            {"status": "queued"},
            {"status": "processing"},
            {"status": "completed", "output": {"video_url": VIDEO_URL}},
        ]
    )

    async def status(task_id: str) -> dict:
        assert task_id == "task-1"
        return next(states)

    result = await wait_for_kie_task("task-1", status, interval_seconds=0.001, timeout_seconds=1)
    assert result["status"] == "completed"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "state, expected", [("failed", "KIE_TASK_FAILED"), ("unknown", "KIE_INVALID_RESPONSE")]
)
async def test_poller_rejects_terminal_or_unknown_states(state: str, expected: str) -> None:
    async def status(_: str) -> dict:
        return {"status": state, "error_message": "failed"}

    with pytest.raises(SmartRemakeError) as exc:
        await wait_for_kie_task("task-1", status, interval_seconds=0.001, timeout_seconds=1)
    assert exc.value.code == expected and exc.value.details["taskId"] == "task-1"


@pytest.mark.asyncio
async def test_poll_timeout_retains_task_id_without_resubmission() -> None:
    calls = []

    async def status(task_id: str) -> dict:
        calls.append(task_id)
        return {"status": "processing"}

    with pytest.raises(SmartRemakeError) as exc:
        await wait_for_kie_task("task-1", status, interval_seconds=0.001, timeout_seconds=0.005)
    assert exc.value.code == "KIE_POLL_TIMEOUT" and exc.value.details["taskId"] == "task-1"
    assert set(calls) == {"task-1"}
