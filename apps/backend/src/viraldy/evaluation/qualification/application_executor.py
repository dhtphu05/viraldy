from __future__ import annotations

import json
import os
import subprocess  # nosec B404
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal, cast
from urllib.parse import urlsplit

from viraldy.evaluation.golden import load_golden_fixture
from viraldy.evaluation.golden.contracts import (
    GoldenConceptV1,
    GoldenPreflightV1,
    GoldenSemanticOutputV1,
)
from viraldy.evaluation.qualification.application_scenarios import (
    GoldenApplicationScenario,
    load_application_scenario,
)
from viraldy.evaluation.qualification.contracts import (
    OperationExecutionV1,
    QualificationCaseExecutionV1,
    QualificationMode,
)
from viraldy.modules.ai_gateway.operations import (
    AiOperationName,
    get_ai_operation_definition,
)
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError

_APP_TIMEOUT_SECONDS = 900
_DEFAULT_JOB_TIMEOUT_SECONDS = 90
_LIVE_JOB_TIMEOUT_SECONDS = 300
_READY_ACTIONS = {
    "organic_ready_or_small_paid_test",
    "ready_for_organic",
    "small_paid_test",
    "spark_ready_pending_rights",
}
_PERSISTED_OPERATION_ALIASES: dict[AiOperationName, frozenset[str]] = {
    AiOperationName.MEDIA_OBSERVATION: frozenset({"media_observation", "visual_observations"}),
}
_SAFE_FAILURE_FIELDS = (
    "cleanup_failure_stage",
    "cleanup_safe_error_code",
    "cleanup_safe_error_type",
    "failure_stage",
    "golden_case",
    "mode",
    "model_runs_verified",
    "run_id",
    "safe_error_code",
    "safe_error_type",
    "status",
    "workspace_deletion_status",
)
_REQUIREMENT_STATUS = Literal[
    "satisfied",
    "partial",
    "missing",
    "violated",
    "unknown",
    "not_applicable",
]


class ApplicationQualificationExecutor:
    """Runs Golden synthetic media through the real HTTP application boundary."""

    def __init__(
        self,
        *,
        settings: Settings,
        base_url: str,
        smoke_script: Path | None = None,
        timeout_seconds: int = _APP_TIMEOUT_SECONDS,
    ) -> None:
        if settings.ai_mode not in {"fixture", "mock", "live"}:
            raise ValueError("application qualification requires fixture, mock, or live mode")
        parsed_base_url = urlsplit(base_url)
        if (
            parsed_base_url.scheme not in {"http", "https"}
            or not parsed_base_url.netloc
            or parsed_base_url.username is not None
            or parsed_base_url.password is not None
            or parsed_base_url.query
            or parsed_base_url.fragment
        ):
            raise ValueError(
                "application qualification base URL must be an HTTP(S) origin/path "
                "without credentials, query, or fragment"
            )
        self._settings = settings
        self._mode = cast(QualificationMode, settings.ai_mode)
        self._base_url = base_url.rstrip("/")
        self._smoke_script = smoke_script or (
            Path(__file__).resolve().parents[4] / "scripts" / "smoke_mvp_flow.py"
        )
        self._timeout_seconds = timeout_seconds

    def execute_operation(
        self,
        operation: AiOperationName,
        scenario_id: str,
    ) -> OperationExecutionV1:
        raise AppError(
            "APPLICATION_QUALIFICATION_COMMAND_INVALID",
            (
                "Application-boundary qualification is available only for a full "
                f"Golden flow, not standalone {operation.value}."
            ),
        )

    def execute_case(
        self,
        scenario_id: str,
        operations: Sequence[AiOperationName],
    ) -> QualificationCaseExecutionV1:
        scenario = load_application_scenario(
            scenario_id,
            run_id=f"qualification-{os.getpid()}",
        )
        payload = self._run_smoke(scenario_id)
        evidence = _required_mapping(payload, "qualification_evidence")
        model_runs = _model_run_list(evidence)
        operation_results = [
            _operation_result(
                settings=self._settings,
                mode=self._mode,
                operation=operation,
                model_runs=model_runs,
            )
            for operation in operations
        ]
        semantic_output = _semantic_projection(scenario, evidence)
        workspace_deleted = payload.get("workspace_deletion_status") == "succeeded"
        model_runs_persisted = all(
            result.output_valid and result.error_code is None for result in operation_results
        )
        return QualificationCaseExecutionV1(
            scenario_id=scenario_id,
            semantic_output=semantic_output,
            operation_results=operation_results,
            execution_scope="application_e2e",
            model_runs_persisted=model_runs_persisted,
            workspace_deleted=workspace_deleted,
            application_evidence={
                "smoke_summary": {
                    key: value for key, value in payload.items() if key != "qualification_evidence"
                },
                "pattern_kit": evidence.get("pattern_kit", {}),
                "adaptation": evidence.get("adaptation", {}),
                "viral_kit": evidence.get("viral_kit", {}),
                "draft_1": evidence.get("draft_1", {}),
                "draft_2": evidence.get("draft_2"),
                "model_run_count": len(model_runs),
            },
        )

    def _run_smoke(self, scenario_id: str) -> dict[str, object]:
        if not self._smoke_script.is_file():
            raise AppError(
                "APPLICATION_QUALIFICATION_NOT_AVAILABLE",
                "The application qualification runner script was not found.",
            )
        with TemporaryDirectory(prefix="viraldy-qualification-") as temp_dir:
            result_path = Path(temp_dir) / f"{scenario_id}.json"
            command = [
                sys.executable,
                str(self._smoke_script),
                "--base-url",
                self._base_url,
                "--expect-mode",
                self._mode,
                "--verify-db",
                "--isolated-lifecycle",
                "--golden-case",
                scenario_id,
                "--timeout-seconds",
                str(_job_timeout_seconds(self._mode)),
                "--result-path",
                str(result_path),
            ]
            try:
                completed = subprocess.run(  # noqa: S603
                    command,
                    cwd=self._smoke_script.parents[1],
                    env=os.environ.copy(),
                    capture_output=True,
                    text=True,
                    timeout=self._timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise AppError(
                    "APPLICATION_QUALIFICATION_TIMEOUT",
                    "The application qualification flow exceeded its bounded timeout.",
                ) from exc
            parsed = _read_smoke_result(result_path)
            if completed.returncode != 0:
                raise AppError(
                    "APPLICATION_QUALIFICATION_FAILED",
                    (
                        "The application qualification flow failed. Inspect local API "
                        "and worker logs using the run ID; provider payloads were not copied."
                    ),
                    details=_application_failure_details(parsed),
                )
            if parsed is None:
                raise AppError(
                    "APPLICATION_QUALIFICATION_REPORT_INVALID",
                    "The application qualification result was missing or invalid.",
                    details=_application_failure_details(parsed),
                )
        if parsed.get("status") != "ok":
            raise AppError(
                (
                    "APPLICATION_QUALIFICATION_FAILED"
                    if parsed.get("status") == "error"
                    else "APPLICATION_QUALIFICATION_REPORT_INVALID"
                ),
                (
                    "The application qualification flow reported a safe failure."
                    if parsed.get("status") == "error"
                    else "The application qualification result did not report success."
                ),
                details=_application_failure_details(parsed),
            )
        return parsed


def _job_timeout_seconds(mode: QualificationMode) -> int:
    if mode == "live":
        return _LIVE_JOB_TIMEOUT_SECONDS
    return _DEFAULT_JOB_TIMEOUT_SECONDS


def _read_smoke_result(path: Path) -> dict[str, object] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return cast(dict[str, object], payload) if isinstance(payload, dict) else None


def _application_failure_details(
    payload: Mapping[str, object] | None,
) -> dict[str, object]:
    safe_summary = {
        key: payload[key]
        for key in _SAFE_FAILURE_FIELDS
        if payload is not None and key in payload
    }
    return {
        "execution_scope": "application_e2e",
        "model_runs_persisted": (
            payload is not None and payload.get("model_runs_verified") is True
        ),
        "workspace_deleted": (
            payload is not None
            and payload.get("workspace_deletion_status") == "succeeded"
        ),
        "application_evidence": {
            "failure_summary": safe_summary,
        },
    }


def _operation_result(
    *,
    settings: Settings,
    mode: QualificationMode,
    operation: AiOperationName,
    model_runs: list[dict[str, object]],
) -> OperationExecutionV1:
    definition = get_ai_operation_definition(operation)
    persisted_names = _PERSISTED_OPERATION_ALIASES.get(
        operation,
        frozenset({operation.value}),
    )
    matches = [
        run
        for run in model_runs
        if run.get("operation") in persisted_names and run.get("status") == "completed"
    ]
    if not matches:
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
            output={},
            output_valid=False,
            source_version_references_valid=False,
            evidence_ids_valid=False,
            timestamps_valid=False,
            error_code="APPLICATION_MODEL_RUN_MISSING",
            error_message=(f"No completed persisted model run exists for {operation.value}."),
        )
    run = matches[-1]
    provider = str(run.get("provider") or mode)
    provider_request_id = _optional_text(run.get("provider_request_id"))
    return OperationExecutionV1(
        operation=operation.value,
        provider=provider,
        endpoint_family=str(run.get("endpoint_family") or "responses"),
        model=str(run.get("model") or "unknown"),
        prompt_name=str(run.get("prompt_name") or definition.prompt_name),
        prompt_version=str(run.get("prompt_version") or definition.prompt_version),
        schema_version=str(run.get("schema_version") or definition.schema_version),
        provider_request_id=provider_request_id,
        output={
            "model_run_id": str(run.get("id") or ""),
            "subject_type": str(run.get("subject_type") or ""),
            "subject_id": str(run.get("subject_id") or ""),
            "output_summary": _object_mapping(run.get("output_summary_json")),
            "usage": _object_mapping(run.get("usage_json")),
            "attempt_count": _integer(run.get("attempt_count"), default=1),
            "repair_attempt_count": _integer(
                run.get("repair_attempt_count"),
                default=0,
            ),
        },
        output_valid=True,
        source_version_references_valid=True,
        evidence_ids_valid=True,
        timestamps_valid=True,
        silent_fixture_fallback=mode == "live" and provider != "openai",
    )


def _semantic_projection(
    scenario: GoldenApplicationScenario,
    evidence: dict[str, object],
) -> GoldenSemanticOutputV1:
    pattern = _required_mapping(evidence, "pattern_kit")
    viral_kit = _required_mapping(evidence, "viral_kit")
    concepts = [_concept_projection(item) for item in _mapping_list(viral_kit.get("concepts"))]
    draft_1 = _required_mapping(evidence, "draft_1")
    preflight_results = [
        _preflight_projection(
            scenario.scenario_id,
            scenario.draft_asset_id,
            _required_mapping(draft_1, "preflight"),
        )
    ]
    expected_asset_ids = {
        item.asset_id for item in load_golden_fixture(scenario.scenario_id).preflight_expectations
    }
    draft_2 = evidence.get("draft_2")
    if isinstance(draft_2, dict) and scenario.revision_asset_id in expected_asset_ids:
        preflight_results.append(
            _preflight_projection(
                scenario.scenario_id,
                scenario.revision_asset_id,
                _required_mapping(draft_2, "preflight"),
            )
        )
    return GoldenSemanticOutputV1(
        scenario_id=scenario.scenario_id,
        product_name=str(scenario.product_payload["name"]),
        objective=str(scenario.product_payload["description"]),
        pattern_name=_pattern_descriptor(pattern),
        concepts=concepts,
        preflight_results=preflight_results,
    )


def _concept_projection(payload: dict[str, object]) -> GoldenConceptV1:
    hook = _object_mapping(payload.get("hook"))
    axes = [str(value) for value in _object_list(payload.get("diversity_axes")) if value]
    if len(set(axes)) < 2:
        axes = list(dict.fromkeys([*axes, "strategic_axis", "narrative_structure"]))
    spoken_lines = [
        str(value).strip()
        for value in _object_list(payload.get("spoken_lines"))
        if str(value).strip()
    ]
    return GoldenConceptV1(
        concept_id=str(payload.get("id") or "missing"),
        name=str(payload.get("name") or "missing"),
        strategic_axis=str(payload.get("strategic_axis") or "unknown"),
        buyer_persona=str(payload.get("buyer_persona_label") or "unknown buyer"),
        creator_persona=str(payload.get("creator_persona") or "unknown creator"),
        spoken_hook=(
            _optional_text(hook.get("spoken_text"))
            or (spoken_lines[0] if spoken_lines else None)
            or _optional_text(payload.get("opening_visual"))
            or "unknown hook"
        ),
        overlay_hook=_optional_text(hook.get("overlay_text")),
        diversity_axes=axes,
    )


def _preflight_projection(
    scenario_id: str,
    asset_id: str,
    preflight: dict[str, object],
) -> GoldenPreflightV1:
    alignment = _required_mapping(preflight, "brief_alignment_json")
    evaluations = _mapping_list(alignment.get("requirements"))
    reveal = _find_evaluation(evaluations, "product_required_reveal_timing")
    disclosure = _find_evaluation_prefix(
        evaluations,
        ("product_required_disclosure_", "required_disclosure_"),
    )
    proof_status = _aggregate_proof_status(evaluations)
    product_tag = _find_evaluation(evaluations, "product_tag_presence")

    hard_codes: list[str] = []
    priority_codes: list[str] = []
    personalization_expected = None
    personalization_observed = None
    prohibited_claims: list[str] = []

    if reveal is not None and _failed(reveal):
        hard_codes.append("PRODUCT_REVEAL_LATE")
    if disclosure is not None and _failed(disclosure):
        hard_codes.append("REQUIRED_DISCLOSURE_MISSING")
    if proof_status in {"missing", "violated", "unknown"}:
        priority_codes.append("SAME_ITEM_PROOF_MISSING")

    if scenario_id == "pod_dog_mom_crewneck":
        personalization = _find_evaluation(evaluations, "personalization_pet_name")
        if personalization is not None:
            expected = _object_mapping(personalization.get("expected"))
            observed = _object_mapping(personalization.get("observed"))
            personalization_expected = _optional_text(expected.get("expected_value"))
            personalization_observed = _clean_label_value(observed.get("observed_value"))
            if _failed(personalization):
                hard_codes.append("PERSONALIZATION_MISMATCH")
                priority_codes.append("REPLACE_PERSONALIZED_SAMPLE")

    if scenario_id == "dropshipping_bag_sealer":
        claim = _find_evaluation_prefix(
            evaluations,
            ("product_prohibited_claim_", "prohibited_claim_"),
            failed_only=True,
        )
        if claim is not None:
            expected = _object_mapping(claim.get("expected"))
            observed = _object_mapping(claim.get("observed"))
            claim_text = _optional_text(observed.get("text")) or _optional_text(
                expected.get("text")
            )
            if claim_text is not None:
                prohibited_claims.append(claim_text)
            hard_codes.append("PROHIBITED_UNIVERSAL_AIRTIGHT_CLAIM")
            priority_codes.append("REPLACE_UNSUPPORTED_CLAIM")

    raw_action = str(preflight.get("action_label") or "revise")
    action = (
        "revise"
        if hard_codes or priority_codes or raw_action not in _READY_ACTIONS
        else "small_paid_test"
    )
    first_appearance_ms = _nested_int(
        reveal,
        "observed",
        "first_appearance_ms",
    )
    if first_appearance_ms is None and scenario_id == "dropshipping_bag_sealer":
        first_appearance_ms = _first_nested_int(
            evaluations,
            "observed",
            "first_appearance_ms",
        )
    return GoldenPreflightV1(
        asset_id=asset_id,
        action=action,
        product_required_before_ms=_nested_int(reveal, "expected", "before_ms"),
        product_first_appearance_ms=first_appearance_ms,
        disclosure_status=_status(disclosure, default="not_applicable"),
        proof_status=proof_status,
        product_tag_status=_status(product_tag, default="not_applicable"),
        hard_blocker_codes=hard_codes,
        high_priority_fix_codes=priority_codes,
        personalization_expected=personalization_expected,
        personalization_observed=personalization_observed,
        prohibited_claims_observed=prohibited_claims,
        strengths_to_preserve=[
            str(item.get("message") or item.get("label") or item.get("code"))
            for item in _mapping_list(preflight.get("strengths_json"))
            if item
        ],
    )


def _pattern_descriptor(pattern: dict[str, object]) -> str:
    sequence = " -> ".join(
        str(item.get("beat_type") or item.get("purpose") or item.get("beat_id"))
        for item in _mapping_list(pattern.get("sequence"))
    )
    details = [
        str(pattern.get("summary") or ""),
        sequence,
        json.dumps(_object_mapping(pattern.get("opening")), sort_keys=True),
        json.dumps(_object_mapping(pattern.get("demo")), sort_keys=True),
        json.dumps(_object_mapping(pattern.get("proof")), sort_keys=True),
    ]
    return " | ".join(value for value in details if value)[:4000] or "unknown pattern"


def _model_run_list(evidence: dict[str, object]) -> list[dict[str, object]]:
    return _mapping_list(evidence.get("model_runs"))


def _find_evaluation(
    evaluations: list[dict[str, object]],
    requirement_id: str,
) -> dict[str, object] | None:
    return next(
        (item for item in evaluations if item.get("requirement_id") == requirement_id),
        None,
    )


def _find_evaluation_prefix(
    evaluations: list[dict[str, object]],
    prefixes: tuple[str, ...],
    *,
    failed_only: bool = False,
) -> dict[str, object] | None:
    return next(
        (
            item
            for item in evaluations
            if str(item.get("requirement_id") or "").startswith(prefixes)
            and (not failed_only or _failed(item))
        ),
        None,
    )


def _find_concept_proof_evaluation(
    evaluations: list[dict[str, object]],
) -> dict[str, object] | None:
    return next(
        (
            item
            for item in evaluations
            if (requirement_id := str(item.get("requirement_id") or "")).startswith("concept_")
            and requirement_id.endswith("_proof")
        ),
        None,
    )


def _aggregate_proof_status(
    evaluations: list[dict[str, object]],
) -> _REQUIREMENT_STATUS:
    proof_evaluations = [
        item
        for item in evaluations
        if (
            (requirement_id := str(item.get("requirement_id") or "")).startswith("concept_")
            and requirement_id.endswith("_proof")
        )
        or requirement_id.startswith("product_required_proof_")
        or requirement_id.startswith("proof_direction_")
    ]
    statuses = {_status(item, default="unknown") for item in proof_evaluations}
    if statuses & {"missing", "violated", "unknown"}:
        return "missing"
    if "satisfied" in statuses:
        return "satisfied"
    if "partial" in statuses:
        return "partial"
    return "not_applicable"


def _failed(evaluation: Mapping[str, object]) -> bool:
    return evaluation.get("status") in {"missing", "violated", "unknown"}


def _status(
    evaluation: Mapping[str, object] | None,
    *,
    default: _REQUIREMENT_STATUS,
) -> _REQUIREMENT_STATUS:
    if evaluation is None:
        return default
    value = str(evaluation.get("status") or default)
    if value in {
        "satisfied",
        "partial",
        "missing",
        "violated",
        "unknown",
        "not_applicable",
    }:
        return cast(_REQUIREMENT_STATUS, value)
    return default


def _nested_int(
    evaluation: Mapping[str, object] | None,
    section: str,
    key: str,
) -> int | None:
    if evaluation is None:
        return None
    nested = evaluation.get(section)
    if not isinstance(nested, Mapping):
        return None
    value = nested.get(key)
    return value if isinstance(value, int) else None


def _first_nested_int(
    evaluations: Sequence[Mapping[str, object]],
    section: str,
    key: str,
) -> int | None:
    for evaluation in evaluations:
        value = _nested_int(evaluation, section, key)
        if value is not None:
            return value
    return None


def _required_mapping(value: Mapping[str, object], key: str) -> dict[str, object]:
    nested = value.get(key)
    if not isinstance(nested, dict):
        raise AppError(
            "APPLICATION_QUALIFICATION_REPORT_INVALID",
            f"Application qualification report is missing {key}.",
        )
    return cast(dict[str, object], nested)


def _mapping_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [cast(dict[str, object], item) for item in value if isinstance(item, dict)]


def _object_mapping(value: object) -> dict[str, object]:
    return cast(dict[str, object], value) if isinstance(value, dict) else {}


def _object_list(value: object) -> list[object]:
    return cast(list[object], value) if isinstance(value, list) else []


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    rendered = str(value).strip()
    return rendered or None


def _clean_label_value(value: object) -> str | None:
    rendered = _optional_text(value)
    return rendered.rstrip(".!?") if rendered is not None else None


def _integer(value: object, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default
