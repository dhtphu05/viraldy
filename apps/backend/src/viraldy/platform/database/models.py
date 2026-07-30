from __future__ import annotations

from viraldy.modules.adaptations.models import AdaptationRunModel
from viraldy.modules.ai_gateway.models import AiModelRunModel

# Import SQLAlchemy models so Alembic and metadata see all tables.
from viraldy.modules.assets.models import AssetModel, AssetVersionModel
from viraldy.modules.campaign_packs.models import CampaignPackModel, CampaignPackVersionModel
from viraldy.modules.creative_dna.models import CreativeDnaVersionModel
from viraldy.modules.feedback.models import FeedbackItemModel
from viraldy.modules.identity.models import UserModel
from viraldy.modules.jobs.models import ProcessingJobEventModel, ProcessingJobModel
from viraldy.modules.media_analysis.models import EvidenceItemModel, MediaArtifactModel
from viraldy.modules.pattern_kits.models import (
    PatternKitActionModel,
    PatternKitEvidenceLinkModel,
    PatternKitModel,
    PatternKitSourceModel,
    PatternKitVersionModel,
)
from viraldy.modules.preflight.models import PreflightRunModel
from viraldy.modules.product_events.models import ProductEventModel
from viraldy.modules.products.models import ProductModel
from viraldy.modules.recommendations.models import (
    RecommendationActionModel,
    RecommendationModel,
)
from viraldy.modules.reference_boards.models import ReferenceBoardModel
from viraldy.modules.references.models import ReferenceModel
from viraldy.modules.tiktok_scorer.models import TikTokScoreRunModel
from viraldy.modules.workspaces.models import WorkspaceMemberModel, WorkspaceModel

__all__ = [
    "AdaptationRunModel",
    "AssetModel",
    "AssetVersionModel",
    "AiModelRunModel",
    "CampaignPackModel",
    "CampaignPackVersionModel",
    "CreativeDnaVersionModel",
    "EvidenceItemModel",
    "FeedbackItemModel",
    "MediaArtifactModel",
    "PatternKitActionModel",
    "PatternKitEvidenceLinkModel",
    "PatternKitModel",
    "PatternKitSourceModel",
    "PatternKitVersionModel",
    "PreflightRunModel",
    "ProductEventModel",
    "ProcessingJobEventModel",
    "ProcessingJobModel",
    "ProductModel",
    "ReferenceBoardModel",
    "ReferenceModel",
    "RecommendationActionModel",
    "RecommendationModel",
    "TikTokScoreRunModel",
    "UserModel",
    "WorkspaceMemberModel",
    "WorkspaceModel",
]
