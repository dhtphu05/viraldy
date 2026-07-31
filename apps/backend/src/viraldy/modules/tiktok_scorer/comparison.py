from __future__ import annotations

from collections.abc import Collection
from uuid import UUID

from viraldy.modules.tiktok_scorer.contracts_v2 import (
    ActionVerificationV1,
    DimensionChangeV1,
    EvidenceComparisonV1,
    FindingComparisonV1,
    TikTokFindingV2,
    TikTokFixActionV1,
    TikTokScoreComparisonV1,
    TikTokScoreResultV2,
    TikTokStrengthV1,
)
from viraldy.modules.tiktok_scorer.policy_packs import HARD_BLOCK_RULE_CLASSES


def compare_score_results(
    before: TikTokScoreResultV2,
    after: TikTokScoreResultV2,
    accepted_fix_action_ids: Collection[UUID] | None = None,
) -> TikTokScoreComparisonV1:
    before_findings = _findings_by_code(before.findings)
    after_findings = _findings_by_code(after.findings)
    before_blockers = {
        code: finding for code, finding in before_findings.items() if _is_verified_blocker(finding)
    }
    resolved_codes = sorted(set(before_blockers) - set(after_findings))
    unresolved_codes = sorted(set(before_blockers).intersection(after_findings))
    regression_codes = sorted(
        code
        for code, finding in after_findings.items()
        if code not in before_findings
        and finding.applicability == "applicable"
        and finding.evidence_status != "insufficient"
        and finding.severity in {"hard", "high"}
    )
    before_required_fix_keys = _required_fix_keys(before.required_fixes)
    after_required_fix_keys = _required_fix_keys(after.required_fixes)
    has_new_required_fixes = bool(after_required_fix_keys - before_required_fix_keys)
    actions_to_verify = [
        action
        for action in before.required_fixes
        if accepted_fix_action_ids is None or action.id in accepted_fix_action_ids
    ]
    actions = [
        _verify_action(action, before_findings, after_findings, before, after)
        for action in actions_to_verify
    ]
    like_for_like, warning = _comparison_context(before, after)
    return TikTokScoreComparisonV1(
        before_asset_version_id=before.asset_version_id,
        after_asset_version_id=after.asset_version_id,
        before_score=before.overall_score,
        after_score=after.overall_score,
        resolved_blockers=[
            _finding_comparison(before_blockers[code], None) for code in resolved_codes
        ],
        unresolved_blockers=[
            _finding_comparison(before_blockers[code], after_findings[code])
            for code in unresolved_codes
        ],
        new_regressions=[
            _finding_comparison(None, after_findings[code]) for code in regression_codes
        ],
        dimension_changes=_dimension_changes(before, after),
        evidence_before_after=_evidence_comparisons(before_findings, after_findings),
        strengths_preserved=_strengths_preserved(before, after),
        actions_verified=actions,
        final_next_action=_final_next_action(
            after=after,
            has_regressions=bool(regression_codes),
            has_unresolved_blockers=bool(unresolved_codes),
            has_required_fixes=bool(after_required_fix_keys),
            has_new_required_fixes=has_new_required_fixes,
            actions=actions,
        ),
        like_for_like=like_for_like,
        comparison_warning=warning,
    )


def _findings_by_code(findings: list[TikTokFindingV2]) -> dict[str, TikTokFindingV2]:
    return {finding.code: finding for finding in findings}


def _required_fix_keys(fixes: list[TikTokFixActionV1]) -> set[tuple[str, str]]:
    return {
        (fix.code, fix.source_finding_code)
        for fix in fixes
        if fix.recommendation_class == "required_fix"
    }


def _is_verified_blocker(finding: TikTokFindingV2) -> bool:
    return (
        finding.severity == "hard"
        and finding.applicability == "applicable"
        and finding.evidence_status == "sufficient"
        and finding.rule_class in HARD_BLOCK_RULE_CLASSES
    )


def _finding_comparison(
    before: TikTokFindingV2 | None,
    after: TikTokFindingV2 | None,
) -> FindingComparisonV1:
    finding = after or before
    if finding is None:
        raise ValueError("finding comparison requires a before or after finding")
    return FindingComparisonV1(
        code=finding.code,
        title=finding.title,
        before_evidence_ids=list(before.evidence_ids) if before is not None else [],
        after_evidence_ids=list(after.evidence_ids) if after is not None else [],
    )


def _dimension_changes(
    before: TikTokScoreResultV2,
    after: TikTokScoreResultV2,
) -> list[DimensionChangeV1]:
    before_by_code = {dimension.code: dimension for dimension in before.dimensions}
    after_by_code = {dimension.code: dimension for dimension in after.dimensions}
    return [
        DimensionChangeV1(
            code=code,
            before_score=before_by_code[code].score if code in before_by_code else None,
            after_score=after_by_code[code].score if code in after_by_code else None,
            before_applicability=(
                before_by_code[code].applicability if code in before_by_code else None
            ),
            after_applicability=(
                after_by_code[code].applicability if code in after_by_code else None
            ),
        )
        for code in sorted(set(before_by_code).union(after_by_code))
    ]


def _evidence_comparisons(
    before: dict[str, TikTokFindingV2],
    after: dict[str, TikTokFindingV2],
) -> list[EvidenceComparisonV1]:
    return [
        EvidenceComparisonV1(
            subject_code=code,
            before_evidence_ids=list(before[code].evidence_ids) if code in before else [],
            after_evidence_ids=list(after[code].evidence_ids) if code in after else [],
        )
        for code in sorted(set(before).union(after))
    ]


def _strengths_preserved(
    before: TikTokScoreResultV2,
    after: TikTokScoreResultV2,
) -> list[TikTokStrengthV1]:
    after_codes = {strength.code for strength in after.strengths}
    return [strength for strength in before.strengths if strength.code in after_codes]


def _verify_action(
    action: TikTokFixActionV1,
    before_findings: dict[str, TikTokFindingV2],
    after_findings: dict[str, TikTokFindingV2],
    before: TikTokScoreResultV2,
    after: TikTokScoreResultV2,
) -> ActionVerificationV1:
    before_finding = before_findings.get(action.source_finding_code)
    after_finding = after_findings.get(action.source_finding_code)
    after_observed: dict[str, object] = {}
    after_evidence_ids: list[UUID] = []
    if before_finding is None:
        status = "not_evaluated"
        reason = "The source finding is unavailable in the prior result."
    elif after_finding is not None:
        status = "not_verified"
        reason = "The source finding remains in the revision diagnostics."
        after_observed = dict(after_finding.observed)
        after_evidence_ids = list(after_finding.evidence_ids)
    elif after.creative_structure_decision == "request_better_media":
        status = "not_evaluated"
        reason = "Revision evidence is insufficient to verify the accepted action."
    elif action.fix_type == "confirm_seller_input" and (
        after.product_snapshot_hash is None
        or after.product_snapshot_hash == before.product_snapshot_hash
    ):
        status = "not_evaluated"
        reason = "No revised Product Context evidence confirms the seller input."
    elif action.fix_type == "confirm_rights" and (
        after.paid_use_rights_status != "confirmed_externally"
    ):
        status = "not_evaluated"
        reason = "Paid-use rights are not externally confirmed in the revision."
    else:
        after_dimension = next(
            (
                dimension
                for dimension in after.dimensions
                if dimension.code == action.source_dimension
            ),
            None,
        )
        if (
            after_dimension is None
            or after_dimension.applicability != "applicable"
            or after_dimension.evidence_status == "insufficient"
            or not after_dimension.evidence_ids
        ):
            status = "not_evaluated"
            reason = "The revision lacks sufficient evidence for this action's dimension."
        else:
            status = "verified"
            reason = "The source finding is absent and revision evidence covers its dimension."
            after_observed = {
                "dimension_score": after_dimension.score,
                "evidence_status": after_dimension.evidence_status,
            }
            after_evidence_ids = list(after_dimension.evidence_ids)
    return ActionVerificationV1(
        action_id=action.id,
        action_code=action.code,
        source_finding_code=action.source_finding_code,
        status=status,
        before=dict(before_finding.observed) if before_finding is not None else {},
        after=after_observed,
        evidence_before_ids=(
            list(before_finding.evidence_ids) if before_finding is not None else []
        ),
        evidence_after_ids=after_evidence_ids,
        reason=reason,
    )


def _comparison_context(
    before: TikTokScoreResultV2,
    after: TikTokScoreResultV2,
) -> tuple[bool, str | None]:
    changed: list[str] = []
    if before.profile_selection.profile_code != after.profile_selection.profile_code:
        changed.append("profile")
    if before.product_snapshot_hash != after.product_snapshot_hash:
        changed.append("Product Context")
    if before.intended_use != after.intended_use:
        changed.append("intended use")
    if before.market != after.market:
        changed.append("market")
    if not changed:
        return True, None
    return False, f"Not like-for-like: {', '.join(changed)} changed between drafts."


def _final_next_action(
    *,
    after: TikTokScoreResultV2,
    has_regressions: bool,
    has_unresolved_blockers: bool,
    has_required_fixes: bool,
    has_new_required_fixes: bool,
    actions: list[ActionVerificationV1],
) -> str:
    if after.creative_structure_decision == "request_better_media":
        return "request_better_media"
    if has_regressions:
        return "address_new_regressions"
    if has_unresolved_blockers or after.creative_structure_decision == "blocked":
        return "review_unresolved_blockers"
    if any(action.status != "verified" for action in actions):
        return "resolve_required_actions"
    if (
        has_new_required_fixes
        or has_required_fixes
        or after.creative_structure_decision == "revise"
    ):
        return "resolve_required_actions"
    return "no_required_changes"


__all__ = ["compare_score_results"]
