import { beforeEach, describe, expect, it, vi } from "vitest";

const cookies = vi.hoisted(() => ({
    values: new Map<string, string>(),
    set: vi.fn(),
    remove: vi.fn(),
}));
vi.mock("@tanstack/react-start/server", () => ({
    getCookie: (name: string) => cookies.values.get(name),
    setCookie: cookies.set,
    deleteCookie: cookies.remove,
    getRequest: () => new Request("https://app.example/account"),
}));

const config = {
    auth_mode: "oidc",
    enabled: true,
    authorization_url: "https://identity.example/auth",
    token_url: "https://identity.example/token",
    registration_url: "https://identity.example/register",
    end_session_url: "https://identity.example/logout",
    revocation_url: "https://identity.example/revoke",
    client_id: "viraldy-web",
    scopes: ["openid", "profile", "email", "phone", "offline_access"],
};
const user = {
    id: "9f98012c-3e64-40eb-b543-0be38eb2af7e",
    email: "seller@example.com",
    display_name: "Seller One",
    phone_number: "+84901234567",
    status: "active",
};
const envelope = (data: unknown) => Response.json({ success: true, data, error: null });
const tokenResponse = (extra: Record<string, unknown> = {}) =>
    Response.json({
        access_token: "new-access",
        refresh_token: "new-refresh",
        token_type: "Bearer",
        expires_in: 300,
        ...extra,
    });
const request = () => new Request("https://app.example/account");
let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    cookies.values.clear();
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(console, "error").mockImplementation(() => {});
});

describe("live OIDC sessions", () => {
    it("starts signup with PKCE, state and a private transaction cookie", async () => {
        fetchMock.mockResolvedValueOnce(envelope(config));
        const { beginAuthorization } = await import("./auth-session.server");
        const target = new URL(await beginAuthorization(request(), "signup", "/smart-remake"));
        expect(target.origin + target.pathname).toBe(config.registration_url);
        expect(target.searchParams.get("code_challenge_method")).toBe("S256");
        expect(target.searchParams.get("state")).toBeTruthy();
        expect(cookies.set).toHaveBeenCalledWith(
            "__Host-viraldy_oidc_transaction",
            expect.any(String),
            expect.objectContaining({ httpOnly: true, secure: true, sameSite: "lax", path: "/" }),
        );
    });

    it("rejects a mismatched callback state before exchanging tokens", async () => {
        cookies.values.set(
            "__Host-viraldy_oidc_transaction",
            JSON.stringify({
                state: "expected",
                verifier: "secret-verifier",
                returnTo: "/account",
                intent: "login",
                createdAt: Date.now(),
            }),
        );
        const { completeAuthorization } = await import("./auth-session.server");
        await expect(
            completeAuthorization(
                new Request("https://app.example/api/auth/callback?code=code&state=wrong"),
            ),
        ).rejects.toThrow("callback validation");
        expect(fetchMock).not.toHaveBeenCalled();
    });

    it("fresh login clears the previous account's refresh token when none is issued", async () => {
        cookies.values.set("__Host-viraldy_refresh", "previous-account-refresh");
        cookies.values.set(
            "__Host-viraldy_oidc_transaction",
            JSON.stringify({
                state: "expected",
                verifier: "secret-verifier",
                returnTo: "/account",
                intent: "login",
                createdAt: Date.now(),
            }),
        );
        fetchMock
            .mockResolvedValueOnce(envelope(config))
            .mockResolvedValueOnce(tokenResponse({ refresh_token: undefined }))
            .mockResolvedValueOnce(envelope(user));
        const { completeAuthorization } = await import("./auth-session.server");
        expect(
            await completeAuthorization(
                new Request("https://app.example/api/auth/callback?code=code&state=expected"),
            ),
        ).toBe("https://app.example/account");
        expect(cookies.remove).toHaveBeenCalledWith("__Host-viraldy_refresh", expect.any(Object));
        expect(cookies.set).toHaveBeenCalledWith(
            "__Host-viraldy_access",
            "new-access",
            expect.objectContaining({ secure: true, httpOnly: true, maxAge: 300 }),
        );
    });

    it("preserves an established session when the backend is unavailable", async () => {
        cookies.values.set("__Host-viraldy_access", "existing-access");
        cookies.values.set("__Host-viraldy_refresh", "existing-refresh");
        fetchMock
            .mockResolvedValueOnce(envelope(config))
            .mockResolvedValueOnce(new Response(null, { status: 503 }));
        const { loadAuthSnapshot } = await import("./auth-session.server");
        expect(await loadAuthSnapshot(request())).toMatchObject({ reason: "auth_unavailable" });
        expect(cookies.remove).not.toHaveBeenCalled();
        expect(fetchMock).toHaveBeenCalledTimes(2);
    });

    it("refreshes an expired token and validates the resulting identity", async () => {
        cookies.values.set("__Host-viraldy_access", "expired-access");
        cookies.values.set("__Host-viraldy_refresh", "existing-refresh");
        fetchMock
            .mockResolvedValueOnce(envelope(config))
            .mockResolvedValueOnce(new Response(null, { status: 401 }))
            .mockResolvedValueOnce(tokenResponse())
            .mockResolvedValueOnce(envelope(user));
        const { loadAuthSnapshot } = await import("./auth-session.server");
        expect(await loadAuthSnapshot(request())).toMatchObject({ authenticated: true, user });
        expect(cookies.set).toHaveBeenCalledWith(
            "__Host-viraldy_refresh",
            "new-refresh",
            expect.any(Object),
        );
    });

    it("does not erase cookies on a temporary refresh failure", async () => {
        cookies.values.set("__Host-viraldy_refresh", "existing-refresh");
        fetchMock
            .mockResolvedValueOnce(envelope(config))
            .mockResolvedValueOnce(new Response(null, { status: 503 }));
        const { refreshSession } = await import("./auth-session.server");
        await expect(refreshSession(request())).rejects.toThrow();
        expect(cookies.remove).not.toHaveBeenCalled();
    });

    it("clears a definitively revoked refresh token", async () => {
        cookies.values.set("__Host-viraldy_refresh", "revoked-refresh");
        fetchMock
            .mockResolvedValueOnce(envelope(config))
            .mockResolvedValueOnce(Response.json({ error: "invalid_grant" }, { status: 400 }));
        const { refreshSession } = await import("./auth-session.server");
        expect(await refreshSession(request())).toBe(false);
        expect(cookies.remove).toHaveBeenCalledWith("__Host-viraldy_refresh", expect.any(Object));
    });

    it("coordinates simultaneous refreshes so rotation cannot overwrite a valid session", async () => {
        cookies.values.set("__Host-viraldy_refresh", "rotating-refresh");
        let exchanges = 0;
        fetchMock.mockImplementation(async (input: string) => {
            if (input.endsWith("/auth/config")) return envelope(config);
            if (input === config.token_url) {
                exchanges += 1;
                await new Promise((resolve) => setTimeout(resolve, 10));
                return exchanges === 1
                    ? tokenResponse()
                    : Response.json({ error: "invalid_grant" }, { status: 400 });
            }
            return envelope(user);
        });
        const { refreshSession } = await import("./auth-session.server");
        expect(await Promise.all([refreshSession(request()), refreshSession(request())])).toEqual([
            true,
            true,
        ]);
        expect(exchanges).toBe(1);
        expect(cookies.remove).not.toHaveBeenCalled();
    });

    it("revokes the refresh token on logout and always clears local cookies", async () => {
        cookies.values.set("__Host-viraldy_refresh", "logout-refresh");
        fetchMock.mockResolvedValueOnce(envelope(config)).mockResolvedValueOnce(new Response());
        const { logoutDestination } = await import("./auth-session.server");
        expect(await logoutDestination(request())).toContain("https://identity.example/logout?");
        expect(fetchMock).toHaveBeenCalledWith(
            config.revocation_url,
            expect.objectContaining({
                method: "POST",
                body: expect.any(URLSearchParams),
            }),
        );
        expect(cookies.remove).toHaveBeenCalledWith("__Host-viraldy_access", expect.any(Object));
    });
});

describe("native password sessions", () => {
    const passwordConfig = { ...config, auth_mode: "password" };

    it("exchanges credentials server-side and sends only the destination to the browser", async () => {
        fetchMock
            .mockResolvedValueOnce(envelope(passwordConfig))
            .mockResolvedValueOnce(
                envelope({
                    access_token: "new-access",
                    refresh_token: "new-refresh",
                    token_type: "Bearer",
                    expires_in: 900,
                }),
            )
            .mockResolvedValueOnce(envelope(user));
        const { authenticatePassword } = await import("./auth-session.server");
        expect(
            await authenticatePassword(
                new Request("https://app.example/api/auth/login", {
                    method: "POST",
                    body: JSON.stringify({
                        email: "seller@example.com",
                        password: crypto.randomUUID(),
                        returnTo: "/smart-remake",
                    }),
                }),
                "login",
            ),
        ).toBe("/smart-remake");
        expect(cookies.set).toHaveBeenCalledWith(
            "__Host-viraldy_access",
            "new-access",
            expect.objectContaining({ httpOnly: true, secure: true }),
        );
    });

    it("rotates native refresh credentials through the backend", async () => {
        cookies.values.set("__Host-viraldy_refresh", "native-refresh");
        fetchMock
            .mockResolvedValueOnce(envelope(passwordConfig))
            .mockResolvedValueOnce(
                envelope({
                    access_token: "new-access",
                    refresh_token: "rotated-native",
                    token_type: "Bearer",
                    expires_in: 900,
                }),
            )
            .mockResolvedValueOnce(envelope(user));
        const { refreshSession } = await import("./auth-session.server");
        expect(await refreshSession(request())).toBe(true);
        expect(fetchMock).toHaveBeenCalledWith(
            expect.stringContaining("/auth/refresh"),
            expect.objectContaining({
                method: "POST",
                body: JSON.stringify({ refresh_token: "native-refresh" }),
            }),
        );
        expect(cookies.set).toHaveBeenCalledWith(
            "__Host-viraldy_refresh",
            "rotated-native",
            expect.any(Object),
        );
    });

    it("revokes native sessions on logout", async () => {
        cookies.values.set("__Host-viraldy_refresh", "native-refresh");
        fetchMock
            .mockResolvedValueOnce(envelope(passwordConfig))
            .mockResolvedValueOnce(new Response(null, { status: 204 }));
        const { logoutDestination } = await import("./auth-session.server");
        expect(await logoutDestination(request())).toBe("https://app.example/login?loggedOut=1");
        expect(fetchMock).toHaveBeenCalledWith(
            expect.stringContaining("/auth/logout"),
            expect.objectContaining({
                method: "POST",
                body: JSON.stringify({ refresh_token: "native-refresh" }),
            }),
        );
    });
});
