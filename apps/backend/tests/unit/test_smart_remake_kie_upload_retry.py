"""Only free image-upload transport failures may receive one retry."""

import asyncio
from email import policy
from email.parser import BytesParser

import httpx
import pytest

from viraldy.modules.smart_remake.engine import kie_client as module
from viraldy.modules.smart_remake.engine.errors import SmartRemakeError
from viraldy.modules.smart_remake.engine.schemas import UploadedMedia

IMAGE_URL = "https://8.8.8.8/image.png"
MEDIA = UploadedMedia(bytes=b"exact verified image bytes", mime_type="image/png")


def upload_response() -> httpx.Response:
    return httpx.Response(200, json={"code": 200, "data": {"downloadUrl": IMAGE_URL}})


@pytest.mark.asyncio
async def test_upload_timeout_retries_exact_media_with_a_fresh_owned_client(monkeypatch):
    clients = []
    requests = []
    real_client = httpx.AsyncClient

    def handler(request):
        requests.append(request)
        if len(requests) == 1:
            raise httpx.WriteTimeout("private provider text test-key", request=request)
        return upload_response()

    def client_factory(**kwargs):
        client = real_client(transport=httpx.MockTransport(handler), **kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr(module.httpx, "AsyncClient", client_factory)
    assert await module.KieClient(api_key="test-key").upload_file(MEDIA) == IMAGE_URL
    assert len(requests) == len(clients) == 2
    assert all(client.is_closed for client in clients)
    filenames = []
    for request in requests:
        assert request.url.path == "/api/file-stream-upload"
        assert request.headers["authorization"] == "Bearer test-key"
        parsed = BytesParser(policy=policy.default).parsebytes(
            f"Content-Type: {request.headers['content-type']}\r\n\r\n".encode() + request.content
        )
        parts = {
            part.get_param("name", header="content-disposition"): part
            for part in parsed.iter_parts()
        }
        assert parts["file"].get_payload(decode=True) == MEDIA.bytes
        filename = parts["fileName"].get_payload(decode=True).decode()
        assert parts["file"].get_filename() == filename
        filenames.append(filename)
    assert filenames[0] == filenames[1]


@pytest.mark.asyncio
async def test_upload_transport_failure_is_bounded_and_does_not_expose_private_error():
    requests = []

    def handler(request):
        requests.append(request)
        raise httpx.ConnectError("private provider text test-key", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = module.KieClient(api_key="test-key", http_client=http)
        with pytest.raises(SmartRemakeError) as error:
            await client.upload_file(MEDIA)
    assert len(requests) == 2
    assert error.value.code == "KIE_UPLOAD_FAILED"
    assert isinstance(error.value.__cause__, httpx.ConnectError)
    assert "test-key" not in str(error.value.details)
    assert "test-key" not in str(error.value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(401, json={"code": 401}),
        httpx.Response(429, json={"code": 429}),
        httpx.Response(503, json={"code": 503}),
        httpx.Response(200, text="not JSON"),
        httpx.Response(200, json={"code": 200, "data": {}}),
    ],
)
async def test_upload_provider_response_errors_are_not_retried(response):
    requests = []
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: requests.append(request) or response,
        )
    ) as http:
        with pytest.raises(SmartRemakeError):
            await module.KieClient(api_key="test-key", http_client=http).upload_file(MEDIA)
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_upload_cancellation_is_not_retried():
    requests = []

    def handler(request):
        requests.append(request)
        raise asyncio.CancelledError()

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(asyncio.CancelledError):
            await module.KieClient(api_key="test-key", http_client=http).upload_file(MEDIA)
    assert len(requests) == 1
