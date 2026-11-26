import { createElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { AuthPage } from "../components/auth-page";
import type { AuthSnapshot } from "../auth-session";
import { authPagePresentation, passwordAuthErrorMessage } from "./auth-presentation";

vi.mock("@tanstack/react-router", () => ({
    Link: ({ to, children }: { to: string; children: ReactNode }) =>
        createElement("a", { href: to }, children),
}));

describe("authPagePresentation", () => {
    it("offers native email and password sign in and registration", () => {
        expect(authPagePresentation("password", "login")).toMatchObject({
            title: "Đăng nhập vào Viraldy",
            ctaLabel: "Đăng nhập",
            showDevAccount: false,
        });
        expect(authPagePresentation("password", "signup")).toMatchObject({
            title: "Tạo tài khoản Viraldy",
            ctaLabel: "Tạo tài khoản",
            showDevAccount: false,
        });
        expect(authPagePresentation("password", "signup").description).not.toMatch(
            /điện thoại|nhà cung cấp/i,
        );
    });

    it("presents a ready-to-use development account on sign in", () => {
        expect(authPagePresentation("local_test", "login")).toMatchObject({
            eyebrow: "Truy cập thử nghiệm",
            title: "Đăng nhập vào Viraldy",
            ctaLabel: "Đăng nhập bằng tài khoản thử nghiệm",
            showDevAccount: true,
        });
    });

    it("makes development sign up distinct and explicit", () => {
        expect(authPagePresentation("local_test", "signup")).toMatchObject({
            eyebrow: "Thiết lập thử nghiệm",
            title: "Tạo tài khoản thử nghiệm",
            ctaLabel: "Tạo tài khoản thử nghiệm và tiếp tục",
            showDevAccount: true,
        });
    });

    it("keeps production sign in and sign up provider-driven", () => {
        expect(authPagePresentation("oidc", "login")).toMatchObject({
            title: "Chào mừng bạn trở lại",
            ctaLabel: "Tiếp tục đăng nhập an toàn",
            showDevAccount: false,
        });
        expect(authPagePresentation("oidc", "signup")).toMatchObject({
            title: "Tạo tài khoản Viraldy",
            ctaLabel: "Tạo tài khoản an toàn",
            showDevAccount: false,
        });
        expect(authPagePresentation("oidc", "signup").description).not.toContain("điện thoại");
    });

    it("uses honest copy when authentication is unavailable", () => {
        expect(authPagePresentation("unavailable", "login")).toMatchObject({
            eyebrow: "Tạm thời không thể truy cập",
            title: "Tạm thời không thể đăng nhập",
            ctaLabel: "Không thể đăng nhập",
            showDevAccount: false,
        });
        expect(authPagePresentation("unavailable", "signup")).toMatchObject({
            title: "Tạm thời không thể tạo tài khoản",
            ctaLabel: "Không thể tạo tài khoản",
        });
    });
});

describe("password auth errors", () => {
    it.each([
        [401, /email hoặc mật khẩu/i],
        [409, /đã tồn tại/i],
        [422, /kiểm tra thông tin/i],
        [429, /quá nhiều lần/i],
        [503, /thử lại/i],
        [0, /kết nối/i],
    ])("gives a friendly explanation for HTTP status %s", (status, message) => {
        expect(passwordAuthErrorMessage(status)).toMatch(message);
    });
});

describe("native auth form markup", () => {
    function markup(
        intent: "login" | "signup",
        mode: AuthSnapshot["mode"] = "password",
        enabled = true,
        search: { returnTo?: string; error?: string; reason?: string; loggedOut?: string } = {},
    ) {
        return renderToStaticMarkup(
            createElement(AuthPage, {
                auth: { authenticated: false, user: null, mode, enabled, reason: null },
                intent,
                returnTo: "/account",
                ...search,
            }),
        );
    }

    it("renders Vietnamese labels and navigation on both forms", () => {
        const login = markup("login");
        expect(login).toContain('lang="vi"');
        expect(login).toContain("Đăng nhập vào Viraldy");
        expect(login).toContain("Mật khẩu");
        expect(login).toContain("Bạn mới sử dụng Viraldy?");
        expect(login).toContain("Tạo tài khoản");
        const signup = markup("signup");
        expect(signup).toContain("Họ và tên");
        expect(signup).toContain("Xác nhận mật khẩu");
        expect(signup).toContain("Bạn đã có tài khoản?");
        expect(signup).toContain("ít nhất 12 ký tự");
    });

    it.each([
        [{ reason: "session_expired" }, "Phiên đăng nhập đã hết hạn"],
        [{ loggedOut: "1" }, "Bạn đã đăng xuất"],
        [{ error: "unknown_error" }, "Không thể hoàn tất yêu cầu"],
        [{ error: "auth_unavailable" }, "Tạm thời không thể đăng nhập"],
        [{ error: "callback_failed" }, "Không thể hoàn tất đăng nhập"],
    ])("renders Vietnamese notices for %j", (search, message) => {
        expect(markup("login", "password", true, search)).toContain(message);
    });

    it("renders a POST login form with password-manager-compatible fields", () => {
        const html = markup("login");
        expect(html).toContain('method="post"');
        expect(html).toContain('action="/api/auth/login"');
        expect(html).toContain('name="email"');
        expect(html).toContain('type="email"');
        expect(html).toMatch(/autocomplete="username"/i);
        expect(html).toMatch(/autocomplete="current-password"/i);
        expect(html).not.toContain('name="display_name"');
        expect(html).not.toContain('name="confirmPassword"');
        expect(html).not.toContain("Mật khẩu của bạn được lưu tại nhà cung cấp danh tính");
    });

    it("renders registration with name and client-only password confirmation, without a phone", () => {
        const html = markup("signup");
        expect(html).toContain('method="post"');
        expect(html).toContain('action="/api/auth/register"');
        expect(html).toContain('name="display_name"');
        expect(html).toContain('name="confirmPassword"');
        expect(html.match(/autocomplete="new-password"/gi)).toHaveLength(2);
        expect(html.match(/maxlength="2048"/gi)).toHaveLength(2);
        expect(html).not.toContain('name="phone_number"');
    });

    it.each(["login", "signup"] as const)(
        "preserves the destination in the native %s POST",
        (intent) => {
            expect(markup(intent)).toMatch(/type="hidden" name="returnTo" value="\/account"/);
        },
    );

    it("sanitizes the native form destination before submitting it", () => {
        expect(markup("login", "password", true, { returnTo: "/\\evil.example" })).toMatch(
            /type="hidden" name="returnTo" value="\/dashboard"/,
        );
    });

    it.each([
        ["login", "invalid_credentials", /email hoặc mật khẩu không chính xác/i],
        ["signup", "signup_failed", /không thể tạo tài khoản/i],
    ] as const)("explains the native %s redirect error", (intent, error, message) => {
        expect(markup(intent, "password", true, { error })).toMatch(message);
    });

    it.each(["login", "signup"] as const)(
        "keeps native %s copy consistent with the available password API",
        (intent) => {
            expect(markup(intent)).not.toMatch(
                /đã xác minh|nhà cung cấp danh tính|đặt lại mật khẩu|quên mật khẩu/i,
            );
        },
    );

    it("disables native credentials when the auth service is unavailable", () => {
        expect(markup("login", "password", false)).toMatch(/<fieldset[^>]*disabled/);
    });

    it.each(["oidc", "local_test"] as const)("preserves the %s provider button", (mode) => {
        const html = markup("login", mode);
        expect(html).toContain('href="/api/auth/login?intent=login');
        expect(html).not.toContain('name="password"');
    });
});
