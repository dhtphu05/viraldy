"""Access original generated images using the same bindings as private previews."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from viraldy.shared.errors.base import AppError, NotFoundError

from .generation_progress import _image_key, _images, _plan


async def generated_image_download(
    repair: Any,
    workspace_id: UUID,
    project_id: UUID,
    operation_id: UUID,
    request_hash: str,
) -> dict[str, str]:
    row = await repair.repository.project(workspace_id, project_id)
    operation = await repair.repository.operation(workspace_id, project_id, operation_id)
    plan = _plan(row, operation, workspace_id)
    if plan is None:
        raise NotFoundError(
            "SMART_REMAKE_GENERATED_IMAGE_NOT_FOUND", "Generated image was not found."
        )
    for group in plan["groups"]:
        for image in _images(row, operation, group):
            if image.get("requestHash") != request_hash:
                continue
            key = _image_key(row, operation, image)
            extension = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}.get(
                str(image.get("mimeType"))
            )
            if key is None or extension is None:
                break
            role = image.get("frameRole") or "reference"
            filename = f"smart-remake-{role}-{request_hash[:12]}.{extension}"
            try:
                url = await repair.media.download_url(key, filename)
            except Exception as exc:
                raise AppError(
                    "SMART_REMAKE_MEDIA_DOWNLOAD_UNAVAILABLE", "Image download is unavailable.", 503
                ) from exc
            return {"url": str(url), "filename": filename}
    raise NotFoundError("SMART_REMAKE_GENERATED_IMAGE_NOT_FOUND", "Generated image was not found.")
