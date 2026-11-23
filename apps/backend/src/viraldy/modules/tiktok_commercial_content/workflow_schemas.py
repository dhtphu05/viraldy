from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from viraldy.modules.product_events.contracts import ProductEventType

DecisionAction = Literal["TEST", "FIX", "RESHOOT", "SKIP", "INSUFFICIENT_EVIDENCE"]
SellerResponse = Literal["accepted", "rejected", "modified", "ignored"]
FamilyScope = Literal["MARKET", "WORKSPACE"]
EntryFlow = Literal[
    "FREE_SCORE", "MARKET_EXPLORER", "PRODUCT_FIRST", "SHARE_SNAPSHOT",
    "FOUNDER_CLINIC", "PARTNER", "OTHER",
]


class PatternSummaryRequest(BaseModel):
    market: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=160)
    min_assets: int = Field(default=3, ge=1, le=100)
    min_families: int = Field(default=1, ge=0, le=100)


class FamilyRefreshRequest(BaseModel):
    scope: FamilyScope = "MARKET"
    asset_ids: list[UUID] = Field(default_factory=list, max_length=200)


class FamilyCandidateQuery(BaseModel):
    scope: FamilyScope = "MARKET"
    limit: int = Field(default=100, ge=1, le=200)


class DirectionSelectRequest(BaseModel):
    status: Literal["selected", "available"] = "selected"


class BatchReviewCreateRequest(BaseModel):
    objective: str = Field(min_length=1, max_length=255)
    asset_ids: list[UUID] = Field(min_length=1, max_length=100)
    product_id: UUID | None = None


class SellerResponseRequest(BaseModel):
    response: SellerResponse
    action: DecisionAction
    feedback: str | None = Field(default=None, max_length=2000)


class SnapshotCreateRequest(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=255)
    snapshot_type: Literal["creative_pattern", "creative_family", "category_pulse", "teardown"]
    title: str = Field(min_length=1, max_length=255)
    category: str | None = Field(default=None, max_length=160)
    market: str | None = Field(default=None, max_length=100)
    date_range: dict[str, str] = Field(default_factory=dict)
    payload: dict[str, object]


class AnalyticsAttributionRequest(BaseModel):
    entry_flow: EntryFlow
    utm: dict[str, str] = Field(default_factory=dict)


class AnalyticsEventRequest(BaseModel):
    event_type: ProductEventType
    subject_type: str | None = Field(default=None, max_length=100)
    subject_id: UUID | None = None
    payload: dict[str, object] = Field(default_factory=dict)
    attribution_id: UUID | None = None
    entry_flow: EntryFlow | None = None
