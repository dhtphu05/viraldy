from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

from viraldy.evaluation.qualification.contracts import (
    GateResultV1,
    QualificationReportPaths,
    QualificationReportV1,
)

_REDACTED = "<redacted>"
_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "credential",
        "password",
        "presigned_url",
        "secret",
        "signed_url",
        "token",
    }
)
_SIGNED_QUERY_KEYS = frozenset(
    {
        "awsaccesskeyid",
        "credential",
        "expires",
        "googleaccessid",
        "signature",
        "sig",
        "token",
        "x-amz-credential",
        "x-amz-signature",
    }
)
_SECRET_VALUE = re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b")


def write_qualification_report(
    report: QualificationReportV1,
    report_root: Path,
) -> QualificationReportPaths:
    root = report_root / report.run_id
    outputs_dir = root / "outputs"
    failures_dir = root / "failures"
    best_outputs_dir = root / "best_outputs"
    outputs_dir.mkdir(parents=True, exist_ok=False)
    failures_dir.mkdir(parents=True, exist_ok=False)
    best_outputs_dir.mkdir(parents=True, exist_ok=False)

    safe_report = sanitize_for_report(report.model_dump(mode="json"))
    json_path = root / "qualification.json"
    markdown_path = root / "qualification.md"
    json_path.write_text(_json_text(safe_report), encoding="utf-8")
    markdown_path.write_text(render_markdown_report(report), encoding="utf-8")

    for case in report.case_results:
        destination = outputs_dir if case.passed else failures_dir
        artifact = {
            "schema_version": "openai_qualification_case_artifact_v1",
            "run_id": report.run_id,
            "mode": report.mode,
            "qualification_state": report.qualification_state,
            "case": case.model_dump(mode="json"),
        }
        (destination / f"{case.scenario_id}.json").write_text(
            _json_text(sanitize_for_report(artifact)),
            encoding="utf-8",
        )
        if case.quality_assessment.best_output_eligible:
            best_artifact = {
                "schema_version": "viraldy_best_response_v1",
                "run_id": report.run_id,
                "mode": report.mode,
                "scenario_id": case.scenario_id,
                "quality_assessment": case.quality_assessment.model_dump(mode="json"),
                "provenance": [
                    {
                        "operation": operation.operation,
                        "provider": operation.provider,
                        "model": operation.model,
                        "prompt_name": operation.prompt_name,
                        "prompt_version": operation.prompt_version,
                        "schema_version": operation.schema_version,
                        "provider_request_id": operation.provider_request_id,
                    }
                    for operation in case.operation_results
                ],
                "semantic_output": case.semantic_output.model_dump(mode="json"),
                "responses": _best_response_sections(case.application_evidence),
            }
            (best_outputs_dir / f"{case.scenario_id}.json").write_text(
                _json_text(sanitize_for_report(best_artifact)),
                encoding="utf-8",
            )

    for operation in report.operation_results:
        destination = (
            outputs_dir
            if operation.output_valid and operation.error_code is None
            else failures_dir
        )
        artifact = {
            "schema_version": "openai_qualification_operation_artifact_v1",
            "run_id": report.run_id,
            "mode": report.mode,
            "qualification_state": report.qualification_state,
            "operation": operation.model_dump(mode="json"),
        }
        (destination / f"operation-{operation.operation}.json").write_text(
            _json_text(sanitize_for_report(artifact)),
            encoding="utf-8",
        )

    return QualificationReportPaths(
        root=root,
        json_path=json_path,
        markdown_path=markdown_path,
        outputs_dir=outputs_dir,
        failures_dir=failures_dir,
        best_outputs_dir=best_outputs_dir,
    )


def render_markdown_report(report: QualificationReportV1) -> str:
    lines = [
        "# OpenAI Qualification Report",
        "",
        f"- Run: `{report.run_id}`",
        f"- Mode: `{report.mode}`",
        f"- State: `{report.qualification_state}`",
        f"- Passed: `{str(report.passed).lower()}`",
        f"- Command: `{report.command}`",
        f"- Sample size: {report.sample_size}",
        f"- Started: `{report.started_at}`",
        f"- Completed: `{report.completed_at}`",
        "",
        "## Qualification Boundary",
        "",
        report.confidence_note,
        "",
        "## Product Readiness",
        "",
        f"- Status: `{report.product_readiness.status}`",
        (
            "- Product ready: "
            f"`{str(report.product_readiness.product_ready).lower()}`"
        ),
        f"- Value score: `{report.product_readiness.value_score:.2f}/5`",
        (
            "- Generic output rate: "
            f"`{report.product_readiness.generic_output_rate:.2%}`"
        ),
        (
            "- Qualified cases: "
            f"`{report.product_readiness.qualified_case_count}/"
            f"{report.product_readiness.required_case_count}`"
        ),
        f"- Best outputs logged: `{report.product_readiness.best_output_count}`",
        "",
        "## Safe Configuration",
        "",
        f"- Provider route: `{report.safe_config.provider_route}`",
        (
            "- API key configured: "
            f"`{str(report.safe_config.api_key_configured).lower()}`"
        ),
        f"- Base URL origin: `{report.safe_config.base_url_origin}`",
        (
            "- Provider response storage enabled: "
            f"`{str(report.safe_config.store_responses).lower()}`"
        ),
        "",
        "## Configuration Gates",
        "",
        *_gate_table(report.configuration_gates),
        "## Hard Gates",
        "",
        *_gate_table(report.hard_gates),
        "## Semantic Gates",
        "",
        *_gate_table(report.semantic_gates),
    ]
    if report.operation_results:
        lines.extend(
            [
                "## Operation Calls",
                "",
                "| Operation | Provider | Model | Request ID | Valid |",
                "|---|---|---|---|---:|",
            ]
        )
        for operation in report.operation_results:
            lines.append(
                f"| {operation.operation} | {operation.provider} | "
                f"{operation.model} | "
                f"{'present' if operation.provider_request_id else 'not applicable'} | "
                f"{'PASS' if operation.output_valid else 'FAIL'} |"
            )
        lines.append("")
    if report.case_results:
        lines.extend(
            [
                "## Golden Cases",
                "",
                "| Scenario | Domain | Result | Value | Generic | Best |",
                "|---|---|---:|---:|---:|---:|",
            ]
        )
        lines.extend(
            f"| {case.scenario_id} | {case.domain} | "
            f"{'PASS' if case.passed else 'FAIL'} | "
            f"{case.quality_assessment.value_score:.2f}/5 | "
            f"{'YES' if case.quality_assessment.generic_output else 'NO'} | "
            f"{'YES' if case.quality_assessment.best_output_eligible else 'NO'} |"
            for case in report.case_results
        )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _best_response_sections(
    application_evidence: Mapping[str, object],
) -> dict[str, object]:
    section_names = (
        "pattern_kit",
        "adaptation",
        "viral_kit",
        "draft_1",
        "draft_2",
    )
    return {
        section: application_evidence[section]
        for section in section_names
        if application_evidence.get(section) is not None
    }


def sanitize_for_report(value: object) -> object:
    if isinstance(value, Mapping):
        sanitized: dict[str, object] = {}
        for raw_key, nested in value.items():
            key = str(raw_key)
            sanitized[key] = (
                _REDACTED
                if key.casefold() in _SENSITIVE_KEYS
                else sanitize_for_report(nested)
            )
        return sanitized
    if isinstance(value, list):
        return [sanitize_for_report(item) for item in value]
    if isinstance(value, str):
        if _SECRET_VALUE.search(value) or _is_signed_url(value):
            return _REDACTED
    return value


def _is_signed_url(value: str) -> bool:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"}:
        return False
    query_keys = {key.casefold() for key, _ in parse_qsl(parsed.query)}
    return bool(query_keys & _SIGNED_QUERY_KEYS)


def _json_text(value: object) -> str:
    return f"{json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True)}\n"


def _gate_table(gates: list[GateResultV1]) -> list[str]:
    if not gates:
        return ["No gates for this command.", ""]
    lines = [
        "| Gate | Value | Threshold | Result |",
        "|---|---:|---:|---:|",
    ]
    lines.extend(
        f"| {gate.gate} | {_format_value(gate.value)} | {gate.threshold} | "
        f"{'PASS' if gate.passed else 'FAIL'} |"
        for gate in gates
    )
    lines.append("")
    return lines


def _format_value(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")
