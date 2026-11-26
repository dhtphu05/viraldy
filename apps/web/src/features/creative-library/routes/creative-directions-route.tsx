import { createFileRoute, Link } from "@tanstack/react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { CheckCircle2, FileVideo, ShieldCheck } from "lucide-react";

import { useApiWorkspace } from "@/shared/hooks/use-workspace";
import {
    listCreativeDirections,
    selectCreativeDirection,
    type CreativeDirection,
} from "@/shared/api/tiktok-commercial-content";
import { AppShell } from "@/widgets/app-shell/app-shell";
import { PageHeader } from "@/shared/ui/page-header";
import { Button } from "@/shared/ui/button";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { StatusChip } from "@/shared/ui/status-chip";
import { toast } from "sonner";

export const Route = createFileRoute("/creative-directions/$adaptationId")({
    head: () => ({ meta: [{ title: "Creative Directions — Viraldy" }] }),
    component: CreativeDirectionsPage,
});

function CreativeDirectionsPage() {
    const { adaptationId } = Route.useParams();
    const { workspaceId } = useApiWorkspace();
    const directions = useQuery({
        queryKey: ["market-creative-directions", workspaceId, adaptationId],
        queryFn: () => listCreativeDirections(workspaceId!, adaptationId),
        enabled: Boolean(workspaceId),
    });
    const select = useMutation({
        mutationFn: (directionId: string) => selectCreativeDirection(workspaceId!, directionId),
        onSuccess: () => {
            toast.success("Direction selected", {
                description: "You can now use it as context for TikTok Score & Fix.",
            });
            void directions.refetch();
        },
        onError: (error) =>
            toast.error(error instanceof Error ? error.message : "Selection failed"),
    });

    return (
        <AppShell>
            <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
                <PageHeader
                    title="3 Creative Directions Worth Testing"
                    description="Product-specific bets grounded in the selected public market reference."
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
                        <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
                        <div>
                            <p className="text-sm font-semibold text-text-primary">
                                MARKET-INFORMED
                            </p>
                            <p className="mt-1 text-sm text-text-secondary">
                                These are relevant market hypotheses, not winning-creative or
                                sales-performance claims.
                            </p>
                        </div>
                    </div>
                </SurfaceCard>
                {directions.isPending && <DirectionsSkeleton />}
                {directions.isError && (
                    <SurfaceCard padding="lg">
                        <p className="text-sm font-semibold text-text-primary">
                            Directions unavailable
                        </p>
                        <p className="mt-1 text-sm text-text-secondary">
                            Generate directions from an analyzed market creative first.
                        </p>
                    </SurfaceCard>
                )}
                {directions.data && directions.data.length === 0 && (
                    <SurfaceCard padding="lg">
                        <p className="text-sm font-semibold text-text-primary">
                            No directions found
                        </p>
                        <p className="mt-1 text-sm text-text-secondary">
                            The adaptation did not persist three direction records.
                        </p>
                    </SurfaceCard>
                )}
                {directions.data && directions.data.length > 0 && (
                    <div className="grid gap-4 lg:grid-cols-3">
                        {directions.data.map((direction) => (
                            <DirectionCard
                                key={direction.id}
                                direction={direction}
                                onSelect={() => select.mutate(direction.id)}
                                selecting={select.isPending}
                            />
                        ))}
                    </div>
                )}
            </div>
        </AppShell>
    );
}

function DirectionCard({
    direction,
    onSelect,
    selecting,
}: {
    direction: CreativeDirection;
    onSelect: () => void;
    selecting: boolean;
}) {
    const payload = direction.payload;
    const provenance = direction.provenance;
    const text = (key: string, fallback: string) => {
        const value = payload[key];
        return typeof value === "string" && value ? value : fallback;
    };
    const list = (key: string) => {
        const value = payload[key];
        return Array.isArray(value)
            ? value.filter((item): item is string => typeof item === "string")
            : [];
    };
    return (
        <SurfaceCard padding="md" className="flex h-full flex-col">
            <div className="flex items-center justify-between gap-2">
                <StatusChip tone={direction.status === "selected" ? "ok" : "info"}>
                    Direction {direction.direction_number}
                </StatusChip>
                {direction.status === "selected" && (
                    <CheckCircle2 className="h-4 w-4 text-success" />
                )}
            </div>
            <h2 className="mt-4 text-lg font-semibold text-text-primary">{direction.title}</h2>
            <div className="mt-4 space-y-3 text-sm">
                <DirectionField label="Best for" value={text("buyer", "Buyer context unknown")} />
                <DirectionField
                    label="Angle"
                    value={text("angle", "Product-specific angle to validate")}
                />
                <DirectionField
                    label="Opening"
                    value={text("opening_visual", "Opening visual not specified")}
                />
                <DirectionField
                    label="Demo"
                    value={text("demo_mechanism", "Visible product demo to define")}
                />
                <DirectionField
                    label="Proof"
                    value={text("proof_mechanism", "Proof mechanism not specified")}
                />
                <DirectionField
                    label="Test hypothesis"
                    value={text("test_hypothesis", "Hypothesis not specified")}
                />
            </div>
            {list("keep_variables").length > 0 && (
                <DirectionList label="Keep" values={list("keep_variables")} tone="positive" />
            )}
            {list("change_variables").length > 0 && (
                <DirectionList label="Adapt" values={list("change_variables")} tone="neutral" />
            )}
            <div className="mt-auto pt-5">
                <p className="mb-3 text-[11px] text-text-tertiary">
                    Evidence: {String(provenance.evidence_status ?? "market_signal_only")} · Source
                    references retained
                </p>
                <div className="flex flex-wrap gap-2">
                    <Button
                        size="sm"
                        onClick={onSelect}
                        disabled={selecting || direction.status === "selected"}
                    >
                        {direction.status === "selected" ? "Selected" : "Select direction"}
                    </Button>
                    <a href={`/tiktok-scorer/new?directionId=${encodeURIComponent(direction.id)}`}>
                        <Button size="sm" variant="secondary">
                            <FileVideo className="h-4 w-4" /> Upload and Check It
                        </Button>
                    </a>
                </div>
            </div>
        </SurfaceCard>
    );
}

function DirectionField({ label, value }: { label: string; value: string }) {
    return (
        <div>
            <p className="text-[10px] font-semibold uppercase tracking-wide text-text-tertiary">
                {label}
            </p>
            <p className="mt-0.5 text-text-primary">{value}</p>
        </div>
    );
}

function DirectionList({
    label,
    values,
    tone,
}: {
    label: string;
    values: string[];
    tone: "positive" | "neutral";
}) {
    return (
        <div
            className={`mt-4 rounded-lg p-3 ${tone === "positive" ? "bg-success/10" : "bg-surface-soft"}`}
        >
            <p className="text-xs font-semibold text-text-primary">{label}</p>
            <ul className="mt-1 space-y-1 text-xs text-text-secondary">
                {values.slice(0, 3).map((value) => (
                    <li key={value}>• {value}</li>
                ))}
            </ul>
        </div>
    );
}

function DirectionsSkeleton() {
    return (
        <div className="grid gap-4 lg:grid-cols-3">
            {[1, 2, 3].map((item) => (
                <SurfaceCard key={item} padding="md" className="h-96 animate-pulse">
                    <div className="h-5 w-24 rounded bg-surface-soft" />
                    <div className="mt-6 h-7 w-3/4 rounded bg-surface-soft" />
                    <div className="mt-6 space-y-4">
                        <div className="h-4 rounded bg-surface-soft" />
                        <div className="h-4 rounded bg-surface-soft" />
                        <div className="h-4 rounded bg-surface-soft" />
                    </div>
                </SurfaceCard>
            ))}
        </div>
    );
}
