import { describe, expect, it } from "vitest";

import {
    buildAuthorizationUrl,
    parseTokenResponse,
    pkceChallenge,
    sanitizeReturnTo,
} from "./auth-flow";

const oidcConfig = {
    authorization_url: "https://identity.example.com/authorize",
    token_url: "https://identity.example.com/oauth/token",
    client_id: "viraldy-web",
    scopes: ["openid", "profile", "email", "phone", "offline_access"],
    registration_url: null,
};

describe("sanitizeReturnTo", () => {
    it("keeps an internal application path", () => {
        expect(sanitizeReturnTo("/products?tab=active#catalog")).toBe(
            "/products?tab=active#catalog",
        );
    });

    it.each([
        "https://evil.example/steal",
        "//evil.example/steal",
        "javascript:alert(1)",
        "/api/auth/login",
        "/login",
        "/register",
        "dashboard",
        "",
    ])("falls back for unsafe or looping target %s", (value) => {
        expect(sanitizeReturnTo(value)).toBe("/dashboard");
    });
});

describe("OIDC Authorization Code + PKCE", () => {
    it("matches the RFC 7636 S256 example", async () => {
        await expect(pkceChallenge("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk")).resolves.toBe(
            "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
        );
    });

    it("builds a login request with identity scopes and no token in the URL", () => {
        const url = new URL(
            buildAuthorizationUrl({
                config: oidcConfig,
                callbackUrl: "https://app.viraldy.com/api/auth/callback",
                state: "csrf-state",
                codeChallenge: "pkce-challenge",
                intent: "login",
            }),
        );

        expect(url.origin + url.pathname).toBe(oidcConfig.authorization_url);
        expect(url.searchParams.get("response_type")).toBe("code");
        expect(url.searchParams.get("client_id")).toBe("viraldy-web");
        expect(url.searchParams.get("scope")).toBe("openid profile email phone offline_access");
        expect(url.searchParams.get("state")).toBe("csrf-state");
        expect(url.searchParams.get("code_challenge_method")).toBe("S256");
        expect(url.searchParams.get("code_challenge")).toBe("pkce-challenge");
        expect(url.search).not.toContain("access_token");
    });

    it("requests account creation for the registration journey", () => {
        const url = new URL(
            buildAuthorizationUrl({
                config: oidcConfig,
                callbackUrl: "https://app.viraldy.com/api/auth/callback",
                state: "csrf-state",
                codeChallenge: "pkce-challenge",
                intent: "signup",
            }),
        );

        expect(url.searchParams.get("prompt")).toBe("create");
    });
});

describe("parseTokenResponse", () => {
    it("accepts a bearer token response without exposing extra provider fields", () => {
        expect(
            parseTokenResponse({
                access_token: "access-token",
                refresh_token: "refresh-token",
                token_type: "Bearer",
                expires_in: 900,
                provider_debug: "must not escape",
            }),
        ).toEqual({
            accessToken: "access-token",
            refreshToken: "refresh-token",
            expiresIn: 900,
        });
    });

    it.each([
        {},
        { access_token: "", token_type: "Bearer", expires_in: 900 },
        { access_token: "token", token_type: "MAC", expires_in: 900 },
        { access_token: "token", token_type: "Bearer", expires_in: 0 },
    ])("rejects malformed token payload %#", (payload) => {
        expect(() => parseTokenResponse(payload)).toThrow("OIDC token response was invalid");
    });
});
