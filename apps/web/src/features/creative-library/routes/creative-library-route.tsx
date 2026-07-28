import { createFileRoute, Outlet } from "@tanstack/react-router";

export const Route = createFileRoute("/creative-library")({
    head: () => ({ meta: [{ title: "Creative Library — Viraldy" }] }),
    component: () => <Outlet />,
});
