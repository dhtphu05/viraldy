"""Owned approval, private checked export, restore, deletion and evidence actions."""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Callable
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from viraldy.modules.jobs.models import ProcessingJobModel
from viraldy.shared.errors.base import AppError, ConflictError

from .assembly_snapshots import (
    active_assembly,
    assembly_expectations,
    assembly_manifest,
    content_hash,
    restore_assembly,
)
from .budget_ledger import budget_summary, list_attempts, usd_amount
from .budget_models import SmartRemakeAttemptModel
from .export_media import LABEL, POLICY_VERSION, export_labeled_media
from .generation_expectations import expectations_hash
from .models import SmartRemakeOperationModel, SmartRemakeProjectModel
from .project_contracts import SmartRemakeMutation
from .project_deletion import delete_inventory, deletion_inventory, suspend_project
from .project_policy import assert_project_policy, constraints_hash, policy_hash
from .project_presentation import without_storage_keys
from .provider_execution import (
    classify_run_execution,
    safe_provider_identifier,
    validated_execution_evidence,
)
from .release_policy import create_approval, validate_export_approval
from .repair_media import now_iso


class ApprovalRequest(SmartRemakeMutation):
    assemblyId: str = Field(min_length=1, max_length=200)
    reportId: str = Field(min_length=1, max_length=200)


class ExportRequest(SmartRemakeMutation):
    assemblyId: str = Field(min_length=1, max_length=200)
    approvalId: str = Field(min_length=1, max_length=200)


class RestoreRequest(SmartRemakeMutation):
    assemblyId: str = Field(min_length=1, max_length=200)


class DeletionRequest(SmartRemakeMutation):
    reason: str = Field(min_length=1, max_length=4000)


def _revision(row: Any, expected: int) -> None:
    if row.state_json["revision"] != expected:
        raise ConflictError("SMART_REMAKE_REVISION_CONFLICT", "Refresh this project's revision.")


def _replay(operation: Any, field: str) -> dict[str, Any]:
    if operation.status != "completed":
        raise AppError(
            operation.result_json.get("errorCode", "SMART_REMAKE_OPERATION_IN_PROGRESS"),
            "This operation has not completed. Refresh its status.",
            409,
        )
    return copy.deepcopy(operation.result_json[field])


def _payload(kind: str, actor_id: UUID, request: SmartRemakeMutation) -> dict[str, Any]:
    return {"kind": kind, "actorId": str(actor_id), **request.model_dump(mode="json")}


def _binding(row: Any) -> dict[str, Any]:
    assert_project_policy(row, purpose="export")
    return {
        "constraints_hash": constraints_hash(row.context_json),
        "policy_hash": policy_hash(row.context_json),
        "rights_valid": True,
        "current_manifest_hash": content_hash(
            assembly_manifest(row.state_json["draftTimeline"], row.state_json)
        ),
    }


def _scene_evidence(state: dict[str, Any]) -> list[dict[str, Any]]:
    scenes = []
    for scene in state.get("scenes", []):
        versions = []
        for version in scene.get("versions", []):
            evidence = {
                key: copy.deepcopy(version.get(key))
                for key in (
                    "id",
                    "parentVersionId",
                    "mediaHash",
                    "technicalCheck",
                    "createdAt",
                    "renderGroupId",
                    "operationId",
                    "source",
                    "usedByRevision",
                    "promptHash",
                    "expectationsHash",
                )
            }
            metadata = version.get("providerMetadata") or {}
            evidence.update(
                {
                    key: metadata.get(key)
                    for key in (
                        "provider",
                        "model",
                        "modelVersion",
                        "promptVersion",
                        "requestHash",
                        "providerRequestId",
                    )
                }
            )
            evidence["providerRequestId"] = (
                metadata.get("providerRequestId")
                if safe_provider_identifier(metadata.get("providerRequestId"))
                else None
            )
            if not evidence["promptHash"] and any(
                version.get(key) for key in ("prompt", "imagePrompt", "videoPrompt")
            ):
                evidence["promptHash"] = content_hash(
                    {key: version.get(key) for key in ("prompt", "imagePrompt", "videoPrompt")}
                )
            versions.append(evidence)
        scenes.append(
            {
                "id": scene["id"],
                "activeVersionId": scene.get("activeVersionId"),
                "versions": versions,
            }
        )
    return scenes


def _plan_evidence(state: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    compiled, plan = (
        context.get("compileResult") or {},
        state.get("renderPlan") or context.get("renderPlan") or {},
    )
    return {
        "sourceSceneMap": copy.deepcopy(state.get("sourceSceneMap")),
        "renderPlan": copy.deepcopy(plan),
        "mode": compiled.get("mode") or (context.get("sceneMap") or {}).get("mode"),
        "executionMode": compiled.get("executionMode") or context.get("executionMode"),
        "promptVersion": compiled.get("promptVersion") or plan.get("promptVersion"),
        "modelVersions": {
            "video": plan.get("videoModel"),
            "image": plan.get("imageModel"),
            "analyzer": compiled.get("analyzerModel"),
            "compiler": compiled.get("compilerModel"),
        },
    }


def _public_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    result = {
        key: receipt[key]
        for key in ("requestId", "taskId")
        if safe_provider_identifier(receipt.get(key))
    }
    if "requestId" not in result and safe_provider_identifier(receipt.get("providerRequestId")):
        result["requestId"] = receipt["providerRequestId"]
    for key in ("costUsd", "actualUsd", "billedUsd"):
        value = receipt.get(key)
        if type(value) not in (str, int, float) or len(str(value)) > 64:
            continue
        try:
            result[key] = str(usd_amount(str(value)))
        except AppError:
            continue
    return result


class ProjectLifecycleService:
    def __init__(
        self, repair: Any, *, export_encoder: Callable[..., Any] = export_labeled_media
    ) -> None:
        self.repair = repair
        self.repository, self.media = repair.repository, repair.media
        self.workspace_id = repair.workspace_id
        self.export_encoder = export_encoder

    async def _envelope(
        self, project_id: UUID, operation: Any, extra: dict[str, Any]
    ) -> dict[str, Any]:
        row = await self.repository.project(self.workspace_id, project_id)
        return {
            "project": await self.repair.present(row),
            "operationId": str(operation.id),
            "status": operation.status,
            **without_storage_keys(extra),
        }

    async def _start(
        self, project_id: UUID, actor_id: UUID, request: SmartRemakeMutation, kind: str
    ) -> tuple[Any, Any, bool, dict[str, Any]]:
        payload = _payload(kind, actor_id, request)
        row, operation, fresh = await self.repository.start(
            self.workspace_id, project_id, request.idempotencyKey, content_hash(payload)
        )
        return row, operation, fresh, payload

    async def _failed(self, operation: Any, payload: dict[str, Any], exc: Exception) -> None:
        await self.repository.finish(
            operation,
            "failed",
            {
                **payload,
                "errorCode": exc.code
                if isinstance(exc, AppError)
                else "SMART_REMAKE_ACTION_FAILED",
            },
        )

    async def approve(
        self, project_id: UUID, actor_id: UUID, request: ApprovalRequest
    ) -> dict[str, Any]:
        _, operation, fresh, payload = await self._start(project_id, actor_id, request, "approval")
        if not fresh:
            return await self._envelope(
                project_id, operation, {"approval": _replay(operation, "approval")}
            )
        try:
            row = await self.repository.project(self.workspace_id, project_id, lock=True)
            _revision(row, request.expectedRevision)
            context = copy.deepcopy(row.context_json)
            context["p0"] = create_approval(
                context["p0"],
                assembly_id=request.assemblyId,
                report_id=request.reportId,
                actor_id=str(actor_id),
                **_binding(row),
            )
            approval = context["p0"]["release"]["approvals"][-1]
            row.context_json = context
            state = copy.deepcopy(row.state_json)
            state["revision"] += 1
            await self.repository.complete(row, state, operation, {**payload, "approval": approval})
        except Exception as exc:
            await self._failed(operation, payload, exc)
            raise
        return await self._envelope(project_id, operation, {"approval": approval})

    async def _signed_export(
        self, row: Any, request: ExportRequest, exported: dict[str, Any], operation: Any
    ) -> dict[str, Any]:
        row = await self.repository.project(self.workspace_id, row.id, lock=True)
        validate_export_approval(
            row.context_json["p0"],
            assembly_id=request.assemblyId,
            approval_id=request.approvalId,
            **_binding(row),
        )
        data = await self.media.read(exported["storageKey"])
        if hashlib.sha256(data).hexdigest() != exported["exportMediaHash"]:
            raise AppError("SMART_REMAKE_EXPORT_CHANGED", "The checked export bytes changed.", 409)
        result = without_storage_keys(exported)
        result["downloadUrl"] = await self.media.download_url(
            exported["storageKey"], f"smart-remake-{row.id}-ai.mp4"
        )
        result["mediaHash"] = exported["exportMediaHash"]
        return await self._envelope(row.id, operation, result)

    async def export(
        self, project_id: UUID, actor_id: UUID, request: ExportRequest
    ) -> dict[str, Any]:
        _, operation, fresh, payload = await self._start(project_id, actor_id, request, "export")
        if not fresh and operation.status == "completed":
            row = await self.repository.project(self.workspace_id, project_id)
            return await self._signed_export(row, request, _replay(operation, "export"), operation)
        if not fresh and operation.status != "running":
            return _replay(operation, "export")
        async with self.repository.execution_guard(operation.id) as acquired:
            if not acquired:
                raise ConflictError(
                    "SMART_REMAKE_OPERATION_IN_PROGRESS", "This export is still running."
                )
            key = None
            try:
                row = await self.repository.project(self.workspace_id, project_id)
                _revision(row, request.expectedRevision)
                binding = _binding(row)
                assembly, _ = validate_export_approval(
                    row.context_json["p0"],
                    assembly_id=request.assemblyId,
                    approval_id=request.approvalId,
                    **binding,
                )
                await self.repository.finish(operation, "running", {**payload, "phase": "encoding"})
                data = await self.media.read(assembly["storageKey"])
                if hashlib.sha256(data).hexdigest() != assembly["mediaHash"]:
                    raise AppError(
                        "SMART_REMAKE_MEDIA_CHANGED", "The reviewed media bytes changed.", 409
                    )
                output, check = await run_in_threadpool(
                    self.export_encoder,
                    data,
                    expected_frames=assembly["timeline"]["totalFrames"],
                    audio_required=row.context_json.get("audioRequired", False),
                )
                digest = hashlib.sha256(output).hexdigest()
                if (
                    check.get("status") != "passed"
                    or check.get("mediaHash") != digest
                    or check.get("frameCount") != assembly["timeline"]["totalFrames"]
                    or check.get("fps") != 24
                    or check.get("label") != LABEL
                    or check.get("policyVersion") != POLICY_VERSION
                    or check.get("labelVerification", {}).get("verified") is not True
                ):
                    raise AppError(
                        "SMART_REMAKE_EXPORT_CHECK_FAILED", "The AI-labeled export failed checks."
                    )
                key = await self.media.put(
                    f"workspaces/{self.workspace_id}/smart-remake/{project_id}/exports",
                    output,
                    "video/mp4",
                )
                row = await self.repository.project(self.workspace_id, project_id, lock=True)
                _revision(row, request.expectedRevision)
                validate_export_approval(
                    row.context_json["p0"],
                    assembly_id=request.assemblyId,
                    approval_id=request.approvalId,
                    **_binding(row),
                )
                exported = {
                    "id": str(uuid4()),
                    "schemaVersion": 1,
                    "assemblyId": request.assemblyId,
                    "approvalId": request.approvalId,
                    "sourceMediaHash": assembly["mediaHash"],
                    "exportMediaHash": digest,
                    "manifestHash": binding["current_manifest_hash"],
                    "constraintsHash": binding["constraints_hash"],
                    "policyHash": binding["policy_hash"],
                    "storageKey": key,
                    "labelPolicyVersion": POLICY_VERSION,
                    "technicalCheck": check,
                    "actorId": str(actor_id),
                    "exportedAt": now_iso(),
                    "operationId": str(operation.id),
                }
                context, state = copy.deepcopy(row.context_json), copy.deepcopy(row.state_json)
                context["p0"]["release"].setdefault("exports", []).append(exported)
                row.context_json = context
                state["revision"] += 1
                await self.repository.complete(
                    row, state, operation, {**payload, "export": exported}
                )
                key = None  # The successful private object now belongs to immutable export history.
            except Exception as exc:
                if key:
                    try:
                        await run_in_threadpool(self.media.storage.delete_object, key)
                    except Exception:
                        # Preserve the key for the project's authorized deletion inventory.
                        row = await self.repository.project(
                            self.workspace_id, project_id, lock=True
                        )
                        context = copy.deepcopy(row.context_json)
                        context["p0"].setdefault("retainedMediaKeys", []).append(key)
                        row.context_json = context
                        await self.repository.save(row, copy.deepcopy(row.state_json))
                await self._failed(operation, payload, exc)
                raise
        return await self._signed_export(row, request, exported, operation)

    async def restore(
        self, project_id: UUID, actor_id: UUID, request: RestoreRequest
    ) -> dict[str, Any]:
        _, operation, fresh, payload = await self._start(project_id, actor_id, request, "restore")
        if not fresh:
            return await self._envelope(project_id, operation, _replay(operation, "restore"))
        try:
            row = await self.repository.project(self.workspace_id, project_id, lock=True)
            _revision(row, request.expectedRevision)
            assert_project_policy(row, purpose="export")
            context, state = copy.deepcopy(row.context_json), copy.deepcopy(row.state_json)
            context["p0"] = restore_assembly(
                context["p0"],
                assembly_id=request.assemblyId,
                actor_id=str(actor_id),
                revision=state["revision"] + 1,
                operation_id=str(operation.id),
            )
            restored = active_assembly(context["p0"])
            retained = await self.media.read(restored["storageKey"])
            if hashlib.sha256(retained).hexdigest() != restored["mediaHash"]:
                raise AppError(
                    "SMART_REMAKE_MEDIA_CHANGED", "The retained assembly bytes changed.", 409
                )
            if not restored.get("stateSnapshot", {}).get("scenes"):
                raise AppError(
                    "SMART_REMAKE_RESTORE_UNAVAILABLE",
                    "This assembly lacks retained scene history.",
                )
            state.update(copy.deepcopy(restored["stateSnapshot"]))
            context.update(copy.deepcopy(restored.get("contextSnapshot", {})))
            current = context["p0"]["assemblies"]["records"][-1]
            expectations = assembly_expectations(
                restored["timeline"], state, context, historical=True
            )
            current.update(
                generationExpectations=expectations,
                expectationsHash=expectations_hash(expectations),
            )
            context["expectationsStale"] = (context.get("generationExpectations") or {}).get(
                "requirementsHash"
            ) != expectations_hash(context["p0"]["requirements"])
            context["p0"]["constraintsHash"] = constraints_hash(context)
            current.update(
                sourceConstraintsHash=restored["constraintsHash"],
                sourceContextHash=restored["contextHash"],
                constraintsHash=constraints_hash(context),
                contextHash=content_hash(
                    {
                        "constraintsHash": constraints_hash(context),
                        "manifestHash": restored["manifestHash"],
                        "policyHash": policy_hash(context),
                    }
                ),
            )
            state.update(
                draftTimeline=copy.deepcopy(restored["timeline"]),
                publishedTimeline=copy.deepcopy(restored["timeline"]),
                finalStorageKey=restored["storageKey"],
                assemblyCheck=copy.deepcopy(restored["technicalCheck"]),
                status="ready",
                revision=state["revision"] + 1,
            )
            row.context_json = context
            result = {"assembly": current, "revision": state["revision"]}
            await self.repository.complete(row, state, operation, {**payload, "restore": result})
        except Exception as exc:
            await self._failed(operation, payload, exc)
            raise
        return await self._envelope(project_id, operation, result)

    async def _deletion_start(
        self, project_id: UUID, actor_id: UUID, request: DeletionRequest
    ) -> tuple[Any, Any, bool, dict[str, Any]]:
        payload = _payload("deletion", actor_id, request)
        row = await self.repository.project(self.workspace_id, project_id, lock=True)
        session = self.repository.session
        existing = (
            await session.execute(
                select(SmartRemakeOperationModel).where(
                    SmartRemakeOperationModel.project_id == project_id,
                    SmartRemakeOperationModel.idempotency_key == request.idempotencyKey,
                )
            )
        ).scalar_one_or_none()
        if existing:
            if existing.request_hash != content_hash(payload):
                raise ConflictError(
                    "SMART_REMAKE_IDEMPOTENCY_CONFLICT", "This key belongs to another request."
                )
            await session.commit()
            return row, existing, False, payload
        _revision(row, request.expectedRevision)
        operation = SmartRemakeOperationModel(
            id=uuid4(),
            project_id=project_id,
            idempotency_key=request.idempotencyKey,
            request_hash=content_hash(payload),
            status="running",
            result_json={**payload, "phase": "suspended"},
        )
        session.add(operation)
        context, state = copy.deepcopy(row.context_json), copy.deepcopy(row.state_json)
        context["p0"] = suspend_project(
            context["p0"], actor_id=str(actor_id), reason=request.reason
        )
        row.context_json = context
        state.update(status="suspended", revision=state["revision"] + 1)
        await self.repository.save(
            row, state
        )  # Commit stop-use before examining jobs or deleting bytes.
        return row, operation, True, payload

    async def _deletion_dependencies(self, row: Any, operation: Any) -> tuple[set[str], bool]:
        session = self.repository.session
        other_projects = (
            (
                await session.execute(
                    select(SmartRemakeProjectModel).where(SmartRemakeProjectModel.id != row.id)
                )
            )
            .scalars()
            .all()
        )
        prefix = f"workspaces/{self.workspace_id}/smart-remake/{row.id}/"
        shared = {
            item["storageKey"]
            for other in other_projects
            for item in deletion_inventory(
                other.state_json, other.context_json, owned_prefix=prefix
            )
            if item.get("storageKey")
        }
        running = (
            await session.execute(
                select(SmartRemakeOperationModel.id)
                .where(
                    SmartRemakeOperationModel.project_id == row.id,
                    SmartRemakeOperationModel.id != operation.id,
                    SmartRemakeOperationModel.status == "running",
                )
                .limit(1)
            )
        ).first()
        jobs = (
            await session.execute(
                select(ProcessingJobModel.id)
                .where(
                    ProcessingJobModel.subject_id == row.id,
                    ProcessingJobModel.status.notin_(
                        ("completed", "succeeded", "failed", "cancelled")
                    ),
                )
                .limit(1)
            )
        ).first()
        pending = (
            await session.execute(
                select(SmartRemakeAttemptModel.id)
                .where(
                    SmartRemakeAttemptModel.project_id == row.id,
                    SmartRemakeAttemptModel.status.notin_(("completed", "failed")),
                )
                .limit(1)
            )
        ).first()
        await session.commit()
        return shared, bool(running or jobs or pending)

    async def delete(
        self, project_id: UUID, actor_id: UUID, request: DeletionRequest
    ) -> dict[str, Any]:
        row, operation, fresh, payload = await self._deletion_start(project_id, actor_id, request)
        if not fresh and operation.status == "completed":
            return await self._envelope(
                project_id, operation, {"deletion": _replay(operation, "deletion")}
            )
        async with self.repository.execution_guard(operation.id) as acquired:
            if not acquired:
                raise ConflictError(
                    "SMART_REMAKE_OPERATION_IN_PROGRESS", "Deletion is still running."
                )
            try:
                shared, running = await self._deletion_dependencies(row, operation)
                prefix = f"workspaces/{self.workspace_id}/smart-remake/{project_id}/"
                inventory = deletion_inventory(
                    row.state_json, row.context_json, owned_prefix=prefix
                )
                result = await delete_inventory(
                    self.media.storage,
                    inventory,
                    owned_prefix=prefix,
                    suspended=row.context_json["p0"].get("status") == "suspended",
                    shared_keys=shared,
                    running_jobs=running,
                    retention_required=row.context_json["p0"].get("evidenceRetentionRequired")
                    is True,
                )
                row = await self.repository.project(self.workspace_id, project_id, lock=True)
                context, state = copy.deepcopy(row.context_json), copy.deepcopy(row.state_json)
                context["p0"]["deletion"].update(result, operationId=str(operation.id))
                row.context_json = context
                state.update(
                    status="deleted" if result["status"] == "completed" else "suspended",
                    revision=state["revision"] + 1,
                )
                result["revision"] = state["revision"]
                await self.repository.complete(
                    row, state, operation, {**payload, "deletion": result}
                )
            except Exception as exc:
                await self._failed(operation, payload, exc)
                raise
        return await self._envelope(project_id, operation, {"deletion": result})

    async def provenance(self, project_id: UUID) -> dict[str, Any]:
        row = await self.repository.project(self.workspace_id, project_id)
        p0, state, context = row.context_json.get("p0", {}), row.state_json, row.context_json
        attempts = await list_attempts(self.repository.session, self.workspace_id, project_id)
        budget = await budget_summary(self.repository.session, self.workspace_id, project_id)
        execution = classify_run_execution(attempts, runtime=p0.get("runtime", {}))
        safe_attempts: list[dict[str, Any]] = []
        for attempt in attempts:
            safe: dict[str, Any] = {
                key: copy.deepcopy(attempt.get(key))
                for key in (
                    "id",
                    "stage",
                    "purpose",
                    "status",
                    "provider",
                    "model",
                    "providerTaskId",
                    "requestHash",
                    "estimatedUsd",
                    "actualUsd",
                    "reservedUsd",
                    "costStatus",
                    "createdAt",
                    "submittedAt",
                    "completedAt",
                )
            }
            metadata, profile = attempt.get("metadata") or {}, attempt.get("profile") or {}
            execution_evidence = validated_execution_evidence(attempt)
            safe.update(
                stageMode=execution_evidence["mode"] if execution_evidence else None,
                modelVersion=profile.get("modelVersion") or metadata.get("modelVersion"),
                promptVersion=metadata.get("promptVersion") or profile.get("promptVersion"),
            )
            safe["profile"] = {
                key: copy.deepcopy(profile[key])
                for key in (
                    "model",
                    "modelVersion",
                    "size",
                    "quality",
                    "complexity",
                    "temperature",
                    "maxOutputTokens",
                    "responseMimeType",
                    "maxAttempts",
                    "repairJson",
                    "resolution",
                    "duration",
                    "aspect_ratio",
                )
                if key in profile
            }
            safe["usage"] = {
                key: value
                for key, value in attempt.get("usage", {}).items()
                if key in {"inputTokens", "outputTokens", "totalTokens", "images", "seconds"}
                and type(value) in (int, float)
            }
            safe["providerTaskId"] = (
                attempt.get("providerTaskId")
                if safe_provider_identifier(attempt.get("providerTaskId"))
                else None
            )
            safe["receipt"] = _public_receipt(attempt.get("receipt") or {})
            if execution_evidence:
                safe["receipt"]["executionEvidence"] = execution_evidence
            safe["error"] = {"code": attempt.get("error", {}).get("code")}
            safe_attempts.append(safe)
        assemblies = p0.get("assemblies", {})
        records = [
            {
                key: copy.deepcopy(record.get(key))
                for key in (
                    "id",
                    "parentAssemblyId",
                    "restoredFromAssemblyId",
                    "mediaHash",
                    "manifestHash",
                    "constraintsHash",
                    "contextHash",
                    "expectationsHash",
                    "timeline",
                    "manifest",
                    "technicalCheck",
                    "actorId",
                    "revision",
                    "createdAt",
                    "operationId",
                )
            }
            for record in assemblies.get("records", [])
        ]
        result: dict[str, Any] = without_storage_keys(
            {
                "schemaVersion": "smart_remake_provenance_v1",
                "project": {
                    "id": str(row.id),
                    "workspaceId": str(row.workspace_id),
                    "revision": row.revision,
                    "status": state.get("status"),
                },
                "run": {
                    **{
                        key: p0.get(key)
                        for key in (
                            "caseId",
                            "runId",
                            "variant",
                            "configVersion",
                            "codeVersion",
                            "promptVersion",
                        )
                    },
                    "serverMode": p0.get("runtime", {}).get("serverMode"),
                    **execution,
                },
                "inputs": [
                    {
                        "role": role,
                        "assetId": asset.get("id"),
                        "mediaHash": asset.get("mediaHash"),
                        "mimeType": asset.get("mimeType"),
                        "rights": p0.get("rights", {}).get(role),
                    }
                    for role, asset in p0.get("assets", {}).items()
                ],
                "requirements": p0.get("requirements"),
                "constraintsHash": constraints_hash(context),
                "expectationsHash": context.get("expectationsHash"),
                "expectationsVersion": (context.get("generationExpectations") or {}).get(
                    "schemaVersion"
                ),
                "policyHash": policy_hash(context),
                "plan": _plan_evidence(state, context),
                "planHistory": [
                    {
                        "id": prior.get("id"),
                        "retiredAt": prior.get("retiredAt"),
                        "revision": prior.get("revision"),
                        "plan": _plan_evidence(
                            prior.get("stateSnapshot", {}), prior.get("contextSnapshot", {})
                        ),
                        "scenes": _scene_evidence(prior.get("stateSnapshot", {})),
                        "timeline": copy.deepcopy(
                            prior.get("stateSnapshot", {}).get("draftTimeline")
                        ),
                    }
                    for prior in p0.get("planHistory", [])
                ],
                "attempts": safe_attempts,
                "stageTimings": [
                    {
                        "attemptId": attempt["id"],
                        "stage": attempt["stage"],
                        "createdAt": attempt["createdAt"],
                        "submittedAt": attempt["submittedAt"],
                        "completedAt": attempt["completedAt"],
                    }
                    for attempt in safe_attempts
                ],
                "failures": [
                    {
                        "attemptId": attempt["id"],
                        "stage": attempt["stage"],
                        "status": attempt["status"],
                        "code": attempt["error"]["code"],
                    }
                    for attempt in safe_attempts
                    if attempt["status"] in {"failed", "unknown"}
                ],
                "budget": budget,
                "scenes": _scene_evidence(state),
                "timeline": state.get("draftTimeline"),
                "assemblies": {
                    "activeAssemblyId": assemblies.get("activeAssemblyId"),
                    "records": records,
                    "history": assemblies.get("history", []),
                },
                "inspections": p0.get("inspections", {}),
                "release": p0.get("release", {}),
                "deletion": p0.get("deletion"),
            }
        )
        return result
