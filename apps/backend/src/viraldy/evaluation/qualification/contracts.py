from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from viraldy.evaluation.golden import GoldenSemanticOutputV1

QualificationMode = Literal["fixture", "mock", "live"]
QualificationExecutionScope = Literal["contract", "application_e2e"]
QualificationState = Literal[
    "fixture_configured",
    "mock_configured",
    "not_yet_qualified",
    "fixture_operation_verified",
    "mock_operation_verified",
    "live_operation_verified",
    "fixture_contract_verified",
    "mock_contract_verified",
    "live_contract_verified",
    "fixture_e2e_verified",
    "mock_e2e_verified",
    "live_e2e_case_verified",
    "live_qualified",
    "failed",
]
GateCategory = Literal["configuration", "hard", "semantic"]
CaseReadinessStatus = Literal["not_ready", "contract_only", "qualified_case"]
ValueStatus = Literal["weak", "limited", "meaningful"]
ProductReadinessStatus = Literal[
    "not_ready",
    "insufficient_evidence",
    "ready_for_limited_beta",
]


class QualificationContractBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QualificationRequestV1(QualificationContractBase):
    check_config: bool = False
    operation: str | None = None
    full_flow: bool = False
    case: str | None = None
    all_cases: bool = False
    write_report: bool = False

    @model_validator(mode="after")
    def validate_command(self) -> QualificationRequestV1:
        command_count = sum(
            (
                self.check_config,
                self.operation is not None,
                self.full_flow,
            )
        )
        if command_count != 1:
            raise ValueError(
                "select exactly one of check_config, operation, or full_flow"
            )
        if self.full_flow:
            if (self.case is None) == (not self.all_cases):
                raise ValueError(
                    "full_flow requires exactly one of case or all_cases"
                )
        elif self.case is not None or self.all_cases:
            raise ValueError("case selection is only valid with full_flow")
        return self


class SafeOperationConfigV1(QualificationContractBase):
    operation: str
    model: str
    prompt_name: str
    prompt_version: str
    schema_version: str
    endpoint_family: str


class SafeQualificationConfigV1(QualificationContractBase):
    mode: QualificationMode
    provider_route: str
    api_key_configured: bool
    base_url_origin: str
    store_responses: bool
    operation_configs: list[SafeOperationConfigV1]


class GateResultV1(QualificationContractBase):
    gate: str = Field(min_length=1)
    category: GateCategory
    passed: bool
    value: float
    threshold: str
    numerator: float
    denominator: int = Field(ge=0)
    detail: str


class CaseQualityAssessmentV1(QualificationContractBase):
    assessment_version: Literal["deterministic_self_assessment_v1"] = (
        "deterministic_self_assessment_v1"
    )
    readiness_status: CaseReadinessStatus
    value_status: ValueStatus
    value_score: float = Field(ge=0, le=5)
    generic_output: bool
    best_output_eligible: bool
    strength_signals: list[str]
    blockers: list[str]
    limitations: list[str]


class ProductReadinessAssessmentV1(QualificationContractBase):
    assessment_version: Literal["deterministic_self_assessment_v1"] = (
        "deterministic_self_assessment_v1"
    )
    status: ProductReadinessStatus
    product_ready: bool
    value_score: float = Field(ge=0, le=5)
    generic_output_rate: float = Field(ge=0, le=1)
    qualified_case_count: int = Field(ge=0)
    required_case_count: int = Field(default=3, ge=1)
    best_output_count: int = Field(ge=0)
    reasons: list[str]
    blockers: list[str]
    limitations: list[str]


class OperationExecutionV1(QualificationContractBase):
    operation: str
    provider: str
    endpoint_family: str
    model: str
    prompt_name: str
    prompt_version: str
    schema_version: str
    provider_request_id: str | None = None
    output: dict[str, object]
    output_valid: bool
    source_version_references_valid: bool
    evidence_ids_valid: bool
    timestamps_valid: bool
    silent_fixture_fallback: bool = False
    error_code: str | None = None
    error_message: str | None = None


class QualificationCaseExecutionV1(QualificationContractBase):
    scenario_id: str
    semantic_output: GoldenSemanticOutputV1
    operation_results: list[OperationExecutionV1]
    semantic_provider_request_id: str | None = None
    semantic_model: str | None = None
    execution_scope: QualificationExecutionScope = "contract"
    model_runs_persisted: bool = False
    workspace_deleted: bool = False
    application_evidence: dict[str, object] = Field(default_factory=dict)


class QualificationCaseResultV1(QualificationContractBase):
    scenario_id: str
    domain: str
    passed: bool
    operation_results: list[OperationExecutionV1]
    hard_gates: list[GateResultV1]
    semantic_gates: list[GateResultV1]
    semantic_output: GoldenSemanticOutputV1
    semantic_provider_request_id: str | None = None
    semantic_model: str | None = None
    execution_scope: QualificationExecutionScope
    model_runs_persisted: bool
    workspace_deleted: bool
    application_evidence: dict[str, object] = Field(default_factory=dict)
    quality_assessment: CaseQualityAssessmentV1


class QualificationReportV1(QualificationContractBase):
    schema_version: Literal["openai_qualification_report_v2"] = (
        "openai_qualification_report_v2"
    )
    run_id: str
    mode: QualificationMode
    qualification_state: QualificationState
    passed: bool
    command: str
    started_at: str
    completed_at: str
    safe_config: SafeQualificationConfigV1
    configuration_gates: list[GateResultV1]
    hard_gates: list[GateResultV1]
    semantic_gates: list[GateResultV1]
    operation_results: list[OperationExecutionV1]
    case_results: list[QualificationCaseResultV1]
    sample_size: int = Field(ge=0)
    product_readiness: ProductReadinessAssessmentV1
    confidence_note: str


@dataclass(frozen=True, slots=True)
class QualificationReportPaths:
    root: Path
    json_path: Path
    markdown_path: Path
    outputs_dir: Path
    failures_dir: Path
    best_outputs_dir: Path


@dataclass(frozen=True, slots=True)
class QualificationRunOutcome:
    report: QualificationReportV1
    report_paths: QualificationReportPaths | None = None

    @property
    def exit_code(self) -> int:
        return 0 if self.report.passed else 1
