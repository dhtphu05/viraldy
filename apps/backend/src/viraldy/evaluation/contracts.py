from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

EvaluationMode = Literal["fixture", "mock", "live"]
AdaptationDecision = Literal["keep", "change", "avoid"]
MetricUnit = Literal["rate", "count", "score_1_to_5"]


class EvaluationContractBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CategoricalAgreementV1(EvaluationContractBase):
    key: str = Field(min_length=1)
    expected: str
    observed: str


class BooleanJudgmentV1(EvaluationContractBase):
    key: str = Field(min_length=1)
    passed: bool


class AdaptationReviewerLabelV1(EvaluationContractBase):
    element_path: str = Field(min_length=1)
    decision: AdaptationDecision


class GeneralizationJudgmentV1(EvaluationContractBase):
    statement_id: str = Field(min_length=1)
    supported: bool


class CampaignPackCompileInputV1(EvaluationContractBase):
    key: str = Field(min_length=1)
    brief: dict[str, object]


class PreflightCompileInputV1(EvaluationContractBase):
    key: str = Field(min_length=1)
    snapshot: dict[str, object]


class PatternKitMetricInputV1(EvaluationContractBase):
    case_id: str = Field(min_length=1)
    candidate: dict[str, object]
    resolvable_evidence_ids: list[UUID] = Field(default_factory=list)
    source_field_checks: list[CategoricalAgreementV1] = Field(default_factory=list)
    expected_sequence: list[str] = Field(default_factory=list)
    applicability_checks: list[CategoricalAgreementV1] = Field(default_factory=list)
    adaptation_reviewer_labels: list[AdaptationReviewerLabelV1] = Field(
        default_factory=list
    )
    forbidden_category_terms: list[str] = Field(default_factory=list)
    generalization_checks: list[GeneralizationJudgmentV1] = Field(default_factory=list)


class ViralKitMetricInputV1(EvaluationContractBase):
    case_id: str = Field(min_length=1)
    candidate: dict[str, object]
    product_grounding_checks: list[BooleanJudgmentV1] = Field(default_factory=list)
    constraint_preservation_checks: list[BooleanJudgmentV1] = Field(default_factory=list)
    diversity_checks: list[BooleanJudgmentV1] = Field(default_factory=list)
    expected_prohibited_claims: list[str] = Field(default_factory=list)
    expected_required_disclosures: list[str] = Field(default_factory=list)
    expected_pattern_kit_version_ids: list[UUID] = Field(default_factory=list)
    campaign_pack_briefs: list[CampaignPackCompileInputV1] = Field(default_factory=list)
    preflight_snapshots: list[PreflightCompileInputV1] = Field(default_factory=list)
    human_usefulness_scores: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_human_scores(self) -> ViralKitMetricInputV1:
        if any(score < 1 or score > 5 for score in self.human_usefulness_scores):
            raise ValueError("human usefulness scores must be between 1 and 5")
        return self


class EvaluationDatasetV1(EvaluationContractBase):
    schema_version: Literal["evaluation_dataset_v1"] = "evaluation_dataset_v1"
    dataset_id: str = Field(min_length=1)
    mode: EvaluationMode
    pattern_kit_cases: list[PatternKitMetricInputV1] = Field(default_factory=list)
    viral_kit_cases: list[ViralKitMetricInputV1] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_case_ids(self) -> EvaluationDatasetV1:
        case_ids = [case.case_id for case in self.pattern_kit_cases]
        case_ids.extend(case.case_id for case in self.viral_kit_cases)
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("evaluation case IDs must be unique")
        return self


class MetricResultV1(EvaluationContractBase):
    metric: str
    value: float
    unit: MetricUnit
    numerator: float
    denominator: int = Field(ge=0)


class PatternKitMetricsResultV1(EvaluationContractBase):
    schema_validity: MetricResultV1
    evidence_resolution: MetricResultV1
    source_field_agreement: MetricResultV1
    sequence_agreement: MetricResultV1
    applicability_agreement: MetricResultV1
    keep_change_avoid_agreement: MetricResultV1
    cross_category_leakage: MetricResultV1
    unsupported_generalization: MetricResultV1


class ViralKitMetricsResultV1(EvaluationContractBase):
    schema_validity: MetricResultV1
    product_grounding: MetricResultV1
    constraint_preservation: MetricResultV1
    diversity_pass_rate: MetricResultV1
    buyer_creator_separation: MetricResultV1
    claim_disclosure_preservation: MetricResultV1
    pattern_kit_traceability: MetricResultV1
    campaign_pack_compile: MetricResultV1
    preflight_compile: MetricResultV1
    human_usefulness: MetricResultV1


class PatternKitCaseResultV1(EvaluationContractBase):
    case_id: str
    metrics: PatternKitMetricsResultV1


class ViralKitCaseResultV1(EvaluationContractBase):
    case_id: str
    metrics: ViralKitMetricsResultV1


class EvaluationAggregateV1(EvaluationContractBase):
    pattern_kit: PatternKitMetricsResultV1 | None = None
    viral_kit: ViralKitMetricsResultV1 | None = None


class EvaluationReportV1(EvaluationContractBase):
    schema_version: Literal["evaluation_report_v1"] = "evaluation_report_v1"
    dataset_id: str
    mode: EvaluationMode
    pattern_kit_cases: list[PatternKitCaseResultV1]
    viral_kit_cases: list[ViralKitCaseResultV1]
    aggregate: EvaluationAggregateV1
