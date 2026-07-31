from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import cast

import pytest

from viraldy.evaluation.golden import (
    load_golden_fixture,
    validate_golden_semantics,
)
from viraldy.evaluation.golden.contracts import GoldenPreflightV1
from viraldy.evaluation.qualification.application_executor import (
    ApplicationQualificationExecutor,
    _job_timeout_seconds,
    _preflight_projection,
)
from viraldy.evaluation.qualification.application_scenarios import (
    load_application_scenario,
)
from viraldy.evaluation.qualification.catalog import FULL_FLOW_OPERATIONS
from viraldy.modules.ai_gateway.operations import AiOperationName
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError


class _InMemoryApplicationExecutor(ApplicationQualificationExecutor):
    def __init__(self, result: dict[str, object]) -> None:
        super().__init__(
            settings=Settings(
                _env_file=None,
                ai_mode="mock",
                ai_provider="openai_compatible",
                ai_base_url="http://127.0.0.1:8787/v1",
                ai_api_key="mock-key",
                ai_text_model="mock-text",
                ai_vision_model="mock-vision",
            ),
            base_url="http://127.0.0.1:8001/api/v1",
        )
        self._result = result

    def _run_smoke(self, scenario_id: str) -> dict[str, object]:
        assert scenario_id == self._result["golden_case"]
        return self._result


@pytest.mark.parametrize(
    "scenario_id",
    [
        "home_travel_steamer",
        "pod_dog_mom_crewneck",
        "dropshipping_bag_sealer",
    ],
)
def test_application_executor_projects_persisted_semantics_and_runs(
    scenario_id: str,
) -> None:
    result = _application_result(scenario_id)

    execution = _InMemoryApplicationExecutor(result).execute_case(
        scenario_id,
        FULL_FLOW_OPERATIONS,
    )

    assert execution.execution_scope == "application_e2e"
    assert execution.model_runs_persisted
    assert execution.workspace_deleted
    assert len(execution.operation_results) == len(FULL_FLOW_OPERATIONS)
    assert all(item.output_valid for item in execution.operation_results)
    report = validate_golden_semantics(
        load_golden_fixture(scenario_id),
        execution.semantic_output,
    )
    assert report.passed, [check.check for check in report.checks if not check.passed]
    expected_asset_ids = {
        item.asset_id for item in load_golden_fixture(scenario_id).preflight_expectations
    }
    assert {
        item.asset_id for item in execution.semantic_output.preflight_results
    } == expected_asset_ids


def test_application_executor_rejects_credentialed_base_url() -> None:
    with pytest.raises(ValueError, match="without credentials"):
        ApplicationQualificationExecutor(
            settings=Settings(_env_file=None, ai_mode="mock"),
            base_url="http://user:secret@127.0.0.1:8001/api/v1",
        )


def test_application_executor_allows_longer_live_provider_jobs() -> None:
    assert _job_timeout_seconds("live") == 300
    assert _job_timeout_seconds("mock") == 90
    assert _job_timeout_seconds("fixture") == 90


@pytest.mark.parametrize("returncode", [0, 1])
def test_application_executor_preserves_safe_failure_stage_and_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    returncode: int,
) -> None:
    smoke_script = tmp_path / "smoke.py"
    smoke_script.write_text("# test runner\n", encoding="utf-8")
    executor = ApplicationQualificationExecutor(
        settings=Settings(
            _env_file=None,
            ai_mode="live",
            ai_provider="openai",
            openai_api_key="unit-test-key",
        ),
        base_url="http://127.0.0.1:8001/api/v1",
        smoke_script=smoke_script,
    )

    def failed_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        result_path = Path(command[command.index("--result-path") + 1])
        result_path.write_text(
            json.dumps(
                {
                    "status": "error",
                    "mode": "live",
                    "golden_case": "home_travel_steamer",
                    "run_id": "live-test",
                    "failure_stage": "database_verification",
                    "model_runs_verified": True,
                    "safe_error_code": "SMOKE_FLOW_FAILED",
                    "safe_error_type": "SmokeFailure",
                    "workspace_deletion_status": "succeeded",
                    "untrusted_detail": "must not be copied",
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(
            command,
            returncode=returncode,
            stdout="provider payload",
            stderr="credential-shaped diagnostic",
        )

    monkeypatch.setattr(subprocess, "run", failed_run)

    with pytest.raises(AppError) as caught:
        executor._run_smoke("home_travel_steamer")

    assert caught.value.code == "APPLICATION_QUALIFICATION_FAILED"
    assert caught.value.details == {
        "application_evidence": {
            "failure_summary": {
                "failure_stage": "database_verification",
                "golden_case": "home_travel_steamer",
                "mode": "live",
                "model_runs_verified": True,
                "run_id": "live-test",
                "safe_error_code": "SMOKE_FLOW_FAILED",
                "safe_error_type": "SmokeFailure",
                "status": "error",
                "workspace_deletion_status": "succeeded",
            }
        },
        "execution_scope": "application_e2e",
        "model_runs_persisted": True,
        "workspace_deleted": True,
    }


def test_application_executor_reports_missing_persisted_operation() -> None:
    result = _application_result("pod_dog_mom_crewneck")
    evidence = cast(dict[str, object], result["qualification_evidence"])
    model_runs = cast(list[dict[str, object]], evidence["model_runs"])
    evidence["model_runs"] = [
        item for item in model_runs if item["operation"] != AiOperationName.CREATIVE_DNA_BUILD.value
    ]

    execution = _InMemoryApplicationExecutor(result).execute_case(
        "pod_dog_mom_crewneck",
        FULL_FLOW_OPERATIONS,
    )

    assert execution.model_runs_persisted is False
    missing = next(
        item
        for item in execution.operation_results
        if item.operation == AiOperationName.CREATIVE_DNA_BUILD.value
    )
    assert missing.error_code == "APPLICATION_MODEL_RUN_MISSING"


def test_preflight_projection_prefers_concept_proof_over_presentation_direction() -> None:
    projection = _preflight_projection(
        "pod_dog_mom_crewneck",
        "pod_personalization_mismatch",
        {
            "action_label": "reject",
            "brief_alignment_json": {
                "requirements": [
                    {
                        "requirement_id": "concept_1_proof",
                        "status": "satisfied",
                    },
                    {
                        "requirement_id": "proof_direction_1",
                        "status": "partial",
                    },
                    {
                        "requirement_id": "personalization_pet_name",
                        "status": "violated",
                        "expected": {"expected_value": "Milo"},
                        "observed": {"observed_value": "Miles"},
                    },
                ]
            },
            "strengths_json": [],
        },
    )

    assert projection.proof_status == "satisfied"
    assert "SAME_ITEM_PROOF_MISSING" not in projection.high_priority_fix_codes


def test_preflight_projection_blocks_when_required_product_proof_is_missing() -> None:
    projection = _preflight_projection(
        "home_travel_steamer",
        "ugc_missing_product_timing",
        {
            "action_label": "reject",
            "brief_alignment_json": {
                "requirements": [
                    {
                        "requirement_id": "concept_1_proof",
                        "status": "satisfied",
                    },
                    {
                        "requirement_id": "product_required_proof_1",
                        "status": "missing",
                    },
                ]
            },
            "strengths_json": [],
        },
    )

    assert projection.proof_status == "missing"
    assert projection.high_priority_fix_codes == ["SAME_ITEM_PROOF_MISSING"]


def _application_result(scenario_id: str) -> dict[str, object]:
    fixture = load_golden_fixture(scenario_id)
    scenario = load_application_scenario(scenario_id, run_id="unit")
    evidence: dict[str, object] = {
        "pattern_kit": {
            "summary": fixture.pattern_name,
            "sequence": [],
            "opening": {},
            "demo": {},
            "proof": {},
        },
        "adaptation": {"status": "completed"},
        "viral_kit": {
            "concepts": [
                {
                    "id": concept.concept_id,
                    "name": concept.name,
                    "strategic_axis": concept.strategic_axis,
                    "buyer_persona_label": concept.buyer_persona,
                    "creator_persona": concept.creator_persona,
                    "hook": {
                        "spoken_text": concept.spoken_hook,
                        "overlay_text": concept.overlay_hook,
                    },
                    "diversity_axes": concept.diversity_axes,
                }
                for concept in fixture.concepts
            ]
        },
        "model_runs": _model_runs(),
    }
    expected_by_asset = {item.asset_id: item for item in fixture.preflight_expectations}
    draft = expected_by_asset[scenario.draft_asset_id]
    evidence["draft_1"] = {
        "preflight": _preflight_payload(draft),
        "presentation": {},
    }
    if scenario.revision_asset_id in expected_by_asset:
        evidence["draft_2"] = {
            "preflight": _preflight_payload(expected_by_asset[scenario.revision_asset_id]),
            "presentation": {},
        }
    return {
        "golden_case": scenario_id,
        "workspace_deletion_status": "succeeded",
        "qualification_evidence": evidence,
    }


def _model_runs() -> list[dict[str, object]]:
    runs: list[dict[str, object]] = []
    for operation in FULL_FLOW_OPERATIONS:
        persisted_operation = (
            "visual_observations"
            if operation is AiOperationName.MEDIA_OBSERVATION
            else operation.value
        )
        runs.append(
            {
                "id": f"model-run-{operation.value}",
                "operation": persisted_operation,
                "status": "completed",
                "provider": "openai_compatible",
                "endpoint_family": "chat_completions",
                "model": "mock-model",
                "prompt_name": f"{operation.value}_prompt",
                "prompt_version": "v2",
                "schema_version": "v1",
                "provider_request_id": f"provider-{operation.value}",
                "subject_type": operation.value,
                "subject_id": f"subject-{operation.value}",
                "output_summary_json": {},
                "usage_json": {},
                "attempt_count": 1,
                "repair_attempt_count": 0,
            }
        )
    return runs


def _preflight_payload(expected: GoldenPreflightV1) -> dict[str, object]:
    requirements: list[dict[str, object]] = []
    if expected.product_required_before_ms is not None:
        requirements.append(
            {
                "requirement_id": "product_required_reveal_timing",
                "status": (
                    "satisfied"
                    if expected.product_first_appearance_ms is not None
                    and expected.product_first_appearance_ms <= expected.product_required_before_ms
                    else "violated"
                ),
                "expected": {
                    "before_ms": expected.product_required_before_ms,
                },
                "observed": {
                    "first_appearance_ms": expected.product_first_appearance_ms,
                },
            }
        )
    elif expected.product_first_appearance_ms is not None:
        requirements.append(
            {
                "requirement_id": "concept_1_scene_1_product",
                "status": "satisfied",
                "expected": {},
                "observed": {
                    "first_appearance_ms": expected.product_first_appearance_ms,
                },
            }
        )
    if expected.disclosure_status != "not_applicable":
        requirements.append(
            {
                "requirement_id": "required_disclosure_1",
                "status": expected.disclosure_status,
                "expected": {},
                "observed": {},
            }
        )
    if expected.proof_status != "not_applicable":
        requirements.append(
            {
                "requirement_id": "proof_direction_1",
                "status": expected.proof_status,
                "expected": {},
                "observed": {},
            }
        )
    if expected.product_tag_status != "not_applicable":
        requirements.append(
            {
                "requirement_id": "product_tag_presence",
                "status": expected.product_tag_status,
                "expected": {},
                "observed": {},
            }
        )
    if expected.personalization_expected is not None:
        requirements.append(
            {
                "requirement_id": "personalization_pet_name",
                "status": (
                    "satisfied"
                    if expected.personalization_expected == expected.personalization_observed
                    else "violated"
                ),
                "expected": {
                    "expected_value": expected.personalization_expected,
                },
                "observed": {
                    "observed_value": expected.personalization_observed,
                },
            }
        )
    if expected.prohibited_claims_observed:
        requirements.append(
            {
                "requirement_id": "product_prohibited_claim_1",
                "status": "violated",
                "expected": {},
                "observed": {
                    "text": expected.prohibited_claims_observed[0],
                },
            }
        )
    return {
        "action_label": ("small_paid_test" if expected.action == "small_paid_test" else "revise"),
        "brief_alignment_json": {"requirements": requirements},
        "strengths_json": [{"message": item} for item in expected.strengths_to_preserve],
    }
