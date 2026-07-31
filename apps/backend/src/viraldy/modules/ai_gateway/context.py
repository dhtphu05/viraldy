from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Literal
from urllib.parse import parse_qsl, urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from viraldy.modules.ai_gateway.operations import AiOperationName
from viraldy.modules.products.contracts import ProductContextV1

_SECRET_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "credential",
        "password",
        "presigned_url",
        "secret",
        "signed_url",
        "token",
    }
)
_SIGNED_QUERY_KEYS = frozenset(
    {
        "awsaccesskeyid",
        "credential",
        "expires",
        "googleaccessid",
        "signature",
        "sig",
        "token",
        "x-amz-credential",
        "x-amz-signature",
    }
)


class OperationContextBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceItemForModelV1(OperationContextBase):
    evidence_id: UUID
    source_artifact_id: UUID | None = None
    source_version_id: UUID
    evidence_type: str = Field(min_length=1, max_length=100)
    observation_id: str | None = Field(default=None, max_length=200)
    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, ge=0)
    value: dict[str, object]
    confidence: float | None = Field(default=None, ge=0, le=1)
    source: str = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_time_range(self) -> EvidenceItemForModelV1:
        if (
            self.start_ms is not None
            and self.end_ms is not None
            and self.end_ms < self.start_ms
        ):
            raise ValueError("end_ms must be greater than or equal to start_ms")
        return self


class ViraldyOperationContextV1(OperationContextBase):
    operation: AiOperationName
    request_id: str = Field(min_length=1, max_length=200)
    workspace_id: UUID
    actor_user_id: UUID | None = None
    locale: Literal["en-US", "vi-VN"] = "en-US"
    creator_output_locale: Literal["en-US"] = "en-US"

    product_context: ProductContextV1 | None = None
    product_context_version: int | None = Field(default=None, ge=1)
    objective: str | None = Field(default=None, max_length=500)
    target_market: str | None = Field(default=None, max_length=100)

    source_artifact_ids: list[UUID] = Field(default_factory=list)
    source_version_ids: list[UUID] = Field(default_factory=list)
    evidence_catalog: list[EvidenceItemForModelV1] = Field(default_factory=list)

    seller_constraints: dict[str, object] = Field(default_factory=dict)
    operation_payload: dict[str, object] = Field(default_factory=dict)

    schema_version: str = Field(min_length=1, max_length=100)
    prompt_version: str = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_context(self) -> ViraldyOperationContextV1:
        if self.product_context is None and self.product_context_version is not None:
            raise ValueError("product_context_version requires product_context")
        if len(set(self.source_artifact_ids)) != len(self.source_artifact_ids):
            raise ValueError("source_artifact_ids must be unique")
        if len(set(self.source_version_ids)) != len(self.source_version_ids):
            raise ValueError("source_version_ids must be unique")
        evidence_ids = [item.evidence_id for item in self.evidence_catalog]
        if len(set(evidence_ids)) != len(evidence_ids):
            raise ValueError("evidence_catalog evidence IDs must be unique")
        _reject_sensitive_material(self.seller_constraints)
        _reject_sensitive_material(self.operation_payload)
        return self

    def stable_json(self) -> str:
        return json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )


def _reject_sensitive_material(value: object, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for raw_key, nested in value.items():
            key = str(raw_key)
            normalized = key.casefold()
            if normalized in _SECRET_KEYS:
                raise ValueError(f"sensitive field is not allowed at {path}.{key}")
            _reject_sensitive_material(nested, f"{path}.{key}")
        return
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        for index, nested in enumerate(value):
            _reject_sensitive_material(nested, f"{path}[{index}]")
        return
    if isinstance(value, str):
        if value.startswith(("data:image/", "data:audio/", "data:video/")):
            raise ValueError(f"binary data URL is not allowed at {path}")
        parsed = urlsplit(value)
        if parsed.scheme in {"http", "https"}:
            query_keys = {key.casefold() for key, _ in parse_qsl(parsed.query)}
            if query_keys & _SIGNED_QUERY_KEYS:
                raise ValueError(f"signed or credentialed URL is not allowed at {path}")
