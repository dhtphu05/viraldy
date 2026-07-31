import { unwrapEnvelope } from "./errors";

const CONFIGURED_API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

export const hasConfiguredApiBaseUrl = Boolean(CONFIGURED_API_BASE_URL);

const API_BASE_URL = "/api/backend";
let refreshPromise: Promise<boolean> | null = null;

export type ApiRequestOptions = {
    headers?: Record<string, string>;
    signal?: AbortSignal;
};

export async function apiGet<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
    const response = await fetchWithSession(`${API_BASE_URL}${path}`, {
        headers: options.headers,
        signal: options.signal,
    });
    return unwrapEnvelope<T>(response);
}

export async function apiPost<T>(
    path: string,
    body?: unknown,
    options: ApiRequestOptions = {},
): Promise<T> {
    const response = await fetchWithSession(`${API_BASE_URL}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...options.headers },
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: options.signal,
    });
    return unwrapEnvelope<T>(response);
}

export async function apiPostForm<T>(
    path: string,
    body: FormData,
    options: ApiRequestOptions = {},
): Promise<T> {
    const response = await fetchWithSession(`${API_BASE_URL}${path}`, {
        method: "POST",
        headers: options.headers,
        body,
        signal: options.signal,
    });
    return unwrapEnvelope<T>(response);
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
    const response = await fetchWithSession(`${API_BASE_URL}${path}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    return unwrapEnvelope<T>(response);
}

async function fetchWithSession(input: string, init?: RequestInit): Promise<Response> {
    const response = await fetch(input, init);
    if (response.status !== 401 || typeof window === "undefined") return response;

    const refreshed = await refreshBrowserSession();
    if (refreshed) return fetch(input, init);

    const returnTo = `${window.location.pathname}${window.location.search}${window.location.hash}`;
    const login = new URL("/login", window.location.origin);
    login.searchParams.set("returnTo", returnTo);
    login.searchParams.set("reason", "session_expired");
    window.location.assign(login.toString());
    return response;
}

async function refreshBrowserSession(): Promise<boolean> {
    if (!refreshPromise) {
        refreshPromise = fetch("/api/auth/refresh", { method: "POST" })
            .then((response) => response.ok)
            .catch(() => false)
            .finally(() => {
                refreshPromise = null;
            });
    }
    return refreshPromise;
}
