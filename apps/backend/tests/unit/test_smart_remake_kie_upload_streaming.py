"""Reference uploads preserve their bytes without a single oversized TLS write."""

import asyncio
import io
import re
from email import policy
from email.parser import BytesParser

import httpx
import pytest

from viraldy.modules.smart_remake.engine import kie_client as module
from viraldy.modules.smart_remake.engine.errors import SmartRemakeError
from viraldy.modules.smart_remake.engine.schemas import UploadedMedia

IMAGE_URL = "https://8.8.8.8/image.png"
MEDIA = UploadedMedia(bytes=bytes(range(256)) * 5000, mime_type="image/png")


class UploadTransport(httpx.AsyncBaseTransport):
    def __init__(self, failure=None):
        self.failure = failure
        self.requests = []
        self.bodies = []
        self.chunk_sizes = []

    async def handle_async_request(self, request):
        self.requests.append(request)
        chunks = []
        self.bodies.append(chunks)
        async for chunk in request.stream:
            self.chunk_sizes.append(len(chunk))
            # Model the boundary at which the observed write timeout occurs;
            # MockTransport would coalesce the body and conceal this boundary.
            assert len(chunk) <= 65536
            chunks.append(chunk)
            if sum(map(len, chunks)) > 100000 and self.failure:
                if self.failure == "cancel":
                    raise asyncio.CancelledError()
                if self.failure == "always" or len(self.requests) == 1:
                    raise httpx.WriteTimeout("interrupted file transfer", request=request)
        return httpx.Response(200, json={"code": 200, "data": {"downloadUrl": IMAGE_URL}})


def multipart_parts(request, body):
    assert int(request.headers["content-length"]) == len(body)
    assert "transfer-encoding" not in request.headers
    parsed = BytesParser(policy=policy.default).parsebytes(
        f"Content-Type: {request.headers['content-type']}\r\n\r\n".encode() + body
    )
    return {
        part.get_param("name", header="content-disposition"): part for part in parsed.iter_parts()
    }


def track_streams(monkeypatch):
    streams = []

    def create_stream(data):
        stream = io.BytesIO(data)
        streams.append(stream)
        return stream

    monkeypatch.setattr(module, "BytesIO", create_stream, raising=False)
    return streams


@pytest.mark.asyncio
async def test_large_reference_upload_streams_exact_media_with_known_content_length(monkeypatch):
    streams = track_streams(monkeypatch)
    transport = UploadTransport()
    async with httpx.AsyncClient(transport=transport) as http:
        assert (
            await module.KieClient(api_key="test-key", http_client=http).upload_file(MEDIA)
            == IMAGE_URL
        )
    assert len(transport.requests) == len(streams) == 1
    assert streams[0].closed
    parts = multipart_parts(transport.requests[0], b"".join(transport.bodies[0]))
    assert parts["file"].get_payload(decode=True) == MEDIA.bytes
    assert parts["file"].get_content_type() == MEDIA.mime_type
    assert parts["file"].get_filename() == parts["fileName"].get_payload(decode=True).decode()
    assert parts["uploadPath"].get_payload(decode=True) == b"smart-remake/products"
    assert max(transport.chunk_sizes) == 65536


@pytest.mark.asyncio
async def test_partial_upload_retry_reopens_media_at_start_and_keeps_the_filename(monkeypatch):
    streams = track_streams(monkeypatch)
    transport = UploadTransport("once")
    async with httpx.AsyncClient(transport=transport) as http:
        assert (
            await module.KieClient(api_key="test-key", http_client=http).upload_file(MEDIA)
            == IMAGE_URL
        )
    assert len(transport.requests) == len(streams) == 2
    assert streams[0] is not streams[1] and all(stream.closed for stream in streams)
    bodies = [b"".join(chunks) for chunks in transport.bodies]
    assert len(bodies[0]) < len(bodies[1])
    filenames = [re.search(rb'filename="([^"]+)"', body).group(1) for body in bodies]
    assert filenames[0] == filenames[1]
    parts = multipart_parts(transport.requests[1], bodies[1])
    assert parts["file"].get_payload(decode=True) == MEDIA.bytes


@pytest.mark.asyncio
@pytest.mark.parametrize("failure,count", [("cancel", 1), ("always", 2)])
async def test_interrupted_upload_closes_every_stream_without_unbounded_retry(
    monkeypatch,
    failure,
    count,
):
    streams = track_streams(monkeypatch)
    transport = UploadTransport(failure)
    async with httpx.AsyncClient(transport=transport) as http:
        with pytest.raises(asyncio.CancelledError if failure == "cancel" else SmartRemakeError):
            await module.KieClient(api_key="test-key", http_client=http).upload_file(MEDIA)
    assert len(transport.requests) == len(streams) == count
    assert all(stream.closed for stream in streams)
