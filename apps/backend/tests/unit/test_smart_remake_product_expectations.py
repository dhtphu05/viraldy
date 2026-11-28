from __future__ import annotations

import copy

import pytest

from tests.unit.test_smart_remake_generation_expectations import context
from viraldy.modules.smart_remake.assembly_snapshots import assembly_expectations
from viraldy.modules.smart_remake.generation_expectations import (
    GenerationExpectations,
    build_generation_expectations,
    expectations_hash,
    require_generation_expectations,
    validate_generation_expectations,
)
from viraldy.modules.smart_remake.project_policy import constraints_hash
from viraldy.shared.errors.base import AppError


def multi_context():
    value = context()
    value["p0"]["additionalProductReferences"] = [
        {"mediaHash": "d" * 64, "storageKey": "private-other-angle", "mimeType": "image/png"}
    ]
    return value


def assembly_case(value):
    snapshot = build_generation_expectations(value)
    version = {
        "id": "version-1", "generationExpectations": snapshot,
        "expectationsHash": expectations_hash(snapshot),
    }
    state = {"scenes": [{"id": "unit-1", "versions": [version]}]}
    timeline = {"items": [{
        "renderUnitId": "unit-1", "sourceSceneId": "source-1",
        "versionId": "version-1", "inFrame": 0, "outFrame": 96,
    }]}
    return timeline, state


def test_single_photo_snapshots_and_policy_hash_keep_existing_serialization():
    value = context()
    snapshot = build_generation_expectations(value)
    assert "productReferenceHashes" not in snapshot
    serialized = GenerationExpectations.model_validate(snapshot).model_dump()
    assert "productReferenceHashes" not in serialized
    assert expectations_hash(snapshot) == (
        "22e09a2b29864311a3af70f1dfbe7af77f7e8b947ff7ff8661e0fb14546d7177"
    )
    assert constraints_hash(value) == (
        "c2412ec79a1e762af04b5bef17c7c5d51fe4f083720182841875b1f3b2923651"
    )


def test_all_product_views_are_frozen_in_primary_first_order_without_private_keys():
    value = multi_context()
    snapshot = build_generation_expectations(value)
    assert snapshot["productReferenceHashes"] == ["b" * 64, "d" * 64]
    assert snapshot["references"]["product"] == {"mediaHash": "b" * 64}
    assert "private-other-angle" not in str(snapshot)
    assert "productReferenceHashes" not in value
    assert validate_generation_expectations(snapshot, expectations_hash(snapshot)) == snapshot


@pytest.mark.parametrize("hashes", [
    [], ["b" * 64], ["d" * 64, "b" * 64], ["b" * 64, "b" * 64],
    ["b" * 64, "not-a-hash"], ["b" * 64] + [f"{i:064x}" for i in range(14)],
])
def test_invalid_product_view_bindings_are_rejected(hashes):
    snapshot = build_generation_expectations(context())
    snapshot["productReferenceHashes"] = hashes
    with pytest.raises(AppError, match="SMART_REMAKE_EXPECTATIONS_REQUIRED"):
        validate_generation_expectations(snapshot)


def test_changing_only_a_supporting_photo_invalidates_generation_and_policy():
    value = multi_context()
    snapshot = build_generation_expectations(value)
    value.update(generationExpectations=snapshot, expectationsHash=expectations_hash(snapshot))
    original_policy = constraints_hash(value)
    require_generation_expectations(value)
    value["p0"]["additionalProductReferences"][0]["mediaHash"] = "e" * 64
    assert constraints_hash(value) != original_policy
    with pytest.raises(AppError, match="SMART_REMAKE_EXPECTATIONS_REQUIRED"):
        require_generation_expectations(value)


def test_assembly_cannot_reuse_clip_after_a_supporting_photo_changes():
    value = multi_context()
    timeline, state = assembly_case(value)
    assert assembly_expectations(timeline, state, value)["productReferenceHashes"] == [
        "b" * 64, "d" * 64,
    ]
    changed = copy.deepcopy(value)
    changed["p0"]["additionalProductReferences"][0]["mediaHash"] = "e" * 64
    with pytest.raises(AppError, match="SMART_REMAKE_ASSEMBLY_EXPECTATIONS_REQUIRED"):
        assembly_expectations(timeline, state, changed)


def test_assembly_rejects_mixing_versions_with_different_supporting_photos():
    value = multi_context()
    timeline, state = assembly_case(value)
    other = copy.deepcopy(state["scenes"][0]["versions"][0])
    other["id"] = "version-2"
    other["generationExpectations"]["productReferenceHashes"] = ["b" * 64, "e" * 64]
    other["expectationsHash"] = expectations_hash(other["generationExpectations"])
    state["scenes"][0]["versions"].append(other)
    timeline["items"].append({**timeline["items"][0], "versionId": "version-2"})
    with pytest.raises(AppError, match="SMART_REMAKE_ASSEMBLY_EXPECTATIONS_REQUIRED"):
        assembly_expectations(timeline, state, value)
