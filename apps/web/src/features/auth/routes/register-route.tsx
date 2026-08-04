import { createFileRoute, redirect } from "@tanstack/react-router";
import { z } from "zod";

import { AuthPage } from "../components/auth-page";

const registerSearchSchema = z.object({
    returnTo: z.string().optional(),
    error: z.string().optional(),
});

export const Route = createFileRoute("/register")({
    validateSearch: (search) => registerSearchSchema.parse(search),
    beforeLoad: ({ context }) => {
        if (context.auth.authenticated) throw redirect({ to: "/dashboard" });
    },
    head: () => ({ meta: [{ title: "Create account — Viraldy" }] }),
    component: RegisterPage,
});

function RegisterPage() {
    const { auth } = Route.useRouteContext();
    const search = Route.useSearch();
    return <AuthPage auth={auth} intent="signup" {...search} />;
}
