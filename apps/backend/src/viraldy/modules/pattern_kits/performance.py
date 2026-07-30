from __future__ import annotations

from viraldy.modules.pattern_kits.contracts import PatternPerformanceSummaryV1
from viraldy.platform.config.settings import Settings
from viraldy.shared.errors.base import AppError


def validate_supported_performance(
    summary: PatternPerformanceSummaryV1,
    settings: Settings,
) -> None:
    if summary.evidence_status != "supported":
        return

    minimum_sample_size = settings.pattern_performance_supported_min_metric_sample_size
    samples_are_supported = all(
        metric.sample_size >= minimum_sample_size for metric in summary.metrics
    )
    if (
        summary.asset_count < settings.pattern_performance_supported_min_asset_count
        or summary.campaign_count < settings.pattern_performance_supported_min_campaign_count
        or not samples_are_supported
    ):
        raise AppError(
            "PATTERN_KIT_PERFORMANCE_UNSUPPORTED",
            "Supported performance evidence does not meet the configured minimum samples.",
            details={
                "minimum_asset_count": settings.pattern_performance_supported_min_asset_count,
                "minimum_campaign_count": (
                    settings.pattern_performance_supported_min_campaign_count
                ),
                "minimum_metric_sample_size": minimum_sample_size,
            },
        )
