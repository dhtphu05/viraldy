import { createFileRoute, Outlet } from "@tanstack/react-router";

export const Route = createFileRoute("/campaigns")({
    head: () => ({ meta: [{ title: "Campaigns — Viraldy" }] }),
    component: () => <Outlet />,
});
