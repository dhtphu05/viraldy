"""KIE reasons survive persistence/reload without exposing provider payloads or retrying."""

from __future__ import annotations

import copy
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest

from tests.unit.test_smart_remake_generation_progress import fixture as progress_fixture
from tests.unit.test_smart_remake_kie_workflow_unit import workflow as workflow_fixture
from viraldy.modules.smart_remake import generation_progress, kie_workflow
from viraldy.modules.smart_remake.engine.errors import SmartRemakeError
from viraldy.modules.smart_remake.engine.kie_client import KieClient
from viraldy.modules.smart_remake.repair_service import RepairService
from viraldy.shared.errors.base import AppError


@pytest.fixture(name="workflow")
def setup_workflow(monkeypatch):
    return workflow_fixture.__wrapped__(monkeypatch)


def test_provider_error_projection_redacts_secrets_urls_and_prompt_echoes_without_mutating():
    from viraldy.modules.smart_remake.provider_errors import public_provider_error_fields

    original = {
        "providerTaskId": "task-owned",
        "providerError": {
            "httpStatus": 500, "providerCode": "CONTENT_POLICY",
            "providerMessage": 'Image rejected. Bearer private-token '
            'https://cdn.test/private?key=secret "prompt": "PRIVATE_PROMPT"',
            "request": {"prompt": "PRIVATE_PROMPT"},
        },
    }
    before = copy.deepcopy(original)
    public = public_provider_error_fields(original)
    assert public["providerTaskId"] == "task-owned"
    assert public["providerError"]["httpStatus"] == 500
    assert public["providerError"]["providerCode"] == "CONTENT_POLICY"
    assert "Image rejected" in public["providerError"]["providerMessage"]
    assert all(value not in json.dumps(public) for value in (
        "private-token", "https://", "PRIVATE_PROMPT", "cdn.test", '"request"',
    ))
    assert original == before


@pytest.mark.parametrize("value", [None, {}, {"providerError": []}, {
    "providerTaskId": "https://provider.test/private?token=secret",
    "providerError": {"httpStatus": True, "providerCode": {}, "providerMessage": []},
}])
def test_invalid_or_legacy_missing_provider_details_remain_omitted(value):
    from viraldy.modules.smart_remake.provider_errors import public_provider_error_fields

    assert public_provider_error_fields(value) == {}


def test_public_projection_limits_messages_and_rejects_invalid_status_and_code():
    from viraldy.modules.smart_remake.provider_errors import public_provider_error_fields

    result = public_provider_error_fields({"taskId": "task-legacy", "providerError": {
        "httpStatus": 999, "providerCode": "arbitrary private text", "providerMessage": "x" * 900,
    }})
    assert result == {"providerTaskId": "task-legacy",
                      "providerError": {"providerMessage": "x" * 500}}


@pytest.mark.parametrize("message", [
    "Rejected https://cdn.test/file?token='PRIVATE' end",
    'Rejected requestBody={"private": "PRIVATE"}',
])
def test_quoted_url_tokens_and_camel_case_body_echoes_are_not_public(message):
    from viraldy.modules.smart_remake.provider_errors import sanitize_provider_error

    result = sanitize_provider_error({"providerMessage": message})
    assert "Rejected" in result["providerMessage"]
    assert "PRIVATE" not in result["providerMessage"]


@pytest.mark.parametrize("code,secrets", [
    ("sk-test-secret", ()),
    ("0123456789abcdef0123456789abcdef", ()),
    ("provider-private-secret", ("provider-private-secret",)),
])
def test_provider_code_cannot_publish_a_credential(code, secrets):
    from viraldy.modules.smart_remake.provider_errors import sanitize_provider_error

    result = sanitize_provider_error({"providerCode": code, "providerMessage": "Rejected."},
                                     secrets=secrets)
    assert result == {"providerMessage": "Rejected."}


@pytest.mark.parametrize("native", [True, False])
async def test_client_retains_sanitized_async_failure_code_and_reason(native):
    calls = []

    def failed(request):
        calls.append(request)
        assert request.method == "GET"
        message = "Image rejected. test-key https://cdn.test/private?token=secret"
        data = {"taskId": "task-owned", "model": "veo-3-1"}
        data.update(
            {"successFlag": 3, "errorCode": "CONTENT_POLICY", "errorMessage": message}
            if native else {"state": "fail", "failCode": "CONTENT_POLICY", "failMsg": message}
        )
        return httpx.Response(200, json={"code": 200, "data": data})

    async with httpx.AsyncClient(transport=httpx.MockTransport(failed)) as http:
        value = await KieClient(api_key="test-key", http_client=http).get_task("task-owned")
    assert value["status"] == "failed"
    assert value["providerError"]["providerCode"] == "CONTENT_POLICY"
    assert "Image rejected" in value["providerError"]["providerMessage"]
    assert "test-key" not in json.dumps(value) and "https://" not in json.dumps(value)
    assert value["error_message"] == value["providerError"]["providerMessage"]
    assert len(calls) == (1 if native else 2)


async def test_missing_provider_failure_reason_does_not_invent_a_diagnostic(monkeypatch):
    client = KieClient(api_key="test-key")
    monkeypatch.setattr(client, "_task_data", AsyncMock(return_value={
        "taskId": "task-legacy", "state": "fail",
    }))
    value = await client.get_task("task-legacy")
    assert value["status"] == "failed" and value["providerError"] == {}
    assert value["error_message"] == "KIE generation failed."


async def test_async_failure_is_retained_on_own_task_and_operation_without_another_submit(
    workflow, monkeypatch,
):
    runner, repair, client, row, operation = workflow
    error = {"providerCode": "CONTENT_POLICY", "providerMessage": "Image rejected."}
    client.get_task = AsyncMock(return_value={
        "task_id": "paid-once", "status": "failed", "error_message": "Image rejected.",
        "providerError": error,
    })
    settle = AsyncMock()
    monkeypatch.setattr(kie_workflow, "settle_generation_attempt", settle)
    with pytest.raises(AppError) as raised:
        await runner.execute(row.id, operation.id)
    assert raised.value.code == "KIE_TASK_FAILED"
    assert operation.result_json["providerError"] == error
    assert operation.result_json["providerTaskId"] == "paid-once"
    task = operation.result_json["tasks"]["0"]
    assert task["providerError"] == error and task["status"] == "failed"
    assert task["taskId"] == "paid-once"
    assert settle.call_args.kwargs["receipt"]["providerMessage"] == "Image rejected."
    assert settle.call_args.kwargs["receipt"]["providerCode"] == "CONTENT_POLICY"
    assert repair.captured == []
    await runner.execute(row.id, operation.id)
    assert len(client.submits) == 1


@pytest.mark.parametrize("code,uncertain", [
    ("KIE_VALIDATION_FAILED", False), ("KIE_SUBMISSION_UNCERTAIN", True),
])
async def test_submit_error_retained_on_own_task_preserves_uncertainty(workflow, code, uncertain):
    runner, _, client, row, operation = workflow
    error = {"status": 200, "providerCode": 500 if uncertain else 422,
             "providerMessage": "Provider rejected input. Bearer private-key"}
    client.create_task = AsyncMock(side_effect=SmartRemakeError("Rejected", code, error))
    with pytest.raises(AppError):
        await runner.execute(row.id, operation.id)
    task = operation.result_json["tasks"]["0"]
    assert task["providerError"] == operation.result_json["providerError"]
    assert "private-key" not in json.dumps(task["providerError"])
    assert operation.result_json["needsReconciliation"] is uncertain
    if uncertain:
        assert task["status"] == "submitting"
        with pytest.raises(AppError):
            await runner.execute(row.id, operation.id)
    else:
        await runner.execute(row.id, operation.id)
    assert client.create_task.await_count == 1


async def test_poll_error_preserves_known_task_and_reason_without_asserting_task_failed(workflow):
    runner, _, client, row, operation = workflow
    client.get_task = AsyncMock(side_effect=SmartRemakeError("Unavailable", "KIE_RATE_LIMITED", {
        "status": 429, "providerCode": 429, "providerMessage": "Slow down.",
    }))
    for _ in range(2):
        with pytest.raises(RuntimeError, match="retrieval can be retried"):
            await runner.execute(row.id, operation.id)
    assert len(client.submits) == 1
    assert operation.status == "running" and operation.result_json["needsReconciliation"] is True
    assert operation.result_json["errorCode"] == "KIE_OUTPUT_PENDING"
    assert operation.result_json["providerTaskId"] == "paid-once"
    assert operation.result_json["providerError"]["providerMessage"] == "Slow down."
    task = operation.result_json["tasks"]["0"]
    assert task["status"] == "submitted" and task["providerError"]["providerCode"] == 429


def test_group_error_details_and_task_id_do_not_leak_to_other_groups():
    row, operation = progress_fixture()
    first, second = operation.result_json["renderPlan"]["groups"]
    error = {"providerCode": 422, "providerMessage": "Unsupported input."}
    operation.result_json.update(errorCode="KIE_TASK_FAILED", providerError=error)
    operation.result_json["tasks"][f"group:{first['id']}"] = {
        "taskId": "task-first", "status": "failed", "errorCode": "KIE_TASK_FAILED",
        "providerError": error,
    }
    operation.status = "failed"
    before = copy.deepcopy(operation.result_json)
    result = generation_progress.generation_progress(row, operation, workspace_id=row.workspace_id)
    assert result["groups"][0]["providerError"] == error
    assert result["groups"][0]["providerTaskId"] == "task-first"
    assert result["groups"][1]["groupId"] == second["id"]
    assert "providerError" not in result["groups"][1]
    assert "providerTaskId" not in result["groups"][1]
    assert operation.result_json == before


def test_legacy_group_without_details_does_not_borrow_operation_error_for_another_task():
    row, operation = progress_fixture()
    first, second = operation.result_json["renderPlan"]["groups"]
    operation.status = "failed"
    operation.result_json.update(errorCode="KIE_TASK_FAILED", providerError={
        "providerMessage": "Old operation reason with no task binding.",
    })
    operation.result_json["tasks"] = {
        f"group:{group['id']}": {"taskId": f"task-{index}", "status": "submitted"}
        for index, group in enumerate((first, second))
    }
    result = generation_progress.generation_progress(row, operation, workspace_id=row.workspace_id)
    assert all("providerError" not in group for group in result["groups"])
    assert [g["providerTaskId"] for g in result["groups"]] == ["task-0", "task-1"]


@pytest.mark.parametrize("running", [False, True])
async def test_project_reload_publishes_optional_provider_error_and_task_id(monkeypatch, running):
    from viraldy.modules.smart_remake import kie_workflow as workflow_module

    workspace, identity = uuid4(), uuid4()
    error = {"providerCode": 500, "providerMessage": "Server exception."}
    operation = SimpleNamespace(id=uuid4(), project_id=identity,
        status="running" if running else "failed", result_json={
        "kind": "render" if running else "repair", "errorCode": "KIE_TASK_FAILED",
        "needsReconciliation": running, "providerError": error, "providerTaskId": "task-owned",
    })
    row = SimpleNamespace(id=identity, workspace_id=workspace, context_json={},
                          state_json={"provider": "kie"})
    repository = SimpleNamespace(project=AsyncMock(return_value=row),
        running=AsyncMock(return_value=operation if running else None),
        latest_operation=AsyncMock(return_value=operation))
    service = RepairService(repository, object(), workspace)
    monkeypatch.setattr(service, "present", AsyncMock(return_value={}))
    monkeypatch.setattr(workflow_module, "reconcile_kie_project", AsyncMock())
    result = await service.get(identity)
    public = result["pendingOperation" if running else "lastOperation"]
    assert public["providerError"] == error and public["providerTaskId"] == "task-owned"
    assert public["needsReconciliation"] is running
