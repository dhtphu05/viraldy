from __future__ import annotations

import copy
import json

import pytest

from viraldy.modules.smart_remake.engine.errors import SmartRemakeError
from viraldy.modules.smart_remake.engine.prompt_sanitizer import (
    sanitize_generation_scene,
    sanitize_reference_product_text,
    validate_generation_payload,
)
from viraldy.modules.smart_remake.generation_expectations import (
    GenerationExpectations,
    build_generation_expectations,
    expectations_hash,
    expectations_scene,
    require_generation_expectations,
    validate_generation_expectations,
    validate_product_lock,
)
from viraldy.shared.errors.base import AppError


def context():
    return {
        "productLock": {
            "productName": "Seller bottle",
            "productType": "bottle",
            "visualIdentity": {"colors": ["blue"], "shape": "cylindrical", "material": "metal"},
            "mustPreserve": ["printed seller mark"],
            "productReference": {
                "storageKey": "private-secret",
                "imageUrl": "https://private.test",
            },
        },
        "referenceAnalysis": {
            "forbiddenReuse": ["Acme", "red", "wood"],
            "subjectPresence": "hands_only",
            "cameraStyle": {"movement": "push in", "angle": "overhead"},
            "setting": {"backgroundElements": ["red background", "wood table"]},
            "privateDebug": "do not expose",
        },
        "sourceMediaHash": "a" * 64,
        "productMediaHash": "b" * 64,
        "sourceSceneMap": {"scenes": [{"id": "source-1", "startFrame": 120, "endFrame": 216}]},
        "renderPlan": {"units": [{"id": "unit-1", "sourceSceneId": "source-1", "sceneIndex": 0}]},
        "sourceOpeningFrames": {
            "source-1": {
                "sourceMediaHash": "a" * 64,
                "frame": 120,
                "layoutHash": "c" * 64,
                "extractorVersion": "source-opening-frame-v1",
            }
        },
        "sceneMap": {
            "scenes": [
                {
                    "prompt": "Open the Acme bottle over a wood table and red background.",
                    "imagePrompt": "Closed Acme bottle in hands, overhead view.",
                    "videoPrompt": "Open Acme cap then pour to the left.",
                    "shotPlan": {
                        "shots": [
                            {
                                "action": "Open Acme",
                                "stateBefore": "Acme cap closed",
                                "physicalAction": {
                                    "contactPoint": "Acme lid",
                                    "movement": "twist left",
                                },
                            }
                        ]
                    },
                    "sourceSegment": {"boundary": {"kind": "source_start"}},
                }
            ]
        },
        "p0": {
            "requirements": {"intent": "Show opening and pouring", "keep": ["red background"]},
            "assets": {
                "source": {"mediaHash": "a" * 64, "storageKey": "private-source"},
                "product": {"mediaHash": "b" * 64},
            },
        },
    }


def fragment_context():
    value = context()
    value["sourceSceneMap"].update(timingMode="fit_target")
    value["sourceSceneMap"]["scenes"][0].update(targetDurationFrames=384)
    original = value["sceneMap"]["scenes"][0]
    value["sceneMap"]["scenes"] = [copy.deepcopy(original), copy.deepcopy(original)]
    value["renderPlan"]["units"] = [
        {"id": f"unit-{index}", "sourceSceneId": "source-1", "sceneIndex": index,
         "sourceStartFrame": start, "sourceEndFrame": end,
         "fragmentIndex": index, "fragmentCount": 2,
         "targetDurationFrames": 192, "rawDurationFrames": 192}
        for index, (start, end) in enumerate(((120, 168), (168, 216)))
    ]
    value["sourceOpeningFrames"] = {
        unit["id"]: {
            "sourceMediaHash": "a" * 64,
            "frame": unit["sourceStartFrame"],
            "layoutHash": str(index + 1) * 64,
            "extractorVersion": "source-opening-frame-v1",
        }
        for index, unit in enumerate(value["renderPlan"]["units"])
    }
    return value


def test_logical_source_scene_can_have_distinct_provider_fragment_expectations():
    value = fragment_context()
    snapshot = build_generation_expectations(value)
    assert [scene["sourceSceneId"] for scene in snapshot["scenes"]] == ["source-1"] * 2
    assert [scene["sourceRange"] for scene in snapshot["scenes"]] == [
        {"startFrame": 120, "endFrame": 168}, {"startFrame": 168, "endFrame": 216},
    ]
    assert [scene["openingFrame"]["frame"] for scene in snapshot["scenes"]] == [120, 168]
    assert snapshot["scenes"][0]["openingFrame"]["layoutHash"] != (
        snapshot["scenes"][1]["openingFrame"]["layoutHash"]
    )


def test_fitted_source_requires_unit_opening_instead_of_legacy_source_fallback():
    value = fragment_context()
    value["sourceOpeningFrames"] = {"source-1": context()["sourceOpeningFrames"]["source-1"]}
    with pytest.raises(AppError):
        build_generation_expectations(value)


@pytest.mark.parametrize("start,end", [(119, 168), (168, 217), (168, 168)])
def test_fragment_expectations_reject_source_ranges_outside_logical_scene(start, end):
    value = fragment_context()
    value["renderPlan"]["units"][0].update(sourceStartFrame=start, sourceEndFrame=end)
    value["sourceOpeningFrames"]["unit-0"]["frame"] = start
    with pytest.raises(AppError):
        build_generation_expectations(value)


def test_shared_logical_source_expectations_reject_overlapping_fragment_ranges():
    value = fragment_context()
    value["renderPlan"]["units"][1]["sourceStartFrame"] = 150
    value["sourceOpeningFrames"]["unit-1"]["frame"] = 150
    with pytest.raises(AppError):
        build_generation_expectations(value)


def test_entire_creative_scene_sanitized_without_damaging_source_presentation():
    original = context()
    scene = sanitize_generation_scene(
        original["sceneMap"]["scenes"][0], original["referenceAnalysis"], original["productLock"]
    )
    text = json.dumps(scene)
    assert "Acme" not in text
    assert "wood table" in text and "red background" in text and "twist left" in text
    assert original["sceneMap"]["scenes"][0]["shotPlan"]["shots"][0]["action"] == "Open Acme"
    validate_generation_payload(scene, original["referenceAnalysis"], original["productLock"])


def test_color_replacement_is_product_scoped_and_target_identity_is_allowed():
    c = context()
    result = sanitize_reference_product_text(
        text="A red bottle on red background and wood table.",
        analysis=c["referenceAnalysis"],
        product_lock=c["productLock"],
    )
    assert "red bottle" not in result
    assert "red background" in result and "wood table" in result
    lock = {**c["productLock"], "productName": "Acme Seller bottle"}
    assert (
        sanitize_reference_product_text(
            text="Acme Seller bottle", analysis=c["referenceAnalysis"], product_lock=lock
        )
        == "Acme Seller bottle"
    )


def test_final_payload_guard_checks_nested_fields_and_negative_instructions():
    c = context()
    for payload in ({"shotPlan": {"stateAfter": "Acme open"}}, "Do not show Acme"):
        with pytest.raises(SmartRemakeError):
            validate_generation_payload(payload, c["referenceAnalysis"], c["productLock"])


def test_snapshot_is_deterministic_private_free_and_independent():
    c = context()
    before = copy.deepcopy(c)
    snapshot = build_generation_expectations(c)
    assert c == before
    assert snapshot["scenes"][0]["openingFrame"]["frame"] == 120
    assert snapshot["scenes"][0]["sourceRange"] == {"startFrame": 120, "endFrame": 216}
    serialized = json.dumps(snapshot)
    assert (
        "Acme" not in serialized
        and "private" not in serialized
        and "forbiddenReuse" not in serialized
    )
    assert "red background" in serialized and "wood table" in serialized
    assert expectations_hash(snapshot) == expectations_hash(dict(reversed(list(snapshot.items()))))
    assert validate_generation_expectations(snapshot, expectations_hash(snapshot)) == snapshot
    assert GenerationExpectations.model_validate(snapshot).scenes[0].renderUnitId == "unit-1"
    assert expectations_scene(snapshot, "unit-1") == snapshot["scenes"][0]
    snapshot["requirements"]["keep"].append("new")
    assert c == before


@pytest.mark.parametrize(
    "mutation", ["reference", "range", "opening", "duplicate", "unknown_version"]
)
def test_invalid_expectation_bindings_are_rejected(mutation):
    snapshot = build_generation_expectations(context())
    if mutation == "reference":
        snapshot["references"]["source"]["mediaHash"] = "bad"
    elif mutation == "range":
        snapshot["scenes"][0]["sourceRange"]["endFrame"] = 119
    elif mutation == "opening":
        snapshot["scenes"][0]["openingFrame"]["frame"] = 168
    elif mutation == "duplicate":
        snapshot["scenes"].append(copy.deepcopy(snapshot["scenes"][0]))
    else:
        snapshot["version"] = "older-version"
    with pytest.raises(AppError):
        validate_generation_expectations(snapshot)


def test_generation_requires_saved_current_snapshot_and_complete_opening_binding():
    c = context()
    with pytest.raises(AppError, match="Update"):
        require_generation_expectations(c)
    snapshot = build_generation_expectations(c)
    c.update(generationExpectations=snapshot, expectationsHash=expectations_hash(snapshot))
    assert require_generation_expectations(c) == snapshot
    c["p0"]["requirements"]["keep"].append("do not omit cap")
    with pytest.raises(AppError):
        require_generation_expectations(c)
    c = context()
    c["sourceOpeningFrames"]["source-1"]["layoutHash"] = None
    snapshot = build_generation_expectations(c)
    c.update(generationExpectations=snapshot, expectationsHash=expectations_hash(snapshot))
    with pytest.raises(AppError):
        require_generation_expectations(c)


@pytest.mark.parametrize(
    "lock",
    [
        {},
        {"productName": "Main Product", "productType": "product"},
        {"productName": "Seller", "visualIdentity": {"shape": "unknown"}},
    ],
)
def test_empty_or_unknown_product_facts_are_not_treated_as_analysis(lock):
    with pytest.raises(AppError) as error:
        validate_product_lock(lock)
    assert error.value.code == "SMART_REMAKE_PRODUCT_ANALYSIS_INCOMPLETE"


def test_unknown_optional_facts_are_not_invented():
    lock = validate_product_lock(
        {
            "productName": "Bottle",
            "productType": "bottle",
            "visualIdentity": {"shape": "cylindrical", "material": None},
        }
    )
    assert lock["visualIdentity"]["material"] is None


def test_negative_source_identity_requirements_preserve_role_without_forbidding_target():
    c = context()
    c["p0"]["requirements"].update(forbid=["Acme logo"], replace=["Acme bottle"])
    raw = copy.deepcopy(c["p0"]["requirements"])
    saved = build_generation_expectations(c)
    assert saved["requirements"]["forbid"] == ["source product identity logo"]
    assert saved["requirements"]["replace"] == ["source product bottle"]
    assert saved["requirementsHash"] == expectations_hash(raw)
    assert c["p0"]["requirements"] == raw
    c["p0"]["requirements"]["keep"] = ["Acme logo"]
    with pytest.raises(SmartRemakeError):
        build_generation_expectations(c)


def test_assembly_selection_changes_hash_and_rejects_invalid_range():
    saved = build_generation_expectations(context())
    previous = expectations_hash(saved)
    saved["scenes"][0]["selection"] = {
        "versionId": "clip-v2",
        "inFrame": 12,
        "outFrame": 108,
        "timebase": "raw_group",
    }
    assert expectations_hash(validate_generation_expectations(saved)) != previous
    saved["scenes"][0]["selection"]["outFrame"] = 12
    with pytest.raises(AppError):
        validate_generation_expectations(saved)


def test_explicit_stale_snapshot_cannot_start_generation():
    c = context()
    snapshot = build_generation_expectations(c)
    c.update(
        generationExpectations=snapshot,
        expectationsHash=expectations_hash(snapshot),
        expectationsStale=True,
    )
    with pytest.raises(AppError):
        require_generation_expectations(c)


@pytest.mark.parametrize(
    "source, preserved, removed",
    [
        (
            "Acme bottle is red and closed on a wood table against a red background.",
            ["closed", "wood table", "red background"],
            ["Acme", "is red"],
        ),
        (
            "Acme bottle made of glass rests on the wood table.",
            ["rests", "wood table"],
            ["Acme", "of glass"],
        ),
        (
            "The Acme bottle remains closed and red while the background is red.",
            ["closed", "background is red"],
            ["Acme", "and red"],
        ),
        (
            "The Acme bottle's material is glass; its cap stays open over a red background.",
            ["cap stays open", "red background"],
            ["Acme", "is glass"],
        ),
        (
            "Acme bottle is closed and the wood table is red.",
            ["closed", "wood table is red"],
            ["Acme"],
        ),
    ],
)
def test_predicate_product_attributes_are_normalized_without_changing_state_or_context(
    source,
    preserved,
    removed,
):
    c = context()
    result = sanitize_reference_product_text(
        text=source,
        analysis=c["referenceAnalysis"],
        product_lock=c["productLock"],
    )
    assert all(value in result for value in preserved)
    assert all(value not in result for value in removed)
    validate_generation_payload(result, c["referenceAnalysis"], c["productLock"])


@pytest.mark.parametrize(
    "source",
    [
        "the product bottle is red and closed",
        "the product bottle made of glass",
        "the bottle's material is glass",
        {"shotPlan": {"stateBefore": "bottle remains red"}},
    ],
)
def test_final_payload_guard_rejects_product_attribute_leak_even_after_brand_was_removed(source):
    c = context()
    with pytest.raises(SmartRemakeError):
        validate_generation_payload(source, c["referenceAnalysis"], c["productLock"])


def test_target_predicate_attributes_and_prop_colors_remain_valid():
    c = context()
    text = "The bottle is blue and metal, closed over a red background and wood table."
    assert (
        sanitize_reference_product_text(
            text=text,
            analysis=c["referenceAnalysis"],
            product_lock=c["productLock"],
        )
        == text
    )
    validate_generation_payload(text, c["referenceAnalysis"], c["productLock"])
