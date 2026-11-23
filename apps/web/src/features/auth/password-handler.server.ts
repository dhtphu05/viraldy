import { authRequestUrl } from "./auth-request.server";
import { authenticatePassword, PasswordSignInError } from "./auth-session.server";
import type { AuthIntent } from "./lib/auth-flow";
import { hasValidMutationOrigin } from "./lib/auth-proxy";

export async function passwordAuthResponse(
    request: Request,
    intent: AuthIntent,
): Promise<Response> {
    const headers = { "Cache-Control": "no-store" };
    if (
        !hasValidMutationOrigin({
            requestUrl: authRequestUrl(request).toString(),
            origin: request.headers.get("origin") ?? undefined,
        })
    )
        return Response.json({ authenticated: false }, { status: 403, headers });
    try {
        const returnTo = await authenticatePassword(request, intent);
        if (request.headers.get("content-type")?.includes("application/x-www-form-urlencoded")) {
            return new Response(null, {
                status: 303,
                headers: {
                    ...headers,
                    Location: new URL(returnTo, authRequestUrl(request)).toString(),
                },
            });
        }
        return Response.json({ authenticated: true, returnTo }, { headers });
    } catch (error) {
        const status = error instanceof PasswordSignInError ? error.status : 503;
        if (request.headers.get("content-type")?.includes("application/x-www-form-urlencoded")) {
            const url = new URL(
                intent === "signup" ? "/register" : "/login",
                authRequestUrl(request),
            );
            url.searchParams.set(
                "error",
                status === 401 ? "invalid_credentials" : "auth_unavailable",
            );
            return new Response(null, {
                status: 303,
                headers: { ...headers, Location: url.toString() },
            });
        }
        return Response.json({ authenticated: false }, { status, headers });
    }
}
