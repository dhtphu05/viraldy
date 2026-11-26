"""Native Chromium tab zoom on the actual authenticated Result screen."""

from __future__ import annotations

import base64
import json
from typing import Any


async def assert_native_result_zoom(playwright: Any, journey: Any, case: str) -> None:
    root = journey.stack.root / f"native-zoom-{case}"
    extension = root / "extension"
    extension.mkdir(parents=True)
    (extension / "manifest.json").write_text(
        json.dumps(
            {
                "manifest_version": 3,
                "name": "Local P0 native zoom",
                "version": "1.0",
                "permissions": ["tabs"],
                "host_permissions": ["http://127.0.0.1/*"],
                "background": {"service_worker": "worker.js"},
            }
        )
    )
    (extension / "worker.js").write_text("chrome.runtime.onInstalled.addListener(()=>{});")
    state = await journey.page.context.storage_state()
    context = await playwright.chromium.launch_persistent_context(
        str(root / "profile"),
        executable_path=playwright.chromium.executable_path,
        headless=True,
        no_viewport=True,
        reduced_motion="reduce",
        ignore_default_args=["--disable-extensions"],
        args=[
            "--window-size=1280,900",
            "--disable-features=DisableLoadExtensionCommandLineSwitch",
            f"--disable-extensions-except={extension}",
            f"--load-extension={extension}",
        ],
    )
    try:
        await context.add_cookies(state["cookies"])
        await context.add_init_script(
            "for (const origin of "
            + json.dumps(state["origins"])
            + ") if (location.origin === origin.origin) "
            + "for (const item of origin.localStorage) localStorage.setItem(item.name,item.value);"
        )
        worker = (
            context.service_workers[0]
            if context.service_workers
            else await context.wait_for_event("serviceworker")
        )
        page = await context.new_page()
        await page.goto(journey.page.url)
        await page.get_by_role("region", name="Kết quả Smart Remake", exact=True).wait_for()
        measure = """() => ({inner:innerWidth,outer:outerWidth,dpr:devicePixelRatio,
            scale:visualViewport.scale,cssZoom:getComputedStyle(document.documentElement).zoom,
            scroll:document.documentElement.scrollWidth})"""
        before = await page.evaluate(measure)
        zoom = await worker.evaluate(
            """async origin => {
                const tab = (await chrome.tabs.query({})).find(t => t.url?.startsWith(origin));
                await chrome.tabs.setZoom(tab.id,2);
                return await chrome.tabs.getZoom(tab.id);
            }""",
            journey.stack.base_url,
        )
        await page.wait_for_function("before => innerWidth <= before/2+1", arg=before["inner"])
        after = await page.evaluate(measure)
        assert zoom == 2 and after["outer"] == before["outer"]
        assert after["dpr"] == before["dpr"] * 2 and after["scale"] == 1
        assert after["cssZoom"] == "1" and after["scroll"] <= after["inner"]
        await page.get_by_role(
            "heading", name="Xem & ghép video", exact=True
        ).scroll_into_view_if_needed()
        await page.evaluate(
            "new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
        )
        # Playwright supplies a CSS-pixel clip that crops the physical viewport
        # at native tab zoom. CDP without a clip retains the actual device pixels.
        client = await context.new_cdp_session(page)
        screenshot = await client.send(
            "Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False}
        )
        (root / "result-native-200.png").write_bytes(base64.b64decode(screenshot["data"]))
        await page.reload()
        await page.get_by_role("region", name="Kết quả Smart Remake", exact=True).wait_for()
        reloaded = await page.evaluate(measure)
        assert reloaded["inner"] == after["inner"] and reloaded["scroll"] <= reloaded["inner"]
        (root / "result-native-zoom.json").write_text(
            json.dumps(
                {
                    "mode": "mock",
                    "nativeZoom": zoom,
                    "before": before,
                    "after": after,
                    "reloaded": reloaded,
                },
                indent=2,
            )
        )
    finally:
        await context.close()
