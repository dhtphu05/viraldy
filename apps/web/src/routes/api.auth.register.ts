import { createFileRoute } from "@tanstack/react-router";

import { passwordAuthResponse } from "@/features/auth/password-handler.server";

export const Route = createFileRoute("/api/auth/register")({
    server: { handlers: { POST: ({ request }) => passwordAuthResponse(request, "signup") } },
});
