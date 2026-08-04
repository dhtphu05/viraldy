import { createFileRoute, Outlet } from "@tanstack/react-router";

export const Route = createFileRoute("/tiktok-scorer")({
    head: () => ({ meta: [{ title: "TikTok Scorer — Viraldy" }] }),
    component: () => <Outlet />,
});
