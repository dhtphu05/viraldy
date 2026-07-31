from __future__ import annotations

import importlib.util
import json
import os
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
from pydantic import SecretStr

import viraldy.evaluation.qualification.executors as qualification_executors
from viraldy.evaluation.golden import (
    GoldenSemanticOutputV1,
    load_golden_fixture,
)
from viraldy.evaluation.qualification import (
    DeterministicQualificationExecutor,
    OperationExecutionV1,
    QualificationCaseExecutionV1,
    QualificationExecutor,
    QualificationRequestV1,
    QualificationRunner,
    require_openai_live_opt_in,
)
from viraldy.modules.ai_gateway.operations import AiOperationName, build_ai_operation_fixture
from viraldy.modules.ai_gateway.providers.base import ProviderEndpointFamily
from viraldy.platform.config.settings import Settings


def _load_qualification_script() -> ModuleType:
    script_path = Path(__file__).parents[2] / "scripts" / "qualify_openai.py"
    spec = importlib.util.spec_from_file_location("qualify_openai", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load qualify_openai.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


qualify_openai = _load_qualification_script()


def _settings(
    mode: str,
    *,
    api_key: str | None = None,
    provider: str = "openai",
) -> Settings:
    return Settings(
        _env_file=None,
        ai_mode=mode,
        ai_provider=provider,
        openai_api_key=SecretStr(api_key) if api_key else None,
    )


def _runner(
    tmp_path: Path,
    mode: str,
    *,
    executor: QualificationExecutor | None = None,
    api_key: str | None = None,
) -> QualificationRunner:
    return QualificationRunner(
        settings=_settings(mode, api_key=api_key),
        executor=executor,
        report_root=tmp_path / "evaluation" / "reports" / "openai",
        run_id_factory=lambda: "20260731T120000000000Z",
    )


@pytest.mark.parametrize("mode", ["fixture", "mock"])
def test_check_config_is_keyless_and_reports_only_safe_values(
    tmp_path: Path,
    mode: str,
) -> None:
    outcome = _runner(tmp_path, mode).run(
        QualificationRequestV1(check_config=True)
    )

    assert outcome.exit_code == 0
    assert outcome.report.passed
    assert outcome.report.mode == mode
    assert outcome.report.qualification_state == f"{mode}_configured"
    assert outcome.report.safe_config.api_key_configured is False
    serialized = outcome.report.model_dump_json()
    assert "OPENAI_API_KEY" not in serialized
    assert "sk-" not in serialized


def test_operation_alias_runs_registered_contract_without_network(
    tmp_path: Path,
) -> None:
    outcome = _runner(tmp_path, "fixture").run(
        QualificationRequestV1(operation="pattern_kit")
    )

    assert outcome.exit_code == 0
    assert [item.operation for item in outcome.report.operation_results] == [
        AiOperationName.PATTERN_KIT_EXTRACT.value
    ]
    operation = outcome.report.operation_results[0]
    assert operation.output_valid
    assert operation.prompt_version
    assert operation.schema_version
    assert operation.provider == "fixture"
    assert operation.provider_request_id is None


def test_full_flow_all_cases_passes_authoritative_golden_gates(
    tmp_path: Path,
) -> None:
    outcome = _runner(tmp_path, "mock").run(
        QualificationRequestV1(
            full_flow=True,
            all_cases=True,
            write_report=True,
        )
    )

    assert outcome.exit_code == 0
    assert outcome.report.passed
    assert outcome.report.qualification_state == "mock_contract_verified"
    assert [item.scenario_id for item in outcome.report.case_results] == [
        "home_travel_steamer",
        "pod_dog_mom_crewneck",
        "dropshipping_bag_sealer",
    ]
    assert outcome.report.sample_size == 3
    assert all(item.passed for item in outcome.report.case_results)
    assert all(gate.passed for gate in outcome.report.hard_gates)
    assert all(gate.passed for gate in outcome.report.semantic_gates)
    assert outcome.report.confidence_note
    assert outcome.report.product_readiness.status == "insufficient_evidence"
    assert outcome.report.product_readiness.product_ready is False
    assert outcome.report.product_readiness.value_score == 5
    assert outcome.report.product_readiness.generic_output_rate == 0
    assert outcome.report_paths is not None
    assert sorted(
        path.name for path in outcome.report_paths.outputs_dir.glob("*.json")
    ) == [
        "dropshipping_bag_sealer.json",
        "home_travel_steamer.json",
        "pod_dog_mom_crewneck.json",
    ]
    assert not list(outcome.report_paths.failures_dir.iterdir())
    assert not list(outcome.report_paths.best_outputs_dir.iterdir())


class _ProductDriftExecutor:
    def __init__(self) -> None:
        self._base = DeterministicQualificationExecutor(mode="mock")

    def execute_operation(
        self,
        operation: AiOperationName,
        scenario_id: str,
    ) -> OperationExecutionV1:
        return self._base.execute_operation(operation, scenario_id)

    def execute_case(
        self,
        scenario_id: str,
        operations: Sequence[AiOperationName],
    ) -> QualificationCaseExecutionV1:
        execution = self._base.execute_case(scenario_id, operations)
        payload = execution.semantic_output.model_dump(mode="json")
        payload["product_name"] = "Generic Product"
        return execution.model_copy(
            update={
                "semantic_output": GoldenSemanticOutputV1.model_validate(payload),
            }
        )


def test_golden_semantic_drift_fails_required_gate_and_exit_code(
    tmp_path: Path,
) -> None:
    outcome = _runner(
        tmp_path,
        "mock",
        executor=_ProductDriftExecutor(),
    ).run(
        QualificationRequestV1(full_flow=True, case="tiktok-shop")
    )

    assert outcome.exit_code == 1
    assert outcome.report.passed is False
    assert outcome.report.case_results[0].passed is False
    failed = {
        gate.gate
        for gate in outcome.report.case_results[0].semantic_gates
        if not gate.passed
    }
    assert "critical_product_fact_hallucinations" in failed
    assert "golden_semantic_equivalence" in failed


class _MissingLiveRequestIdExecutor:
    def __init__(self) -> None:
        self._base = DeterministicQualificationExecutor(mode="mock")

    def execute_operation(
        self,
        operation: AiOperationName,
        scenario_id: str,
    ) -> OperationExecutionV1:
        execution = self._base.execute_operation(operation, scenario_id)
        return execution.model_copy(
            update={
                "provider": "openai",
                "provider_request_id": None,
            }
        )

    def execute_case(
        self,
        scenario_id: str,
        operations: Sequence[AiOperationName],
    ) -> QualificationCaseExecutionV1:
        fixture = load_golden_fixture(scenario_id)
        operation_results = [
            self.execute_operation(operation, scenario_id)
            for operation in operations
        ]
        return QualificationCaseExecutionV1(
            scenario_id=scenario_id,
            semantic_output=GoldenSemanticOutputV1(
                scenario_id=fixture.scenario_id,
                product_name=fixture.product_name,
                objective=fixture.objective,
                pattern_name=fixture.pattern_name,
                concepts=fixture.concepts,
                preflight_results=fixture.preflight_expectations,
            ),
            operation_results=operation_results,
            semantic_provider_request_id=None,
        )


def test_live_cannot_pass_without_provider_request_id(
    tmp_path: Path,
) -> None:
    outcome = _runner(
        tmp_path,
        "live",
        api_key="-".join(("unit", "test", "provider", "credential")),
        executor=_MissingLiveRequestIdExecutor(),
    ).run(
        QualificationRequestV1(full_flow=True, case="pod")
    )

    assert outcome.exit_code == 1
    assert outcome.report.qualification_state == "failed"
    request_id_gate = next(
        gate
        for gate in outcome.report.hard_gates
        if gate.gate == "live_provider_request_ids"
    )
    assert request_id_gate.passed is False


class _ApplicationBoundaryExecutor(_MissingLiveRequestIdExecutor):
    def execute_operation(
        self,
        operation: AiOperationName,
        scenario_id: str,
    ) -> OperationExecutionV1:
        execution = self._base.execute_operation(operation, scenario_id)
        return execution.model_copy(
            update={
                "provider": "openai",
                "provider_request_id": f"provider-{operation.value}-{scenario_id}",
            }
        )

    def execute_case(
        self,
        scenario_id: str,
        operations: Sequence[AiOperationName],
    ) -> QualificationCaseExecutionV1:
        execution = super().execute_case(scenario_id, operations)
        fixture = load_golden_fixture(scenario_id)
        return execution.model_copy(
            update={
                "semantic_provider_request_id": f"semantic-{scenario_id}",
                "execution_scope": "application_e2e",
                "model_runs_persisted": True,
                "workspace_deleted": True,
                "application_evidence": {
                    "pattern_kit": {"summary": fixture.pattern_name},
                    "viral_kit": {
                        "concepts": [
                            concept.model_dump(mode="json")
                            for concept in fixture.concepts
                        ]
                    },
                    "draft_1": {
                        "preflight_results": [
                            result.model_dump(mode="json")
                            for result in fixture.preflight_expectations
                        ]
                    },
                },
            }
        )


class _ContractOnlyOpenAIExecutor(_ApplicationBoundaryExecutor):
    def execute_case(
        self,
        scenario_id: str,
        operations: Sequence[AiOperationName],
    ) -> QualificationCaseExecutionV1:
        execution = super().execute_case(scenario_id, operations)
        return execution.model_copy(
            update={
                "execution_scope": "contract",
                "model_runs_persisted": False,
                "workspace_deleted": False,
            }
        )


def test_live_qualification_requires_application_boundary_and_cleanup(
    tmp_path: Path,
) -> None:
    contract_outcome = _runner(
        tmp_path,
        "live",
        api_key="-".join(("unit", "test", "provider", "credential")),
        executor=_ApplicationBoundaryExecutor(),
    ).run(QualificationRequestV1(full_flow=True, case="pod"))
    assert contract_outcome.report.qualification_state == "live_e2e_case_verified"

    all_cases = _runner(
        tmp_path,
        "live",
        api_key="-".join(("unit", "test", "provider", "credential")),
        executor=_ApplicationBoundaryExecutor(),
    ).run(QualificationRequestV1(full_flow=True, all_cases=True))
    assert all_cases.report.qualification_state == "live_qualified"
    assert all_cases.report.product_readiness.status == "ready_for_limited_beta"
    assert all_cases.report.product_readiness.product_ready
    assert all_cases.report.product_readiness.best_output_count == 3

    contract_only = _runner(
        tmp_path,
        "live",
        api_key="-".join(("unit", "test", "provider", "credential")),
        executor=_ContractOnlyOpenAIExecutor(),
    ).run(QualificationRequestV1(full_flow=True, all_cases=True))
    assert contract_only.report.qualification_state == "live_contract_verified"
    assert contract_only.report.product_readiness.status == "insufficient_evidence"
    assert contract_only.report.product_readiness.product_ready is False


def test_live_report_logs_only_qualified_non_generic_best_outputs(
    tmp_path: Path,
) -> None:
    outcome = _runner(
        tmp_path,
        "live",
        api_key="-".join(("unit", "test", "provider", "credential")),
        executor=_ApplicationBoundaryExecutor(),
    ).run(
        QualificationRequestV1(
            full_flow=True,
            all_cases=True,
            write_report=True,
        )
    )

    assert outcome.report_paths is not None
    best_paths = sorted(outcome.report_paths.best_outputs_dir.glob("*.json"))
    assert [path.stem for path in best_paths] == [
        "dropshipping_bag_sealer",
        "home_travel_steamer",
        "pod_dog_mom_crewneck",
    ]
    best_payload = json.loads(best_paths[0].read_text(encoding="utf-8"))
    assert best_payload["schema_version"] == "viraldy_best_response_v1"
    assert best_payload["quality_assessment"]["value_status"] == "meaningful"
    assert best_payload["quality_assessment"]["generic_output"] is False
    assert set(best_payload["responses"]) == {
        "draft_1",
        "pattern_kit",
        "viral_kit",
    }
    assert "unit-test-provider-credential" not in best_paths[0].read_text(
        encoding="utf-8"
    )


class _ExplodingExecutor:
    def execute_operation(
        self,
        operation: AiOperationName,
        scenario_id: str,
    ) -> OperationExecutionV1:
        raise RuntimeError("boom")

    def execute_case(
        self,
        scenario_id: str,
        operations: Sequence[AiOperationName],
    ) -> QualificationCaseExecutionV1:
        raise RuntimeError("boom")


def test_execution_failure_does_not_substitute_golden_semantic_output(
    tmp_path: Path,
) -> None:
    outcome = _runner(
        tmp_path,
        "mock",
        executor=_ExplodingExecutor(),
    ).run(QualificationRequestV1(full_flow=True, case="pod"))

    assert outcome.exit_code == 1
    semantic_output = outcome.report.case_results[0].semantic_output
    assert semantic_output.product_name == "unavailable"
    assert semantic_output.concepts == []


class _CapturingSemanticProvider:
    provider_name = "openai"

    def __init__(self) -> None:
        self.semantic_inputs: list[str] = []

    def generate_structured(self, request: Any) -> Any:
        text_parts = [
            part.text for part in request.user_content if hasattr(part, "text")
        ]
        self.semantic_inputs.extend(text_parts)
        payload = json.loads(text_parts[0])
        scenario_id = str(payload["scenario"]["scenario_id"])
        fixture = load_golden_fixture(scenario_id)
        semantic_output = GoldenSemanticOutputV1(
            scenario_id=fixture.scenario_id,
            product_name=fixture.product_name,
            objective=fixture.objective,
            pattern_name=fixture.pattern_name,
            concepts=fixture.concepts,
            preflight_results=fixture.preflight_expectations,
        )
        return SimpleNamespace(
            parsed_output=semantic_output,
            provider_request_id="semantic-provider-request",
            model=request.model,
        )

    def transcribe_audio(self, request: Any) -> Any:
        raise AssertionError("qualification semantic provider must not transcribe")


def test_live_qualification_never_feeds_golden_expected_outputs_to_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operation_contexts: list[str] = []

    def execute_operation(
        settings: Settings,
        context: Any,
        output_model: Any,
        *,
        provider: Any,
    ) -> Any:
        del settings, output_model, provider
        operation_contexts.append(context.stable_json())
        qualification_input = context.operation_payload["qualification_input"]
        output = build_ai_operation_fixture(context.operation, qualification_input)
        return SimpleNamespace(
            parsed_output=output,
            provider="openai",
            endpoint_family=ProviderEndpointFamily.RESPONSES,
            model="test-openai-model",
            provider_request_id=f"provider-{context.operation.value}",
        )

    monkeypatch.setattr(
        qualification_executors,
        "execute_structured_operation",
        execute_operation,
    )
    provider = _CapturingSemanticProvider()
    executor = qualification_executors.OpenAIQualificationExecutor(
        settings=_settings(
            "live",
            api_key="-".join(("unit", "test", "provider", "credential")),
        ),
        provider=provider,
    )

    executor.execute_case(
        "home_travel_steamer",
        [AiOperationName.PATTERN_KIT_EXTRACT, AiOperationName.VIRAL_KIT_COMPOSE],
    )

    forbidden = (
        '"golden_fixture"',
        '"pattern_name"',
        '"concepts"',
        '"preflight_expectations"',
    )
    assert operation_contexts
    assert provider.semantic_inputs
    for payload in [*operation_contexts, *provider.semantic_inputs]:
        assert all(field not in payload for field in forbidden)
    semantic_payload = json.loads(provider.semantic_inputs[0])
    assert semantic_payload["operation_outputs"]


class _InvalidTimestampExecutor(_ProductDriftExecutor):
    def execute_case(
        self,
        scenario_id: str,
        operations: Sequence[AiOperationName],
    ) -> QualificationCaseExecutionV1:
        execution = self._base.execute_case(scenario_id, operations)
        payload = execution.semantic_output.model_dump(mode="json")
        first_result = payload["preflight_results"][0]
        assert isinstance(first_result, dict)
        first_result["product_first_appearance_ms"] = 999_999
        return execution.model_copy(
            update={
                "semantic_output": GoldenSemanticOutputV1.model_validate(payload),
            }
        )


def test_timestamp_outside_media_duration_fails_hard_gate(
    tmp_path: Path,
) -> None:
    outcome = _runner(
        tmp_path,
        "mock",
        executor=_InvalidTimestampExecutor(),
    ).run(
        QualificationRequestV1(full_flow=True, case="tiktok-shop")
    )

    assert outcome.exit_code == 1
    timestamp_gate = next(
        gate
        for gate in outcome.report.hard_gates
        if gate.gate == "timestamps_inside_media_duration"
    )
    assert timestamp_gate.passed is False


class _SensitiveFailureExecutor(_ProductDriftExecutor):
    def execute_case(
        self,
        scenario_id: str,
        operations: Sequence[AiOperationName],
    ) -> QualificationCaseExecutionV1:
        execution = super().execute_case(scenario_id, operations)
        operation_results = list(execution.operation_results)
        first = operation_results[0]
        fake_secret = "".join(("sk", "-", "secret-value"))
        operation_results[0] = first.model_copy(
            update={
                "output": {
                    **first.output,
                    "api_key": fake_secret,
                    "source_url": (
                        "https://storage.invalid/video?"
                        "X-Amz-Signature=private-signature"
                    ),
                }
            }
        )
        return execution.model_copy(update={"operation_results": operation_results})


def test_report_writer_uses_required_tree_and_redacts_failure_artifacts(
    tmp_path: Path,
) -> None:
    outcome = _runner(
        tmp_path,
        "mock",
        executor=_SensitiveFailureExecutor(),
    ).run(
        QualificationRequestV1(
            full_flow=True,
            case="dropshipping",
            write_report=True,
        )
    )

    assert outcome.exit_code == 1
    assert outcome.report_paths is not None
    report_paths = outcome.report_paths
    assert report_paths.root.name == "20260731T120000000000Z"
    assert report_paths.json_path.name == "qualification.json"
    assert report_paths.markdown_path.name == "qualification.md"
    assert report_paths.outputs_dir.is_dir()
    assert report_paths.failures_dir.is_dir()
    failure_path = report_paths.failures_dir / "dropshipping_bag_sealer.json"
    assert failure_path.is_file()
    written = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [report_paths.json_path, report_paths.markdown_path, failure_path]
    )
    assert "".join(("sk", "-", "secret-value")) not in written
    assert "private-signature" not in written
    assert "<redacted>" in written
    payload = json.loads(report_paths.json_path.read_text(encoding="utf-8"))
    assert payload["passed"] is False


def test_cli_exit_is_nonzero_when_a_required_gate_fails(
    tmp_path: Path,
) -> None:
    exit_code = qualify_openai.main(
        ["--full-flow", "--case", "tiktok-shop"],
        settings=_settings("mock"),
        executor=_ProductDriftExecutor(),
        report_root=tmp_path,
    )

    assert exit_code == 1


def test_cli_parser_supports_goal_commands() -> None:
    check_config = qualify_openai.parse_args(["--check-config"])
    operation = qualify_openai.parse_args(["--operation", "media_observation"])
    one_case = qualify_openai.parse_args(
        ["--full-flow", "--case", "tiktok-shop"]
    )
    all_cases = qualify_openai.parse_args(
        [
            "--full-flow",
            "--all-cases",
            "--write-report",
            "--application-base-url",
            "http://127.0.0.1:8001/api/v1",
        ]
    )

    assert check_config.check_config
    assert operation.operation == "media_observation"
    assert one_case.case == "tiktok-shop"
    assert all_cases.all_cases
    assert all_cases.write_report
    assert all_cases.application_base_url == "http://127.0.0.1:8001/api/v1"


def test_cli_rejects_application_url_outside_full_flow() -> None:
    with pytest.raises(SystemExit):
        qualify_openai.parse_args(
            [
                "--check-config",
                "--application-base-url",
                "http://127.0.0.1:8001/api/v1",
            ]
        )


def test_live_guard_skips_cleanly_without_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("VIRALDY_RUN_OPENAI_LIVE_TESTS", "1")

    with pytest.raises(pytest.skip.Exception):
        require_openai_live_opt_in(os.environ)


@pytest.mark.openai_live
def test_openai_live_operation_qualification() -> None:
    require_openai_live_opt_in(os.environ)
    outcome = QualificationRunner(
        settings=Settings(
            _env_file=None,
            ai_mode="live",
            ai_provider="openai",
            openai_api_key=SecretStr(os.environ["OPENAI_API_KEY"]),
        )
    ).run(
        QualificationRequestV1(operation="seller_decision_summary")
    )
    assert outcome.exit_code == 0
    assert outcome.report.qualification_state == "live_operation_verified"
