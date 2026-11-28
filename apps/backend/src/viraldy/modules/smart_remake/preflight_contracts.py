"""Read-only action scope and server-controlled budget recommendations."""

from __future__ import annotations

from typing import Any, Literal, cast
from uuid import UUID

from pydantic import (
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    model_serializer,
    model_validator,
)

from .inspection_service import InspectionSubjectRequest
from .project_contracts import SmartRemakeApiModel, SmartRemakeBudgetPolicy
from .repair_schemas import RepairIntent

PreflightAction = Literal["analyze", "reanalyze", "render", "repair", "inspect"]


class PreflightRequest(SmartRemakeApiModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"action": "analyze", "targetDuration": 8, "budgetMode": "unlimited"}]
        }
    )

    action: PreflightAction
    budgetMode: Literal["unlimited", "limited"] | None = None
    projectId: str | None = None
    expectedRevision: int | None = Field(default=None, ge=1)
    targetDuration: Literal[8, 12, 16] | None = None
    referenceStartFrame: int | None = Field(default=None, ge=0)
    analysisScope: Literal["excerpt", "full_source"] | None = None
    sourceDurationSeconds: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    requiresCharacter: bool = False
    sceneId: str | None = Field(default=None, min_length=1, max_length=200)
    baseVersionId: str | None = Field(default=None, min_length=1, max_length=200)
    repairIntent: RepairIntent | None = None
    repairScope: Literal["provider_group"] | None = None
    subject: InspectionSubjectRequest | None = None

    @model_serializer(mode="wrap")
    def compatible_repair_scope(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        payload = cast(dict[str, Any], handler(self))
        if self.repairScope is None:
            payload.pop("repairScope", None)
        return payload

    @model_validator(mode="after")
    def matching_action(self) -> PreflightRequest:
        if self.analysisScope is not None or self.sourceDurationSeconds is not None:
            if self.action not in {"analyze", "reanalyze"}:
                raise ValueError("Source analysis scope belongs only to analysis actions.")
            if self.analysisScope == "full_source" and self.referenceStartFrame not in {None, 0}:
                raise ValueError("Full-source analysis starts at the first source frame.")
        if self.projectId is not None:
            UUID(self.projectId)
            if self.expectedRevision is None:
                raise ValueError("A saved project requires its current revision.")
        elif self.action != "analyze" or self.targetDuration is None:
            raise ValueError("A new analysis requires duration; other actions require a project.")
        if self.action == "repair" and self.sceneId is None:
            raise ValueError("A repair requires its retained scene.")
        if self.action == "inspect" and self.subject is None:
            raise ValueError("An inspection requires its retained subject.")
        if self.action != "repair" and (
            self.sceneId or self.baseVersionId or self.repairIntent or self.repairScope
        ):
            raise ValueError("Scene/base version identities belong to repair actions.")
        if self.action != "inspect" and self.subject is not None:
            raise ValueError("An inspection subject belongs to an inspection action.")
        return self


class PreflightScope(SmartRemakeApiModel):
    targetDuration: float
    sceneCount: int
    groupCount: int
    imageCount: int
    sourceStartFrame: int | None = None
    sourceEndFrame: int | None = None
    analysisScope: Literal["excerpt", "full_source"] | None = None
    sceneId: str | None = None
    baseVersionId: str | None = None
    repairScope: Literal["provider_group"] | None = None
    renderGroupId: str | None = None


class PreflightCalls(SmartRemakeApiModel):
    analysis: int = 0
    image: int = 0
    video: int = 0
    inspection: int = 0
    total: int = 0


class PreflightBudget(SmartRemakeApiModel):
    knownActualUsd: str
    reservedUsd: str | None
    exposureUsd: str | None
    additionalReservationUsd: str | None
    minimumCapUsd: str | None
    minimumMaxAttempts: int | None
    minimumDurationSeconds: int | None
    unknownCostAttempts: int = 0
    recommended: SmartRemakeBudgetPolicy


class PreflightBlocker(SmartRemakeApiModel):
    code: str
    message: str
    action: Literal["refresh", "reconcile", "new_project", "configure"] | None = None


class PreflightResponse(SmartRemakeApiModel):
    action: PreflightAction
    projectId: str | None = None
    revision: int | None = None
    contextHash: str
    mode: str
    scope: PreflightScope
    calls: PreflightCalls
    budget: PreflightBudget | None
    blockers: list[PreflightBlocker]
