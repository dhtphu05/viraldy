"""Native Veo proof accepts only its fixed authenticated API routes."""
import httpx
import pytest

from viraldy.modules.smart_remake import provider_execution as module


@pytest.mark.parametrize("method,path,operation", [
    ("GET", "/api/v1/veo/record-info", "kie.tasks.get"),
    ("POST", "/api/v1/jobs/createTask", "kie.tasks.create"),
    ("GET", "/api/v1/jobs/recordInfo", "kie.tasks.get"),
])
def test_verified_native_and_retained_unified_routes_bind_canonical_model(
    monkeypatch, method, path, operation,
):
    monkeypatch.setattr(module, "_verified_tls", lambda *args: True)
    response = httpx.Response(200, request=httpx.Request(method, "https://api.kie.ai" + path),
                              json={"code": 200, "data": {"taskId": "retained"}})
    proof = module.observe_response(response, provider="kie", model="veo-3-1",
                                    operation=operation, owned_transport=True)
    assert proof is not None
    assert proof.model == "veo-3-1" and proof.operation == operation


@pytest.mark.parametrize("url,method,owned", [
    ("https://api.kie.ai/api/v1/veo/generate", "POST", True),
    ("https://api.kie.ai/api/v1/playground/forwardByLogin", "POST", True),
    ("https://api.kie.ai/api/v1/veo/generate-untrusted", "POST", True),
    ("https://other.test/api/v1/veo/generate", "POST", True),
    ("https://api.kie.ai/api/v1/veo/generate", "GET", True),
    ("https://api.kie.ai/api/v1/veo/generate", "POST", False),
])
def test_native_route_extension_does_not_authorize_proxy_or_injected_transport(
    monkeypatch, url, method, owned,
):
    monkeypatch.setattr(module, "_verified_tls", lambda *args: True)
    response = httpx.Response(200, request=httpx.Request(method, url), json={"code": 200})
    assert module.observe_response(response, provider="kie", model="veo-3-1",
                                   operation="kie.tasks.create", owned_transport=owned) is None
