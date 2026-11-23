import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";

import { getPublicMarketInsight } from "@/shared/api/market-insights";
import { Button } from "@/shared/ui/button";
import { SurfaceCard } from "@/shared/ui/surface-card";

export const Route = createFileRoute("/insights/$slug")({
    head: () => ({ meta: [{ title: "Market Insight — Viraldy" }] }),
    component: MarketInsightPage,
});

function MarketInsightPage() {
    const { slug } = Route.useParams();
    const snapshot = useQuery({
        queryKey: ["public-market-insight", slug],
        queryFn: () => getPublicMarketInsight(slug),
    });
    const payload = snapshot.data?.payload ?? {};
    const list = (key: string) =>
        Array.isArray(payload[key])
            ? payload[key].filter((item): item is string => typeof item === "string")
            : [];
    return (
        <main className="min-h-screen bg-background px-5 py-12 text-text-primary sm:px-10">
            <div className="mx-auto max-w-4xl space-y-6">
                {snapshot.isPending && (
                    <p className="text-sm text-text-secondary">Loading public market insight…</p>
                )}
                {snapshot.isError && (
                    <SurfaceCard padding="lg">
                        <p className="text-lg font-semibold">Insight unavailable</p>
                        <p className="mt-2 text-sm text-text-secondary">
                            This snapshot is not published or no longer exists.
                        </p>
                    </SurfaceCard>
                )}
                {snapshot.data && (
                    <>
                        <header>
                            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">
                                Viraldy Market Insight
                            </p>
                            <h1 className="mt-3 text-3xl font-semibold tracking-tight sm:text-5xl">
                                {snapshot.data.title}
                            </h1>
                            <p className="mt-3 text-sm text-text-secondary">
                                {snapshot.data.category ?? "Public commercial creative"} ·{" "}
                                {snapshot.data.market ?? "Market not specified"}
                            </p>
                        </header>
                        <SurfaceCard padding="md" className="border-primary/20 bg-primary/[0.03]">
                            <div className="flex gap-3">
                                <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
                                <div>
                                    <p className="text-sm font-semibold">
                                        MARKET PREVALENT / PUBLIC DISTRIBUTION SIGNAL
                                    </p>
                                    <p className="mt-1 text-sm text-text-secondary">
                                        Observed prevalence does not mean sales performance, GMV,
                                        ROAS, or a winning creative.
                                    </p>
                                </div>
                            </div>
                        </SurfaceCard>
                        <div className="grid gap-4 sm:grid-cols-3">
                            <SnapshotMetric
                                label="Observed"
                                value={payload.observed_count ?? payload.sample_size ?? "Unknown"}
                            />
                            <SnapshotMetric
                                label="Families"
                                value={payload.family_count ?? "Unknown"}
                            />
                            <SnapshotMetric
                                label="Period"
                                value={formatRange(snapshot.data.date_range)}
                            />
                        </div>
                        {list("patterns").length > 0 && (
                            <SnapshotList
                                title="Most observed patterns"
                                values={list("patterns")}
                            />
                        )}
                        {list("limitations").length > 0 && (
                            <SnapshotList title="Limitations" values={list("limitations")} />
                        )}
                        <Button
                            onClick={() => {
                                window.location.href = "/creative-library";
                            }}
                        >
                            Explore public creatives
                        </Button>
                    </>
                )}
            </div>
        </main>
    );
}

function SnapshotMetric({ label, value }: { label: string; value: unknown }) {
    return (
        <SurfaceCard padding="md">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-text-tertiary">
                {label}
            </p>
            <p className="mt-2 text-lg font-semibold text-text-primary">{String(value)}</p>
        </SurfaceCard>
    );
}
function SnapshotList({ title, values }: { title: string; values: string[] }) {
    return (
        <SurfaceCard padding="md">
            <h2 className="text-sm font-semibold">{title}</h2>
            <ul className="mt-3 space-y-2 text-sm text-text-secondary">
                {values.map((value) => (
                    <li key={value}>• {value}</li>
                ))}
            </ul>
        </SurfaceCard>
    );
}
function formatRange(range: Record<string, string>) {
    return range.min && range.max ? `${range.min} → ${range.max}` : "Not specified";
}
