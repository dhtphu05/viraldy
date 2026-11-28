"""Strict request boundaries for the owned, pre-provider Smart Remake intake.

The persisted ``p0`` metadata key and existing environment/contract identifiers
remain compatibility boundaries. Source modules and symbols use functional names.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer,
    model_validator,
)

from .rights_policy import RightsPolicyVersion


class SmartRemakeApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)


class SmartRemakeRequirements(SmartRemakeApiModel):
    intent: str = Field(min_length=1, max_length=4000)
    keep: list[str] = Field(default_factory=list, max_length=40)
    replace: list[str] = Field(default_factory=list, max_length=40)
    forbid: list[str] = Field(default_factory=list, max_length=40)
    claims: list[str] = Field(default_factory=list, max_length=40)
    requiresCharacter: bool = False
    characterReferencePolicy: Literal["product_and_character"] = "product_and_character"

    @field_validator("keep", "replace", "forbid", "claims")
    @classmethod
    def bounded_requirements(cls, values: list[str]) -> list[str]:
        if any(not value.strip() or len(value) > 2000 for value in values):
            raise ValueError("Requirements must contain 1–2000 nonblank characters.")
        return [value.strip() for value in values]


class SmartRemakeRightsDeclaration(SmartRemakeApiModel):
    basis: Literal["owned", "licensed", "permission", "public_domain", "attested"]
    scope: str = Field(default="", max_length=2000)
    declared: bool
    evidenceNote: str = Field(default="", max_length=4000)
    attribution: str | None = Field(default=None, max_length=2000)
    revoked: bool = False


class SmartRemakeCharacterConsent(SmartRemakeApiModel):
    consented: bool
    scope: str = Field(min_length=1, max_length=2000)
    evidenceNote: str = Field(min_length=1, max_length=4000)
    revoked: bool = False


class SmartRemakeRightsAttestation(SmartRemakeApiModel):
    policyVersion: RightsPolicyVersion
    accepted: bool
    revoked: bool = False


class SmartRemakeRights(SmartRemakeApiModel):
    source: SmartRemakeRightsDeclaration
    product: SmartRemakeRightsDeclaration
    character: SmartRemakeRightsDeclaration | None = None
    characterConsent: SmartRemakeCharacterConsent | None = None
    attestation: SmartRemakeRightsAttestation | None = None
    providerDisclosureAcknowledged: bool

    @model_serializer(mode="wrap")
    def preserve_legacy_serialization(
        self, handler: SerializerFunctionWrapHandler
    ) -> dict[str, Any]:
        saved: dict[str, Any] = handler(self)
        # Existing intake/metadata idempotency hashes include the original rights shape.
        return {
            key: value
            for key, value in saved.items()
            if key != "attestation" or self.attestation is not None
        }


class SmartRemakeBudgetPolicy(SmartRemakeApiModel):
    capUsd: str | None = Field(default=None, examples=["5.00"])
    maxAttempts: int | None = Field(default=20, ge=1, le=1000)
    maxDurationSeconds: int | None = Field(default=1800, ge=1, le=86400)
    mode: Literal["unlimited", "limited"] | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_mode(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        cap = value.get("capUsd")
        empty_cap = cap is None or (isinstance(cap, str) and not cap.strip())
        if value.get("mode") == "unlimited" or (value.get("mode") is None and empty_cap):
            return {
                **{
                    key: item
                    for key, item in value.items()
                    if key not in {"capUsd", "maxAttempts", "maxDurationSeconds"}
                },
                "mode": "unlimited",
            }
        return value

    @field_validator("capUsd")
    @classmethod
    def exact_decimal(cls, value: str | None) -> str | None:
        from decimal import Decimal

        if value is None:
            return value
        if not re.fullmatch(r"(?:0|[1-9]\d{0,7})(?:\.\d{1,6})?", value):
            raise ValueError(
                "capUsd must be a positive USD decimal string with at most 6 decimals."
            )
        if Decimal(value) <= 0:
            raise ValueError("capUsd must be positive.")
        return value

    @model_validator(mode="after")
    def require_limited_controls(self) -> SmartRemakeBudgetPolicy:
        if self.mode != "unlimited" and (
            self.capUsd is None or self.maxAttempts is None or self.maxDurationSeconds is None
        ):
            raise ValueError("A limited budget requires positive money, attempt and time limits.")
        return self

    @model_serializer(mode="wrap")
    def preserve_legacy_serialization(
        self, handler: SerializerFunctionWrapHandler
    ) -> dict[str, Any]:
        if self.mode == "unlimited":
            return {"mode": "unlimited"}
        saved: dict[str, Any] = handler(self)
        # Missing mode is the original bounded-policy wire/hash contract.
        return {
            key: value for key, value in saved.items() if key != "mode" or self.mode is not None
        }


class SmartRemakeIntakeRequest(SmartRemakeApiModel):
    idempotencyKey: str = Field(min_length=1, max_length=200)
    projectName: str = Field(default="Smart Remake", min_length=1, max_length=200)
    targetDuration: Literal[8, 12, 16] = 16
    requirements: SmartRemakeRequirements
    rights: SmartRemakeRights
    budget: SmartRemakeBudgetPolicy = Field(default_factory=SmartRemakeBudgetPolicy)


class SmartRemakeMutation(SmartRemakeApiModel):
    expectedRevision: int = Field(ge=1)
    idempotencyKey: str = Field(min_length=1, max_length=200)


class SmartRemakeRequirementsPatch(SmartRemakeMutation):
    requirements: SmartRemakeRequirements


class SmartRemakeRightsPatch(SmartRemakeMutation):
    rights: SmartRemakeRights


class SmartRemakeBudgetPatch(SmartRemakeMutation):
    budget: SmartRemakeBudgetPolicy


class SmartRemakeRightsReviewRequest(SmartRemakeMutation):
    evidenceNote: str = Field(min_length=1, max_length=4000)
