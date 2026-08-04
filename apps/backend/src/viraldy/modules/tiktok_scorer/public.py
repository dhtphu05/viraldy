from __future__ import annotations

from viraldy.modules.media_analysis.public import EvidenceItemModel
from viraldy.modules.tiktok_scorer.contracts import TikTokScoreResultV2
from viraldy.modules.tiktok_scorer.repository import (
    RUBRIC_VERSION,
    RULE_VERSION,
    SyncTikTokScoreRepository,
    TikTokScoreRepository,
)
from viraldy.modules.tiktok_scorer.scorer import score_tiktok_structure


def score_from_evidence_bundle(evidence: list[EvidenceItemModel]) -> TikTokScoreResultV2:
    return TikTokScoreResultV2.model_validate(score_tiktok_structure(evidence))


def score_from_creative_dna(
    creative_dna_json: dict[str, object],
    evidence: list[EvidenceItemModel],
) -> TikTokScoreResultV2:
    # Current v2 calculators still score normalized evidence; DNA is validated by callers.
    _ = creative_dna_json
    return score_from_evidence_bundle(evidence)


__all__ = [
    "RUBRIC_VERSION",
    "RULE_VERSION",
    "SyncTikTokScoreRepository",
    "TikTokScoreRepository",
    "score_from_creative_dna",
    "score_from_evidence_bundle",
]
