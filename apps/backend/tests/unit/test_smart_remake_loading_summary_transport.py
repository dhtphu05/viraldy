"""The optional summary has one distinct, accurately described model attempt."""

from __future__ import annotations

from uuid import uuid4

import httpx
import pytest

from tests.unit.test_smart_remake_unlimited_ledger import stored_ledger as _stored_ledger
from viraldy.modules.smart_remake import budgeted_analysis
from viraldy.modules.smart_remake.engine.gemini_client import HttpGeminiClient
from viraldy.modules.smart_remake.project_policy import stable_hash
from viraldy.shared.errors.base import ConflictError

stored_ledger = _stored_ledger
SHORT_PROFILE = {"maxOutputTokens": 768, "timeoutSeconds": 15, "thinkingBudget": 0}


def test_legacy_request_snapshot_and_hash_are_unchanged(monkeypatch):
    monkeypatch.setenv("SMART_REMAKE_GEMINI_MODEL", "gemini-2.5-flash")
    snapshot = budgeted_analysis.request_snapshot(
        "system", "prompt", [{"bytes": b"owned", "mime_type": "video/mp4"}]
    )
    assert snapshot["profile"] == {
        "temperature": "0.1",
        "maxOutputTokens": 16384,
        "responseMimeType": "application/json",
        "maxAttempts": 1,
        "repairJson": False,
    }
    assert (
        stable_hash(snapshot) == "46f010642c7a85d62fdd801c9b7e6396b526769fba49feb5d1833196a0a24172"
    )


@pytest.mark.asyncio
async def test_short_namespace_keeps_legacy_key_and_replays_only_its_own_request(
    stored_ledger, monkeypatch
):
    stored, operation_id, calls = stored_ledger, uuid4(), []

    class Client:
        async def generate_json(self, **kwargs):
            calls.append(kwargs)
            return {"observed": True}

    def client(**options):
        result = budgeted_analysis.LedgerGeminiClient(
            stored.session,
            stored.workspace,
            stored.project.id,
            operation_id,
            None,
            client=Client(),
            **options,
        )

        async def owned(*args):
            return stored.project

        monkeypatch.setattr(result, "_project", owned)
        monkeypatch.setattr(result, "_preflight", owned)
        return result

    deep = client()
    summary = client(
        purpose="loading_summary", attempt_namespace="loading_summary", profile=SHORT_PROFILE
    )
    await deep.generate_json(system_instruction="deep", prompt="deep source")
    await summary.generate_json(system_instruction="summary", prompt="short source")
    replay = client(
        purpose="loading_summary", attempt_namespace="loading_summary", profile=SHORT_PROFILE
    )
    await replay.generate_json(system_instruction="summary", prompt="short source")
    assert len(calls) == len(stored.rows) == 2
    assert stored.rows[0].idempotency_key == f"{operation_id}:analysis:0"
    assert stored.rows[1].idempotency_key == f"{operation_id}:analysis:loading_summary:0"
    assert stored.rows[0].profile_json == budgeted_analysis.PROFILE
    expected = {**budgeted_analysis.PROFILE, **SHORT_PROFILE}
    assert stored.rows[1].purpose == "loading_summary" and stored.rows[1].profile_json == expected
    assert stored.rows[1].metadata_json["request"]["profile"] == expected
    changed = client(
        purpose="loading_summary",
        attempt_namespace="loading_summary",
        profile={**SHORT_PROFILE, "maxOutputTokens": 512},
    )
    with pytest.raises(ConflictError):
        await changed.generate_json(system_instruction="summary", prompt="short source")
    assert len(calls) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("short", [False, True])
async def test_http_profile_matches_actual_body_and_timeout_without_extra_requests(
    monkeypatch, short
):
    monkeypatch.setenv("GEMINI_API_KEY", "offline-key")
    monkeypatch.setenv("SMART_REMAKE_GEMINI_TIMEOUT_SECONDS", "42")
    calls, timeouts = [], []

    class FakeHttp:
        def __init__(self, **kwargs):
            timeouts.append(kwargs["timeout"])

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, *args, **kwargs):
            calls.append(kwargs)
            return httpx.Response(
                200,
                request=httpx.Request("POST", "https://example.test"),
                json={"candidates": [{"content": {"parts": [{"text": "{}"}]}}]},
            )

    monkeypatch.setattr(httpx, "AsyncClient", FakeHttp)
    options = (
        {"max_output_tokens": 768, "timeout_seconds": 15, "thinking_budget": 0} if short else {}
    )
    client = HttpGeminiClient(max_attempts=1, repair_json=False, **options)
    assert await client.generate_json(system_instruction="JSON", prompt="Observe") == {}
    config = calls[0]["json"]["generationConfig"]
    assert config["maxOutputTokens"] == (768 if short else 16384)
    assert timeouts == [15 if short else 42]
    if short:
        assert config["thinkingConfig"] == {"thinkingBudget": 0}
    else:
        assert "thinkingConfig" not in config
    assert len(calls) == 1


def test_summary_ledger_profile_must_match_the_physical_transport():
    transport = HttpGeminiClient(
        max_attempts=1,
        repair_json=False,
        max_output_tokens=768,
        timeout_seconds=15,
        thinking_budget=0,
    )
    client = budgeted_analysis.LedgerGeminiClient(
        object(),
        uuid4(),
        uuid4(),
        uuid4(),
        None,
        client=transport,
        purpose="loading_summary",
        attempt_namespace="loading_summary",
        profile=SHORT_PROFILE,
    )
    assert client.profile == {**budgeted_analysis.PROFILE, **SHORT_PROFILE}
    with pytest.raises(ValueError, match="profile"):
        budgeted_analysis.LedgerGeminiClient(
            object(),
            uuid4(),
            uuid4(),
            uuid4(),
            None,
            client=transport,
            profile={"maxOutputTokens": 512},
        )


@pytest.mark.asyncio
async def test_summary_transport_enforces_total_deadline_as_a_recordable_failure(monkeypatch):
    import asyncio
    from unittest.mock import AsyncMock

    from viraldy.modules.smart_remake.engine.errors import SmartRemakeError

    monkeypatch.setenv("GEMINI_API_KEY", "offline-key")

    async def slow(**kwargs):
        await asyncio.sleep(0.1)
        return "{}"

    client = HttpGeminiClient(
        max_attempts=1, repair_json=False, max_output_tokens=768, timeout_seconds=0.01
    )
    request = AsyncMock(side_effect=slow)
    monkeypatch.setattr(client, "_request_text", request)
    with pytest.raises(SmartRemakeError, match="timed out"):
        await client.generate_json(system_instruction="JSON", prompt="Observe")
    request.assert_awaited_once()


@pytest.mark.asyncio
async def test_total_deadline_remains_unknown_in_ledger_and_never_replays_paid_request(
    stored_ledger, monkeypatch
):
    import asyncio

    from viraldy.shared.errors.base import AppError

    stored, operation_id, calls = stored_ledger, uuid4(), []
    monkeypatch.setenv("GEMINI_API_KEY", "offline-key")

    class SlowHttp:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, *args, **kwargs):
            calls.append(kwargs)
            await asyncio.sleep(0.1)
            return httpx.Response(
                200,
                request=httpx.Request("POST", "https://example.test"),
                json={"candidates": [{"content": {"parts": [{"text": "{}"}]}}]},
            )

    monkeypatch.setattr(httpx, "AsyncClient", SlowHttp)

    def model():
        transport = HttpGeminiClient(
            max_attempts=1, repair_json=False, max_output_tokens=768, timeout_seconds=0.01
        )
        client = budgeted_analysis.LedgerGeminiClient(
            stored.session,
            stored.workspace,
            stored.project.id,
            operation_id,
            None,
            client=transport,
            purpose="loading_summary",
            attempt_namespace="loading_summary",
        )

        async def owned(*args):
            return stored.project

        monkeypatch.setattr(client, "_project", owned)
        monkeypatch.setattr(client, "_preflight", owned)
        return client

    with pytest.raises(AppError) as failure:
        await model().generate_json(system_instruction="summary", prompt="Observe source")
    assert failure.value.code == "SMART_REMAKE_MODEL_ATTEMPT_UNCERTAIN"
    assert len(stored.rows) == len(calls) == 1
    assert stored.rows[0].status == "unknown" and stored.rows[0].actual_usd is None
    assert stored.rows[0].purpose == "loading_summary"
    with pytest.raises(ConflictError):
        await model().generate_json(system_instruction="summary", prompt="Observe source")
    assert len(stored.rows) == len(calls) == 1


@pytest.mark.parametrize("namespace", ["", "contains:separator", "A", "a" * 33])
def test_namespace_cannot_change_the_structure_of_persisted_attempt_keys(namespace):
    with pytest.raises(ValueError, match="namespace"):
        budgeted_analysis.LedgerGeminiClient(
            object(), uuid4(), uuid4(), uuid4(), None, attempt_namespace=namespace
        )


@pytest.mark.parametrize(
    "options",
    [{"max_output_tokens": 0}, {"timeout_seconds": float("nan")}, {"thinking_budget": -1}],
)
def test_invalid_server_transport_limits_are_rejected_without_model_calls(options):
    with pytest.raises(ValueError):
        HttpGeminiClient(**options)


@pytest.mark.asyncio
async def test_optional_billing_rejection_does_not_retry_or_fall_back(monkeypatch):
    from viraldy.modules.smart_remake.engine.errors import SmartRemakeError

    monkeypatch.setenv("GEMINI_API_KEY", "offline-key")
    calls = []

    class BillingHttp:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, *args, **kwargs):
            calls.append(kwargs)
            return httpx.Response(
                429,
                request=httpx.Request("POST", "https://example.test"),
                text="prepayment credits are depleted",
            )

    monkeypatch.setattr(httpx, "AsyncClient", BillingHttp)
    client = HttpGeminiClient(
        max_attempts=1,
        repair_json=False,
        max_output_tokens=768,
        timeout_seconds=15,
        thinking_budget=0,
    )
    with pytest.raises(SmartRemakeError, match="billing reasons"):
        await client.generate_json(system_instruction="JSON", prompt="Observe")
    assert len(calls) == 1
