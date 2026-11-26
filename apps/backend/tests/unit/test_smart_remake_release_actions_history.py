from __future__ import annotations

import pytest

from tests.unit.test_smart_remake_release_actions import harness as _harness


@pytest.fixture
def history_harness():
    return _harness.__wrapped__()


@pytest.mark.asyncio
async def test_provenance_retains_unassembled_plan_versions_and_known_model_metadata(
    history_harness, monkeypatch
):
    from viraldy.modules.smart_remake import project_lifecycle

    h = history_harness
    old_state = {
        "schemaVersion": 2,
        "scenes": [
            {
                "id": "old-scene",
                "activeVersionId": "old-good",
                "versions": [
                    {
                        "id": "old-candidate",
                        "storageKey": "owned/private-candidate",
                        "mediaHash": "candidate-hash",
                        "prompt": "Archived candidate prompt",
                        "providerMetadata": {
                            "provider": "kie",
                            "model": "veo3_lite",
                            "providerRequestId": "task-old",
                            "authorization": "SECRET",
                        },
                    }
                ],
            }
        ],
        "renderPlan": {"videoModel": "veo3_lite", "imageModel": "gpt-image-2.6-sunburst"},
        "draftTimeline": {"items": [{"versionId": "old-good"}]},
    }
    h.row.context_json["p0"]["planHistory"] = [
        {
            "id": "old-plan",
            "revision": 2,
            "retiredAt": "yesterday",
            "stateSnapshot": old_state,
            "contextSnapshot": {
                "sceneMap": {"mode": "smart_remake"},
                "compileResult": {"executionMode": "fixture", "promptVersion": "compiler-v2"},
                "sourceThumbnailKeys": {"old": "private-key"},
            },
        }
    ]

    async def get_attempts(*_):
        return [
            {
                "id": "attempt",
                "stage": "video",
                "status": "completed",
                "profile": {
                    "model": "veo3_lite",
                    "modelVersion": "lite-version",
                    "quality": "max",
                    "apiKey": "SECRET",
                },
                "metadata": {
                    "mode": "fixture",
                    "promptVersion": "video-prompt-v2",
                    "request": {"secret": "SECRET"},
                },
            }
        ]

    async def get_budget(*_):
        return {}

    monkeypatch.setattr(project_lifecycle, "list_attempts", get_attempts)
    monkeypatch.setattr(project_lifecycle, "budget_summary", get_budget)
    result = await h.service.provenance(h.project)
    prior = result["planHistory"][0]
    version = prior["scenes"][0]["versions"][0]
    assert prior["id"] == "old-plan" and prior["revision"] == 2
    assert prior["plan"]["mode"] == "smart_remake"
    assert prior["plan"]["executionMode"] == "fixture"
    assert prior["plan"]["promptVersion"] == "compiler-v2"
    assert version["id"] == "old-candidate" and version["mediaHash"] == "candidate-hash"
    assert version["provider"] == "kie" and version["model"] == "veo3_lite"
    assert version["promptHash"] and "prompt" not in version
    assert result["attempts"][0]["stageMode"] is None
    assert result["attempts"][0]["modelVersion"] == "lite-version"
    assert result["attempts"][0]["promptVersion"] == "video-prompt-v2"
    assert "SECRET" not in str(result) and "private-key" not in str(result)
    assert "storageKey" not in str(result)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "runtime,mode",
    [
        ({"serverMode": "mock", "executionMode": "fixture"}, "fixture"),
        ({"serverMode": "live", "executionMode": "unverified"}, None),
        ({}, None),
    ],
)
async def test_provenance_uses_authoritative_runtime_without_inferring_live_execution(
    history_harness, monkeypatch, runtime, mode
):
    from viraldy.modules.smart_remake import project_lifecycle

    h = history_harness
    h.row.context_json["p0"]["runtime"] = runtime
    h.row.context_json["p0"]["run"] = {"mode": "live", "caseId": "unjoined-client-case"}

    async def get_attempts(*_):
        return []

    async def get_budget(*_):
        return {}

    monkeypatch.setattr(project_lifecycle, "list_attempts", get_attempts)
    monkeypatch.setattr(project_lifecycle, "budget_summary", get_budget)
    result = await h.service.provenance(h.project)
    assert result["run"]["mode"] == mode
    assert result["run"]["serverMode"] == runtime.get("serverMode")
    assert result["run"]["providerExecution"] == (runtime.get("executionMode") or "unverified")
    for field in ("caseId", "runId", "variant", "codeVersion", "configVersion", "promptVersion"):
        assert result["run"][field] is None


@pytest.mark.asyncio
async def test_provenance_ignores_forged_execution_mode_and_normalizes_openai_request_id(
    history_harness, monkeypatch
):
    from viraldy.modules.smart_remake import project_lifecycle

    h = history_harness
    h.row.context_json["p0"]["runtime"] = {
        "serverMode": "live",
        "executionMode": "unverified",
        "compileOperationId": "compile",
    }

    async def get_attempts(*_):
        return [
            {
                "id": "attempt",
                "stage": "image",
                "provider": "openai",
                "model": "gpt-image-2.6-sunburst",
                "requestHash": "request",
                "status": "completed",
                "actualUsd": None,
                "metadata": {"mode": "live", "aiMode": "live"},
                "receipt": {
                    "providerRequestId": "openai-request",
                    "executionEvidence": {
                        "mode": "live",
                        "provider": "openai",
                        "requestHash": "request",
                        "httpAttempted": True,
                    },
                },
            }
        ]

    async def get_budget(*_):
        return {}

    monkeypatch.setattr(project_lifecycle, "list_attempts", get_attempts)
    monkeypatch.setattr(project_lifecycle, "budget_summary", get_budget)
    result = await h.service.provenance(h.project)
    assert result["attempts"][0]["stageMode"] is None
    assert "executionEvidence" not in result["attempts"][0]["receipt"]
    assert result["attempts"][0]["receipt"]["requestId"] == "openai-request"
    assert result["run"]["mode"] is None
    assert result["run"]["providerExecution"] == "unverified"


def _bound_google_proof(monkeypatch):
    import httpx

    from viraldy.modules.smart_remake import provider_execution

    # This fixture exercises binding/serialization; it performs no HTTP request.
    monkeypatch.setattr(provider_execution, "_verified_tls", lambda response, host: True)
    observed = provider_execution.observe_response(
        httpx.Response(
            200,
            request=httpx.Request(
                "POST",
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-test:generateContent",
            ),
            json={"response": "fixture"},
        ),
        provider="google",
        model="gemini-test",
        operation="google.generate_content",
        owned_transport=True,
    )
    return provider_execution.bind_execution_evidence(
        observed,
        attempt_id="attempt",
        request_hash="a" * 64,
        provider="google",
        model="gemini-test",
        request_id="request-1",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case", ["bound", "preflight_zero", "mixed", "prior_compile", "wrong_request", "fixture"]
)
async def test_provenance_classifies_only_complete_current_compile_execution_evidence(
    history_harness, monkeypatch, case
):
    from viraldy.modules.smart_remake import project_lifecycle

    h = history_harness
    h.row.context_json["p0"]["runtime"] = {
        "serverMode": "live",
        "executionMode": "unverified",
        "compileOperationId": "compile-current",
    }
    proof = _bound_google_proof(monkeypatch)
    attempt = {
        "id": "attempt",
        "stage": "analysis",
        "status": "completed",
        "provider": "google",
        "model": "gemini-test",
        "requestHash": "a" * 64,
        "actualUsd": None,
        "metadata": {"operationId": "compile-current", "mode": "live"},
        "receipt": {"executionEvidence": proof},
    }
    attempts = [attempt]
    if case == "preflight_zero":
        attempts.append(
            {
                "id": "local-rejected",
                "status": "failed",
                "stage": "image",
                "actualUsd": "0",
                "receipt": {},
                "usage": {},
                "providerTaskId": None,
                "error": {"phase": "preflight", "httpAttempted": False},
            }
        )
    elif case == "mixed":
        attempts.append(
            {
                "id": "missing",
                "stage": "image",
                "provider": "openai",
                "model": "gpt-image",
                "requestHash": "b" * 64,
                "metadata": {"mode": "live"},
                "receipt": {},
                "status": "completed",
            }
        )
    elif case == "prior_compile":
        attempt["metadata"]["operationId"] = "compile-old"
    elif case == "wrong_request":
        attempt["requestHash"] = "c" * 64
    elif case == "fixture":
        h.row.context_json["p0"]["runtime"]["executionMode"] = "fixture"

    async def get_attempts(*_):
        return attempts

    async def get_budget(*_):
        return {}

    monkeypatch.setattr(project_lifecycle, "list_attempts", get_attempts)
    monkeypatch.setattr(project_lifecycle, "budget_summary", get_budget)
    result = await h.service.provenance(h.project)
    expected = (
        "live" if case in {"bound", "preflight_zero"} else "fixture" if case == "fixture" else None
    )
    assert result["run"]["mode"] == expected
    assert result["run"]["providerExecution"] == (expected or "unverified")
    assert result["run"]["serverMode"] == "live"
    if case == "wrong_request":
        assert result["attempts"][0]["stageMode"] is None
        assert "executionEvidence" not in result["attempts"][0]["receipt"]
    else:
        assert result["attempts"][0]["stageMode"] == "live"
        assert (
            result["attempts"][0]["receipt"]["executionEvidence"]["responseHash"]
            == proof["responseHash"]
        )
    assert result["attempts"][0]["actualUsd"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "unsafe",
    [
        "prompt SECRET with spaces",
        "Bearer\nSECRET",
        "api_key=SECRET",
        "https://provider.invalid/private",
        "x" * 257,
    ],
)
async def test_provenance_receipt_ids_and_amounts_never_export_arbitrary_provider_text(
    history_harness, monkeypatch, unsafe
):
    from viraldy.modules.smart_remake import project_lifecycle

    history_harness.row.state_json["scenes"][0]["versions"][0]["providerMetadata"] = {
        "providerRequestId": unsafe
    }

    async def get_attempts(*_):
        return [
            {
                "id": "attempt",
                "stage": "image",
                "providerTaskId": unsafe,
                "receipt": {
                    "requestId": unsafe,
                    "taskId": unsafe,
                    "providerRequestId": unsafe,
                    "costUsd": unsafe,
                    "actualUsd": unsafe,
                    "billedUsd": unsafe,
                },
            }
        ]

    async def get_budget(*_):
        return {}

    monkeypatch.setattr(project_lifecycle, "list_attempts", get_attempts)
    monkeypatch.setattr(project_lifecycle, "budget_summary", get_budget)
    result = await history_harness.service.provenance(history_harness.project)
    assert result["attempts"][0]["providerTaskId"] is None
    assert result["attempts"][0]["receipt"] == {}
    assert result["scenes"][0]["versions"][0]["providerRequestId"] is None
    assert unsafe not in str(result)


@pytest.mark.asyncio
async def test_provenance_preserves_bounded_ids_aliases_and_exact_numeric_receipts(
    history_harness, monkeypatch
):
    from viraldy.modules.smart_remake import project_lifecycle

    async def get_attempts(*_):
        return [
            {
                "id": "attempt",
                "stage": "image",
                "providerTaskId": "task_123-4.5/part:1",
                "receipt": {
                    "providerRequestId": "req_123-4.5/part:1",
                    "taskId": "task_123-4.5/part:1",
                    "costUsd": "0.125",
                    "actualUsd": 1,
                    "billedUsd": 0.25,
                },
            }
        ]

    async def get_budget(*_):
        return {}

    monkeypatch.setattr(project_lifecycle, "list_attempts", get_attempts)
    monkeypatch.setattr(project_lifecycle, "budget_summary", get_budget)
    result = await history_harness.service.provenance(history_harness.project)
    assert result["attempts"][0]["providerTaskId"] == "task_123-4.5/part:1"
    assert result["attempts"][0]["receipt"] == {
        "requestId": "req_123-4.5/part:1",
        "taskId": "task_123-4.5/part:1",
        "costUsd": "0.125",
        "actualUsd": "1",
        "billedUsd": "0.25",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("amount", [True, "NaN", "Infinity", "-1", "0.123456789", "1e100000"])
async def test_provenance_rejects_nonfinite_negative_or_inexact_receipt_amounts(
    history_harness, monkeypatch, amount
):
    from viraldy.modules.smart_remake import project_lifecycle

    async def get_attempts(*_):
        return [
            {
                "id": "attempt",
                "receipt": {"costUsd": amount, "actualUsd": amount, "billedUsd": amount},
            }
        ]

    async def get_budget(*_):
        return {}

    monkeypatch.setattr(project_lifecycle, "list_attempts", get_attempts)
    monkeypatch.setattr(project_lifecycle, "budget_summary", get_budget)
    result = await history_harness.service.provenance(history_harness.project)
    assert result["attempts"][0]["receipt"] == {}
