"""Small public diagnostics, separate from private provider requests and receipts."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from .provider_execution import safe_provider_identifier


def sanitize_provider_message(value: Any, *, secrets: Iterable[str] = ()) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    message = value
    for secret in secrets:
        if isinstance(secret, str) and secret:
            message = message.replace(secret, "[REDACTED]")
    message = re.sub(r"https?://\S+", "[URL]", message, flags=re.I)
    message = re.sub(r"\bBearer\s+\S+", "[REDACTED]", message, flags=re.I)
    message = re.sub(r"\bsk-[A-Za-z0-9_-]+|\b[a-f0-9]{32}(?:[a-f0-9]{32})?\b",
                     "[REDACTED]", message, flags=re.I)
    # Keep the provider's reason, but never publish an echoed prompt/request body.
    message = re.sub(
        r"([\"']?(?:prompt|image_?prompt|video_?prompt|input_?data|payload|request[ _]?body|"
        r"api[ _]?key|authorization)[\"']?\s*[:=])\s*[\s\S]*",
        r"\1 [REDACTED]", message, flags=re.I,
    )
    return " ".join(message.split())[:500] or None


def sanitize_provider_error(value: Any, *, secrets: Iterable[str] = ()) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    secrets = tuple(secrets)
    result: dict[str, Any] = {}
    status = value.get("httpStatus", value.get("status"))
    if type(status) is int and 100 <= status <= 599:
        result["httpStatus"] = status
    code = value.get("providerCode")
    if type(code) is int or (
        isinstance(code, str) and re.fullmatch(r"[A-Za-z0-9_.:-]{1,120}", code)
        and sanitize_provider_message(code, secrets=secrets) == code
    ):
        result["providerCode"] = code
    if message := sanitize_provider_message(value.get("providerMessage"), secrets=secrets):
        result["providerMessage"] = message
    return result


def public_provider_error_fields(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    fields: dict[str, Any] = {}
    if error := sanitize_provider_error(value.get("providerError")):
        fields["providerError"] = error
    task_id = value.get("providerTaskId", value.get("taskId"))
    if safe_provider_identifier(task_id):
        fields["providerTaskId"] = task_id
    return fields
