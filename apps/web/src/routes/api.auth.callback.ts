import { createFileRoute } from "@tanstack/react-router";

import { completeAuthorization } from "@/features/auth/auth-session.server";

export const Route = createFileRoute("/api/auth/callback")({
    server: {
        handlers: {
            GET: async ({ request }) => {
                try {
                    return redirectResponse(await completeAuthorization(request));
                } catch (error) {
                    console.error(
                        `[auth] Failed to complete authorization: ${error instanceof Error ? error.name : "UnknownError"}`,
                    );
                    const fallback = new URL("/login", request.url);
                    fallback.searchParams.set("error", "callback_failed");
                    return redirectResponse(fallback);
                }
            },
        },
    },
});

function redirectResponse(destination: string | URL): Response {
    return new Response(null, { status: 303, headers: { Location: destination.toString() } });
}
