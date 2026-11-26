from __future__ import annotations

import copy
import ssl
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

from viraldy.modules.smart_remake import provider_execution as execution


def _response(
    url="https://generativelanguage.googleapis.com/v1beta/models/gemini-test:generateContent",
):
    return httpx.Response(200, request=httpx.Request("POST", url), json={"safe": True})


def _proof(
    monkeypatch, *, provider="google", model="gemini-test", operation="google.generate_content"
):
    monkeypatch.setattr(execution, "_verified_tls", lambda response, host: True)
    value = execution.observe_response(
        _response(), provider=provider, model=model, operation=operation, owned_transport=True
    )
    return execution.bind_execution_evidence(
        value,
        attempt_id="attempt",
        request_hash="a" * 64,
        provider=provider,
        model=model,
        request_id="response-1",
    )


def _attempt(proof, **overrides):
    return {
        "id": "attempt",
        "stage": "analysis",
        "status": "completed",
        "provider": "google",
        "model": "gemini-test",
        "requestHash": "a" * 64,
        "actualUsd": None,
        "metadata": {"operationId": "compile"},
        "receipt": {"executionEvidence": proof},
        **overrides,
    }


def test_only_owned_verified_official_response_mints_nominal_proof(monkeypatch):
    response = _response()
    assert (
        execution.observe_response(
            response,
            provider="google",
            model="gemini-test",
            operation="google.generate_content",
            owned_transport=True,
        )
        is None
    )  # ordinary MockTransport/Response has no negotiated TLS stream
    monkeypatch.setattr(execution, "_verified_tls", lambda response, host: True)
    assert (
        execution.observe_response(
            httpx.Response(200),
            provider="google",
            model="gemini-test",
            operation="google.generate_content",
            owned_transport=True,
        )
        is None
    )
    for owned, provider, operation, url in (
        (False, "google", "google.generate_content", str(response.request.url)),
        (True, "google", "unknown", str(response.request.url)),
        (True, "openai", "google.generate_content", str(response.request.url)),
        (
            True,
            "google",
            "google.generate_content",
            "https://external.test/v1beta/models/x:generateContent",
        ),
        (
            True,
            "google",
            "google.generate_content",
            "http://generativelanguage.googleapis.com/v1beta/models/x:generateContent",
        ),
    ):
        assert (
            execution.observe_response(
                _response(url),
                provider=provider,
                model="gemini-test",
                operation=operation,
                owned_transport=owned,
            )
            is None
        )
    proof = _proof(monkeypatch)
    assert proof["mode"] == "live" and proof["transport"] == "verified_tls"
    assert "http" not in str(proof) and "safe" not in str(proof)
    assert (
        execution.bind_execution_evidence(
            {"mode": "live"},
            attempt_id="attempt",
            request_hash="a" * 64,
            provider="google",
            model="gemini-test",
        )
        is None
    )
    value = execution.observe_response(
        response,
        provider="google",
        model="gemini-test",
        operation="google.generate_content",
        owned_transport=True,
    )
    assert (
        execution.bind_execution_evidence(
            value, attempt_id="attempt", request_hash="a" * 64, provider="kie", model="other"
        )
        is None
    )


def test_native_tls_requires_negotiated_verified_context_and_hostname():
    class Stream:
        def __init__(self, obj):
            self.obj = obj

        def get_extra_info(self, name):
            return self.obj

    response = _response()
    response.extensions["network_stream"] = Stream(object())
    assert not execution._verified_tls(response, "generativelanguage.googleapis.com")
    context = ssl.create_default_context()
    obj = context.wrap_bio(
        ssl.MemoryBIO(), ssl.MemoryBIO(), server_hostname="generativelanguage.googleapis.com"
    )
    response.extensions["network_stream"] = Stream(obj)
    assert not execution._verified_tls(response, "wrong.test")
    assert not execution._verified_tls(response, "generativelanguage.googleapis.com")


def test_witness_cannot_attest_another_intent(monkeypatch):
    monkeypatch.setattr(execution, "_verified_tls", lambda response, host: True)
    value = execution.observe_response(
        _response(),
        provider="google",
        model="gemini-test",
        operation="google.generate_content",
        owned_transport=True,
    )
    bound = dict(attempt_id="first", request_hash="a" * 64, provider="google", model="gemini-test")
    original = execution.bind_execution_evidence(value, **bound)
    assert original is not None
    assert (
        execution.bind_execution_evidence(
            value, **{**bound, "attempt_id": "other", "request_hash": "b" * 64}
        )
        is None
    )
    assert execution.bind_execution_evidence(value, **bound) == original


def test_receipt_proof_is_bound_and_validated(monkeypatch):
    proof = _proof(monkeypatch)
    attempt = _attempt(proof)
    assert execution.validated_execution_evidence(attempt) == proof
    for key, value in (
        ("attemptId", "other"),
        ("provider", "openai"),
        ("model", "other"),
        ("requestHash", "b" * 64),
        ("mode", "mock"),
        ("transport", "mock"),
        ("observedAt", "invalid"),
        ("responseHash", "invalid"),
        ("operation", "untrusted"),
        ("requestId", "https://secret.test/?key=private"),
    ):
        mutated = {**proof, key: value}
        assert execution.validated_execution_evidence(_attempt(mutated)) is None
    assert execution.validated_execution_evidence(_attempt({"mode": "live"})) is None
    assert execution.validated_execution_evidence(_attempt({**proof, "extra": "secret"})) is None
    original = copy.deepcopy(attempt)
    execution.validated_execution_evidence(attempt)["mode"] = "mock"
    assert attempt == original


def test_run_requires_every_physical_proof_and_current_compile(monkeypatch):
    proof = _proof(monkeypatch)
    runtime = {"executionMode": "unverified", "serverMode": "live", "compileOperationId": "compile"}
    assert execution.classify_run_execution([_attempt(proof)], runtime=runtime) == {
        "mode": "live",
        "providerExecution": "live",
    }
    for attempts, selected_runtime in (
        ([], runtime),
        ([_attempt(None)], runtime),
        ([_attempt(proof)], {**runtime, "compileOperationId": "other"}),
        ([_attempt(proof)], {"serverMode": "live"}),
        ([_attempt(proof, stage="image")], runtime),
        ([_attempt(proof), _attempt(None, id="other", stage="video")], runtime),
    ):
        assert execution.classify_run_execution(attempts, runtime=selected_runtime) == {
            "mode": None,
            "providerExecution": "unverified",
        }
    assert execution.classify_run_execution(
        [_attempt(proof)], runtime={"executionMode": "fixture"}
    ) == {
        "mode": "fixture",
        "providerExecution": "fixture",
    }


def test_run_ignores_only_proven_local_zero_without_remote_evidence(monkeypatch):
    runtime = {"compileOperationId": "compile"}
    live = _attempt(_proof(monkeypatch))
    local = _attempt(
        None,
        id="local",
        status="failed",
        stage="image",
        actualUsd="0.00000000",
        receipt={},
        usage={},
        error={"phase": "preflight", "httpAttempted": False},
    )
    assert execution.classify_run_execution([live, local], runtime=runtime)["mode"] == "live"
    assert (
        execution.classify_run_execution(
            [live, {**local, "receipt": {"intentHash": local["requestHash"]}}], runtime=runtime
        )["mode"]
        == "live"
    )
    for changes in (
        {"providerTaskId": "task"},
        {"receipt": {"requestId": "remote"}},
        {"receipt": {"intentHash": "wrong"}},
        {"usage": {"images": 1}},
        {"actualUsd": None},
        {"status": "unknown"},
        {"error": {"phase": "preflight", "httpAttempted": True}},
    ):
        assert (
            execution.classify_run_execution([live, {**local, **changes}], runtime=runtime)["mode"]
            is None
        )


async def test_real_gemini_mock_transport_never_becomes_live(monkeypatch):
    from viraldy.modules.smart_remake.engine import gemini_client

    monkeypatch.setenv("GEMINI_API_KEY", "offline-test")
    original = httpx.AsyncClient
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(
            200,
            json={
                "responseId": "response-1",
                "candidates": [
                    {
                        "content": {"parts": [{"text": '{"ok":true}'}]},
                    }
                ],
            },
        )

    monkeypatch.setattr(
        gemini_client.httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs),
    )
    client = gemini_client.HttpGeminiClient(max_attempts=1, repair_json=False)
    assert await client.generate_json(system_instruction="system", prompt="prompt") == {"ok": True}
    assert len(calls) == 1
    assert client.last_execution_evidence is None
    assert client.last_request_id == "response-1"


@pytest.mark.parametrize("failed", [False, True])
@pytest.mark.parametrize("borrowed_nominal", [False, True])
async def test_analysis_injected_client_cannot_serialize_forged_proof(
    monkeypatch, failed, borrowed_nominal
):
    from viraldy.modules.smart_remake import budgeted_analysis

    monkeypatch.setenv("SMART_REMAKE_P0_MAX_ANALYSIS_USD", "1")
    captured = []
    monkeypatch.setattr(execution, "_verified_tls", lambda response, host: True)
    witness = execution.observe_response(
        _response(),
        provider="google",
        model=budgeted_analysis.get_gemini_model(),
        operation="google.generate_content",
        owned_transport=True,
    )

    class Session:
        async def execute(self, *args):
            pass

        async def rollback(self):
            pass

    class Injected:
        last_execution_evidence = witness if borrowed_nominal else {"mode": "live"}
        last_usage = {}
        last_request_id = "fake-response"

        async def generate_json(self, **kwargs):
            if failed:
                raise ValueError("invalid model output")
            return {"safe": True}

    row = SimpleNamespace(context_json={"p0": {}})

    async def project(*args):
        return row

    async def reserve(*args, **kwargs):
        return SimpleNamespace(id=uuid4()), True

    async def marker(*args, **kwargs):
        pass

    async def record(*args, **kwargs):
        captured.append(kwargs)

    monkeypatch.setattr(budgeted_analysis.LedgerGeminiClient, "_project", project)
    monkeypatch.setattr(budgeted_analysis.LedgerGeminiClient, "_preflight", project)
    monkeypatch.setattr(budgeted_analysis, "reserve_attempt", reserve)
    monkeypatch.setattr(budgeted_analysis, "mark_submitted", marker)
    monkeypatch.setattr(budgeted_analysis, "complete_attempt", record)
    monkeypatch.setattr(budgeted_analysis, "unknown_attempt", record)
    client = budgeted_analysis.LedgerGeminiClient(
        Session(), uuid4(), uuid4(), uuid4(), uuid4(), client=Injected()
    )
    if failed:
        with pytest.raises(budgeted_analysis.AppError):
            await client.generate_json(system_instruction="system", prompt="prompt")
    else:
        assert await client.generate_json(system_instruction="system", prompt="prompt") == {
            "safe": True
        }
    assert len(captured) == 1
    assert "executionEvidence" not in captured[0]["receipt"]
