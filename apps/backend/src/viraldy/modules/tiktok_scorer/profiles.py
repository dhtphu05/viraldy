from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import cast

from viraldy.modules.tiktok_scorer.contracts_v2 import ProfileCodeV1

DIMENSION_CODES = (
    "hook_clarity",
    "product_visibility",
    "demo_clarity",
    "proof_strength",
    "creator_authenticity",
    "offer_clarity",
    "cta_readiness",
    "tiktok_native_fit",
    "claim_safety",
)

PROFILE_CODES = {
    "general_tiktok_v1",
    "product_led_demo_v1",
    "creator_review_v1",
    "story_led_pov_v1",
    "tutorial_howto_v1",
    "unboxing_reaction_v1",
    "comment_reply_faq_v1",
    "offer_led_shop_v1",
}


@dataclass(frozen=True, slots=True)
class TikTokScoreProfileV1:
    code: ProfileCodeV1
    version: int
    label: str
    weights: Mapping[str, float]
    structurally_ready_threshold: int
    requires_early_product_grounding: bool = False
    product_grounding_deadline_ms: int | None = None

    def validate(self) -> None:
        if set(self.weights) != set(DIMENSION_CODES):
            raise ValueError(f"{self.code} must weight all nine canonical dimensions")
        if round(sum(self.weights.values()), 6) != 1:
            raise ValueError(f"{self.code} weights must sum to 1")
        if not 0 <= self.structurally_ready_threshold <= 100:
            raise ValueError("profile readiness threshold must be between 0 and 100")
        if self.requires_early_product_grounding != (
            self.product_grounding_deadline_ms is not None
        ):
            raise ValueError(
                "a product grounding deadline is required exactly when the profile opts in"
            )


def _weights(**overrides: float) -> Mapping[str, float]:
    base = {
        "hook_clarity": 0.15,
        "product_visibility": 0.13,
        "demo_clarity": 0.12,
        "proof_strength": 0.10,
        "creator_authenticity": 0.12,
        "offer_clarity": 0.11,
        "cta_readiness": 0.10,
        "tiktok_native_fit": 0.09,
        "claim_safety": 0.08,
    }
    base.update(overrides)
    return MappingProxyType(base)


_PROFILES: Mapping[str, TikTokScoreProfileV1] = MappingProxyType(
    {
        "general_tiktok_v1": TikTokScoreProfileV1(
            code="general_tiktok_v1",
            version=1,
            label="General TikTok",
            weights=_weights(),
            structurally_ready_threshold=78,
        ),
        "product_led_demo_v1": TikTokScoreProfileV1(
            code="product_led_demo_v1",
            version=1,
            label="Product-led demo",
            weights=_weights(
                hook_clarity=0.12,
                product_visibility=0.19,
                demo_clarity=0.18,
                proof_strength=0.13,
                creator_authenticity=0.08,
                offer_clarity=0.09,
                cta_readiness=0.08,
                tiktok_native_fit=0.06,
                claim_safety=0.07,
            ),
            structurally_ready_threshold=80,
            requires_early_product_grounding=True,
            product_grounding_deadline_ms=3000,
        ),
        "creator_review_v1": TikTokScoreProfileV1(
            code="creator_review_v1",
            version=1,
            label="Creator review",
            weights=_weights(
                hook_clarity=0.14,
                product_visibility=0.12,
                demo_clarity=0.10,
                proof_strength=0.14,
                creator_authenticity=0.20,
                offer_clarity=0.08,
                cta_readiness=0.07,
                tiktok_native_fit=0.08,
                claim_safety=0.07,
            ),
            structurally_ready_threshold=78,
        ),
        "story_led_pov_v1": TikTokScoreProfileV1(
            code="story_led_pov_v1",
            version=1,
            label="Story-led POV",
            weights=_weights(
                hook_clarity=0.19,
                product_visibility=0.09,
                demo_clarity=0.08,
                proof_strength=0.09,
                creator_authenticity=0.19,
                offer_clarity=0.10,
                cta_readiness=0.08,
                tiktok_native_fit=0.11,
                claim_safety=0.07,
            ),
            structurally_ready_threshold=77,
        ),
        "tutorial_howto_v1": TikTokScoreProfileV1(
            code="tutorial_howto_v1",
            version=1,
            label="Tutorial / how-to",
            weights=_weights(
                hook_clarity=0.10,
                product_visibility=0.15,
                demo_clarity=0.22,
                proof_strength=0.11,
                creator_authenticity=0.08,
                offer_clarity=0.07,
                cta_readiness=0.07,
                tiktok_native_fit=0.09,
                claim_safety=0.11,
            ),
            structurally_ready_threshold=80,
            requires_early_product_grounding=True,
            product_grounding_deadline_ms=4500,
        ),
        "unboxing_reaction_v1": TikTokScoreProfileV1(
            code="unboxing_reaction_v1",
            version=1,
            label="Unboxing / reaction",
            weights=_weights(
                hook_clarity=0.14,
                product_visibility=0.16,
                demo_clarity=0.11,
                proof_strength=0.10,
                creator_authenticity=0.16,
                offer_clarity=0.08,
                cta_readiness=0.07,
                tiktok_native_fit=0.11,
                claim_safety=0.07,
            ),
            structurally_ready_threshold=78,
        ),
        "comment_reply_faq_v1": TikTokScoreProfileV1(
            code="comment_reply_faq_v1",
            version=1,
            label="Comment reply / FAQ",
            weights=_weights(
                hook_clarity=0.18,
                product_visibility=0.10,
                demo_clarity=0.13,
                proof_strength=0.11,
                creator_authenticity=0.15,
                offer_clarity=0.08,
                cta_readiness=0.07,
                tiktok_native_fit=0.11,
                claim_safety=0.07,
            ),
            structurally_ready_threshold=78,
        ),
        "offer_led_shop_v1": TikTokScoreProfileV1(
            code="offer_led_shop_v1",
            version=1,
            label="Offer-led TikTok Shop",
            weights=_weights(
                hook_clarity=0.13,
                product_visibility=0.15,
                demo_clarity=0.11,
                proof_strength=0.09,
                creator_authenticity=0.08,
                offer_clarity=0.18,
                cta_readiness=0.13,
                tiktok_native_fit=0.06,
                claim_safety=0.07,
            ),
            structurally_ready_threshold=81,
            requires_early_product_grounding=True,
            product_grounding_deadline_ms=3000,
        ),
    }
)

for _profile in _PROFILES.values():
    _profile.validate()


def get_profile(code: ProfileCodeV1 | str) -> TikTokScoreProfileV1:
    try:
        return _PROFILES[code]
    except KeyError as exc:
        raise ValueError(f"Unknown TikTok score profile: {code}") from exc


def list_profiles() -> tuple[TikTokScoreProfileV1, ...]:
    return tuple(_PROFILES[code] for code in sorted(PROFILE_CODES))


def profile_seed_payloads() -> tuple[dict[str, object], ...]:
    """Return the canonical serializable beta configuration for persistence seeds."""

    return tuple(
        {
            "code": profile.code,
            "label": profile.label,
            "profile_version": profile.version,
            "weights_json": dict(profile.weights),
            "thresholds_json": {
                "structurally_ready": profile.structurally_ready_threshold,
                "requires_early_product_grounding": profile.requires_early_product_grounding,
                "product_grounding_deadline_ms": profile.product_grounding_deadline_ms,
                "configuration_status": "beta_uncalibrated",
            },
            "configuration_json": {
                "stable_core_only": True,
                "auxiliary_signals_affect_score": False,
                "late_product_reveal_is_universal_blocker": False,
            },
        }
        for profile in list_profiles()
    )


def as_profile_code(code: str) -> ProfileCodeV1:
    if code not in PROFILE_CODES:
        raise ValueError(f"Unknown TikTok score profile: {code}")
    return cast(ProfileCodeV1, code)


__all__ = [
    "DIMENSION_CODES",
    "PROFILE_CODES",
    "TikTokScoreProfileV1",
    "as_profile_code",
    "get_profile",
    "list_profiles",
    "profile_seed_payloads",
]
