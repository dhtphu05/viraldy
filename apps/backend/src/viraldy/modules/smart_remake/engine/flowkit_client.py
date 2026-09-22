import base64
from typing import Any

import httpx

from .config import get_flowkit_url
from .errors import SmartRemakeError
from .guards import assert_allowed_endpoint


class FlowKitClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or get_flowkit_url()).rstrip("/")

    async def _json(
        self,
        method: str,
        path: str,
        *,
        body: Any | None = None,
        code: str = "FLOWKIT_INVALID_RESPONSE",
    ) -> Any:
        assert_allowed_endpoint(path)
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.request(
                    method,
                    f"{self.base_url}{path}",
                    json=body if method != "GET" else None,
                    headers={"Content-Type": "application/json"},
                )
        except httpx.HTTPError as exc:
            raise SmartRemakeError(
                "FlowKit is unavailable.",
                "FLOWKIT_UNAVAILABLE",
                {"pathname": path, "cause": str(exc)},
            ) from exc

        text = response.text
        try:
            payload = response.json() if text.strip() else {}
        except ValueError as exc:
            raise SmartRemakeError(
                f"FlowKit returned invalid JSON for {path}.",
                code,
                {"pathname": path, "status": response.status_code},
            ) from exc

        if response.status_code >= 400:
            message = _error_message(payload) or f"FlowKit HTTP {response.status_code} for {path}."
            error_code = _flowkit_error_code(response.status_code, payload, code)
            if error_code == "FLOWKIT_USER_QUOTA_REACHED":
                message = "Google Flow user quota is exhausted. Check Flow credits or wait for the quota reset before rendering again."
            elif error_code == "FLOWKIT_RATE_LIMITED":
                message = "Google Flow is rate-limiting requests. Wait briefly and try again."
            raise SmartRemakeError(
                message,
                error_code,
                {"pathname": path, "status": response.status_code, "flowKitError": payload},
            )
        return payload

    async def check_health(self) -> dict[str, Any]:
        return await self._json("GET", "/health", code="FLOWKIT_UNAVAILABLE")

    async def check_google_flow_auth(self) -> None:
        payload = await self._json("GET", "/api/flow/credits", code="FLOWKIT_AUTH_INVALID")
        if isinstance(payload, dict) and payload.get("error"):
            raise SmartRemakeError(
                "Google Flow authentication is invalid. Refresh Google Flow in Chrome, confirm you are signed in, then retry Smart Remake render.",
                "FLOWKIT_AUTH_INVALID",
                {"flowKitError": payload["error"]},
            )

    async def create_project(self, payload: dict[str, Any]) -> dict[str, Any]:
        return _require_id(
            await self._json("POST", "/api/projects", body=payload, code="FLOWKIT_PROJECT_CREATE_FAILED"),
            "FLOWKIT_PROJECT_CREATE_FAILED",
            "FlowKit project create",
        )

    async def upload_product_image(
        self,
        *,
        bytes_data: bytes,
        mime_type: str,
        project_id: str,
        file_name: str,
    ) -> dict[str, Any]:
        payload = await self._json(
            "POST",
            "/api/flow/upload-image-base64",
            body={
                "base64": base64.b64encode(bytes_data).decode("ascii"),
                "mime_type": mime_type,
                "project_id": project_id,
                "file_name": file_name,
            },
            code="FLOWKIT_PRODUCT_UPLOAD_FAILED",
        )
        if not isinstance(payload, dict) or not payload.get("media_id"):
            raise SmartRemakeError(
                "FlowKit product image upload response is missing media_id.",
                "FLOWKIT_PRODUCT_UPLOAD_FAILED",
                {"payload": payload},
            )
        return payload

    async def list_project_characters(self, project_id: str) -> list[dict[str, Any]]:
        payload = await self._json(
            "GET",
            f"/api/projects/{project_id}/characters",
            code="FLOWKIT_INVALID_RESPONSE",
        )
        if not isinstance(payload, list):
            raise SmartRemakeError("FlowKit characters response must be a list.", "FLOWKIT_INVALID_RESPONSE")
        return [item for item in payload if isinstance(item, dict)]

    async def update_project_character(
        self,
        project_id: str,
        character_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._json(
            "PATCH",
            f"/api/characters/{character_id}",
            body={"project_id": project_id, **payload},
            code="FLOWKIT_CHARACTER_PATCH_FAILED",
        )

    async def create_video(self, payload: dict[str, Any]) -> dict[str, Any]:
        return _require_id(
            await self._json("POST", "/api/videos", body=payload, code="FLOWKIT_VIDEO_CREATE_FAILED"),
            "FLOWKIT_VIDEO_CREATE_FAILED",
            "FlowKit video create",
        )

    async def create_scene(self, payload: dict[str, Any]) -> dict[str, Any]:
        return _require_id(
            await self._json("POST", "/api/scenes", body=payload, code="FLOWKIT_SCENE_CREATE_FAILED"),
            "FLOWKIT_SCENE_CREATE_FAILED",
            "FlowKit scene create",
        )

    async def create_batch_requests(self, payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result = await self._json(
            "POST",
            "/api/requests/batch",
            body={"requests": payload},
            code="FLOWKIT_INVALID_BATCH_STATUS",
        )
        if isinstance(result, dict):
            result = result.get("requests") or result.get("data") or result.get("items")
        if not isinstance(result, list):
            raise SmartRemakeError("FlowKit batch response must be a list.", "FLOWKIT_INVALID_BATCH_STATUS")
        return [_require_id(item, "FLOWKIT_INVALID_BATCH_STATUS", "FlowKit batch request") for item in result if isinstance(item, dict)]

    async def get_request_status(self, request_id: str) -> dict[str, Any]:
        return _require_id(
            await self._json("GET", f"/api/requests/{request_id}", code="FLOWKIT_INVALID_BATCH_STATUS"),
            "FLOWKIT_INVALID_BATCH_STATUS",
            "FlowKit request status",
        )

    async def list_scenes(self, video_id: str) -> list[dict[str, Any]]:
        payload = await self._json(
            "GET",
            f"/api/scenes?video_id={video_id}",
            code="FLOWKIT_INVALID_RESPONSE",
        )
        if not isinstance(payload, list):
            raise SmartRemakeError("FlowKit scenes response must be a list.", "FLOWKIT_INVALID_RESPONSE")
        return [item for item in payload if isinstance(item, dict)]


def _require_id(payload: Any, code: str, label: str) -> dict[str, Any]:
    if not isinstance(payload, dict) or not isinstance(payload.get("id"), str) or not payload["id"].strip():
        raise SmartRemakeError(f"{label} response is missing id.", code, {"payload": payload})
    return payload


def _error_message(payload: Any) -> str | None:
    if isinstance(payload, str) and payload.strip():
        return payload.strip()
    if not isinstance(payload, dict):
        return None
    for key in ("message", "detail", "error"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        nested = _error_message(value)
        if nested:
            return nested
    return None


def _flowkit_error_code(status_code: int, payload: Any, fallback: str) -> str:
    if status_code in (401, 403):
        return "FLOWKIT_AUTH_INVALID"
    if status_code == 429:
        text = repr(payload).upper()
        if any(marker in text for marker in ("PUBLIC_ERROR_USER_QUOTA_REACHED", "USER_QUOTA_REACHED", "RESOURCE_EXHAUSTED", "QUOTA_EXCEEDED")):
            return "FLOWKIT_USER_QUOTA_REACHED"
        return "FLOWKIT_RATE_LIMITED"
    return fallback
