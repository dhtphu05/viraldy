from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProviderUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    cached_input_tokens: int | None = Field(default=None, ge=0)


def extract_provider_usage(value: object) -> ProviderUsage:
    usage = _get(value, "usage")
    if usage is None:
        return ProviderUsage()
    input_details = _get(usage, "input_tokens_details")
    return ProviderUsage(
        input_tokens=_int_or_none(_get(usage, "input_tokens")),
        output_tokens=_int_or_none(_get(usage, "output_tokens")),
        total_tokens=_int_or_none(_get(usage, "total_tokens")),
        cached_input_tokens=_int_or_none(_get(input_details, "cached_tokens")),
    )


def _get(value: object, key: str) -> Any:
    if value is None:
        return None
    if isinstance(value, Mapping):
        return value.get(key)
    return getattr(value, key, None)


def _int_or_none(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    return None
