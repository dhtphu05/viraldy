from __future__ import annotations

# Import SQLAlchemy models so Alembic and metadata see all tables.
from viraldy.modules.assets.models import AssetModel, AssetVersionModel
from viraldy.modules.identity.models import UserModel
from viraldy.modules.jobs.models import ProcessingJobModel
from viraldy.modules.products.models import ProductModel
from viraldy.modules.recommendations.models import (
    RecommendationActionModel,
    RecommendationModel,
)
from viraldy.modules.workspaces.models import WorkspaceMemberModel, WorkspaceModel

__all__ = [
    "AssetModel",
    "AssetVersionModel",
    "ProcessingJobModel",
    "ProductModel",
    "RecommendationActionModel",
    "RecommendationModel",
    "UserModel",
    "WorkspaceMemberModel",
    "WorkspaceModel",
]
