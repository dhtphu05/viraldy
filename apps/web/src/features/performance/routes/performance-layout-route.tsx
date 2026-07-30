import { createFileRoute, Outlet } from "@tanstack/react-router";

export const Route = createFileRoute("/performance")({
    head: () => ({ meta: [{ title: "Performance — Viraldy" }] }),
    component: () => <Outlet />,
});
