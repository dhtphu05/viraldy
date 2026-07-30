from __future__ import annotations

import pytest

from viraldy.modules.assets.validators import validate_upload_declaration
from viraldy.platform.auth.policy import Permission, WorkspaceMembershipPolicy, WorkspaceRole
from viraldy.shared.errors.base import AppError, PayloadTooLargeError


def test_workspace_role_permissions() -> None:
    expected_permissions = {
        WorkspaceRole.OWNER: set(Permission),
        WorkspaceRole.ADMIN: set(Permission),
        WorkspaceRole.MEMBER: {
            Permission.WORKSPACE_READ,
            Permission.MEMBERS_READ,
            Permission.PRODUCT_READ,
            Permission.PRODUCT_WRITE,
            Permission.REFERENCE_READ,
            Permission.REFERENCE_WRITE,
            Permission.ANALYSIS_RUN,
            Permission.PATTERN_KIT_WRITE,
            Permission.VIRAL_KIT_WRITE,
            Permission.CAMPAIGN_PACK_WRITE,
            Permission.PREFLIGHT_RUN,
            Permission.RECOMMENDATION_ACT,
            Permission.FEEDBACK_WRITE,
        },
        WorkspaceRole.VIEWER: {
            Permission.WORKSPACE_READ,
            Permission.PRODUCT_READ,
            Permission.REFERENCE_READ,
        },
    }
    policy = WorkspaceMembershipPolicy()

    for role, expected in expected_permissions.items():
        actual = {
            permission for permission in Permission if policy.has_permission(role, permission)
        }
        assert actual == expected


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
