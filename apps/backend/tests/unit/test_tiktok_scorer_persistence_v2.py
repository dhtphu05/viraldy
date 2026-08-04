from __future__ import annotations

from sqlalchemy import inspect

from viraldy.modules.tiktok_scorer.models import (
    TikTokFixActionEventModel,
    TikTokFixActionModel,
    TikTokScoreComparisonModel,
    TikTokScoreDimensionModel,
    TikTokScoreFindingModel,
    TikTokScoreProfileModel,
    TikTokScoreRunModel,
)


def test_v2_persistence_uses_normalized_entities() -> None:
    tables = {
        model.__tablename__
        for model in (
            TikTokScoreProfileModel,
            TikTokScoreRunModel,
            TikTokScoreDimensionModel,
            TikTokScoreFindingModel,
            TikTokFixActionModel,
            TikTokFixActionEventModel,
            TikTokScoreComparisonModel,
        )
    }

    assert tables == {
        "tiktok_score_profiles",
        "tiktok_score_runs",
        "tiktok_score_dimensions",
        "tiktok_score_findings",
        "tiktok_fix_actions",
        "tiktok_fix_action_events",
        "tiktok_score_comparisons",
    }


def test_score_run_persists_immutable_context_and_provenance() -> None:
    columns = {column.key for column in inspect(TikTokScoreRunModel).columns}

    assert {
        "asset_id",
        "asset_version_id",
        "product_id",
        "score_mode",
        "intended_use",
        "score_profile",
        "score_profile_version",
        "profile_selection_mode",
        "profile_selection_confidence",
        "product_context_snapshot_json",
        "product_context_snapshot_hash",
        "policy_pack_versions_json",
        "rule_versions_json",
        "prompt_versions_json",
        "model_provider_versions_json",
        "media_checksum_sha256",
        "creative_direction_context_snapshot_json",
        "creative_direction_context_version",
        "parent_score_run_id",
        "processing_job_id",
        "current_stage",
        "completed_at",
        "latency_ms",
        "token_usage_json",
        "cost_estimate",
        "failure_code",
        "result_json",
    }.issubset(columns)


def test_child_entities_are_workspace_scoped() -> None:
    for model in (
        TikTokScoreDimensionModel,
        TikTokScoreFindingModel,
        TikTokFixActionModel,
        TikTokFixActionEventModel,
        TikTokScoreComparisonModel,
    ):
        assert "workspace_id" in {column.key for column in inspect(model).columns}
