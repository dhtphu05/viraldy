from __future__ import annotations

from viraldy.modules.ugc_review.comparison import compare_review_results
from viraldy.modules.ugc_review.models import (
    UGCReviewComparisonModel,
    UGCReviewFindingModel,
    UGCReviewRecommendationEventModel,
    UGCReviewResultModel,
    UGCReviewRevisionModel,
)
from viraldy.modules.ugc_review.repository import (
    SyncUGCReviewRepository,
    UGCReviewRepository,
    map_result_to_models,
    result_response_from_model,
)
from viraldy.modules.ugc_review.schemas import (
    CreateUGCReviewForm,
    CreateUGCReviewRevisionForm,
    RecordUGCRecommendationActionRequest,
    ReviewEvidence,
    UGCComparisonFinding,
    UGCRecommendation,
    UGCRecommendationActionEventResponse,
    UGCReviewCreateResponse,
    UGCReviewResultResponse,
    UGCReviewRevisionResponse,
    UGCReviewStatusResponse,
    UGCRevisionComparisonResponse,
)
from viraldy.modules.ugc_review.service import (
    UGCAssetVersion,
    UGCReviewService,
    UGCVideoIngestionPort,
    UGCVideoUpload,
)

__all__ = [
    "CreateUGCReviewForm",
    "CreateUGCReviewRevisionForm",
    "RecordUGCRecommendationActionRequest",
    "ReviewEvidence",
    "SyncUGCReviewRepository",
    "UGCAssetVersion",
    "UGCComparisonFinding",
    "UGCRecommendation",
    "UGCRecommendationActionEventResponse",
    "UGCReviewComparisonModel",
    "UGCReviewCreateResponse",
    "UGCReviewFindingModel",
    "UGCReviewRecommendationEventModel",
    "UGCReviewRepository",
    "UGCReviewResultModel",
    "UGCReviewResultResponse",
    "UGCReviewRevisionModel",
    "UGCReviewRevisionResponse",
    "UGCReviewService",
    "UGCReviewStatusResponse",
    "UGCRevisionComparisonResponse",
    "UGCVideoIngestionPort",
    "UGCVideoUpload",
    "compare_review_results",
    "map_result_to_models",
    "result_response_from_model",
]
