from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0016_seed_tiktok_profiles"
down_revision: str | None = "0015_tiktok_scorer_v2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PROFILES: tuple[tuple[str, str, str], ...] = (
    (
        "general_tiktok_v1",
        "General TikTok",
        "Balanced beta profile for general TikTok structure diagnostics.",
    ),
    (
        "product_led_demo_v1",
        "Product-led demo",
        "Prioritizes product grounding, mechanism, product-in-use, and observable proof.",
    ),
    (
        "creator_review_v1",
        "Creator review",
        "Prioritizes firsthand product experience, natural delivery, and grounded proof.",
    ),
    (
        "story_led_pov_v1",
        "Story-led POV",
        "Allows necessary story setup before a later product reveal when the story converges.",
    ),
    (
        "tutorial_howto_v1",
        "Tutorial / how-to",
        "Prioritizes ordered steps, key-step visibility, comprehension, and safe usage.",
    ),
    (
        "unboxing_reaction_v1",
        "Unboxing / reaction",
        "Allows packaging-led setup while requiring the actual product to become clear.",
    ),
    (
        "comment_reply_faq_v1",
        "Comment reply / FAQ",
        "Allows a buyer question to open the video and prioritizes a grounded answer.",
    ),
    (
        "offer_led_shop_v1",
        "Offer-led TikTok Shop",
        "Prioritizes verified value, offer clarity, product grounding, and a clear next step.",
    ),
)


def _weights(code: str) -> dict[str, float]:
    profiles = {
        "general_tiktok_v1": {
            "hook_clarity": 0.15,
            "product_visibility": 0.13,
            "demo_clarity": 0.12,
            "proof_strength": 0.10,
            "creator_authenticity": 0.12,
            "offer_clarity": 0.11,
            "cta_readiness": 0.10,
            "tiktok_native_fit": 0.09,
            "claim_safety": 0.08,
        },
        "product_led_demo_v1": {
            "hook_clarity": 0.12,
            "product_visibility": 0.19,
            "demo_clarity": 0.18,
            "proof_strength": 0.13,
            "creator_authenticity": 0.08,
            "offer_clarity": 0.09,
            "cta_readiness": 0.08,
            "tiktok_native_fit": 0.06,
            "claim_safety": 0.07,
        },
        "creator_review_v1": {
            "hook_clarity": 0.14,
            "product_visibility": 0.12,
            "demo_clarity": 0.10,
            "proof_strength": 0.14,
            "creator_authenticity": 0.20,
            "offer_clarity": 0.08,
            "cta_readiness": 0.07,
            "tiktok_native_fit": 0.08,
            "claim_safety": 0.07,
        },
        "story_led_pov_v1": {
            "hook_clarity": 0.19,
            "product_visibility": 0.09,
            "demo_clarity": 0.08,
            "proof_strength": 0.09,
            "creator_authenticity": 0.19,
            "offer_clarity": 0.10,
            "cta_readiness": 0.08,
            "tiktok_native_fit": 0.11,
            "claim_safety": 0.07,
        },
        "tutorial_howto_v1": {
            "hook_clarity": 0.10,
            "product_visibility": 0.15,
            "demo_clarity": 0.22,
            "proof_strength": 0.11,
            "creator_authenticity": 0.08,
            "offer_clarity": 0.07,
            "cta_readiness": 0.07,
            "tiktok_native_fit": 0.09,
            "claim_safety": 0.11,
        },
        "unboxing_reaction_v1": {
            "hook_clarity": 0.14,
            "product_visibility": 0.16,
            "demo_clarity": 0.11,
            "proof_strength": 0.10,
            "creator_authenticity": 0.16,
            "offer_clarity": 0.08,
            "cta_readiness": 0.07,
            "tiktok_native_fit": 0.11,
            "claim_safety": 0.07,
        },
        "comment_reply_faq_v1": {
            "hook_clarity": 0.18,
            "product_visibility": 0.10,
            "demo_clarity": 0.13,
            "proof_strength": 0.11,
            "creator_authenticity": 0.15,
            "offer_clarity": 0.08,
            "cta_readiness": 0.07,
            "tiktok_native_fit": 0.11,
            "claim_safety": 0.07,
        },
        "offer_led_shop_v1": {
            "hook_clarity": 0.13,
            "product_visibility": 0.15,
            "demo_clarity": 0.11,
            "proof_strength": 0.09,
            "creator_authenticity": 0.08,
            "offer_clarity": 0.18,
            "cta_readiness": 0.13,
            "tiktok_native_fit": 0.06,
            "claim_safety": 0.07,
        },
    }
    return profiles[code]


def _threshold(code: str) -> int:
    return {
        "general_tiktok_v1": 78,
        "product_led_demo_v1": 80,
        "creator_review_v1": 78,
        "story_led_pov_v1": 77,
        "tutorial_howto_v1": 80,
        "unboxing_reaction_v1": 78,
        "comment_reply_faq_v1": 78,
        "offer_led_shop_v1": 81,
    }[code]


def _configuration(code: str) -> dict[str, object]:
    _ = code
    return {
        "stable_core_only": True,
        "auxiliary_signals_affect_score": False,
        "late_product_reveal_is_universal_blocker": False,
    }


def _thresholds(code: str) -> dict[str, object]:
    deadlines: dict[str, int] = {
        "product_led_demo_v1": 3000,
        "tutorial_howto_v1": 4500,
        "offer_led_shop_v1": 3000,
    }
    deadline = deadlines.get(code)
    return {
        "structurally_ready": _threshold(code),
        "requires_early_product_grounding": deadline is not None,
        "product_grounding_deadline_ms": deadline,
        "configuration_status": "beta_uncalibrated",
    }


def upgrade() -> None:
    table = sa.table(
        "tiktok_score_profiles",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("workspace_id", postgresql.UUID(as_uuid=True)),
        sa.column("code", sa.String()),
        sa.column("label", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("profile_version", sa.Integer()),
        sa.column("weights_json", postgresql.JSONB()),
        sa.column("thresholds_json", postgresql.JSONB()),
        sa.column("configuration_json", postgresql.JSONB()),
        sa.column("is_system", sa.Boolean()),
        sa.column("is_active", sa.Boolean()),
    )
    op.bulk_insert(
        table,
        [
            {
                "id": UUID(f"00000000-0000-4000-8000-{index:012d}"),
                "workspace_id": None,
                "code": code,
                "label": label,
                "description": description,
                "profile_version": 1,
                "weights_json": _weights(code),
                "thresholds_json": _thresholds(code),
                "configuration_json": _configuration(code),
                "is_system": True,
                "is_active": True,
            }
            for index, (code, label, description) in enumerate(PROFILES, start=1)
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM tiktok_score_profiles "
            "WHERE workspace_id IS NULL AND is_system = true "
            "AND profile_version = 1 AND code = ANY(:codes)"
        ).bindparams(codes=[profile[0] for profile in PROFILES])
    )
