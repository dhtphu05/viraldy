import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { AppShell } from "@/widgets/app-shell/app-shell";
import { PageHeader } from "@/shared/ui/page-header";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { MetricCard } from "@/shared/ui/metric-card";
import { StatusChip } from "@/shared/ui/status-chip";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { RelativeTime } from "@/shared/ui/relative-time";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import { EmptyState } from "@/shared/ui/empty-state";
import { DemoMediaTile } from "@/shared/ui/demo-media-tile";
import { RecommendationCardPerf } from "@/features/performance/components/recommendation-card-perf";
import { EvidenceDrawer } from "@/features/performance/components/evidence-drawer";
import { ImportPerformanceDialog } from "@/features/performance/components/import-performance-dialog";
import { ReportsSheet } from "@/features/performance/components/reports-sheet";
import { useAppStore } from "@/app/store/app-store";
import {
    seedCampaignPerf,
    seedFatigueAlerts,
    seedPatterns,
    overviewBusinessMetrics,
} from "@/features/performance/mocks/performanceSeed";
import {
    fmtMoney,
    fmtNum,
    decisionTone,
    generateVariants,
} from "@/features/performance/lib/performanceEngine";
import type { PerfRecommendation, DecisionGroup } from "@/features/performance/types/performance";
import {
    BarChart3,
    TrendingUp,
    ArrowRight,
    Sparkles,
    AlertTriangle,
    RefreshCcw,
    Wrench,
    Ban,
    PauseCircle,
    Search,
    FileDown,
    Download,
    Upload,
    ChevronRight,
} from "lucide-react";
import { toast } from "sonner";
import type { Metric } from "@/shared/types";

export const Route = createFileRoute("/performance/")({
    validateSearch: (search: Record<string, unknown>) => ({
        import:
            search.import === true ||
            search.import === "true" ||
            search.import === "1" ||
            search.import === 1
                ? true
                : undefined,
    }),
    head: () => ({
        meta: [
            { title: "Performance — Viraldy" },
            {
                name: "description",
                content:
                    "Turn creative decisions into GMV, gross profit, and the next campaign action.",
            },
        ],
    }),
    component: PerformancePage,
});

const groupMeta: Record<
    DecisionGroup,
    { icon: typeof Sparkles; label: string; description: string }
> = {
    Scale: { icon: Sparkles, label: "Scale", description: "Ready for controlled expansion." },
    Fix: { icon: Wrench, label: "Fix", description: "Creative or downstream fixes suggested." },
    Rehire: { icon: RefreshCcw, label: "Rehire", description: "High-efficiency creators." },
    Hold: { icon: PauseCircle, label: "Hold", description: "Pause paid amplification for now." },
    Stop: { icon: Ban, label: "Stop", description: "Cut underperformers to protect margin." },
    Refresh: { icon: TrendingUp, label: "Refresh", description: "Refresh hook or first scene." },
};

function PerformancePage() {
    const routeSearch = Route.useSearch();
    const navigate = useNavigate();
    const recs = useAppStore((s) => s.perfRecommendations);
    const accepted = useAppStore((s) => s.perfAcceptedRecs);
    const dismissed = useAppStore((s) => s.perfDismissedRecs);
    const snoozed = useAppStore((s) => s.perfSnoozedRecs);
    const activity = useAppStore((s) => s.perfActivity);
    const filters = useAppStore((s) => s.perfFilters);
    const setFilters = useAppStore((s) => s.setPerfFilters);
    const acceptRec = useAppStore((s) => s.acceptPerfRec);
    const unacceptRec = useAppStore((s) => s.unacceptPerfRec);
    const addVariants = useAppStore((s) => s.addVariants);

    const [openImport, setOpenImport] = useState(false);
    const [openReports, setOpenReports] = useState(false);
    const [selected, setSelected] = useState<PerfRecommendation | null>(null);
    const [groupFilter, setGroupFilter] = useState<DecisionGroup | "All">("All");

    useEffect(() => {
        const importParam = new URLSearchParams(window.location.search).get("import");
        if (!routeSearch.import && importParam !== "1" && importParam !== "true") return;
        setOpenImport(true);
        void navigate({ to: "/performance", replace: true, search: {} });
    }, [navigate, routeSearch.import]);

    const business = overviewBusinessMetrics();

    const metrics: Metric[] = [
        {
            id: "m-gmv",
            label: "GMV influenced",
            value: fmtMoney(business.gmv),
            delta: "+18%",
            deltaTone: "ok",
            hint: "vs previous 30 days",
        },
        {
            id: "m-gp",
            label: "Gross profit influenced",
            value: fmtMoney(business.grossProfit),
            delta: "+9%",
            deltaTone: "ok",
            hint: "vs previous 30 days",
        },
        {
            id: "m-eff",
            label: "Sample efficiency",
            value: `$${business.sampleEfficiency.toFixed(1)}`,
            delta: "per $1 sample",
            deltaTone: "neutral",
            hint: "Blended across campaigns",
        },
        {
            id: "m-assets",
            label: "Active assets w/ data",
            value: fmtNum(business.activeAssets),
            delta: `${seedCampaignPerf.length} campaigns`,
            deltaTone: "info",
            hint: "Mapped to performance rows",
        },
    ];

    const decisionCounts = useMemo(() => {
        const map: Record<DecisionGroup, PerfRecommendation[]> = {
            Scale: [],
            Fix: [],
            Rehire: [],
            Hold: [],
            Stop: [],
            Refresh: [],
        };
        for (const r of recs) {
            if (dismissed[r.id] || snoozed[r.id]) continue;
            map[r.group].push(r);
        }
        return map;
    }, [recs, dismissed, snoozed]);

    const visibleRecs = useMemo(() => {
        return recs.filter((r) => {
            if (dismissed[r.id]) return false;
            if (snoozed[r.id] && new Date(snoozed[r.id]) > new Date()) return false;
            if (groupFilter !== "All" && r.group !== groupFilter) return false;
            if (filters.search) {
                const q = filters.search.toLowerCase();
                if (!(r.title + r.object + r.reason).toLowerCase().includes(q)) return false;
            }
            return true;
        });
    }, [recs, dismissed, snoozed, groupFilter, filters.search]);

    const topRecommendation = visibleRecs.find((r) => !accepted.includes(r.id)) ?? visibleRecs[0];
    const activeFilterLabels = [
        filters.search ? `Search: ${filters.search}` : null,
        groupFilter !== "All" ? `Decision: ${groupFilter}` : null,
        filters.dateRange !== "30d" ? `Range: ${filters.dateRange}` : null,
    ].filter((label): label is string => Boolean(label));

    const onCreateVariants = (rec: PerfRecommendation) => {
        const pattern =
            seedPatterns.find((p) => p.campaignId === rec.campaignId) ?? seedPatterns[0];
        const generated = generateVariants(
            pattern.angle,
            pattern.hook,
            seedCampaignPerf.find((c) => c.campaignId === rec.campaignId)?.product ?? "product",
        );
        addVariants(
            generated.map((g) => ({
                id: g.id,
                name: g.name,
                patternId: pattern.id,
                keep: g.keep,
                change: g.change,
                creator: g.creator,
                cta: g.cta,
                priority: g.priority,
                reason: g.reason,
                createdAt: new Date().toISOString(),
            })),
        );
        toast.success(`Generated ${generated.length} variants`, {
            description: "Available in Campaign Pack drafts.",
        });
    };

    return (
        <AppShell>
            <div className="flex flex-col gap-6">
                <PageHeader
                    title="Performance"
                    description="Connect creative decisions to GMV, gross profit, sample efficiency, and the next campaign action."
                    actions={
                        <>
                            <Button variant="ghost" size="sm" onClick={() => setOpenReports(true)}>
                                <FileDown className="h-4 w-4" /> View reports
                            </Button>
                            <Button size="sm" onClick={() => setOpenImport(true)}>
                                <Upload className="h-4 w-4" /> Import performance data
                            </Button>
                        </>
                    }
                />

                {/* Decision summary */}
                <section aria-labelledby="what-next">
                    <div className="mb-3 flex items-end justify-between gap-3">
                        <div>
                            <h2 id="what-next" className="text-sm font-semibold text-text-primary">
                                What should you do next?
                            </h2>
                            <p className="mt-0.5 text-xs text-text-tertiary">
                                Click a summary to filter recommendations below.
                            </p>
                        </div>
                        {groupFilter !== "All" && (
                            <Button variant="ghost" size="sm" onClick={() => setGroupFilter("All")}>
                                Clear filter
                            </Button>
                        )}
                    </div>
                    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
                        {(Object.keys(groupMeta) as DecisionGroup[]).map((g) => {
                            const items = decisionCounts[g];
                            const meta = groupMeta[g];
                            const active = groupFilter === g;
                            const Icon = meta.icon;
                            return (
                                <button
                                    key={g}
                                    type="button"
                                    onClick={() => setGroupFilter(active ? "All" : g)}
                                    className={`surface-card inner-top-highlight flex flex-col gap-2 p-3 text-left transition ${active ? "ring-1 ring-primary" : "hover:bg-surface-soft/70"}`}
                                >
                                    <div className="flex items-center justify-between">
                                        <StatusChip tone={decisionTone[g]}>{meta.label}</StatusChip>
                                        <Icon className="h-4 w-4 text-text-tertiary" />
                                    </div>
                                    <p className="tabular text-xl font-semibold text-text-primary">
                                        {items.length}
                                    </p>
                                    <p className="line-clamp-2 text-xs text-text-secondary">
                                        {meta.description}
                                    </p>
                                    {items[0] && (
                                        <p className="truncate text-[11px] text-text-tertiary">
                                            Top: {items[0].object}
                                        </p>
                                    )}
                                </button>
                            );
                        })}
                    </div>
                </section>

                {/* Business metrics */}
                <section aria-labelledby="business-metrics">
                    <h2 id="business-metrics" className="sr-only">
                        Business metrics
                    </h2>
                    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                        {metrics.map((m) => (
                            <MetricCard key={m.id} metric={m} />
                        ))}
                    </div>
                </section>

                {/* Filter bar */}
                <SurfaceCard padding="none" className="flex flex-wrap items-center gap-2 p-3">
                    <div className="relative min-w-[220px] flex-1">
                        <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-text-tertiary" />
                        <Input
                            placeholder="Search recommendations, campaigns, creators, assets"
                            aria-label="Search recommendations, campaigns, creators, and assets"
                            className="h-9 pl-8 text-sm"
                            value={filters.search ?? ""}
                            onChange={(e) => setFilters({ search: e.target.value })}
                        />
                    </div>
                    <Select
                        value={filters.dateRange}
                        onValueChange={(v) =>
                            setFilters({ dateRange: v as typeof filters.dateRange })
                        }
                    >
                        <SelectTrigger className="h-9 w-[140px]">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="7d">Last 7 days</SelectItem>
                            <SelectItem value="14d">Last 14 days</SelectItem>
                            <SelectItem value="30d">Last 30 days</SelectItem>
                            <SelectItem value="90d">Last 90 days</SelectItem>
                        </SelectContent>
                    </Select>
                    <Select
                        value={groupFilter}
                        onValueChange={(v) => setGroupFilter(v as DecisionGroup | "All")}
                    >
                        <SelectTrigger className="h-9 w-[140px]">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="All">All decisions</SelectItem>
                            {(Object.keys(groupMeta) as DecisionGroup[]).map((g) => (
                                <SelectItem key={g} value={g}>
                                    {groupMeta[g].label}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    <div className="ml-auto flex items-center gap-2">
                        {(filters.search || groupFilter !== "All") && (
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                    setFilters({ search: "" });
                                    setGroupFilter("All");
                                }}
                            >
                                Clear all
                            </Button>
                        )}
                    </div>
                </SurfaceCard>

                {activeFilterLabels.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5">
                        {activeFilterLabels.map((label) => (
                            <span
                                key={label}
                                className="rounded-full bg-surface-soft px-2 py-0.5 text-xs text-text-secondary"
                            >
                                {label}
                            </span>
                        ))}
                    </div>
                )}

                {topRecommendation && (
                    <SurfaceCard padding="md" className="border-primary/20 bg-primary-soft/35">
                        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                            {topRecommendation.mediaUrl && (
                                <DemoMediaTile
                                    mediaUrl={topRecommendation.mediaUrl}
                                    mediaKind={topRecommendation.mediaKind}
                                    posterUrl={topRecommendation.posterUrl}
                                    seed={topRecommendation.objectId ?? topRecommendation.id}
                                    label={topRecommendation.object}
                                    badges={[
                                        topRecommendation.mediaAspectRatio ?? "media",
                                        "top signal",
                                    ]}
                                    aspect={topRecommendation.mediaAspectRatio ?? "16 / 9"}
                                    fit={
                                        topRecommendation.mediaAspectRatio === "9:16"
                                            ? "contain"
                                            : "cover"
                                    }
                                    className="w-full max-w-[180px] rounded-md bg-black"
                                />
                            )}
                            <div className="min-w-0">
                                <div className="flex flex-wrap items-center gap-2">
                                    <StatusChip tone={decisionTone[topRecommendation.group]}>
                                        {topRecommendation.kind}
                                    </StatusChip>
                                    <StatusChip
                                        tone={
                                            topRecommendation.confidence === "High"
                                                ? "ok"
                                                : topRecommendation.confidence === "Medium"
                                                  ? "info"
                                                  : "warn"
                                        }
                                    >
                                        Confidence: {topRecommendation.confidence}
                                    </StatusChip>
                                </div>
                                <p className="mt-2 text-sm font-semibold text-text-primary">
                                    {topRecommendation.title}
                                </p>
                                <p className="mt-1 text-sm text-text-secondary">
                                    {topRecommendation.nextAction}
                                </p>
                            </div>
                            <div className="flex flex-wrap gap-2">
                                <Button
                                    size="sm"
                                    variant="secondary"
                                    onClick={() => setSelected(topRecommendation)}
                                >
                                    View evidence
                                </Button>
                                {topRecommendation.group === "Scale" && (
                                    <Button
                                        size="sm"
                                        onClick={() => onCreateVariants(topRecommendation)}
                                    >
                                        Create variants
                                    </Button>
                                )}
                            </div>
                        </div>
                    </SurfaceCard>
                )}

                {/* Two-column: recommendations + winning patterns/fatigue */}
                <div className="grid gap-4 lg:grid-cols-[minmax(0,65fr)_minmax(0,35fr)]">
                    <SurfaceCard padding="none" className="flex flex-col">
                        <div className="flex items-center justify-between border-b border-hairline px-5 py-3">
                            <div>
                                <h3 className="text-sm font-semibold">Recommended actions</h3>
                                <p className="mt-0.5 text-xs text-text-tertiary">
                                    {visibleRecs.length} active · {Object.keys(dismissed).length}{" "}
                                    dismissed
                                </p>
                            </div>
                            <Button variant="ghost" size="sm" asChild>
                                <Link
                                    to="/performance/$campaignId"
                                    params={{ campaignId: seedCampaignPerf[0].campaignId }}
                                >
                                    View campaign details <ChevronRight className="h-4 w-4" />
                                </Link>
                            </Button>
                        </div>
                        <div className="grid gap-3 p-4 md:grid-cols-2">
                            {visibleRecs.length === 0 ? (
                                <div className="col-span-full">
                                    <EmptyState
                                        title="No urgent performance action detected"
                                        description="Current campaign signals are mixed or incomplete. Continue collecting data or review individual assets."
                                        icon={BarChart3}
                                    />
                                </div>
                            ) : (
                                visibleRecs.map((r) => (
                                    <RecommendationCardPerf
                                        key={r.id}
                                        rec={r}
                                        onOpen={() => setSelected(r)}
                                        onAccept={() => {
                                            acceptRec(r.id);
                                            toast.success("Recommendation accepted", {
                                                action: {
                                                    label: "Undo",
                                                    onClick: () => unacceptRec(r.id),
                                                },
                                            });
                                        }}
                                        className={accepted.includes(r.id) ? "opacity-60" : ""}
                                    />
                                ))
                            )}
                        </div>
                    </SurfaceCard>

                    <div className="flex flex-col gap-4">
                        <SurfaceCard padding="none">
                            <div className="border-b border-hairline px-5 py-3">
                                <h3 className="text-sm font-semibold">Winning pattern</h3>
                                <p className="mt-0.5 text-xs text-text-tertiary">
                                    Directional signal across active assets
                                </p>
                            </div>
                            <div className="space-y-3 p-4">
                                {seedPatterns.slice(0, 1).map((p) => (
                                    <div key={p.id} className="space-y-2 text-sm">
                                        <StatusChip tone="ok">{p.angle}</StatusChip>
                                        <p className="text-sm italic text-text-secondary">
                                            {p.hook}
                                        </p>
                                        <dl className="mt-2 space-y-1 text-xs">
                                            <Row k="Creator type" v={p.creatorType} />
                                            <Row k="Product reveal" v={p.productReveal} />
                                            <Row k="Proof" v={p.proof} />
                                            <Row k="CTA" v={p.cta} />
                                            <Row k="Signal" v={p.signal} />
                                        </dl>
                                        <div className="flex flex-wrap gap-2 pt-2">
                                            <Button
                                                size="sm"
                                                variant="secondary"
                                                onClick={() =>
                                                    navigate({
                                                        to: "/performance/$campaignId",
                                                        params: { campaignId: p.campaignId },
                                                    })
                                                }
                                            >
                                                Open campaign
                                            </Button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </SurfaceCard>

                        <SurfaceCard padding="none">
                            <div className="border-b border-hairline px-5 py-3">
                                <h3 className="text-sm font-semibold">Fatigue signals</h3>
                                <p className="mt-0.5 text-xs text-text-tertiary">
                                    Directional decline in CTR or conversion
                                </p>
                            </div>
                            <div className="divide-y divide-hairline">
                                {seedFatigueAlerts.map((f) => (
                                    <div key={f.id} className="p-4">
                                        <div className="flex items-center gap-2">
                                            <StatusChip
                                                tone={f.state === "high" ? "destructive" : "warn"}
                                            >
                                                {f.state === "high"
                                                    ? "High risk"
                                                    : "Prepare refresh"}
                                            </StatusChip>
                                            <p className="truncate text-sm font-medium">
                                                {f.assetName}
                                            </p>
                                        </div>
                                        <p className="mt-1.5 text-xs text-text-secondary">
                                            {f.reason}
                                        </p>
                                        <p className="mt-1 text-xs text-text-tertiary">
                                            Suggested: {f.suggestion}
                                        </p>
                                        <div className="mt-2 flex gap-2">
                                            <Button
                                                size="sm"
                                                variant="secondary"
                                                onClick={() =>
                                                    navigate({
                                                        to: "/performance/$campaignId",
                                                        params: { campaignId: f.campaignId },
                                                    })
                                                }
                                            >
                                                Review
                                            </Button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </SurfaceCard>
                    </div>
                </div>

                {/* Campaign performance table */}
                <SurfaceCard padding="none">
                    <div className="flex items-center justify-between border-b border-hairline px-5 py-3">
                        <div>
                            <h3 className="text-sm font-semibold">Campaign performance</h3>
                            <p className="mt-0.5 text-xs text-text-tertiary">
                                Click a row to open detail
                            </p>
                        </div>
                        <Button variant="ghost" size="sm" onClick={() => setOpenImport(true)}>
                            <Upload className="h-4 w-4" /> Import metrics
                        </Button>
                    </div>
                    <div className="grid gap-3 p-3 sm:hidden">
                        {seedCampaignPerf.map((c) => (
                            <button
                                key={c.campaignId}
                                type="button"
                                className="rounded-md border border-hairline bg-surface p-3 text-left transition-colors hover:bg-surface-soft focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                                onClick={() =>
                                    navigate({
                                        to: "/performance/$campaignId",
                                        params: { campaignId: c.campaignId },
                                    })
                                }
                            >
                                <div className="flex items-start justify-between gap-3">
                                    <div className="min-w-0">
                                        <p className="truncate text-sm font-medium text-text-primary">
                                            {c.campaignName}
                                        </p>
                                        <p className="truncate text-xs text-text-tertiary">
                                            {c.product}
                                        </p>
                                    </div>
                                    <ChevronRight className="mt-0.5 h-4 w-4 shrink-0 text-text-tertiary" />
                                </div>
                                <div className="mt-3 flex flex-wrap items-center gap-2">
                                    <StatusChip tone={c.status === "Live" ? "ok" : "info"} dot>
                                        {c.status}
                                    </StatusChip>
                                    <StatusChip tone={decisionTone[c.primaryDecision]}>
                                        {c.primaryDecision}
                                    </StatusChip>
                                </div>
                                <dl className="mt-3 grid grid-cols-2 gap-3 text-xs">
                                    <div>
                                        <dt className="text-text-tertiary">GMV</dt>
                                        <dd className="tabular font-medium text-text-primary">
                                            {fmtMoney(c.gmv)}
                                        </dd>
                                    </div>
                                    <div>
                                        <dt className="text-text-tertiary">Gross profit</dt>
                                        <dd className="tabular font-medium text-text-primary">
                                            {fmtMoney(c.grossProfit)}
                                        </dd>
                                    </div>
                                    <div>
                                        <dt className="text-text-tertiary">Sample eff.</dt>
                                        <dd className="tabular font-medium text-text-primary">
                                            ${c.sampleEfficiency.toFixed(1)}
                                        </dd>
                                    </div>
                                    <div>
                                        <dt className="text-text-tertiary">Updated</dt>
                                        <dd className="tabular font-medium text-text-primary">
                                            <RelativeTime value={c.lastUpdated} />
                                        </dd>
                                    </div>
                                </dl>
                            </button>
                        ))}
                    </div>
                    <div className="hidden overflow-x-auto sm:block">
                        <table className="w-full min-w-[900px] text-sm">
                            <thead className="sticky top-0 z-10 bg-surface-soft/95 backdrop-blur-sm">
                                <tr className="text-left text-xs font-medium text-text-tertiary">
                                    <th className="px-4 py-2.5">Campaign</th>
                                    <th className="px-3 py-2.5">Status</th>
                                    <th className="px-3 py-2.5 text-right">GMV</th>
                                    <th className="px-3 py-2.5 text-right">Gross profit</th>
                                    <th className="px-3 py-2.5 text-right">Sample eff.</th>
                                    <th className="px-3 py-2.5 text-right">Ad spend</th>
                                    <th className="px-3 py-2.5 text-right">ROAS</th>
                                    <th className="px-3 py-2.5">Decision</th>
                                    <th className="px-3 py-2.5">Updated</th>
                                    <th />
                                </tr>
                            </thead>
                            <tbody>
                                {seedCampaignPerf.map((c) => (
                                    <tr
                                        key={c.campaignId}
                                        className="cursor-pointer border-t border-hairline hover:bg-surface-soft/50"
                                        onClick={() =>
                                            navigate({
                                                to: "/performance/$campaignId",
                                                params: { campaignId: c.campaignId },
                                            })
                                        }
                                    >
                                        <td className="px-4 py-3">
                                            <p className="font-medium text-text-primary">
                                                {c.campaignName}
                                            </p>
                                            <p className="text-xs text-text-tertiary">
                                                {c.product}
                                            </p>
                                        </td>
                                        <td className="px-3 py-3">
                                            <StatusChip
                                                tone={c.status === "Live" ? "ok" : "info"}
                                                dot
                                            >
                                                {c.status}
                                            </StatusChip>
                                        </td>
                                        <td className="px-3 py-3 text-right tabular">
                                            {fmtMoney(c.gmv)}
                                        </td>
                                        <td className="px-3 py-3 text-right tabular">
                                            {fmtMoney(c.grossProfit)}
                                        </td>
                                        <td className="px-3 py-3 text-right tabular">
                                            ${c.sampleEfficiency.toFixed(1)}
                                        </td>
                                        <td className="px-3 py-3 text-right tabular">
                                            {fmtMoney(c.adSpend)}
                                        </td>
                                        <td className="px-3 py-3 text-right tabular">
                                            {c.roas === null ? (
                                                <span className="text-text-tertiary">Organic</span>
                                            ) : (
                                                c.roas.toFixed(2)
                                            )}
                                        </td>
                                        <td className="px-3 py-3">
                                            <StatusChip tone={decisionTone[c.primaryDecision]}>
                                                {c.primaryDecision}
                                            </StatusChip>
                                        </td>
                                        <td className="px-3 py-3 text-xs text-text-tertiary">
                                            <RelativeTime value={c.lastUpdated} />
                                        </td>
                                        <td className="px-3 py-3">
                                            <ChevronRight className="h-4 w-4 text-text-tertiary" />
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </SurfaceCard>

                {/* Recent activity */}
                <SurfaceCard padding="none">
                    <div className="border-b border-hairline px-5 py-3">
                        <h3 className="text-sm font-semibold">Recent performance activity</h3>
                    </div>
                    <div className="divide-y divide-hairline">
                        {activity.length === 0 ? (
                            <EmptyState
                                title="No recent activity yet"
                                description="Accept a recommendation, import data, or generate variants to see events here."
                                icon={TrendingUp}
                            />
                        ) : (
                            activity.slice(0, 8).map((e) => (
                                <div
                                    key={e.id}
                                    className="flex items-center justify-between gap-3 px-5 py-3 text-sm"
                                >
                                    <div className="min-w-0">
                                        <p className="truncate text-text-primary">{e.detail}</p>
                                    </div>
                                    <span className="shrink-0 text-xs text-text-tertiary">
                                        <RelativeTime value={e.at} />
                                    </span>
                                </div>
                            ))
                        )}
                    </div>
                </SurfaceCard>
            </div>

            <EvidenceDrawer
                rec={selected}
                open={!!selected}
                onOpenChange={(v) => !v && setSelected(null)}
                onGenerateVariants={onCreateVariants}
            />
            <ImportPerformanceDialog open={openImport} onOpenChange={setOpenImport} />
            <ReportsSheet open={openReports} onOpenChange={setOpenReports} />
        </AppShell>
    );
}

function Row({ k, v }: { k: string; v: string }) {
    return (
        <div className="flex justify-between gap-3">
            <dt className="text-text-tertiary">{k}</dt>
            <dd className="text-right text-text-secondary">{v}</dd>
        </div>
    );
}
