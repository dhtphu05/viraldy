from __future__ import annotations

import pytest

from viraldy.modules.assets.validators import validate_upload_declaration
from viraldy.platform.auth.policy import Permission, WorkspaceMembershipPolicy, WorkspaceRole
from viraldy.shared.errors.base import AppError, PayloadTooLargeError


def test_workspace_role_permissions() -> None:
    policy = WorkspaceMembershipPolicy()
    assert policy.has_permission(WorkspaceRole.OWNER, Permission.DATA_DELETE)
    assert policy.has_permission(WorkspaceRole.ADMIN, Permission.DATA_EXPORT)
    assert policy.has_permission(WorkspaceRole.MEMBER, Permission.PRODUCT_WRITE)
    assert policy.has_permission(WorkspaceRole.MEMBER, Permission.FEEDBACK_WRITE)
    assert not policy.has_permission(WorkspaceRole.MEMBER, Permission.DATA_EXPORT)
    assert not policy.has_permission(WorkspaceRole.MEMBER, Permission.DATA_DELETE)
    assert policy.has_permission(WorkspaceRole.VIEWER, Permission.WORKSPACE_READ)
    assert policy.has_permission(WorkspaceRole.VIEWER, Permission.PRODUCT_READ)
    assert not policy.has_permission(WorkspaceRole.VIEWER, Permission.PRODUCT_WRITE)
    assert not policy.has_permission(WorkspaceRole.VIEWER, Permission.RECOMMENDATION_ACT)


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
