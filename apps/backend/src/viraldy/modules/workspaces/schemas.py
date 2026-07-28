from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class CreateWorkspaceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,254}$")


class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    status: str

    model_config = {"from_attributes": True}
