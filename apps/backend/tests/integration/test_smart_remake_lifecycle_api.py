"""Real API/PG/FFmpeg P0 journeys with constructor-only offline provider seams."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import importlib
import io
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from httpx import ASGITransport, AsyncClient
from PIL import Image
from pydantic import SecretStr
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from tests.integration.test_smart_remake_kie_workflow import kie_database_url as _database_url
from tests.unit.test_smart_remake_rights import intake_payload
from viraldy.api.dependencies.auth import get_current_user
from viraldy.api.middleware.errors import app_error_handler, validation_error_handler
from viraldy.modules.identity.models import UserModel
from viraldy.modules.jobs.repository import WorkerJobRepository
from viraldy.modules.smart_remake import (
    inspection_tasks,
    intake_router,
    kie_worker,
    kie_workflow,
    lifecycle_router,
    timeline_compile,
    timeline_worker,
)
from viraldy.modules.smart_remake.budget_ledger import list_attempts
from viraldy.modules.smart_remake.budget_models import SmartRemakeAttemptModel
from viraldy.modules.smart_remake.budgeted_analysis import request_snapshot
from viraldy.modules.smart_remake.engine import openai_images
from viraldy.modules.smart_remake.engine.media_binaries import ffmpeg_path
from viraldy.modules.smart_remake.fixture import FixtureGeminiClient
from viraldy.modules.smart_remake.loading_summary import SUMMARY_MARKER
from viraldy.modules.smart_remake.models import SmartRemakeProjectModel
from viraldy.modules.smart_remake.project_policy import stable_hash
from viraldy.modules.workspaces.models import WorkspaceModel
from viraldy.platform.config.settings import get_settings
from viraldy.platform.database.session import get_async_session
from viraldy.shared.errors.base import AppError

router = importlib.import_module("viraldy.modules.smart_remake.router")


def wire_keys(value):
    if isinstance(value, dict):
        return set(value) | set().union(*(wire_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(wire_keys(item) for item in value))
    return set()


@pytest.fixture(scope="module")
def api_database_url():
    yield from _database_url.__wrapped__()


class PrivateStorage:
    def __init__(self):
        self.objects = {}

    def upload_file(self, source_path, key, content_type):
        assert key.startswith("workspaces/") and "/smart-remake/" in key
        self.objects[key] = (Path(source_path).read_bytes(), content_type)

    def download_object(self, key, destination_path):
        Path(destination_path).write_bytes(self.objects[key][0])

    def delete_object(self, key):
        self.objects.pop(key, None)

    def object_exists(self, key):
        return key in self.objects

    def create_presigned_download(self, key, *, filename=None):
        assert key in self.objects
        return (
            f"https://private-media.example.test/signed/{hashlib.sha256(key.encode()).hexdigest()}"
        )


@pytest.fixture
async def api(api_database_url, tmp_path, monkeypatch):
    for key, value in {
        "SMART_REMAKE_ENABLED": "true",
        "KIE_API_KEY": "offline-only",
        "GEMINI_API_KEY": "offline-only",
        "SMART_REMAKE_P0_MAX_ANALYSIS_USD": "0.20",
        "SMART_REMAKE_P0_MAX_INSPECTION_USD": "0.10",
        "SMART_REMAKE_P0_MAX_IMAGE_USD": "0.50",
        "SMART_REMAKE_P0_MAX_VIDEO_USD": "1.00",
    }.items():
        monkeypatch.setenv(key, value)
    settings = get_settings().model_copy(
        update={
            "database_url": api_database_url,
            "database_sync_url": api_database_url.replace(
                "postgresql+asyncpg", "postgresql+psycopg"
            ),
            "ai_mode": "live",
            "openai_api_key": SecretStr("offline-only"),
        }
    )
    source = tmp_path / "authored.mp4"
    subprocess.run(  # noqa: S603 - fixed argv and pytest-owned media path
        [
            ffmpeg_path(),
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=90x160:r=24:d=8",
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(source),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
    clip = source.read_bytes()
    image = io.BytesIO()
    Image.new("RGB", (720, 1280), "red").save(image, format="PNG")
    product = image.getvalue()
    storage, calls, dispatched = PrivateStorage(), [], []
    engine = create_async_engine(api_database_url)
    sync_engine = create_engine(settings.database_sync_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    actor, workspace, foreign = uuid4(), uuid4(), uuid4()
    async with sessions() as session:
        session.add(UserModel(id=actor, external_auth_id=str(actor), email=f"{actor}@example.test"))
        await session.flush()
        for identity in (workspace, foreign):
            session.add(
                WorkspaceModel(
                    id=identity, slug=str(identity), name="P0 API", created_by_user_id=actor
                )
            )
        await session.commit()

    def receipt(stage, request_hash=None):
        with Session(sync_engine) as session:
            statement = select(SmartRemakeAttemptModel).where(
                SmartRemakeAttemptModel.workspace_id == workspace,
                SmartRemakeAttemptModel.stage == stage,
                SmartRemakeAttemptModel.status.in_(("reserved", "submitted")),
            )
            if request_hash:
                statement = statement.where(SmartRemakeAttemptModel.request_hash == request_hash)
            attempt = session.scalars(
                statement.order_by(SmartRemakeAttemptModel.created_at.desc())
            ).first()
            assert attempt is not None, f"{stage} provider requires a committed ledger reservation"
            assert str(attempt.id) not in {item["attemptId"] for item in calls}
            calls.append(
                {"stage": stage, "attemptId": str(attempt.id), "requestHash": attempt.request_hash}
            )

    async def paid_receipt(stage, request_hash=None):
        await asyncio.to_thread(receipt, stage, request_hash)

    def worker(job_id):
        with Session(sync_engine, expire_on_commit=False) as session:
            repository = WorkerJobRepository(session)
            job = repository.claim_job(UUID(job_id))
            assert job is not None
            session.commit()

            def ensure_active():
                repository.assert_claim_active(job)
                session.commit()

            execute = {
                "smart_remake_kie": kie_worker.execute_kie_job,
                "smart_remake_compose": timeline_worker.execute_compose_job,
                "smart_remake_inspect": inspection_tasks.execute_inspection_job,
            }[job.job_type]
            output = execute(job, settings, ensure_active)
            repository.mark_succeeded(job, output)
            session.commit()
            return output

    class ProviderHTTP:
        def __init__(self, **kwargs):
            self.timeout = kwargs.get("timeout")

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, **kwargs):
            assert url.startswith("https://generativelanguage.googleapis.com/")
            body = kwargs["json"]
            system = body["system_instruction"]["parts"][0]["text"]
            prompt = body["contents"][0]["parts"][0]["text"]
            media = [
                {
                    "bytes": base64.b64decode(part["inline_data"]["data"]),
                    "mime_type": part["inline_data"]["mime_type"],
                }
                for part in body["contents"][0]["parts"][1:]
            ]
            try:
                inspection = json.loads(prompt)
            except json.JSONDecodeError:
                inspection = {}
            stage = "inspection" if inspection.get("observations") else "analysis"
            config = body["generationConfig"]
            profile = {"maxOutputTokens": config["maxOutputTokens"]}
            if thinking := config.get("thinkingConfig"):
                profile["thinkingBudget"] = thinking["thinkingBudget"]
            summary = system.startswith(SUMMARY_MARKER)
            if summary:
                profile["timeoutSeconds"] = self.timeout
            await paid_receipt(
                stage, stable_hash(request_snapshot(system, prompt, media, profile=profile))
            )
            if summary:
                result = {
                    "summary": "Video kiểm thử có nền đỏ.",
                    "observations": [{"label": "Bối cảnh", "detail": "Khung hình nền đỏ."}],
                }
            elif stage == "inspection":
                result = {
                    "findings": [
                        {
                            "requirementId": rule["id"],
                            "status": "passed",
                            "observed": "Self-authored red media matches.",
                            "observationIds": [item["id"] for item in inspection["observations"]],
                        }
                        for rule in inspection["requirements"]
                    ]
                }
            else:
                result = await FixtureGeminiClient().generate_json(
                    system_instruction=system, prompt=prompt, media=media
                )
            return httpx.Response(
                200,
                json={
                    "candidates": [{"content": {"parts": [{"text": json.dumps(result)}]}}],
                    "usageMetadata": {"promptTokenCount": 21, "candidatesTokenCount": 17},
                    "responseId": f"offline-api-{len(calls)}",
                },
            )

    class Images:
        def __init__(self, *args):
            pass

        async def edit(self, **kwargs):
            await paid_receipt("image")
            return {
                "bytes": product,
                "mimeType": "image/png",
                "mediaHash": hashlib.sha256(product).hexdigest(),
                "requestId": f"offline-image-{len(calls)}",
                "usage": {"input_tokens": 7},
            }

    class Video:
        async def upload_file(self, media):
            return f"https://8.8.8.8/{hashlib.sha256(media.bytes).hexdigest()}.png"

        async def create_task(self, *, model, input_data):
            await paid_receipt("video")
            return {"task_id": f"offline-video-{len(calls)}", "status": "queued"}

        async def get_task(self, task_id):
            return {
                "task_id": task_id,
                "status": "completed",
                "output": {"video_url": "https://8.8.8.8/owned.mp4"},
            }

        async def download_file(self, url):
            return clip

    async def dispatch(session, job_id):
        dispatched.append(str(job_id))

    monkeypatch.setattr(httpx, "AsyncClient", ProviderHTTP)
    monkeypatch.setattr(openai_images, "OpenAIImageClient", Images)
    monkeypatch.setattr(kie_workflow, "KieClient", Video)
    monkeypatch.setattr(kie_workflow, "_dispatch", dispatch)
    for module in (router, intake_router, timeline_compile, kie_workflow):
        monkeypatch.setattr(module, "S3StorageAdapter", lambda settings: storage)
    for module in (router, intake_router, lifecycle_router):
        monkeypatch.setattr(module, "require_workspace_permission", AsyncMock())
    app = FastAPI()
    app.include_router(router.router)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    async def db_override():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=actor)
    app.dependency_overrides[get_async_session] = db_override
    app.dependency_overrides[get_settings] = lambda: settings
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        try:
            yield SimpleNamespace(
                client=client,
                base=f"/workspaces/{workspace}/smart-remake",
                actor=actor,
                workspace=workspace,
                foreign=foreign,
                settings=settings,
                sessions=sessions,
                storage=storage,
                calls=calls,
                dispatched=dispatched,
                clip=clip,
                product=product,
                worker=lambda job_id: asyncio.to_thread(worker, job_id),
            )
        finally:
            await engine.dispose()
            sync_engine.dispose()


async def prepare(api, *, full_source=False):
    response = await api.client.post(
        f"{api.base}/projects",
        data={"metadata": intake_payload().model_dump_json()},
        files={
            "referenceVideo": ("source.mp4", api.clip, "video/mp4"),
            "productImage": ("product.png", api.product, "image/png"),
        },
    )
    assert response.status_code == 200, response.text
    project = response.json()["data"]["project"]
    assert project["phase"] == "intake"
    assert not api.calls
    response = await api.client.post(
        f"{api.base}/compile",
        data={
            "timelineMode": "reference",
            "projectId": project["id"],
            "expectedRevision": project["revision"],
            "idempotencyKey": "compile-owned",
            "targetDuration": "8",
            "sourceCutFrames": "[0,192]",
            **({"analysisScope": "full_source"} if full_source else {}),
        },
    )
    assert response.status_code == 200, response.text
    return project, response.json()["data"]


@pytest.mark.asyncio
async def test_owned_intake_compile_get_and_replay_use_real_ledger(api):
    intake, compiled = await prepare(api)
    assert compiled["projectId"] == intake["id"]
    assert len(api.calls) == 2
    assert {call["stage"] for call in api.calls} == {"analysis"}
    response = await api.client.get(f"{api.base}/projects/{intake['id']}")
    assert response.status_code == 200, response.text
    project = response.json()["data"]
    for private in ("storageKey", "sourceKey", "productKey", "finalStorageKey"):
        assert private not in response.text
    assert project["revision"] == compiled["revision"]
    response = await api.client.post(
        f"{api.base}/compile",
        data={
            "timelineMode": "reference",
            "projectId": intake["id"],
            "expectedRevision": 1,
            "idempotencyKey": "compile-owned",
            "targetDuration": "8",
            "sourceCutFrames": "[0,192]",
        },
    )
    assert response.status_code == 200, response.text
    assert len(api.calls) == 2
    async with api.sessions() as session:
        row = await session.get(SmartRemakeProjectModel, UUID(intake["id"]))
        attempts = await list_attempts(session, api.workspace, row.id)
        assert len(attempts) == 2
        assert all(item["receipt"]["requestId"].startswith("offline-api-") for item in attempts)
        assert all(item["usage"]["promptTokenCount"] == 21 for item in attempts)
        assert row.context_json["p0"]["inputHash"]
    response = await api.client.get(
        f"/workspaces/{api.foreign}/smart-remake/projects/{intake['id']}"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_direct_live_compile_without_intake_never_calls_provider(api):
    response = await api.client.post(
        f"{api.base}/compile",
        data={
            "timelineMode": "reference",
            "targetDuration": "8",
            "sourceCutFrames": "[0,192]",
        },
        files={
            "referenceVideo": ("source.mp4", api.clip, "video/mp4"),
            "productImage": ("product.png", api.product, "image/png"),
        },
    )
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "SMART_REMAKE_INTAKE_REQUIRED"
    assert not api.calls


@pytest.mark.asyncio
async def test_revoked_owned_rights_block_generation_before_paid_provider(api):
    intake, compiled = await prepare(api)
    rights = intake_payload().rights.model_dump(mode="json")
    rights["product"]["revoked"] = True
    response = await api.client.patch(
        f"{api.base}/projects/{intake['id']}/rights",
        json={
            "expectedRevision": compiled["revision"],
            "idempotencyKey": "revoke-before-generate",
            "rights": rights,
        },
    )
    assert response.status_code == 200, response.text
    response = await api.client.post(
        f"{api.base}/render",
        data={
            "compileResult": json.dumps(compiled),
            "projectId": intake["id"],
            "expectedRevision": response.json()["data"]["project"]["revision"],
            "idempotencyKey": "blocked-generate",
            "provider": "kie",
        },
    )
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "SMART_REMAKE_RIGHTS_REQUIRED"
    assert len(api.calls) == 2
    assert not api.dispatched


@pytest.mark.asyncio
async def test_missing_rights_evidence_or_cap_blocks_before_model(api):
    payload = intake_payload().model_dump(mode="json")
    payload["rights"]["source"]["evidenceNote"] = ""
    response = await api.client.post(
        f"{api.base}/projects",
        data={"metadata": json.dumps(payload)},
        files={
            "referenceVideo": ("source.mp4", api.clip, "video/mp4"),
            "productImage": ("product.png", api.product, "image/png"),
        },
    )
    assert response.status_code == 200, response.text
    project = response.json()["data"]["project"]
    response = await api.client.post(
        f"{api.base}/compile",
        data={
            "timelineMode": "reference",
            "projectId": project["id"],
            "expectedRevision": project["revision"],
            "idempotencyKey": "missing-evidence",
            "targetDuration": "8",
            "sourceCutFrames": "[0,192]",
        },
    )
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "SMART_REMAKE_RIGHTS_EVIDENCE_REQUIRED"
    payload["budget"] = {"mode": "limited"}
    response = await api.client.post(
        f"{api.base}/projects",
        data={"metadata": json.dumps(payload)},
        files={
            "referenceVideo": ("source.mp4", api.clip, "video/mp4"),
            "productImage": ("product.png", api.product, "image/png"),
        },
    )
    assert response.status_code == 422
    assert not api.calls


@pytest.mark.asyncio
async def test_real_worker_inspector_checked_export_restore_and_deletion_api(api):
    intake, compiled = await prepare(api, full_source=True)
    project_id = intake["id"]
    endpoint = f"{api.base}/projects/{project_id}"
    response = await api.client.post(
        f"{api.base}/render",
        data={
            "compileResult": json.dumps(compiled),
            "projectId": project_id,
            "expectedRevision": compiled["revision"],
            "idempotencyKey": "generate",
            "provider": "kie",
        },
    )
    assert response.status_code == 200, response.text
    generated = response.json()["data"]
    output = await api.worker(generated["processingJobId"])
    assert output["status"] == "completed"
    response = await api.client.get(endpoint)
    assert response.status_code == 200, response.text
    project = response.json()["data"]
    assert project["scenes"][0]["activeVersionId"]
    assert {call["stage"] for call in api.calls} == {"analysis", "image", "video"}
    selections = [
        {key: item[key] for key in ("renderUnitId", "versionId", "inFrame", "outFrame")}
        for item in project["draftTimeline"]["items"]
    ]
    response = await api.client.patch(
        f"{endpoint}/timeline",
        json={
            "expectedRevision": project["revision"],
            "idempotencyKey": "select",
            "items": selections,
        },
    )
    assert response.status_code == 200, response.text
    project = response.json()["data"]["project"]
    response = await api.client.post(
        f"{endpoint}/publish",
        json={
            "expectedRevision": project["revision"],
            "idempotencyKey": "compose",
        },
    )
    assert response.status_code == 200, response.text
    await api.worker(api.dispatched[-1])
    response = await api.client.get(endpoint)
    assert response.status_code == 200, response.text
    project = response.json()["data"]
    assert "downloadUrl" not in project
    assembly_id = project["assemblies"]["activeAssemblyId"]
    original_hash = project["assemblies"]["records"][0]["mediaHash"]
    response = await api.client.post(
        f"{endpoint}/inspections",
        json={
            "expectedRevision": project["revision"],
            "idempotencyKey": "inspect-final",
            "subject": {"kind": "assembly", "assemblyId": assembly_id},
        },
    )
    assert response.status_code == 200, response.text
    inspection_job = response.json()["data"]["processingJobId"]
    await api.worker(inspection_job)
    assert {call["stage"] for call in api.calls} == {"analysis", "image", "video", "inspection"}
    response = await api.client.get(endpoint)
    project = response.json()["data"]
    report = next(
        report
        for report in project["inspectionSummary"]["reports"]
        if report["subject"].get("assemblyId") == assembly_id
    )
    assert report["status"] == "needs_review"
    assert report["observations"] and report["coverage"]
    assert report["modelProfile"]["provider"] == "google"
    assert report["id"] in project["inspectionSummary"]["currentReportIds"]
    previews = {
        (item["mediaId"], item["mediaHash"], item["timebase"]): item
        for item in project["inspectionMedia"]
    }
    mappings = [edge for edge in project["inspectionMappings"]
                if edge.get("assemblyId") == assembly_id]
    assert mappings and any(edge["from"]["timebase"] == "final" for edge in mappings)
    for edge in mappings:
        assert edge["from"]["outFrame"] - edge["from"]["inFrame"] == (
            edge["to"]["outFrame"] - edge["to"]["inFrame"]
        )
        for evidence_range in (edge["from"], edge["to"]):
            assert (evidence_range["mediaId"], evidence_range["mediaHash"],
                    evidence_range["timebase"]) in previews
    local_media = [item for item in previews.values()
                   if item["timebase"] == "scene_local" and item.get("assemblyId") == assembly_id]
    assert local_media
    for item in local_media:
        raw = previews[(item["playbackMediaId"], item["playbackMediaHash"], "raw_group")]
        assert item["playbackTimebase"] == "raw_group" and item["url"] == raw["url"]
    for observed in report["observations"]:
        binding = (observed["mediaId"], observed["mediaHash"], observed.get("timebase") or "image")
        assert binding in previews
        assert previews[binding]["url"].startswith("https://private-media.example.test/signed/")
    assert previews[("subject", report["subject"]["mediaHash"], "final")]["frameCount"] == 192
    for finding in report["findings"]:
        if finding["status"] == "passed":
            continue
        response = await api.client.post(
            f"{endpoint}/inspection-reviews",
            json={
                "expectedRevision": project["revision"],
                "idempotencyKey": f"review-{finding['id']}",
                "reportId": report["id"],
                "findingId": finding["id"],
                "decision": "accept",
                "reason": "Human checked the complete authored video against the originals.",
            },
        )
        assert response.status_code == 200, response.text
        project = response.json()["data"]["project"]
    response = await api.client.post(
        f"{endpoint}/approvals",
        json={
            "expectedRevision": project["revision"],
            "idempotencyKey": "approve",
            "assemblyId": assembly_id,
            "reportId": report["id"],
        },
    )
    assert response.status_code == 200, response.text
    approval_result = response.json()["data"]
    project = approval_result["project"]
    approval_id = approval_result["approval"]["id"]
    response = await api.client.post(
        f"{endpoint}/exports",
        json={
            "expectedRevision": project["revision"],
            "idempotencyKey": "checked-export",
            "assemblyId": assembly_id,
            "approvalId": approval_id,
        },
    )
    assert response.status_code == 200, response.text
    exported = response.json()["data"]
    assert exported["downloadUrl"].startswith("https://private-media.example.test/signed/")
    assert exported["technicalCheck"]["labelVerification"]["verified"] is True
    assert exported["exportMediaHash"] != original_hash
    project = exported["project"]
    leaked = {"storageKey", "stateSnapshot", "contextSnapshot"} & wire_keys(response.json())
    assert not leaked, sorted(leaked)
    paid_count = len(api.calls)
    response = await api.client.post(
        f"{endpoint}/restore",
        json={
            "expectedRevision": project["revision"],
            "idempotencyKey": "restore",
            "assemblyId": assembly_id,
        },
    )
    assert response.status_code == 200, response.text
    project = response.json()["data"]["project"]
    restored = project["assemblies"]["records"][-1]
    assert restored["id"] != assembly_id and restored["mediaHash"] == original_hash
    assert project["release"]["activeApprovalId"] is None
    assert report["id"] not in project["inspectionSummary"]["currentReportIds"]
    assert len(api.calls) == paid_count
    response = await api.client.post(
        f"{endpoint}/exports",
        json={
            "expectedRevision": project["revision"],
            "idempotencyKey": "stale-export",
            "assemblyId": assembly_id,
            "approvalId": approval_id,
        },
    )
    assert response.status_code == 409, response.text
    response = await api.client.get(f"{endpoint}/provenance")
    assert response.status_code == 200, response.text
    assert "storageKey" not in response.text and "requestId" in response.text
    provenance = response.json()["data"]
    assert provenance["run"]["mode"] is None
    assert provenance["run"]["providerExecution"] == "unverified"
    response = await api.client.post(
        f"{endpoint}/deletions",
        json={
            "expectedRevision": project["revision"],
            "idempotencyKey": "delete",
            "reason": "End self-authored API pilot.",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["deletion"]["status"] == "completed"
    assert not api.storage.objects
    assert len(api.calls) == paid_count
    response = await api.client.get(endpoint)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["status"] == "deleted"
    assert not response.json()["data"].get("finalVideoUrl")
