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

    let accessToken = readCookie(ACCESS_COOKIE);
    if (!accessToken && readCookie(REFRESH_COOKIE) && config.auth_mode === "oidc") {
        accessToken = await refreshAccessToken(request, config);
    }
    if (!accessToken) return unauthenticated(config.auth_mode, true, "missing_session");

    try {
        return {
            authenticated: true,
            user: await fetchCurrentUser(accessToken),
            mode: config.auth_mode,
            enabled: true,
            reason: null,
        };
    } catch (error) {
        if (config.auth_mode === "oidc" && readCookie(REFRESH_COOKIE)) {
            const refreshed = await refreshAccessToken(request, config);
            if (refreshed) {
                try {
                    return {
                        authenticated: true,
                        user: await fetchCurrentUser(refreshed),
                        mode: config.auth_mode,
                        enabled: true,
                        reason: null,
                    };
                } catch (retryError) {
                    logSafeAuthError("validate refreshed session", retryError);
                }
            }
        }
        logSafeAuthError("validate session", error);
        clearSessionCookies(request);
        return unauthenticated(config.auth_mode, true, "session_expired");
    }
}

export async function beginAuthorization(
    request: Request,
    intent: AuthIntent,
    returnToInput: string | null,
): Promise<string> {
    const config = await fetchAuthConfig();
    if (!config.enabled) throw new Error("Authentication is disabled");
    const returnTo = sanitizeReturnTo(returnToInput);

    if (config.auth_mode === "local_test") {
        const localToken = "local-test";
        await fetchCurrentUser(localToken);
        setSessionCookies(request, {
            accessToken: localToken,
            refreshToken: null,
            expiresIn: LOCAL_SESSION_TTL_SECONDS,
        });
        return new URL(returnTo, request.url).toString();
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
        Date.now() - transaction.createdAt > OIDC_TRANSACTION_TTL_SECONDS * 1000
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
    return new URL(transaction.returnTo, request.url).toString();
}

export async function refreshSession(request: Request): Promise<boolean> {
    const config = await fetchAuthConfig();
    if (!config.enabled || config.auth_mode !== "oidc") return false;
    return Boolean(await refreshAccessToken(request, config));
}

export async function logoutDestination(request: Request): Promise<string> {
    clearSessionCookies(request);
    clearTransactionCookie(request);
    const localDestination = new URL("/login?loggedOut=1", request.url).toString();
    try {
        const config = await fetchAuthConfig();
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
    });
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
        body: new URLSearchParams({
            grant_type: "authorization_code",
            code,
            client_id: config.client_id,
            redirect_uri: redirectUri,
            code_verifier: verifier,
        }),
    });
    if (!response.ok) throw new Error("OIDC code exchange failed");
    return parseTokenResponse(await response.json());
}

async function refreshAccessToken(request: Request, config: AuthConfig): Promise<string | null> {
    const refreshToken = readCookie(REFRESH_COOKIE);
    if (!refreshToken || !config.token_url || !config.client_id) return null;
    try {
        const response = await fetch(config.token_url, {
            method: "POST",
            headers: {
                Accept: "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            body: new URLSearchParams({
                grant_type: "refresh_token",
                refresh_token: refreshToken,
                client_id: config.client_id,
            }),
        });
        if (!response.ok) throw new Error("OIDC refresh failed");
        const tokens = parseTokenResponse(await response.json());
        await fetchCurrentUser(tokens.accessToken);
        setSessionCookies(request, {
            ...tokens,
            refreshToken: tokens.refreshToken ?? refreshToken,
        });
        return tokens.accessToken;
    } catch (error) {
        logSafeAuthError("refresh session", error);
        clearSessionCookies(request);
        return null;
    }
}

function setSessionCookies(request: Request, tokens: ParsedTokenResponse): void {
    setAuthCookie(request, ACCESS_COOKIE, tokens.accessToken, {
        maxAge: Math.max(1, Math.min(Math.floor(tokens.expiresIn), 24 * 60 * 60)),
    });
    if (tokens.refreshToken) {
        setAuthCookie(request, REFRESH_COOKIE, tokens.refreshToken, {
            maxAge: REFRESH_COOKIE_TTL_SECONDS,
        });
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
    return new URL(request.url).protocol === "https:";
}

function callbackUrl(request: Request): string {
    return new URL("/api/auth/callback", request.url).toString();
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
