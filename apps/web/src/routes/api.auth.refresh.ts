import { createFileRoute } from "@tanstack/react-router";

import { refreshSession } from "@/features/auth/auth-session.server";
import { authRequestUrl } from "@/features/auth/auth-request.server";
import { hasValidMutationOrigin } from "@/features/auth/lib/auth-proxy";

export const Route = createFileRoute("/api/auth/refresh")({
    server: {
        handlers: {
            POST: async ({ request }) => {
                if (
                    !hasValidMutationOrigin({
                        requestUrl: authRequestUrl(request).toString(),
                        origin: request.headers.get("origin") ?? undefined,
                    })
                ) {
                    return Response.json({ authenticated: false }, { status: 403 });
                }
                try {
                    const authenticated = await refreshSession(request);
                    return Response.json(
                        { authenticated },
                        {
                            status: authenticated ? 200 : 401,
                            headers: { "Cache-Control": "no-store" },
                        },
                    );
                } catch {
                    return Response.json(
                        { authenticated: false },
                        {
                            status: 503,
                            headers: { "Cache-Control": "no-store" },
                        },
                    );
                }
            },
        },
    },
});
