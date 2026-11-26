# ruff: noqa: F811 -- shared offline fixtures are injected by pytest.
from __future__ import annotations

import base64
import importlib
from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr
from test_smart_remake_image_workflow import image, prepare, setup  # noqa: F401
from test_smart_remake_kie_workflow_unit import workflow  # noqa: F401
from test_smart_remake_lifecycle_paid_ledger import enable, ledger  # noqa: F401

from viraldy.modules.smart_remake import generation_budget, provider_execution
from viraldy.modules.smart_remake.engine import kie_client, openai_images
from viraldy.modules.smart_remake.engine.kie_adapter import KIE_MODEL
from viraldy.modules.smart_remake.engine.schemas import UploadedMedia
from viraldy.shared.errors.base import AppError


def witness(monkeypatch, provider, model, operation):
    monkeypatch.setattr(provider_execution, "_verified_tls", lambda response, host: True)
    method, url = {
        "openai.images.edit": ("POST", openai_images.IMAGE_EDIT_URL),
        "kie.tasks.create": ("POST", "https://api.kie.ai/api/v1/jobs/createTask"),
        "kie.tasks.get": ("GET", "https://api.kie.ai/api/v1/jobs/recordInfo"),
    }[operation]
    return provider_execution.observe_response(
        httpx.Response(200, json={"validated": True}, request=httpx.Request(method, url)),
        provider=provider, model=model, operation=operation, owned_transport=True,
    )


def settings():
    return SimpleNamespace(ai_mode="live", openai_api_key=SecretStr("test-key"))


@pytest.mark.asyncio
async def test_injected_http_clients_return_valid_data_without_live_execution_evidence():
    media = UploadedMedia(bytes=image((30, 30)), mime_type="image/png")

    def respond(request):
        if request.url.host == "api.openai.com":
            return httpx.Response(200, json={
                "data": [{"b64_json": base64.b64encode(image()).decode()}]
            })
        return httpx.Response(200, json={"code": 200, "data": {"taskId": "task-1"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        client = openai_images.OpenAIImageClient(settings(), http_client=http)
        output = await client.edit(prompt="Show product", product=media, layout=media)
        assert output["bytes"] == image()
        assert client.last_execution_evidence is None
        kie = kie_client.KieClient(api_key="test-key", http_client=http)
        await kie.create_task(model=KIE_MODEL, input_data=kie_input())
        assert kie.last_execution_evidence is None


@pytest.mark.asyncio
async def test_owned_openai_response_proof_is_bound_to_image_attempt(setup, ledger, monkeypatch):
    repair, row, _, _, _, _, _ = setup
    enable(repair, row)
    proof = witness(monkeypatch, "openai", "gpt-image-2.6-flare", "openai.images.edit")

    @asynccontextmanager
    async def transport(self):
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(
            200, headers={"x-request-id": "req-owned"},
            json={"data": [{"b64_json": base64.b64encode(image()).decode()}]},
        ))) as http:
            yield http

    def observe(response, **kwargs):
        assert not response.is_closed or response.is_stream_consumed
        assert kwargs["owned_transport"] is True
        return proof

    monkeypatch.setattr(openai_images.OpenAIImageClient, "_client", transport)
    monkeypatch.setattr(openai_images, "observe_response", observe)
    values = (*setup[:3], openai_images.OpenAIImageClient(settings()), *setup[4:])
    asset = await prepare(values)
    receipt = next(value["receipt"] for name, value in ledger.calls if name == "complete")
    evidence = receipt["executionEvidence"]
    assert evidence["attemptId"] == asset["attemptId"]
    assert evidence["requestHash"] == asset["requestHash"]
    assert evidence["requestId"] == "req-owned"
    assert "https://" not in str(evidence)
    assert values[3].last_execution_evidence is None


def test_borrowed_or_dictionary_proof_from_fake_client_cannot_promote(monkeypatch):
    borrowed = witness(monkeypatch, "openai", openai_images.IMAGE_MODEL, "openai.images.edit")
    fake = SimpleNamespace(last_execution_evidence=borrowed)
    for value in (borrowed, {"mode": "live", "executionEvidence": borrowed}):
        fake.last_execution_evidence = value
        assert generation_budget.generation_execution_receipt(
            fake, attempt_id=str(uuid4()), request_hash="a" * 64,
            provider="openai", model=openai_images.IMAGE_MODEL, operation="openai.images.edit",
        ) == {}


@pytest.mark.asyncio
async def test_fake_kie_receipt_cannot_forge_live_execution(workflow, ledger):
    runner, repair, client, row, operation = workflow
    enable(repair, row)

    async def status(task_id):
        return {"status": "completed", "output": {"video_url": "https://1.1.1.1/v.mp4"},
                "receipt": {"executionEvidence": {"mode": "live"}, "credits": 8}}

    client.get_task = status
    await runner._task(row, operation, 0, reconcile_only=False)
    receipt = next(value["receipt"] for name, value in ledger.calls if name == "complete")
    assert receipt["credits"] == 8
    assert "executionEvidence" not in receipt


def kie_input():
    return {
        "model": "veo3_lite", "prompt": "Show product", "duration": 8, "aspect_ratio": "9:16",
        "generation_type": "FIRST_AND_LAST_FRAMES_2_VIDEO", "enable_translation": False,
        "resolution": "720p", "image_urls": ["https://1.1.1.1/reference.png"],
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("created_live", [True, False])
async def test_only_owned_kie_create_can_attest_generation_despite_owned_poll(
    workflow, ledger, monkeypatch, created_live
):
    runner, repair, _, row, operation = workflow
    enable(repair, row)
    observed = []
    proofs = {
        operation: witness(monkeypatch, "kie", KIE_MODEL, operation)
        for operation in ("kie.tasks.create", "kie.tasks.get")
    }

    @asynccontextmanager
    async def transport(self):
        def respond(request):
            data = {"taskId": "task-owned"}
            if request.method == "GET":
                data.update(successFlag=1, response={"resultUrls": ["https://1.1.1.1/v.mp4"]})
            return httpx.Response(200, json={"code": 200, "data": data})

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
            yield http

    def observe(response, **kwargs):
        observed.append(kwargs["operation"])
        assert kwargs["owned_transport"] is True
        return proofs[kwargs["operation"]]

    async def request(*args):
        return {"model": KIE_MODEL, "input": kie_input()}, []

    monkeypatch.setattr(kie_client.KieClient, "_client", transport)
    monkeypatch.setattr(kie_client, "observe_response", observe)
    runner.client = kie_client.KieClient(api_key="test-key")
    monkeypatch.setattr(runner, "_request", request)
    if not created_live:
        # A resumed fake/unknown creation may be polled by the owned physical
        # client. A real status response cannot attest that old request's inputs.
        attempt, _ = await generation_budget.reserve_generation_attempt(
            repair, row, operation, slot="video:0", request_hash="b" * 64,
            stage="video", provider="kie", model=KIE_MODEL, profile={},
        )
        operation.result_json["tasks"] = {"0": {
            "taskId": "task-owned", "attemptId": str(attempt.id),
            "requestHash": "b" * 64, "requestModel": KIE_MODEL, "status": "submitted",
        }}
    await runner._task(row, operation, 0, reconcile_only=False)
    create_receipts = [payload.get("receipt") or {} for name, payload in ledger.calls
                       if name == "submitted"]
    proofs_saved = [receipt["executionEvidence"] for receipt in create_receipts
                    if "executionEvidence" in receipt]
    if created_live:
        assert len(proofs_saved) == 1
        proof = proofs_saved[0]
        assert proof["operation"] == "kie.tasks.create" and proof["taskId"] == "task-owned"
        assert proof["attemptId"] == operation.result_json["tasks"]["0"]["attemptId"]
        assert observed == ["kie.tasks.create", "kie.tasks.get"]
    else:
        assert not proofs_saved and observed == ["kie.tasks.get"]
    completion = next(payload["receipt"] for name, payload in ledger.calls if name == "complete")
    assert "executionEvidence" not in completion  # Existing create receipt is merged by ledger.


def test_original_client_with_replaced_method_cannot_borrow_previous_witness(monkeypatch):
    client = openai_images.OpenAIImageClient(settings())
    client.last_execution_evidence = witness(
        monkeypatch, "openai", openai_images.IMAGE_MODEL, "openai.images.edit"
    )

    async def fake_edit(**kwargs):
        return {"executionEvidence": client.last_execution_evidence}

    monkeypatch.setattr(client, "edit", fake_edit)
    assert generation_budget.generation_execution_receipt(
        client, attempt_id=str(uuid4()), request_hash="a" * 64,
        provider="openai", model=openai_images.IMAGE_MODEL, operation="openai.images.edit",
    ) == {}


@pytest.mark.asyncio
async def test_failed_current_call_cannot_reuse_original_clients_old_proof(monkeypatch):
    client = openai_images.OpenAIImageClient(settings())
    client.last_execution_evidence = witness(
        monkeypatch, "openai", openai_images.IMAGE_MODEL, "openai.images.edit"
    )
    media = UploadedMedia(bytes=image((30, 30)), mime_type="image/png")
    with pytest.raises(AppError, match="OPENAI_IMAGE_VALIDATION_FAILED"):
        await client.edit(prompt="", product=media, layout=media)
    assert client.last_execution_evidence is None


def test_physical_subclass_cannot_present_borrowed_proof(monkeypatch):
    class FakeClient(openai_images.OpenAIImageClient):
        pass

    client = FakeClient(settings())
    client.last_execution_evidence = witness(
        monkeypatch, "openai", openai_images.IMAGE_MODEL, "openai.images.edit"
    )
    assert generation_budget.generation_execution_receipt(
        client, attempt_id=str(uuid4()), request_hash="a" * 64,
        provider="openai", model=openai_images.IMAGE_MODEL, operation="openai.images.edit",
    ) == {}


def test_public_factory_replaced_before_wrapper_import_cannot_become_physical(monkeypatch):
    original = openai_images.OpenAIImageClient

    class FactoryFake:
        edit = original.edit

    client = FactoryFake()
    client.last_execution_evidence = witness(
        monkeypatch, "openai", openai_images.IMAGE_MODEL, "openai.images.edit"
    )
    with monkeypatch.context() as patch:
        patch.setattr(openai_images, "OpenAIImageClient", FactoryFake)
        importlib.reload(generation_budget)
        assert generation_budget.generation_execution_receipt(
            client, attempt_id=str(uuid4()), request_hash="a" * 64,
            provider="openai", model=openai_images.IMAGE_MODEL, operation="openai.images.edit",
        ) == {}
    importlib.reload(generation_budget)


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["openai", "kie"])
@pytest.mark.parametrize("failure", ["http", "json", "semantic", "timeout"])
async def test_failed_owned_http_retains_proof_but_timeout_has_none(
    setup, workflow, ledger, monkeypatch, provider, failure
):
    model = "gpt-image-2.6-flare" if provider == "openai" else KIE_MODEL
    operation_name = "openai.images.edit" if provider == "openai" else "kie.tasks.create"
    proof = witness(monkeypatch, provider, model, operation_name)

    @asynccontextmanager
    async def transport(self):
        def respond(request):
            if failure == "timeout":
                raise httpx.ReadTimeout("No response received", request=request)
            if failure == "http":
                return httpx.Response(503, json={"code": 503, "data": {}})
            if failure == "json":
                return httpx.Response(200, content=b"invalid json")
            payload = {"data": [{"b64_json": "invalid PNG"}]} if provider == "openai" else {
                "code": 200, "data": {"missingTaskId": True}
            }
            return httpx.Response(200, json=payload)

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
            yield http

    def observe(response, **kwargs):
        assert kwargs["owned_transport"] is True
        return proof

    if provider == "openai":
        repair, row, _, _, _, _, _ = setup
        enable(repair, row)
        monkeypatch.setattr(openai_images.OpenAIImageClient, "_client", transport)
        monkeypatch.setattr(openai_images, "observe_response", observe)
        client = openai_images.OpenAIImageClient(settings())
        values = (*setup[:3], client, *setup[4:])
        with pytest.raises(AppError):
            await prepare(values)
    else:
        runner, repair, _, row, operation = workflow
        enable(repair, row)
        monkeypatch.setattr(kie_client.KieClient, "_client", transport)
        monkeypatch.setattr(kie_client, "observe_response", observe)
        client = kie_client.KieClient(api_key="test-key")
        runner.client = client

        async def request(*args):
            return {"model": KIE_MODEL, "input": kie_input()}, []

        monkeypatch.setattr(runner, "_request", request)
        with pytest.raises(AppError):
            await runner._task(row, operation, 0, reconcile_only=False)
    result = next(payload for name, payload in ledger.calls if name == "unknown")
    if failure == "timeout":
        assert "executionEvidence" not in result["receipt"]
    else:
        assert result["receipt"]["executionEvidence"]["operation"] == operation_name
        assert "actual_usd" not in result
    assert client.last_execution_evidence is None
