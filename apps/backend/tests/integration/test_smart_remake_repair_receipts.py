"""Exact repair receipts are authorized reads, including uncertain provider work."""

from __future__ import annotations

import copy
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest

from tests.integration import test_smart_remake_preflight_api as preflight
from viraldy.modules.smart_remake.budget_models import SmartRemakeAttemptModel
from viraldy.modules.smart_remake.models import SmartRemakeOperationModel, SmartRemakeProjectModel

api = preflight.api
preflight_database_url = preflight.preflight_database_url
router = preflight.router


def path(api, workspace=None):
    return (
        f"/workspaces/{workspace or api.workspace}/smart-remake"
        f"/projects/{api.project.id}/repair-receipts"
    )


async def operation(api, *, key="repair-key", status="completed", result=None):
    result = (
        result
        if result is not None
        else {
            "kind": "repair",
            "sceneId": "s0",
            "request": {"baseVersionId": "v0"},
        }
    )
    async with api.sessions() as session:
        row = SmartRemakeOperationModel(
            project_id=api.project.id,
            idempotency_key=key,
            request_hash="a" * 64,
            status=status,
            result_json=result,
        )
        session.add(row)
        await session.commit()
        return row


async def test_receipt_missing_key_returns_explicit_null_without_constructing_storage(
    api,
    monkeypatch,
):
    storage = Mock(side_effect=AssertionError("Receipt reads must not construct storage."))
    monkeypatch.setattr(router, "S3StorageAdapter", storage)
    response = await api.client.get(path(api), params={"requestKey": "not-recorded"})
    assert response.status_code == 200
    assert response.json()["data"] == {"receipt": None}
    storage.assert_not_called()


async def test_receipt_obeys_workspace_permission_and_project_ownership(api):
    await operation(api)
    for workspace, expected in [(uuid4(), 403), (api.foreign, 404), (api.viewer, 404)]:
        response = await api.client.get(path(api, workspace), params={"requestKey": "repair-key"})
        assert response.status_code == expected


@pytest.mark.parametrize("key", ["", " " * 2, "x" * 201])
async def test_receipt_requires_bounded_nonblank_request_key(api, key):
    response = await api.client.get(path(api), params={"requestKey": key})
    assert response.status_code == 422


@pytest.mark.parametrize("kind", ["render", "compose", "compile", "inspection"])
async def test_receipt_does_not_expose_other_operation_kinds(api, kind):
    await operation(api, result={"kind": kind, "candidateVersionId": "some-other-version"})
    response = await api.client.get(path(api), params={"requestKey": "repair-key"})
    assert response.json()["data"] == {"receipt": None}


@pytest.mark.parametrize(
    "status,extra,uncertain",
    [
        ("running", {}, False),
        ("running", {"needsReconciliation": True, "errorCode": "TIMEOUT"}, True),
        ("failed", {"errorCode": "SMART_REMAKE_REPAIR_INTENT_CONFLICT"}, False),
        ("completed", {}, False),
    ],
)
async def test_receipt_preserves_durable_status_without_guessing_from_fees(
    api,
    status,
    extra,
    uncertain,
):
    row = await operation(
        api,
        status=status,
        result={
            "kind": "repair",
            "sceneId": "s0",
            "request": {"baseVersionId": "v0"},
            **extra,
        },
    )
    async with api.sessions() as session:
        session.add(
            SmartRemakeAttemptModel(
                id=uuid4(),
                project_id=api.project.id,
                workspace_id=api.workspace,
                idempotency_key="retained-video",
                request_hash="b" * 64,
                stage="video",
                purpose="repair",
                status="completed",
                provider="kie",
                model="veo3_lite",
                estimated_usd=Decimal("0.5"),
                actual_usd=None,
            )
        )
        await session.commit()
    response = await api.client.get(path(api), params={"requestKey": "repair-key"})
    receipt = response.json()["data"]["receipt"]
    assert receipt == {
        "operationId": str(row.id),
        "sceneId": "s0",
        "baseVersionId": "v0",
        "candidateVersionId": None,
        "status": status,
        "errorCode": extra.get("errorCode"),
        "needsReconciliation": uncertain,
    }


async def test_receipt_validates_explicit_candidate_scene_and_parent(api):
    candidate = {"id": "candidate-exact", "parentVersionId": "v0", "source": "regenerated"}
    result = {
        "kind": "repair",
        "sceneId": "s0",
        "request": {"baseVersionId": "v0"},
        "candidateVersionId": candidate["id"],
    }
    await operation(api, result=result)
    async with api.sessions() as session:
        project = await session.get(SmartRemakeProjectModel, api.project.id)
        state = copy.deepcopy(project.state_json)
        state["scenes"][0]["versions"].append(candidate)
        state["scenes"][0]["versions"].append({"id": "newest", "parentVersionId": "v0"})
        project.state_json = state
        await session.commit()
    response = await api.client.get(path(api), params={"requestKey": "repair-key"})
    assert response.json()["data"]["receipt"]["candidateVersionId"] == candidate["id"]

    async with api.sessions() as session:
        project = await session.get(SmartRemakeProjectModel, api.project.id)
        state = copy.deepcopy(project.state_json)
        state["scenes"][0]["versions"][-2]["parentVersionId"] = "other-parent"
        project.state_json = state
        await session.commit()
    response = await api.client.get(path(api), params={"requestKey": "repair-key"})
    assert response.json()["data"]["receipt"]["candidateVersionId"] is None


async def test_receipt_supports_legacy_repair_manifest_without_kind(api):
    row = await operation(
        api,
        result={
            "sceneId": "s0",
            "request": {
                "baseVersionId": "v0",
                "prompt": "a",
                "imagePrompt": "b",
                "videoPrompt": "c",
            },
        },
    )
    response = await api.client.get(path(api), params={"requestKey": "repair-key"})
    assert response.json()["data"]["receipt"]["operationId"] == str(row.id)


async def test_receipt_keeps_unassociated_legacy_failure_without_inventing_scene(api):
    await operation(api, status="failed", result={"kind": "repair", "errorCode": "INVALID"})
    response = await api.client.get(path(api), params={"requestKey": "repair-key"})
    receipt = response.json()["data"]["receipt"]
    assert receipt["sceneId"] is None and receipt["baseVersionId"] is None
    assert receipt["candidateVersionId"] is None and receipt["status"] == "failed"


@pytest.mark.parametrize("association", ["wrong-scene", "wrong-operation", "missing-version"])
async def test_receipt_rejects_mismatched_retained_candidate_association(api, association):
    row = await operation(
        api,
        result={
            "kind": "repair",
            "sceneId": "s0",
            "request": {"baseVersionId": "v0"},
            "candidateVersionId": "candidate",
        },
    )
    async with api.sessions() as session:
        project = await session.get(SmartRemakeProjectModel, api.project.id)
        state = copy.deepcopy(project.state_json)
        if association != "missing-version":
            state["scenes"][1 if association == "wrong-scene" else 0]["versions"].append(
                {
                    "id": "candidate",
                    "parentVersionId": "v0",
                    "providerMetadata": {
                        "sourceOperationId": (
                            str(uuid4()) if association == "wrong-operation" else str(row.id)
                        )
                    },
                }
            )
        project.state_json = state
        await session.commit()
    response = await api.client.get(path(api), params={"requestKey": "repair-key"})
    assert response.json()["data"]["receipt"]["candidateVersionId"] is None


async def test_receipt_returns_only_readable_normalization_reason(api):
    await operation(
        api,
        status="failed",
        result={
            "kind": "repair",
            "sceneId": "s0",
            "request": {"baseVersionId": "v0"},
            "repairNormalization": {
                "phase": "resolved",
                "reason": "Giữ đúng nhận diện sản phẩm.",
                "result": {"prompt": "private provider prompt"},
            },
            "compiledScene": {"sourceKey": "private/storage"},
        },
    )
    response = await api.client.get(path(api), params={"requestKey": "repair-key"})
    receipt = response.json()["data"]["receipt"]
    assert receipt["normalizationReason"] == "Giữ đúng nhận diện sản phẩm."
    assert "private" not in str(receipt)


async def test_legacy_non_repair_manifest_is_not_a_receipt(api):
    await operation(api, result={"sceneId": "s0", "request": {"baseVersionId": "v0"}})
    response = await api.client.get(path(api), params={"requestKey": "repair-key"})
    assert response.json()["data"] == {"receipt": None}
