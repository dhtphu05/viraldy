import { describe, expect, it } from "vitest";

import {
    parseAuthConfig,
    parseCurrentUser,
    passwordCredentialsSchema,
    passwordRegistrationSchema,
    passwordAuthResponseSchema,
    profileInitials,
} from "./auth-contract";

describe("parseAuthConfig", () => {
    it("accepts native password auth without identity provider endpoints", () => {
        expect(
            parseAuthConfig({
                auth_mode: "password",
                enabled: true,
                authorization_url: null,
                token_url: null,
                client_id: null,
                scopes: [],
                registration_url: null,
                end_session_url: null,
            }),
        ).toMatchObject({ auth_mode: "password", enabled: true, revocation_url: null });
    });

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
        ).toMatchObject({ auth_mode: "local_test", enabled: true, revocation_url: null });
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

    it.each([undefined, null, "https://identity.example.com/oauth/revoke"])(
        "accepts optional phone scope and revocation endpoint %s",
        (revocation_url) => {
            const config = parseAuthConfig({
                auth_mode: "oidc",
                enabled: true,
                authorization_url: "https://identity.example.com/authorize",
                token_url: "https://identity.example.com/oauth/token",
                client_id: "viraldy-web",
                scopes: ["openid", "profile", "email", "offline_access"],
                registration_url: null,
                end_session_url: null,
                ...(revocation_url === undefined ? {} : { revocation_url }),
            });

            expect(config.revocation_url).toBe(revocation_url ?? null);
        },
    );

    it.each([
        { authorization_url: null },
        { token_url: null },
        { client_id: null },
        { scopes: ["profile", "email", "offline_access"] },
        { scopes: ["openid", "email", "offline_access"] },
        { scopes: ["openid", "profile", "offline_access"] },
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

    it("rejects a malformed revocation endpoint", () => {
        expect(() =>
            parseAuthConfig({
                auth_mode: "local_test",
                enabled: true,
                authorization_url: null,
                token_url: null,
                client_id: null,
                scopes: [],
                registration_url: null,
                end_session_url: null,
                revocation_url: "not-a-url",
            }),
        ).toThrow("Auth configuration was invalid");
    });
});

describe("native password credentials", () => {
    const passphrase = crypto.randomUUID();
    const credentials = { email: "seller@example.com", password: passphrase };

    it("trims email without changing the password", () => {
        expect(
            passwordCredentialsSchema.parse({
                email: " seller@example.com ",
                password: `  ${passphrase}  `,
            }),
        ).toEqual({ email: "seller@example.com", password: `  ${passphrase}  ` });
    });

    it.each(["", "not-an-email", "seller@"])("rejects invalid email %s", (email) => {
        expect(passwordCredentialsSchema.safeParse({ ...credentials, email }).success).toBe(false);
    });

    it.each([
        ["", false],
        ["a", true],
        ["password", true],
        ["é".repeat(6), true],
        ["🔐".repeat(4), true],
        ["a".repeat(1024), true],
        ["é".repeat(1024), true],
        ["🔐".repeat(1024), true],
        ["a".repeat(1025), false],
        ["é".repeat(1025), false],
        ["🔐".repeat(1025), false],
    ])("matches backend login bounds of 1–1024 Unicode characters %#", (password, valid) => {
        expect(passwordCredentialsSchema.safeParse({ ...credentials, password }).success).toBe(
            valid,
        );
    });

    it.each([
        ["", false],
        ["password", false],
        ["a".repeat(11), false],
        ["é".repeat(6), false],
        ["🔐".repeat(4), false],
        ["a".repeat(12), true],
        ["é".repeat(12), true],
        ["🔐".repeat(12), true],
        ["a".repeat(1024), true],
        ["é".repeat(1024), true],
        ["🔐".repeat(1024), true],
        ["a".repeat(1025), false],
        ["é".repeat(1025), false],
        ["🔐".repeat(1025), false],
    ])(
        "matches backend registration bounds of 12–1024 Unicode characters %#",
        (password, valid) => {
            expect(
                passwordRegistrationSchema.safeParse({
                    ...credentials,
                    password,
                    display_name: "Seller One",
                    confirmPassword: password,
                }).success,
            ).toBe(valid);
        },
    );

    it("accepts registration with a display name and matching confirmation without a phone", () => {
        expect(
            passwordRegistrationSchema.parse({
                ...credentials,
                display_name: " Seller One ",
                confirmPassword: credentials.password,
            }),
        ).toMatchObject({ display_name: "Seller One", email: credentials.email });
    });

    it.each(["", "   ", "a".repeat(256)])("rejects an invalid display name", (display_name) => {
        expect(
            passwordRegistrationSchema.safeParse({
                ...credentials,
                display_name,
                confirmPassword: credentials.password,
            }).success,
        ).toBe(false);
    });

    it("reports mismatched passwords on the confirmation field", () => {
        const result = passwordRegistrationSchema.safeParse({
            ...credentials,
            display_name: "Seller One",
            confirmPassword: "another-passphrase",
        });
        expect(result.success).toBe(false);
        if (!result.success) expect(result.error.issues[0].path).toEqual(["confirmPassword"]);
    });

    it("accepts only a completed BFF session response", () => {
        expect(
            passwordAuthResponseSchema.parse({ authenticated: true, returnTo: "/account" }),
        ).toEqual({ authenticated: true, returnTo: "/account" });
        expect(passwordAuthResponseSchema.safeParse({ authenticated: false }).success).toBe(false);
        expect(
            passwordAuthResponseSchema.safeParse({ error: { message: "internal details" } })
                .success,
        ).toBe(false);
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

    it("accepts an explicitly unavailable phone number", () => {
        expect(parseCurrentUser({ ...user, phone_number: null }).phone_number).toBeNull();
    });

    it("requires the phone number field even when its value can be null", () => {
        const { phone_number, ...withoutPhone } = user;
        expect(phone_number).toBeDefined();
        expect(() => parseCurrentUser(withoutPhone)).toThrow("Authenticated profile was invalid");
        expect(() => parseCurrentUser({ ...user, phone_number: undefined })).toThrow(
            "Authenticated profile was invalid",
        );
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
