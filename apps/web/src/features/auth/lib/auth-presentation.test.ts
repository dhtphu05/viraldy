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
            title: "Sign in to Viraldy",
            ctaLabel: "Sign in",
            showDevAccount: false,
        });
        expect(authPagePresentation("password", "signup")).toMatchObject({
            title: "Create your Viraldy account",
            ctaLabel: "Create account",
            showDevAccount: false,
        });
        expect(authPagePresentation("password", "signup").description).not.toMatch(
            /phone|provider/i,
        );
    });

    it("presents a ready-to-use development account on sign in", () => {
        expect(authPagePresentation("local_test", "login")).toMatchObject({
            eyebrow: "Development access",
            title: "Sign in to Viraldy",
            ctaLabel: "Sign in with dev account",
            showDevAccount: true,
        });
    });

    it("makes development sign up distinct and explicit", () => {
        expect(authPagePresentation("local_test", "signup")).toMatchObject({
            eyebrow: "Development setup",
            title: "Create your dev account",
            ctaLabel: "Create dev account & continue",
            showDevAccount: true,
        });
    });

    it("keeps production sign in and sign up provider-driven", () => {
        expect(authPagePresentation("oidc", "login")).toMatchObject({
            title: "Welcome back",
            ctaLabel: "Continue to secure sign in",
            showDevAccount: false,
        });
        expect(authPagePresentation("oidc", "signup")).toMatchObject({
            title: "Create your Viraldy account",
            ctaLabel: "Create account securely",
            showDevAccount: false,
        });
        expect(authPagePresentation("oidc", "signup").description).not.toContain("phone");
    });

    it("uses honest copy when authentication is unavailable", () => {
        expect(authPagePresentation("unavailable", "login")).toMatchObject({
            eyebrow: "Access unavailable",
            title: "Sign in is temporarily unavailable",
            ctaLabel: "Sign in unavailable",
            showDevAccount: false,
        });
        expect(authPagePresentation("unavailable", "signup")).toMatchObject({
            title: "Account creation is temporarily unavailable",
            ctaLabel: "Account creation unavailable",
        });
    });
});

describe("password auth errors", () => {
    it.each([
        [401, /email or password/i],
        [409, /already exists/i],
        [422, /check your details/i],
        [429, /too many attempts/i],
        [503, /try again/i],
        [0, /connection/i],
    ])("gives a friendly explanation for HTTP status %s", (status, message) => {
        expect(passwordAuthErrorMessage(status)).toMatch(message);
    });
});

describe("native auth form markup", () => {
    function markup(
        intent: "login" | "signup",
        mode: AuthSnapshot["mode"] = "password",
        enabled = true,
        search: { returnTo?: string; error?: string } = {},
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
        expect(html).not.toContain("Your password stays with the identity provider");
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
        ["login", "invalid_credentials", /email or password is incorrect/i],
        ["signup", "signup_failed", /couldn(?:'|&#x27;)t create your account/i],
    ] as const)("explains the native %s redirect error", (intent, error, message) => {
        expect(markup(intent, "password", true, { error })).toMatch(message);
    });

    it.each(["login", "signup"] as const)(
        "keeps native %s copy consistent with the available password API",
        (intent) => {
            expect(markup(intent)).not.toMatch(
                /verified|identity provider|reset password|forgot password/i,
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
