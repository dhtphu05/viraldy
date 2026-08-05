from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def sanitize_postgres_json(value: Any) -> Any:
    """Remove values PostgreSQL JSONB cannot store while preserving JSON shape."""
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, Mapping):
        return {
            sanitize_postgres_json(key): sanitize_postgres_json(nested)
            for key, nested in value.items()
        }
    if isinstance(value, Sequence) and not isinstance(value, bytes | bytearray | memoryview):
        return [sanitize_postgres_json(item) for item in value]
    return value
