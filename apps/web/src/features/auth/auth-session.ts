import { createServerFn } from "@tanstack/react-start";

import type { CurrentUser } from "./lib/auth-contract";

export type AuthReason = "missing_session" | "session_expired" | "auth_unavailable" | null;

export type AuthSnapshot = {
    authenticated: boolean;
    user: CurrentUser | null;
    mode: "local_test" | "oidc" | "unavailable";
    enabled: boolean;
    reason: AuthReason;
};

export const getAuthSnapshot = createServerFn({ method: "GET" }).handler(
    async (): Promise<AuthSnapshot> => {
        const { loadAuthSnapshotForCurrentRequest } = await import("./auth-session.server");
        return loadAuthSnapshotForCurrentRequest();
    },
);
