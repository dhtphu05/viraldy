from __future__ import annotations

from viraldy.evaluation.tiktok_scorer_contracts import (
    TikTokScorerEvaluationReportV1,
    TikTokScorerMetricResultV1,
    TikTokScorerMetricsV1,
)


def render_tiktok_scorer_markdown(report: TikTokScorerEvaluationReportV1) -> str:
    lines = [
        "# TikTok Scorer Evaluation Report",
        "",
        f"- Dataset: `{report.dataset_id}`",
        f"- Cases: {len(report.cases)}",
        f"- Qualification: {'PASS' if report.qualification_passed else 'FAIL'}",
        "",
        "## Measurement limitations",
        "",
        *[f"- {item}" for item in report.limitations],
        "",
        "## Aggregate metrics",
        "",
        *_metric_table(_metrics(report.aggregate)),
    ]
    if report.cases:
        lines.extend(["## Cases", ""])
        for case in report.cases:
            lines.extend(
                [
                    f"### {case.case_id}",
                    "",
                    f"Categories: {', '.join(case.categories)}",
                    "",
                    *_metric_table(_metrics(case.metrics)),
                ]
            )
            if case.qualification_issues:
                lines.extend(
                    [
                        "Qualification issues:",
                        "",
                        *[
                            f"- `{issue.code}`: {issue.message}"
                            for issue in case.qualification_issues
                        ],
                        "",
                    ]
                )
    return "\n".join(lines).rstrip() + "\n"


def _metric_table(metrics: list[TikTokScorerMetricResultV1]) -> list[str]:
    lines = [
        "| Metric | Status | Value | Unit | Numerator | Denominator | Target |",
        "|---|---|---:|---|---:|---:|---|",
    ]
    for metric in metrics:
        value = "UNMEASURED" if metric.value is None else _format(metric.value)
        numerator = "—" if metric.numerator is None else _format(metric.numerator)
        target = "—"
        if metric.target_max is not None:
            if metric.target_met is None:
                result = "UNMEASURED"
            else:
                result = "PASS" if metric.target_met else "FAIL"
            target = f"≤ {_format(metric.target_max)} ({result})"
        lines.append(
            f"| {metric.metric} | {metric.status} | {value} | {metric.unit} | "
            f"{numerator} | {metric.denominator} | {target} |"
        )
        if metric.status == "unmeasured" and metric.reason:
            lines.append(f"| ↳ reason |  | {metric.reason} |  |  |  |  |")
    lines.append("")
    return lines


def _metrics(metrics: TikTokScorerMetricsV1) -> list[TikTokScorerMetricResultV1]:
    return [getattr(metrics, name) for name in TikTokScorerMetricsV1.model_fields]


def _format(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")


__all__ = ["render_tiktok_scorer_markdown"]
