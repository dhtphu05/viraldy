import { createFileRoute } from "@tanstack/react-router";

import { accessTokenFromCookie } from "@/features/auth/auth-session.server";
import {
    backendPathFromRequest,
    hasValidMutationOrigin,
    upstreamRequestInit,
} from "@/features/auth/lib/auth-proxy";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1").replace(
    /\/$/,
    "",
);
const mutationMethods = new Set(["POST", "PUT", "PATCH", "DELETE"]);

async function proxyBackend(request: Request): Promise<Response> {
    if (
        mutationMethods.has(request.method) &&
        !hasValidMutationOrigin({
            requestUrl: request.url,
            origin: request.headers.get("origin") ?? undefined,
        })
    ) {
        return apiError(403, "FORBIDDEN", "Request origin was not accepted.");
    }

    const accessToken = accessTokenFromCookie();
    if (!accessToken) return apiError(401, "UNAUTHENTICATED", "Please sign in to continue.");

    let backendPath: string;
    try {
        backendPath = backendPathFromRequest(request.url);
    } catch {
        return apiError(400, "INVALID_PROXY_PATH", "The API path was invalid.");
    }

    const headers = new Headers({
        Accept: request.headers.get("accept") ?? "application/json",
        Authorization: `Bearer ${accessToken}`,
    });
    for (const header of ["content-type", "idempotency-key", "x-request-id"] as const) {
        const value = request.headers.get(header);
        if (value) headers.set(header, value);
    }

    try {
        const upstream = await fetch(
            `${API_BASE_URL}${backendPath}`,
            upstreamRequestInit(request, headers),
        );
        const responseHeaders = new Headers();
        for (const header of ["content-type", "content-disposition", "x-request-id"] as const) {
            const value = upstream.headers.get(header);
            if (value) responseHeaders.set(header, value);
        }
        responseHeaders.set("Cache-Control", "no-store");
        return new Response(upstream.body, {
            status: upstream.status,
            statusText: upstream.statusText,
            headers: responseHeaders,
        });
    } catch (error) {
        console.error(
            `[auth] Backend proxy request failed: ${error instanceof Error ? error.name : "UnknownError"}`,
        );
        return apiError(502, "BACKEND_UNAVAILABLE", "Viraldy is temporarily unavailable.");
    }
}

function apiError(status: number, code: string, message: string): Response {
    return Response.json(
        {
            success: false,
            data: null,
            error: { code, message },
            request_id: "web-bff",
        },
        { status, headers: { "Cache-Control": "no-store" } },
    );
}

export const Route = createFileRoute("/api/backend/$")({
    server: {
        handlers: {
            GET: ({ request }) => proxyBackend(request),
            POST: ({ request }) => proxyBackend(request),
            PUT: ({ request }) => proxyBackend(request),
            PATCH: ({ request }) => proxyBackend(request),
            DELETE: ({ request }) => proxyBackend(request),
        },
    },
});
