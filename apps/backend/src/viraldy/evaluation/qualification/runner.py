from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit

from viraldy.evaluation.golden import GoldenSemanticOutputV1, load_golden_fixture
from viraldy.evaluation.qualification.catalog import (
    FULL_FLOW_OPERATIONS,
    QUALIFIABLE_OPERATIONS,
    resolve_cases,
    resolve_operation,
)
from viraldy.evaluation.qualification.contracts import (
    OperationExecutionV1,
    QualificationCaseExecutionV1,
    QualificationCaseResultV1,
    QualificationMode,
    QualificationReportV1,
    QualificationRequestV1,
    QualificationRunOutcome,
    QualificationState,
    SafeOperationConfigV1,
    SafeQualificationConfigV1,
)
from viraldy.evaluation.qualification.executors import (
    DeterministicQualificationExecutor,
    OpenAIQualificationExecutor,
    QualificationExecutor,
)
from viraldy.evaluation.qualification.gates import (
    aggregate_hard_gates,
    case_hard_gates,
    configuration_gates,
    semantic_gates,
)
from viraldy.evaluation.qualification.quality import (
    assess_case_quality,
    assess_product_readiness,
)
from viraldy.evaluation.qualification.reporting import (
    write_qualification_report,
)
from viraldy.modules.ai_gateway.operations import (
    AiOperationName,
    get_ai_operation_definition,
)
from viraldy.modules.ai_gateway.providers.base import AiProviderError
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError

_REPORT_CONFIDENCE_NOTE = (
    "These results apply only to the selected Golden fixtures and configured "
    "models. Small-sample qualification is not universal model accuracy and does "
    "not guarantee virality, GMV, ROAS, conversion, policy approval, or sales."
)


class QualificationRunner:
    def __init__(
        self,
        *,
        settings: Settings,
        executor: QualificationExecutor | None = None,
        report_root: Path = Path("evaluation/reports/openai"),
        run_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._settings = settings
        self._mode = _qualification_mode(settings.ai_mode)
        self._executor = executor or _default_executor(settings, self._mode)
        self._report_root = report_root
        self._run_id_factory = run_id_factory or _new_run_id

    def run(self, request: QualificationRequestV1) -> QualificationRunOutcome:
        run_id = self._run_id_factory()
        started_at = _timestamp()
        safe_config = _safe_config(self._settings, self._mode)
        config_results = configuration_gates(safe_config)

        operation_results: list[OperationExecutionV1] = []
        case_results: list[QualificationCaseResultV1] = []
        hard_results = []
        semantic_results = []

        if request.operation is not None:
            operation = resolve_operation(request.operation)
            operation_results = [
                self._execute_operation_safely(operation, "home_travel_steamer")
            ]
            hard_results = aggregate_hard_gates(
                self._mode,
                [],
                operation_results,
            )
        elif request.full_flow:
            scenario_ids = resolve_cases(request.case, request.all_cases)
            for scenario_id in scenario_ids:
                case_results.append(self._execute_case_safely(scenario_id))
            hard_results = aggregate_hard_gates(
                self._mode,
                [result.hard_gates for result in case_results],
            )
            semantic_results = semantic_gates(
                [
                    (
                        load_golden_fixture(result.scenario_id),
                        result.semantic_output,
                    )
                    for result in case_results
                ]
            )

        passed = all(
            gate.passed
            for gate in (*config_results, *hard_results, *semantic_results)
        )
        state = _qualification_state(
            mode=self._mode,
            request=request,
            passed=passed,
            case_results=case_results,
        )
        command = _command_name(request)
        product_readiness = assess_product_readiness(
            mode=self._mode,
            command=command,
            passed=passed,
            case_results=case_results,
            global_gates=(*config_results, *hard_results, *semantic_results),
        )
        report = QualificationReportV1(
            run_id=run_id,
            mode=self._mode,
            qualification_state=state,
            passed=passed,
            command=command,
            started_at=started_at,
            completed_at=_timestamp(),
            safe_config=safe_config,
            configuration_gates=config_results,
            hard_gates=hard_results,
            semantic_gates=semantic_results,
            operation_results=operation_results,
            case_results=case_results,
            sample_size=len(case_results),
            product_readiness=product_readiness,
            confidence_note=_REPORT_CONFIDENCE_NOTE,
        )
        paths = (
            write_qualification_report(report, self._report_root)
            if request.write_report
            else None
        )
        return QualificationRunOutcome(report=report, report_paths=paths)

    def _execute_operation_safely(
        self,
        operation: AiOperationName,
        scenario_id: str,
    ) -> OperationExecutionV1:
        try:
            return self._executor.execute_operation(operation, scenario_id)
        except Exception as exc:
            return _failed_operation(
                operation=operation,
                settings=self._settings,
                mode=self._mode,
                exc=exc,
            )

    def _execute_case_safely(
        self,
        scenario_id: str,
    ) -> QualificationCaseResultV1:
        fixture = load_golden_fixture(scenario_id)
        try:
            execution = self._executor.execute_case(
                scenario_id,
                FULL_FLOW_OPERATIONS,
            )
        except Exception as exc:
            execution = QualificationCaseExecutionV1(
                scenario_id=scenario_id,
                semantic_output=_failed_semantic_output(scenario_id),
                operation_results=[
                    _failed_operation(
                        operation=FULL_FLOW_OPERATIONS[0],
                        settings=self._settings,
                        mode=self._mode,
                        exc=exc,
                    )
                ],
            )
        hard_results = case_hard_gates(self._mode, fixture, execution)
        semantic_results = semantic_gates(
            [(fixture, execution.semantic_output)]
        )
        passed = all(
            gate.passed for gate in (*hard_results, *semantic_results)
        )
        quality_assessment = assess_case_quality(
            mode=self._mode,
            passed=passed,
            hard_gates=hard_results,
            semantic_gates=semantic_results,
            execution_scope=execution.execution_scope,
            model_runs_persisted=execution.model_runs_persisted,
            workspace_deleted=execution.workspace_deleted,
            application_evidence=execution.application_evidence,
        )
        return QualificationCaseResultV1(
            scenario_id=scenario_id,
            domain=fixture.domain,
            passed=passed,
            operation_results=execution.operation_results,
            hard_gates=hard_results,
            semantic_gates=semantic_results,
            semantic_output=execution.semantic_output,
            semantic_provider_request_id=execution.semantic_provider_request_id,
            semantic_model=execution.semantic_model,
            execution_scope=execution.execution_scope,
            model_runs_persisted=execution.model_runs_persisted,
            workspace_deleted=execution.workspace_deleted,
            application_evidence=execution.application_evidence,
            quality_assessment=quality_assessment,
        )


def _safe_config(
    settings: Settings,
    mode: QualificationMode,
) -> SafeQualificationConfigV1:
    parsed_url = urlsplit(settings.openai_base_url)
    origin = f"{parsed_url.scheme}://{parsed_url.netloc}"
    return SafeQualificationConfigV1(
        mode=mode,
        provider_route=(
            mode if mode in {"fixture", "mock"} else settings.ai_provider
        ),
        api_key_configured=settings.openai_api_key is not None,
        base_url_origin=origin,
        store_responses=settings.openai_store_responses,
        operation_configs=[
            _safe_operation_config(settings, operation)
            for operation in QUALIFIABLE_OPERATIONS
        ],
    )


def _safe_operation_config(
    settings: Settings,
    operation: AiOperationName,
) -> SafeOperationConfigV1:
    definition = get_ai_operation_definition(operation)
    return SafeOperationConfigV1(
        operation=operation.value,
        model=settings.resolve_openai_model(
            operation.value,
            vision=operation is AiOperationName.MEDIA_OBSERVATION,
        ),
        prompt_name=definition.prompt_name,
        prompt_version=definition.prompt_version,
        schema_version=definition.schema_version,
        endpoint_family="responses",
    )


def _default_executor(
    settings: Settings,
    mode: QualificationMode,
) -> QualificationExecutor:
    if mode == "live":
        return OpenAIQualificationExecutor(settings=settings)
    return DeterministicQualificationExecutor(mode=mode)


def _qualification_mode(value: str) -> QualificationMode:
    if value not in {"fixture", "mock", "live"}:
        raise ValueError(
            "AI_MODE must be fixture, mock, or live for OpenAI qualification"
        )
    return cast(QualificationMode, value)


def _qualification_state(
    *,
    mode: QualificationMode,
    request: QualificationRequestV1,
    passed: bool,
    case_results: list[QualificationCaseResultV1],
) -> QualificationState:
    if not passed:
        return "failed"
    if request.check_config:
        if mode == "live":
            return "not_yet_qualified"
        return cast(QualificationState, f"{mode}_configured")
    if request.operation is not None:
        return cast(QualificationState, f"{mode}_operation_verified")
    application_verified = bool(case_results) and all(
        result.execution_scope == "application_e2e"
        and result.model_runs_persisted
        and result.workspace_deleted
        for result in case_results
    )
    if mode == "live" and application_verified:
        return (
            "live_qualified"
            if request.all_cases and len(case_results) == 3
            else "live_e2e_case_verified"
        )
    if application_verified:
        return cast(QualificationState, f"{mode}_e2e_verified")
    return cast(QualificationState, f"{mode}_contract_verified")


def _failed_operation(
    *,
    operation: AiOperationName,
    settings: Settings,
    mode: QualificationMode,
    exc: Exception,
) -> OperationExecutionV1:
    definition = get_ai_operation_definition(operation)
    error_code, error_message, provider_request_id = _safe_error(exc)
    return OperationExecutionV1(
        operation=operation.value,
        provider="openai" if mode == "live" else mode,
        endpoint_family="responses",
        model=settings.resolve_openai_model(
            operation.value,
            vision=operation is AiOperationName.MEDIA_OBSERVATION,
        ),
        prompt_name=definition.prompt_name,
        prompt_version=definition.prompt_version,
        schema_version=definition.schema_version,
        provider_request_id=provider_request_id,
        output={},
        output_valid=False,
        source_version_references_valid=False,
        evidence_ids_valid=False,
        timestamps_valid=False,
        silent_fixture_fallback=False,
        error_code=error_code,
        error_message=error_message,
    )


def _safe_error(exc: Exception) -> tuple[str, str, str | None]:
    if isinstance(exc, AiProviderError):
        return exc.code, exc.safe_message, exc.info.provider_request_id
    if isinstance(exc, AppError):
        details = exc.details or {}
        raw_request_id = details.get("provider_request_id")
        request_id = (
            str(raw_request_id) if raw_request_id is not None else None
        )
        return exc.code, exc.message, request_id
    return (
        "QUALIFICATION_EXECUTION_FAILED",
        f"Qualification execution failed with {type(exc).__name__}.",
        None,
    )


def _failed_semantic_output(scenario_id: str) -> GoldenSemanticOutputV1:
    return GoldenSemanticOutputV1(
        scenario_id=scenario_id,
        product_name="unavailable",
        objective="unavailable",
        pattern_name="unavailable",
        concepts=[],
        preflight_results=[],
    )


def _command_name(request: QualificationRequestV1) -> str:
    if request.check_config:
        return "check_config"
    if request.operation is not None:
        return f"operation:{resolve_operation(request.operation).value}"
    return "full_flow:all_cases" if request.all_cases else f"full_flow:{request.case}"


def _new_run_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")


def _timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
