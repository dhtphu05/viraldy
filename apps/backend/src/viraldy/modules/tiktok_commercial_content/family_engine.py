from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.modules.assets.models import AssetModel
from viraldy.modules.tiktok_commercial_content.models import (
    CreativeFamilyCandidateModel,
    CreativeFamilyMemberModel,
    CreativeFamilyModel,
)


@dataclass(frozen=True, slots=True)
class FamilyCandidateDecision:
    relationship: str
    score: float
    confidence: str
    signals: dict[str, object]
    reason: str


def compare_assets(left: AssetModel, right: AssetModel) -> FamilyCandidateDecision | None:
    if left.id == right.id or left.library_scope != right.library_scope:
        return None

    left_meta = left.metadata_json
    right_meta = right.metadata_json
    signals: dict[str, object] = {}
    score = 0.0

    left_url = _first_media_url(left_meta)
    right_url = _first_media_url(right_meta)
    same_media = bool(left_url and right_url and left_url == right_url)
    if same_media:
        score += 0.65
        signals["shared_media_url"] = True

    same_advertiser = _same_value(left_meta, right_meta, "advertiser_business_id")
    if same_advertiser:
        score += 0.12
        signals["advertiser"] = "same"

    same_creator = _same_value(left_meta, right_meta, "creator_reference")
    if same_creator:
        score += 0.08
        signals["creator"] = "same"

    title_overlap = _token_overlap(_title(left_meta), _title(right_meta))
    if title_overlap:
        score += min(0.15, title_overlap * 0.15)
        signals["title_overlap"] = round(title_overlap, 3)

    same_product = _same_value(left_meta, right_meta, "product_reference")
    if same_product:
        score += 0.08
        signals["product"] = "same"

    if not signals or score < 0.32:
        return None

    if same_media:
        relationship = "SAME_FOOTAGE"
    elif score >= 0.65 and title_overlap >= 0.5:
        relationship = "SAME_CONCEPT"
    else:
        relationship = "POSSIBLE_MATCH"

    confidence = "high" if score >= 0.9 else "medium" if score >= 0.6 else "low"
    reason = _reason(relationship, signals)
    return FamilyCandidateDecision(
        relationship=relationship,
        score=round(min(score, 1.0), 3),
        confidence=confidence,
        signals=signals,
        reason=reason,
    )


class CreativeFamilyEngine:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def refresh(
        self,
        *,
        scope: str,
        workspace_id: UUID | None,
        asset_ids: list[UUID] | None = None,
        limit: int = 200,
    ) -> list[CreativeFamilyCandidateModel]:
        assets = await self._assets(scope, workspace_id, asset_ids, limit)
        candidates: list[CreativeFamilyCandidateModel] = []
        for left, right in combinations(assets, 2):
            left_id, right_id = sorted((left.id, right.id), key=str)
            decision = compare_assets(left, right)
            if decision is None:
                continue
            row = await self._session.scalar(
                select(CreativeFamilyCandidateModel).where(
                    CreativeFamilyCandidateModel.scope == scope,
                    CreativeFamilyCandidateModel.workspace_id == workspace_id,
                    CreativeFamilyCandidateModel.asset_a_id == left_id,
                    CreativeFamilyCandidateModel.asset_b_id == right_id,
                )
            )
            if row is None:
                row = CreativeFamilyCandidateModel(
                    id=uuid4(),
                    scope=scope,
                    workspace_id=workspace_id,
                    asset_a_id=left_id,
                    asset_b_id=right_id,
                    relationship=decision.relationship,
                    candidate_score=decision.score,
                    confidence=decision.confidence,
                    signals_json=decision.signals,
                    reason=decision.reason,
                )
                self._session.add(row)
            else:
                row.relationship = decision.relationship
                row.candidate_score = decision.score
                row.confidence = decision.confidence
                row.signals_json = decision.signals
                row.reason = decision.reason
            candidates.append(row)
        await self._session.flush()
        await self._auto_group(candidates, workspace_id)
        await self._session.commit()
        return candidates

    async def list_candidates(
        self, *, scope: str, workspace_id: UUID | None, limit: int = 100
    ) -> list[CreativeFamilyCandidateModel]:
        return list(
            await self._session.scalars(
                select(CreativeFamilyCandidateModel)
                .where(
                    CreativeFamilyCandidateModel.scope == scope,
                    CreativeFamilyCandidateModel.workspace_id == workspace_id,
                )
                .order_by(CreativeFamilyCandidateModel.candidate_score.desc())
                .limit(limit)
            )
        )

    async def _assets(
        self,
        scope: str,
        workspace_id: UUID | None,
        asset_ids: list[UUID] | None,
        limit: int,
    ) -> list[AssetModel]:
        workspace_filter = (
            AssetModel.workspace_id == workspace_id
            if scope == "WORKSPACE"
            else AssetModel.workspace_id.is_(None)
        )
        statement = select(AssetModel).where(
            AssetModel.library_scope == scope,
            workspace_filter,
        )
        if asset_ids:
            statement = statement.where(AssetModel.id.in_(asset_ids))
        return list(await self._session.scalars(statement.limit(min(limit, 200))))

    async def _auto_group(
        self, candidates: list[CreativeFamilyCandidateModel], workspace_id: UUID | None
    ) -> None:
        for candidate in candidates:
            if candidate.relationship not in {"SAME_FOOTAGE", "NEAR_DUPLICATE"}:
                continue
            if candidate.candidate_score < 0.9:
                continue
            family = await self._family_for_asset(
                candidate.asset_a_id, candidate.scope, workspace_id
            )
            if family is None:
                family = CreativeFamilyModel(
                    id=uuid4(),
                    scope=candidate.scope,
                    workspace_id=workspace_id,
                    family_type="near_duplicate",
                    representative_asset_id=candidate.asset_a_id,
                    confidence=candidate.candidate_score,
                    status="candidate",
                )
                self._session.add(family)
                await self._session.flush()
            await self._add_member(family.id, candidate.asset_a_id, "BASE", candidate)
            await self._add_member(
                family.id, candidate.asset_b_id, candidate.relationship, candidate
            )

    async def _family_for_asset(
        self, asset_id: UUID, scope: str, workspace_id: UUID | None
    ) -> CreativeFamilyModel | None:
        return cast(
            CreativeFamilyModel | None,
            await self._session.scalar(
                select(CreativeFamilyModel)
                .join(
                    CreativeFamilyMemberModel,
                    CreativeFamilyMemberModel.creative_family_id == CreativeFamilyModel.id,
                )
                .where(
                    CreativeFamilyMemberModel.creative_asset_id == asset_id,
                    CreativeFamilyModel.scope == scope,
                    CreativeFamilyModel.workspace_id == workspace_id,
                )
            ),
        )

    async def _add_member(
        self,
        family_id: UUID,
        asset_id: UUID,
        relationship: str,
        candidate: CreativeFamilyCandidateModel,
    ) -> None:
        exists = await self._session.scalar(
            select(CreativeFamilyMemberModel).where(
                CreativeFamilyMemberModel.creative_family_id == family_id,
                CreativeFamilyMemberModel.creative_asset_id == asset_id,
            )
        )
        if exists is None:
            self._session.add(
                CreativeFamilyMemberModel(
                    creative_family_id=family_id,
                    creative_asset_id=asset_id,
                    relationship=relationship,
                    similarity_score=candidate.candidate_score,
                    similarity_evidence=candidate.signals_json,
                )
            )


def _first_media_url(metadata: dict[str, object]) -> str | None:
    for key in ("source_url", "media_url", "canonical_source_url"):
        value = metadata.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _title(metadata: dict[str, object]) -> str:
    value = metadata.get("title")
    return value if isinstance(value, str) else ""


def _same_value(left: dict[str, object], right: dict[str, object], key: str) -> bool:
    return bool(left.get(key) and left.get(key) == right.get(key))


def _token_overlap(left: str, right: str) -> float:
    left_tokens = {token for token in left.lower().split() if len(token) > 2}
    right_tokens = {token for token in right.lower().split() if len(token) > 2}
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _reason(relationship: str, signals: dict[str, object]) -> str:
    labels = []
    if signals.get("shared_media_url"):
        labels.append("shared media")
    if signals.get("advertiser") == "same":
        labels.append("same advertiser")
    if signals.get("creator") == "same":
        labels.append("same creator")
    if signals.get("product") == "same":
        labels.append("same product")
    if "title_overlap" in signals:
        labels.append("title overlap")
    return f"{relationship.replace('_', ' ').title()} candidate from {', '.join(labels)}."
