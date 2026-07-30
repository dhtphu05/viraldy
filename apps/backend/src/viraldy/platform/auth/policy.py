from __future__ import annotations

from enum import StrEnum


class WorkspaceRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class Permission(StrEnum):
    WORKSPACE_READ = "workspace.read"
    WORKSPACE_MANAGE = "workspace.manage"
    MEMBERS_READ = "members.read"
    MEMBERS_MANAGE = "members.manage"
    PRODUCT_READ = "product.read"
    PRODUCT_WRITE = "product.write"
    REFERENCE_READ = "reference.read"
    REFERENCE_WRITE = "reference.write"
    ANALYSIS_RUN = "analysis.run"
    PATTERN_KIT_WRITE = "pattern_kit.write"
    VIRAL_KIT_WRITE = "viral_kit.write"
    CAMPAIGN_PACK_WRITE = "campaign_pack.write"
    PREFLIGHT_RUN = "preflight.run"
    RECOMMENDATION_ACT = "recommendation.act"
    FEEDBACK_WRITE = "feedback.write"
    DATA_EXPORT = "data.export"
    DATA_DELETE = "data.delete"


ROLE_PERMISSIONS: dict[WorkspaceRole, set[Permission]] = {
    WorkspaceRole.OWNER: set(Permission),
    WorkspaceRole.ADMIN: {
        Permission.WORKSPACE_READ,
        Permission.WORKSPACE_MANAGE,
        Permission.MEMBERS_READ,
        Permission.MEMBERS_MANAGE,
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
        Permission.DATA_EXPORT,
        Permission.DATA_DELETE,
    },
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


class WorkspaceMembershipPolicy:
    def has_permission(self, role: WorkspaceRole, permission: Permission) -> bool:
        return permission in ROLE_PERMISSIONS[role]


def normalize_workspace_role(value: str) -> WorkspaceRole:
    if value == "editor":
        return WorkspaceRole.MEMBER
    return WorkspaceRole(value)
