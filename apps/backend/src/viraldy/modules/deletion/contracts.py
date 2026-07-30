from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DeletionResourceType(StrEnum):
    WORKSPACE = "workspace"
    PRODUCT = "product"
    ASSET = "asset"
    REFERENCE = "reference"
    CREATIVE_DNA = "creative_dna"
    PATTERN_KIT = "pattern_kit"
    VIRAL_KIT = "viral_kit"
    CAMPAIGN_PACK = "campaign_pack"


class DeletionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audit_id: UUID
    workspace_id: UUID
    resource_type: DeletionResourceType
    resource_id: UUID
    status: Literal["storage_cleanup_pending", "succeeded"]
    deleted_object_count: int
    deleted_row_counts: dict[str, int]
    completed_at: datetime | None
