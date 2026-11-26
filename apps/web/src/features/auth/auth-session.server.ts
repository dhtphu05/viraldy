import { deleteCookie, getCookie, getRequest, setCookie } from "@tanstack/react-start/server";

import {
    buildAuthorizationUrl,
    parseTokenResponse,
    pkceChallenge,
    randomBase64Url,
    sanitizeReturnTo,
    type AuthIntent,
    type OidcBrowserConfig,
    type ParsedTokenResponse,
} from "./lib/auth-flow";
import {
    parseAuthConfig,
    parseCurrentUser,
    type AuthConfig,
    type CurrentUser,
} from "./lib/auth-contract";
import type { AuthReason, AuthSnapshot } from "./auth-session";
import { authRequestUrl } from "./auth-request.server";
import { authPeerHeaders } from "./auth-peer.server";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1").replace(
    /\/$/,
    "",
);
const ACCESS_COOKIE = "viraldy_access";
const REFRESH_COOKIE = "viraldy_refresh";
const TRANSACTION_COOKIE = "viraldy_oidc_transaction";
const OIDC_TRANSACTION_TTL_SECONDS = 10 * 60;
const REFRESH_COOKIE_TTL_SECONDS = 30 * 24 * 60 * 60;
const LOCAL_SESSION_TTL_SECONDS = 8 * 60 * 60;
const AUTH_TIMEOUT_MS = 10_000;
type RefreshedSession = { tokens: ParsedTokenResponse; user: CurrentUser };
const refreshes = new Map<string, Promise<RefreshedSession>>();

class RejectedSession extends Error {}

export class PasswordSignInError extends Error {
    constructor(public status: number) {
        super("Unable to complete sign-in");
    }
}

export async function authenticatePassword(request: Request, intent: AuthIntent): Promise<string> {
    const config = await fetchAuthConfig();
    if (!config.enabled || config.auth_mode !== "password") throw new PasswordSignInError(503);
    if (Number(request.headers.get("content-length")) > 16_384) throw new PasswordSignInError(413);
    const text = await request.text();
    if (text.length > 16_384) throw new PasswordSignInError(413);
    let payload: Record<string, unknown>;
    try {
        const parsed: unknown = request.headers
            .get("content-type")
            ?.includes("application/x-www-form-urlencoded")
            ? Object.fromEntries(new URLSearchParams(text))
            : JSON.parse(text);
        if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed))
            throw new Error();
        payload = parsed as Record<string, unknown>;
    } catch {
        throw new PasswordSignInError(400);
    }
    const response = await fetch(
        `${API_BASE_URL}/auth/${intent === "signup" ? "register" : "login"}`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Accept: "application/json",
                ...authPeerHeaders(),
            },
            body: JSON.stringify({
                email: payload.email,
                password: payload.password,
                ...(intent === "signup" ? { display_name: payload.display_name } : {}),
            }),
            signal: AbortSignal.timeout(AUTH_TIMEOUT_MS),
        },
    );
    if (!response.ok) throw new PasswordSignInError(response.status);
    const tokens = parseTokenResponse(await envelopeData(response));
    await fetchCurrentUser(tokens.accessToken);
    setSessionCookies(request, tokens);
    return sanitizeReturnTo(typeof payload.returnTo === "string" ? payload.returnTo : null);
}

type OidcTransaction = {
    state: string;
    verifier: string;
    returnTo: string;
    intent: AuthIntent;
    createdAt: number;
};

export function loadAuthSnapshotForCurrentRequest(): Promise<AuthSnapshot> {
    return loadAuthSnapshot(getRequest());
}

export async function loadAuthSnapshot(request: Request): Promise<AuthSnapshot> {
    let config: AuthConfig;
    try {
        config = await fetchAuthConfig();
    } catch (error) {
        logSafeAuthError("load auth configuration", error);
        return unauthenticated("unavailable", false, "auth_unavailable");
    }

    if (!config.enabled) return unauthenticated(config.auth_mode, false, "auth_unavailable");

    const accessToken = readCookie(ACCESS_COOKIE);
    const canRefresh =
        Boolean(readCookie(REFRESH_COOKIE)) &&
        (config.auth_mode === "oidc" || config.auth_mode === "password");
    try {
        if (accessToken) {
            try {
                return authenticatedSnapshot(config, await fetchCurrentUser(accessToken));
            } catch (error) {
                if (!(error instanceof RejectedSession)) throw error;
            }
        }
        if (canRefresh) {
            const refreshed = await refreshAccessToken(request, config);
            if (refreshed) return authenticatedSnapshot(config, refreshed.user);
        }
    } catch (error) {
        logSafeAuthError("validate session", error);
        return unauthenticated(config.auth_mode, false, "auth_unavailable");
    }
    if (accessToken || canRefresh) clearSessionCookies(request);
    return unauthenticated(
        config.auth_mode,
        true,
        accessToken || canRefresh ? "session_expired" : "missing_session",
    );
}

function authenticatedSnapshot(config: AuthConfig, user: CurrentUser): AuthSnapshot {
    return { authenticated: true, user, mode: config.auth_mode, enabled: true, reason: null };
}

export async function beginAuthorization(
    request: Request,
    intent: AuthIntent,
    returnToInput: string | null,
): Promise<string> {
    const config = await fetchAuthConfig();
    if (!config.enabled) throw new Error("Authentication is disabled");
    const returnTo = sanitizeReturnTo(returnToInput);

    if (config.auth_mode === "password") {
        const destination = new URL(
            intent === "signup" ? "/register" : "/login",
            authRequestUrl(request),
        );
        destination.searchParams.set("returnTo", returnTo);
        return destination.toString();
    }

    if (config.auth_mode === "local_test") {
        const localToken = "local-test";
        await fetchCurrentUser(localToken);
        setSessionCookies(request, {
            accessToken: localToken,
            refreshToken: null,
            expiresIn: LOCAL_SESSION_TTL_SECONDS,
        });
        return new URL(returnTo, authRequestUrl(request)).toString();
    }

    const oidcConfig = toOidcBrowserConfig(config);
    const state = randomBase64Url(32);
    const verifier = randomBase64Url(48);
    const transaction: OidcTransaction = {
        state,
        verifier,
        returnTo,
        intent,
        createdAt: Date.now(),
    };
    setAuthCookie(request, TRANSACTION_COOKIE, JSON.stringify(transaction), {
        maxAge: OIDC_TRANSACTION_TTL_SECONDS,
    });

    return buildAuthorizationUrl({
        config: oidcConfig,
        callbackUrl: callbackUrl(request),
        state,
        codeChallenge: await pkceChallenge(verifier),
        intent,
    });
}

export async function completeAuthorization(request: Request): Promise<string> {
    const url = new URL(request.url);
    const transaction = readTransaction();
    clearTransactionCookie(request);
    const code = url.searchParams.get("code");
    const returnedState = url.searchParams.get("state");
    if (url.searchParams.has("error")) throw new Error("OIDC authorization was not completed");
    if (
        !transaction ||
        !code ||
        !returnedState ||
        returnedState !== transaction.state ||
        Date.now() - transaction.createdAt > OIDC_TRANSACTION_TTL_SECONDS * 1000 ||
        transaction.createdAt > Date.now()
    ) {
        throw new Error("OIDC callback validation failed");
    }

    const config = await fetchAuthConfig();
    if (config.auth_mode !== "oidc" || !config.enabled) {
        throw new Error("OIDC is not available");
    }
    const tokens = await exchangeAuthorizationCode({
        config,
        code,
        verifier: transaction.verifier,
        callbackUrl: callbackUrl(request),
    });
    await fetchCurrentUser(tokens.accessToken);
    setSessionCookies(request, tokens);
    return new URL(transaction.returnTo, authRequestUrl(request)).toString();
}

export async function refreshSession(request: Request): Promise<boolean> {
    const config = await fetchAuthConfig();
    if (!config.enabled || !["oidc", "password"].includes(config.auth_mode)) return false;
    return Boolean(await refreshAccessToken(request, config));
}

export async function logoutDestination(request: Request): Promise<string> {
    const refreshToken = readCookie(REFRESH_COOKIE);
    clearSessionCookies(request);
    clearTransactionCookie(request);
    const localDestination = new URL("/login?loggedOut=1", authRequestUrl(request)).toString();
    try {
        const config = await fetchAuthConfig();
        if (config.auth_mode === "password" && refreshToken) {
            const response = await fetch(`${API_BASE_URL}/auth/logout`, {
                method: "POST",
                headers: { "Content-Type": "application/json", ...authPeerHeaders() },
                body: JSON.stringify({ refresh_token: refreshToken }),
                signal: AbortSignal.timeout(AUTH_TIMEOUT_MS),
            });
            if (!response.ok) throw new Error("Session revocation failed");
            return localDestination;
        }
        if (
            config.auth_mode === "oidc" &&
            config.revocation_url &&
            refreshToken &&
            config.client_id
        ) {
            try {
                const response = await fetch(config.revocation_url, {
                    method: "POST",
                    headers: { "Content-Type": "application/x-www-form-urlencoded" },
                    body: tokenForm({
                        token: refreshToken,
                        token_type_hint: "refresh_token",
                        client_id: config.client_id,
                    }),
                    signal: AbortSignal.timeout(AUTH_TIMEOUT_MS),
                });
                if (!response.ok) throw new Error("Token revocation failed");
            } catch (error) {
                logSafeAuthError("revoke session", error);
            }
        }
        if (config.auth_mode !== "oidc" || !config.end_session_url) return localDestination;
        const endSession = new URL(config.end_session_url);
        endSession.searchParams.set("client_id", config.client_id ?? "");
        endSession.searchParams.set("post_logout_redirect_uri", localDestination);
        return endSession.toString();
    } catch (error) {
        logSafeAuthError("load logout configuration", error);
        return localDestination;
    }
}

export function accessTokenFromCookie(): string | null {
    return readCookie(ACCESS_COOKIE);
}

export async function fetchAuthConfig(): Promise<AuthConfig> {
    const response = await fetch(`${API_BASE_URL}/auth/config`, {
        headers: { Accept: "application/json" },
        cache: "no-store",
        signal: AbortSignal.timeout(AUTH_TIMEOUT_MS),
    });
    if (!response.ok) throw new Error("Auth configuration request failed");
    return parseAuthConfig(await envelopeData(response));
}

async function fetchCurrentUser(accessToken: string): Promise<CurrentUser> {
    const response = await fetch(`${API_BASE_URL}/me`, {
        headers: {
            Accept: "application/json",
            Authorization: `Bearer ${accessToken}`,
        },
        cache: "no-store",
        signal: AbortSignal.timeout(AUTH_TIMEOUT_MS),
    });
    if (response.status === 401 || response.status === 403) throw new RejectedSession();
    if (!response.ok) throw new Error("Authenticated profile request failed");
    return parseCurrentUser(await envelopeData(response));
}

async function exchangeAuthorizationCode({
    config,
    code,
    verifier,
    callbackUrl: redirectUri,
}: {
    config: AuthConfig;
    code: string;
    verifier: string;
    callbackUrl: string;
}): Promise<ParsedTokenResponse> {
    if (!config.token_url || !config.client_id) throw new Error("OIDC token endpoint is missing");
    const response = await fetch(config.token_url, {
        method: "POST",
        headers: {
            Accept: "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        body: tokenForm({
            grant_type: "authorization_code",
            code,
            client_id: config.client_id,
            redirect_uri: redirectUri,
            code_verifier: verifier,
        }),
        signal: AbortSignal.timeout(AUTH_TIMEOUT_MS),
    });
    if (!response.ok) throw new Error("OIDC code exchange failed");
    return parseTokenResponse(await response.json());
}

async function refreshAccessToken(
    request: Request,
    config: AuthConfig,
): Promise<RefreshedSession | null> {
    const refreshToken = readCookie(REFRESH_COOKIE);
    if (!refreshToken || (config.auth_mode === "oidc" && (!config.token_url || !config.client_id)))
        return null;
    // Share one rotating-token exchange within a server instance; apply cookies in each request context.
    const digest = await crypto.subtle.digest(
        "SHA-256",
        new TextEncoder().encode(`${config.token_url}\n${config.client_id}\n${refreshToken}`),
    );
    const key = Array.from(new Uint8Array(digest), (byte) =>
        byte.toString(16).padStart(2, "0"),
    ).join("");
    let pending = refreshes.get(key);
    if (!pending) {
        pending = exchangeRefreshToken(config, refreshToken);
        refreshes.set(key, pending);
    }
    try {
        const refreshed = await pending;
        setSessionCookies(request, refreshed.tokens);
        return refreshed;
    } catch (error) {
        if (error instanceof RejectedSession) {
            clearSessionCookies(request);
            return null;
        }
        throw error;
    } finally {
        if (refreshes.get(key) === pending) refreshes.delete(key);
    }
}

async function exchangeRefreshToken(
    config: AuthConfig,
    refreshToken: string,
): Promise<RefreshedSession> {
    const native = config.auth_mode === "password";
    const response = await fetch(native ? `${API_BASE_URL}/auth/refresh` : config.token_url!, {
        method: "POST",
        headers: {
            Accept: "application/json",
            "Content-Type": native ? "application/json" : "application/x-www-form-urlencoded",
            ...(native ? authPeerHeaders() : {}),
        },
        body: native
            ? JSON.stringify({ refresh_token: refreshToken })
            : tokenForm({
                  grant_type: "refresh_token",
                  refresh_token: refreshToken,
                  client_id: config.client_id!,
              }),
        signal: AbortSignal.timeout(AUTH_TIMEOUT_MS),
    });
    if (!response.ok) {
        if (native && [400, 401, 403, 422].includes(response.status)) throw new RejectedSession();
        const payload = (await response.json().catch(() => null)) as { error?: string } | null;
        if (response.status === 400 && payload?.error === "invalid_grant")
            throw new RejectedSession();
        throw new Error("OIDC refresh service is unavailable");
    }
    const tokens = parseTokenResponse(
        native ? await envelopeData(response) : await response.json(),
    );
    const user = await fetchCurrentUser(tokens.accessToken);
    return { tokens: { ...tokens, refreshToken: tokens.refreshToken ?? refreshToken }, user };
}

function tokenForm(fields: Record<string, string>): URLSearchParams {
    const body = new URLSearchParams(fields);
    const clientSecret = process.env.AUTH_CLIENT_SECRET;
    if (clientSecret) body.set("client_secret", clientSecret);
    return body;
}

function setSessionCookies(request: Request, tokens: ParsedTokenResponse): void {
    setAuthCookie(request, ACCESS_COOKIE, tokens.accessToken, {
        maxAge: Math.max(1, Math.min(Math.floor(tokens.expiresIn), 24 * 60 * 60)),
    });
    if (tokens.refreshToken) {
        setAuthCookie(request, REFRESH_COOKIE, tokens.refreshToken, {
            maxAge: REFRESH_COOKIE_TTL_SECONDS,
        });
    } else {
        clearAuthCookie(request, REFRESH_COOKIE);
    }
}

function clearSessionCookies(request: Request): void {
    clearAuthCookie(request, ACCESS_COOKIE);
    clearAuthCookie(request, REFRESH_COOKIE);
}

function readTransaction(): OidcTransaction | null {
    const raw = readCookie(TRANSACTION_COOKIE);
    if (!raw) return null;
    try {
        const parsed = JSON.parse(raw) as Partial<OidcTransaction>;
        if (
            typeof parsed.state !== "string" ||
            typeof parsed.verifier !== "string" ||
            typeof parsed.returnTo !== "string" ||
            (parsed.intent !== "login" && parsed.intent !== "signup") ||
            typeof parsed.createdAt !== "number"
        ) {
            return null;
        }
        return {
            state: parsed.state,
            verifier: parsed.verifier,
            returnTo: sanitizeReturnTo(parsed.returnTo),
            intent: parsed.intent,
            createdAt: parsed.createdAt,
        };
    } catch {
        return null;
    }
}

function clearTransactionCookie(request: Request): void {
    clearAuthCookie(request, TRANSACTION_COOKIE);
}

function setAuthCookie(
    request: Request,
    baseName: string,
    value: string,
    options: { maxAge: number },
): void {
    const secure = isSecureRequest(request);
    setCookie(cookieName(baseName, secure), value, {
        httpOnly: true,
        secure,
        sameSite: "lax",
        path: "/",
        maxAge: options.maxAge,
    });
}

function clearAuthCookie(request: Request, baseName: string): void {
    const secure = isSecureRequest(request);
    deleteCookie(cookieName(baseName, secure), { path: "/", secure });
    deleteCookie(baseName, { path: "/" });
    deleteCookie(`__Host-${baseName}`, { path: "/", secure: true });
}

function readCookie(baseName: string): string | null {
    return getCookie(`__Host-${baseName}`) ?? getCookie(baseName) ?? null;
}

function cookieName(baseName: string, secure: boolean): string {
    return secure ? `__Host-${baseName}` : baseName;
}

function isSecureRequest(request: Request): boolean {
    return authRequestUrl(request).protocol === "https:";
}

function callbackUrl(request: Request): string {
    return new URL("/api/auth/callback", authRequestUrl(request)).toString();
}

function toOidcBrowserConfig(config: AuthConfig): OidcBrowserConfig {
    if (!config.authorization_url || !config.token_url || !config.client_id) {
        throw new Error("OIDC browser configuration is incomplete");
    }
    return {
        authorization_url: config.authorization_url,
        token_url: config.token_url,
        client_id: config.client_id,
        scopes: config.scopes,
        registration_url: config.registration_url,
    };
}

function unauthenticated(
    mode: AuthSnapshot["mode"],
    enabled: boolean,
    reason: Exclude<AuthReason, null>,
): AuthSnapshot {
    return { authenticated: false, user: null, mode, enabled, reason };
}

async function envelopeData(response: Response): Promise<unknown> {
    const payload = (await response.json()) as { data?: unknown; error?: unknown };
    if (payload.error || !("data" in payload)) throw new Error("API envelope was invalid");
    return payload.data;
}

function logSafeAuthError(action: string, error: unknown): void {
    const name = error instanceof Error ? error.name : "UnknownError";
    console.error(`[auth] Failed to ${action}: ${name}`);
}
