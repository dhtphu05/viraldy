import { createFileRoute } from "@tanstack/react-router";

import { beginAuthorization } from "@/features/auth/auth-session.server";

export const Route = createFileRoute("/api/auth/login")({
    server: {
        handlers: {
            GET: async ({ request }) => {
                const url = new URL(request.url);
                const intent = url.searchParams.get("intent") === "signup" ? "signup" : "login";
                try {
                    return redirectResponse(
                        await beginAuthorization(request, intent, url.searchParams.get("returnTo")),
                        302,
                    );
                } catch (error) {
                    console.error(
                        `[auth] Failed to begin authorization: ${error instanceof Error ? error.name : "UnknownError"}`,
                    );
                    const fallback = new URL(
                        intent === "signup" ? "/register" : "/login",
                        request.url,
                    );
                    fallback.searchParams.set("error", "auth_unavailable");
                    return redirectResponse(fallback, 302);
                }
            },
        },
    },
});

function redirectResponse(destination: string | URL, status: 302): Response {
    return new Response(null, { status, headers: { Location: destination.toString() } });
}
