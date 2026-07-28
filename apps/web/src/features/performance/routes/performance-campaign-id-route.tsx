import { createFileRoute, Link, notFound, useNavigate } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { AppShell } from "@/widgets/app-shell/app-shell";
import { PageHeader } from "@/shared/ui/page-header";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { Button } from "@/shared/ui/button";
import { StatusChip } from "@/shared/ui/status-chip";
import { EmptyState } from "@/shared/ui/empty-state";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/shared/ui/tabs";
import { Checkbox } from "@/shared/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter,
} from "@/shared/ui/dialog";
import { EvidenceDrawer } from "@/features/performance/components/evidence-drawer";
import { ImportPerformanceDialog } from "@/features/performance/components/import-performance-dialog";
import { useAppStore } from "@/app/store/app-store";
import {
    seedCampaignPerf,
    seedPerfAssets,
    seedPatterns,
    seedFatigueAlerts,
    seedTrends,
    seedCreatorPerf,
    seedImportIssues,
} from "@/features/performance/mocks/performanceSeed";
import {
    fmtMoney,
    fmtPct,
    fmtNum,
    decisionTone,
    grossProfit,
    roasLabel,
    gmvPerSample,
    diagnoseAsset,
    bestOnAttention,
    bestOnConversion,
    bestOnProfit,
    bestOnSampleEfficiency,
    bestPaidReady,
    generateVariants,
    tableToCsv,
    downloadBlob,
} from "@/features/performance/lib/performanceEngine";
import { toast } from "sonner";
import { formatDistanceToNow } from "date-fns";
import {
    ArrowLeft,
    BarChart3,
    ChevronRight,
    FileDown,
    Upload,
    Sparkles,
    RefreshCcw,
    Wrench,
    PauseCircle,
    Ban,
    ShieldCheck,
    ArrowUpRight,
} from "lucide-react";
import type { PerfAsset, PerfRecommendation } from "@/features/performance/types/performance";
import {
    ResponsiveContainer,
    LineChart,
    Line,
    XAxis,
    YAxis,
    Tooltip,
    CartesianGrid,
    ScatterChart,
    Scatter,
    ZAxis,
} from "recharts";

export const Route = createFileRoute("/performance/$campaignId")({
    head: () => ({ meta: [{ title: "Campaign performance — Viraldy" }] }),
    component: CampaignPerformancePage,
    notFoundComponent: () => (
        <AppShell>
            <EmptyState
                title="Campaign performance not found"
                description="This campaign may not have performance data mapped yet."
                icon={BarChart3}
                action={
                    <Button asChild size="sm">
                        <Link to="/performance">Back to Performance</Link>
                    </Button>
                }
            />
        </AppShell>
    ),
});

function CampaignPerformancePage() {
    const { campaignId } = Route.useParams();
    const navigate = useNavigate();
    const summary = seedCampaignPerf.find((c) => c.campaignId === campaignId);
    const assets = useMemo(
        () => seedPerfAssets.filter((a) => a.campaignId === campaignId),
        [campaignId],
    );
    const trend = seedTrends[campaignId] ?? [];
    const patterns = seedPatterns.filter((p) => p.campaignId === campaignId);
    const fatigue = seedFatigueAlerts.filter((f) => f.campaignId === campaignId);
    const allRecs = useAppStore((s) => s.perfRecommendations);
    const recs = useMemo(
        () => allRecs.filter((r) => r.campaignId === campaignId),
        [allRecs, campaignId],
    );
    const accept = useAppStore((s) => s.acceptPerfRec);
    const addVariants = useAppStore((s) => s.addVariants);
    const savePattern = useAppStore((s) => s.savePattern);
    const dismissed = useAppStore((s) => s.perfDismissedRecs);
    const accepted = useAppStore((s) => s.perfAcceptedRecs);

    const [tab, setTab] = useState("decisions");
    const [selectedRec, setSelectedRec] = useState<PerfRecommendation | null>(null);
    const [openImport, setOpenImport] = useState(false);
    const [selectedAssets, setSelectedAssets] = useState<string[]>([]);
    const [openCompare, setOpenCompare] = useState(false);
    const [chartMetric, setChartMetric] = useState<"gmv" | "orders" | "ctr" | "sampleEfficiency">(
        "gmv",
    );

    if (!summary) throw notFound();

    const medianCtr = assets.length ? median(assets.map((a) => a.ctr)) : 0;
    const medianOrders = assets.length ? median(assets.map((a) => a.orders)) : 0;

    const grouped: Record<string, PerfRecommendation[]> = {};
    for (const r of recs) {
        if (dismissed[r.id]) continue;
        (grouped[r.group] ||= []).push(r);
    }

    const toggleAsset = (id: string) =>
        setSelectedAssets((s) =>
            s.includes(id) ? s.filter((x) => x !== id) : s.length >= 4 ? s : [...s, id],
        );

    const onGenerateVariants = () => {
        const p = patterns[0];
        if (!p) return toast.error("No winning pattern for this campaign yet.");
        const generated = generateVariants(p.angle, p.hook, summary.product);
        addVariants(
            generated.map((g) => ({
                id: g.id,
                name: g.name,
                patternId: p.id,
                keep: g.keep,
                change: g.change,
                creator: g.creator,
                cta: g.cta,
                priority: g.priority,
                reason: g.reason,
                createdAt: new Date().toISOString(),
            })),
        );
        toast.success(`Generated ${generated.length} next-test variants`);
    };

    const exportAssetsCsv = () => {
        const cols = [
            "name",
            "creator",
            "angle",
            "hook",
            "ugcScore",
            "views",
            "ctr",
            "orders",
            "gmv",
            "grossProfit",
            "roas",
        ];
        const rows = assets.map((a) => ({
            name: a.name,
            creator: a.creator,
            angle: a.angle,
            hook: a.hook,
            ugcScore: a.ugcScore,
            views: a.views,
            ctr: (a.ctr * 100).toFixed(2) + "%",
            orders: a.orders,
            gmv: a.gmv,
            grossProfit: grossProfit(a),
            roas: roasLabel(a),
        }));
        downloadBlob(
            `${summary.campaignName.toLowerCase().replace(/\s+/g, "-")}-asset-performance.csv`,
            tableToCsv(rows, cols),
            "text/csv",
        );
        toast.success("Asset CSV downloaded");
    };

    return (
        <AppShell>
            <div className="flex flex-col gap-6">
                <div>
                    <Link
                        to="/performance"
                        className="mb-2 inline-flex items-center gap-1 text-xs text-text-tertiary hover:text-text-primary"
                    >
                        <ArrowLeft className="h-3 w-3" /> Performance
                    </Link>
                    <PageHeader
                        title={summary.campaignName}
                        description={`${summary.product} · ${summary.status} · Last updated ${formatDistanceToNow(new Date(summary.lastUpdated), { addSuffix: true })}`}
                        actions={
                            <>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => setOpenImport(true)}
                                >
                                    <Upload className="h-4 w-4" /> Import data
                                </Button>
                                <Button variant="ghost" size="sm" onClick={exportAssetsCsv}>
                                    <FileDown className="h-4 w-4" /> Export
                                </Button>
                                <Button size="sm" onClick={onGenerateVariants}>
                                    <Sparkles className="h-4 w-4" /> Generate next test
                                </Button>
                            </>
                        }
                    />
                </div>

                {/* Compact metric strip */}
                <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
                    <Stat label="GMV" value={fmtMoney(summary.gmv)} />
                    <Stat label="Gross profit" value={fmtMoney(summary.grossProfit)} />
                    <Stat
                        label="Sample efficiency"
                        value={`$${summary.sampleEfficiency.toFixed(1)}`}
                        sub="per $1 sample"
                    />
                    <Stat
                        label="ROAS"
                        value={summary.roas === null ? "Organic" : summary.roas.toFixed(2)}
                    />
                    <Stat
                        label="Active assets"
                        value={String(summary.activeAssets)}
                        sub={`${summary.rightsReady} Spark-ready`}
                    />
                </div>

                <Tabs value={tab} onValueChange={setTab}>
                    <TabsList className="w-full sm:w-auto">
                        <TabsTrigger value="decisions">Decisions</TabsTrigger>
                        <TabsTrigger value="assets">Assets</TabsTrigger>
                        <TabsTrigger value="patterns">Creative patterns</TabsTrigger>
                        <TabsTrigger value="trends">Trends</TabsTrigger>
                        <TabsTrigger value="data-quality">Data quality</TabsTrigger>
                    </TabsList>

                    {/* -------- DECISIONS -------- */}
                    <TabsContent value="decisions" className="mt-4 space-y-4">
                        {patterns[0] && (
                            <SurfaceCard padding="none">
                                <div className="border-b border-hairline px-5 py-3">
                                    <h3 className="text-sm font-semibold">Scale winning angle</h3>
                                </div>
                                <div className="grid gap-4 p-5 md:grid-cols-[minmax(0,1fr)_auto]">
                                    <div className="min-w-0">
                                        <StatusChip tone="ok" className="mb-2">
                                            {patterns[0].angle}
                                        </StatusChip>
                                        <p className="text-sm text-text-primary">
                                            The {patterns[0].angle.toLowerCase()} angle is
                                            outperforming other groups on gross profit, orders, and
                                            sample efficiency.
                                        </p>
                                        <p className="mt-1 text-xs text-text-secondary">
                                            Estimated opportunity:{" "}
                                            <span className="font-medium">
                                                +$2,600 gross profit
                                            </span>{" "}
                                            if the next controlled test performs within the current
                                            range.
                                        </p>
                                        <div className="mt-3 flex flex-wrap gap-2">
                                            <Button size="sm" onClick={onGenerateVariants}>
                                                <Sparkles className="h-4 w-4" /> Generate three
                                                variants
                                            </Button>
                                            <Button
                                                size="sm"
                                                variant="secondary"
                                                onClick={() => {
                                                    savePattern(patterns[0]);
                                                    toast.success("Pattern saved");
                                                }}
                                            >
                                                Save to Pattern Library
                                            </Button>
                                        </div>
                                    </div>
                                    <StatusChip tone="info">
                                        Confidence: {patterns[0].confidence}
                                    </StatusChip>
                                </div>
                            </SurfaceCard>
                        )}

                        {Object.keys(grouped).length === 0 ? (
                            <SurfaceCard>
                                <EmptyState
                                    title="No urgent action for this campaign"
                                    description="Signals are healthy or waiting for more data."
                                    icon={BarChart3}
                                />
                            </SurfaceCard>
                        ) : (
                            (["Scale", "Fix", "Rehire", "Refresh", "Hold", "Stop"] as const).map(
                                (g) =>
                                    grouped[g]?.length ? (
                                        <SurfaceCard key={g} padding="none">
                                            <div className="flex items-center gap-2 border-b border-hairline px-5 py-3">
                                                <StatusChip tone={decisionTone[g]}>{g}</StatusChip>
                                                <span className="text-xs text-text-tertiary">
                                                    {grouped[g].length} recommendation
                                                    {grouped[g].length > 1 ? "s" : ""}
                                                </span>
                                            </div>
                                            <div className="divide-y divide-hairline">
                                                {grouped[g].map((r) => (
                                                    <div
                                                        key={r.id}
                                                        className={`grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 px-5 py-4 ${accepted.includes(r.id) ? "opacity-60" : ""}`}
                                                    >
                                                        <div className="min-w-0">
                                                            <p className="truncate text-sm font-medium">
                                                                {r.title}
                                                            </p>
                                                            <p className="mt-1 line-clamp-2 text-xs text-text-secondary">
                                                                {r.reason}
                                                            </p>
                                                            <p className="mt-1 text-xs text-text-tertiary">
                                                                Impact: {r.estimatedImpact} ·
                                                                Confidence: {r.confidence}
                                                            </p>
                                                        </div>
                                                        <div className="flex items-center gap-2">
                                                            <Button
                                                                size="sm"
                                                                variant="ghost"
                                                                onClick={() => setSelectedRec(r)}
                                                            >
                                                                Evidence
                                                            </Button>
                                                            <Button
                                                                size="sm"
                                                                onClick={() => {
                                                                    accept(r.id);
                                                                    toast.success("Accepted");
                                                                }}
                                                            >
                                                                Accept
                                                            </Button>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </SurfaceCard>
                                    ) : null,
                            )
                        )}
                    </TabsContent>

                    {/* -------- ASSETS -------- */}
                    <TabsContent value="assets" className="mt-4 space-y-4">
                        <SurfaceCard padding="none">
                            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-hairline px-5 py-3">
                                <div>
                                    <h3 className="text-sm font-semibold">Asset performance</h3>
                                    <p className="text-xs text-text-tertiary">
                                        {selectedAssets.length} selected · pick 2–4 to compare
                                    </p>
                                </div>
                                <div className="flex items-center gap-2">
                                    <Button size="sm" variant="ghost" onClick={exportAssetsCsv}>
                                        <FileDown className="h-4 w-4" /> Export CSV
                                    </Button>
                                    <Button
                                        size="sm"
                                        disabled={selectedAssets.length < 2}
                                        onClick={() => setOpenCompare(true)}
                                    >
                                        Compare selected
                                    </Button>
                                </div>
                            </div>
                            <div className="overflow-x-auto">
                                <table className="w-full min-w-[1100px] text-sm">
                                    <thead className="bg-surface-soft/60">
                                        <tr className="text-left text-xs font-medium text-text-tertiary">
                                            <th className="w-10 px-3 py-2.5" />
                                            <th className="px-3 py-2.5">Asset</th>
                                            <th className="px-3 py-2.5">Creator</th>
                                            <th className="px-3 py-2.5">Angle</th>
                                            <th className="px-3 py-2.5">Rights</th>
                                            <th className="px-3 py-2.5 text-right">UGC</th>
                                            <th className="px-3 py-2.5 text-right">Views</th>
                                            <th className="px-3 py-2.5 text-right">CTR</th>
                                            <th className="px-3 py-2.5 text-right">Orders</th>
                                            <th className="px-3 py-2.5 text-right">GMV</th>
                                            <th className="px-3 py-2.5 text-right">Gross profit</th>
                                            <th className="px-3 py-2.5 text-right">ROAS</th>
                                            <th className="px-3 py-2.5">Signals</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {assets.map((a) => {
                                            const diags = diagnoseAsset(a, medianCtr, medianOrders);
                                            const gp = grossProfit(a);
                                            return (
                                                <tr
                                                    key={a.id}
                                                    className="border-t border-hairline hover:bg-surface-soft/50"
                                                >
                                                    <td className="px-3 py-3">
                                                        <Checkbox
                                                            checked={selectedAssets.includes(a.id)}
                                                            onCheckedChange={() =>
                                                                toggleAsset(a.id)
                                                            }
                                                            aria-label={`Select ${a.name}`}
                                                        />
                                                    </td>
                                                    <td className="px-3 py-3">
                                                        <p className="font-medium text-text-primary">
                                                            {a.name}
                                                        </p>
                                                        <p className="line-clamp-1 text-xs text-text-tertiary">
                                                            {a.hook}
                                                        </p>
                                                    </td>
                                                    <td className="px-3 py-3 text-xs text-text-secondary">
                                                        {a.creator}
                                                    </td>
                                                    <td className="px-3 py-3 text-xs text-text-secondary">
                                                        {a.angle}
                                                    </td>
                                                    <td className="px-3 py-3">
                                                        <StatusChip
                                                            tone={
                                                                a.rightsStatus === "complete"
                                                                    ? "ok"
                                                                    : a.rightsStatus === "missing"
                                                                      ? "warn"
                                                                      : "info"
                                                            }
                                                        >
                                                            {a.rightsStatus}
                                                        </StatusChip>
                                                    </td>
                                                    <td className="px-3 py-3 text-right tabular">
                                                        {a.ugcScore}
                                                    </td>
                                                    <td className="px-3 py-3 text-right tabular">
                                                        {fmtNum(a.views)}
                                                    </td>
                                                    <td className="px-3 py-3 text-right tabular">
                                                        {fmtPct(a.ctr, 1)}
                                                    </td>
                                                    <td className="px-3 py-3 text-right tabular">
                                                        {a.orders}
                                                    </td>
                                                    <td className="px-3 py-3 text-right tabular">
                                                        {fmtMoney(a.gmv)}
                                                    </td>
                                                    <td
                                                        className={`px-3 py-3 text-right tabular ${gp < 0 ? "text-destructive" : ""}`}
                                                    >
                                                        {fmtMoney(gp)}
                                                    </td>
                                                    <td className="px-3 py-3 text-right tabular text-xs">
                                                        {roasLabel(a)}
                                                    </td>
                                                    <td className="px-3 py-3">
                                                        <div className="flex flex-wrap gap-1">
                                                            {diags.slice(0, 2).map((d) => (
                                                                <StatusChip
                                                                    key={d.id}
                                                                    tone={
                                                                        d.severity === "destructive"
                                                                            ? "destructive"
                                                                            : d.severity === "warn"
                                                                              ? "warn"
                                                                              : d.severity === "ok"
                                                                                ? "ok"
                                                                                : "info"
                                                                    }
                                                                    className="text-[10px]"
                                                                >
                                                                    {d.label}
                                                                </StatusChip>
                                                            ))}
                                                        </div>
                                                    </td>
                                                </tr>
                                            );
                                        })}
                                    </tbody>
                                </table>
                            </div>
                        </SurfaceCard>

                        {/* Creator perf */}
                        <SurfaceCard padding="none">
                            <div className="border-b border-hairline px-5 py-3">
                                <h3 className="text-sm font-semibold">Creators</h3>
                            </div>
                            <div className="divide-y divide-hairline">
                                {seedCreatorPerf
                                    .filter((c) => assets.some((a) => a.creatorId === c.creatorId))
                                    .map((c) => (
                                        <div
                                            key={c.creatorId}
                                            className="grid grid-cols-[minmax(0,1fr)_auto_auto_auto] items-center gap-4 px-5 py-3 text-sm"
                                        >
                                            <div className="min-w-0">
                                                <p className="truncate font-medium">{c.handle}</p>
                                                <p className="text-xs text-text-tertiary">
                                                    {c.assets} asset{c.assets > 1 ? "s" : ""} · avg
                                                    score {c.avgUgcScore}
                                                </p>
                                            </div>
                                            <div className="text-right tabular text-xs">
                                                <p className="text-text-tertiary">GMV / sample</p>
                                                <p className="font-semibold">${c.gmvPerSample}</p>
                                            </div>
                                            <div className="text-right tabular text-xs">
                                                <p className="text-text-tertiary">Gross profit</p>
                                                <p
                                                    className={`font-semibold ${c.grossProfit < 0 ? "text-destructive" : ""}`}
                                                >
                                                    {fmtMoney(c.grossProfit)}
                                                </p>
                                            </div>
                                            <StatusChip
                                                tone={
                                                    c.recommendation === "Rehire"
                                                        ? "ok"
                                                        : c.recommendation === "Do not send"
                                                          ? "destructive"
                                                          : "info"
                                                }
                                            >
                                                {c.recommendation}
                                            </StatusChip>
                                        </div>
                                    ))}
                            </div>
                        </SurfaceCard>
                    </TabsContent>

                    {/* -------- CREATIVE PATTERNS -------- */}
                    <TabsContent value="patterns" className="mt-4 space-y-4">
                        <SurfaceCard padding="none">
                            <div className="border-b border-hairline px-5 py-3">
                                <h3 className="text-sm font-semibold">Pattern → GMV map</h3>
                                <p className="text-xs text-text-tertiary">
                                    Directional signals across current assets. Not causal.
                                </p>
                            </div>
                            <div className="overflow-x-auto">
                                <table className="w-full min-w-[700px] text-sm">
                                    <thead className="bg-surface-soft/60">
                                        <tr className="text-left text-xs font-medium text-text-tertiary">
                                            <th className="px-4 py-2.5">Pattern</th>
                                            <th className="px-3 py-2.5 text-right">Assets</th>
                                            <th className="px-3 py-2.5 text-right">Median CTR</th>
                                            <th className="px-3 py-2.5 text-right">Orders</th>
                                            <th className="px-3 py-2.5 text-right">GMV</th>
                                            <th className="px-3 py-2.5">Signal</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {groupByAngle(assets).map((row) => (
                                            <tr
                                                key={row.angle}
                                                className="border-t border-hairline"
                                            >
                                                <td className="px-4 py-3 font-medium">
                                                    {row.angle}
                                                </td>
                                                <td className="px-3 py-3 text-right tabular">
                                                    {row.count}
                                                </td>
                                                <td className="px-3 py-3 text-right tabular">
                                                    {fmtPct(row.medianCtr)}
                                                </td>
                                                <td className="px-3 py-3 text-right tabular">
                                                    {row.orders}
                                                </td>
                                                <td className="px-3 py-3 text-right tabular">
                                                    {fmtMoney(row.gmv)}
                                                </td>
                                                <td className="px-3 py-3">
                                                    <StatusChip tone={row.signal.tone}>
                                                        {row.signal.label}
                                                    </StatusChip>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </SurfaceCard>

                        {patterns.map((p) => (
                            <SurfaceCard key={p.id}>
                                <div className="flex flex-wrap items-start justify-between gap-3">
                                    <div className="min-w-0 space-y-2">
                                        <StatusChip tone="ok">Winning pattern</StatusChip>
                                        <p className="text-sm italic text-text-secondary">
                                            {p.hook}
                                        </p>
                                        <dl className="space-y-1 text-xs">
                                            <Row k="Angle" v={p.angle} />
                                            <Row k="Creator type" v={p.creatorType} />
                                            <Row k="Product reveal" v={p.productReveal} />
                                            <Row k="Proof" v={p.proof} />
                                            <Row k="CTA" v={p.cta} />
                                            <Row k="Signal" v={p.signal} />
                                        </dl>
                                    </div>
                                    <div className="flex flex-col gap-2">
                                        <Button size="sm" onClick={onGenerateVariants}>
                                            <Sparkles className="h-4 w-4" /> Generate variants
                                        </Button>
                                        <Button
                                            size="sm"
                                            variant="secondary"
                                            onClick={() => {
                                                savePattern(p);
                                                toast.success("Saved to Pattern Library");
                                            }}
                                        >
                                            Save pattern
                                        </Button>
                                        <Button size="sm" variant="ghost" asChild>
                                            <Link
                                                to="/campaigns/$campaignId"
                                                params={{ campaignId }}
                                            >
                                                Open Campaign Pack{" "}
                                                <ArrowUpRight className="h-3.5 w-3.5" />
                                            </Link>
                                        </Button>
                                    </div>
                                </div>
                            </SurfaceCard>
                        ))}
                    </TabsContent>

                    {/* -------- TRENDS -------- */}
                    <TabsContent value="trends" className="mt-4 space-y-4">
                        <SurfaceCard padding="none">
                            <div className="flex items-center justify-between border-b border-hairline px-5 py-3">
                                <h3 className="text-sm font-semibold">Trend over time</h3>
                                <Select
                                    value={chartMetric}
                                    onValueChange={(v) => setChartMetric(v as typeof chartMetric)}
                                >
                                    <SelectTrigger className="h-8 w-[200px]">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="gmv">GMV &amp; gross profit</SelectItem>
                                        <SelectItem value="orders">
                                            Orders &amp; product clicks
                                        </SelectItem>
                                        <SelectItem value="ctr">CTR &amp; watch rate</SelectItem>
                                        <SelectItem value="sampleEfficiency">
                                            Sample efficiency
                                        </SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="h-72 p-4">
                                <ResponsiveContainer width="100%" height="100%">
                                    <LineChart
                                        data={trend}
                                        margin={{ top: 10, right: 12, left: 0, bottom: 0 }}
                                    >
                                        <CartesianGrid
                                            strokeDasharray="3 3"
                                            stroke="hsl(0 0% 90%)"
                                        />
                                        <XAxis
                                            dataKey="date"
                                            tickFormatter={(v) =>
                                                new Date(v).toLocaleDateString(undefined, {
                                                    month: "short",
                                                    day: "numeric",
                                                })
                                            }
                                            fontSize={11}
                                        />
                                        <YAxis fontSize={11} />
                                        <Tooltip
                                            labelFormatter={(v) => new Date(v).toLocaleDateString()}
                                        />
                                        {chartMetric === "gmv" && (
                                            <>
                                                <Line
                                                    type="monotone"
                                                    dataKey="gmv"
                                                    stroke="var(--color-chart-1)"
                                                    strokeWidth={2}
                                                    dot={false}
                                                    name="GMV"
                                                />
                                                <Line
                                                    type="monotone"
                                                    dataKey="grossProfit"
                                                    stroke="var(--color-chart-3)"
                                                    strokeWidth={2}
                                                    dot={false}
                                                    name="Gross profit"
                                                />
                                            </>
                                        )}
                                        {chartMetric === "orders" && (
                                            <>
                                                <Line
                                                    type="monotone"
                                                    dataKey="orders"
                                                    stroke="var(--color-chart-1)"
                                                    strokeWidth={2}
                                                    dot={false}
                                                    name="Orders"
                                                />
                                                <Line
                                                    type="monotone"
                                                    dataKey="productClicks"
                                                    stroke="var(--color-chart-2)"
                                                    strokeWidth={2}
                                                    dot={false}
                                                    name="Product clicks"
                                                />
                                            </>
                                        )}
                                        {chartMetric === "ctr" && (
                                            <>
                                                <Line
                                                    type="monotone"
                                                    dataKey="ctr"
                                                    stroke="var(--color-chart-1)"
                                                    strokeWidth={2}
                                                    dot={false}
                                                    name="CTR"
                                                />
                                                <Line
                                                    type="monotone"
                                                    dataKey="watchRate"
                                                    stroke="var(--color-chart-2)"
                                                    strokeWidth={2}
                                                    dot={false}
                                                    name="Watch rate"
                                                />
                                            </>
                                        )}
                                        {chartMetric === "sampleEfficiency" && (
                                            <Line
                                                type="monotone"
                                                dataKey="sampleEfficiency"
                                                stroke="var(--color-chart-3)"
                                                strokeWidth={2}
                                                dot={false}
                                                name="Sample efficiency"
                                            />
                                        )}
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        </SurfaceCard>

                        <SurfaceCard padding="none">
                            <div className="border-b border-hairline px-5 py-3">
                                <h3 className="text-sm font-semibold">
                                    Asset scatter — spend vs gross profit
                                </h3>
                                <p className="text-xs text-text-tertiary">
                                    Bubble size = orders. Table alternative below.
                                </p>
                            </div>
                            <div className="h-72 p-4">
                                <ResponsiveContainer width="100%" height="100%">
                                    <ScatterChart
                                        margin={{ top: 10, right: 20, left: 0, bottom: 10 }}
                                    >
                                        <CartesianGrid
                                            strokeDasharray="3 3"
                                            stroke="hsl(0 0% 90%)"
                                        />
                                        <XAxis
                                            dataKey="adSpend"
                                            type="number"
                                            name="Ad spend"
                                            fontSize={11}
                                            tickFormatter={(v) => `$${v}`}
                                        />
                                        <YAxis
                                            dataKey="grossProfit"
                                            type="number"
                                            name="Gross profit"
                                            fontSize={11}
                                            tickFormatter={(v) => `$${v}`}
                                        />
                                        <ZAxis dataKey="orders" range={[60, 400]} />
                                        <Tooltip
                                            cursor={{ strokeDasharray: "3 3" }}
                                            formatter={(v: number, k: string) =>
                                                k === "orders" ? [v, "Orders"] : [`$${v}`, k]
                                            }
                                        />
                                        <Scatter
                                            data={assets.map((a) => ({
                                                ...a,
                                                grossProfit: grossProfit(a),
                                            }))}
                                            fill="var(--color-chart-1)"
                                        />
                                    </ScatterChart>
                                </ResponsiveContainer>
                            </div>
                            <div className="border-t border-hairline p-4">
                                <details className="text-sm">
                                    <summary className="cursor-pointer text-xs text-text-tertiary">
                                        Table alternative
                                    </summary>
                                    <div className="mt-2 overflow-x-auto">
                                        <table className="w-full min-w-[500px] text-xs">
                                            <thead className="text-text-tertiary">
                                                <tr>
                                                    <th className="p-2 text-left">Asset</th>
                                                    <th className="p-2 text-right">Ad spend</th>
                                                    <th className="p-2 text-right">Gross profit</th>
                                                    <th className="p-2 text-right">Orders</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {assets.map((a) => (
                                                    <tr
                                                        key={a.id}
                                                        className="border-t border-hairline"
                                                    >
                                                        <td className="p-2">{a.name}</td>
                                                        <td className="p-2 text-right tabular">
                                                            {fmtMoney(a.adSpend)}
                                                        </td>
                                                        <td className="p-2 text-right tabular">
                                                            {fmtMoney(grossProfit(a))}
                                                        </td>
                                                        <td className="p-2 text-right tabular">
                                                            {a.orders}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </details>
                            </div>
                        </SurfaceCard>

                        {fatigue.length > 0 && (
                            <SurfaceCard padding="none">
                                <div className="border-b border-hairline px-5 py-3">
                                    <h3 className="text-sm font-semibold">Fatigue signals</h3>
                                </div>
                                <div className="divide-y divide-hairline">
                                    {fatigue.map((f) => (
                                        <div key={f.id} className="p-4">
                                            <div className="flex items-center gap-2">
                                                <StatusChip
                                                    tone={
                                                        f.state === "high" ? "destructive" : "warn"
                                                    }
                                                >
                                                    {f.state === "high"
                                                        ? "High risk"
                                                        : "Prepare refresh"}
                                                </StatusChip>
                                                <p className="text-sm font-medium">{f.assetName}</p>
                                            </div>
                                            <p className="mt-1.5 text-xs text-text-secondary">
                                                {f.reason}
                                            </p>
                                            <p className="mt-1 text-xs text-text-tertiary">
                                                Suggested: {f.suggestion}
                                            </p>
                                        </div>
                                    ))}
                                </div>
                            </SurfaceCard>
                        )}
                    </TabsContent>

                    {/* -------- DATA QUALITY -------- */}
                    <TabsContent value="data-quality" className="mt-4 space-y-4">
                        <SurfaceCard>
                            <div className="flex flex-wrap items-center justify-between gap-2">
                                <div>
                                    <StatusChip
                                        tone={summary.dataQuality === "complete" ? "ok" : "warn"}
                                    >
                                        {summary.dataQuality}
                                    </StatusChip>
                                    <p className="mt-2 text-sm text-text-secondary">
                                        Recommendation confidence is{" "}
                                        <span className="font-medium">Medium</span> because
                                        {seedImportIssues.missingCost.includes(campaignId)
                                            ? " two creator assets do not have complete sample-cost data"
                                            : " some assets have limited comparison data"}
                                        .
                                    </p>
                                </div>
                                <Button
                                    size="sm"
                                    variant="secondary"
                                    onClick={() => setOpenImport(true)}
                                >
                                    Re-import data
                                </Button>
                            </div>
                        </SurfaceCard>

                        <div className="grid gap-4 md:grid-cols-3">
                            <Kpi label="Mapped rows" value={String(assets.length)} tone="ok" />
                            <Kpi
                                label="Unmatched rows"
                                value={String(seedImportIssues.unmatched.length)}
                                tone="warn"
                            />
                            <Kpi
                                label="Duplicate rows"
                                value={String(seedImportIssues.duplicates.length)}
                                tone="warn"
                            />
                        </div>

                        <SurfaceCard padding="none">
                            <div className="border-b border-hairline px-5 py-3">
                                <h3 className="text-sm font-semibold">
                                    Unmatched &amp; duplicate rows
                                </h3>
                            </div>
                            <div className="divide-y divide-hairline">
                                {[
                                    ...seedImportIssues.unmatched.map((r) => ({
                                        ...r,
                                        state: "unmatched" as const,
                                    })),
                                    ...seedImportIssues.duplicates.map((r) => ({
                                        ...r,
                                        state: "duplicate" as const,
                                    })),
                                ].map((r) => (
                                    <div
                                        key={`${r.state}-${r.row}`}
                                        className="flex items-center justify-between gap-3 px-5 py-3 text-sm"
                                    >
                                        <div>
                                            <p className="font-medium">
                                                Row {r.row}: {r.asset}
                                            </p>
                                            <p className="text-xs text-text-tertiary">{r.note}</p>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <StatusChip tone="warn">{r.state}</StatusChip>
                                            <Button
                                                size="sm"
                                                variant="ghost"
                                                onClick={() => toast.success("Row ignored locally")}
                                            >
                                                Ignore
                                            </Button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </SurfaceCard>
                    </TabsContent>
                </Tabs>
            </div>

            <EvidenceDrawer
                rec={selectedRec}
                open={!!selectedRec}
                onOpenChange={(v) => !v && setSelectedRec(null)}
                onGenerateVariants={onGenerateVariants}
            />
            <ImportPerformanceDialog open={openImport} onOpenChange={setOpenImport} />

            <Dialog open={openCompare} onOpenChange={setOpenCompare}>
                <DialogContent className="max-w-4xl">
                    <DialogHeader>
                        <DialogTitle>Compare assets</DialogTitle>
                        <DialogDescription>
                            Side-by-side comparison of selected assets.
                        </DialogDescription>
                    </DialogHeader>
                    <CompareTable assets={assets.filter((a) => selectedAssets.includes(a.id))} />
                    <DialogFooter>
                        <Button variant="secondary" onClick={() => setOpenCompare(false)}>
                            Close
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </AppShell>
    );
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
    return (
        <SurfaceCard padding="none" className="min-h-[96px] p-4">
            <p className="text-xs uppercase tracking-wide text-text-tertiary">{label}</p>
            <p className="mt-1 tabular text-xl font-semibold text-text-primary">{value}</p>
            {sub && <p className="mt-0.5 text-xs text-text-tertiary">{sub}</p>}
        </SurfaceCard>
    );
}

function Kpi({
    label,
    value,
    tone,
}: {
    label: string;
    value: string;
    tone: "ok" | "warn" | "info" | "destructive" | "neutral";
}) {
    return (
        <SurfaceCard padding="none" className="p-4">
            <div className="flex items-center justify-between">
                <p className="text-xs uppercase tracking-wide text-text-tertiary">{label}</p>
                <StatusChip tone={tone}>{tone === "ok" ? "Complete" : "Attention"}</StatusChip>
            </div>
            <p className="mt-2 tabular text-lg font-semibold">{value}</p>
        </SurfaceCard>
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

function median(arr: number[]): number {
    const s = [...arr].sort((a, b) => a - b);
    const m = Math.floor(s.length / 2);
    return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

function groupByAngle(assets: PerfAsset[]) {
    const map = new Map<string, PerfAsset[]>();
    assets.forEach((a) => {
        const arr = map.get(a.angle) ?? [];
        arr.push(a);
        map.set(a.angle, arr);
    });
    return Array.from(map.entries()).map(([angle, list]) => {
        const gmv = list.reduce((n, a) => n + a.gmv, 0);
        const orders = list.reduce((n, a) => n + a.orders, 0);
        const medianCtr = median(list.map((a) => a.ctr));
        const eff =
            list.reduce((n, a) => n + a.sampleCost, 0) > 0
                ? gmv / list.reduce((n, a) => n + a.sampleCost, 0)
                : 0;
        const signal =
            eff > 30
                ? { label: "Directional winner", tone: "ok" as const }
                : eff > 10
                  ? { label: "Promising", tone: "info" as const }
                  : list.length < 2
                    ? { label: "Insufficient data", tone: "neutral" as const }
                    : { label: "Weak current signal", tone: "warn" as const };
        return { angle, count: list.length, orders, gmv, medianCtr, signal };
    });
}

function CompareTable({ assets }: { assets: PerfAsset[] }) {
    if (assets.length === 0)
        return <p className="text-sm text-text-tertiary">Select assets to compare.</p>;
    const bestAtt = bestOnAttention(assets);
    const bestConv = bestOnConversion(assets);
    const bestProf = bestOnProfit(assets);
    const bestEff = bestOnSampleEfficiency(assets);
    const bestPaid = bestPaidReady(assets);
    return (
        <div className="space-y-4">
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
                <Callout label="Best on attention" v={bestAtt?.name} />
                <Callout label="Best on conversion" v={bestConv?.name} />
                <Callout label="Best on profit" v={bestProf?.name} />
                <Callout label="Best sample efficiency" v={bestEff?.name} />
                <Callout
                    label="Best paid-ready"
                    v={bestPaid?.name ?? "None with complete rights"}
                />
            </div>
            <div className="overflow-x-auto">
                <table className="w-full min-w-[600px] text-sm">
                    <thead className="text-xs text-text-tertiary">
                        <tr>
                            <th className="p-2 text-left">Metric</th>
                            {assets.map((a) => (
                                <th key={a.id} className="p-2 text-left">
                                    {a.name}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody className="[&_tr]:border-t [&_tr]:border-hairline">
                        <tr>
                            <td className="p-2">Creator</td>
                            {assets.map((a) => (
                                <td key={a.id} className="p-2 text-xs">
                                    {a.creator}
                                </td>
                            ))}
                        </tr>
                        <tr>
                            <td className="p-2">Angle</td>
                            {assets.map((a) => (
                                <td key={a.id} className="p-2 text-xs">
                                    {a.angle}
                                </td>
                            ))}
                        </tr>
                        <tr>
                            <td className="p-2">UGC score</td>
                            {assets.map((a) => (
                                <td key={a.id} className="p-2 tabular">
                                    {a.ugcScore}
                                </td>
                            ))}
                        </tr>
                        <tr>
                            <td className="p-2">Views</td>
                            {assets.map((a) => (
                                <td key={a.id} className="p-2 tabular">
                                    {fmtNum(a.views)}
                                </td>
                            ))}
                        </tr>
                        <tr>
                            <td className="p-2">CTR</td>
                            {assets.map((a) => (
                                <td key={a.id} className="p-2 tabular">
                                    {fmtPct(a.ctr)}
                                </td>
                            ))}
                        </tr>
                        <tr>
                            <td className="p-2">Orders</td>
                            {assets.map((a) => (
                                <td key={a.id} className="p-2 tabular">
                                    {a.orders}
                                </td>
                            ))}
                        </tr>
                        <tr>
                            <td className="p-2">GMV</td>
                            {assets.map((a) => (
                                <td key={a.id} className="p-2 tabular">
                                    {fmtMoney(a.gmv)}
                                </td>
                            ))}
                        </tr>
                        <tr>
                            <td className="p-2">Gross profit</td>
                            {assets.map((a) => (
                                <td
                                    key={a.id}
                                    className={`p-2 tabular ${grossProfit(a) < 0 ? "text-destructive" : ""}`}
                                >
                                    {fmtMoney(grossProfit(a))}
                                </td>
                            ))}
                        </tr>
                        <tr>
                            <td className="p-2">Rights</td>
                            {assets.map((a) => (
                                <td key={a.id} className="p-2 text-xs">
                                    {a.rightsStatus}
                                </td>
                            ))}
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    );
}

function Callout({ label, v }: { label: string; v?: string }) {
    return (
        <div className="rounded-md border border-hairline p-2.5">
            <p className="text-[10px] uppercase tracking-wide text-text-tertiary">{label}</p>
            <p className="mt-0.5 line-clamp-2 text-xs font-medium text-text-primary">{v ?? "—"}</p>
        </div>
    );
}
