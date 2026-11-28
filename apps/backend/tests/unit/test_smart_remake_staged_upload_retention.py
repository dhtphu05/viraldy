"""Dedicated upload originals participate in safe, expiry-aware project deletion."""

import copy
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from tests.unit import test_smart_remake_asset_intake as intake_tests
from tests.unit import test_smart_remake_release_actions as lifecycle_tests
from tests.unit.test_smart_remake_release_deletion import Storage
from viraldy.modules.smart_remake.project_deletion import delete_inventory, deletion_inventory
from viraldy.modules.smart_remake.project_lifecycle import DeletionRequest
from viraldy.platform.storage.keys import asset_source_key

assets = intake_tests.assets
harness = lifecycle_tests.harness


def staged_reference(workspace, *, expires=None):
    asset, version = uuid4(), uuid4()
    return {
        "assetId": str(asset),
        "assetVersionId": str(version),
        "role": "reference_video",
        "storageKey": f"{asset_source_key(workspace, asset, version)}/__r2__/{version.hex}",
        "uploadExpiresAt": expires or (datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
    }


def dedicated_assets(assets):
    for role in ("source", "product"):
        asset, version = assets.rows[assets.ids[role]]
        key = f"{asset_source_key(assets.workspace, asset.id, version.id)}/__r2__/{version.id.hex}"
        assets.storage.objects[key] = assets.storage.objects.pop(version.storage_key)
        assets.storage.metadata[key] = assets.storage.metadata.pop(version.storage_key)
        version.storage_key = key
        asset.metadata_json = {
            "smartRemakeUploadRole": "reference_video" if role == "source" else "product_image",
            "smartRemakeUploadExpiresAt": (datetime.now(UTC) + timedelta(minutes=10)).isoformat(),
        }


async def test_intake_binds_only_dedicated_originals_after_canonical_replay(assets):
    dedicated_assets(assets)
    assets.projects.project = AsyncMock(wraps=assets.projects.project)
    row = await intake_tests.ingest(assets)
    references = copy.deepcopy(row.context_json["p0"]["stagedUploads"])
    assert len(references) == 2
    assert assets.projects.project.await_args.kwargs == {"lock": True}
    assert {item["assetVersionId"] for item in references} == {
        str(assets.ids["source"]),
        str(assets.ids["product"]),
    }
    await intake_tests.ingest(assets)
    assert row.context_json["p0"]["stagedUploads"] == references
    assets.payload.metadata.projectName = "Different request"
    from viraldy.shared.errors.base import AppError

    with pytest.raises(AppError):
        await intake_tests.ingest(assets)
    assert row.context_json["p0"]["stagedUploads"] == references


async def test_original_references_exist_at_initial_project_commit(assets):
    dedicated_assets(assets)
    create = assets.projects.create

    async def assert_bound_before_commit(row):
        assert len(row.context_json["p0"]["stagedUploads"]) == 2
        await create(row)

    assets.projects.create = assert_bound_before_commit
    await intake_tests.ingest(assets)


@pytest.mark.parametrize("case", ["ordinary", "forged_key"])
async def test_intake_does_not_bind_unrelated_library_uploads(assets, case):
    if case == "forged_key":
        for role in ("source", "product"):
            assets.rows[assets.ids[role]][0].metadata_json = {
                "smartRemakeUploadRole": "reference_video"
            }
    row = await intake_tests.ingest(assets)
    assert not row.context_json["p0"].get("stagedUploads")


def test_inventory_contains_staged_originals_without_widening_project_ownership():
    workspace, project = uuid4(), uuid4()
    reference = staged_reference(workspace)
    prefix = f"workspaces/{workspace}/smart-remake/{project}/"
    context = {"p0": {"stagedUploads": [reference, reference]}}
    inventory = deletion_inventory({}, context, owned_prefix=prefix)
    assert len(inventory) == 1
    assert inventory[0]["storageKey"] == reference["storageKey"]
    assert inventory[0]["status"] == "pending"


@pytest.mark.parametrize(
    "case", ["key", "workspace", "traversal", "version", "role", "missing_key"]
)
async def test_forged_staged_references_cannot_delete_objects(case):
    workspace, project = uuid4(), uuid4()
    reference = staged_reference(workspace)
    if case == "key":
        reference["storageKey"] += "-lookalike"
    elif case == "workspace":
        reference = staged_reference(uuid4())
    elif case == "traversal":
        reference["storageKey"] += "/../other"
    elif case == "version":
        reference["assetVersionId"] = str(uuid4())
    elif case == "role":
        reference["role"] = "library_asset"
    else:
        reference["storageKey"] = None
    prefix = f"workspaces/{workspace}/smart-remake/{project}/"
    storage = Storage()
    result = await delete_inventory(
        storage,
        [
            {
                "status": "pending",
                "storageKey": reference["storageKey"],
                "stagedUpload": reference,
                "keyHash": "forged",
            }
        ],
        owned_prefix=prefix,
        suspended=True,
        shared_keys=set(),
    )
    assert not storage.deleted
    assert result["objects"][0]["status"] == "retained_unowned"


async def test_active_upload_url_defers_original_deletion_then_retry_finishes(monkeypatch):
    from viraldy.modules.smart_remake import project_deletion

    workspace, project = uuid4(), uuid4()
    expires = datetime.now(UTC) + timedelta(minutes=10)
    reference = staged_reference(workspace, expires=expires.isoformat())
    prefix = f"workspaces/{workspace}/smart-remake/{project}/"
    inventory = deletion_inventory({}, {"p0": {"stagedUploads": [reference]}}, owned_prefix=prefix)
    storage = Storage()
    storage.keys.add(reference["storageKey"])
    result = await delete_inventory(
        storage, inventory, owned_prefix=prefix, suspended=True, shared_keys=set()
    )
    assert result["status"] == "partial"
    assert result["objects"][0]["status"] == "pending_upload_expiry"
    assert not storage.deleted
    monkeypatch.setattr(
        project_deletion, "now_iso", lambda: (expires + timedelta(seconds=1)).isoformat()
    )
    result = await delete_inventory(
        storage, result["objects"], owned_prefix=prefix, suspended=True, shared_keys=set()
    )
    assert result["status"] == "completed"
    assert storage.deleted == [reference["storageKey"]]


async def test_expired_shared_original_is_retained():
    workspace, project = uuid4(), uuid4()
    reference = staged_reference(workspace)
    prefix = f"workspaces/{workspace}/smart-remake/{project}/"
    inventory = deletion_inventory({}, {"p0": {"stagedUploads": [reference]}}, owned_prefix=prefix)
    storage = Storage()
    result = await delete_inventory(
        storage,
        inventory,
        owned_prefix=prefix,
        suspended=True,
        shared_keys={reference["storageKey"]},
    )
    assert result["status"] == "partial"
    assert result["objects"][0]["status"] == "retained_shared"
    assert not storage.deleted


@pytest.mark.parametrize("expiry", [None, "invalid", "2026-01-01T00:00:00"])
async def test_unknown_upload_expiry_cannot_claim_complete_deletion(expiry):
    workspace, project = uuid4(), uuid4()
    reference = staged_reference(workspace)
    reference["uploadExpiresAt"] = expiry
    prefix = f"workspaces/{workspace}/smart-remake/{project}/"
    inventory = deletion_inventory({}, {"p0": {"stagedUploads": [reference]}}, owned_prefix=prefix)
    storage = Storage()
    result = await delete_inventory(
        storage, inventory, owned_prefix=prefix, suspended=True, shared_keys=set()
    )
    assert result["status"] == "partial"
    assert result["objects"][0]["status"] == "retained_upload_expiry_unknown"
    assert not storage.deleted


async def test_lifecycle_retains_original_shared_with_another_project(harness):
    h = harness
    reference = staged_reference(h.row.workspace_id)
    h.row.context_json["p0"]["stagedUploads"] = [reference]
    h.media.data[reference["storageKey"]] = b"staged source"
    session = lifecycle_tests.Session(h.repo)
    session.others = [
        SimpleNamespace(state_json={}, context_json={"p0": {"stagedUploads": [reference]}})
    ]
    h.repo.session = session

    async def save(row, state):
        row.state_json, row.revision = copy.deepcopy(state), state["revision"]

    h.repo.save = save
    result = await h.service.delete(
        h.project,
        h.actor,
        DeletionRequest(expectedRevision=3, idempotencyKey="delete-staged", reason="Remove media"),
    )
    assert result["deletion"]["status"] == "partial"
    assert reference["storageKey"] not in h.media.deleted
    assert any(item["status"] == "retained_shared" for item in result["deletion"]["objects"])


async def test_same_lifecycle_request_retries_staged_cleanup_after_expiry(harness, monkeypatch):
    from viraldy.modules.smart_remake import project_deletion

    h = harness
    expires = datetime.now(UTC) + timedelta(minutes=10)
    reference = staged_reference(h.row.workspace_id, expires=expires.isoformat())
    h.row.context_json["p0"]["stagedUploads"] = [reference]
    h.media.data[reference["storageKey"]] = b"staged source"
    h.repo.session = lifecycle_tests.Session(h.repo)

    async def save(row, state):
        row.state_json, row.revision = copy.deepcopy(state), state["revision"]

    h.repo.save = save
    request = DeletionRequest(
        expectedRevision=3, idempotencyKey="delete-staged", reason="Remove media"
    )
    result = await h.service.delete(h.project, h.actor, request)
    assert result["deletion"]["status"] == "partial"
    assert reference["storageKey"] not in h.media.deleted
    monkeypatch.setattr(
        project_deletion, "now_iso", lambda: (expires + timedelta(seconds=1)).isoformat()
    )
    result = await h.service.delete(h.project, h.actor, request)
    assert result["deletion"]["status"] == "completed"
    assert reference["storageKey"] in h.media.deleted


async def test_same_lifecycle_request_retries_a_failed_staged_object(harness, monkeypatch):
    h = harness
    reference = staged_reference(h.row.workspace_id)
    h.row.context_json["p0"]["stagedUploads"] = [reference]
    h.media.data[reference["storageKey"]] = b"staged source"
    h.repo.session = lifecycle_tests.Session(h.repo)

    async def save(row, state):
        row.state_json, row.revision = copy.deepcopy(state), state["revision"]

    h.repo.save = save
    remove = h.media.delete_object

    def fail_staged(key):
        if key == reference["storageKey"]:
            raise OSError("private storage failure")
        remove(key)

    monkeypatch.setattr(h.media, "delete_object", fail_staged)
    request = DeletionRequest(
        expectedRevision=3, idempotencyKey="delete-failed", reason="Remove media"
    )
    result = await h.service.delete(h.project, h.actor, request)
    assert result["deletion"]["status"] == "failed"
    monkeypatch.setattr(h.media, "delete_object", remove)
    result = await h.service.delete(h.project, h.actor, request)
    assert result["deletion"]["status"] == "completed"
    assert reference["storageKey"] in h.media.deleted
