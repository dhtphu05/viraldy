import { createFileRoute, Link } from "@tanstack/react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Check, ClipboardList, Loader2, Play, ShieldCheck } from "lucide-react";

import { useApiWorkspace } from "@/shared/hooks/use-workspace";
import {
    getBatchReview,
    respondToBatchItem,
    startBatchReview,
    type BatchReview,
} from "@/shared/api/tiktok-commercial-content";
import { AppShell } from "@/widgets/app-shell/app-shell";
import { PageHeader } from "@/shared/ui/page-header";
import { Button } from "@/shared/ui/button";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { StatusChip } from "@/shared/ui/status-chip";
import { toast } from "sonner";

export const Route = createFileRoute("/batch-reviews/$batchId")({
    head: () => ({ meta: [{ title: "Batch Creative Review — Viraldy" }] }),
    component: BatchReviewPage,
});

function BatchReviewPage() {
    const { batchId } = Route.useParams();
    const { workspaceId } = useApiWorkspace();
    const batch = useQuery({
        queryKey: ["market-batch-review", workspaceId, batchId],
        queryFn: () => getBatchReview(workspaceId!, batchId),
        enabled: Boolean(workspaceId),
    });
    const start = useMutation({
        mutationFn: () => startBatchReview(workspaceId!, batchId),
        onSuccess: (data) => {
            void data;
            void batch.refetch();
            toast.success("Batch review completed");
        },
        onError: (error) =>
            toast.error(error instanceof Error ? error.message : "Batch review failed"),
    });
    const respond = useMutation({
        mutationFn: ({
            itemId,
            action,
        }: {
            itemId: string;
            action: "TEST" | "FIX" | "RESHOOT" | "SKIP" | "INSUFFICIENT_EVIDENCE";
        }) => respondToBatchItem(workspaceId!, itemId, { response: "accepted", action }),
        onSuccess: () => void batch.refetch(),
        onError: (error) =>
            toast.error(error instanceof Error ? error.message : "Decision could not be saved"),
    });

    return (
        <AppShell>
            <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
                <PageHeader
                    title="Batch Creative Review"
                    description="See how many distinct ideas you have and what deserves action."
                    actions={
                        <Link to="/creative-library" search={{ import: undefined }}>
                            <Button variant="secondary" size="sm">
                                Back to Explorer
                            </Button>
                        </Link>
                    }
                />
                <SurfaceCard padding="md" className="border-primary/20 bg-primary/[0.03]">
                    <div className="flex items-start gap-3">
                        <ShieldCheck className="mt-0.5 h-5 w-5 text-primary" />
                        <p className="text-sm text-text-secondary">
                            Public market reach is excluded from portfolio decisions. Decisions use
                            available creative evidence and explicit seller responses.
                        </p>
                    </div>
                </SurfaceCard>
                {batch.isPending && <Loader2 className="h-5 w-5 animate-spin text-primary" />}
                {batch.isError && (
                    <SurfaceCard padding="lg">
                        <p className="text-sm text-text-primary">Batch review unavailable.</p>
                    </SurfaceCard>
                )}
                {batch.data && (
                    <BatchContent
                        batch={batch.data}
                        onStart={() => start.mutate()}
                        starting={start.isPending}
                        onAction={(itemId, action) => respond.mutate({ itemId, action })}
                    />
                )}
            </div>
        </AppShell>
    );
}

function BatchContent({
    batch,
    onStart,
    starting,
    onAction,
}: {
    batch: BatchReview;
    onStart: () => void;
    starting: boolean;
    onAction: (
        itemId: string,
        action: "TEST" | "FIX" | "RESHOOT" | "SKIP" | "INSUFFICIENT_EVIDENCE",
    ) => void;
}) {
    const decisions = (batch.summary.decisions ?? {}) as Record<string, number>;
    return (
        <>
            <div className="grid gap-3 sm:grid-cols-3">
                <Metric
                    label="Files"
                    value={String(batch.summary.file_count ?? batch.items.length)}
                />
                <Metric
                    label="Distinct ideas"
                    value={String(batch.summary.distinct_ideas ?? batch.items.length)}
                />
                <Metric
                    label="Needs action"
                    value={String((decisions.FIX ?? 0) + (decisions.RESHOOT ?? 0))}
                />
            </div>
            <SurfaceCard padding="none" className="overflow-hidden">
                <div className="flex items-center justify-between border-b border-divider px-4 py-3">
                    <div className="flex items-center gap-2">
                        <ClipboardList className="h-4 w-4 text-primary" />
                        <p className="text-sm font-semibold text-text-primary">
                            Portfolio decisions
                        </p>
                    </div>
                    <StatusChip tone={batch.status === "completed" ? "ok" : "info"}>
                        {batch.status}
                    </StatusChip>
                </div>
                <div className="divide-y divide-divider">
                    {batch.items.map((item) => (
                        <div
                            key={item.id}
                            className="grid gap-3 px-4 py-4 lg:grid-cols-[1.2fr_0.8fr_2fr_auto] lg:items-center"
                        >
                            <div>
                                <p className="text-sm font-medium text-text-primary">
                                    Creative {item.asset_id.slice(0, 8)}
                                </p>
                                <p className="mt-1 text-xs text-text-tertiary">
                                    {item.primary_reason ?? "Awaiting review"}
                                </p>
                            </div>
                            <StatusChip
                                tone={
                                    item.decision === "TEST"
                                        ? "ok"
                                        : item.decision === "INSUFFICIENT_EVIDENCE"
                                          ? "warn"
                                          : "info"
                                }
                            >
                                {item.decision ?? "QUEUED"}
                            </StatusChip>
                            <p className="text-xs text-text-secondary">
                                {item.recommended_action
                                    ? `Recommended: ${item.recommended_action}`
                                    : "No recommendation yet"}
                            </p>
                            <div className="flex flex-wrap gap-1.5">
                                <Button
                                    size="sm"
                                    variant="secondary"
                                    onClick={() => onAction(item.id, "TEST")}
                                >
                                    <Check className="h-3.5 w-3.5" /> Test
                                </Button>
                                <Button
                                    size="sm"
                                    variant="secondary"
                                    onClick={() => onAction(item.id, "FIX")}
                                >
                                    Fix
                                </Button>
                                <Button
                                    size="sm"
                                    variant="secondary"
                                    onClick={() => onAction(item.id, "RESHOOT")}
                                >
                                    Reshoot
                                </Button>
                            </div>
                        </div>
                    ))}
                </div>
                {batch.status !== "completed" && (
                    <div className="border-t border-divider p-4">
                        <Button onClick={onStart} disabled={starting}>
                            <Play className="h-4 w-4" />{" "}
                            {starting ? "Reviewing…" : "Start batch review"}
                        </Button>
                    </div>
                )}
            </SurfaceCard>
        </>
    );
}

function Metric({ label, value }: { label: string; value: string }) {
    return (
        <SurfaceCard padding="md">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-text-tertiary">
                {label}
            </p>
            <p className="mt-2 text-2xl font-semibold text-text-primary">{value}</p>
        </SurfaceCard>
    );
}
