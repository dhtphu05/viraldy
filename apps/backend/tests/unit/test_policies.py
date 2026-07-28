from __future__ import annotations

import pytest

from viraldy.modules.assets.validators import validate_upload_declaration
from viraldy.platform.auth.policy import Permission, WorkspaceMembershipPolicy, WorkspaceRole
from viraldy.shared.errors.base import AppError, PayloadTooLargeError


def test_workspace_role_permissions() -> None:
    policy = WorkspaceMembershipPolicy()
    assert policy.has_permission(WorkspaceRole.OWNER, Permission.MANAGE_MEMBERS)
    assert policy.has_permission(WorkspaceRole.EDITOR, Permission.CREATE_UPDATE_BUSINESS_RESOURCES)
    assert not policy.has_permission(
        WorkspaceRole.VIEWER,
        Permission.CREATE_UPDATE_BUSINESS_RESOURCES,
    )


def test_upload_declaration_rejects_unknown_mime() -> None:
    with pytest.raises(AppError, match="UNSUPPORTED_MIME_TYPE"):
        validate_upload_declaration(
            filename="asset.mov",
            declared_mime_type="application/x-msdownload",
            declared_size_bytes=10,
            asset_type="ugc",
            allowed_mime_types=["video/mp4"],
            max_size_bytes=100,
        )


def test_upload_declaration_rejects_large_file() -> None:
    with pytest.raises(PayloadTooLargeError):
        validate_upload_declaration(
            filename="asset.mp4",
            declared_mime_type="video/mp4",
            declared_size_bytes=101,
            asset_type="ugc",
            allowed_mime_types=["video/mp4"],
            max_size_bytes=100,
        )
