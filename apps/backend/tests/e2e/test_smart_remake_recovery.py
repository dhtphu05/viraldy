"""Real isolated API/worker/storage recovery; only external AI providers are fakes.

RUN_P0_SMART_REMAKE_BROWSER=1 uv run pytest -o addopts='' \
    tests/e2e/test_smart_remake_recovery.py -q -s
"""

from __future__ import annotations

import asyncio
import gc
import hashlib
import json
import os
import sys
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit
from uuid import uuid4

import boto3
import psycopg
import pytest
from botocore.client import Config
from celery import Celery

from tests.e2e.smart_remake_capture import retain_browser_capture
from tests.e2e.smart_remake_journey import SmartRemakeJourney
from tests.e2e.smart_remake_runtime import isolated_stack
from tests.e2e.test_smart_remake_browser import register

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_P0_SMART_REMAKE_BROWSER") != "1",
    reason="Explicit opt-in starts new isolated Docker infrastructure and real browsers.",
)


@pytest.fixture(scope="module")
def recovery_stack():
    # Durable temporary artifacts must survive concurrent pytest retention sweepers.
    root = Path(tempfile.mkdtemp(prefix="viraldy-p0-recovery-"))
    print(f"P0 recovery artifacts: {root}")
    with isolated_stack(root) as stack:
        yield stack


@asynccontextmanager
async def seller(stack: Any, case: str):
    from playwright.async_api import async_playwright

    stack.scenario(
        name=case,
        repair=False,
        inspectionFailure=False,
        unknownVideoReceipt=False,
        downloadFailure=False,
    )
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 1000})
        await context.tracing.start(screenshots=True, snapshots=True)
        page = await context.new_page()
        journey = SmartRemakeJourney(page, stack)
        try:
            await register(page, stack.base_url)
            await journey.workspace()
            await journey.fill_prepare(8)
            await journey.analyze(8)
            yield journey
        finally:
            if journey.project_id:
                try:
                    await retain_browser_capture(journey, case)
                except Exception as exc:
                    (stack.root / f"{case}-capture-error.txt").write_text(type(exc).__name__)
            await page.screenshot(path=str(stack.root / f"{case}-last-screen.png"), full_page=True)
            await context.tracing.stop(path=str(stack.root / f"{case}-trace.zip"))
            await context.close()
            await browser.close()


async def submit_render(journey: SmartRemakeJourney) -> dict[str, Any]:
    async with journey.page.expect_response(
        lambda response: response.request.method == "POST" and response.url.endswith("/render"),
        timeout=30000,
    ) as submitted:
        await journey.page.get_by_role("button", name="Tạo video · 8 giây", exact=True).click()
    response = await submitted.value
    assert response.status == 200
    return (await response.json())["data"]


def processing_job(stack: Any, project_id: str, operation_id: str) -> str:
    """Read the real operation's dispatch identity; never write lifecycle or job tables."""
    dsn = stack.environment["DATABASE_SYNC_URL"].replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(dsn) as connection:
        connection.read_only = True
        found = connection.execute(
            "SELECT result_json ->> 'processingJobId' FROM smart_remake_operations "
            "WHERE project_id = %s AND id = %s",
            (project_id, operation_id),
        ).fetchone()
    assert found and found[0], "The real operation must have a durable dispatch record"
    return str(found[0])


def storage_client(stack: Any) -> Any:
    env = stack.environment
    return boto3.client(
        "s3",
        endpoint_url=env["S3_ENDPOINT_URL"],
        aws_access_key_id=env["S3_ACCESS_KEY_ID"],
        aws_secret_access_key=env["S3_SECRET_ACCESS_KEY"],
        region_name="us-east-1",
        config=Config(s3={"addressing_style": "path"}),
    )


def owned_key(stack: Any, url: str) -> str:
    """Derive only the exact test-owned object from a URL issued by the real API."""
    parsed, expected = urlsplit(url), urlsplit(stack.environment["S3_ENDPOINT_URL"])
    assert parsed.netloc == expected.netloc
    prefix = f"/{stack.environment['S3_BUCKET']}/"
    assert parsed.path.startswith(prefix)
    key = unquote(parsed.path[len(prefix) :])
    assert key.startswith("workspaces/") and "/smart-remake/" in key
    return key


def record(stack: Any, case: str, **checks: Any) -> None:
    (stack.root / f"{case}-checks.json").write_text(
        json.dumps(
            {
                "mode": "mock",
                "infrastructure": ["API", "Celery", "PostgreSQL", "Redis", "MinIO"],
                "providerBoundary": "constructor fakes with committed attempt reservations",
                **checks,
            },
            indent=2,
        )
        + "\n"
    )


async def wait_failed(journey: SmartRemakeJourney, operation_id: str) -> dict[str, Any]:
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        project = await journey.project()
        last = project.get("lastOperation") or {}
        if not project.get("pendingOperation") and last.get("id") == operation_id:
            assert last["status"] == "failed", last
            return project
        await asyncio.sleep(0.2)
    raise AssertionError("Compose failure was not durably recorded; inspect worker.log")


@pytest.mark.asyncio
async def test_duplicate_delivery_and_two_tab_revision_conflict(recovery_stack):
    stack = recovery_stack
    async with seller(stack, "duplicate-and-tabs") as journey:
        before = {stage: len(stack.calls(stage)) for stage in ("image", "video")}
        stack.stop("worker")
        try:
            submitted = await submit_render(journey)
            job_id = submitted["processingJobId"]
            operation_id = submitted["repairProject"]["pendingOperation"]["id"]
            assert processing_job(stack, journey.project_id, operation_id) == job_id
            client = Celery(
                "p0-recovery",
                broker=stack.environment["CELERY_BROKER_URL"],
                backend=stack.environment["CELERY_RESULT_BACKEND"],
            )
            # Two genuine duplicate broker deliveries join the normal initial delivery.
            duplicates = [
                client.send_task(
                    "viraldy.worker.tasks.process_asset.run_processing_job",
                    args=[job_id],
                    queue="default",
                )
                for _ in range(2)
            ]
        finally:
            stack.start_worker()
        project = await journey.wait_idle()
        duplicate_results = [
            await asyncio.to_thread(result.get, timeout=60) for result in duplicates
        ]
        # Release result subscriptions while this test's Redis still exists. Celery's
        # AsyncResult destructor otherwise reconnects during GC after container teardown.
        for result in duplicates:
            result.forget()
        duplicates.clear()
        del result
        gc.collect()
        client.close()
        assert all(result.get("ignored") is True for result in duplicate_results), duplicate_results
        expected_images = len(project["renderPlan"]["units"])
        assert len(stack.calls("image")) == before["image"] + expected_images
        assert len(stack.calls("video")) == before["video"] + 1
        await journey.refresh_ui()
        second_page = await journey.page.context.new_page()
        await second_page.goto(journey.page.url)
        await second_page.get_by_role("region", name="Kết quả Smart Remake", exact=True).wait_for()
        other = SmartRemakeJourney(second_page, stack)
        other.root, other.project_id = journey.root, journey.project_id
        first_snapshot, second_snapshot = await journey.project(), await other.project()
        assert first_snapshot["revision"] == second_snapshot["revision"]
        selected = project["draftTimeline"]["items"][0]
        payload = {
            "expectedRevision": first_snapshot["revision"],
            "idempotencyKey": str(uuid4()),
            "items": [
                {
                    "renderUnitId": selected["renderUnitId"],
                    "versionId": selected["versionId"],
                    "inFrame": 24,
                    "outFrame": 24 + selected["targetDurationFrames"],
                    "reviewed": True,
                }
            ],
        }
        first = await journey.page.request.patch(
            f"{journey.root}/projects/{journey.project_id}/timeline",
            data=payload,
            headers={"Origin": stack.base_url},
        )
        assert first.status == 200
        stale_payload = {
            **payload,
            "idempotencyKey": str(uuid4()),
            "expectedRevision": second_snapshot["revision"],
        }
        stale = await second_page.request.patch(
            f"{other.root}/projects/{other.project_id}/timeline",
            data=stale_payload,
            headers={"Origin": stack.base_url},
        )
        assert stale.status == 409
        assert (await stale.json())["error"]["code"] == "SMART_REMAKE_REVISION_CONFLICT"
        fresh = await journey.project()
        assert fresh["draftTimeline"]["items"][0]["inFrame"] == 24
        assert fresh["revision"] == first_snapshot["revision"] + 1
        await second_page.reload()
        await second_page.get_by_role("region", name="Kết quả Smart Remake", exact=True).wait_for()
        assert (await other.project())["revision"] == fresh["revision"]
        assert len(stack.calls("image")) == before["image"] + expected_images
        assert len(stack.calls("video")) == before["video"] + 1
        await second_page.screenshot(path=str(stack.root / "two-tabs-reloaded.png"), full_page=True)
        record(
            stack,
            "duplicate-and-tabs",
            duplicateDeliveries=2,
            duplicateResults=duplicate_results,
            imageCalls=expected_images,
            videoCalls=1,
            staleRevisionHttp=stale.status,
            revisionAfter=fresh["revision"],
            retainedSelection={"inFrame": 24, "outFrame": 24 + selected["targetDurationFrames"]},
        )


@pytest.mark.asyncio
async def test_missing_raw_during_compose_preserves_previous_assembly_and_recovers(recovery_stack):
    stack = recovery_stack
    async with seller(stack, "storage-compose-recovery") as journey:
        await submit_render(journey)
        await journey.wait_idle()
        await journey.refresh_ui()
        await journey.choose_ranges([0, 0])
        first = await journey.compose(8)
        old_id = first["assemblies"]["activeAssemblyId"]
        old_preview = await journey.page.request.get(first["finalVideoUrl"])
        assert old_preview.status == 200
        old_hash = hashlib.sha256(await old_preview.body()).hexdigest()
        scene = first["scenes"][0]
        version = next(v for v in scene["versions"] if v["id"] == scene["activeVersionId"])
        key = owned_key(stack, version["videoUrl"])
        client, bucket = storage_client(stack), stack.environment["S3_BUCKET"]
        retained = client.get_object(Bucket=bucket, Key=key)["Body"].read()
        assert hashlib.sha256(retained).hexdigest() == version["mediaHash"]
        calls = stack.calls()
        stack.stop("worker")
        try:
            # API preflight reads valid footage. The owned object disappears before worker decode.
            queued = await journey.mutate("publish", {})
            operation_id = queued["data"]["operationId"]
            client.delete_object(Bucket=bucket, Key=key)
            missing = await journey.page.request.get(version["videoUrl"])
            assert missing.status == 404
            stack.start_worker()
            failed = await wait_failed(journey, operation_id)
            assert failed["assemblies"]["activeAssemblyId"] == old_id
            assert failed["revision"] == first["revision"]
            available = await journey.page.request.get(failed["finalVideoUrl"])
            assert available.status == 200
            assert hashlib.sha256(await available.body()).hexdigest() == old_hash
            assert stack.calls() == calls
        finally:
            # Restoring the same test-owned bytes repairs storage, not lifecycle/database state.
            client.put_object(Bucket=bucket, Key=key, Body=retained, ContentType="video/mp4")
            if "worker" not in stack.processes:
                stack.start_worker()
        retried = await journey.mutate("publish", {})
        recovered = await journey.wait_idle()
        assert retried["data"]["operationId"] != operation_id
        assert recovered["assemblies"]["activeAssemblyId"] != old_id
        assert stack.calls() == calls, "Storage retry cannot generate new AI footage"
        preview = await journey.page.request.get(recovered["finalVideoUrl"])
        assert preview.status == 200
        assert hashlib.sha256(await preview.body()).hexdigest() == old_hash
        await journey.refresh_ui()
        record(
            stack,
            "storage-compose-recovery",
            missingObjectHttp=missing.status,
            failedOperationId=operation_id,
            failureCode=failed["lastOperation"]["errorCode"],
            previousAssemblyId=old_id,
            recoveredAssemblyId=recovered["assemblies"]["activeAssemblyId"],
            retainedMediaHash=old_hash,
            duplicateGenerationCalls=0,
        )


@pytest.mark.asyncio
async def test_expired_minio_preview_signature_refreshes_without_new_generation(recovery_stack):
    stack = recovery_stack
    async with seller(stack, "expired-media-refresh") as journey:
        await submit_render(journey)
        await journey.wait_idle()
        await journey.refresh_ui()
        calls = stack.calls()
        stack.stop("api")
        stack.environment["S3_PRESIGNED_EXPIRY_SECONDS"] = "2"
        stack.spawn(
            "api",
            [
                sys.executable,
                "-m",
                "tests.e2e.smart_remake_server",
                "api",
                str(urlsplit(stack.api_url).port),
            ],
            stack.root,
        )
        stack.wait_http("api", f"{stack.api_url}/health/live")
        short_lived = await journey.project()
        version = short_lived["scenes"][0]["versions"][0]
        signed = version["videoUrl"]
        live = await journey.page.request.get(signed)
        assert live.status == 200
        actual_hash = hashlib.sha256(await live.body()).hexdigest()
        assert actual_hash == version["mediaHash"]
        await asyncio.sleep(3.1)
        expired = await journey.page.request.get(signed)
        assert expired.status == 403
        assert "expired" in (await expired.text()).lower()
        player = journey.page.get_by_label("Video Clip AI · 8 giây · Cảnh 1", exact=True)
        await player.evaluate("(video, url) => { video.src = url; video.load(); }", signed)
        await journey.page.wait_for_function("""() => {
            const video = [...document.querySelectorAll('video')].find(
                item => item.ariaLabel === 'Video Clip AI · 8 giây · Cảnh 1');
            return !!video?.error;
        }""")
        await journey.refresh_ui()
        await journey.page.wait_for_function("""() => {
            const video = [...document.querySelectorAll('video')].find(
                item => item.ariaLabel === 'Video Clip AI · 8 giây · Cảnh 1');
            return video && video.readyState >= 2 && !video.error;
        }""")
        refreshed = await journey.project()
        fresh_url = refreshed["scenes"][0]["versions"][0]["videoUrl"]
        assert fresh_url != signed
        fresh_media = await journey.page.request.get(fresh_url)
        assert fresh_media.status == 200
        assert hashlib.sha256(await fresh_media.body()).hexdigest() == actual_hash
        assert stack.calls() == calls
        record(
            stack,
            "expired-media-refresh",
            validHttp=live.status,
            expiredHttp=expired.status,
            refreshedHttp=fresh_media.status,
            retainedMediaHash=actual_hash,
            duplicateGenerationCalls=0,
            playerRecovered=True,
            presignedExpirySeconds=2,
        )
