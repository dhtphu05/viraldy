import { createFileRoute } from "@tanstack/react-router";

import { refreshSession } from "@/features/auth/auth-session.server";
import { hasValidMutationOrigin } from "@/features/auth/lib/auth-proxy";

export const Route = createFileRoute("/api/auth/refresh")({
    server: {
        handlers: {
            POST: async ({ request }) => {
                if (
                    !hasValidMutationOrigin({
                        requestUrl: request.url,
                        origin: request.headers.get("origin") ?? undefined,
                    })
                ) {
                    return Response.json({ authenticated: false }, { status: 403 });
                }
                const authenticated = await refreshSession(request);
                return Response.json({ authenticated }, { status: authenticated ? 200 : 401 });
            },
        },
    },
});
