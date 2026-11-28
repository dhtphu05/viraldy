"""Separate observed provider outcomes from their still-unknown monetary bill."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid5

from viraldy.shared.errors.base import AppError

from .generation_expectations import (
    require_generation_expectations,
    validate_generation_expectations,
)
from .project_policy import stable_hash
from .provider_execution import validated_execution_evidence

IMAGE_REJECTION_CODES = frozenset({
    "OPENAI_IMAGE_AUTH_FAILED", "OPENAI_IMAGE_PERMISSION_DENIED",
    "OPENAI_IMAGE_RATE_LIMITED", "OPENAI_IMAGE_CREDITS_EXHAUSTED", "OPENAI_IMAGE_REQUEST_REJECTED",
})
VIDEO_REJECTION_CODES = frozenset({
    "KIE_AUTH_FAILED", "KIE_CREDITS_EXHAUSTED", "KIE_RATE_LIMITED",
    "KIE_VALIDATION_FAILED",
})
PROVIDER_REJECTION_CODES = frozenset({
    "insufficient_quota", "billing_hard_limit_reached", "rate_limit_exceeded",
    "credit_balance_exhausted", "project_spend_limit_exceeded", "organization_spend_limit_exceeded",
    "organization_usage_limit_exceeded", "slow_down",
})
REJECTION_HTTP_STATUSES = frozenset({400, 401, 403, 404, 413, 422, 429})


def is_known_image_rejection(attempt: Any) -> bool:
    """A server-observed HTTP rejection settles control, never asserts a free bill."""
    receipt = getattr(attempt, "receipt_json", None) or {}
    error = getattr(attempt, "error_json", None) or {}
    code = receipt.get("errorCode")
    if (
        getattr(attempt, "status", None) != "failed"
        or getattr(attempt, "stage", None) != "image"
        or getattr(attempt, "provider", None) != "openai"
        or not isinstance(code, str)
        or code not in IMAGE_REJECTION_CODES
        or (error.get("errorCode") is not None and error["errorCode"] != code)
        or ("httpStatus" in receipt and (
            type(receipt["httpStatus"]) is not int
            or receipt["httpStatus"] not in REJECTION_HTTP_STATUSES
        ))
        or getattr(attempt, "provider_task_id", None)
        or getattr(attempt, "usage_json", None)
    ):
        return False
    proof = validated_execution_evidence({
        "id": str(attempt.id), "requestHash": attempt.request_hash,
        "provider": attempt.provider, "model": attempt.model,
        "providerTaskId": getattr(attempt, "provider_task_id", None), "receipt": receipt,
    })
    return proof is not None and proof["operation"] == "openai.images.edit"


def is_known_video_rejection(attempt: Any) -> bool:
    """A verified KIE rejection settles control while its monetary bill stays unknown."""
    receipt = getattr(attempt, "receipt_json", None)
    error = getattr(attempt, "error_json", None)
    if not isinstance(receipt, dict) or (error is not None and not isinstance(error, dict)):
        return False
    error = error or {}
    code = receipt.get("errorCode")
    status, provider_code = receipt.get("httpStatus"), receipt.get("providerCode")
    if (
        getattr(attempt, "status", None) != "failed"
        or getattr(attempt, "stage", None) != "video"
        or getattr(attempt, "provider", None) != "kie"
        or getattr(attempt, "model", None) != "veo-3-1"
        or getattr(attempt, "purpose", None) not in {"initial", "repair"}
        or not isinstance(code, str) or code not in VIDEO_REJECTION_CODES
        or (error.get("errorCode") is not None and error["errorCode"] != code)
        or ("httpStatus" in receipt and (
            type(status) is not int or not (status == 200 or 400 <= status < 500)
        ))
        or ("providerCode" in receipt and (
            type(provider_code) is not int or not 400 <= provider_code < 500
        ))
        or receipt.get("requestOutcome", "rejected") != "rejected"
        or getattr(attempt, "provider_task_id", None)
        or getattr(attempt, "usage_json", None)
    ):
        return False
    proof = validated_execution_evidence({
        "id": str(attempt.id), "requestHash": attempt.request_hash,
        "provider": attempt.provider, "model": attempt.model,
        "providerTaskId": None, "receipt": receipt,
    })
    return proof is not None and proof["operation"] == "kie.tasks.create"


def _is_unknown_image_transport(attempt: Any) -> bool:
    """A lost synchronous image response has no response witness to reconcile."""
    from .engine.openai_images import SUPPORTED_IMAGE_MODELS

    metadata = getattr(attempt, "metadata_json", None)
    receipt = {"errorCode": "OPENAI_IMAGE_SUBMISSION_UNRESOLVED"}
    submitted = getattr(attempt, "submitted_at", None)
    if (
        getattr(attempt, "stage", None) != "image"
        or getattr(attempt, "provider", None) != "openai"
        or getattr(attempt, "model", None) not in SUPPORTED_IMAGE_MODELS
        or getattr(attempt, "purpose", None) not in {"initial", "repair"}
        or getattr(attempt, "actual_usd", None) is not None
        or getattr(attempt, "receipt_json", None) != receipt
        or getattr(attempt, "error_json", None) != receipt
        or not isinstance(metadata, dict)
        or not isinstance(submitted, datetime) or submitted.utcoffset() != UTC.utcoffset(None)
    ):
        return False
    slot = metadata.get("slot")
    return (
        isinstance(slot, str) and re.fullmatch(r"image:(0|[1-9][0-9]*)(:ending)?", slot) is not None
        and getattr(attempt, "idempotency_key", None) == f"{metadata.get('operationId')}:{slot}"
    )


def _is_authorized_replacement_record(attempt: Any, authorization: Any) -> bool:
    """Validate one server consent against this unchanged unknown provider receipt."""
    metadata = getattr(attempt, "metadata_json", None)
    receipt = getattr(attempt, "receipt_json", None)
    usage = getattr(attempt, "usage_json", None)
    image_transport = _is_unknown_image_transport(attempt)
    if (
        not isinstance(metadata, dict)
        or not isinstance(authorization, dict) or not isinstance(receipt, dict)
        or set(authorization) != {
            "schemaVersion", "actorId", "operationId", "attemptId", "requestHash",
            "receiptHash", "replacementKey", "confirmedAt", "reason",
        }
        or type(authorization.get("schemaVersion")) is not int
        or authorization["schemaVersion"] != 1
        or getattr(attempt, "status", None) != "unknown"
        or not (image_transport or (
            getattr(attempt, "stage", None) == "video"
            and getattr(attempt, "provider", None) == "kie"
            and getattr(attempt, "model", None) == "veo-3-1"
        ))
        or getattr(attempt, "provider_task_id", None) not in (None, "")
        or (usage is not None and (not isinstance(usage, dict) or usage))
        or not isinstance(authorization.get("reason"), str)
        or not authorization["reason"].strip() or len(authorization["reason"]) > 1000
    ):
        return False
    try:
        for key in ("actorId", "operationId", "attemptId", "replacementKey"):
            if (
                not isinstance(authorization[key], str)
                or str(UUID(authorization[key])) != authorization[key]
            ):
                return False
        confirmed = datetime.fromisoformat(authorization["confirmedAt"])
        if confirmed.utcoffset() != UTC.utcoffset(None) or confirmed > datetime.now(UTC):
            return False
    except (TypeError, ValueError):
        return False
    if (
        authorization["actorId"] != str(getattr(attempt, "actor_id", None))
        or authorization["operationId"] != metadata.get("operationId")
        or authorization["attemptId"] != str(attempt.id)
        or authorization["requestHash"] != attempt.request_hash
        or authorization["receiptHash"] != stable_hash(receipt)
    ):
        return False
    if image_transport:
        # Explicit consent settles permission for one replacement, not the outcome/bill.
        return bool(confirmed >= attempt.submitted_at)
    proof = validated_execution_evidence({
        "id": str(attempt.id), "requestHash": attempt.request_hash,
        "provider": attempt.provider, "model": attempt.model,
        "providerTaskId": None, "receipt": receipt,
    })
    return (
        proof is not None and proof["operation"] == "kie.tasks.create"
        and confirmed >= datetime.fromisoformat(proof["observedAt"])
    )


def authorized_unconfirmed_replacement_keys(attempt: Any) -> frozenset[str]:
    """Read valid additive admin consents without rewriting primary or historical records."""
    metadata = getattr(attempt, "metadata_json", None)
    if not isinstance(metadata, dict):
        return frozenset()
    additional = metadata.get("additionalReplacementAuthorizations")
    records = [metadata.get("replacementAuthorization")]
    if isinstance(additional, list):
        records.extend(additional)
    return frozenset(
        record["replacementKey"] for record in records
        if isinstance(record, dict) and _is_authorized_replacement_record(attempt, record)
    )


def is_authorized_unconfirmed_replacement(attempt: Any) -> bool:
    """Recognize exact server-recorded consent, without changing the unknown outcome."""
    return bool(authorized_unconfirmed_replacement_keys(attempt))


def is_completed_analysis_response(attempt: Any) -> bool:
    """A completed synchronous response may be unusable without still being in flight."""
    receipt, error = getattr(attempt, "receipt_json", None), getattr(attempt, "error_json", None)
    usage = getattr(attempt, "usage_json", None)
    if (
        getattr(attempt, "status", None) not in {"unknown", "failed"}
        or getattr(attempt, "stage", None) != "analysis"
        or getattr(attempt, "purpose", None) != "initial"
        or getattr(attempt, "provider", None) != "google"
        or getattr(attempt, "provider_task_id", None)
        or not isinstance(receipt, dict)
        or not isinstance(error, dict)
        or error.get("code") != "MODEL_ATTEMPT_UNCERTAIN"
        or not isinstance(usage, dict)
    ):
        return False
    token_fields = {"totalTokenCount", "promptTokenCount", "candidatesTokenCount"}
    counts = {key: value for key, value in usage.items() if key in token_fields}
    if not counts or any(type(value) is not int or value < 0 for value in counts.values()):
        return False
    if not any(counts.values()):
        return False
    proof = validated_execution_evidence({
        "id": str(attempt.id), "requestHash": attempt.request_hash,
        "provider": attempt.provider, "model": attempt.model,
        "providerTaskId": None, "receipt": receipt,
    })
    return (
        proof is not None
        and proof["operation"] == "google.generate_content"
        and bool(proof.get("requestId"))
        and receipt.get("requestId") == proof["requestId"]
    )


def is_retired_conditioning_attempt(attempt: Any) -> bool:
    """Identify only the server-bound automatic image check removed from generation."""
    metadata = getattr(attempt, "metadata_json", None) or {}
    subject = metadata.get("subject") if isinstance(metadata, dict) else None
    context_hash = metadata.get("contextHash") if isinstance(metadata, dict) else None
    if (
        getattr(attempt, "stage", None) != "inspection"
        or getattr(attempt, "provider", None) != "google"
        or getattr(attempt, "purpose", None) != "recheck"
        or getattr(attempt, "provider_task_id", None)
        or not isinstance(subject, dict) or metadata.get("stage") != "conditioning"
        or subject.get("kind") != "image" or subject.get("imageRole") != "conditioning"
        or subject.get("projectId") != str(getattr(attempt, "project_id", None))
        or not isinstance(context_hash, str) or re.fullmatch(r"[a-f0-9]{64}", context_hash) is None
    ):
        return False
    try:
        parent = UUID(metadata.get("parentOperationId"))
    except (TypeError, ValueError, AttributeError):
        return False
    return metadata.get("operationId") == str(uuid5(parent, "conditioning:" + context_hash))


def attempt_needs_reconciliation(attempt: Any) -> bool:
    if (
        getattr(attempt, "stage", None) == "analysis"
        and getattr(attempt, "purpose", None) == "loading_summary"
    ) or is_known_image_rejection(attempt) or is_known_video_rejection(attempt) or (
        is_authorized_unconfirmed_replacement(attempt)
    ) or (
        is_completed_analysis_response(attempt)
    ) or (
        is_retired_conditioning_attempt(attempt)
    ):
        return False
    return attempt.status in {"reserved", "submitted", "unknown"} or (
        attempt.status != "completed" and attempt.actual_usd is None
    )


def analysis_retry_disposition(
    row: Any, operation: Any, attempts: list[Any], *, workspace_id: Any,
) -> str:
    """Offer a new user-confirmed intent without rewriting or replaying the old request."""
    result = operation.result_json or {}
    if (
        getattr(row, "workspace_id", None) != workspace_id
        or getattr(operation, "project_id", None) != row.id
        or operation.status != "failed"
        or result.get("kind") != "compile"
        or result.get("needsReconciliation")
        or any(
            getattr(attempt, "project_id", None) != row.id
            or getattr(attempt, "workspace_id", None) != workspace_id
            or attempt_needs_reconciliation(attempt)
            for attempt in attempts
        )
    ):
        return "reconcile"
    if result.get("errorCode") in {
        "SMART_REMAKE_MODEL_ATTEMPT_UNCERTAIN", "SMART_REMAKE_ATTEMPT_RECONCILIATION_REQUIRED",
        "SMART_REMAKE_COMPILE_RECONCILIATION_REQUIRED",
    } and not any(
        (attempt.metadata_json or {}).get("operationId") == str(operation.id)
        and is_completed_analysis_response(attempt)
        for attempt in attempts
    ):
        return "reconcile"
    return "new_analysis"


def image_rejection_details(value: Any) -> dict[str, Any]:
    """Keep a small server receipt; model/provider messages never enter project JSON."""
    if not isinstance(value, dict) or value.get("requestOutcome") != "rejected":
        return {}
    status = value.get("httpStatus")
    if type(status) is not int or status not in REJECTION_HTTP_STATUSES:
        return {}
    details: dict[str, Any] = {"requestOutcome": "rejected", "httpStatus": status}
    for key in ("providerErrorCode", "providerErrorType"):
        if isinstance(value.get(key), str) and value[key] in PROVIDER_REJECTION_CODES | {
            "rate_limit_error", "invalid_request_error", "authentication_error",
            "permission_error", "server_error",
        }:
            details[key] = value[key]
    if isinstance(value.get("classification"), str) and value["classification"] in {
        "credits_exhausted", "rate_limit", "ambiguous",
    }:
        details["classification"] = value["classification"]
    retry_after = value.get("retryAfterSeconds")
    if type(retry_after) is int and 0 <= retry_after <= 86400:
        details["retryAfterSeconds"] = retry_after
    return details


def initial_render_recovery(row: Any, operation: Any, attempts: list[Any]) -> dict[str, Any] | None:
    """Offer explicit initial retry only before any clip/video submission exists."""
    result = operation.result_json or {}
    if (
        operation.project_id != row.id
        or operation.status != "failed"
        or result.get("kind") != "render"
        or result.get("needsReconciliation") is not False
        or not isinstance(result.get("errorCode"), str)
        or result["errorCode"] not in IMAGE_REJECTION_CODES
        or result.get("tasks")
        or not row.state_json.get("scenes")
        or any(s.get("versions") or s.get("activeVersionId") for s in row.state_json["scenes"])
        or any(getattr(a, "stage", None) == "video" for a in attempts)
        or any(attempt_needs_reconciliation(a) for a in attempts)
    ):
        return None
    try:
        require_generation_expectations(row.context_json)
        if result.get("expectationsHash") != row.context_json.get("expectationsHash"):
            return None
        validate_generation_expectations(
            result.get("generationExpectations"), result.get("expectationsHash")
        )
    except (AppError, KeyError, TypeError, ValueError):
        return None
    image_bindings = {
        image.get("attemptId"): image.get("requestHash")
        for image in result.get("images", {}).values()
    }
    rejected = next((a for a in attempts if (
        getattr(a, "project_id", None) == row.id
        and getattr(a, "workspace_id", None) == row.workspace_id
        and getattr(a, "purpose", None) == "initial"
        and image_bindings.get(str(a.id)) == a.request_hash
        and (a.metadata_json or {}).get("operationId") == str(operation.id)
        and is_known_image_rejection(a)
    )), None)
    if rejected is None:
        return None
    recovery: dict[str, Any] = {
        "kind": "retry_initial_render", "stage": "image",
        "errorCode": result["errorCode"], "requestKey": operation.idempotency_key,
    }
    receipt = rejected.receipt_json
    if (
        isinstance(receipt.get("providerErrorCode"), str)
        and receipt["providerErrorCode"] in PROVIDER_REJECTION_CODES
    ):
        recovery["providerErrorCode"] = receipt["providerErrorCode"]
    status = receipt.get("httpStatus")
    if type(status) is int and status in REJECTION_HTTP_STATUSES:
        recovery["httpStatus"] = status
    retry_after = receipt.get("retryAfterSeconds")
    if type(retry_after) is int and 0 <= retry_after <= 86400:
        recovery["retryAfterSeconds"] = retry_after
    return recovery
