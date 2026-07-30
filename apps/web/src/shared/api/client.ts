import { authHeaders } from "./auth";
import { unwrapEnvelope } from "./errors";

const CONFIGURED_API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

export const hasConfiguredApiBaseUrl = Boolean(CONFIGURED_API_BASE_URL);

const API_BASE_URL = CONFIGURED_API_BASE_URL || "http://localhost:8000/api/v1";

export async function apiGet<T>(path: string): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${path}`, { headers: authHeaders() });
    return unwrapEnvelope<T>(response);
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${path}`, {
        method: "POST",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: body === undefined ? undefined : JSON.stringify(body),
    });
    return unwrapEnvelope<T>(response);
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${path}`, {
        method: "PATCH",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    return unwrapEnvelope<T>(response);
}
