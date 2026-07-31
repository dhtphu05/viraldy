import { createFileRoute, redirect } from "@tanstack/react-router";
import { z } from "zod";

import { AuthPage } from "../components/auth-page";

const authSearchSchema = z.object({
    returnTo: z.string().optional(),
    error: z.string().optional(),
    reason: z.string().optional(),
    loggedOut: z.union([z.string(), z.number()]).optional(),
});

export const Route = createFileRoute("/login")({
    validateSearch: (search) => authSearchSchema.parse(search),
    beforeLoad: ({ context }) => {
        if (context.auth.authenticated) throw redirect({ to: "/dashboard" });
    },
    head: () => ({ meta: [{ title: "Sign in — Viraldy" }] }),
    component: LoginPage,
});

function LoginPage() {
    const { auth } = Route.useRouteContext();
    const search = Route.useSearch();
    return <AuthPage auth={auth} intent="login" {...search} />;
}
