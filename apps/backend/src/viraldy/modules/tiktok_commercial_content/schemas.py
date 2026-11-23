from __future__ import annotations

from datetime import date, timedelta
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

SearchType = Literal["exact_phrase", "fuzzy_phrase"]
ProviderEntityType = Literal["ad", "advertiser", "commercial_content"]
SUPPORTED_COUNTRY_CODES = frozenset(
    {
        "AT",
        "BE",
        "BG",
        "CH",
        "CY",
        "CZ",
        "DE",
        "DK",
        "EE",
        "ES",
        "FI",
        "FR",
        "GB",
        "GR",
        "HR",
        "HU",
        "IE",
        "IS",
        "IT",
        "LI",
        "LT",
        "LU",
        "LV",
        "MT",
        "NL",
        "NO",
        "PL",
        "PT",
        "RO",
        "SE",
        "SI",
        "SK",
    }
)


class TikTokRequestBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _normalize_country_code(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    if not value.isalpha():
        raise ValueError(f"{field_name} must use a two-letter country code")
    normalized = value.upper()
    if normalized not in SUPPORTED_COUNTRY_CODES:
        raise ValueError(
            f"{field_name} must be supported by TikTok Commercial Content API "
            "(EU/EEA, GB, or CH)"
        )
    return normalized


class DateRange(TikTokRequestBase):
    min: date
    max: date

    @model_validator(mode="after")
    def validate_range(self) -> DateRange:
        if self.max < self.min:
            raise ValueError("date max must be on or after date min")
        if self.min < date(2022, 10, 1):
            raise ValueError("TikTok Commercial Content API dates must be on or after 2022-10-01")
        if self.max >= date.today():
            latest_supported_date = date.today() - timedelta(days=1)
            raise ValueError(
                "TikTok Commercial Content API dates must end by "
                f"{latest_supported_date.isoformat()}"
            )
        return self


class ReachRange(TikTokRequestBase):
    min: str | None = None
    max: str | None = None

    @model_validator(mode="after")
    def validate_sizes(self) -> ReachRange:
        for value in (self.min, self.max):
            if value is not None and not _valid_size(value):
                raise ValueError("reach values must use an integer K, M, or B suffix")
        return self


class AdSearchRequest(TikTokRequestBase):
    search_term: str | None = Field(default=None, max_length=50)
    search_type: SearchType = "fuzzy_phrase"
    date_range: DateRange
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    advertiser_business_ids: list[int] = Field(default_factory=list, max_length=50)
    reach_range: ReachRange | None = None
    max_count: int = Field(default=20, ge=1, le=50)
    cursor: str | None = None

    @model_validator(mode="after")
    def normalize_search_term(self) -> AdSearchRequest:
        if self.search_term is not None and not self.search_term.strip():
            raise ValueError("search_term must not be blank")
        self.country_code = _normalize_country_code(self.country_code, "country_code")
        return self


class AdvertiserSearchRequest(TikTokRequestBase):
    search_term: str = Field(min_length=1, max_length=50)
    max_count: int = Field(default=20, ge=1, le=50)


class CommercialContentSearchRequest(TikTokRequestBase):
    date_range: DateRange
    creator_country_code: str | None = Field(default=None, min_length=2, max_length=2)
    creator_usernames: list[str] = Field(default_factory=list, max_length=50)
    max_count: int = Field(default=20, ge=1, le=50)
    cursor: str | None = None

    @model_validator(mode="after")
    def normalize_creator_country_code(self) -> CommercialContentSearchRequest:
        self.creator_country_code = _normalize_country_code(
            self.creator_country_code, "creator_country_code"
        )
        return self


class AdReportRequest(TikTokRequestBase):
    date_range: DateRange
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    advertiser_business_ids: list[int] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def normalize_country_code(self) -> AdReportRequest:
        self.country_code = _normalize_country_code(self.country_code, "country_code")
        return self


class MarketSignal(TikTokRequestBase):
    label: Literal[
        "MARKET_OBSERVED",
        "MARKET_PREVALENT",
        "PUBLIC_DISTRIBUTION_SIGNAL",
    ]
    scope: Literal["public_market"] = "public_market"
    limitations: list[str] = Field(default_factory=list)


class TikTokMedia(TikTokRequestBase):
    url: str | None
    media_type: Literal["video", "image"]


class TikTokAdvertiser(TikTokRequestBase):
    business_id: str
    business_name: str | None = None
    country_code: str | None = None
    paid_for_by: str | None = None
    follower_count: int | None = None
    avatar_url: str | None = None
    profile_url: str | None = None


class TikTokAd(TikTokRequestBase):
    id: str
    first_shown_date: date | None = None
    last_shown_date: date | None = None
    status: str | None = None
    status_statement: str | None = None
    videos: list[TikTokMedia] = Field(default_factory=list)
    image_urls: list[str] = Field(default_factory=list)
    image_count: int = 0
    reach: str | None = None
    title: str | None = None
    external_url: str | None = None
    download_url: str | None = None
    call_to_action: str | None = None
    advertising_objective: str | None = None
    targeting_info: dict[str, object] | None = None
    moderation_metadata: dict[str, object] | None = None


class TikTokAdResult(TikTokRequestBase):
    source_id: UUID
    asset_id: UUID | None = None
    provider_entity_id: str
    ad: TikTokAd
    advertiser: TikTokAdvertiser | None = None
    market_signal: MarketSignal
    intelligence_status: Literal[
        "NOT_ANALYZED", "QUEUED", "PROCESSING", "PARTIAL", "READY", "FAILED"
    ] = "NOT_ANALYZED"
    media_state: Literal[
        "METADATA_ONLY", "DIRECT_STREAM_AVAILABLE", "AVAILABLE_ON_SAVE", "READY"
    ] = "METADATA_ONLY"


class TikTokAdvertiserResult(TikTokRequestBase):
    business_id: str
    business_name: str | None = None
    country_code: str | None = None


class CommercialContentResult(TikTokRequestBase):
    source_id: UUID
    provider_entity_id: str
    create_date: date | None = None
    label: str | None = None
    brand_names: list[str] = Field(default_factory=list)
    creator_username: str | None = None
    video_id: str | None = None
    video_status: str | None = None
    video_url: str | None = None
    cover_image_url: str | None = None
    market_signal: MarketSignal


class CursorPage(TikTokRequestBase):
    has_more: bool
    next_cursor: str | None = None


class TikTokAdSearchResponse(TikTokRequestBase):
    results: list[TikTokAdResult]
    page: CursorPage


class TikTokAdvertiserSearchResponse(TikTokRequestBase):
    results: list[TikTokAdvertiserResult]


class CommercialContentSearchResponse(TikTokRequestBase):
    results: list[CommercialContentResult]
    page: CursorPage


class SaveReferenceRequest(TikTokRequestBase):
    board_id: UUID
    product_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=2000)


class AttachProductRequest(TikTokRequestBase):
    product_id: UUID | None = None


class GenerateDirectionsRequest(TikTokRequestBase):
    product_id: UUID
    objective: str = Field(min_length=1, max_length=255)
    target_market: str = Field(min_length=1, max_length=100)
    target_buyer: dict[str, object] = Field(default_factory=dict)
    constraints: dict[str, object] = Field(default_factory=dict)


class SaveReferenceResponse(TikTokRequestBase):
    reference_id: UUID
    asset_id: UUID
    asset_version_id: UUID
    import_job_id: UUID | None = None
    media_type: Literal["video", "image"] | None = None
    status: str


def _valid_size(value: str) -> bool:
    number, suffix = value[:-1], value[-1].upper()
    return number.isdigit() and suffix in {"K", "M", "B"} and int(number) < 1000
