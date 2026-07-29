from __future__ import annotations

from copy import deepcopy
from typing import Any

from viraldy.modules.media_analysis.contracts import MediaObservationBundleV1

KNOWN_FIXTURE_CHECKSUMS = {
    "viraldy-demo-reference-v1",
    "viraldy-demo-ugc-fixable-v1",
    "viraldy-demo-quick-v1",
    "viraldy-fixture-beauty-tool-v1",
    "viraldy-fixture-pod-gift-v1",
    "viraldy-fixture-pet-accessory-v1",
    "viraldy-fixture-fashion-accessory-v1",
}


def is_known_fixture(checksum: str | None, metadata: dict[str, object] | None = None) -> bool:
    if checksum in KNOWN_FIXTURE_CHECKSUMS:
        return True
    return str((metadata or {}).get("fixture_id", "")) in KNOWN_FIXTURE_CHECKSUMS


def fixture_media_contract(
    checksum: str | None, metadata: dict[str, object] | None = None
) -> dict[str, Any]:
    fixture_id = (
        checksum if checksum in KNOWN_FIXTURE_CHECKSUMS else str((metadata or {}).get("fixture_id"))
    )
    if fixture_id not in KNOWN_FIXTURE_CHECKSUMS:
        raise ValueError("unsupported_fixture")

    scenario = _fixture_scenario(fixture_id)
    first_product_ms = int(scenario["product_first_ms"])
    cta_ms = int(scenario["cta_ms"])

    observation_bundle = _fixture_observation_bundle(scenario)
    return deepcopy(
        {
            "analysis_mode": "fixture",
            "provider": "fixture",
            "model_version": "fixture_media_v1",
            "metadata": {
                "duration_ms": 28000,
                "container": "mp4",
                "video_codec": "h264",
                "audio_codec": "aac",
                "width": 1080,
                "height": 1920,
                "fps": 30,
                "video_stream_count": 1,
                "audio_stream_count": 1,
            },
            "transcript": {
                "language": "en",
                "segments": [
                    {"start_ms": 0, "end_ms": 2100, "text": str(scenario["spoken"])},
                    {
                        "start_ms": first_product_ms,
                        "end_ms": first_product_ms + 1800,
                        "text": str(scenario["demo_line"]),
                    },
                    {
                        "start_ms": cta_ms,
                        "end_ms": 27000,
                        "text": str(scenario["cta_line"]),
                    },
                ],
                "full_text": " ".join(
                    [
                        str(scenario["spoken"]),
                        str(scenario["demo_line"]),
                        str(scenario["cta_line"]),
                    ]
                ),
            },
            "ocr": {
                "segments": [
                    {
                        "start_ms": 300,
                        "end_ms": 1800,
                        "text": str(scenario["overlay"]),
                        "confidence": 0.91,
                        "frame_storage_key": "fixtures/opening.jpg",
                    },
                    {
                        "start_ms": cta_ms,
                        "end_ms": 27000,
                        "text": str(scenario["cta_overlay"]),
                        "confidence": 0.95,
                        "frame_storage_key": "fixtures/cta.jpg",
                    },
                ]
            },
            "sampled_frames": {
                "frames": [
                    {"timestamp_ms": 500, "storage_key": "fixtures/opening.jpg"},
                    {"timestamp_ms": first_product_ms, "storage_key": "fixtures/product.jpg"},
                    {"timestamp_ms": 11200, "storage_key": "fixtures/demo.jpg"},
                    {"timestamp_ms": cta_ms, "storage_key": "fixtures/cta.jpg"},
                ]
            },
            "scene_boundaries": {
                "scenes": [
                    {"scene_index": 0, "start_ms": 0, "end_ms": first_product_ms},
                    {"scene_index": 1, "start_ms": first_product_ms, "end_ms": 15000},
                    {"scene_index": 2, "start_ms": 15000, "end_ms": 28000},
                ]
            },
            "visual_observations": observation_bundle.model_dump(mode="json"),
        }
    )


def _fixture_scenario(fixture_id: str) -> dict[str, object]:
    if fixture_id == "viraldy-demo-ugc-fixable-v1":
        return {
            **_fixture_scenarios()["home_organization"],
            "product_first_ms": 6100,
            "cta_ms": 24800,
            "visibility": "partial",
            "shot_type": "medium",
            "claim": "best ever",
            "claim_risk": "medium",
        }
    scenario = _fixture_scenarios().get(fixture_id)
    return scenario if scenario else _fixture_scenarios()["home_organization"]


def _fixture_scenarios() -> dict[str, dict[str, object]]:
    return {
        "home_organization": {
            "category": "home_organization",
            "product_first_ms": 2400,
            "cta_ms": 18200,
            "spoken": "My counter was always a mess.",
            "demo_line": "This rack gave me half my counter back.",
            "cta_line": "It is linked in my TikTok Shop.",
            "overlay": "I did not know I needed this",
            "cta_overlay": "TikTok Shop",
            "visual": "messy kitchen counter",
            "pain": "limited counter space",
            "hook_type": "problem_first",
            "demo_type": "before_after",
            "demo_action": "show product creating visible counter space",
            "proof_type": "before_after",
            "proof": "visible before/after counter space result",
            "creator_persona": "home_organizer",
            "delivery": "authentic_review",
            "visibility": "clear",
            "shot_type": "close_up",
            "claim": None,
            "claim_risk": "low",
        },
        "viraldy-demo-reference-v1": {},
        "viraldy-demo-quick-v1": {},
        "viraldy-fixture-beauty-tool-v1": {
            "category": "beauty_tool",
            "product_first_ms": 1800,
            "cta_ms": 19000,
            "spoken": "Here is the smoother finish after one tool pass.",
            "demo_line": "The tool moves through one visible section.",
            "cta_line": "The product tag has the exact tool.",
            "overlay": "Smoother finish check",
            "cta_overlay": "Product tag",
            "visual": "beauty tool close-up beside finished look",
            "pain": "uneven styling finish",
            "hook_type": "result_first",
            "demo_type": "usage",
            "demo_action": "show the beauty tool moving through one visible section",
            "proof_type": "visual_result",
            "proof": "finished section is shown on camera",
            "creator_persona": "beauty_reviewer",
            "delivery": "faceless_demo",
            "visibility": "clear",
            "shot_type": "close_up",
            "claim": "smoother-looking finish",
            "claim_risk": "low",
        },
        "viraldy-fixture-pod-gift-v1": {
            "category": "pod_personalized_gift",
            "product_first_ms": 1600,
            "cta_ms": 20000,
            "spoken": "I checked the custom name reveal before gifting it.",
            "demo_line": "The custom detail is visible on the item.",
            "cta_line": "The product tag links the customizable listing.",
            "overlay": "Custom name reveal",
            "cta_overlay": "Customize in shop",
            "visual": "personalized gift reveal with visible custom detail",
            "pain": "generic gifts feel impersonal",
            "hook_type": "curiosity",
            "demo_type": "unboxing",
            "demo_action": "show the custom print detail and packaging reveal",
            "proof_type": "visual_result",
            "proof": "customized name detail is readable on the item",
            "creator_persona": "gift_shopper",
            "delivery": "storytelling",
            "visibility": "clear",
            "shot_type": "close_up",
            "claim": "personalized detail is visible",
            "claim_risk": "low",
        },
        "viraldy-fixture-pet-accessory-v1": {
            "category": "pet_accessory",
            "product_first_ms": 2100,
            "cta_ms": 20600,
            "spoken": "This made the pet walk setup easier to handle.",
            "demo_line": "The accessory stays visible while it is attached.",
            "cta_line": "Check the product tag for the accessory.",
            "overlay": "Walk setup check",
            "cta_overlay": "Product tag",
            "visual": "pet accessory shown attached and in use",
            "pain": "messy pet-walk setup",
            "hook_type": "problem_first",
            "demo_type": "usage",
            "demo_action": "show the pet accessory attached and used during setup",
            "proof_type": "demonstration",
            "proof": "accessory remains visible while being used",
            "creator_persona": "pet_owner",
            "delivery": "demonstration",
            "visibility": "clear",
            "shot_type": "in_use",
            "claim": "easier setup for the walk",
            "claim_risk": "low",
        },
        "viraldy-fixture-fashion-accessory-v1": {
            "category": "fashion_accessory",
            "product_first_ms": 1700,
            "cta_ms": 21000,
            "spoken": "I tried the accessory with two outfits before deciding.",
            "demo_line": "The accessory is visible in both outfit checks.",
            "cta_line": "The product tag has this accessory.",
            "overlay": "Two outfit check",
            "cta_overlay": "Product tag",
            "visual": "fashion accessory shown in close-up and worn",
            "pain": "hard to style one accessory with different outfits",
            "hook_type": "testimonial",
            "demo_type": "comparison",
            "demo_action": "show the accessory worn with two outfit contexts",
            "proof_type": "comparison",
            "proof": "two outfit looks are shown with the accessory visible",
            "creator_persona": "style_reviewer",
            "delivery": "testimonial",
            "visibility": "clear",
            "shot_type": "in_use",
            "claim": "works with two outfit styles shown",
            "claim_risk": "low",
        },
    }


def _fixture_observation_bundle(scenario: dict[str, object]) -> MediaObservationBundleV1:
    first_product_ms = int(scenario["product_first_ms"])
    cta_ms = int(scenario["cta_ms"])
    payload = {
        "schema_version": "media_observation_v1",
        "duration_ms": 28000,
        "hooks": [
            {
                "observation_id": "hook_opening_001",
                "time_range": {"start_ms": 0, "end_ms": 2100},
                "hook_type": scenario["hook_type"],
                "spoken_text": scenario["spoken"],
                "overlay_text": scenario["overlay"],
                "visual_description": scenario["visual"],
                "buyer_pain": scenario["pain"],
                "clarity": "clear",
                "face_present": True,
                "product_present": False,
                "confidence": 0.91,
                "frame_storage_keys": ["fixtures/opening.jpg"],
            }
        ],
        "product_appearances": [
            {
                "observation_id": "product_appearance_001",
                "time_range": {"start_ms": first_product_ms, "end_ms": first_product_ms + 1800},
                "visibility": scenario["visibility"],
                "shot_type": scenario["shot_type"],
                "usage_visible": True,
                "product_match_confidence": 0.84,
                "confidence": 0.88,
                "frame_storage_keys": ["fixtures/product.jpg"],
            }
        ],
        "product_visibility": {
            "first_appearance_ms": first_product_ms,
            "total_visible_ms": 9600 if first_product_ms > 5000 else 12600,
            "screen_time_ratio": 0.34 if first_product_ms > 5000 else 0.45,
            "clear_close_up_present": first_product_ms <= 5000,
            "usage_present": True,
        },
        "demo": {
            "detected": True,
            "demo_type": scenario["demo_type"],
            "steps": [
                {
                    "observation_id": "demo_step_001",
                    "step_index": 1,
                    "time_range": {"start_ms": first_product_ms + 1800, "end_ms": 15000},
                    "action": scenario["demo_action"],
                    "product_visible": True,
                    "mechanism_visible": True,
                    "result_visible": True,
                    "confidence": 0.86,
                    "frame_storage_keys": ["fixtures/demo.jpg"],
                }
            ],
            "before_state_visible": True,
            "after_state_visible": True,
            "mechanism_clarity": "clear",
            "continuity": "edited_but_clear",
            "confidence": 0.87,
        },
        "proof_moments": [
            {
                "observation_id": "proof_result_001",
                "time_range": {"start_ms": 15000, "end_ms": cta_ms},
                "proof_type": scenario["proof_type"],
                "description": scenario["proof"],
                "verifiability": "observable",
                "confidence": 0.84,
                "frame_storage_keys": ["fixtures/demo.jpg"],
            }
        ],
        "ctas": [
            {
                "observation_id": "cta_shop_001",
                "time_range": {"start_ms": cta_ms, "end_ms": 27000},
                "modality": "mixed",
                "cta_type": "link_in_shop",
                "text": scenario["cta_line"],
                "product_tag_visible": True,
                "confidence": 0.9,
                "frame_storage_keys": ["fixtures/cta.jpg"],
            }
        ],
        "offers": [],
        "creator": {
            "face_present": True,
            "speaking_present": True,
            "delivery_style": scenario["delivery"],
            "creator_persona": scenario["creator_persona"],
            "emotion": "relieved",
            "pacing": "fast",
            "sales_language_intensity": "low",
            "authenticity_cues": ["first-person pain", "visible product use"],
            "confidence": 0.82,
        },
        "editing": {
            "cut_count": 6,
            "average_shot_duration_ms": 3500,
            "first_three_second_cut_count": 2,
            "pattern_interrupts": [],
            "dead_air_ranges": [],
            "caption_density": "medium",
            "visual_pacing": "fast",
            "transition_types": ["jump_cut"],
            "confidence": 0.78,
        },
        "claims": [
            {
                "observation_id": "claim_best_001",
                "time_range": {"start_ms": 14200, "end_ms": 15000},
                "text": scenario["claim"],
                "source": "spoken",
                "category": "superlative",
                "risk": scenario["claim_risk"],
                "qualification_present": False,
                "confidence": 0.81,
                "frame_storage_keys": [],
            }
        ]
        if scenario["claim"]
        else [],
        "platform": {
            "aspect_ratio": "9:16",
            "vertical": True,
            "native_signals": ["first_person", "jump_cuts"],
            "shop_signals": ["tiktok_shop_mention"],
            "caption_style": ["short_overlay"],
            "visual_safe_zone_risk": False,
            "confidence": 0.86,
        },
        "uncertainties": [],
    }
    return MediaObservationBundleV1.model_validate(payload)
