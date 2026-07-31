from __future__ import annotations

from decimal import Decimal

from viraldy.modules.ai_gateway.repository import AiUsageRecord
from viraldy.modules.ai_gateway.service import summarize_usage_records


def _run(
    usage: dict[str, object],
    estimated_cost: Decimal | None,
) -> AiUsageRecord:
    return AiUsageRecord(usage_json=usage, estimated_cost=estimated_cost)


def test_usage_summary_keeps_cost_unknown_when_estimates_are_incomplete() -> None:
    summary = summarize_usage_records(
        [
            _run(
                {
                    "input_tokens": 100,
                    "output_tokens": 20,
                    "total_tokens": 120,
                    "cached_input_tokens": 10,
                },
                Decimal("0.002"),
            ),
            _run(
                {
                    "input_tokens": 50,
                    "output_tokens": 10,
                    "total_tokens": 60,
                    "cached_input_tokens": 0,
                },
                None,
            ),
            _run({}, None),
        ]
    )

    assert summary.completed_run_count == 3
    assert summary.usage_reported_run_count == 2
    assert summary.total_tokens == 180
    assert summary.cached_input_tokens == 10
    assert summary.estimated_cost is None
    assert summary.cost_estimate_complete is False


def test_usage_summary_aggregates_cost_only_when_complete() -> None:
    summary = summarize_usage_records(
        [
            _run({"input_tokens": 100, "output_tokens": 20, "total_tokens": 120}, Decimal("0.002")),
            _run({"input_tokens": 50, "output_tokens": 10, "total_tokens": 60}, Decimal("0.001")),
        ]
    )

    assert summary.input_tokens == 150
    assert summary.output_tokens == 30
    assert summary.total_tokens == 180
    assert summary.estimated_cost == Decimal("0.003")
    assert summary.cost_estimate_complete is True


def test_usage_summary_preserves_partial_provider_usage() -> None:
    summary = summarize_usage_records(
        [
            _run({"input_tokens": 100}, Decimal("0.001")),
            _run({"output_tokens": 20, "cached_input_tokens": 5}, Decimal("0.002")),
            _run({}, None),
        ]
    )

    assert summary.completed_run_count == 3
    assert summary.usage_reported_run_count == 2
    assert summary.input_tokens == 100
    assert summary.output_tokens == 20
    assert summary.total_tokens is None
    assert summary.cached_input_tokens == 5
    assert summary.estimated_cost == Decimal("0.003")
    assert summary.cost_estimate_complete is True
