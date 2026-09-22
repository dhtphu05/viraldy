import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { AppShell } from "@/widgets/app-shell/app-shell";
import { PageHeader } from "@/shared/ui/page-header";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { DecisionHero } from "@/shared/ui/decision-hero";
import { MetricStrip, type MetricStripItem } from "@/shared/ui/metric-strip";
import { StatusChip } from "@/shared/ui/status-chip";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { RelativeTime } from "@/shared/ui/relative-time";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import { EmptyState } from "@/shared/ui/empty-state";
import { DemoMediaTile } from "@/shared/ui/demo-media-tile";
import { ViraldyIcon } from "@/shared/ui/viraldy-icon";
import { RecommendationCardPerf } from "@/features/performance/components/recommendation-card-perf";
import { EvidenceDrawer } from "@/features/performance/components/evidence-drawer";
import { ImportPerformanceDialog } from "@/features/performance/components/import-performance-dialog";
import { ReportsSheet } from "@/features/performance/components/reports-sheet";
import { useAppStore } from "@/app/store/app-store";
import {
    seedCampaignPerf,
    seedFatigueAlerts,
    seedPatterns,
    seedPerfAssets,
} from "@/features/performance/mocks/performanceSeed";
import {
    fmtMoney,
    fmtNum,
    decisionTone,
    generateVariants,
    grossProfit,
} from "@/features/performance/lib/performanceEngine";
import { isWithinDemoDays } from "@/shared/mocks/time";
import type { PerfRecommendation, DecisionGroup } from "@/features/performance/types/performance";
import { BarChart3, TrendingUp, Search, FileDown, ChevronRight } from "lucide-react";
import { toast } from "sonner";

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

const decisionGroups: DecisionGroup[] = ["Scale", "Fix", "Rehire", "Refresh", "Hold", "Stop"];

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
        void navigate({ to: "/performance", replace: true, search: { import: undefined } });
    }, [navigate, routeSearch.import]);

    const rangeDays = Number.parseInt(filters.dateRange, 10);
    const filteredAssets = useMemo(
        () => seedPerfAssets.filter((asset) => isWithinDemoDays(asset.createdAt, rangeDays)),
        [rangeDays],
    );
    const filteredCampaigns = useMemo(
        () =>
            seedCampaignPerf.filter((campaign) =>
                isWithinDemoDays(campaign.lastUpdated, rangeDays),
            ),
        [rangeDays],
    );
    const business = useMemo(() => {
        const gmv = filteredAssets.reduce((total, asset) => total + asset.gmv, 0);
        const grossProfitTotal = filteredAssets.reduce(
            (total, asset) => total + grossProfit(asset),
            0,
        );
        const sampleCost = filteredAssets.reduce((total, asset) => total + asset.sampleCost, 0);
        return {
            gmv,
            grossProfit: grossProfitTotal,
            sampleEfficiency: sampleCost > 0 ? gmv / sampleCost : 0,
            activeAssets: filteredAssets.length,
        };
    }, [filteredAssets]);

    const metrics: MetricStripItem[] = [
        {
            id: "m-gmv",
            label: "GMV influenced",
            value: fmtMoney(business.gmv),
            delta: "+18%",
            tone: "ok",
            hint: "vs previous 30 days",
        },
        {
            id: "m-gp",
            label: "Gross profit influenced",
            value: fmtMoney(business.grossProfit),
            delta: "+9%",
            tone: "ok",
            hint: "vs previous 30 days",
        },
        {
            id: "m-eff",
            label: "Sample efficiency",
            value: `$${business.sampleEfficiency.toFixed(1)}`,
            delta: "per $1 sample",
            tone: "neutral",
            hint: "Blended across campaigns",
        },
        {
            id: "m-assets",
            label: "Active assets w/ data",
            value: fmtNum(business.activeAssets),
            delta: `${filteredCampaigns.length} campaigns`,
            tone: "info",
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
            if (!isWithinDemoDays(r.createdAt, rangeDays)) continue;
            map[r.group].push(r);
        }
        return map;
    }, [recs, dismissed, snoozed, rangeDays]);

    const visibleRecs = useMemo(() => {
        return recs.filter((r) => {
            if (dismissed[r.id]) return false;
            if (snoozed[r.id] && new Date(snoozed[r.id]) > new Date()) return false;
            if (!isWithinDemoDays(r.createdAt, rangeDays)) return false;
            if (groupFilter !== "All" && r.group !== groupFilter) return false;
            if (filters.search) {
                const q = filters.search.toLowerCase();
                if (!(r.title + r.object + r.reason).toLowerCase().includes(q)) return false;
            }
            return true;
        });
    }, [recs, dismissed, snoozed, groupFilter, filters.search, rangeDays]);

    const topRecommendation = visibleRecs.find((r) => !accepted.includes(r.id)) ?? visibleRecs[0];
    const activeFilterLabels = [
        filters.search ? `Search: ${filters.search}` : null,
        groupFilter !== "All" ? `Decision: ${groupFilter}` : null,
        filters.dateRange !== "30d" ? `Range: ${filters.dateRange}` : null,
    ].filter((label): label is string => Boolean(label));

    const clearPerformanceFilters = () => {
        setFilters({ search: "", dateRange: "30d" });
        setGroupFilter("All");
    };

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

    const onAcceptRecommendation = (rec: PerfRecommendation) => {
        acceptRec(rec.id);
        toast.success("Recommendation accepted", {
            action: {
                label: "Undo",
                onClick: () => unacceptRec(rec.id),
            },
        });
    };

    return (
        <AppShell>
            <div className="flex flex-col gap-6">
                <PageHeader
                    title="Performance"
                    description="Connect creative decisions to GMV, gross profit, sample efficiency, and the next campaign action. Current values are a demo scenario until imported data is added."
                    actions={
                        <>
                            <Button variant="ghost" size="sm" onClick={() => setOpenReports(true)}>
                                <FileDown className="h-4 w-4" /> View reports
                            </Button>
                            <Button size="sm" onClick={() => setOpenImport(true)}>
                                <ViraldyIcon name="importPerformance" size="sm" />
                                Import performance data
                            </Button>
                        </>
                    }
                />

                {topRecommendation && (
                    <DecisionHero
                        eyebrow="Top recommended decision"
                        actionLabel={topRecommendation.title}
                        reason={
                            <>
                                <p>{topRecommendation.reason}</p>
                                <p className="mt-1">
                                    <span className="font-medium text-text-primary">Next:</span>{" "}
                                    {topRecommendation.nextAction}
                                </p>
                            </>
                        }
                        confidence={topRecommendation.confidence}
                        statusTone={decisionTone[topRecommendation.group]}
                        score={topRecommendation.supportingMetrics[0]?.value}
                        scoreLabel={topRecommendation.supportingMetrics[0]?.label}
                        media={
                            topRecommendation.mediaUrl ? (
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
                                    className="w-full max-w-[180px] rounded-md bg-black lg:ml-auto"
                                />
                            ) : undefined
                        }
                        primaryAction={
                            topRecommendation.group === "Scale" ? (
                                <Button
                                    size="sm"
                                    onClick={() => onCreateVariants(topRecommendation)}
                                >
                                    <ViraldyIcon name="createVariants" size="sm" />
                                    Create variants
                                </Button>
                            ) : (
                                <Button
                                    size="sm"
                                    onClick={() => onAcceptRecommendation(topRecommendation)}
                                >
                                    Accept recommendation
                                </Button>
                            )
                        }
                        secondaryAction={
                            <Button
                                size="sm"
                                variant="secondary"
                                onClick={() => setSelected(topRecommendation)}
                            >
                                Review evidence
                            </Button>
                        }
                    />
                )}

                <section aria-labelledby="decision-filter" className="hidden sm:block">
                    <div className="mb-2 flex items-center justify-between gap-3">
                        <h2
                            id="decision-filter"
                            className="text-xs font-semibold uppercase text-text-tertiary"
                        >
                            Decision filter
                        </h2>
                        {groupFilter !== "All" && (
                            <Button variant="ghost" size="sm" onClick={() => setGroupFilter("All")}>
                                Clear
                            </Button>
                        )}
                    </div>
                    <div className="flex flex-wrap gap-1 rounded-lg bg-surface p-1">
                        {(["All", ...decisionGroups] as const).map((group) => {
                            const active = groupFilter === group;
                            const count =
                                group === "All"
                                    ? null
                                    : decisionCounts[group as DecisionGroup].length;
                            return (
                                <button
                                    key={group}
                                    type="button"
                                    aria-pressed={active}
                                    onClick={() => setGroupFilter(group)}
                                    className={`flex min-h-9 items-center justify-center gap-2 rounded-md px-3 text-sm font-medium transition-colors duration-[180ms] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                                        active
                                            ? "bg-primary text-primary-foreground"
                                            : "text-text-secondary hover:bg-surface-soft hover:text-text-primary"
                                    }`}
                                >
                                    {group}
                                    {count !== null && (
                                        <span
                                            className={`tabular text-xs ${active ? "text-primary-foreground/80" : "text-text-tertiary"}`}
                                        >
                                            {count}
                                        </span>
                                    )}
                                </button>
                            );
                        })}
                    </div>
                </section>

                <MetricStrip metrics={metrics} ariaLabel="Performance outcomes" />

                <div className="flex flex-wrap items-end justify-between gap-3">
                    <div>
                        <h2
                            id="performance-recommendations"
                            className="text-sm font-semibold text-text-primary"
                        >
                            Recommended actions
                        </h2>
                        <p className="mt-0.5 text-xs text-text-tertiary">
                            {visibleRecs.length} active · {Object.keys(dismissed).length} dismissed
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

                <div
                    className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap sm:items-center"
                    aria-label="Recommendation filters"
                >
                    <div className="relative col-span-2 min-w-0 sm:flex-[1_1_280px]">
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
                        <SelectTrigger
                            className="h-9 w-full min-w-0 sm:w-[140px]"
                            aria-label="Performance date range"
                        >
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="7d">Last 7 days</SelectItem>
                            <SelectItem value="14d">Last 14 days</SelectItem>
                            <SelectItem value="30d">Last 30 days</SelectItem>
                            <SelectItem value="90d">Last 90 days</SelectItem>
                        </SelectContent>
                    </Select>
                    <div className="min-w-0 sm:hidden">
                        <Select
                            value={groupFilter}
                            onValueChange={(v) => setGroupFilter(v as DecisionGroup | "All")}
                        >
                            <SelectTrigger className="h-9 w-full" aria-label="Performance decision">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="All">All decisions</SelectItem>
                                {decisionGroups.map((group) => (
                                    <SelectItem key={group} value={group}>
                                        {group}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    {(filters.search || groupFilter !== "All" || filters.dateRange !== "30d") && (
                        <Button
                            variant="ghost"
                            size="sm"
                            className="col-span-2 w-fit sm:col-auto"
                            onClick={clearPerformanceFilters}
                        >
                            Clear all
                        </Button>
                    )}
                </div>

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

                <div className="flex flex-col gap-8">
                    <section className="min-w-0" aria-labelledby="performance-recommendations">
                        <div className="mt-3 divide-y divide-divider rounded-lg bg-surface">
                            {visibleRecs.length === 0 ? (
                                <div>
                                    <EmptyState
                                        title={
                                            activeFilterLabels.length
                                                ? "No recommendations match these filters"
                                                : "No urgent performance action detected"
                                        }
                                        description={
                                            activeFilterLabels.length
                                                ? "Clear the active search, decision, or date filter to review all available recommendations."
                                                : "Current campaign signals are mixed or incomplete. Import fresh data or continue collecting results."
                                        }
                                        icon={BarChart3}
                                        tone={activeFilterLabels.length ? "neutral" : "success"}
                                        action={
                                            <>
                                                {activeFilterLabels.length > 0 && (
                                                    <Button
                                                        variant="secondary"
                                                        size="sm"
                                                        onClick={clearPerformanceFilters}
                                                    >
                                                        Clear filters
                                                    </Button>
                                                )}
                                                <Button
                                                    size="sm"
                                                    onClick={() => setOpenImport(true)}
                                                >
                                                    <ViraldyIcon
                                                        name="importPerformance"
                                                        size="sm"
                                                    />
                                                    Import performance data
                                                </Button>
                                            </>
                                        }
                                    />
                                </div>
                            ) : (
                                visibleRecs.map((r) => (
                                    <RecommendationCardPerf
                                        key={r.id}
                                        rec={r}
                                        onOpen={() => setSelected(r)}
                                        onAccept={() => onAcceptRecommendation(r)}
                                        className={accepted.includes(r.id) ? "opacity-60" : ""}
                                    />
                                ))
                            )}
                        </div>
                    </section>

                    <section className="grid gap-8 border-t border-divider pt-6 lg:grid-cols-2">
                        <div className="min-w-0">
                            <div>
                                <h3 className="text-sm font-semibold">Winning pattern</h3>
                                <p className="mt-0.5 text-xs text-text-tertiary">
                                    Directional signal across active assets
                                </p>
                            </div>
                            <div className="mt-4 space-y-3">
                                {seedPatterns.slice(0, 1).map((p) => (
                                    <div key={p.id} className="space-y-2 text-sm">
                                        <StatusChip tone="ok">{p.angle}</StatusChip>
                                        <p className="text-sm italic text-text-secondary">
                                            {p.hook}
                                        </p>
                                        <dl className="mt-2 grid gap-x-6 gap-y-1 text-xs sm:grid-cols-2">
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
                        </div>

                        <div className="min-w-0">
                            <div>
                                <h3 className="text-sm font-semibold">Fatigue signals</h3>
                                <p className="mt-0.5 text-xs text-text-tertiary">
                                    Directional decline in CTR or conversion
                                </p>
                            </div>
                            <div className="mt-2 divide-y divide-divider">
                                {seedFatigueAlerts.map((f) => (
                                    <div key={f.id} className="py-3">
                                        <div className="flex flex-wrap items-center gap-2">
                                            <StatusChip
                                                tone={f.state === "high" ? "destructive" : "warn"}
                                            >
                                                {f.state === "high"
                                                    ? "High risk"
                                                    : "Prepare refresh"}
                                            </StatusChip>
                                            <p className="min-w-0 text-sm font-medium">
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
                        </div>
                    </section>
                </div>

                {/* Campaign performance table */}
                <SurfaceCard variant="outlined" padding="none">
                    <div className="flex items-center justify-between border-b border-hairline px-5 py-3">
                        <div>
                            <h3 className="text-sm font-semibold">Campaign performance</h3>
                            <p className="mt-0.5 text-xs text-text-tertiary">
                                Click a row to open detail
                            </p>
                        </div>
                        <Button variant="ghost" size="sm" onClick={() => setOpenImport(true)}>
                            <ViraldyIcon name="importPerformance" size="sm" /> Import metrics
                        </Button>
                    </div>
                    <div className="grid gap-3 p-3 sm:hidden">
                        {filteredCampaigns.map((c) => (
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
                            <thead className="sticky top-0 z-10 bg-surface-soft">
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
                                {filteredCampaigns.map((c) => (
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

                <section className="border-t border-divider pt-6">
                    <div>
                        <h3 className="text-sm font-semibold">Recent performance activity</h3>
                    </div>
                    <div className="mt-2 divide-y divide-divider">
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
                                    className="flex items-center justify-between gap-3 py-3 text-sm"
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
                </section>
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
