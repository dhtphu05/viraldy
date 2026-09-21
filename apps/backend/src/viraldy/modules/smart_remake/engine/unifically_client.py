from typing import Any

import httpx

from .config import (
    get_unifically_api_base_url,
    get_unifically_api_key,
    get_unifically_files_base_url,
)
from .errors import SmartRemakeError
from .schemas import UploadedMedia


class UnificallyClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        api_base_url: str | None = None,
        files_base_url: str | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else get_unifically_api_key()
        self.api_base_url = (api_base_url or get_unifically_api_base_url()).rstrip("/")
        self.files_base_url = (files_base_url or get_unifically_files_base_url()).rstrip("/")
        if not self.api_key:
            raise SmartRemakeError(
                "UNIFICALLY_API_KEY is required when Smart Remake provider is unifically.",
                "UNIFICALLY_NOT_CONFIGURED",
            )

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    async def upload_file(self, media: UploadedMedia) -> str:
        filename = media.file_name or _default_file_name(media.mime_type)
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.put(
                    f"{self.files_base_url}/upload",
                    headers=self._headers(),
                    files={"file": (filename, media.bytes, media.mime_type)},
                )
        except httpx.HTTPError as exc:
            raise SmartRemakeError(
                "Unifically file upload failed.",
                "UNIFICALLY_UPLOAD_FAILED",
                {"cause": str(exc)},
            ) from exc
        payload = _response_payload(response, "UNIFICALLY_UPLOAD_FAILED")
        file_url = payload.get("file_url") if isinstance(payload, dict) else None
        if not isinstance(file_url, str) or not file_url.strip():
            raise SmartRemakeError(
                "Unifically upload response is missing file_url.",
                "UNIFICALLY_UPLOAD_FAILED",
                {"payload": payload},
            )
        return file_url

    async def create_task(self, *, model: str, input_data: dict[str, Any]) -> dict[str, Any]:
        payload = await self._json(
            "POST",
            "/v1/tasks",
            body={"model": model, "input": input_data},
            code="UNIFICALLY_TASK_CREATE_FAILED",
        )
        task_id = payload.get("task_id") if isinstance(payload, dict) else None
        if not isinstance(task_id, str) or not task_id.strip():
            raise SmartRemakeError(
                "Unifically create task response is missing task_id.",
                "UNIFICALLY_TASK_CREATE_FAILED",
                {"payload": payload},
            )
        return payload

    async def get_task(self, task_id: str) -> dict[str, Any]:
        payload = await self._json("GET", f"/v1/tasks/{task_id}", code="UNIFICALLY_TASK_STATUS_FAILED")
        if not isinstance(payload, dict):
            raise SmartRemakeError(
                "Unifically task status response must be an object.",
                "UNIFICALLY_TASK_STATUS_FAILED",
                {"payload": payload},
            )
        payload.setdefault("task_id", task_id)
        return payload

    async def download_file(self, url: str) -> bytes:
        try:
            async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
                response = await client.get(url)
        except httpx.HTTPError as exc:
            raise SmartRemakeError(
                "Could not download Unifically output video.",
                "UNIFICALLY_OUTPUT_DOWNLOAD_FAILED",
                {"url": url, "cause": str(exc)},
            ) from exc
        if response.status_code >= 400:
            raise SmartRemakeError(
                f"Could not download Unifically output video. HTTP {response.status_code}.",
                "UNIFICALLY_OUTPUT_DOWNLOAD_FAILED",
                {"url": url, "status": response.status_code},
            )
        return response.content

    async def _json(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        code: str,
    ) -> Any:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.request(
                    method,
                    f"{self.api_base_url}{path}",
                    json=body if method != "GET" else None,
                    headers={**self._headers(), "Content-Type": "application/json"},
                )
        except httpx.HTTPError as exc:
            raise SmartRemakeError(
                "Unifically API is unavailable.",
                "UNIFICALLY_UNAVAILABLE",
                {"pathname": path, "cause": str(exc)},
            ) from exc
        return _response_payload(response, code)


def _response_payload(response: httpx.Response, code: str) -> Any:
    try:
        payload = response.json() if response.text.strip() else {}
    except ValueError as exc:
        raise SmartRemakeError(
            "Unifically returned invalid JSON.",
            "UNIFICALLY_INVALID_RESPONSE",
            {"status": response.status_code},
        ) from exc

    if response.status_code >= 400:
        raise SmartRemakeError(
            _error_message(payload) or f"Unifically HTTP {response.status_code}.",
            _http_error_code(response.status_code, code),
            {"status": response.status_code, "unificallyError": payload},
        )
    if isinstance(payload, dict) and payload.get("success") is False:
        raise SmartRemakeError(
            _error_message(payload) or "Unifically request failed.",
            code,
            {"status": response.status_code, "unificallyError": payload},
        )
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def _http_error_code(status_code: int, fallback: str) -> str:
    if status_code in (401, 403):
        return "UNIFICALLY_AUTH_FAILED"
    if status_code == 429:
        return "UNIFICALLY_RATE_LIMITED"
    if status_code in (400, 422):
        return "UNIFICALLY_VALIDATION_FAILED"
    return fallback


def _error_message(payload: Any) -> str | None:
    if isinstance(payload, str) and payload.strip():
        return payload.strip()
    if not isinstance(payload, dict):
        return None
    for key in ("message", "error_message", "error", "detail"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        nested = _error_message(value)
        if nested:
            return nested
    data = payload.get("data")
    return _error_message(data)


def _default_file_name(mime_type: str) -> str:
    if mime_type == "image/png":
        return "smart_remake_product.png"
    if mime_type == "image/webp":
        return "smart_remake_product.webp"
    return "smart_remake_product.jpg"
