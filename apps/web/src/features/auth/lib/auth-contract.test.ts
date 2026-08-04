import { describe, expect, it } from "vitest";

import { parseAuthConfig, parseCurrentUser, profileInitials } from "./auth-contract";

describe("parseAuthConfig", () => {
    it("accepts local-test mode without OIDC endpoints", () => {
        expect(
            parseAuthConfig({
                auth_mode: "local_test",
                enabled: true,
                authorization_url: null,
                token_url: null,
                client_id: null,
                scopes: [],
                registration_url: null,
                end_session_url: null,
            }),
        ).toMatchObject({ auth_mode: "local_test", enabled: true });
    });

    it("accepts a complete public OIDC browser configuration", () => {
        const config = parseAuthConfig({
            auth_mode: "oidc",
            enabled: true,
            authorization_url: "https://identity.example.com/authorize",
            token_url: "https://identity.example.com/oauth/token",
            client_id: "viraldy-web",
            scopes: ["openid", "profile", "email", "phone", "offline_access"],
            registration_url: null,
            end_session_url: "https://identity.example.com/logout",
        });

        expect(config.client_id).toBe("viraldy-web");
        expect(config.scopes).toEqual(["openid", "profile", "email", "phone", "offline_access"]);
    });

    it.each([
        { authorization_url: null },
        { token_url: null },
        { client_id: null },
        { scopes: ["openid", "profile", "email"] },
        { scopes: ["openid", "profile", "email", "phone"] },
    ])("rejects an incomplete OIDC config %#", (override) => {
        expect(() =>
            parseAuthConfig({
                auth_mode: "oidc",
                enabled: true,
                authorization_url: "https://identity.example.com/authorize",
                token_url: "https://identity.example.com/oauth/token",
                client_id: "viraldy-web",
                scopes: ["openid", "profile", "email", "phone", "offline_access"],
                registration_url: null,
                end_session_url: null,
                ...override,
            }),
        ).toThrow("OIDC browser configuration is incomplete");
    });
});

describe("current user contract", () => {
    const user = {
        id: "9f98012c-3e64-40eb-b543-0be38eb2af7e",
        email: "seller@example.com",
        display_name: "Mika Kwan",
        phone_number: "+14155552671",
        status: "active",
    };

    it("keeps the complete identity returned by /me", () => {
        expect(parseCurrentUser(user)).toEqual(user);
        expect(parseCurrentUser({ ...user, phone_number: "+12" }).phone_number).toBe("+12");
    });

    it.each([
        { ...user, email: "not-an-email" },
        { ...user, display_name: "" },
        { ...user, phone_number: "415-555-2671" },
        { ...user, status: "suspended" },
    ])("rejects an unusable authenticated profile %#", (payload) => {
        expect(() => parseCurrentUser(payload)).toThrow("Authenticated profile was invalid");
    });

    it("derives readable initials without relying on mock data", () => {
        expect(profileInitials(user)).toBe("MK");
        expect(profileInitials({ ...user, display_name: "Prince" })).toBe("PR");
    });
});
