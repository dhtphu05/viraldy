from __future__ import annotations

from enum import StrEnum


class WorkspaceRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class Permission(StrEnum):
    READ = "read"
    MANAGE_MEMBERS = "manage_members"
    MANAGE_BUSINESS_RESOURCES = "manage_business_resources"
    CREATE_UPDATE_BUSINESS_RESOURCES = "create_update_business_resources"


ROLE_PERMISSIONS: dict[WorkspaceRole, set[Permission]] = {
    WorkspaceRole.OWNER: set(Permission),
    WorkspaceRole.ADMIN: {
        Permission.READ,
        Permission.MANAGE_MEMBERS,
        Permission.MANAGE_BUSINESS_RESOURCES,
        Permission.CREATE_UPDATE_BUSINESS_RESOURCES,
    },
    WorkspaceRole.EDITOR: {
        Permission.READ,
        Permission.CREATE_UPDATE_BUSINESS_RESOURCES,
    },
    WorkspaceRole.VIEWER: {Permission.READ},
}


class WorkspaceMembershipPolicy:
    def has_permission(self, role: WorkspaceRole, permission: Permission) -> bool:
        return permission in ROLE_PERMISSIONS[role]
