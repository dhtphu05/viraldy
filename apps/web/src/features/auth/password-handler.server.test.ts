import { beforeEach, describe, expect, it, vi } from "vitest";

const authenticate = vi.hoisted(() => vi.fn());
vi.mock("./auth-session.server", () => ({
    authenticatePassword: authenticate,
    PasswordSignInError: class extends Error {},
}));
import { passwordAuthResponse } from "./password-handler.server";

beforeEach(() => vi.clearAllMocks());

describe("password form CSRF and response boundary", () => {
    it.each([undefined, "https://evil.example"])(
        "rejects missing or foreign Origin %s",
        async (origin) => {
            const response = await passwordAuthResponse(
                new Request("https://app.example/api/auth/login", {
                    method: "POST",
                    headers: origin ? { Origin: origin } : {},
                }),
                "login",
            );
            expect(response.status).toBe(403);
            expect(authenticate).not.toHaveBeenCalled();
        },
    );

    it("returns only session state and a safe destination to JavaScript", async () => {
        authenticate.mockResolvedValueOnce("/account");
        const response = await passwordAuthResponse(
            new Request("https://app.example/api/auth/login", {
                method: "POST",
                headers: { Origin: "https://app.example", "Content-Type": "application/json" },
            }),
            "login",
        );
        expect(await response.json()).toEqual({ authenticated: true, returnTo: "/account" });
        expect(response.headers.get("cache-control")).toBe("no-store");
    });

    it("redirects a successful native HTML form without requiring hydration", async () => {
        authenticate.mockResolvedValueOnce("/account");
        const response = await passwordAuthResponse(
            new Request("https://app.example/api/auth/register", {
                method: "POST",
                headers: {
                    Origin: "https://app.example",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            }),
            "signup",
        );
        expect(response.status).toBe(303);
        expect(response.headers.get("location")).toBe("https://app.example/account");
    });
});
