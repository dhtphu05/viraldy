const BACKEND_PROXY_PREFIX = "/api/backend/";

export function backendPathFromRequest(requestUrl: string): string {
    const url = new URL(requestUrl);
    if (!url.pathname.startsWith(BACKEND_PROXY_PREFIX)) {
        throw new Error("Invalid backend proxy path");
    }
    const relativePath = url.pathname.slice(BACKEND_PROXY_PREFIX.length);
    if (!relativePath) throw new Error("Invalid backend proxy path");
    return `/${relativePath}${url.search}`;
}

export function hasValidMutationOrigin({
    requestUrl,
    origin,
}: {
    requestUrl: string;
    origin: string | undefined;
}): boolean {
    if (!origin) return false;
    try {
        return new URL(origin).origin === new URL(requestUrl).origin;
    } catch {
        return false;
    }
}

export type DuplexRequestInit = RequestInit & { duplex?: "half" };

export function upstreamRequestInit(request: Request, headers: Headers): DuplexRequestInit {
    const body = request.method === "GET" || request.method === "HEAD" ? undefined : request.body;
    return {
        method: request.method,
        headers,
        body,
        redirect: "manual",
        ...(body ? { duplex: "half" as const } : {}),
    };
}
