from __future__ import annotations

from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from viraldy.modules.tiktok_scorer.contracts_v2 import ProfileCodeV1

ScorerGoldenCategoryV1 = Literal[
    "generic_tiktok_video",
    "tiktok_shop_product_demo",
    "product_led_demo",
    "story_led_pov_valid_later_reveal",
    "creator_review",
    "tutorial_howto",
    "unboxing_reaction",
    "comment_reply",
    "pod_personalization",
    "dropshipping_visual_demo",
    "video_without_audio",
    "dark_blurry_video",
    "missing_product",
    "wrong_product_sku",
    "missing_cta",
    "unsupported_claim",
    "missing_disclosure",
    "personalization_mismatch",
    "incomparable_before_after",
    "revision_resolving_blockers",
    "revision_introducing_regression",
    "compatible_viral_kit_enrichment",
    "incompatible_outdated_viral_kit_ignored",
    "direction_service_failure_core_succeeds",
]
ScorerDecisionV1 = Literal[
    "request_better_media",
    "blocked",
    "revise",
    "usable_with_improvements",
    "structurally_ready",
]
ScorerDimensionBandV1 = Literal["low", "medium", "high", "not_evaluated"]
ScorerScoreBandV1 = Literal["low", "medium", "high", "not_scored"]
ScorerFixTypeV1 = Literal[
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
ScorerMetricStatusV1 = Literal["measured", "unmeasured"]
ScorerMetricUnitV1 = Literal["rate", "count", "milliseconds", "usd", "score_1_to_5"]


class ScorerEvaluationContractV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ScorerGoldenEvidenceV1(ScorerEvaluationContractV1):
    evidence_id: UUID
    source_type: str = Field(min_length=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    summary: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.end_ms < self.start_ms:
            raise ValueError("golden evidence end must not precede start")
        return self


class ScorerExpectedActionV1(ScorerEvaluationContractV1):
    action_code: str = Field(min_length=1)
    priority: Literal["P0", "P1", "P2"]
    fix_type: ScorerFixTypeV1
    owner_role: Literal["seller", "creator", "editor", "compliance_reviewer"]
    evidence_ids: list[UUID]
    completion_criteria: list[str]
    capture_requirements: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_execution_labels(self) -> Self:
        if self.priority in {"P0", "P1"}:
            if not self.evidence_ids:
                raise ValueError("P0/P1 expected actions require evidence labels")
            if not self.completion_criteria:
                raise ValueError("P0/P1 expected actions require completion criteria")
        if self.fix_type in {"reshoot_scene", "add_missing_scene"}:
            if not self.capture_requirements:
                raise ValueError("reshoot expectations must say what to capture")
        return self


class ScorerExpectedOptionalUpgradeV1(ScorerEvaluationContractV1):
    code: str = Field(min_length=1)
    affects_score: Literal[False] = False


class ScorerExpectedRevisionLabelV1(ScorerEvaluationContractV1):
    action_code: str = Field(min_length=1)
    expected_status: Literal["verified", "not_verified", "not_evaluated"]


class TikTokScorerGoldenCaseV1(ScorerEvaluationContractV1):
    schema_version: Literal["tiktok_scorer_golden_case_v1"] = (
        "tiktok_scorer_golden_case_v1"
    )
    case_id: str = Field(min_length=1)
    categories: list[ScorerGoldenCategoryV1] = Field(min_length=1)
    descriptor: str = Field(min_length=1)
    synthetic_only: Literal[True] = True
    claims_real_world_accuracy: Literal[False] = False
    profile_code: ProfileCodeV1
    duration_ms: int = Field(gt=0)
    audio_available: bool
    evidence: list[ScorerGoldenEvidenceV1] = Field(min_length=1)
    expected_decisions: list[ScorerDecisionV1] = Field(min_length=1)
    expected_score_band: ScorerScoreBandV1
    expected_dimension_bands: dict[str, ScorerDimensionBandV1] = Field(default_factory=dict)
    expected_hard_blocker_codes: list[str] = Field(default_factory=list)
    expected_actions: list[ScorerExpectedActionV1] = Field(default_factory=list)
    expected_revision_labels: list[ScorerExpectedRevisionLabelV1] = Field(
        default_factory=list
    )
    expected_optional_upgrades: list[ScorerExpectedOptionalUpgradeV1] = Field(
        default_factory=list
    )

    @model_validator(mode="after")
    def validate_case_labels(self) -> Self:
        evidence_ids = [item.evidence_id for item in self.evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("golden evidence IDs must be unique within a case")
        for item in self.evidence:
            if item.end_ms > self.duration_ms:
                raise ValueError("golden evidence must remain inside the synthetic duration")
        allowed = set(evidence_ids)
        action_codes = [action.action_code for action in self.expected_actions]
        if len(action_codes) != len(set(action_codes)):
            raise ValueError("expected action codes must be unique within a case")
        for action in self.expected_actions:
            if not set(action.evidence_ids) <= allowed:
                raise ValueError("expected action references unknown golden evidence")
        if not set(self.expected_hard_blocker_codes) <= set(action_codes):
            raise ValueError("expected hard blockers require corresponding action labels")
        return self


class TikTokScorerGoldenDatasetV1(ScorerEvaluationContractV1):
    schema_version: Literal["tiktok_scorer_golden_dataset_v1"] = (
        "tiktok_scorer_golden_dataset_v1"
    )
    dataset_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    synthetic_only: Literal[True] = True
    claims_real_world_accuracy: Literal[False] = False
    cases: list[TikTokScorerGoldenCaseV1] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_cases(self) -> Self:
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("TikTok scorer golden case IDs must be unique")
        return self


class ScorerHumanLabelsV1(ScorerEvaluationContractV1):
    fix_action_usefulness_scores: dict[str, int] = Field(default_factory=dict)
    seller_clarity_scores: dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_scores(self) -> Self:
        scores = [
            *self.fix_action_usefulness_scores.values(),
            *self.seller_clarity_scores.values(),
        ]
        if any(score < 1 or score > 5 for score in scores):
            raise ValueError("human scorer labels must be between 1 and 5")
        return self


class TikTokScorerEvaluationSampleV1(ScorerEvaluationContractV1):
    golden_case: TikTokScorerGoldenCaseV1
    candidate_score: dict[str, object]
    candidate_comparison: dict[str, object] | None = None
    human_labels: ScorerHumanLabelsV1 = Field(default_factory=ScorerHumanLabelsV1)
    latency_ms: float | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)


class TikTokScorerEvaluationDatasetV1(ScorerEvaluationContractV1):
    schema_version: Literal["tiktok_scorer_evaluation_dataset_v1"] = (
        "tiktok_scorer_evaluation_dataset_v1"
    )
    dataset_id: str = Field(min_length=1)
    samples: list[TikTokScorerEvaluationSampleV1] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_samples(self) -> Self:
        case_ids = [sample.golden_case.case_id for sample in self.samples]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("evaluation samples must use unique golden cases")
        return self


class TikTokScorerMetricResultV1(ScorerEvaluationContractV1):
    metric: str = Field(min_length=1)
    status: ScorerMetricStatusV1
    value: float | None
    unit: ScorerMetricUnitV1
    numerator: float | None
    denominator: int = Field(ge=0)
    reason: str | None = None
    target_max: float | None = None
    target_met: bool | None = None

    @model_validator(mode="after")
    def validate_measurement_state(self) -> Self:
        if self.status == "measured":
            if self.value is None or self.numerator is None or self.denominator == 0:
                raise ValueError("measured metrics require a value and non-zero denominator")
        elif self.value is not None or self.numerator is not None:
            raise ValueError("unmeasured metrics must not report a value or numerator")
        if self.target_met is not None and self.target_max is None:
            raise ValueError("target_met requires target_max")
        return self


class TikTokScorerMetricsV1(ScorerEvaluationContractV1):
    schema_valid_rate: TikTokScorerMetricResultV1
    evidence_validity: TikTokScorerMetricResultV1
    timestamp_accuracy: TikTokScorerMetricResultV1
    out_of_range_timestamp_rate: TikTokScorerMetricResultV1
    dimension_agreement: TikTokScorerMetricResultV1
    blocker_precision: TikTokScorerMetricResultV1
    blocker_recall: TikTokScorerMetricResultV1
    false_hard_blocker_rate: TikTokScorerMetricResultV1
    fix_action_usefulness: TikTokScorerMetricResultV1
    edit_vs_reshoot_agreement: TikTokScorerMetricResultV1
    seller_action_agreement: TikTokScorerMetricResultV1
    seller_clarity: TikTokScorerMetricResultV1
    revision_resolution_accuracy: TikTokScorerMetricResultV1
    latency: TikTokScorerMetricResultV1
    cost_per_score: TikTokScorerMetricResultV1
    generic_output_rate: TikTokScorerMetricResultV1


class ScorerQualificationIssueV1(ScorerEvaluationContractV1):
    code: Literal[
        "schema_invalid",
        "fabricated_evidence",
        "timestamp_out_of_range",
        "p0_p1_evidence_missing",
        "p0_p1_completion_missing",
        "reshoot_capture_not_explained",
        "optional_upgrade_affects_score",
        "false_universal_product_timing_blocker",
    ]
    message: str = Field(min_length=1)


class TikTokScorerCaseEvaluationV1(ScorerEvaluationContractV1):
    case_id: str
    categories: list[ScorerGoldenCategoryV1]
    metrics: TikTokScorerMetricsV1
    qualification_issues: list[ScorerQualificationIssueV1]


class TikTokScorerEvaluationReportV1(ScorerEvaluationContractV1):
    schema_version: Literal["tiktok_scorer_evaluation_report_v1"] = (
        "tiktok_scorer_evaluation_report_v1"
    )
    dataset_id: str
    cases: list[TikTokScorerCaseEvaluationV1]
    aggregate: TikTokScorerMetricsV1
    qualification_passed: bool
    limitations: list[str] = Field(min_length=1)


__all__ = [
    "ScorerExpectedActionV1",
    "ScorerExpectedOptionalUpgradeV1",
    "ScorerExpectedRevisionLabelV1",
    "ScorerGoldenCategoryV1",
    "ScorerGoldenEvidenceV1",
    "ScorerHumanLabelsV1",
    "ScorerQualificationIssueV1",
    "TikTokScorerCaseEvaluationV1",
    "TikTokScorerEvaluationDatasetV1",
    "TikTokScorerEvaluationReportV1",
    "TikTokScorerEvaluationSampleV1",
    "TikTokScorerGoldenCaseV1",
    "TikTokScorerGoldenDatasetV1",
    "TikTokScorerMetricResultV1",
    "TikTokScorerMetricsV1",
]
