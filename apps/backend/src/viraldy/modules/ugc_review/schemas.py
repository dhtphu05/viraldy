from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import UploadFile
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from viraldy.modules.domain_intelligence.public import (
    ReviewEvidence,
    UGCRecommendation,
    UGCReviewContext,
    UGCReviewResult,
)

UGCReviewJobStatus = Literal["queued", "running", "completed", "failed"]
UGCRecommendationAction = Literal[
    "accepted",
    "ignored",
    "not_applicable",
    "sent_to_creator",
    "marked_completed",
]


class UGCReviewApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)


class CreateUGCReviewForm(UGCReviewApiModel):
    asset_id: UUID | None = None
    asset_version_id: UUID | None = None
    market: str = Field(default="US", min_length=2, max_length=20)
    platform: str = Field(default="tiktok_shop", min_length=1, max_length=50)
    commerce_domain: Literal[
        "generic",
        "tiktok_shop_us",
        "pod_personalization",
        "dropshipping",
    ] = "generic"
    intended_use: Literal[
        "organic",
        "affiliate",
        "paid_candidate",
        "spark_candidate",
        "unknown",
    ] = "unknown"
    product_name: str | None = Field(default=None, min_length=1, max_length=300)
    product_category: str | None = Field(default=None, min_length=1, max_length=300)
    exact_variant_or_sku: str | None = Field(default=None, min_length=1, max_length=300)
    product_description: str | None = Field(default=None, min_length=1, max_length=5000)
    current_offer: str | None = Field(default=None, min_length=1, max_length=2000)
    verified_shipping_language: str | None = Field(default=None, min_length=1, max_length=2000)
    approved_personalization: str | None = Field(default=None, min_length=1, max_length=2000)
    physical_sample_available: bool | None = None
    creator_brief: str | None = Field(default=None, min_length=1, max_length=10000)
    material_connection: Literal["yes", "no", "unknown"] = "unknown"
    seller_notes: str | None = Field(default=None, min_length=1, max_length=5000)
    video_file: UploadFile | None = None

    @model_validator(mode="after")
    def validate_asset_reference_pair(self) -> CreateUGCReviewForm:
        if (self.asset_id is None) != (self.asset_version_id is None):
            raise ValueError("asset_id and asset_version_id must be provided together")
        return self

    def to_context(self) -> UGCReviewContext:
        return UGCReviewContext.model_validate(
            self.model_dump(exclude={"asset_id", "asset_version_id", "video_file"})
        )


class CreateUGCReviewRevisionForm(UGCReviewApiModel):
    asset_version_id: UUID | None = None
    video_file: UploadFile | None = None


class UGCReviewCreateResponse(UGCReviewApiModel):
    review_id: UUID
    status: Literal["queued"]
    mode: Literal["ugc_review_v1"]
    asset_id: UUID
    asset_version_id: UUID


class UGCReviewRevisionResponse(UGCReviewCreateResponse):
    parent_review_id: UUID


class UGCReviewStatusResponse(UGCReviewApiModel):
    review_id: UUID
    status: UGCReviewJobStatus
    progress: int = Field(ge=0, le=100)
    stage: str | None
    error_code: str | None = None
    error_message: str | None = None


class UGCReviewResultResponse(UGCReviewResult):
    asset_id: UUID
    asset_version_id: UUID


class RecordUGCRecommendationActionRequest(UGCReviewApiModel):
    action: UGCRecommendationAction
    reason: str | None = Field(default=None, max_length=2000)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("reason must not be blank")
        return stripped


class UGCRecommendationActionEventResponse(UGCReviewApiModel):
    id: UUID
    review_id: UUID
    recommendation_id: str
    action: UGCRecommendationAction
    reason: str | None
    created_at: str


class UGCComparisonFinding(UGCReviewApiModel):
    identity: str
    rule_code: str | None = None
    mistake_code: str | None = None
    title: str
    parent_recommendation_id: str | None = None
    revision_recommendation_id: str | None = None
    parent_evidence: list[ReviewEvidence] = Field(default_factory=list)
    revision_evidence: list[ReviewEvidence] = Field(default_factory=list)


class UGCRevisionComparisonResponse(UGCReviewApiModel):
    parent_review_id: str
    revision_review_id: str
    summary: str
    resolved: list[UGCComparisonFinding]
    still_open: list[UGCComparisonFinding]
    new_findings: list[UGCComparisonFinding]
    strengths_preserved: list[str]


__all__ = [
    "CreateUGCReviewForm",
    "CreateUGCReviewRevisionForm",
    "RecordUGCRecommendationActionRequest",
    "ReviewEvidence",
    "UGCComparisonFinding",
    "UGCRecommendation",
    "UGCRecommendationAction",
    "UGCRecommendationActionEventResponse",
    "UGCReviewContext",
    "UGCReviewCreateResponse",
    "UGCReviewJobStatus",
    "UGCReviewResultResponse",
    "UGCReviewRevisionResponse",
    "UGCReviewStatusResponse",
    "UGCRevisionComparisonResponse",
]
