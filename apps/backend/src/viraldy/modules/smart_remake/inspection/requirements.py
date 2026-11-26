"""One authoritative requirement derivation for checking and report validation."""

from __future__ import annotations

import json
from typing import Any

from .contracts import InspectionConstraints, InspectionSubject, Requirement

TECHNICAL_REQUIREMENT = Requirement(
    id="technical",
    category="technical",
    expected="Decodable media with the exact retained frame clock and output format.",
)


def expectation_scenes(
    subject: InspectionSubject, constraints: InspectionConstraints
) -> list[dict[str, Any]]:
    if constraints.expectations is None:
        return []
    if subject.kind == "image" and subject.imageRole != "conditioning":
        return []
    scenes = [scene.model_dump(mode="json") for scene in constraints.expectations.scenes]
    scope = constraints.sceneIds or ([subject.sceneId] if subject.sceneId else [])
    if not scope and subject.kind == "assembly":
        scope = [item["renderUnitId"] for item in constraints.timeline.get("items", [])]
    if scope:
        selected = [scene for scene in scenes if scene["renderUnitId"] in scope]
        if len(selected) != len(scope):
            raise ValueError("The inspection scene has no retained expectations.")
        return selected
    return scenes


def _scene_rules(
    subject: InspectionSubject, constraints: InspectionConstraints
) -> list[Requirement]:
    rules = []
    for scene in expectation_scenes(subject, constraints):
        scene_id = scene["renderUnitId"]
        shared = {"sceneId": scene_id, "sourceSceneId": scene["sourceSceneId"]}
        output_frame = subject.range.inFrame if subject.range else None
        if subject.kind == "assembly":
            output_frame = next(
                (
                    item["targetStartFrame"]
                    for item in constraints.timeline.get("items", [])
                    if item["renderUnitId"] == scene_id
                ),
                None,
            )
        directions = {
            "shotPlan": scene["shotPlan"],
            "sourceSegment": scene["sourceSegment"],
            "userEdits": scene["userEdits"],
            "precedence": (
                "User creative edits override base presentation/action only; "
                "product identity and saved global requirements remain fixed."
            ),
        }
        encoded = json.dumps(directions, ensure_ascii=False, sort_keys=True)
        opening = scene["openingFrame"]
        rules.append(
            Requirement(
                id=f"scene:{scene_id}:opening",
                category="structure",
                expected="Match the intended opening state, pose, product handling and framing. "
                + encoded,
                sourceFrame=opening["frame"],
                sourceMediaHash=opening["sourceMediaHash"],
                outputFrame=output_frame,
                **shared,
            )
        )
        rules.append(
            Requirement(
                id=f"scene:{scene_id}:presentation",
                category="structure",
                expected="Preserve this scene's intended camera, framing and product presentation. "
                + encoded,
                **shared,
            )
        )
        if subject.kind != "image":
            rules.append(
                Requirement(
                    id=f"scene:{scene_id}:action",
                    category="action",
                    expected=(
                        "Preserve this scene's physical action, contact points, "
                        "state transition and order. " + encoded
                    ),
                    **shared,
                )
            )
    return rules


def requirements_for(
    subject: InspectionSubject, constraints: InspectionConstraints
) -> list[Requirement]:
    value = (
        constraints.expectations.requirements
        if constraints.expectations
        else constraints.requirements
    )
    rules = [
        Requirement(
            id="product",
            category="product",
            expected="Preserve the identity and visible details of the original product.",
        )
    ]
    if value.get("requiresCharacter") is True:
        rules.append(
            Requirement(
                id="character",
                category="character",
                expected="Match the supplied original character reference.",
            )
        )
    if subject.kind != "image":
        rules.extend(
            [
                Requirement(
                    id="action",
                    category="action",
                    expected=str(
                        value.get("intent")
                        or "Preserve the source action and physical cause and effect."
                    ),
                ),
                Requirement(
                    id="structure",
                    category="structure",
                    expected="Preserve scene order, planned duration and source cut structure.",
                ),
                Requirement(
                    id="claims",
                    category="claims",
                    expected="Only authorized claims: "
                    + json.dumps(value.get("claims", []), ensure_ascii=False),
                ),
            ]
        )
        if subject.neighborVersionIds:
            rules.append(
                Requirement(
                    id="continuity",
                    category="continuity",
                    expected="Preserve product, character and action continuity across neighbors.",
                )
            )
    for group in ("keep", "replace", "forbid"):
        for index, text in enumerate(value.get(group, [])):
            rules.append(
                Requirement(
                    id=f"{group}:{index}", category="constraints", expected=f"{group}: {text}"
                )
            )
    if constraints.expectations is not None:
        identity = constraints.expectations.model_dump(mode="json")["productLock"]
        rules[0] = rules[0].model_copy(
            update={
                "expected": rules[0].expected
                + " Product facts and fixed constraints: "
                + json.dumps(identity, ensure_ascii=False, sort_keys=True)
            }
        )
        rules.extend(_scene_rules(subject, constraints))
    return rules


def temporal_review_required(rule: Requirement, *, is_video: bool) -> bool:
    return is_video and (
        rule.category in {"action", "structure", "continuity", "claims"}
        or rule.id.startswith(("keep:", "replace:", "forbid:"))
    )
