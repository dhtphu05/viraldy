from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .contracts import Capture

_SENSITIVE = re.compile(
    r"api.?key|authorization|cookie|password|secret|(?:^|_)token$|access.?token|"
    r"refresh.?token|signed.?url",
    re.I,
)
_URL = re.compile(r"https?://[^\s\"<>]+")
_INLINE_CREDENTIAL = re.compile(
    r"(bearer\s+)[^\s,;]+|((?:api[_-]?key|password|secret|access[_-]?token)\s*[:=]\s*)[^\s,;]+",
    re.I,
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_hash(value: object) -> str:
    return sha256_bytes(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    )


def redact_private_values(value: Any) -> Any:
    """Strip credentials/query strings before persisting provider metadata or failures."""
    if isinstance(value, Mapping):
        return {
            str(key): "[redacted]" if _SENSITIVE.search(str(key)) else redact_private_values(item)
            for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return [redact_private_values(item) for item in value]
    if isinstance(value, str):
        return _INLINE_CREDENTIAL.sub(
            lambda match: f"{match.group(1) or match.group(2)}[redacted]",
            _URL.sub(_safe_url, value),
        )
    return value


def _safe_url(match: re.Match[str]) -> str:
    parts = urlsplit(match.group())
    hostname = parts.hostname or ""
    port = f":{parts.port}" if parts.port else ""
    return urlunsplit((parts.scheme, f"{hostname}{port}", parts.path, "", ""))


def capture_provenance(payload: Mapping[str, object]) -> list[Capture]:
    """Load normalized captured records, never private lifecycle JSON.

    v1 export envelope: schemaVersion + captures (evaluation Capture wire fields).
    Runtime projections use runtime_adapter; this envelope is for retained captures.
    """
    if payload.get("schemaVersion") != "smart_remake_capture_v1":
        raise ValueError("unsupported public Smart Remake provenance version")
    captures = payload.get("captures")
    if not isinstance(captures, list):
        raise ValueError("public provenance requires captures[]")
    return [Capture.model_validate(redact_private_values(item)) for item in captures]
