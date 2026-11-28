"""Owned inspection operations: immutable context, durable submission and human review."""

from __future__ import annotations

import copy
import hashlib
import importlib
from collections.abc import Awaitable, Callable
from typing import Any, Literal, cast
from uuid import UUID, uuid4

from pydantic import Field, model_validator
from starlette.concurrency import run_in_threadpool

from viraldy.shared.errors.base import AppError, ConflictError

from .assembly_snapshots import (
    assembly_expectations,
    content_hash,
    get_assembly,
    retained_expectations,
)
from .generation_expectations import (
    expectations_hash,
    require_generation_expectations,
    validate_generation_expectations,
)
from .product_references import product_reference_assets
from .project_contracts import SmartRemakeApiModel, SmartRemakeMutation
from .project_policy import assert_project_policy, constraints_hash, policy_hash
from .repair_media import now_iso
from .timeline_media import probe_timeline_media

STATUSES = {"passed", "failed", "needs_review", "insufficient_evidence"}
HARD_CATEGORIES = {"technical", "rights", "consent", "policy"}


class InspectionSubjectRequest(SmartRemakeApiModel):
    kind: Literal["image", "scene", "assembly"]
    sceneId: str | None = Field(default=None, min_length=1, max_length=200)
    versionId: str | None = Field(default=None, min_length=1, max_length=200)
    assemblyId: str | None = Field(default=None, min_length=1, max_length=200)
    imageRole: Literal["product", "character"] | None = None

    @model_validator(mode="after")
    def matching_identity(self) -> InspectionSubjectRequest:
        supplied = {
            name
            for name in ("sceneId", "versionId", "assemblyId", "imageRole")
            if getattr(self, name) is not None
        }
        required = {
            "scene": {"sceneId", "versionId"},
            "assembly": {"assemblyId"},
            "image": {"imageRole"},
        }[self.kind]
        if supplied != required:
            raise ValueError("The subject identity must match its kind.")
        return self


class InspectionRequest(SmartRemakeMutation):
    subject: InspectionSubjectRequest = Field(
        examples=[{"kind": "assembly", "assemblyId": "example-assembly"}]
    )


class InspectionReviewRequest(SmartRemakeMutation):
    reportId: str = Field(min_length=1, max_length=200)
    findingId: str = Field(min_length=1, max_length=200)
    decision: Literal["accept", "reject"]
    reason: str = Field(min_length=1, max_length=4000)


def _error(code: str, message: str, status: int = 409) -> AppError:
    return AppError(f"SMART_REMAKE_INSPECTION_{code}", message, status)


def _revision(row: Any, expected: int) -> None:
    if row.state_json["revision"] != expected:
        raise ConflictError("SMART_REMAKE_REVISION_CONFLICT", "Refresh this project's revision.")


def _owned(workspace_id: UUID, value: dict[str, Any]) -> dict[str, Any]:
    key, media_hash = value.get("storageKey"), value.get("mediaHash")
    if not isinstance(key, str) or not key.startswith(f"workspaces/{workspace_id}/smart-remake/"):
        raise _error("MEDIA_FORBIDDEN", "Inspection media must belong to this workspace.", 403)
    if not isinstance(media_hash, str) or len(media_hash) != 64:
        raise _error("MEDIA_CHANGED", "Inspection media needs a retained content hash.")
    return copy.deepcopy(value)


def _snapshot(row: Any, request: InspectionSubjectRequest, workspace_id: UUID) -> dict[str, Any]:
    assert_project_policy(row, purpose="inspection")
    state, p0 = row.state_json, row.context_json["p0"]
    subject: dict[str, Any] = {"kind": request.kind, "projectId": str(row.id)}
    timeline = state.get("draftTimeline") or {}
    source_scene_map = state.get("sourceSceneMap")
    neighbor_assets: dict[str, dict[str, Any]] = {}
    expectations: dict[str, Any] | None = None
    if request.kind == "scene":
        scene = next((s for s in state.get("scenes", []) if s["id"] == request.sceneId), None)
        version = next(
            (v for v in (scene or {}).get("versions", []) if v["id"] == request.versionId), None
        )
        if version is None:
            raise _error("SUBJECT_NOT_FOUND", "This retained scene version was not found.", 404)
        retained = _owned(workspace_id, version)
        expectations = retained_expectations(version)
        items = timeline.get("items", [])
        index = next(
            (i for i, item in enumerate(items) if item.get("renderUnitId") == request.sceneId), None
        )
        selection = (
            copy.deepcopy(items[index])
            if index is not None
            else {"inFrame": 0, "outFrame": retained.get("frameCount", 192)}
        )
        # Candidate inspection uses its proposed range, never an unrelated active version.
        if selection.get("versionId") != request.versionId:
            selection.update(
                versionId=request.versionId,
                inFrame=retained.get("suggestedInFrame", 0),
                outFrame=retained.get("suggestedOutFrame", retained.get("frameCount", 192)),
            )
        neighbors = (
            [
                item.get("versionId")
                for item in items[max(0, index - 1) : index + 2]
                if item.get("renderUnitId") != request.sceneId
            ]
            if index is not None
            else []
        )
        selection.pop("reviewed", None)
        local_items = (
            copy.deepcopy(items[max(0, index - 1) : index + 2]) if index is not None else []
        )
        for item in local_items:
            item.pop("reviewed", None)
            if item.get("renderUnitId") == request.sceneId:
                continue
            adjacent: dict[str, Any] = next(
                (s for s in state.get("scenes", []) if s["id"] == item.get("renderUnitId")), {}
            )
            neighbor = next(
                (v for v in adjacent.get("versions", []) if v["id"] == item.get("versionId")), None
            )
            if neighbor:
                identity = "neighbor-" + str(item["renderUnitId"])
                neighbor_assets[identity] = {
                    **_owned(workspace_id, neighbor),
                    "role": "neighbor",
                    "versionId": item["versionId"],
                    "mimeType": "video/mp4",
                    "range": {
                        "inFrame": item["inFrame"],
                        "outFrame": item["outFrame"],
                        "fps": 24,
                        "timebase": "raw_group",
                    },
                }
        timeline = {**timeline, "items": local_items}
        subject.update(
            sceneId=request.sceneId,
            versionId=request.versionId,
            range={
                "inFrame": selection["inFrame"],
                "outFrame": selection["outFrame"],
                "fps": 24,
                "timebase": "raw_group",
            },
            neighborVersionIds=neighbors,
        )
        manifest = {
            "selection": selection,
            "neighbors": neighbors,
            "renderPlan": state.get("renderPlan"),
        }
        manifest_hash = content_hash(manifest)
    elif request.kind == "assembly":
        assembly = get_assembly(p0, request.assemblyId)
        retained = _owned(workspace_id, assembly)
        manifest = assembly["manifest"]
        manifest_hash = content_hash(manifest)
        if manifest_hash != assembly.get("manifestHash"):
            raise _error("MEDIA_CHANGED", "The retained assembly manifest changed.")
        timeline = assembly["timeline"]
        source_scene_map = assembly.get("stateSnapshot", {}).get(
            "sourceSceneMap",
            assembly.get("contextSnapshot", {}).get("sourceSceneMap", source_scene_map),
        )
        expectations = retained_expectations(assembly)
        if expectations is not None and assembly.get("constraintsHash") != constraints_hash(
            row.context_json
        ):
            raise AppError(
                "SMART_REMAKE_ASSEMBLY_EXPECTATIONS_REQUIRED",
                "The scene/product facts changed. Assemble or restore a new preview first.",
                409,
            )
        if expectations is None:
            historical = copy.deepcopy(assembly.get("contextSnapshot") or {})
            saved_requirements = historical.get("requirementsSnapshot")
            historical_binding = retained_expectations(historical)
            saved_requirements_hash = (
                expectations_hash(saved_requirements)
                if saved_requirements is not None
                else (historical_binding or {}).get("requirementsHash")
            )
            if saved_requirements_hash != expectations_hash(p0["requirements"]):
                raise AppError(
                    "SMART_REMAKE_ASSEMBLY_EXPECTATIONS_REQUIRED",
                    "The historical requirements are missing or changed. Assemble a new preview.",
                    409,
                )
            if any(
                historical.get(f"{role}MediaHash") != p0["assets"][role]["mediaHash"]
                for role in ("source", "product")
            ):
                raise AppError(
                    "SMART_REMAKE_ASSEMBLY_EXPECTATIONS_REQUIRED",
                    "Assemble a new preview with complete retained requirements.",
                    409,
                )
            expectations = assembly_expectations(
                timeline,
                assembly.get("stateSnapshot") or {},
                {**historical, "p0": p0},
                historical=True,
            )
        subject.update(
            assemblyId=request.assemblyId,
            range={
                "inFrame": 0,
                "outFrame": timeline["totalFrames"],
                "fps": 24,
                "timebase": "final",
            },
            neighborVersionIds=[item.get("versionId") for item in timeline["items"]],
        )
    else:
        retained = _owned(workspace_id, p0.get("assets", {}).get(request.imageRole, {}))
        subject.update(imageRole=request.imageRole)
        manifest = {"imageRole": request.imageRole, "mediaHash": retained["mediaHash"]}
        manifest_hash = content_hash(manifest)
        expectations = require_generation_expectations(row.context_json)
    if expectations is None:
        raise AppError(
            "SMART_REMAKE_EXPECTATIONS_REQUIRED",
            "Update the scene plan before checking media without retained expectations.",
            409,
        )
    expectations = validate_generation_expectations(expectations)
    if request.kind == "assembly":
        selections = {
            item["renderUnitId"]: {
                "versionId": item["versionId"],
                "inFrame": item["inFrame"],
                "outFrame": item["outFrame"],
                "timebase": "raw_group",
            }
            for item in timeline["items"]
        }
        if {
            scene["renderUnitId"]: scene.get("selection") for scene in expectations["scenes"]
        } != selections:
            raise _error("MEDIA_CHANGED", "The expectations do not bind these selected ranges.")
    product_views = product_reference_assets(row.context_json)
    if (
        expectations.get(
            "productReferenceHashes", [expectations["references"]["product"]["mediaHash"]]
        )
        != [asset.get("mediaHash") for asset in product_views]
        or expectations["requirementsHash"] != expectations_hash(p0["requirements"])
        or expectations["references"]
        != {
            role: {"mediaHash": asset["mediaHash"]}
            for role, asset in p0["assets"].items()
            if role in {"source", "product", "character"}
        }
    ):
        code = (
            "SMART_REMAKE_ASSEMBLY_EXPECTATIONS_REQUIRED"
            if request.kind == "assembly"
            else "SMART_REMAKE_EXPECTATIONS_REQUIRED"
        )
        raise AppError(
            code, "The saved expectations changed. Prepare a new preview and check it.", 409
        )
    subject["mediaHash"] = retained["mediaHash"]
    assets = {role: _owned(workspace_id, asset) for role, asset in p0["assets"].items()}
    assets.update(
        {
            f"product-reference-{index + 1}": {**_owned(workspace_id, asset), "role": "product"}
            for index, asset in enumerate(product_views)
            if index > 0
        }
    )
    assets.update(neighbor_assets)
    return {
        "subject": subject,
        "media": retained,
        "references": assets,
        "constraintsHash": constraints_hash(row.context_json),
        "manifestHash": manifest_hash,
        "policyHash": policy_hash(row.context_json),
        "requirements": copy.deepcopy(expectations["requirements"]),
        "expectations": expectations,
        "expectationsHash": expectations_hash(expectations),
        "requirementsHash": expectations["requirementsHash"],
        "checkerProfile": importlib.import_module(
            ".inspection.public", package=__package__
        ).inspection_profile(),
        "timeline": copy.deepcopy(timeline),
        "sourceSceneMap": copy.deepcopy(source_scene_map),
        "manifest": copy.deepcopy(manifest),
    }


def _context_hash(snapshot: dict[str, Any]) -> str:
    return content_hash(snapshot)


def _recheck_snapshot(
    row: Any, request: InspectionSubjectRequest, workspace_id: UUID
) -> dict[str, Any]:
    try:
        return _snapshot(row, request, workspace_id)
    except AppError as exc:
        if exc.code in {
            "SMART_REMAKE_EXPECTATIONS_REQUIRED",
            "SMART_REMAKE_ASSEMBLY_EXPECTATIONS_REQUIRED",
        }:
            raise _error("STALE", "The saved requirements changed. Queue a fresh check.") from exc
        raise


def _public_inspector() -> Callable[..., Awaitable[Any]]:
    try:
        module = importlib.import_module(".inspection.public", package=__package__)
        return cast(Callable[..., Awaitable[Any]], module.inspect_subject)
    except (ImportError, AttributeError) as exc:
        raise _error("UNAVAILABLE", "The Inspector module is unavailable.", 503) from exc


def _model_adapter(invoke: Callable[..., Any]) -> Callable[..., Awaitable[Any]]:
    async def call(request: Any) -> Any:
        if not hasattr(request, "images"):
            return await invoke(request)
        payload = {
            "systemInstruction": request.systemInstruction,
            "prompt": request.prompt,
            "media": [
                {"bytes": image.data, "mimeType": image.mimeType} for image in request.images
            ],
        }
        output = await invoke(payload)
        contracts = importlib.import_module(".inspection.contracts", package=__package__)
        if isinstance(output, contracts.InspectionModelResult):
            return output
        profile = getattr(invoke, "model_profile", {"provider": "budget-wrapper"})
        return contracts.InspectionModelResult.model_validate(
            {"output": output, "modelProfile": profile}
        )

    return call


def _evidence_valid(evidence: Any, media_by_hash: dict[tuple[str, str], dict[str, Any]]) -> bool:
    if not isinstance(evidence, list) or not evidence:
        return False
    for item in evidence:
        if not isinstance(item, dict):
            return False
        media_id, media_hash = item.get("mediaId"), item.get("mediaHash")
        if not isinstance(media_id, str) or not isinstance(media_hash, str):
            return False
        identity = (media_id, media_hash)
        if identity not in media_by_hash:
            return False
        media = media_by_hash[identity]
        start, end = item.get("inFrame"), item.get("outFrame")
        if media["mimeType"].startswith("image/"):
            if start is not None or end is not None or item.get("timebase") is not None:
                return False
        elif (
            type(start) is not int
            or type(end) is not int
            or not 0 <= start < end <= media["frameCount"]
            or start < media.get("range", {}).get("inFrame", 0)
            or end > media.get("range", {}).get("outFrame", media["frameCount"])
            or item.get("timebase")
            != (
                media.get("range", {}).get("timebase")
                or ("source" if media.get("role") == "source" else "raw_group")
            )
        ):
            return False
    return True


def validate_report(
    report: Any, snapshot: dict[str, Any], media: dict[str, Any], references: list[dict[str, Any]]
) -> dict[str, Any]:
    """Validate the server context independently of model statements about binding."""
    if hasattr(report, "model_dump"):
        report = report.model_dump(mode="json", exclude_none=True)
    if not isinstance(report, dict):
        raise _error("REPORT_INVALID", "The Inspector returned an invalid report.")
    required = (
        "id",
        "schemaVersion",
        "checkedAt",
        "checkerVersion",
        "rubricVersion",
        "modelProfile",
    )
    if (
        any(not report.get(key) for key in required)
        or report.get("status") not in STATUSES
        or report.get("subject") != snapshot["subject"]
        or report.get("constraintsHash") != snapshot["constraintsHash"]
        or report.get("manifestHash") != snapshot["manifestHash"]
        or report.get("expectationsHash") != snapshot.get("expectationsHash")
        or any(
            report.get(key) != value for key, value in snapshot.get("checkerProfile", {}).items()
        )
    ):
        raise _error("REPORT_INVALID", "The Inspector report does not bind this saved context.")
    media_by_hash = {(item["id"], item["mediaHash"]): item for item in [media, *references]}
    findings, coverage = report.get("findings"), report.get("coverage")
    if not isinstance(findings, list) or not isinstance(coverage, list):
        raise _error("REPORT_INVALID", "The Inspector report has no typed findings or coverage.")
    for entry in coverage:
        if (
            not isinstance(entry, dict)
            or entry.get("status") not in STATUSES
            or not entry.get("requirementId")
            or not isinstance(entry.get("evidence"), list)
            or (entry["evidence"] and not _evidence_valid(entry["evidence"], media_by_hash))
        ):
            raise _error("REPORT_INVALID", "The Inspector coverage contains invalid evidence.")
    ids = set()
    for finding in findings:
        if (
            not isinstance(finding, dict)
            or not finding.get("id")
            or finding["id"] in ids
            or finding.get("status") not in STATUSES
            or not finding.get("requirementId")
            or not finding.get("category")
            or not finding.get("severity")
            or (
                finding.get("status") == "passed"
                and not _evidence_valid(finding.get("evidence"), media_by_hash)
            )
            or (finding.get("evidence") and not _evidence_valid(finding["evidence"], media_by_hash))
        ):
            raise _error("REPORT_INVALID", "The Inspector finding contains invalid evidence.")
        ids.add(finding["id"])
    if report["status"] == "passed":
        if (
            not coverage
            or not findings
            or any(f.get("status") != "passed" for f in findings)
            or any(
                not isinstance(c, dict)
                or c.get("status") != "passed"
                or not _evidence_valid(c.get("evidence"), media_by_hash)
                for c in coverage
            )
        ):
            raise _error(
                "REPORT_INVALID", "A passing report requires observed evidence and coverage."
            )
    return copy.deepcopy(report)


class InspectionService:
    def __init__(
        self,
        repository: Any,
        media: Any,
        workspace_id: UUID,
        *,
        settings: Any = None,
        inspector: Callable[..., Awaitable[Any]] | None = None,
        probe: Callable[[bytes], dict[str, Any]] = probe_timeline_media,
    ) -> None:
        self.repository, self.media, self.workspace_id = repository, media, workspace_id
        self.settings, self.inspector, self.probe = settings, inspector, probe

    async def queue(
        self, project_id: UUID, actor_id: UUID, request: InspectionRequest
    ) -> tuple[Any, Any, bool]:
        payload = {
            "kind": "inspection",
            "actorId": str(actor_id),
            **request.model_dump(mode="json"),
        }
        row, operation, fresh = await self.repository.start(
            self.workspace_id, project_id, request.idempotencyKey, content_hash(payload)
        )
        if not fresh:
            return row, operation, False
        try:
            _revision(row, request.expectedRevision)
            snapshot = _snapshot(row, request.subject, self.workspace_id)
            result = {
                **payload,
                "snapshot": snapshot,
                "contextHash": _context_hash(snapshot),
                "phase": "queued",
                "queuedAt": now_iso(),
            }
            await self.repository.finish(operation, "running", result)
        except AppError as exc:
            await self.repository.finish(
                operation,
                "failed",
                {**payload, "errorCode": exc.code, "errorStatus": exc.status_code},
            )
            raise
        return row, operation, True

    async def _read_media(self, value: dict[str, Any], identity: str, mime: str) -> dict[str, Any]:
        try:
            data = await self.media.read(value["storageKey"])
        except Exception as exc:
            raise _error("MEDIA_UNAVAILABLE", "Owned inspection media could not be read.") from exc
        if hashlib.sha256(data).hexdigest() != value["mediaHash"]:
            raise _error("MEDIA_CHANGED", "Owned inspection bytes no longer match their hash.")
        mime = value.get("mimeType") or mime
        result = {"id": identity, "mediaHash": value["mediaHash"], "bytes": data, "mimeType": mime}
        for key in ("role", "versionId", "range"):
            if key in value:
                result[key] = copy.deepcopy(value[key])
        if not mime.startswith("image/"):
            info = await run_in_threadpool(self.probe, data)
            result["frameCount"] = info["frameCount"]
            result["fps"] = 24
        return result

    async def execute(
        self,
        project_id: UUID,
        operation_id: UUID,
        *,
        invoke_model: Callable[..., Any] | None = None,
    ) -> dict[str, Any]:
        async with self.repository.execution_guard(operation_id) as acquired:
            operation = await self.repository.operation(self.workspace_id, project_id, operation_id)
            if not acquired or operation.status != "running":
                return copy.deepcopy(operation.result_json)
            intent = copy.deepcopy(operation.result_json)
            if intent.get("kind") != "inspection":
                raise _error("OPERATION_INVALID", "This is not an inspection operation.")
            if intent.get("phase") == "invoking":
                result = {
                    **intent,
                    "needsReconciliation": True,
                    "errorCode": "SMART_REMAKE_INSPECTION_RECONCILIATION_REQUIRED",
                }
                await self.repository.finish(operation, "running", result)
                return result
            try:
                row = await self.repository.project(self.workspace_id, project_id)
                request = InspectionSubjectRequest.model_validate(intent["subject"])
                current = _recheck_snapshot(row, request, self.workspace_id)
                if _context_hash(current) != intent["contextHash"]:
                    raise _error("STALE", "The inspection input changed. Queue a new inspection.")
                inspector = self.inspector or _public_inspector()
                media = await self._read_media(current["media"], "subject", "video/mp4")
                if current["subject"].get("range"):
                    media["range"] = current["subject"]["range"]
                references = [
                    dict(
                        await self._read_media(
                            asset, role, "video/mp4" if role == "source" else "image/png"
                        ),
                        role=asset.get("role", role),
                    )
                    for role, asset in current["references"].items()
                ]
                bounds = current["subject"].get("range")
                if bounds and bounds["outFrame"] > media["frameCount"]:
                    raise _error("MEDIA_CHANGED", "The selected range exceeds the owned media.")
                if invoke_model is None:
                    raise _error(
                        "UNAVAILABLE", "The budgeted Inspector invocation is unavailable.", 503
                    )
                constraints = {
                    key: copy.deepcopy(current[key])
                    for key in (
                        "constraintsHash",
                        "manifestHash",
                        "requirements",
                        "timeline",
                        "sourceSceneMap",
                        "manifest",
                        "expectations",
                        "expectationsHash",
                        "requirementsHash",
                    )
                }
                constraints.update(
                    fps=24,
                    frameCount=media.get("frameCount"),
                    technicalCheck=current["media"].get("technicalCheck"),
                )
                contracts = importlib.import_module(".inspection.contracts", package=__package__)
                try:
                    contracts.InspectionSubject.model_validate(current["subject"])
                    contracts.ResolvedMedia.model_validate(media)
                    for reference in references:
                        contracts.ResolvedMedia.model_validate(reference)
                    contracts.InspectionConstraints.model_validate(constraints)
                except (ValueError, TypeError) as exc:
                    raise _error(
                        "CONTEXT_INVALID", "The saved Inspector inputs are invalid."
                    ) from exc
                # Commit before remote work: no open project transaction/row lock spans the call.
                intent.update(phase="invoking", startedAt=now_iso())
                await self.repository.finish(operation, "running", intent)
                report = await inspector(
                    subject=copy.deepcopy(current["subject"]),
                    media=media,
                    references=references,
                    constraints=constraints,
                    invoke_model=_model_adapter(invoke_model),
                )
                if self.inspector is None or hasattr(report, "model_dump"):
                    validator = importlib.import_module(
                        ".inspection.validation", package=__package__
                    )
                    try:
                        report = validator.validate_report_binding(
                            report, current["subject"], media, references, constraints
                        )
                    except (ValueError, TypeError) as exc:
                        raise _error("REPORT_INVALID", "The Inspector binding is invalid.") from exc
                report = validate_report(report, current, media, references)
                row = await self.repository.project(self.workspace_id, project_id, lock=True)
                if (
                    _context_hash(_recheck_snapshot(row, request, self.workspace_id))
                    != intent["contextHash"]
                ):
                    raise _error("STALE", "The inspection input changed while checking.")
                report.update(
                    operationId=str(operation.id),
                    actorId=intent["actorId"],
                    contextHash=intent["contextHash"],
                    subjectRequest=intent["subject"],
                )
                context = copy.deepcopy(row.context_json)
                inspections = context["p0"].setdefault(
                    "inspections", {"reports": [], "reviews": []}
                )
                if any(r["id"] == report["id"] for r in inspections["reports"]):
                    raise _error("REPORT_INVALID", "The Inspector reused a report identity.")
                inspections["reports"].append(report)
                context["p0"]["inspectionSummary"] = {
                    "reportId": report["id"],
                    "status": report["status"],
                    "subject": report["subject"],
                    "checkedAt": report["checkedAt"],
                }
                row.context_json = context
                state = copy.deepcopy(row.state_json)
                state["revision"] += 1
                result = {
                    **intent,
                    "phase": "completed",
                    "reportId": report["id"],
                    "completedAt": now_iso(),
                }
                await self.repository.complete(row, state, operation, result)
                return result
            except Exception as exc:
                code = (
                    exc.code
                    if isinstance(exc, AppError)
                    else "SMART_REMAKE_INSPECTION_CHECKER_FAILED"
                )
                ambiguous = not isinstance(exc, AppError) and intent.get("phase") == "invoking"
                result = {**intent, "errorCode": code, "needsReconciliation": ambiguous}
                await self.repository.finish(
                    operation, "running" if ambiguous else "failed", result
                )
                return result

    async def review(
        self, project_id: UUID, actor_id: UUID, request: InspectionReviewRequest
    ) -> dict[str, Any]:
        payload = {
            "kind": "inspection_review",
            "actorId": str(actor_id),
            **request.model_dump(mode="json"),
        }
        row, operation, fresh = await self.repository.start(
            self.workspace_id, project_id, request.idempotencyKey, content_hash(payload)
        )
        if not fresh:
            saved = operation.result_json
            if operation.status == "failed" and saved.get("errorCode"):
                raise AppError(
                    saved["errorCode"],
                    "This inspection review was rejected.",
                    saved.get("errorStatus", 409),
                )
            return copy.deepcopy(saved.get("review", saved))
        try:
            # start() commits its lock. Reload under a new lock before copying policy;
            # revocations remain possible while the operation is being queued.
            row = await self.repository.project(self.workspace_id, project_id, lock=True)
            _revision(row, request.expectedRevision)
            assert_project_policy(row, purpose="inspection")
            context = copy.deepcopy(row.context_json)
            inspections = context["p0"].get("inspections", {})
            report = next(
                (r for r in inspections.get("reports", []) if r["id"] == request.reportId), None
            )
            if not report:
                raise _error("REPORT_NOT_FOUND", "This inspection report was not found.", 404)
            if report.get("stage") == "conditioning" or not report.get("subjectRequest"):
                raise _error(
                    "HARD_BLOCK", "Conditioning prechecks require a fresh successful check.", 403
                )
            snapshot = _recheck_snapshot(
                row,
                InspectionSubjectRequest.model_validate(report["subjectRequest"]),
                self.workspace_id,
            )
            if report["contextHash"] != _context_hash(snapshot):
                raise _error("STALE", "Recheck this changed context before reviewing findings.")
            finding = next((f for f in report["findings"] if f["id"] == request.findingId), None)
            if not finding:
                raise _error("FINDING_NOT_FOUND", "This inspection finding was not found.", 404)
            if (
                request.decision == "accept"
                and finding["status"] != "passed"
                and (
                    finding["category"] in HARD_CATEGORIES
                    or finding.get("hardBlocking") is True
                    or finding.get("severity") in {"critical", "blocker"}
                )
            ):
                raise _error("HARD_BLOCK", "Human review cannot override a hard failure.", 403)
            review = {
                "id": str(uuid4()),
                "reportId": request.reportId,
                "findingId": request.findingId,
                "decision": request.decision,
                "reason": request.reason,
                "actorId": str(actor_id),
                "reviewedAt": now_iso(),
                "contextHash": report["contextHash"],
                "operationId": str(operation.id),
            }
            inspections.setdefault("reviews", []).append(review)
            row.context_json = context
            state = copy.deepcopy(row.state_json)
            state["revision"] += 1
            await self.repository.complete(row, state, operation, {**payload, "review": review})
            return review
        except AppError as exc:
            await self.repository.finish(
                operation,
                "failed",
                {**payload, "errorCode": exc.code, "errorStatus": exc.status_code},
            )
            raise
