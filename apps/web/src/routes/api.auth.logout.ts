import { createFileRoute } from "@tanstack/react-router";

import { logoutDestination } from "@/features/auth/auth-session.server";
import { hasValidMutationOrigin } from "@/features/auth/lib/auth-proxy";

export const Route = createFileRoute("/api/auth/logout")({
    server: {
        handlers: {
            POST: async ({ request }) => {
                if (
                    !hasValidMutationOrigin({
                        requestUrl: request.url,
                        origin: request.headers.get("origin") ?? undefined,
                    })
                ) {
                    return new Response("Forbidden", { status: 403 });
                }
                return new Response(null, {
                    status: 303,
                    headers: { Location: await logoutDestination(request) },
                });
            },
        },
    },
});
