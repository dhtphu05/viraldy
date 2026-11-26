"""One Gemini HTTP attempt per durable, owned and budgeted model intent."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Awaitable, Callable
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from viraldy.shared.errors.base import AppError, ConflictError, NotFoundError

from .budget_ledger import (
    complete_attempt,
    fail_attempt,
    mark_submitted,
    reservation_estimate,
    reserve_attempt,
    unknown_attempt,
)
from .engine.config import get_gemini_model
from .engine.gemini_client import HttpGeminiClient, SmartRemakeGeminiClient
from .models import SmartRemakeProjectModel
from .project_policy import assert_project_policy, stable_hash
from .provider_execution import bind_execution_evidence

_PHYSICAL_GEMINI_CLIENT = HttpGeminiClient

PROFILE = {
    "temperature": "0.1",
    "maxOutputTokens": 16384,
    "responseMimeType": "application/json",
    "maxAttempts": 1,
    "repairJson": False,
}


def _input_binding(row: SmartRemakeProjectModel) -> str:
    p0 = row.context_json["p0"]
    return stable_hash(
        {
            "inputHash": p0.get("inputHash"),
            "constraintsHash": p0.get("constraintsHash"),
            "assets": {
                role: {key: asset.get(key) for key in ("storageKey", "mediaHash", "mimeType")}
                for role, asset in p0.get("assets", {}).items()
            },
        }
    )


def request_snapshot(
    system: str, prompt: str, media: list[dict[str, Any]] | None,
    *, profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    references = []
    for item in media or []:
        data, mime = item.get("bytes"), item.get("mime_type", item.get("mimeType"))
        if not isinstance(data, bytes) or not isinstance(mime, str) or not mime:
            raise AppError(
                "SMART_REMAKE_MODEL_MEDIA_INVALID", "Model media requires owned bytes and MIME."
            )
        references.append(
            {
                "mediaHash": hashlib.sha256(data).hexdigest(),
                "mimeType": mime,
                "byteLength": len(data),
            }
        )
    return {
        "systemInstruction": system,
        "prompt": prompt,
        "media": references,
        "provider": "google",
        "model": get_gemini_model(),
        "profile": {**PROFILE, **(profile or {})},
    }


class LedgerGeminiClient:
    def __init__(
        self,
        session: AsyncSession,
        workspace_id: UUID,
        project_id: UUID,
        operation_id: UUID,
        actor_id: UUID | None,
        purpose: str = "initial",
        stage: Literal["analysis", "inspection"] = "analysis",
        client: SmartRemakeGeminiClient | None = None,
        metadata: dict[str, Any] | None = None,
        attempt_namespace: str | None = None,
        profile: dict[str, Any] | None = None,
    ) -> None:
        self.session = session
        self.workspace_id, self.project_id = workspace_id, project_id
        self.operation_id, self.actor_id = operation_id, actor_id
        self.purpose, self.stage = purpose, stage
        self.client = client or HttpGeminiClient(max_attempts=1, repair_json=False)
        if attempt_namespace is not None and re.fullmatch(
            r"[a-z][a-z0-9_]{0,31}", attempt_namespace
        ) is None:
            raise ValueError("A model attempt namespace must be a short server-owned identifier.")
        self.attempt_namespace = attempt_namespace
        self.profile = {**PROFILE, **(profile or {})}
        if type(self.client) is _PHYSICAL_GEMINI_CLIENT:
            self.client.max_attempts, self.client.repair_json = 1, False
            actual_profile = {**PROFILE, "maxOutputTokens": self.client.max_output_tokens}
            if self.client.timeout_seconds is not None:
                actual_profile["timeoutSeconds"] = self.client.timeout_seconds
            if self.client.thinking_budget is not None:
                actual_profile["thinkingBudget"] = self.client.thinking_budget
            if profile is not None and self.profile != actual_profile:
                raise ValueError("The ledger profile must match the actual Gemini transport.")
            self.profile = actual_profile
        self.metadata = metadata or {}
        self._ordinals: dict[str, int] = {}

    async def _project(self) -> SmartRemakeProjectModel:
        row = (
            await self.session.execute(
                select(SmartRemakeProjectModel)
                .where(
                    SmartRemakeProjectModel.id == self.project_id,
                    SmartRemakeProjectModel.workspace_id == self.workspace_id,
                )
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        if row is None:
            raise NotFoundError(
                "SMART_REMAKE_PROJECT_NOT_FOUND", "Smart Remake project was not found."
            )
        assert_project_policy(row, purpose=self.stage)
        return row

    async def generate_json(
        self, *, system_instruction: str, prompt: str, media: list[dict[str, Any]] | None = None
    ) -> Any:
        env = f"SMART_REMAKE_P0_MAX_{self.stage.upper()}_USD"
        row = await self._project()
        bound, estimate_metadata = reservation_estimate(
            row.context_json.get("p0", {}).get("budgetPolicy"), os.getenv(env),
            error_code="SMART_REMAKE_STAGE_BOUND_REQUIRED",
            message=f"Configure {env} before a paid call.",
        )
        if (
            type(self.client) is _PHYSICAL_GEMINI_CLIENT
            and not os.getenv("GEMINI_API_KEY", "").strip()
        ):
            raise AppError(
                "SMART_REMAKE_MODEL_NOT_CONFIGURED", "Configure the model provider first.", 503
            )
        snapshot = request_snapshot(system_instruction, prompt, media, profile=self.profile)
        owned_media = [
            {"bytes": item["bytes"], "mime_type": item.get("mime_type", item.get("mimeType"))}
            for item in media or []
        ]
        request_hash = stable_hash(snapshot)
        ordinal = self._ordinals.setdefault(request_hash, len(self._ordinals))
        namespace = f"{self.attempt_namespace}:" if self.attempt_namespace else ""
        key = f"{self.operation_id}:{self.stage}:{namespace}{ordinal}"
        initial_binding = _input_binding(row)
        attempt, created = await reserve_attempt(
            self.session,
            self.workspace_id,
            self.project_id,
            idempotency_key=key,
            request_hash=request_hash,
            stage=self.stage,
            reservation_usd=bound,
            actor_id=self.actor_id,
            provider="google",
            model=snapshot["model"],
            purpose=self.purpose,
            profile=self.profile,
            metadata={
                **self.metadata, "operationId": str(self.operation_id),
                "request": snapshot, **estimate_metadata,
            },
        )
        attempt_id = attempt.id
        if not created:
            row = await self._preflight(initial_binding)
            cached = row.context_json.get("p0", {}).get("modelResults", {}).get(str(attempt_id))
            if (
                attempt.status == "completed"
                and cached
                and cached.get("requestHash") == request_hash
            ):
                return cached["result"]
            raise ConflictError(
                "SMART_REMAKE_ATTEMPT_RECONCILIATION_REQUIRED",
                "Model attempt needs reconciliation; it will not be resubmitted.",
            )
        try:
            await self._preflight(initial_binding)
            await mark_submitted(
                self.session,
                self.workspace_id,
                self.project_id,
                attempt_id,
                receipt={"intentHash": request_hash},
            )
            await self._preflight(initial_binding)
        except AppError as exc:
            await self.session.rollback()
            await fail_attempt(
                self.session,
                self.workspace_id,
                self.project_id,
                attempt_id,
                error={"code": exc.code, "phase": "preflight", "httpAttempted": False},
                definitely_not_submitted=True,
                preflight_rejected=True,
            )
            raise
        try:
            if type(self.client) is _PHYSICAL_GEMINI_CLIENT:
                self.client.last_usage, self.client.last_request_id = {}, None
                self.client.last_execution_evidence = None
                self.client.last_finish_reason = None
            result = await self.client.generate_json(
                system_instruction=system_instruction, prompt=prompt, media=owned_media or None
            )
            # Merge a single cached result in SQL; no stale context snapshot can
            # discard another checker/worker's cache entry or rights mutation.
            cached = json.dumps(
                {str(attempt_id): {"requestHash": request_hash, "result": result}},
                allow_nan=False,
                ensure_ascii=False,
            )
            await self.session.execute(
                text("""
                UPDATE smart_remake_projects
                SET context_json = jsonb_set(context_json, '{p0,modelResults}',
                    COALESCE(context_json #> '{p0,modelResults}', '{}'::jsonb)
                    || CAST(:results AS jsonb), true)
                WHERE id = :project_id AND workspace_id = :workspace_id
            """),
                {
                    "results": cached,
                    "project_id": self.project_id,
                    "workspace_id": self.workspace_id,
                },
            )
            request_id = getattr(self.client, "last_request_id", None)
            receipt: dict[str, Any] = {"intentHash": request_hash}
            if isinstance(request_id, str):
                receipt["requestId"] = request_id
            proof = bind_execution_evidence(
                self.client.last_execution_evidence
                if type(self.client) is _PHYSICAL_GEMINI_CLIENT
                else None,
                attempt_id=attempt_id,
                request_hash=request_hash,
                provider="google",
                model=snapshot["model"],
                request_id=request_id,
            )
            if proof is not None:
                receipt["executionEvidence"] = proof
            usage = getattr(self.client, "last_usage", {})
            await complete_attempt(
                self.session,
                self.workspace_id,
                self.project_id,
                attempt_id,
                receipt=receipt,
                usage=usage if isinstance(usage, dict) else {},
            )
            return result
        except Exception as exc:
            await self.session.rollback()
            error_receipt: dict[str, Any] = {
                "requestId": getattr(self.client, "last_request_id", None)
            }
            proof = bind_execution_evidence(
                self.client.last_execution_evidence
                if type(self.client) is _PHYSICAL_GEMINI_CLIENT
                else None,
                attempt_id=attempt_id,
                request_hash=request_hash,
                provider="google",
                model=snapshot["model"],
                request_id=getattr(self.client, "last_request_id", None),
            )
            if proof is not None:
                error_receipt["executionEvidence"] = proof
            diagnostics: dict[str, object] = {}
            cause = getattr(exc, "code", None)
            if isinstance(cause, str) and cause in {
                "SMART_REMAKE_GEMINI_ERROR", "SMART_REMAKE_GEMINI_OUTPUT_TRUNCATED",
            }:
                diagnostics["causeCode"] = cause
            reason = getattr(self.client, "last_finish_reason", None)
            if isinstance(reason, str) and reason in {"STOP", "MAX_TOKENS"}:
                diagnostics["providerFinishReason"] = reason
            # Exception text can contain prompts, API keys or provider URLs.
            await unknown_attempt(
                self.session,
                self.workspace_id,
                self.project_id,
                attempt_id,
                error={
                    "code": "MODEL_ATTEMPT_UNCERTAIN", "exceptionType": type(exc).__name__,
                    **diagnostics,
                },
                receipt=error_receipt,
                usage=getattr(self.client, "last_usage", {}),
            )
            raise AppError(
                "SMART_REMAKE_MODEL_ATTEMPT_UNCERTAIN",
                "Model response could not be retained; reconcile before retrying.",
                409,
                details=diagnostics,
            ) from exc

    async def _preflight(self, expected_binding: str) -> SmartRemakeProjectModel:
        row = await self._project()
        if _input_binding(row) != expected_binding:
            raise ConflictError(
                "SMART_REMAKE_INPUT_CHANGED", "Owned model inputs changed before submission."
            )
        await self.session.commit()
        return row


def inspection_invoke(
    session: AsyncSession,
    workspace_id: UUID,
    project_id: UUID,
    operation_id: UUID,
    actor_id: UUID | None,
    metadata: dict[str, Any] | None = None,
) -> Callable[[dict[str, Any]], Awaitable[Any]]:
    client = LedgerGeminiClient(
        session,
        workspace_id,
        project_id,
        operation_id,
        actor_id,
        purpose="recheck",
        stage="inspection",
        metadata=metadata,
    )

    async def invoke(payload: dict[str, Any]) -> Any:
        system = payload.get("system_instruction", payload.get("systemInstruction"))
        prompt, media = payload.get("prompt"), payload.get("media")
        if not isinstance(system, str) or not isinstance(prompt, str) or not prompt.strip():
            raise AppError(
                "SMART_REMAKE_INSPECTION_MODEL_INPUT_INVALID", "Inspector prompt is required."
            )
        if media is not None and (
            not isinstance(media, list) or any(not isinstance(x, dict) for x in media)
        ):
            raise AppError(
                "SMART_REMAKE_MODEL_MEDIA_INVALID", "Inspector media must be owned byte inputs."
            )
        return await client.generate_json(system_instruction=system, prompt=prompt, media=media)

    invoke.model_profile = {"provider": "google", "model": get_gemini_model(), **PROFILE}  # type: ignore[attr-defined]
    return invoke
