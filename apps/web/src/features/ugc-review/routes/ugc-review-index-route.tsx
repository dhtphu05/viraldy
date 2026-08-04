import { createFileRoute } from "@tanstack/react-router";

import { UgcReviewForm } from "../components/ugc-review-form";
import { AppShell } from "@/widgets/app-shell/app-shell";

export const Route = createFileRoute("/ugc-review/")({
    validateSearch: (
        search: Record<string, unknown>,
    ): { campaignId?: string; upload?: boolean; workspaceId?: string } => ({
        campaignId: typeof search.campaignId === "string" ? search.campaignId : undefined,
        upload:
            search.upload === true ||
            search.upload === "true" ||
            search.upload === "1" ||
            search.upload === 1
                ? true
                : undefined,
        workspaceId: typeof search.workspaceId === "string" ? search.workspaceId : undefined,
    }),
    head: () => ({ meta: [{ title: "Review a UGC draft — Viraldy" }] }),
    component: UgcReviewIndexRoute,
});

function UgcReviewIndexRoute() {
    const { workspaceId } = Route.useSearch();
    return (
        <AppShell>
            <UgcReviewForm preferredWorkspaceId={workspaceId} />
        </AppShell>
    );
}
