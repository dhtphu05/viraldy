from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from viraldy.modules.domain_intelligence.constants import ACTIVE_MVP_RULE_CODES
from viraldy.modules.domain_intelligence.evidence_adapter import adapt_media_evidence
from viraldy.modules.domain_intelligence.execution_brief import apply_execution_brief_synthesis
from viraldy.modules.domain_intelligence.execution_brief_contracts import (
    UGCExecutionBriefRecommendationPatchV1,
    UGCExecutionBriefSynthesisV1,
)
from viraldy.modules.domain_intelligence.importer import (
    ArtifactValidationError,
    PolicyPackImporter,
    ValidatedPolicyPack,
    validate_policy_pack,
)
from viraldy.modules.domain_intelligence.message_renderer import render_creator_message
from viraldy.modules.domain_intelligence.repository import (
    DomainIntelligenceRepository,
    SyncDomainIntelligenceRepository,
)
from viraldy.modules.domain_intelligence.schemas import (
    CommerceDomain,
    Confidence,
    DomainRule,
    EvaluationCandidate,
    ImportSummary,
    IntendedUse,
    MaterialConnection,
    NormalizedEvidence,
    NormalizedEvidenceBundle,
    OwnerRole,
    PolicyPackCounts,
    PolicyPackStatus,
    RecommendationGroup,
    RecommendationPriority,
    RecommendationTaskKind,
    ReviewEvidence,
    ReviewFixType,
    ReviewNextAction,
    ReviewTimeRange,
    UGCRecommendation,
    UGCReviewContext,
    UGCReviewResult,
    UGCRevisionComparison,
    UnknownState,
)
from viraldy.modules.domain_intelligence.selector import select_applicable_rules
from viraldy.modules.domain_intelligence.semantic_evaluator import (
    DeterministicSemanticFallback,
    SemanticEvaluator,
)
from viraldy.modules.domain_intelligence.service import evaluate_review


class DomainIntelligenceQueries:
    def __init__(self, session: AsyncSession) -> None:
        self._repository = DomainIntelligenceRepository(session)

    async def status(self) -> PolicyPackStatus:
        return await self._repository.get_status()

    async def select_rules(
        self,
        context: UGCReviewContext,
        evidence: NormalizedEvidenceBundle,
    ) -> list[DomainRule]:
        rules = await self._repository.list_active_rules()
        return select_applicable_rules(rules, context, evidence)


class SyncDomainIntelligenceQueries:
    def __init__(self, session: Session) -> None:
        self._repository = SyncDomainIntelligenceRepository(session)

    def status(self) -> PolicyPackStatus:
        return self._repository.get_status()

    def select_rules(
        self,
        context: UGCReviewContext,
        evidence: NormalizedEvidenceBundle,
    ) -> list[DomainRule]:
        rules = self._repository.list_active_rules()
        return select_applicable_rules(rules, context, evidence)


__all__ = [
    "ACTIVE_MVP_RULE_CODES",
    "ArtifactValidationError",
    "CommerceDomain",
    "Confidence",
    "DeterministicSemanticFallback",
    "DomainIntelligenceQueries",
    "DomainRule",
    "EvaluationCandidate",
    "ImportSummary",
    "IntendedUse",
    "MaterialConnection",
    "NormalizedEvidence",
    "NormalizedEvidenceBundle",
    "OwnerRole",
    "PolicyPackCounts",
    "PolicyPackImporter",
    "PolicyPackStatus",
    "RecommendationPriority",
    "RecommendationGroup",
    "RecommendationTaskKind",
    "ReviewEvidence",
    "ReviewFixType",
    "ReviewNextAction",
    "ReviewTimeRange",
    "SemanticEvaluator",
    "SyncDomainIntelligenceQueries",
    "UGCRecommendation",
    "UGCExecutionBriefRecommendationPatchV1",
    "UGCExecutionBriefSynthesisV1",
    "UGCRevisionComparison",
    "UGCReviewContext",
    "UGCReviewResult",
    "UnknownState",
    "ValidatedPolicyPack",
    "adapt_media_evidence",
    "apply_execution_brief_synthesis",
    "evaluate_review",
    "render_creator_message",
    "select_applicable_rules",
    "validate_policy_pack",
]
