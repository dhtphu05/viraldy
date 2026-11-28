"""Server-owned HTTP execution evidence; transport proof is separate from billing."""

from __future__ import annotations

import copy
import hashlib
import re
import ssl
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

import httpx

_OPERATIONS = {
    "google.generate_content": (
        "google",
        "generativelanguage.googleapis.com",
        "POST",
        r"/v1beta/models/[^/]+:generateContent",
    ),
    "openai.images.edit": ("openai", "api.openai.com", "POST", r"/v1/images/edits"),
    "kie.tasks.create": ("kie", "api.kie.ai", "POST", r"/api/v1/jobs/createTask"),
    "kie.tasks.get": ("kie", "api.kie.ai", "GET", r"/api/v1/(?:jobs/recordInfo|veo/record-info)"),
}
_SEAL = object()
_HASH = re.compile(r"[a-f0-9]{64}")


@dataclass(frozen=True, slots=True)
class ProviderExecutionEvidence:
    """Nominal witness minted by the owned, verified HTTP response observer only."""

    provider: str
    model: str
    operation: str
    response_hash: str
    observed_at: str
    _seal: object
    _binding: tuple[str, str, str, str] | None = field(default=None, init=False, repr=False)


def _verified_tls(response: httpx.Response, host: str) -> bool:
    stream = response.extensions.get("network_stream")
    if stream is None or not hasattr(stream, "get_extra_info"):
        return False
    try:
        connection = stream.get_extra_info("ssl_object")
        return (
            isinstance(connection, ssl.SSLObject | ssl.SSLSocket)
            and connection.server_hostname == host
            and connection.context.check_hostname
            and connection.context.verify_mode == ssl.CERT_REQUIRED
            and connection.version() is not None
        )
    except (AttributeError, OSError, ValueError):
        return False


def observe_response(
    response: httpx.Response,
    *,
    provider: str,
    model: str,
    operation: str,
    owned_transport: bool,
) -> ProviderExecutionEvidence | None:
    """Observe inside the client context; injected transports never attest live."""
    expected = _OPERATIONS.get(operation)
    if (
        not owned_transport
        or expected is None
        or expected[0] != provider
        or not isinstance(response, httpx.Response)
        or not _verified_tls(response, expected[1])
    ):
        return None
    try:
        request = response.request
    except (RuntimeError, AttributeError):
        return None
    if (
        request.url.scheme != "https"
        or request.url.host != expected[1]
        or request.method != expected[2]
        or re.fullmatch(expected[3], request.url.path) is None
    ):
        return None
    return ProviderExecutionEvidence(
        provider,
        model,
        operation,
        hashlib.sha256(response.content).hexdigest(),
        datetime.now(UTC).isoformat(),
        _SEAL,
    )


def _safe_identifier(value: object) -> bool:
    return (
        isinstance(value, str)
        and 0 < len(value) <= 256
        and re.fullmatch(r"[A-Za-z0-9_.:/-]+", value) is not None
        and "://" not in value
    )


safe_provider_identifier = _safe_identifier


def bind_execution_evidence(
    value: object,
    *,
    attempt_id: UUID | str,
    request_hash: str,
    provider: str,
    model: str,
    request_id: str | None = None,
    task_id: str | None = None,
) -> dict[str, Any] | None:
    """Bind a nominal physical witness to an immutable durable ledger intent."""
    if (
        not isinstance(value, ProviderExecutionEvidence)
        or value._seal is not _SEAL
        or value.provider != provider
        or value.model != model
        or _HASH.fullmatch(request_hash) is None
    ):
        return None
    binding = (str(attempt_id), request_hash, provider, model)
    if value._binding is not None and value._binding != binding:
        return None
    # Internal one-time binding prevents a borrowed witness from attesting a
    # different intent. The frozen public fields remain immutable.
    object.__setattr__(value, "_binding", binding)
    proof: dict[str, Any] = {
        "version": 1,
        "mode": "live",
        "transport": "verified_tls",
        "provider": provider,
        "model": model,
        "attemptId": str(attempt_id),
        "requestHash": request_hash,
        "operation": value.operation,
        "responseHash": value.response_hash,
        "observedAt": value.observed_at,
    }
    for key, identifier in (("requestId", request_id), ("taskId", task_id)):
        if _safe_identifier(identifier):
            proof[key] = identifier
    return proof


def validated_execution_evidence(attempt: dict[str, Any]) -> dict[str, Any] | None:
    """Validate persisted server receipt evidence against its owning ledger row."""
    proof = (attempt.get("receipt") or {}).get("executionEvidence")
    required = {
        "version",
        "mode",
        "transport",
        "provider",
        "model",
        "attemptId",
        "requestHash",
        "operation",
        "responseHash",
        "observedAt",
    }
    if not isinstance(proof, dict) or not required <= proof.keys():
        return None
    if proof.keys() - required - {"requestId", "taskId"}:
        return None
    if any(not isinstance(proof[key], str) for key in required - {"version"}):
        return None
    operation = _OPERATIONS.get(proof.get("operation", ""))
    if (
        type(proof.get("version")) is not int
        or proof["version"] != 1
        or proof.get("mode") != "live"
        or proof.get("transport") != "verified_tls"
        or operation is None
        or operation[0] != attempt.get("provider")
        or any(
            proof.get(key) != attempt.get(source)
            for key, source in (
                ("attemptId", "id"),
                ("requestHash", "requestHash"),
                ("provider", "provider"),
                ("model", "model"),
            )
        )
        or any(
            not isinstance(proof.get(key), str) or _HASH.fullmatch(proof[key]) is None
            for key in ("requestHash", "responseHash")
        )
        or any(not _safe_identifier(proof[key]) for key in ("requestId", "taskId") if key in proof)
    ):
        return None
    try:
        timestamp = datetime.fromisoformat(proof["observedAt"])
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            return None
    except (TypeError, ValueError):
        return None
    if proof.get("taskId") and attempt.get("providerTaskId") != proof["taskId"]:
        return None
    return copy.deepcopy(proof)


def _proven_local_zero(attempt: dict[str, Any]) -> bool:
    error = attempt.get("error") or {}
    try:
        zero = Decimal(str(attempt.get("actualUsd"))) == 0
    except InvalidOperation:
        zero = False
    receipt = attempt.get("receipt") or {}
    local_receipt = not receipt or (
        set(receipt) == {"intentHash"} and receipt["intentHash"] == attempt.get("requestHash")
    )
    return (
        attempt.get("status") == "failed"
        and zero
        and error.get("phase") == "preflight"
        and error.get("httpAttempted") is False
        and local_receipt
        and not attempt.get("providerTaskId")
        and not attempt.get("usage")
    )


def classify_run_execution(
    attempts: list[dict[str, Any]], *, runtime: dict[str, Any]
) -> dict[str, Any]:
    if runtime.get("executionMode") == "fixture":
        return {"mode": "fixture", "providerExecution": "fixture"}
    physical = [attempt for attempt in attempts if not _proven_local_zero(attempt)]
    compile_id = runtime.get("compileOperationId")
    current_analysis = (
        any(
            attempt.get("stage") == "analysis"
            and (attempt.get("metadata") or {}).get("operationId") == compile_id
            for attempt in physical
        )
        if isinstance(compile_id, str) and compile_id
        else False
    )
    live = (
        bool(physical)
        and current_analysis
        and all(validated_execution_evidence(attempt) is not None for attempt in physical)
    )
    return {
        "mode": "live" if live else None,
        "providerExecution": "live" if live else "unverified",
    }
