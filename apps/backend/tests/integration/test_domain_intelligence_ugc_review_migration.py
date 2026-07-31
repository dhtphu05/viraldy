from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import Inspector, create_engine, inspect
from testcontainers.postgres import PostgresContainer  # type: ignore[import-untyped]

from alembic import command
from alembic.config import Config
from viraldy.platform.config.settings import get_settings

EXPECTED_COLUMNS: dict[str, set[str]] = {
    "domain_policy_packs": {
        "id",
        "pack_name",
        "version",
        "status",
        "content_hash",
        "meta",
        "raw_payload",
        "imported_at",
        "updated_at",
    },
    "domain_policy_sources": {
        "source_id",
        "title",
        "publisher",
        "url",
        "source_type",
        "source_date",
        "evidence_strength",
        "notes",
        "raw_payload",
        "imported_at",
        "updated_at",
    },
    "domain_policy_rules": {
        "code",
        "pack_id",
        "domain",
        "title",
        "rule_type",
        "severity",
        "enabled_for_mvp",
        "applicability",
        "required_conditions",
        "implementation",
        "source_ids",
        "raw_payload",
        "created_at",
        "updated_at",
    },
    "domain_creative_patterns": {
        "code",
        "pack_id",
        "name",
        "finding_classification",
        "performance_evidence_status",
        "enabled_for_mvp",
        "raw_payload",
        "created_at",
        "updated_at",
    },
    "domain_mistake_definitions": {
        "code",
        "pack_id",
        "category",
        "title",
        "severity",
        "editable_or_reshoot",
        "enabled_for_mvp",
        "raw_payload",
        "created_at",
        "updated_at",
    },
    "domain_uncertainties": {
        "code",
        "pack_id",
        "topic",
        "classification",
        "raw_payload",
        "created_at",
        "updated_at",
    },
    "domain_policy_rule_sources": {"rule_code", "source_id"},
    "ugc_review_results": {
        "id",
        "workspace_id",
        "processing_job_id",
        "asset_id",
        "asset_version_id",
        "headline",
        "summary",
        "recommended_next_action",
        "overall_confidence",
        "strengths_to_keep",
        "creator_revision_message",
        "policy_pack_version",
        "request_context",
        "analysis_provenance",
        "result_payload",
        "created_at",
        "updated_at",
    },
    "ugc_review_findings": {
        "id",
        "workspace_id",
        "processing_job_id",
        "rule_code",
        "mistake_code",
        "recommendation_id",
        "recommendation_group",
        "title",
        "reason",
        "owner_role",
        "fix_type",
        "confidence",
        "evidence",
        "recommendation_payload",
        "created_at",
    },
    "ugc_review_recommendation_events": {
        "id",
        "workspace_id",
        "processing_job_id",
        "finding_id",
        "seller_action",
        "reason",
        "created_at",
    },
    "ugc_review_revisions": {
        "id",
        "workspace_id",
        "parent_processing_job_id",
        "child_processing_job_id",
        "parent_asset_version_id",
        "child_asset_version_id",
        "created_at",
    },
    "ugc_review_comparisons": {
        "id",
        "workspace_id",
        "parent_processing_job_id",
        "child_processing_job_id",
        "resolved_findings",
        "still_open_findings",
        "new_findings",
        "strengths_preserved",
        "summary",
        "comparison_payload",
        "created_at",
    },
}

UGC_TABLES = {
    "ugc_review_results",
    "ugc_review_findings",
    "ugc_review_recommendation_events",
    "ugc_review_revisions",
    "ugc_review_comparisons",
}


def _constraint_columns(constraints: Iterable[dict[str, object]]) -> set[tuple[str, ...]]:
    return {
        tuple(constraint["column_names"])  # type: ignore[arg-type]
        for constraint in constraints
    }


def _foreign_key(
    inspector: Inspector,
    table: str,
    columns: tuple[str, ...],
) -> dict[str, object]:
    return next(
        foreign_key
        for foreign_key in inspector.get_foreign_keys(table)
        if tuple(foreign_key["constrained_columns"]) == columns
    )


def _assert_foreign_key(
    inspector: Inspector,
    table: str,
    column: str,
    referred_table: str,
    ondelete: str,
) -> None:
    foreign_key = _foreign_key(inspector, table, (column,))
    assert foreign_key["referred_table"] == referred_table
    assert foreign_key["options"] == {"ondelete": ondelete}


def test_domain_intelligence_ugc_review_migration_schema_and_downgrade(
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    with PostgresContainer("postgres:16.6-alpine") as postgres:
        sync_url = postgres.get_connection_url().replace(
            "postgresql+psycopg2",
            "postgresql+psycopg",
        )
        async_url = sync_url.replace("postgresql+psycopg", "postgresql+asyncpg")
        monkeypatch.setenv("DATABASE_SYNC_URL", sync_url)
        monkeypatch.setenv("DATABASE_URL", async_url)
        get_settings.cache_clear()

        config = Config("alembic.ini")
        command.upgrade(config, "head")

        engine = create_engine(sync_url)
        try:
            inspector = inspect(engine)
            tables = set(inspector.get_table_names())
            assert set(EXPECTED_COLUMNS).issubset(tables)

            for table, expected_columns in EXPECTED_COLUMNS.items():
                actual_columns = {
                    column["name"] for column in inspector.get_columns(table)
                }
                assert expected_columns == actual_columns

            for table in UGC_TABLES:
                workspace = _foreign_key(inspector, table, ("workspace_id",))
                assert workspace["referred_table"] == "workspaces"
                assert workspace["options"] == {"ondelete": "CASCADE"}

            _assert_foreign_key(
                inspector,
                "ugc_review_results",
                "processing_job_id",
                "processing_jobs",
                "CASCADE",
            )
            _assert_foreign_key(
                inspector,
                "ugc_review_results",
                "asset_id",
                "assets",
                "SET NULL",
            )
            _assert_foreign_key(
                inspector,
                "ugc_review_results",
                "asset_version_id",
                "asset_versions",
                "SET NULL",
            )
            _assert_foreign_key(
                inspector,
                "ugc_review_findings",
                "rule_code",
                "domain_policy_rules",
                "SET NULL",
            )
            _assert_foreign_key(
                inspector,
                "ugc_review_findings",
                "mistake_code",
                "domain_mistake_definitions",
                "SET NULL",
            )
            _assert_foreign_key(
                inspector,
                "ugc_review_recommendation_events",
                "finding_id",
                "ugc_review_findings",
                "CASCADE",
            )
            for table in {
                "ugc_review_findings",
                "ugc_review_recommendation_events",
            }:
                _assert_foreign_key(
                    inspector,
                    table,
                    "processing_job_id",
                    "processing_jobs",
                    "CASCADE",
                )
            for table in {"ugc_review_revisions", "ugc_review_comparisons"}:
                for column in {"parent_processing_job_id", "child_processing_job_id"}:
                    _assert_foreign_key(
                        inspector,
                        table,
                        column,
                        "processing_jobs",
                        "CASCADE",
                    )

            assert _constraint_columns(
                inspector.get_unique_constraints("domain_policy_packs")
            ) == {("pack_name", "version")}
            assert _constraint_columns(
                inspector.get_unique_constraints("ugc_review_results")
            ) == {("processing_job_id",)}
            assert _constraint_columns(
                inspector.get_unique_constraints("ugc_review_findings")
            ) == {("processing_job_id", "recommendation_id")}
            assert _constraint_columns(
                inspector.get_unique_constraints("ugc_review_revisions")
            ) == {("child_processing_job_id",)}
            assert _constraint_columns(
                inspector.get_unique_constraints("ugc_review_comparisons")
            ) == {("parent_processing_job_id", "child_processing_job_id")}

            rule_source_pk = inspector.get_pk_constraint("domain_policy_rule_sources")
            assert set(rule_source_pk["constrained_columns"]) == {"rule_code", "source_id"}
            _assert_foreign_key(
                inspector,
                "domain_policy_rule_sources",
                "rule_code",
                "domain_policy_rules",
                "CASCADE",
            )
            _assert_foreign_key(
                inspector,
                "domain_policy_rule_sources",
                "source_id",
                "domain_policy_sources",
                "CASCADE",
            )

            checks = {
                table: {
                    constraint["name"]
                    for constraint in inspector.get_check_constraints(table)
                }
                for table in {
                    "domain_policy_sources",
                    "ugc_review_results",
                    "ugc_review_findings",
                    "ugc_review_recommendation_events",
                    "ugc_review_revisions",
                    "ugc_review_comparisons",
                }
            }
            assert checks["domain_policy_sources"] == {
                "ck_domain_policy_sources_evidence_strength"
            }
            assert checks["ugc_review_results"] == {
                "ck_ugc_review_results_confidence",
                "ck_ugc_review_results_next_action",
            }
            assert checks["ugc_review_findings"] == {
                "ck_ugc_review_findings_confidence",
                "ck_ugc_review_findings_fix_type",
                "ck_ugc_review_findings_owner_role",
                "ck_ugc_review_findings_recommendation_group",
            }
            assert checks["ugc_review_recommendation_events"] == {
                "ck_ugc_review_recommendation_events_seller_action"
            }
            assert checks["ugc_review_revisions"] == {
                "ck_ugc_review_revisions_distinct_jobs"
            }
            assert checks["ugc_review_comparisons"] == {
                "ck_ugc_review_comparisons_distinct_jobs"
            }

            expected_indexes = {
                "ix_domain_policy_rules_domain_enabled",
                "ix_domain_policy_rule_sources_source_id",
                "ix_ugc_review_findings_job_group",
                "ix_ugc_review_revisions_workspace_parent_created",
                "ix_ugc_review_comparisons_workspace_parent_created",
            }
            actual_indexes = {
                index["name"]
                for table in EXPECTED_COLUMNS
                for index in inspector.get_indexes(table)
            }
            assert expected_indexes.issubset(actual_indexes)
        finally:
            engine.dispose()

        command.downgrade(config, "0016_seed_tiktok_profiles")
        engine = create_engine(sync_url)
        try:
            downgraded_tables = set(inspect(engine).get_table_names())
        finally:
            engine.dispose()

    assert not set(EXPECTED_COLUMNS).intersection(downgraded_tables)
    assert "processing_jobs" in downgraded_tables
