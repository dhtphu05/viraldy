from __future__ import annotations

import os
import secrets
import tempfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_RELEASE_BROWSER_TESTS") != "1",
    reason="Opt-in test requires a running clean-checkout frontend and native-auth backend.",
)


@pytest.mark.asyncio
async def test_image_discovery_handoff_without_optional_local_assets() -> None:
    from playwright.async_api import async_playwright

    base = os.getenv("AUTH_BROWSER_BASE_URL", "http://127.0.0.1:8081").rstrip("/")
    media = Path(__file__).resolve().parents[3] / "web/public/demo-media"
    screenshots = Path(tempfile.mkdtemp(prefix="viraldy-release-browser-"))
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 1000})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto(f"{base}/register?returnTo=%2Fcreative-library")
        password = secrets.token_urlsafe(24)
        await page.get_by_label("Full name", exact=True).fill("Release Seller")
        await page.get_by_label("Email", exact=True).fill(
            f"release-{secrets.token_hex(6)}@example.com"
        )
        await page.get_by_label("Password", exact=True).fill(password)
        await page.get_by_label("Confirm password", exact=True).fill(password)
        await page.get_by_role("button", name="Create account", exact=True).click()
        await page.wait_for_url("**/creative-library", timeout=20000)
        await page.wait_for_load_state("networkidle")
        await page.get_by_label("Tải ảnh sản phẩm lên", exact=True).set_input_files(
            [str(media / "sofa-cover-product.jpg"), str(media / "pet_hair_roller.jpg")]
        )
        choose = page.get_by_role("button", name="Dùng video này")
        try:
            await choose.first.wait_for(timeout=20000)
        except Exception:
            await page.screenshot(path=str(screenshots / "discovery-failure.png"))
            raise AssertionError(
                f"Discovery did not return results. Browser errors: {errors}; "
                f"visible content: {(await page.locator('body').inner_text())[-2500:]}"
            ) from None
        assert await choose.count() >= 5
        await page.wait_for_function(
            """() => [...document.querySelectorAll('article video')].some(
                video => video.readyState >= 2 && !video.error
                    && video.currentSrc.includes('/demo-media/'))"""
        )
        await page.screenshot(
            path=os.getenv("RELEASE_DESKTOP_SCREENSHOT", str(screenshots / "desktop.png"))
        )
        await choose.first.click()
        await page.wait_for_url("**/smart-remake", timeout=20000)
        await page.get_by_alt_text("Ảnh sản phẩm 1", exact=True).wait_for()
        await page.get_by_alt_text("Ảnh sản phẩm 2", exact=True).wait_for()
        await page.get_by_role("button", name="Phân tích video", exact=True).click()
        await page.get_by_text("Prompt tạo video", exact=True).wait_for(timeout=30000)
        assert await page.locator("pre").first.inner_text()
        await page.get_by_role("button", name="Tạo video 8 giây", exact=True).click()
        await page.get_by_text(
            "Video mẫu chưa có trên máy này. Hãy cấu hình dịch vụ tạo video để tiếp tục.",
            exact=True,
        ).first.wait_for(timeout=15000)
        for width in (768, 375):
            await page.set_viewport_size({"width": width, "height": 844})
            assert await page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        await page.screenshot(
            path=os.getenv("RELEASE_MOBILE_SCREENSHOT", str(screenshots / "mobile.png"))
        )
        assert not errors, errors
        await browser.close()
