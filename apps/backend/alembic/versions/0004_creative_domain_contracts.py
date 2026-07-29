from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_creative_domain_contracts"
down_revision: str | None = "0003_keyless_product_hardening"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _jsonb_default_object() -> sa.TextClause:
    return sa.text("'{}'::jsonb")


def upgrade() -> None:
    op.add_column("products", sa.Column("product_context_json", postgresql.JSONB(), nullable=True))
    op.add_column(
        "products", sa.Column("context_schema_version", sa.String(length=100), nullable=True)
    )
    op.execute(
        sa.text(
            """
            UPDATE products
            SET
                context_schema_version = 'product_context_v1',
                product_context_json = jsonb_build_object(
                    'schema_version', 'product_context_v1',
                    'identity', jsonb_build_object(
                        'name', name,
                        'brand', NULL,
                        'category', COALESCE(NULLIF(metadata_json->>'category', ''), 'unknown'),
                        'subcategory', NULLIF(metadata_json->>'subcategory', ''),
                        'variant', NULLIF(metadata_json->>'variant', ''),
                        'market',
                            COALESCE(
                                NULLIF(market, ''),
                                NULLIF(metadata_json->>'market', ''),
                                'unknown'
                            ),
                        'currency', NULLIF(metadata_json->>'currency', '')
                    ),
                    'personas', '[]'::jsonb,
                    'benefits', '[]'::jsonb,
                    'features', '[]'::jsonb,
                    'commercial', jsonb_build_object(
                        'price', NULL,
                        'compare_at_price', NULL,
                        'discount_text', NULL,
                        'bundle_text', NULL,
                        'shipping_text', NULL,
                        'commission_percent', NULL,
                        'margin_band', 'unknown',
                        'offer_notes', '[]'::jsonb
                    ),
                    'creative', jsonb_build_object(
                        'primary_angles',
                            CASE
                                WHEN description IS NULL OR btrim(description) = ''
                                THEN '[]'::jsonb
                                ELSE jsonb_build_array(description)
                            END,
                        'demonstration_mechanisms', '[]'::jsonb,
                        'visual_differentiators', '[]'::jsonb,
                        'available_proof', '[]'::jsonb,
                        'creator_personas', '[]'::jsonb,
                        'preferred_delivery_styles', '[]'::jsonb,
                        'brand_voice', '[]'::jsonb,
                        'prohibited_visuals', '[]'::jsonb
                    ),
                    'governance', jsonb_build_object(
                        'claims', '[]'::jsonb,
                        'required_disclosures', '[]'::jsonb,
                        'prohibited_content', '[]'::jsonb,
                        'rights_notes', '[]'::jsonb
                    )
                )
            WHERE product_context_json IS NULL
            """
        )
    )
    op.alter_column(
        "products",
        "product_context_json",
        existing_type=postgresql.JSONB(),
        nullable=False,
    )
    op.alter_column(
        "products",
        "context_schema_version",
        existing_type=sa.String(length=100),
        nullable=False,
    )

    op.add_column(
        "evidence_items",
        sa.Column(
            "evidence_schema_version",
            sa.String(length=100),
            nullable=False,
            server_default="evidence_legacy_v1",
        ),
    )
    op.add_column(
        "evidence_items", sa.Column("observation_id", sa.String(length=120), nullable=True)
    )

    op.add_column(
        "creative_dna_versions",
        sa.Column(
            "schema_version",
            sa.String(length=100),
            nullable=False,
            server_default="creative_dna_legacy_v1",
        ),
    )
    op.add_column(
        "tiktok_score_runs",
        sa.Column(
            "schema_version",
            sa.String(length=100),
            nullable=False,
            server_default="tiktok_score_v1",
        ),
    )
    op.add_column(
        "adaptation_runs",
        sa.Column(
            "schema_version",
            sa.String(length=100),
            nullable=False,
            server_default="adaptation_legacy_v1",
        ),
    )
    op.add_column(
        "adaptation_runs",
        sa.Column("product_snapshot_json", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "adaptation_runs",
        sa.Column("product_context_schema_version", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "campaign_pack_versions",
        sa.Column(
            "brief_schema_version",
            sa.String(length=100),
            nullable=False,
            server_default="campaign_pack_brief_legacy_v1",
        ),
    )
    op.add_column(
        "campaign_pack_versions",
        sa.Column("product_snapshot_json", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "campaign_pack_versions",
        sa.Column(
            "compiled_requirements_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=_jsonb_default_object(),
        ),
    )
    op.add_column(
        "campaign_pack_versions",
        sa.Column("requirements_schema_version", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "preflight_runs",
        sa.Column(
            "schema_version",
            sa.String(length=100),
            nullable=False,
            server_default="ugc_preflight_legacy_v1",
        ),
    )
    op.add_column(
        "preflight_runs",
        sa.Column("product_snapshot_json", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "preflight_runs",
        sa.Column("product_context_schema_version", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "preflight_runs",
        sa.Column("requirements_snapshot_json", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "recommendations",
        sa.Column(
            "payload_schema_version",
            sa.String(length=100),
            nullable=False,
            server_default="recommendation_legacy_v1",
        ),
    )


def downgrade() -> None:
    op.drop_column("recommendations", "payload_schema_version")
    op.drop_column("preflight_runs", "requirements_snapshot_json")
    op.drop_column("preflight_runs", "product_context_schema_version")
    op.drop_column("preflight_runs", "product_snapshot_json")
    op.drop_column("preflight_runs", "schema_version")
    op.drop_column("campaign_pack_versions", "requirements_schema_version")
    op.drop_column("campaign_pack_versions", "compiled_requirements_json")
    op.drop_column("campaign_pack_versions", "product_snapshot_json")
    op.drop_column("campaign_pack_versions", "brief_schema_version")
    op.drop_column("adaptation_runs", "product_context_schema_version")
    op.drop_column("adaptation_runs", "product_snapshot_json")
    op.drop_column("adaptation_runs", "schema_version")
    op.drop_column("tiktok_score_runs", "schema_version")
    op.drop_column("creative_dna_versions", "schema_version")
    op.drop_column("evidence_items", "observation_id")
    op.drop_column("evidence_items", "evidence_schema_version")
    op.drop_column("products", "context_schema_version")
    op.drop_column("products", "product_context_json")
