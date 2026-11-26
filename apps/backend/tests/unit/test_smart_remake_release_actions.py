from __future__ import annotations

import copy
import hashlib
from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from tests.smart_remake_expectations import install_expectations
from viraldy.modules.smart_remake.assembly_snapshots import active_assembly, record_assembly
from viraldy.modules.smart_remake.inspection.public import inspection_profile
from viraldy.modules.smart_remake.project_lifecycle import (
    ApprovalRequest,
    DeletionRequest,
    ExportRequest,
    ProjectLifecycleService,
    RestoreRequest,
)
from viraldy.modules.smart_remake.project_policy import constraints_hash
from viraldy.modules.smart_remake.project_presentation import (
    project_policy_fields,
    without_storage_keys,
)
from viraldy.shared.errors.base import AppError, ConflictError


class Repo:
    def __init__(self, row):
        self.row, self.operations, self.saved = row, {}, []
        self.session = SimpleNamespace()

    async def project(self, workspace, project, lock=False):
        assert workspace == self.row.workspace_id and project == self.row.id
        return self.row

    async def start(self, workspace, project, key, request_hash):
        row = await self.project(workspace, project)
        if key in self.operations:
            op = self.operations[key]
            if op.request_hash != request_hash:
                raise ConflictError("SMART_REMAKE_IDEMPOTENCY_CONFLICT", "Different request.")
            return row, op, False
        op = SimpleNamespace(
            id=uuid4(), request_hash=request_hash, status="running", result_json={}
        )
        self.operations[key] = op
        return row, op, True

    async def finish(self, operation, status, result):
        operation.status, operation.result_json = status, copy.deepcopy(result)

    async def complete(self, row, state, operation, result):
        row.state_json, row.revision = copy.deepcopy(state), state["revision"]
        await self.finish(operation, "completed", result)
        self.saved.append(copy.deepcopy(row.context_json))

    @asynccontextmanager
    async def execution_guard(self, operation_id):
        yield True


class Media:
    def __init__(self, row, data):
        self.row, self.data, self.puts, self.signed, self.deleted = row, {}, [], [], []
        self.data[f"workspaces/{row.workspace_id}/smart-remake/{row.id}/final"] = data
        self.storage = self

    async def read(self, key):
        return self.data[key]

    async def put(self, prefix, data, mime):
        key = f"{prefix}/stored-{len(self.puts)}"
        self.data[key] = data
        self.puts.append(key)
        return key

    async def url(self, key):
        return "https://example.invalid/preview"

    async def download_url(self, key, filename):
        self.signed.append(key)
        return "https://example.invalid/authorized-export"

    def delete_object(self, key):
        assert self.row.context_json["p0"]["deletion"]["status"] == "suspended"
        self.deleted.append(key)
        self.data.pop(key, None)

    def object_exists(self, key):
        return key in self.data


@pytest.fixture
def harness():
    workspace, project, actor = uuid4(), uuid4(), uuid4()
    prefix = f"workspaces/{workspace}/smart-remake/{project}"
    raw, final = b"raw", b"final"

    def digest(data):
        return hashlib.sha256(data).hexdigest()

    timeline = {
        "fps": 24,
        "totalFrames": 192,
        "items": [
            {
                "id": "item",
                "renderUnitId": "scene",
                "sourceSceneId": "source",
                "versionId": "v1",
                "targetStartFrame": 0,
                "targetDurationFrames": 192,
                "inFrame": 0,
                "outFrame": 192,
                "reviewed": True,
            }
        ],
    }
    state = {
        "id": str(project),
        "schemaVersion": 2,
        "sourceSceneMap": {"scenes": []},
        "revision": 3,
        "status": "ready",
        "scenes": [
            {
                "id": "scene",
                "versions": [{"id": "v1", "storageKey": f"{prefix}/raw", "mediaHash": digest(raw)}],
                "activeVersionId": "v1",
            }
        ],
        "draftTimeline": timeline,
        "publishedTimeline": timeline,
        "finalStorageKey": f"{prefix}/final",
    }
    declaration = {
        "basis": "owned",
        "declared": True,
        "scope": "pilot",
        "evidenceNote": "Self-authored",
    }
    context = {
        "audioRequired": False,
        "p0": {
            "inputHash": "input",
            "targetDuration": 8,
            "requirements": {"intent": "Product showcase"},
            "rights": {
                "source": declaration,
                "product": declaration,
                "providerDisclosureAcknowledged": True,
            },
            "assets": {
                role: {
                    "id": role,
                    "storageKey": f"{prefix}/{role}",
                    "mediaHash": digest(role.encode()),
                    "mimeType": "image/png" if role == "product" else "video/mp4",
                }
                for role in ("source", "product")
            },
            "budgetPolicy": {"capUsd": "10", "maxAttempts": 10, "maxDurationSeconds": 100},
        },
    }
    check = {"status": "passed", "frameCount": 192, "mediaHash": digest(final)}
    context["sourceKey"] = context["p0"]["assets"]["source"]["storageKey"]
    context["productKey"] = context["p0"]["assets"]["product"]["storageKey"]
    install_expectations(context, state=state)
    context["p0"] = record_assembly(
        context["p0"],
        project_id=str(project),
        timeline=timeline,
        state=state,
        storage_key=f"{prefix}/final",
        media_hash=digest(final),
        technical_check=check,
        constraints_hash=constraints_hash(context),
        context_hash="context",
        revision=3,
        actor_id=str(actor),
        operation_id="compose",
        context=context,
    )
    assembly = active_assembly(context["p0"])
    evidence = [{"mediaHash": digest(final), "inFrame": 0, "outFrame": 192}]
    report = {
        "id": "report",
        "subject": {
            "kind": "assembly",
            "projectId": str(project),
            "assemblyId": assembly["id"],
            "mediaHash": digest(final),
        },
        "status": "passed",
        "manifestHash": assembly["manifestHash"],
        "constraintsHash": constraints_hash(context),
        **inspection_profile(),
        "expectationsHash": assembly["expectationsHash"],
        "coverage": [{"requirementId": "product", "status": "passed", "evidence": evidence}],
        "findings": [
            {"id": "finding", "category": "product", "status": "passed", "evidence": evidence}
        ],
    }
    context["p0"]["inspections"] = {"reports": [report], "reviews": []}
    row = SimpleNamespace(
        id=project, workspace_id=workspace, state_json=state, context_json=context, revision=3
    )
    repo, media = Repo(row), Media(row, final)
    encoded = b"labeled-final"

    def encoder(data, **kwargs):
        assert data == final
        return encoded, {
            "status": "passed",
            "mediaHash": digest(encoded),
            "frameCount": 192,
            "fps": 24,
            "label": "AI-generated",
            "policyVersion": "smart-remake-ai-label-v1",
            "labelVerification": {"verified": True},
        }

    async def present(row):
        return without_storage_keys(
            {**copy.deepcopy(row.state_json), **project_policy_fields(row.context_json)}
        )

    service = ProjectLifecycleService(
        SimpleNamespace(repository=repo, media=media, workspace_id=workspace, present=present),
        export_encoder=encoder,
    )
    return SimpleNamespace(
        service=service,
        repo=repo,
        row=row,
        media=media,
        actor=actor,
        project=project,
        assembly=assembly,
        final=final,
    )


@pytest.mark.asyncio
async def test_approval_revision_actor_and_idempotency(harness):
    h = harness
    req = ApprovalRequest(
        expectedRevision=3, idempotencyKey="approve", assemblyId=h.assembly["id"], reportId="report"
    )
    result = await h.service.approve(h.project, h.actor, req)
    assert result["approval"]["actorId"] == str(h.actor)
    assert h.row.revision == 4
    assert await h.service.approve(h.project, h.actor, req) == result
    assert h.row.revision == 4
    with pytest.raises(AppError):
        await h.service.approve(h.project, uuid4(), req)
    with pytest.raises(AppError):
        await h.service.approve(
            h.project, h.actor, req.model_copy(update={"idempotencyKey": "other"})
        )


@pytest.mark.asyncio
async def test_export_private_label_and_checked_replay_then_revoked_rights(harness):
    h = harness
    approval = await h.service.approve(
        h.project,
        h.actor,
        ApprovalRequest(
            expectedRevision=3,
            idempotencyKey="approve",
            assemblyId=h.assembly["id"],
            reportId="report",
        ),
    )
    req = ExportRequest(
        expectedRevision=4,
        idempotencyKey="export",
        assemblyId=h.assembly["id"],
        approvalId=approval["approval"]["id"],
    )
    result = await h.service.export(h.project, h.actor, req)
    assert result["downloadUrl"].startswith("https://")
    assert "storageKey" not in str(result)
    assert len(h.media.puts) == 1 and len(h.media.signed) == 1
    assert await h.media.read(h.assembly["storageKey"]) == h.final
    replay = await h.service.export(h.project, h.actor, req)
    assert replay["id"] == result["id"] and len(h.media.puts) == 1
    h.row.context_json["p0"]["rights"]["product"]["revoked"] = True
    with pytest.raises(AppError):
        await h.service.export(h.project, h.actor, req)
    assert len(h.media.signed) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["bytes_changed", "trim_changed", "bad_label"])
async def test_export_checks_before_signed_url(harness, change):
    h = harness
    approval = await h.service.approve(
        h.project,
        h.actor,
        ApprovalRequest(
            expectedRevision=3,
            idempotencyKey="approve",
            assemblyId=h.assembly["id"],
            reportId="report",
        ),
    )
    if change == "bytes_changed":
        h.media.data[h.assembly["storageKey"]] = b"changed"
    elif change == "trim_changed":
        h.row.state_json["draftTimeline"]["items"][0]["inFrame"] = 1
    else:
        h.service.export_encoder = lambda *_args, **_kwargs: (b"unlabeled", {"status": "passed"})
    with pytest.raises(AppError):
        await h.service.export(
            h.project,
            h.actor,
            ExportRequest(
                expectedRevision=4,
                idempotencyKey="export",
                assemblyId=h.assembly["id"],
                approvalId=approval["approval"]["id"],
            ),
        )
    assert not h.media.signed


@pytest.mark.asyncio
async def test_restore_preserves_history_restores_metadata_and_invalidates(harness):
    h = harness
    h.row.state_json["scenes"] = [{"id": "recompiled", "versions": []}]
    result = await h.service.restore(
        h.project,
        h.actor,
        RestoreRequest(expectedRevision=3, idempotencyKey="restore", assemblyId=h.assembly["id"]),
    )
    assert h.row.state_json["scenes"][0]["id"] == "scene"
    assert h.row.state_json["draftTimeline"]["items"][0]["versionId"] == "v1"
    assert result["assembly"]["id"] != h.assembly["id"]
    assert h.row.context_json["p0"]["release"]["activeApprovalId"] is None
    assert h.row.revision == 4
    assert len(h.row.context_json["p0"]["assemblies"]["records"]) == 2


def test_strict_action_requests_reject_client_authority_fields():
    with pytest.raises(ValidationError):
        ExportRequest(
            expectedRevision=1,
            idempotencyKey="k",
            assemblyId="a",
            approvalId="b",
            downloadUrl="https://evil",
        )
    with pytest.raises(ValidationError):
        DeletionRequest(expectedRevision=1, idempotencyKey="k", reason=" ")


class Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return self

    def all(self):
        return self.value

    def first(self):
        return self.value


class Session:
    def __init__(self, repo):
        self.repo, self.others, self.jobs, self.pending = repo, [], None, None
        self.running = None
        self.commits = 0

    async def execute(self, statement):
        name = statement.column_descriptions[0]["name"]
        entity = statement.column_descriptions[0]["entity"].__name__
        if name == "SmartRemakeOperationModel":
            key = statement.compile().params["idempotency_key_1"]
            return Result(self.repo.operations.get(key))
        if name == "SmartRemakeProjectModel":
            return Result(self.others)
        if entity == "SmartRemakeOperationModel":
            return Result(self.running)
        if entity == "ProcessingJobModel":
            return Result(self.jobs)
        return Result(self.pending)

    def add(self, operation):
        self.repo.operations[operation.idempotency_key] = operation

    async def commit(self):
        self.commits += 1


@pytest.mark.asyncio
@pytest.mark.parametrize("pending", ["running", "jobs", "pending"])
async def test_deletion_immediately_stops_use_while_any_remote_work_pending(harness, pending):
    h = harness
    session = Session(h.repo)
    setattr(session, pending, (uuid4(),))
    h.repo.session = session

    async def save(row, state):
        row.state_json, row.revision = copy.deepcopy(state), state["revision"]
        h.repo.saved.append(copy.deepcopy(row.context_json))
        await session.commit()

    h.repo.save = save
    req = DeletionRequest(expectedRevision=3, idempotencyKey="delete", reason="Stop use now")
    result = await h.service.delete(h.project, h.actor, req)
    assert result["deletion"]["status"] == "blocked"
    assert result["deletion"]["providerDeletion"] == "unverified"
    assert h.repo.saved[0]["p0"]["status"] == "suspended"
    assert h.row.context_json["p0"]["release"]["activeApprovalId"] is None
    assert not h.media.deleted
    assert await h.service.delete(h.project, h.actor, req) == result
    with pytest.raises(AppError):
        await h.service.delete(h.project, uuid4(), req)


@pytest.mark.asyncio
async def test_deletion_shared_key_survives_and_provenance_uses_per_key_results(harness):
    h = harness
    session = Session(h.repo)
    session.others = [
        SimpleNamespace(state_json={"finalStorageKey": h.assembly["storageKey"]}, context_json={})
    ]
    h.repo.session = session

    async def save(row, state):
        row.state_json, row.revision = copy.deepcopy(state), state["revision"]
        h.repo.saved.append(copy.deepcopy(row.context_json))

    h.repo.save = save
    result = await h.service.delete(
        h.project,
        h.actor,
        DeletionRequest(expectedRevision=3, idempotencyKey="delete", reason="Seller removal"),
    )
    assert result["deletion"]["status"] == "partial"
    assert h.assembly["storageKey"] not in h.media.deleted
    assert any(item["status"] == "retained_shared" for item in result["deletion"]["objects"])
    assert "storageKey" not in str(result)
    assert "deleted" in {item["status"] for item in result["deletion"]["objects"]}
    assert result["deletion"]["revision"] == 5


@pytest.mark.asyncio
async def test_provenance_all_attempts_unknown_cost_and_no_raw_provider_secrets(
    harness, monkeypatch
):
    from viraldy.modules.smart_remake import project_lifecycle

    h = harness
    attempts = [
        {
            "id": "attempt",
            "stage": "video",
            "status": "unknown",
            "actualUsd": None,
            "estimatedUsd": "1",
            "reservedUsd": "1",
            "costStatus": "unknown",
            "receipt": {"taskId": "task123", "signedUrl": "https://private?token=SECRET"},
            "profile": {"apiKey": "SECRET"},
            "metadata": {"request": {"secret": "SECRET"}},
            "usage": {
                "inputTokens": 5,
                "outputTokens": "https://private?token=SECRET",
                "apiKey": "SECRET",
            },
            "error": {"code": "TIMEOUT", "message": "SECRET"},
        }
    ]

    async def get_attempts(*_):
        return attempts

    async def get_budget(*_):
        return {"actualUsd": None, "knownActualUsd": "0", "reservedUsd": "1"}

    monkeypatch.setattr(project_lifecycle, "list_attempts", get_attempts)
    monkeypatch.setattr(project_lifecycle, "budget_summary", get_budget)
    result = await h.service.provenance(h.project)
    assert result["schemaVersion"] == "smart_remake_provenance_v1"
    assert result["attempts"][0]["actualUsd"] is None
    assert result["attempts"][0]["receipt"]["taskId"] == "task123"
    assert "SECRET" not in str(result) and "storageKey" not in str(result)
    assert result["assemblies"]["records"][0]["mediaHash"] == h.assembly["mediaHash"]
    assert result["budget"]["actualUsd"] is None
    assert result["stageTimings"][0]["attemptId"] == "attempt"
    assert result["failures"][0]["code"] == "TIMEOUT"


@pytest.mark.asyncio
async def test_restore_under_current_requirements_needs_new_inspection(harness):
    h = harness
    original = copy.deepcopy(h.row.context_json["p0"]["assemblies"]["records"][0])
    h.row.context_json["p0"]["requirements"]["intent"] = "Updated constraints"
    result = await h.service.restore(
        h.project,
        h.actor,
        RestoreRequest(expectedRevision=3, idempotencyKey="restore", assemblyId=h.assembly["id"]),
    )
    restored = active_assembly(h.row.context_json["p0"])
    assert restored["constraintsHash"] == constraints_hash(h.row.context_json)
    assert restored["sourceConstraintsHash"] == original["constraintsHash"]
    assert h.row.context_json["p0"]["assemblies"]["records"][0] == original
    with pytest.raises(AppError):
        await h.service.approve(
            h.project,
            h.actor,
            ApprovalRequest(
                expectedRevision=result["revision"],
                idempotencyKey="approve",
                assemblyId=restored["id"],
                reportId="report",
            ),
        )


@pytest.mark.asyncio
async def test_rights_revoked_after_export_commit_prevents_url_signing(harness):
    h = harness
    approval = await h.service.approve(
        h.project,
        h.actor,
        ApprovalRequest(
            expectedRevision=3,
            idempotencyKey="approve",
            assemblyId=h.assembly["id"],
            reportId="report",
        ),
    )
    complete = h.repo.complete

    async def revoke_after_complete(row, state, operation, result):
        await complete(row, state, operation, result)
        h.repo.row = copy.deepcopy(row)
        h.repo.row.context_json["p0"]["rights"]["product"]["revoked"] = True

    h.repo.complete = revoke_after_complete
    with pytest.raises(AppError):
        await h.service.export(
            h.project,
            h.actor,
            ExportRequest(
                expectedRevision=4,
                idempotencyKey="export",
                assemblyId=h.assembly["id"],
                approvalId=approval["approval"]["id"],
            ),
        )
    assert not h.media.signed


@pytest.mark.asyncio
async def test_restore_corrupt_retained_output_preserves_current_project(harness):
    h = harness
    before = copy.deepcopy(h.row.context_json)
    h.media.data[h.assembly["storageKey"]] = b"corrupt"
    with pytest.raises(AppError):
        await h.service.restore(
            h.project,
            h.actor,
            RestoreRequest(
                expectedRevision=3, idempotencyKey="restore", assemblyId=h.assembly["id"]
            ),
        )
    assert h.row.context_json == before
    assert h.row.revision == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["approve", "restore"])
async def test_rights_revocation_after_start_is_never_overwritten(harness, action):
    h = harness
    start = h.repo.start

    async def revoke_after_start(*args):
        result = await start(*args)
        h.repo.row = copy.deepcopy(h.repo.row)
        h.repo.row.context_json["p0"]["rights"]["product"]["revoked"] = True
        return result

    h.repo.start = revoke_after_start
    request = (
        ApprovalRequest(
            expectedRevision=3,
            idempotencyKey="approve",
            assemblyId=h.assembly["id"],
            reportId="report",
        )
        if action == "approve"
        else RestoreRequest(
            expectedRevision=3, idempotencyKey="restore", assemblyId=h.assembly["id"]
        )
    )
    with pytest.raises(AppError):
        await getattr(h.service, action)(h.project, h.actor, request)
    assert h.repo.row.context_json["p0"]["rights"]["product"]["revoked"] is True
    assert h.repo.row.revision == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["approve", "restore", "delete"])
async def test_presentation_failure_cannot_downgrade_a_committed_action(harness, action):
    h = harness
    if action == "delete":
        h.repo.session = Session(h.repo)

        async def save(row, state):
            row.state_json, row.revision = copy.deepcopy(state), state["revision"]

        h.repo.save = save
    present = h.service.repair.present
    calls = 0

    async def fail_once(row):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("Temporary presentation failure")
        return await present(row)

    h.service.repair.present = fail_once
    request = {
        "approve": ApprovalRequest(
            expectedRevision=3,
            idempotencyKey="action",
            assemblyId=h.assembly["id"],
            reportId="report",
        ),
        "restore": RestoreRequest(
            expectedRevision=3, idempotencyKey="action", assemblyId=h.assembly["id"]
        ),
        "delete": DeletionRequest(expectedRevision=3, idempotencyKey="action", reason="Stop use"),
    }[action]
    with pytest.raises(RuntimeError):
        await getattr(h.service, action)(h.project, h.actor, request)
    operation = h.repo.operations["action"]
    assert operation.status == "completed"
    revision = h.repo.row.revision
    history = copy.deepcopy(h.repo.row.context_json)
    result = await getattr(h.service, action)(h.project, h.actor, request)
    assert result["status"] == "completed"
    assert result["operationId"] == str(operation.id)
    assert h.repo.row.revision == revision
    assert h.repo.row.context_json == history


@pytest.mark.asyncio
async def test_production_succeeded_job_is_terminal_for_deletion(harness):
    h = harness

    class StatusAwareSession(Session):
        async def execute(self, statement):
            if statement.column_descriptions[0]["entity"].__name__ == "ProcessingJobModel":
                excluded = next(
                    value for key, value in statement.compile().params.items() if "status" in key
                )
                return Result(None if "succeeded" in excluded else (uuid4(),))
            return await super().execute(statement)

    h.repo.session = StatusAwareSession(h.repo)

    async def save(row, state):
        row.state_json, row.revision = copy.deepcopy(state), state["revision"]

    h.repo.save = save
    result = await h.service.delete(
        h.project,
        h.actor,
        DeletionRequest(
            expectedRevision=3, idempotencyKey="delete", reason="Cleanup after successful worker"
        ),
    )
    assert result["deletion"]["status"] == "completed"
