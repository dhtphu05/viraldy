from __future__ import annotations

import os
import secrets

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_AUTH_BROWSER_TESTS") != "1",
    reason="Opt-in test requires a running native-auth backend and frontend.",
)


@pytest.mark.asyncio
async def test_register_login_refresh_logout_in_browser() -> None:
    from playwright.async_api import async_playwright

    base = os.getenv("AUTH_BROWSER_BASE_URL", "http://127.0.0.1:8081").rstrip("/")
    api = os.getenv("AUTH_BROWSER_API_URL", "http://127.0.0.1:8000").rstrip("/")
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 1000})
        page = await context.new_page()
        email = f"auth-browser-{secrets.token_hex(6)}@example.com"
        password = secrets.token_urlsafe(24)
        await page.goto(f"{base}/")
        await page.wait_for_url("**/login", timeout=20000)
        assert await page.title() == "Đăng nhập — Viraldy"
        await page.goto(f"{base}/register?returnTo=%2Faccount")
        await page.get_by_label("Họ và tên", exact=True).fill("Live Auth Check")
        await page.get_by_label("Email", exact=True).fill(email)
        await page.get_by_label("Mật khẩu", exact=True).fill(password)
        await page.get_by_label("Xác nhận mật khẩu", exact=True).fill(password)
        await page.get_by_role("button", name="Tạo tài khoản", exact=True).click()
        await page.wait_for_url("**/account", timeout=20000)
        cookies = [
            cookie
            for cookie in await context.cookies()
            if "viraldy_access" in cookie["name"] or "viraldy_refresh" in cookie["name"]
        ]
        assert len(cookies) == 2
        assert all(cookie["httpOnly"] for cookie in cookies)
        refresh_status = await page.evaluate("""async () =>
            (await fetch('/api/auth/refresh', {method: 'POST'})).status
        """)
        assert refresh_status == 200
        profile = await context.request.get(f"{base}/api/backend/me")
        assert profile.status == 200
        assert (await profile.json())["data"]["email"] == email
        old_access = next(
            cookie["value"]
            for cookie in await context.cookies()
            if "viraldy_access" in cookie["name"]
        )
        await page.get_by_role("button", name="Sign out", exact=True).click()
        await page.wait_for_url("**/login?loggedOut=1", timeout=15000)
        rejected = await context.request.get(
            f"{api}/api/v1/me", headers={"Authorization": f"Bearer {old_access}"}
        )
        assert rejected.status == 401
        await page.get_by_label("Email", exact=True).fill(email)
        await page.get_by_label("Mật khẩu", exact=True).fill("incorrect-password")
        await page.get_by_role("button", name="Đăng nhập", exact=True).click()
        await page.get_by_role("alert").wait_for()
        await page.get_by_label("Email", exact=True).fill(email)
        await page.get_by_label("Mật khẩu", exact=True).fill(password)
        await page.get_by_role("button", name="Đăng nhập", exact=True).click()
        await page.wait_for_url("**/dashboard", timeout=20000)
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.goto(f"{base}/account")
        await page.get_by_role("button", name="Sign out", exact=True).click()
        await page.wait_for_url("**/login?loggedOut=1", timeout=15000)
        assert await page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        await page.get_by_label("Email", exact=True).fill(email)
        await page.get_by_label("Mật khẩu", exact=True).fill(password)
        await page.get_by_role("button", name="Đăng nhập", exact=True).click()
        await page.wait_for_url("**/dashboard", timeout=20000)
        await browser.close()
