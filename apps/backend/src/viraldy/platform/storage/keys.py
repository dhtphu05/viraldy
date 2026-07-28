from __future__ import annotations

from uuid import UUID


def asset_source_key(workspace_id: UUID, asset_id: UUID, version_id: UUID) -> str:
    return f"workspaces/{workspace_id}/assets/{asset_id}/versions/{version_id}/source"
