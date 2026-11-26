"""Real browser/API/worker acceptance; only provider constructors are offline.

RUN_P0_SMART_REMAKE_BROWSER=1 .venv/bin/pytest \
    tests/e2e/test_smart_remake_browser.py --no-cov -v

An opt-in skip is not acceptance evidence. A completed run must retain its
artifacts and report all failures; no API response routing/interception is used.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import tempfile
from pathlib import Path

import pytest

from tests.e2e.smart_remake_capture import retain_browser_capture
from tests.e2e.smart_remake_journey import SmartRemakeJourney
from tests.e2e.smart_remake_media import assert_export_pixels_and_audio
from tests.e2e.smart_remake_runtime import isolated_stack
from tests.e2e.smart_remake_zoom import assert_native_result_zoom

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_P0_SMART_REMAKE_BROWSER") != "1",
    reason="Explicit opt-in starts disposable Docker infrastructure and a real browser.",
)


@pytest.fixture(scope="module")
def smart_remake_stack():
    # Other agents run pytest concurrently; its shared retention sweeper can
    # delete completed browser artifacts before the integrator reads them.
    root = Path(tempfile.mkdtemp(prefix="viraldy-p0-b-browser-"))
    with isolated_stack(root) as stack:
        yield stack


@pytest.mark.asyncio
async def test_smart_remake_isolated_stack_accepts_real_auth_and_worker(smart_remake_stack):
    """Startup probe is separate from lifecycle acceptance, never counted as it."""
    from playwright.async_api import async_playwright

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await register(page, smart_remake_stack.base_url)
        me = await context.request.get(f"{smart_remake_stack.base_url}/api/backend/me")
        assert me.status == 200
        assert smart_remake_stack.processes["worker"].poll() is None
        assert not smart_remake_stack.calls(), (
            "Registration and empty intake must not call a provider"
        )
        await context.close()
        await browser.close()


@pytest.mark.asyncio
async def test_smart_remake_prepare_responsive_keyboard_focus_and_reduced_motion(
    smart_remake_stack,
):
    from playwright.async_api import async_playwright

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(reduced_motion="reduce")
        page = await context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await register(page, smart_remake_stack.base_url)
        assert await page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")
        focus = await page.evaluate("document.activeElement?.tagName")
        assert focus == "H1", "Wizard transition should move focus to its heading"
        for width in (390, 768, 1280, 1440):
            await page.set_viewport_size({"width": width, "height": 1000})
            assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
            await page.screenshot(
                path=str(smart_remake_stack.root / f"prepare-{width}.png"), full_page=True
            )
        await page.keyboard.press("Tab")
        assert await page.evaluate("document.activeElement !== document.body")
        # CSS zoom exercises 200% reflow. It is recorded explicitly, not described
        # as a native browser-chrome zoom or as result-screen acceptance.
        await page.evaluate("document.documentElement.style.zoom = '2'")
        assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        await page.screenshot(
            path=str(smart_remake_stack.root / "prepare-css-zoom-200.png"), full_page=True
        )
        await page.evaluate("document.documentElement.style.zoom = ''")
        assert not errors, errors
        (smart_remake_stack.root / "prepare-browser-checks.json").write_text(
            json.dumps(
                {
                    "mode": "fixture",
                    "screen": "prepare",
                    "widths": [390, 768, 1280, 1440],
                    "keyboard": True,
                    "headingFocus": True,
                    "reducedMotion": True,
                    "cssZoomPercent": 200,
                    "nativeBrowserZoom": "unmeasured",
                },
                indent=2,
            )
        )
        await context.close()
        await browser.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("case,duration", [("pass", 8), ("repair", 16)])
async def test_smart_remake_complete_seller_journey_through_real_worker(
    smart_remake_stack, case, duration
):
    """Execution of these cases is gated operationally on Chat A's M2 checkpoint."""
    from playwright.async_api import async_playwright

    from viraldy.modules.smart_remake.timeline_media import probe_timeline_media

    smart_remake_stack.scenario(
        name=case,
        repair=False,
        inspectionFailure=False,
        unknownVideoReceipt=False,
        downloadFailure=False,
    )
    call_baseline = {stage: len(smart_remake_stack.calls(stage)) for stage in ("image", "video")}
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 1000}, reduced_motion="reduce", accept_downloads=True
        )
        await context.tracing.start(screenshots=True, snapshots=True)
        page = await context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        journey = SmartRemakeJourney(page, smart_remake_stack)
        try:
            await register(page, smart_remake_stack.base_url)
            await journey.workspace()
            await journey.fill_prepare(duration)
            await journey.analyze(duration)
            assert all(
                len(smart_remake_stack.calls(stage)) == count
                for stage, count in call_baseline.items()
            )
            # Broker delivery survives an absent consumer. Double Generate is a
            # real UI interaction and must create only one durable render intent.
            smart_remake_stack.stop("worker")
            async with page.expect_response(
                lambda response: response.request.method == "POST"
                and response.url.endswith("/render"),
                timeout=30000,
            ) as rendered:
                await page.get_by_role(
                    "button", name=f"Tạo video · {duration} giây", exact=True
                ).dblclick()
            assert (await rendered.value).status == 200
            assert (await journey.project())["pendingOperation"]
            smart_remake_stack.start_worker()
            project = await journey.wait_idle()
            assert all(scene["versions"] for scene in project["scenes"])
            await journey.refresh_ui()
            original_hashes = journey.scene_hashes(project)
            initial_video_calls = len(smart_remake_stack.calls("video"))
            initial_image_calls = len(smart_remake_stack.calls("image"))
            assert initial_video_calls - call_baseline["video"] == (1 if duration == 8 else 2)
            await page.get_by_label("Căn cứ xem xét quyền", exact=True).fill(
                "Reviewed original local FFmpeg/Pillow generators and fixture rights manifest."
            )
            async with page.expect_response(
                lambda response: response.url.endswith("/rights/reviews")
            ) as rights:
                await page.get_by_role("button", name="Lưu xem xét quyền", exact=True).click()
            assert (await rights.value).status == 200
            starts = [5, 1] if duration == 8 else [1, 2, 3, 4]
            await journey.choose_ranges(starts)
            project = await journey.compose(duration)
            first_assembly = project["assemblies"]["activeAssemblyId"]
            first_revision = next(
                record["revision"]
                for record in project["assemblies"]["records"]
                if record["id"] == first_assembly
            )
            if case == "pass":
                # A second real compose gives the history control a retained,
                # inactive assembly to restore without another provider call.
                project = await journey.compose(duration)
            assert len(smart_remake_stack.calls("video")) == initial_video_calls
            assert len(smart_remake_stack.calls("image")) == initial_image_calls
            assert not project.get("downloadUrl"), "Private preview must not expose export bypass"
            smart_remake_stack.scenario(inspectionFailure=case == "repair")
            scene_report = await journey.inspect_scene()
            await assert_evidence_modal(journey, scene_report, clocks=("raw_group",))
            await assert_scene_local_evidence(journey, scene_report)
            report = await journey.inspect_assembly()
            await assert_evidence_modal(journey, report)
            if case == "repair":
                assert report["status"] == "failed"
                await retain_browser_capture(journey, "repair-first-pass")
                await repair_first_scene(journey, original_hashes)
                await journey.choose_ranges(starts, indexes=[0])
                await assert_scene_local_evidence(journey, scene_report)
                project = await journey.compose(duration)
                assert project["assemblies"]["activeAssemblyId"] != first_assembly
                report = await journey.inspect_assembly()
                assert len(smart_remake_stack.calls("video")) == initial_video_calls + 1
                assert len(smart_remake_stack.calls("image")) == initial_image_calls
            assert report["status"] == "needs_review", "Sampled semantics require human review"
            await journey.review_semantics(report)
            await journey.refresh_ui()
            async with page.expect_response(
                lambda response: response.url.endswith("/approvals")
            ) as approved:
                await page.get_by_role(
                    "button", name="Duyệt nội dung bản ghép này", exact=True
                ).click()
            assert (await approved.value).status == 200
            async with page.expect_response(
                lambda response: response.url.endswith("/exports")
            ) as exported:
                await page.get_by_role("button", name="Tải bản có nhãn AI", exact=True).click()
            response = await exported.value
            assert response.status == 200
            export = (await response.json())["data"]
            media = await journey.fetch_export(export)
            check = probe_timeline_media(media)
            assert check["decodedFrameCount"] == duration * 24 and check["fps"] == 24
            assert export["technicalCheck"]["labelVerification"]["verified"] is True
            assert export["technicalCheck"]["label"] == "AI-generated"
            export_path = smart_remake_stack.root / f"{case}-checked-export.mp4"
            export_path.write_bytes(media)
            assert_export_pixels_and_audio(export_path, duration)
            await retain_browser_capture(journey, f"{case}-approved")
            await journey.assert_reload_is_read_only()
            project = await journey.project()
            before_restore = len(smart_remake_stack.calls())
            await page.get_by_text("Lịch sử bản ghép", exact=True).click()
            entry = page.get_by_role("listitem").filter(
                has=page.get_by_text(f"Bản ghép v{first_revision}", exact=True)
            )
            async with page.expect_response(
                lambda response: response.request.method == "POST"
                and response.url.endswith("/restore")
            ) as restore:
                await entry.get_by_role("button", name="Khôi phục bản ghép", exact=True).click()
            assert (await restore.value).status == 200
            restored = await journey.project()
            assert restored["assemblies"]["activeAssemblyId"] != first_assembly
            assert not restored["release"].get("activeApprovalId")
            assert len(smart_remake_stack.calls()) == before_restore
            await journey.mutate(
                "exports",
                {
                    "assemblyId": export["assemblyId"],
                    "approvalId": export["approvalId"],
                },
                status=409,
            )
            await journey.refresh_ui()
            await journey.assert_reload_is_read_only()
            for width in (390, 768, 1280, 1440):
                await page.set_viewport_size({"width": width, "height": 1000})
                assert await page.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth"
                ), width
                await page.screenshot(
                    path=str(smart_remake_stack.root / f"{case}-result-{width}.png"), full_page=True
                )
            assert await page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")
            await page.get_by_role("button", name="Làm mới dự án", exact=True).focus()
            await page.keyboard.press("Tab")
            assert await page.evaluate("document.activeElement !== document.body")
            await page.evaluate("document.documentElement.style.zoom = '2'")
            assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            await page.screenshot(
                path=str(smart_remake_stack.root / f"{case}-result-css-zoom-200.png"),
                full_page=True,
            )
            await page.evaluate("document.documentElement.style.zoom = ''")
            await assert_native_result_zoom(playwright, journey, case)
            (smart_remake_stack.root / f"{case}-result-browser-checks.json").write_text(
                json.dumps(
                    {
                        "mode": "mock",
                        "screen": "result",
                        "widths": [390, 768, 1280, 1440],
                        "keyboard": True,
                        "reducedMotion": True,
                        "cssZoomPercent": 200,
                        "nativeBrowserZoom": 200,
                    },
                    indent=2,
                )
            )
            assert not errors, errors
        finally:
            if journey.project_id:
                try:
                    await retain_browser_capture(journey, case)
                except Exception as exc:
                    (smart_remake_stack.root / f"{case}-capture-error.txt").write_text(
                        type(exc).__name__
                    )
            await page.screenshot(
                path=str(smart_remake_stack.root / f"{case}-last-screen.png"), full_page=True
            )
            await context.tracing.stop(path=str(smart_remake_stack.root / f"{case}-trace.zip"))
            await context.close()
            await browser.close()


async def repair_first_scene(journey, original_hashes):
    page, stack = journey.page, journey.stack
    before = await journey.project()
    scene = before["scenes"][0]
    stack.scenario(inspectionFailure=False, repair=True)
    await (
        page.get_by_role("region", name="Kết quả Smart Remake", exact=True)
        .get_by_role("button")
        .filter(has=page.get_by_text("Cảnh 1", exact=True))
        .click()
    )
    await page.get_by_role("button", name="Sửa và tạo lại cảnh", exact=True).click()
    await page.get_by_label("Yêu cầu tạo video", exact=True).fill(
        "Keep the orange box product visible and preserve the source action."
    )
    async with page.expect_response(
        lambda response: response.url.endswith("/repairs")
    ) as submitted:
        await page.get_by_role("button", name="Tạo lại cảnh 1", exact=True).click()
    assert (await submitted.value).status == 200
    project = await journey.wait_idle()
    assert journey.scene_hashes(project) == original_hashes, "Candidate must remain inactive"
    await journey.refresh_ui()
    await (
        page.get_by_role("group", name="Công cụ cảnh", exact=True)
        .get_by_role("button", name="Lịch sử", exact=True)
        .click()
    )
    await page.get_by_role("button", name="So sánh bản này", exact=True).click()
    await assert_comparison_playback(journey, before, project)
    async with page.expect_response(
        lambda response: response.request.method == "POST" and response.url.endswith("/accept")
    ) as accepted:
        await page.get_by_role("button", name="Dùng bản này", exact=True).click()
    assert (await accepted.value).status == 200
    project = await journey.wait_idle()
    current = journey.scene_hashes(project)
    assert current[scene["id"]] != original_hashes[scene["id"]]
    for sibling in before["scenes"][1:]:
        assert current[sibling["id"]] == original_hashes[sibling["id"]]


async def assert_comparison_playback(journey, before, candidate_project):
    page = journey.page
    current_start = before["draftTimeline"]["items"][0]["inFrame"] / 24
    candidate = candidate_project["scenes"][0]["versions"][-1]
    candidate_start = candidate.get("suggestedInFrame", 0) / 24
    players = ["Video Clip AI · 8 giây · Cảnh 1", "Video Bản mới"]
    await page.wait_for_function(
        """labels => labels.every(label => {
        const video = [...document.querySelectorAll('video')].find(v => v.ariaLabel === label);
        return video && video.readyState >= 2 && !video.error;
    })""",
        arg=players,
    )
    output = page.get_by_role("region", name="Kết quả Smart Remake", exact=True)
    await output.get_by_role("button", name="Phát video", exact=True).click()
    await page.wait_for_function(
        """({labels, starts}) => {
        const videos = labels.map(label => [...document.querySelectorAll('video')]
            .find(v => v.ariaLabel === label));
        return videos.every(v => v && !v.paused)
            && videos.filter(v => !v.muted && v.volume > 0).length === 1
            && Math.abs((videos[0].currentTime-starts[0])-(videos[1].currentTime-starts[1])) < 0.08;
    }""",
        arg={"labels": players, "starts": [current_start, candidate_start]},
    )
    await page.screenshot(path=str(journey.stack.root / "repair-comparison.png"))
    await output.get_by_role("button", name="Tạm dừng video", exact=True).click()


async def assert_evidence_modal(journey, report, *, clocks=("source", "final")):
    page = journey.page
    names = {"source": "Video mẫu", "raw_group": "Clip AI gốc", "final": "Video đã ghép"}
    for clock in clocks:
        evidence = next(
            item
            for finding in report["findings"]
            for item in finding["evidence"]
            if item.get("timebase") == clock
        )
        label = (
            f"Xem bằng chứng · {names[clock]} · frame "
            f"{evidence['inFrame']}–{evidence['outFrame']}"
        )
        trigger = page.get_by_role("button", name=label, exact=True).first
        await trigger.click()
        dialog = page.get_by_role("dialog", name="Bằng chứng kiểm tra", exact=True)
        await dialog.wait_for()
        video = dialog.get_by_label("Video Bằng chứng", exact=True)
        await video.wait_for()
        await page.wait_for_function(
            """start => {
            const video = document.querySelector('[role=dialog] video');
            return video && video.readyState >= 2 && Math.abs(video.currentTime-start) < 1/24;
        }""",
            arg=evidence["inFrame"] / 24,
        )
        media_url = await video.evaluate("element => element.currentSrc")
        response = await page.context.request.get(media_url)
        assert response.status == 200
        assert hashlib.sha256(await response.body()).hexdigest() == evidence["mediaHash"]
        authorized = (await journey.project())["inspectionMedia"]
        assert any(
            item["mediaId"] == evidence["mediaId"]
            and item["mediaHash"] == evidence["mediaHash"]
            and item["timebase"] == clock
            for item in authorized
        ), "Evidence must resolve to the exact server-authorized media clock and hash"
        play = dialog.get_by_role("button", name="Phát video", exact=True)
        if evidence["outFrame"] - evidence["inFrame"] == 1:
            assert await play.is_disabled(), "A single-frame observation must remain static"
            assert await dialog.get_by_text("Một frame được chọn", exact=True).is_visible()
            assert await video.evaluate("element => element.paused")
        else:
            await play.click()
            await page.wait_for_function(
                """end => {
                const video = document.querySelector('[role=dialog] video');
                return video?.paused && video.currentTime < end
                    && Math.abs(video.currentTime-(end-1/24)) < 0.001;
            }""",
                arg=evidence["outFrame"] / 24,
            )
        await page.keyboard.press("Escape")
        await dialog.wait_for(state="hidden")
        assert await trigger.evaluate(
            "element => document.activeElement === element"
        ), "Closing evidence must restore keyboard focus"


async def assert_scene_local_evidence(journey, report):
    """Use the server's frozen edit mapping, including an older report after repair."""
    page = journey.page
    project = await journey.project()
    mapping = next(
        item
        for item in project["inspectionMappings"]
        if item.get("reportId") == report["id"]
        and item["from"]["timebase"] == "scene_local"
        and item["to"]["timebase"] == "raw_group"
        and item["to"]["mediaId"] == "subject"
        and item["to"]["inFrame"] > 0
    )
    local, raw = mapping["from"], mapping["to"]
    assert local["inFrame"] == 0 and local["mediaHash"] == raw["mediaHash"]
    assert local["outFrame"] - local["inFrame"] == raw["outFrame"] - raw["inFrame"]
    for key in ("contextHash", "manifestHash"):
        assert mapping[key] == report[key]
    for key in ("sceneId", "versionId"):
        assert mapping[key] == report["subject"][key]
    virtual = next(
        item
        for item in project["inspectionMedia"]
        if item["mediaId"] == local["mediaId"]
        and item["mediaHash"] == local["mediaHash"]
        and item["timebase"] == "scene_local"
    )
    assert virtual["playbackMediaId"] == raw["mediaId"]
    assert virtual["playbackMediaHash"] == raw["mediaHash"]
    assert virtual["playbackTimebase"] == "raw_group"
    article = page.get_by_role("article").filter(
        has=page.locator(f'time[datetime="{report["checkedAt"]}"]')
    )
    trigger = article.get_by_role(
        "button", name=f"Trong cảnh · frame {local['inFrame']}–{local['outFrame']}", exact=True
    ).first
    await trigger.click()
    dialog = page.get_by_role("dialog", name="Bằng chứng kiểm tra", exact=True)
    await dialog.wait_for()
    video = dialog.get_by_label("Video Bằng chứng", exact=True)
    await page.wait_for_function(
        """start => {
        const video = document.querySelector('[role=dialog] video');
        return video?.readyState >= 2 && video.paused && Math.abs(video.currentTime-start) < 1/24;
    }""",
        arg=raw["inFrame"] / 24,
    )
    response = await page.context.request.get(await video.evaluate("element => element.currentSrc"))
    assert response.status == 200
    assert hashlib.sha256(await response.body()).hexdigest() == raw["mediaHash"]
    await page.screenshot(path=str(journey.stack.root / f"scene-local-{report['id']}.png"))
    (journey.stack.root / f"scene-local-{report['id']}.json").write_text(
        json.dumps(
            {
                "mode": "mock",
                "mapping": mapping,
                "observedRawSecond": await video.evaluate("element => element.currentTime"),
            },
            indent=2,
        )
    )
    await page.keyboard.press("Escape")
    await dialog.wait_for(state="hidden")
    assert await trigger.evaluate("element => document.activeElement === element")


@pytest.mark.asyncio
async def test_smart_remake_unknown_video_receipt_reload_and_restart_never_resubmit(
    smart_remake_stack,
):
    import asyncio
    import time

    from playwright.async_api import async_playwright

    smart_remake_stack.scenario(
        name="unknown",
        repair=False,
        inspectionFailure=False,
        unknownVideoReceipt=True,
        downloadFailure=False,
    )
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        journey = SmartRemakeJourney(page, smart_remake_stack)
        await context.tracing.start(screenshots=True, snapshots=True)
        try:
            await register(page, smart_remake_stack.base_url)
            await journey.workspace()
            await journey.fill_prepare(8)
            await journey.analyze(8)
            before = len(smart_remake_stack.calls("video"))
            await page.get_by_role("button", name="Tạo video · 8 giây", exact=True).click()
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                project = await journey.project()
                pending = project.get("pendingOperation") or {}
                if pending.get("needsReconciliation"):
                    break
                await asyncio.sleep(0.2)
            else:
                raise AssertionError("Unknown provider receipt did not reach reconciliation state")
            assert len(smart_remake_stack.calls("video")) == before + 1
            assert project["budget"]["actualUsd"] is None
            assert project["budget"]["unknownAttemptCount"] >= 1
            calls = smart_remake_stack.calls()
            await journey.assert_reload_is_read_only()
            smart_remake_stack.stop("worker")
            smart_remake_stack.start_worker()
            await journey.assert_reload_is_read_only()
            assert smart_remake_stack.calls() == calls
        finally:
            if journey.project_id:
                await retain_browser_capture(journey, "unknown-receipt")
            await page.screenshot(
                path=str(smart_remake_stack.root / "unknown-receipt.png"), full_page=True
            )
            await context.tracing.stop(
                path=str(smart_remake_stack.root / "unknown-receipt-trace.zip")
            )
            await context.close()
            await browser.close()


@pytest.mark.asyncio
async def test_smart_remake_missing_rights_and_exhausted_budget_fail_before_provider(
    smart_remake_stack,
):
    from playwright.async_api import async_playwright

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        journey = SmartRemakeJourney(page, smart_remake_stack)
        await register(page, smart_remake_stack.base_url)
        await journey.workspace()
        before = len(smart_remake_stack.calls())
        for declared, cap, expected in (
            (False, "10.00", "SMART_REMAKE_RIGHTS_REQUIRED"),
            (True, "0.001", "SMART_REMAKE_BUDGET_EXCEEDED"),
        ):
            project = await journey.create_intake(declared=declared, cap=cap)
            assert project["phase"] == "intake" and len(smart_remake_stack.calls()) == before
            response = await context.request.post(
                f"{journey.root}/compile",
                headers={"Origin": smart_remake_stack.base_url},
                multipart={
                    "timelineMode": "reference",
                    "mode": "smart_remake",
                    "projectId": journey.project_id,
                    "expectedRevision": str(project["revision"]),
                    "idempotencyKey": secrets.token_hex(12),
                    "targetDuration": "8",
                    "aspectRatio": "9:16",
                },
            )
            assert response.status in (403, 429)
            assert (await response.json())["error"]["code"] == expected
            assert len(smart_remake_stack.calls()) == before, (
                "Backend must reject before provider boundary"
            )
        await context.close()
        await browser.close()


async def register(page, base_url):
    await page.goto(f"{base_url}/register?returnTo=%2Fsmart-remake")
    await page.get_by_label("Họ và tên", exact=True).fill("P0 Offline Seller")
    await page.get_by_label("Email", exact=True).fill(f"p0-{secrets.token_hex(6)}@example.com")
    password = secrets.token_urlsafe(24)
    await page.get_by_label("Mật khẩu", exact=True).fill(password)
    await page.get_by_label("Xác nhận mật khẩu", exact=True).fill(password)
    await page.get_by_role("button", name="Tạo tài khoản", exact=True).click()
    await page.wait_for_url("**/smart-remake", timeout=30000)
    await page.get_by_role("heading", name="Tạo video cho sản phẩm của bạn", exact=True).wait_for()
