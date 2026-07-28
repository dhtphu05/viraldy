import { createFileRoute, Outlet } from "@tanstack/react-router";

export const Route = createFileRoute("/ugc-review")({
    head: () => ({ meta: [{ title: "UGC Review — Viraldy" }] }),
    component: () => <Outlet />,
});
