from __future__ import annotations

import copy

import pytest

from viraldy.modules.smart_remake.project_deletion import (
    delete_inventory,
    deletion_inventory,
    suspend_project,
)
from viraldy.shared.errors.base import AppError


class Storage:
    def __init__(self):
        self.keys = {"owned/product", "owned/raw", "owned/final", "owned/image", "owned/old"}
        self.deleted = []
        self.fail = False
        self.keep = False

    def delete_object(self, key):
        if self.fail:
            raise RuntimeError("secret signed token")
        self.deleted.append(key)
        if not self.keep:
            self.keys.discard(key)

    def object_exists(self, key):
        return key in self.keys


@pytest.fixture
def inventory():
    state = {
        "finalStorageKey": "owned/final",
        "scenes": [
            {"versions": [{"storageKey": "owned/raw"}, {"storageKey": "owned/raw"}]},
        ],
    }
    context = {
        "productKey": "owned/product",
        "sourceKey": "elsewhere/shared",
        "sourceThumbnailKeys": {"scene": "https://private.invalid?secret=token"},
        "imageAssets": {"img": {"storageKey": "owned/image"}},
        "p0": {
            "assets": {"product": {"storageKey": "owned/product"}},
            "assemblies": {"records": [{"storageKey": "owned/old"}]},
            "release": {"exports": [{"storageKey": "owned/final"}]},
        },
        "untrusted": {"storageKey": "owned/should-not-delete"},
    }
    return deletion_inventory(state, context, owned_prefix="owned/")


def test_inventory_only_collects_server_owned_known_keys_and_deduplicates(inventory):
    owned = {entry["storageKey"] for entry in inventory if "storageKey" in entry}
    assert owned == {"owned/product", "owned/raw", "owned/final", "owned/image", "owned/old"}
    assert len(inventory) == 7
    assert "token" not in str(inventory)
    assert "elsewhere" not in str(inventory)
    assert all(entry["keyHash"] for entry in inventory)


def test_suspension_is_immutable_and_records_actor():
    p0 = {"rights": {"source": {"declared": True}}}
    before = copy.deepcopy(p0)
    result = suspend_project(p0, actor_id="actor", reason="seller requested removal")
    assert p0 == before
    assert result["status"] == "suspended"
    assert result["deletion"]["actorId"] == "actor"
    assert result["deletion"]["providerDeletion"] == "unverified"


@pytest.mark.asyncio
async def test_deletion_preserves_shared_objects_and_reports_verified_deletion(inventory):
    storage = Storage()
    result = await delete_inventory(
        storage, inventory, owned_prefix="owned/", suspended=True, shared_keys={"owned/raw"}
    )
    assert result["status"] == "partial"
    assert storage.deleted == [
        entry["storageKey"]
        for entry in inventory
        if entry.get("status") == "pending" and entry.get("storageKey") != "owned/raw"
    ]
    assert "owned/raw" in storage.keys
    assert len({entry["keyHash"] for entry in result["objects"]}) == len(inventory)
    assert all(
        entry["status"] in {"deleted", "retained_shared", "retained_unowned"}
        for entry in result["objects"]
    )
    assert result["providerDeletion"] == "unverified"


@pytest.mark.asyncio
async def test_unsuspended_or_running_or_retention_prevents_removal(inventory):
    storage = Storage()
    with pytest.raises(AppError):
        await delete_inventory(
            storage, inventory, owned_prefix="owned/", suspended=False, shared_keys=set()
        )
    for flag in ({"running_jobs": True}, {"retention_required": True}):
        result = await delete_inventory(
            storage, inventory, owned_prefix="owned/", suspended=True, shared_keys=set(), **flag
        )
        assert result["status"] == "blocked"
        assert not storage.deleted


@pytest.mark.asyncio
async def test_storage_failure_is_sanitized_and_remaining_objects_fail_verification(inventory):
    storage = Storage()
    storage.fail = True
    result = await delete_inventory(
        storage, inventory, owned_prefix="owned/", suspended=True, shared_keys=set()
    )
    assert result["status"] == "failed"
    assert "token" not in str(result)
    assert any(entry.get("errorCode") == "RuntimeError" for entry in result["objects"])
    storage.fail, storage.keep = False, True
    result = await delete_inventory(
        storage, inventory, owned_prefix="owned/", suspended=True, shared_keys=set()
    )
    assert result["status"] == "failed"
    assert any(entry.get("errorCode") == "OBJECT_STILL_EXISTS" for entry in result["objects"])


@pytest.mark.asyncio
async def test_empty_inventory_and_all_owned_deletion_complete():
    storage = Storage()
    empty = await delete_inventory(
        storage, [], owned_prefix="owned/", suspended=True, shared_keys=set()
    )
    assert empty["status"] == "completed"
    inventory = deletion_inventory({"finalStorageKey": "owned/final"}, {}, owned_prefix="owned/")
    result = await delete_inventory(
        storage, inventory, owned_prefix="owned/", suspended=True, shared_keys=set()
    )
    assert result["status"] == "completed"


def test_traversal_and_prefix_lookalike_are_never_owned():
    inventory = deletion_inventory(
        {"finalStorageKey": "owned/../elsewhere/key"},
        {"productKey": "owned-lookalike/key"},
        owned_prefix="owned/",
    )
    assert all(entry["status"] == "retained_unowned" for entry in inventory)


@pytest.mark.asyncio
async def test_manipulated_inventory_cannot_delete_another_project():
    storage = Storage()
    result = await delete_inventory(
        storage,
        [{"storageKey": "other/private", "status": "pending", "keyHash": "forged"}],
        owned_prefix="owned/",
        suspended=True,
        shared_keys=set(),
    )
    assert not storage.deleted
    assert result["objects"][0]["status"] == "retained_unowned"
    assert "storageKey" not in result["objects"][0]


def test_deletion_inventory_includes_raw_versions_frozen_before_recompile():
    context = {
        "p0": {
            "assemblies": {
                "records": [
                    {
                        "storageKey": "owned/final-old",
                        "manifest": {"selections": [{"storageKey": "owned/selected-old"}]},
                        "stateSnapshot": {
                            "scenes": [
                                {
                                    "versions": [
                                        {"storageKey": "owned/selected-old"},
                                        {"storageKey": "owned/candidate-old"},
                                    ]
                                }
                            ]
                        },
                    }
                ]
            }
        }
    }
    inventory = deletion_inventory({}, context, owned_prefix="owned/")
    assert {item["storageKey"] for item in inventory} == {
        "owned/final-old",
        "owned/selected-old",
        "owned/candidate-old",
    }


def test_retained_recompile_media_are_inventory_and_checked_against_owned_prefix():
    context = {"p0": {"retainedMediaKeys": ["owned/thumbnail", "other/private", "owned/thumbnail"]}}
    result = deletion_inventory({}, context, owned_prefix="owned/")
    assert len(result) == 2
    assert result[0]["storageKey"] == "owned/thumbnail"
    assert result[1]["status"] == "retained_unowned"


def test_retired_plan_inventory_includes_unassembled_candidates_and_thumbnails():
    context = {
        "p0": {
            "planHistory": [
                {
                    "stateSnapshot": {
                        "scenes": [{"versions": [{"storageKey": "owned/unassembled-candidate"}]}],
                        "finalStorageKey": "owned/old-preview",
                    },
                    "contextSnapshot": {
                        "sourceThumbnailKeys": {"old": "owned/old-thumbnail"},
                        "imageAssets": {"old-image": {"storageKey": "owned/conditioning"}},
                        "untrusted": {"storageKey": "owned/not-media"},
                        "sourceKey": "other/should-retain",
                    },
                }
            ]
        }
    }
    inventory = deletion_inventory({}, context, owned_prefix="owned/")
    assert {item["storageKey"] for item in inventory if item.get("storageKey")} == {
        "owned/unassembled-candidate",
        "owned/old-preview",
        "owned/old-thumbnail",
        "owned/conditioning",
    }
    assert any(item["status"] == "retained_unowned" for item in inventory)
