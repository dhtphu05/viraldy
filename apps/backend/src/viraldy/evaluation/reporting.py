from __future__ import annotations

import json
from pathlib import Path

from viraldy.evaluation.contracts import (
    EvaluationReportV1,
    MetricResultV1,
    PatternKitMetricsResultV1,
    ViralKitMetricsResultV1,
)


def render_json_report(report: EvaluationReportV1) -> str:
    payload = report.model_dump(mode="json")
    return f"{json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True)}\n"


def render_markdown_report(report: EvaluationReportV1) -> str:
    lines = [
        "# Viraldy Evaluation Report",
        "",
        f"- Dataset: `{report.dataset_id}`",
        f"- Mode: `{report.mode}`",
        f"- PatternKit cases: {len(report.pattern_kit_cases)}",
        f"- ViralKit cases: {len(report.viral_kit_cases)}",
        "",
        "## Aggregate Metrics",
        "",
    ]
    if report.aggregate.pattern_kit is None:
        lines.extend(["### PatternKit", "", "No PatternKit cases.", ""])
    else:
        lines.extend(
            ["### PatternKit", "", *_metric_table(_pattern_metrics(report.aggregate.pattern_kit))]
        )
    if report.aggregate.viral_kit is None:
        lines.extend(["### ViralKit", "", "No ViralKit cases.", ""])
    else:
        lines.extend(
            ["### ViralKit", "", *_metric_table(_viral_metrics(report.aggregate.viral_kit))]
        )
    if report.pattern_kit_cases:
        lines.extend(["## PatternKit Cases", ""])
        for pattern_case in report.pattern_kit_cases:
            lines.extend(
                [
                    f"### {pattern_case.case_id}",
                    "",
                    *_metric_table(_pattern_metrics(pattern_case.metrics)),
                ]
            )
    if report.viral_kit_cases:
        lines.extend(["## ViralKit Cases", ""])
        for viral_case in report.viral_kit_cases:
            lines.extend(
                [
                    f"### {viral_case.case_id}",
                    "",
                    *_metric_table(_viral_metrics(viral_case.metrics)),
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def write_reports(report: EvaluationReportV1, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "evaluation-report.json"
    markdown_path = output_dir / "evaluation-report.md"
    json_path.write_text(render_json_report(report), encoding="utf-8")
    markdown_path.write_text(render_markdown_report(report), encoding="utf-8")
    return json_path, markdown_path


def _metric_table(metrics: list[MetricResultV1]) -> list[str]:
    lines = [
        "| Metric | Value | Unit | Numerator | Denominator |",
        "|---|---:|---|---:|---:|",
    ]
    lines.extend(
        f"| {metric.metric} | {_format_value(metric.value)} | {metric.unit} | "
        f"{_format_value(metric.numerator)} | {metric.denominator} |"
        for metric in metrics
    )
    lines.append("")
    return lines


def _pattern_metrics(metrics: PatternKitMetricsResultV1) -> list[MetricResultV1]:
    return [
        metrics.schema_validity,
        metrics.evidence_resolution,
        metrics.source_field_agreement,
        metrics.sequence_agreement,
        metrics.applicability_agreement,
        metrics.keep_change_avoid_agreement,
        metrics.cross_category_leakage,
        metrics.unsupported_generalization,
    ]


def _viral_metrics(metrics: ViralKitMetricsResultV1) -> list[MetricResultV1]:
    return [
        metrics.schema_validity,
        metrics.product_grounding,
        metrics.constraint_preservation,
        metrics.diversity_pass_rate,
        metrics.buyer_creator_separation,
        metrics.claim_disclosure_preservation,
        metrics.pattern_kit_traceability,
        metrics.campaign_pack_compile,
        metrics.preflight_compile,
        metrics.human_usefulness,
    ]


def _format_value(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")
