"""Server-only references to dedicated upload originals eligible for later cleanup."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from viraldy.modules.assets.public import AssetModel, AssetVersionModel
from viraldy.platform.storage.keys import asset_source_key
from viraldy.platform.storage.s3 import R2_OBJECT_MARKER

UPLOAD_EXPIRY_METADATA_KEY = "smartRemakeUploadExpiresAt"
_ROLES = {"reference_video", "product_image", "character_image"}


def _key(reference: Any, workspace_id: UUID) -> str | None:
    if not isinstance(reference, dict):
        return None
    role = reference.get("role")
    if not isinstance(role, str) or role not in _ROLES:
        return None
    try:
        asset_id = UUID(reference["assetId"])
        version_id = UUID(reference["assetVersionId"])
    except (KeyError, TypeError, ValueError, AttributeError):
        return None
    expected = (
        f"{asset_source_key(workspace_id, asset_id, version_id)}"
        f"{R2_OBJECT_MARKER}{version_id.hex}"
    )
    return expected if reference.get("storageKey") == expected else None


def staged_key_for_project(reference: Any, project_prefix: str) -> str | None:
    """Validate staged ownership separately; project-owned prefix rules stay unchanged."""
    parts = project_prefix.rstrip("/").split("/")
    if len(parts) != 4 or parts[0] != "workspaces" or parts[2] != "smart-remake":
        return None
    try:
        workspace_id = UUID(parts[1])
        UUID(parts[3])
    except ValueError:
        return None
    return _key(reference, workspace_id)


def staged_upload_reference(
    asset: AssetModel, version: AssetVersionModel, workspace_id: UUID
) -> dict[str, Any] | None:
    metadata = getattr(asset, "metadata_json", {}) or {}
    reference = {
        "assetId": str(asset.id),
        "assetVersionId": str(version.id),
        "role": metadata.get("smartRemakeUploadRole"),
        "storageKey": version.storage_key,
        "uploadExpiresAt": metadata.get(UPLOAD_EXPIRY_METADATA_KEY),
    }
    if asset.workspace_id != workspace_id or _key(reference, workspace_id) is None:
        return None
    return reference
