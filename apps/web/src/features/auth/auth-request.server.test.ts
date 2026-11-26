import { afterEach, describe, expect, it, vi } from "vitest";

import { authRequestUrl } from "./auth-request.server";

afterEach(() => vi.unstubAllEnvs());

describe("public authentication origin", () => {
    it("uses the configured HTTPS origin behind an HTTP reverse proxy", () => {
        vi.stubEnv("AUTH_PUBLIC_ORIGIN", "https://app.example");
        const url = authRequestUrl(new Request("http://internal:3000/api/auth/callback?code=abc"));
        expect(url.toString()).toBe("https://app.example/api/auth/callback?code=abc");
    });

    it("preserves the local request origin when no override is configured", () => {
        vi.stubEnv("AUTH_PUBLIC_ORIGIN", "");
        expect(authRequestUrl(new Request("http://127.0.0.1:8081/login")).origin).toBe(
            "http://127.0.0.1:8081",
        );
    });

    it.each(["https://app.example/path", "https://user:pass@app.example", "file:///tmp"])(
        "rejects an invalid configured origin %s",
        (origin) => {
            vi.stubEnv("AUTH_PUBLIC_ORIGIN", origin);
            expect(() => authRequestUrl(new Request("http://internal/login"))).toThrow();
        },
    );

    it("rejects an insecure production origin", () => {
        vi.stubEnv("AUTH_PUBLIC_ORIGIN", "http://app.example");
        vi.stubEnv("NODE_ENV", "production");
        expect(() => authRequestUrl(new Request("http://internal/login"))).toThrow();
    });

    it("requires a canonical public origin in production", () => {
        vi.stubEnv("AUTH_PUBLIC_ORIGIN", "");
        vi.stubEnv("NODE_ENV", "production");
        expect(() => authRequestUrl(new Request("http://internal/login"))).toThrow(
            "AUTH_PUBLIC_ORIGIN",
        );
    });
});
