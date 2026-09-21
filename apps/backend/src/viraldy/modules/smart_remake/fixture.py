from __future__ import annotations

from typing import Any


class FixtureGeminiClient:
    """Deterministic local AI adapter used by Viraldy's fixture mode."""

    async def generate_json(
        self,
        *,
        system_instruction: str,
        prompt: str,
        media: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        del system_instruction, media
        if "product lock" in prompt.lower() or "productname" in prompt.lower():
            return {
                "productName": "Target Product",
                "productType": "consumer product",
                "visualIdentity": {"colors": ["brand colors"], "shape": "as shown"},
                "productUsage": {
                    "realisticUseCases": ["use the product as demonstrated"],
                    "suitableSurfaces": ["the demonstrated surface"],
                    "contactPoints": ["the intended grip or contact point"],
                    "handlingInstructions": ["hold and use naturally"],
                    "usageConstraints": ["keep the product physically accurate"],
                    "forbiddenUsageErrors": ["do not change the product identity"],
                },
                "mustPreserve": ["shape", "label", "materials", "brand markings"],
                "canChange": ["background", "lighting", "camera framing"],
                "forbiddenErrors": ["wrong proportions", "warped label", "invented accessories"],
                "productReference": {"characterName": "Target Product"},
            }

        duration = 16 if "16" in prompt else 8
        beat_count = 4 if duration == 16 else 2
        beat_duration = duration / beat_count
        beats = [
            {
                "startSecond": index * beat_duration,
                "endSecond": (index + 1) * beat_duration,
                "action": action,
                "role": role,
                "priority": "mandatory" if index < 2 else "supporting",
                "physicalAction": {
                    "operator": "hands",
                    "targetSurface": "the demonstrated surface",
                    "contactPoint": "the intended product contact point",
                    "movement": action,
                    "visibleEffect": "clear product result",
                },
            }
            for index, (action, role) in enumerate(
                [
                    ("establish the problem and reveal the product", "hook"),
                    ("demonstrate the product action", "demonstration"),
                    ("show the visible result", "proof"),
                    ("finish on a clean product hero and call to action", "cta"),
                ][:beat_count]
            )
        ]
        return {
            "analysisOnly": True,
            "subjectPresence": "hands_only",
            "format": "vertical product demonstration",
            "sceneCount": 1,
            "cameraStyle": {
                "angle": "front three-quarter",
                "framing": "product-focused",
                "movement": "smooth push-in",
            },
            "setting": {
                "locationType": "clean practical surface",
                "backgroundElements": ["simple uncluttered background"],
            },
            "creativeConcept": {
                "hook": "Show the product solving the demonstrated problem immediately",
                "adType": "product_demo",
                "productMoment": "clear before-and-after result",
            },
            "motionBeats": beats,
            "sourceShots": beats,
            "forbiddenReuse": ["do not copy logos or unrelated people from the reference"],
            "audioPlan": {"mode": "silent", "referenceMusic": {"mode": "none"}},
            "pacingPlan": {
                "pace": "fast",
                "shotCount": beat_count,
                "averageShotDuration": beat_duration,
                "cutStyle": "hard_cut",
            },
            "openingShot": {
                "durationSeconds": 1,
                "framing": "product close-up",
                "firstAction": "reveal the product",
            },
            "openingForbiddenSubstitutions": ["do not replace the product with a generic object"],
        }
