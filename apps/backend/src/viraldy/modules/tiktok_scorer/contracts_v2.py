from __future__ import annotations

from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from viraldy.modules.media_analysis.public import validate_evidence_refs

ApplicabilityV2 = Literal["applicable", "not_applicable", "unknown"]
EvidenceStatusV2 = Literal["sufficient", "partial", "insufficient"]
ConfidenceV2 = Literal["high", "medium", "low"]
PriorityV2 = Literal["P0", "P1", "P2", "P3"]
SeverityV2 = Literal["hard", "high", "medium", "low", "info"]
ProfileCodeV1 = Literal[
    "general_tiktok_v1",
    "product_led_demo_v1",
    "creator_review_v1",
    "story_led_pov_v1",
    "tutorial_howto_v1",
    "unboxing_reaction_v1",
    "comment_reply_faq_v1",
    "offer_led_shop_v1",
]
IntendedUseV1 = Literal[
    "tiktok_organic",
    "tiktok_shop_affiliate",
    "ugc_paid_candidate",
    "spark_candidate",
]
ScoreModeV2 = Literal["quick", "product_aware", "usage_aware"]
RuleClassV1 = Literal[
    "official_hard_rule",
    "product_governance_rule",
    "operational_hard_constraint",
    "contextual_guideline",
    "directional_pattern",
    "seller_preference",
]


class TikTokContractV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ProfileSelectionV1(TikTokContractV2):
    profile_code: ProfileCodeV1
    selection_mode: Literal[
        "user_selected",
        "model_suggested",
        "model_suggested_user_confirmed",
        "user_overridden",
        "inherited",
    ]
    confidence: float = Field(ge=0, le=1)
    alternative_profiles: list[ProfileCodeV1] = Field(default_factory=list)
    evidence_ids: list[UUID] = Field(default_factory=list)


class TikTokDimensionResultV2(TikTokContractV2):
    code: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=160)
    score: int | None = Field(default=None, ge=0, le=100)
    applicability: ApplicabilityV2
    evidence_status: EvidenceStatusV2
    confidence: ConfidenceV2
    reason: str = Field(min_length=1)
    positive_signals: list[str] = Field(default_factory=list)
    missing_signals: list[str] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)
    evidence_ids: list[UUID] = Field(default_factory=list)
    contributing_rule_codes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_responsible_score(self) -> Self:
        responsibly_scoreable = (
            self.applicability == "applicable" and self.evidence_status != "insufficient"
        )
        if not responsibly_scoreable and self.score is not None:
            raise ValueError(
                "score must be null when a dimension is not applicable, unknown, "
                "or has insufficient evidence"
            )
        if self.score is not None and not self.evidence_ids:
            raise ValueError("scored dimensions must reference evidence")
        return self


class VideoSceneV1(TikTokContractV2):
    scene_id: UUID
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    summary: str = Field(min_length=1)
    shot_type: str | None = None
    product_visible: bool | None = None
    product_match_confidence: float | None = Field(default=None, ge=0, le=1)
    product_visibility_quality: str | None = None
    spoken_text: str | None = None
    overlay_texts: list[str] = Field(default_factory=list)
    demo_step: str | None = None
    proof_role: str | None = None
    creator_present: bool | None = None
    visual_quality: Literal[
        "good",
        "usable",
        "dark",
        "blurry",
        "obscured",
        "unknown",
    ]
    continuity_group_id: UUID | None = None
    reusable_for_edit: bool
    evidence_ids: list[UUID]

    @model_validator(mode="after")
    def validate_scene(self) -> Self:
        _validate_time_range((self.start_ms, self.end_ms), field_name="scene")
        if not self.evidence_ids:
            raise ValueError("a scene must reference observed evidence")
        return self


class SafeZoneObservationV1(TikTokContractV2):
    time_range_ms: tuple[int, int]
    status: Literal["safe", "risk", "unknown"]
    reason: str
    evidence_ids: list[UUID]

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        _validate_time_range(self.time_range_ms, field_name="safe-zone observation")
        if not self.evidence_ids:
            raise ValueError("a safe-zone observation must reference evidence")
        return self


class SceneInventoryV1(TikTokContractV2):
    asset_version_id: UUID
    duration_ms: int | None = Field(default=None, ge=0)
    audio_available: bool | None
    scenes: list[VideoSceneV1] = Field(default_factory=list)
    asr_coverage: float | None = Field(default=None, ge=0, le=1)
    ocr_coverage: float | None = Field(default=None, ge=0, le=1)
    product_appearance_ranges: list[tuple[int, int]] = Field(default_factory=list)
    cta_ranges: list[tuple[int, int]] = Field(default_factory=list)
    disclosure_ranges: list[tuple[int, int]] = Field(default_factory=list)
    safe_zone_observations: list[SafeZoneObservationV1] = Field(default_factory=list)
    continuity_group_ids: list[UUID] = Field(default_factory=list)
    evidence_ids: list[UUID] = Field(default_factory=list)
    coverage_status: EvidenceStatusV2
    overall_confidence: ConfidenceV2
    extractor_versions: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_inventory(self) -> Self:
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("scene inventory evidence IDs must be unique")
        if self.duration_ms is None:
            if self.scenes or self._all_ranges():
                raise ValueError("scenes and time ranges require a known media duration")
            return self

        scene_ids = [scene.scene_id for scene in self.scenes]
        if len(scene_ids) != len(set(scene_ids)):
            raise ValueError("scene IDs must be unique")
        allowed_evidence = set(self.evidence_ids)
        for scene in self.scenes:
            _validate_within_duration(
                (scene.start_ms, scene.end_ms), self.duration_ms, field_name="scene"
            )
            _validate_evidence_subset(scene.evidence_ids, allowed_evidence)
            if (
                scene.continuity_group_id is not None
                and scene.continuity_group_id not in self.continuity_group_ids
            ):
                raise ValueError("scene references an unknown continuity group")
        for time_range in self._all_ranges():
            _validate_within_duration(time_range, self.duration_ms, field_name="inventory range")
        for observation in self.safe_zone_observations:
            _validate_within_duration(
                observation.time_range_ms,
                self.duration_ms,
                field_name="safe-zone observation",
            )
            _validate_evidence_subset(observation.evidence_ids, allowed_evidence)
        return self

    def _all_ranges(self) -> list[tuple[int, int]]:
        return [
            *self.product_appearance_ranges,
            *self.cta_ranges,
            *self.disclosure_ranges,
        ]


class TikTokFindingV2(TikTokContractV2):
    id: UUID
    code: str = Field(min_length=1, max_length=120)
    rule_code: str = Field(min_length=1, max_length=160)
    rule_class: RuleClassV1
    source_dimension: str = Field(min_length=1, max_length=120)
    severity: SeverityV2
    priority: PriorityV2
    applicability: ApplicabilityV2
    evidence_status: EvidenceStatusV2
    title: str = Field(min_length=1, max_length=240)
    reason: str = Field(min_length=1)
    expected: dict[str, object]
    observed: dict[str, object]
    target_time_range_ms: tuple[int, int] | None = None
    evidence_ids: list[UUID]
    uncertainty: list[str] = Field(default_factory=list)
    requires_seller_truth: bool
    can_be_resolved_by_edit: bool | None
    requires_physical_reshoot: bool | None

    @model_validator(mode="after")
    def validate_finding(self) -> Self:
        if not self.evidence_ids:
            raise ValueError("every finding must reference evidence")
        if self.target_time_range_ms is not None:
            _validate_time_range(self.target_time_range_ms, field_name="finding")
        return self


class VideoEditOperationV1(TikTokContractV2):
    operation: Literal[
        "move_clip",
        "trim_clip_start",
        "trim_clip_end",
        "split_clip",
        "insert_existing_clip",
        "extend_readable_hold",
        "add_overlay",
        "replace_overlay",
        "remove_overlay",
        "replace_spoken_line",
        "preserve_clip",
    ]
    source_scene_id: UUID | None
    source_range_ms: tuple[int, int] | None
    target_start_ms: int | None = Field(default=None, ge=0)
    target_duration_ms: int | None = Field(default=None, ge=0)
    text_value: str | None = None
    evidence_ids: list[UUID]
    feasibility: Literal[
        "verified_possible",
        "likely_possible",
        "requires_editor_confirmation",
    ]

    @model_validator(mode="after")
    def validate_operation_shape(self) -> Self:
        if self.source_range_ms is not None:
            _validate_time_range(self.source_range_ms, field_name="operation source")
        if self.operation in {"move_clip", "insert_existing_clip", "preserve_clip"}:
            if self.source_scene_id is None or self.source_range_ms is None:
                raise ValueError(f"{self.operation} requires a source scene and source range")
        if self.operation in {"add_overlay", "replace_overlay", "replace_spoken_line"}:
            if not self.text_value:
                raise ValueError(f"{self.operation} requires text_value")
        if not self.evidence_ids:
            raise ValueError("edit operations must reference evidence")
        return self

    def validate_against_inventory(self, inventory: SceneInventoryV1) -> Self:
        duration_ms = inventory.duration_ms
        if duration_ms is None:
            raise ValueError("operation timestamps require a known media duration")
        scene_by_id = {scene.scene_id: scene for scene in inventory.scenes}
        if self.source_scene_id is not None and self.source_scene_id not in scene_by_id:
            raise ValueError("operation references a scene that does not exist")
        if self.source_range_ms is not None:
            _validate_within_duration(
                self.source_range_ms,
                duration_ms,
                field_name="operation source",
            )
            if self.source_scene_id is not None:
                scene = scene_by_id[self.source_scene_id]
                if (
                    self.source_range_ms[0] < scene.start_ms
                    or self.source_range_ms[1] > scene.end_ms
                ):
                    raise ValueError("operation source range must be inside its source scene")
        if self.target_start_ms is not None:
            target_end = self.target_start_ms + (self.target_duration_ms or 0)
            _validate_within_duration(
                (self.target_start_ms, target_end),
                duration_ms,
                field_name="operation target",
            )
        _validate_evidence_subset(self.evidence_ids, set(inventory.evidence_ids))
        return self


class TikTokFixActionV1(TikTokContractV2):
    id: UUID
    code: str = Field(min_length=1, max_length=160)
    source_finding_id: UUID
    source_finding_code: str = Field(min_length=1, max_length=120)
    recommendation_class: Literal["required_fix", "high_priority_improvement"]
    basis: Literal[
        "official_rule",
        "product_governance",
        "operational_constraint",
        "score_profile",
        "contextual_guideline",
        "video_diagnosis",
    ]
    priority: Literal["P0", "P1", "P2"]
    severity: Literal["hard", "high", "medium", "low"]
    source_dimension: str
    owner_role: Literal["seller", "creator", "editor", "compliance_reviewer"]
    fix_type: Literal[
        "edit_existing_footage",
        "trim_or_reorder",
        "add_overlay",
        "replace_overlay_copy",
        "replace_spoken_line",
        "reshoot_scene",
        "add_missing_scene",
        "confirm_seller_input",
        "confirm_rights",
        "request_better_media",
    ]
    title: str = Field(min_length=1)
    why_it_matters: str = Field(min_length=1)
    expected: dict[str, object]
    observed: dict[str, object]
    evidence_ids: list[UUID]
    target_time_range_ms: tuple[int, int] | None
    video_operations: list[VideoEditOperationV1]
    instructions: list[str] = Field(min_length=1)
    strengths_to_preserve: list[str]
    required_inputs: list[str]
    estimated_effort: Literal["low", "medium", "high"]
    reshoot_required: bool
    completion_criteria: list[str] = Field(min_length=1)
    verification_method: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_fix(self) -> Self:
        if not self.evidence_ids:
            raise ValueError("fix actions must reference the finding evidence")
        if self.target_time_range_ms is not None:
            _validate_time_range(self.target_time_range_ms, field_name="fix target")
        if self.reshoot_required and self.fix_type not in {"reshoot_scene", "add_missing_scene"}:
            raise ValueError("reshoot_required is only valid for reshoot or missing-scene fixes")
        if not self.reshoot_required and self.fix_type == "reshoot_scene":
            raise ValueError("reshoot_scene must set reshoot_required")
        return self


class TikTokStrengthV1(TikTokContractV2):
    code: str
    title: str
    source_dimension: str
    evidence_ids: list[UUID]


class AuxiliarySignalV1(TikTokContractV2):
    status: Literal["evaluated", "not_evaluated", "directional"]
    reason: str
    evidence_ids: list[UUID] = Field(default_factory=list)
    market: str | None = None
    observed_at: datetime | None = None
    source: str | None = None
    expires_at: datetime | None = None


class TikTokAuxiliarySignalsV1(TikTokContractV2):
    search_discovery_readiness: AuxiliarySignalV1 = Field(
        default_factory=lambda: AuxiliarySignalV1(
            status="not_evaluated",
            reason="No target query or buyer question was provided.",
        )
    )
    community_conversation_potential: AuxiliarySignalV1 = Field(
        default_factory=lambda: AuxiliarySignalV1(
            status="not_evaluated",
            reason="No community-conversation context was provided.",
        )
    )
    trend_relevance: AuxiliarySignalV1 = Field(
        default_factory=lambda: AuxiliarySignalV1(
            status="not_evaluated",
            reason="No current, expiring trend observation was provided.",
        )
    )

    @classmethod
    def directional_defaults(cls, *, trend_reason: str) -> TikTokAuxiliarySignalsV1:
        return cls(
            community_conversation_potential=AuxiliarySignalV1(
                status="directional",
                reason=trend_reason,
            )
        )

    @model_validator(mode="after")
    def validate_trend_metadata(self) -> Self:
        trend = self.trend_relevance
        if trend.status != "not_evaluated":
            if not all((trend.market, trend.observed_at, trend.source, trend.expires_at)):
                raise ValueError(
                    "evaluated or directional trend data requires market, observation time, "
                    "source, and expiry"
                )
            if trend.expires_at is not None and trend.observed_at is not None:
                if trend.expires_at <= trend.observed_at:
                    raise ValueError("trend expiry must follow its observation time")
        return self


class CreativeDirectionContextV1(TikTokContractV2):
    source_type: Literal["viral_kit"]
    source_id: UUID
    source_version: int = Field(ge=1)
    source_status: str = "concept_selected"
    concept_id: UUID
    concept_status: Literal["selected", "rejected"] = "selected"
    product_snapshot_hash: str = Field(min_length=1)
    objective: str | None
    market: str | None
    buyer_context: dict[str, object]
    message_angle: str
    hook_mechanism: str
    narrative_sequence: list[str]
    demo_mechanism: str | None
    proof_mechanism: str | None
    cta_strategy: str | None
    keep: list[str]
    change: list[str]
    avoid: list[str]
    allowed_claims: list[str]
    prohibited_claims: list[str]
    required_disclosures: list[str]
    expected_learning: str | None


class CreativeUpgradeSuggestionV1(TikTokContractV2):
    id: UUID
    source_type: Literal["viral_kit"]
    source_id: UUID
    source_version: int
    concept_id: UUID
    affects_score: Literal[False] = False
    recommendation_class: Literal["optional_upgrade", "next_iteration_direction"]
    title: str
    why_it_fits: str
    keep_from_current_video: list[str]
    change_in_current_video: list[str]
    additional_footage_needed: list[str]
    suggested_hook_mechanism: str | None
    suggested_narrative_sequence: list[str]
    suggested_demo_mechanism: str | None
    suggested_proof_mechanism: str | None
    suggested_cta_strategy: str | None
    claim_guardrails: list[str]
    evidence_ids: list[UUID]
    expected_learning: str | None


class TikTokScoreComputationV2(TikTokContractV2):
    asset_version_id: UUID
    profile_selection: ProfileSelectionV1
    intended_use: IntendedUseV1
    market: str | None = None
    objective: str | None = None
    product_snapshot_hash: str | None = None
    direction_governance_conflicts: list[str] = Field(default_factory=list)
    policy_pack_versions: dict[str, str] = Field(default_factory=dict)
    scene_inventory: SceneInventoryV1
    dimensions: list[TikTokDimensionResultV2]
    findings: list[TikTokFindingV2]
    critical_evidence_unavailable: bool = False
    paid_use_rights_status: Literal[
        "not_applicable",
        "not_evaluated",
        "pending_confirmation",
        "confirmed_externally",
    ] = "not_evaluated"
    auxiliary_signals: TikTokAuxiliarySignalsV1 = Field(default_factory=TikTokAuxiliarySignalsV1)

    @model_validator(mode="after")
    def validate_computation(self) -> Self:
        if self.asset_version_id != self.scene_inventory.asset_version_id:
            raise ValueError(
                "score input and scene inventory must reference the same asset version"
            )
        allowed = set(self.scene_inventory.evidence_ids)
        _validate_evidence_subset(self.profile_selection.evidence_ids, allowed)
        for dimension in self.dimensions:
            _validate_evidence_subset(dimension.evidence_ids, allowed)
        for finding in self.findings:
            _validate_evidence_subset(finding.evidence_ids, allowed)
            if finding.target_time_range_ms is not None:
                _validate_optional_duration_range(
                    finding.target_time_range_ms,
                    self.scene_inventory.duration_ms,
                    field_name="finding",
                )
        return self


class TikTokScoreResultV2(TikTokContractV2):
    schema_version: Literal["tiktok_diagnostic_v2"] = "tiktok_diagnostic_v2"
    asset_version_id: UUID
    profile_selection: ProfileSelectionV1
    intended_use: IntendedUseV1
    market: str | None
    objective: str | None
    product_snapshot_hash: str | None
    policy_pack_versions: dict[str, str]
    scene_inventory: SceneInventoryV1
    overall_score: int | None = Field(default=None, ge=0, le=100)
    overall_confidence: ConfidenceV2
    creative_structure_decision: Literal[
        "request_better_media",
        "blocked",
        "revise",
        "usable_with_improvements",
        "structurally_ready",
    ]
    paid_use_rights_status: Literal[
        "not_applicable",
        "not_evaluated",
        "pending_confirmation",
        "confirmed_externally",
    ]
    final_paid_readiness: Literal[
        "not_applicable",
        "pending_rights_confirmation",
        "not_ready",
        "externally_confirmed",
    ]
    dimensions: list[TikTokDimensionResultV2]
    findings: list[TikTokFindingV2]
    required_fixes: list[TikTokFixActionV1]
    strengths: list[TikTokStrengthV1]
    auxiliary_signals: TikTokAuxiliarySignalsV1
    optional_upgrades: list[CreativeUpgradeSuggestionV1]
    evidence_ids: list[UUID]
    uncertainty: list[str]

    @model_validator(mode="after")
    def validate_result_lineage(self) -> Self:
        if self.asset_version_id != self.scene_inventory.asset_version_id:
            raise ValueError("result and scene inventory must reference the same asset version")
        allowed = set(self.scene_inventory.evidence_ids)
        all_refs: list[list[UUID]] = [
            self.profile_selection.evidence_ids,
            self.evidence_ids,
            *[dimension.evidence_ids for dimension in self.dimensions],
            *[finding.evidence_ids for finding in self.findings],
            *[fix.evidence_ids for fix in self.required_fixes],
            *[strength.evidence_ids for strength in self.strengths],
            *[upgrade.evidence_ids for upgrade in self.optional_upgrades],
        ]
        for refs in all_refs:
            _validate_evidence_subset(refs, allowed)
        duration_ms = self.scene_inventory.duration_ms
        for finding in self.findings:
            if finding.target_time_range_ms is not None:
                _validate_optional_duration_range(
                    finding.target_time_range_ms, duration_ms, field_name="finding"
                )
        finding_ids = {finding.id for finding in self.findings}
        for fix in self.required_fixes:
            if fix.source_finding_id not in finding_ids:
                raise ValueError("fix action references a finding that does not exist")
            if fix.target_time_range_ms is not None:
                _validate_optional_duration_range(
                    fix.target_time_range_ms, duration_ms, field_name="fix target"
                )
            for operation in fix.video_operations:
                operation.validate_against_inventory(self.scene_inventory)
        return self


class FindingComparisonV1(TikTokContractV2):
    code: str
    title: str
    before_evidence_ids: list[UUID]
    after_evidence_ids: list[UUID]


class DimensionChangeV1(TikTokContractV2):
    code: str
    before_score: int | None
    after_score: int | None
    before_applicability: ApplicabilityV2 | None
    after_applicability: ApplicabilityV2 | None


class EvidenceComparisonV1(TikTokContractV2):
    subject_code: str
    before_evidence_ids: list[UUID]
    after_evidence_ids: list[UUID]


class ActionVerificationV1(TikTokContractV2):
    action_id: UUID
    action_code: str
    source_finding_code: str
    status: Literal["verified", "not_verified", "not_evaluated"]
    before: dict[str, object]
    after: dict[str, object]
    evidence_before_ids: list[UUID]
    evidence_after_ids: list[UUID]
    reason: str


class TikTokScoreComparisonV1(TikTokContractV2):
    schema_version: Literal["tiktok_score_comparison_v1"] = "tiktok_score_comparison_v1"
    before_asset_version_id: UUID
    after_asset_version_id: UUID
    before_score: int | None
    after_score: int | None
    resolved_blockers: list[FindingComparisonV1]
    unresolved_blockers: list[FindingComparisonV1]
    new_regressions: list[FindingComparisonV1]
    dimension_changes: list[DimensionChangeV1]
    evidence_before_after: list[EvidenceComparisonV1]
    strengths_preserved: list[TikTokStrengthV1]
    actions_verified: list[ActionVerificationV1]
    final_next_action: Literal[
        "request_better_media",
        "resolve_required_actions",
        "address_new_regressions",
        "review_unresolved_blockers",
        "no_required_changes",
    ]
    like_for_like: bool
    comparison_warning: str | None


def _validate_time_range(time_range: tuple[int, int], *, field_name: str) -> None:
    start_ms, end_ms = time_range
    if start_ms < 0 or end_ms < 0:
        raise ValueError(f"{field_name} timestamps must be non-negative")
    if end_ms < start_ms:
        raise ValueError(f"{field_name} end timestamp must not precede its start")


def _validate_within_duration(
    time_range: tuple[int, int],
    duration_ms: int,
    *,
    field_name: str,
) -> None:
    _validate_time_range(time_range, field_name=field_name)
    if time_range[1] > duration_ms:
        raise ValueError(f"{field_name} timestamp must remain within media duration")


def _validate_optional_duration_range(
    time_range: tuple[int, int],
    duration_ms: int | None,
    *,
    field_name: str,
) -> None:
    if duration_ms is None:
        raise ValueError(f"{field_name} timestamps require a known media duration")
    _validate_within_duration(time_range, duration_ms, field_name=field_name)


def _validate_evidence_subset(evidence_ids: list[UUID], allowed: set[UUID]) -> None:
    try:
        validate_evidence_refs(evidence_ids, allowed)
    except Exception as exc:
        raise ValueError("payload references evidence outside the scene inventory") from exc


__all__ = [
    "ActionVerificationV1",
    "ApplicabilityV2",
    "AuxiliarySignalV1",
    "ConfidenceV2",
    "CreativeDirectionContextV1",
    "CreativeUpgradeSuggestionV1",
    "DimensionChangeV1",
    "EvidenceComparisonV1",
    "EvidenceStatusV2",
    "FindingComparisonV1",
    "IntendedUseV1",
    "PriorityV2",
    "ProfileCodeV1",
    "ProfileSelectionV1",
    "RuleClassV1",
    "ScoreModeV2",
    "SafeZoneObservationV1",
    "SceneInventoryV1",
    "SeverityV2",
    "TikTokAuxiliarySignalsV1",
    "TikTokDimensionResultV2",
    "TikTokFindingV2",
    "TikTokFixActionV1",
    "TikTokScoreComparisonV1",
    "TikTokScoreComputationV2",
    "TikTokScoreResultV2",
    "TikTokStrengthV1",
    "VideoEditOperationV1",
    "VideoSceneV1",
]
