from __future__ import annotations

from datetime import UTC, datetime, timedelta

from viraldy.modules.deletion.contracts import DeletionResourceType
from viraldy.modules.deletion.policy import (
    DELETION_ORDER,
    RESOURCE_TABLES,
    subject_aliases,
)
from viraldy.modules.deletion.retention import retention_cutoffs
from viraldy.modules.deletion.storage_cleanup import extract_storage_keys
from viraldy.platform.config.settings import Settings


def test_every_supported_deletion_resource_has_a_root_table() -> None:
    assert set(RESOURCE_TABLES) == set(DeletionResourceType)
    assert RESOURCE_TABLES[DeletionResourceType.WORKSPACE] == "workspaces"
    assert RESOURCE_TABLES[DeletionResourceType.CREATIVE_DNA] == "creative_dna_versions"


def test_deletion_order_is_child_first_for_known_cycles_and_lineage() -> None:
    positions = {table_name: index for index, table_name in enumerate(DELETION_ORDER)}

    assert positions["generation_artifacts"] < positions["generation_runs"]
    assert positions["viral_kit_pattern_links"] < positions["viral_kit_versions"]
    assert positions["pattern_kit_sources"] < positions["pattern_kit_versions"]
    assert positions["campaign_pack_versions"] < positions["campaign_packs"]
    assert positions["asset_versions"] < positions["assets"]
    assert positions["processing_job_events"] < positions["processing_jobs"]
    assert positions["workspace_members"] < positions["workspaces"]


def test_subject_aliases_cover_legacy_and_canonical_trace_subjects() -> None:
    assert {"asset", "media_analysis"}.issubset(
        subject_aliases(DeletionResourceType.ASSET)
    )
    assert {"creative_dna", "creative_dna_version"}.issubset(
        subject_aliases(DeletionResourceType.CREATIVE_DNA)
    )


def test_retention_cutoffs_use_explicit_asset_and_model_windows() -> None:
    now = datetime(2026, 7, 30, tzinfo=UTC)
    settings = Settings(
        asset_retention_days=14,
        model_output_retention_days=45,
    )

    cutoffs = retention_cutoffs(settings, now)

    assert cutoffs.asset_before == now - timedelta(days=14)
    assert cutoffs.model_output_before == now - timedelta(days=45)


def test_extract_storage_keys_finds_nested_media_keys_and_filters_fixtures() -> None:
    payload = {
        "frames": [
            {"storage_key": "workspaces/ws/frames/one.jpg"},
            {"storage_key": "fixtures/opening.jpg"},
        ],
        "observations": [
            {
                "frame_storage_keys": [
                    "workspaces/ws/frames/one.jpg",
                    "workspaces/ws/frames/two.jpg",
                ]
            }
        ],
        "thumbnail_storage_key": "workspaces/ws/thumbnails/opening.jpg",
        "unrelated_url": "https://example.invalid/not-an-object-key",
    }

    assert extract_storage_keys(payload) == {
        "workspaces/ws/frames/one.jpg",
        "workspaces/ws/frames/two.jpg",
        "workspaces/ws/thumbnails/opening.jpg",
    }
