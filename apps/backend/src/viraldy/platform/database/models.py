from __future__ import annotations

from viraldy.modules.adaptations.models import AdaptationRunModel

# Import SQLAlchemy models so Alembic and metadata see all tables.
from viraldy.modules.assets.models import AssetModel, AssetVersionModel
from viraldy.modules.campaign_packs.models import CampaignPackModel, CampaignPackVersionModel
from viraldy.modules.creative_dna.models import CreativeDnaVersionModel
from viraldy.modules.identity.models import UserModel
from viraldy.modules.jobs.models import ProcessingJobModel
from viraldy.modules.media_analysis.models import EvidenceItemModel, MediaArtifactModel
from viraldy.modules.preflight.models import PreflightRunModel
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
    "CampaignPackModel",
    "CampaignPackVersionModel",
    "CreativeDnaVersionModel",
    "EvidenceItemModel",
    "MediaArtifactModel",
    "PreflightRunModel",
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
