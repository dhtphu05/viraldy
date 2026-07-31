export type AuthIntent = "login" | "signup";

export type OidcBrowserConfig = {
    authorization_url: string;
    token_url: string;
    client_id: string;
    scopes: string[];
    registration_url: string | null;
};

export type ParsedTokenResponse = {
    accessToken: string;
    refreshToken: string | null;
    expiresIn: number;
};

const DEFAULT_RETURN_TO = "/dashboard";
const AUTH_LOOP_PATHS = ["/login", "/register", "/api/auth"];

export function sanitizeReturnTo(value: string | null | undefined): string {
    if (!value || !value.startsWith("/") || value.startsWith("//")) {
        return DEFAULT_RETURN_TO;
    }

    const path = value.split(/[?#]/, 1)[0];
    if (AUTH_LOOP_PATHS.some((prefix) => path === prefix || path.startsWith(`${prefix}/`))) {
        return DEFAULT_RETURN_TO;
    }
    return value;
}

export async function pkceChallenge(verifier: string): Promise<string> {
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
    return bytesToBase64Url(new Uint8Array(digest));
}

export function buildAuthorizationUrl({
    config,
    callbackUrl,
    state,
    codeChallenge,
    intent,
}: {
    config: OidcBrowserConfig;
    callbackUrl: string;
    state: string;
    codeChallenge: string;
    intent: AuthIntent;
}): string {
    const baseUrl =
        intent === "signup" && config.registration_url
            ? config.registration_url
            : config.authorization_url;
    const url = new URL(baseUrl);
    url.searchParams.set("response_type", "code");
    url.searchParams.set("client_id", config.client_id);
    url.searchParams.set("redirect_uri", callbackUrl);
    url.searchParams.set("scope", config.scopes.join(" "));
    url.searchParams.set("state", state);
    url.searchParams.set("code_challenge", codeChallenge);
    url.searchParams.set("code_challenge_method", "S256");
    if (intent === "signup" && !config.registration_url) {
        url.searchParams.set("prompt", "create");
    }
    return url.toString();
}

export function parseTokenResponse(payload: unknown): ParsedTokenResponse {
    if (!isRecord(payload)) throw invalidTokenResponse();
    const accessToken = payload.access_token;
    const tokenType = payload.token_type;
    const expiresIn = payload.expires_in;
    const refreshToken = payload.refresh_token;

    if (
        typeof accessToken !== "string" ||
        accessToken.length === 0 ||
        typeof tokenType !== "string" ||
        tokenType.toLowerCase() !== "bearer" ||
        typeof expiresIn !== "number" ||
        !Number.isFinite(expiresIn) ||
        expiresIn <= 0 ||
        (refreshToken !== undefined && typeof refreshToken !== "string")
    ) {
        throw invalidTokenResponse();
    }

    return {
        accessToken,
        refreshToken: refreshToken || null,
        expiresIn,
    };
}

export function randomBase64Url(byteLength: number): string {
    const bytes = new Uint8Array(byteLength);
    crypto.getRandomValues(bytes);
    return bytesToBase64Url(bytes);
}

function bytesToBase64Url(bytes: Uint8Array): string {
    let binary = "";
    for (const byte of bytes) binary += String.fromCharCode(byte);
    return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null && !Array.isArray(value);
}

function invalidTokenResponse(): Error {
    return new Error("OIDC token response was invalid");
}
