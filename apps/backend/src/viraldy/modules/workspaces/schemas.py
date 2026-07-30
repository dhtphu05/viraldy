from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from viraldy.platform.auth.policy import WorkspaceRole


class CreateWorkspaceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,254}$")


class UpdateWorkspaceRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9-]{1,254}$")
    status: str | None = Field(default=None, pattern=r"^(active|archived)$")


class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class WorkspaceMemberResponse(BaseModel):
    workspace_id: UUID
    user_id: UUID
    email: EmailStr
    display_name: str | None
    role: WorkspaceRole
    created_at: datetime

    model_config = {"from_attributes": True}


class AddWorkspaceMemberRequest(BaseModel):
    email: EmailStr
    role: WorkspaceRole = WorkspaceRole.MEMBER


class UpdateWorkspaceMemberRequest(BaseModel):
    role: WorkspaceRole
