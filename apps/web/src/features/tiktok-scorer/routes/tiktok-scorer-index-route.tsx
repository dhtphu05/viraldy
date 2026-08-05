import { useQuery } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowRight, Plus, RefreshCw, Search, SlidersHorizontal, Video } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { ScorerErrorState, ScorerLoadingState } from "../components/scorer-route-state";
import { useScorerWorkspace } from "../hooks/use-scorer-workspace";
import { filterScoreRuns, type HistoryFilters } from "../lib/tiktok-score-view-model";
import type { TikTokScoreRun } from "../types";
import { listProducts } from "@/shared/api/products";
import { formatUtcDateTime } from "@/shared/lib/date-format";
import {
    getAssetPlayback,
    listTikTokScores,
    trackTikTokScoreEvent,
} from "@/shared/api/tiktok-scores";
import { queryKeys } from "@/shared/api/query-keys";
import { Button } from "@/shared/ui/button";
import { ConfidenceBadge } from "@/shared/ui/confidence-badge";
import { EmptyState } from "@/shared/ui/empty-state";
import { Input } from "@/shared/ui/input";
import { PageHeader } from "@/shared/ui/page-header";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import { StatusChip } from "@/shared/ui/status-chip";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table";
import { AppShell } from "@/widgets/app-shell/app-shell";

export const Route = createFileRoute("/tiktok-scorer/")({
    head: () => ({
        meta: [
            { title: "TikTok Scorer — Viraldy" },
            {
                name: "description",
                content: "Evidence-linked TikTok video diagnostics and an edit-or-reshoot plan.",
            },
        ],
    }),
    component: TikTokScorerIndexRoute,
});

const INITIAL_FILTERS: HistoryFilters = {
    search: "",
    status: "all",
    mode: "all",
    profile: "all",
    product: "all",
    intendedUse: "all",
    decision: "all",
    date: "all",
};

function TikTokScorerIndexRoute() {
    const { workspaceId, workspaces } = useScorerWorkspace();
    const [filters, setFilters] = useState(INITIAL_FILTERS);
    const [offset, setOffset] = useState(0);
    const [sort, setSort] = useState("updated_at_desc");
    const trackedOpenWorkspace = useRef<string | null>(null);
    const limit = 25;
    const createdFrom = historyStartDate(filters.date);
    const history = useQuery({
        queryKey: [...queryKeys.tiktokScores.list(workspaceId), filters, sort, limit, offset],
        queryFn: () =>
            listTikTokScores(workspaceId!, {
                search: filters.search,
                status: filters.status,
                score_mode: filters.mode,
                score_profile: filters.profile,
                product_id: filters.product,
                intended_use: filters.intendedUse,
                decision: filters.decision,
                created_from: createdFrom,
                limit,
                offset,
                sort,
            }),
        enabled: Boolean(workspaceId),
        retry: 1,
    });
    const productCatalog = useQuery({
        queryKey: queryKeys.products.list(workspaceId),
        queryFn: () => listProducts(workspaceId!),
        enabled: Boolean(workspaceId),
        retry: 1,
    });
    const filtered = useMemo(
        () => filterScoreRuns(history.data?.items ?? [], filters),
        [filters, history.data?.items],
    );
    const products = useMemo(() => {
        if (productCatalog.data) {
            return productCatalog.data.map((product) => ({
                value: product.id,
                label: product.name,
            }));
        }
        return (history.data?.items ?? [])
            .filter((run) => run.productId && run.productName)
            .map((run) => ({ value: run.productId!, label: run.productName! }))
            .filter(
                (product, index, items) =>
                    items.findIndex((item) => item.value === product.value) === index,
            );
    }, [history.data?.items, productCatalog.data]);
    const hasFilters = Object.entries(filters).some(([key, value]) =>
        key === "search" ? Boolean(value) : value !== "all",
    );

    useEffect(() => {
        if (!workspaceId || trackedOpenWorkspace.current === workspaceId) return;
        trackedOpenWorkspace.current = workspaceId;
        void trackTikTokScoreEvent({
            eventType: "tiktok_scorer_opened",
            workspaceId,
        });
    }, [workspaceId]);

    return (
        <AppShell>
            <div className="flex flex-col gap-6">
                <PageHeader
                    title="TikTok Scorer"
                    description="Upload a TikTok or UGC video, see what is observable or blocked, and get an exact edit-or-reshoot plan. This is structural diagnosis—not performance prediction."
                    actions={
                        <Button asChild>
                            <Link to="/tiktok-scorer/new">
                                <Plus className="h-4 w-4" />
                                Score a video
                            </Link>
                        </Button>
                    }
                />

                {workspaces.isLoading ? (
                    <ScorerLoadingState label="Loading your workspace" />
                ) : workspaces.isError ? (
                    <ScorerErrorState
                        error={workspaces.error}
                        onRetry={() => void workspaces.refetch()}
                        resource="Workspace"
                    />
                ) : !workspaceId ? (
                    <SurfaceCard>
                        <EmptyState
                            title="No workspace is available"
                            description="Create or join a workspace before starting a score."
                        />
                    </SurfaceCard>
                ) : history.isLoading ? (
                    <ScorerLoadingState label="Loading score history" />
                ) : history.isError ? (
                    <ScorerErrorState
                        error={history.error}
                        onRetry={() => void history.refetch()}
                        resource="Score history"
                    />
                ) : (
                    <>
                        <HistoryFilters
                            filters={filters}
                            products={products}
                            sort={sort}
                            stale={history.isFetching}
                            onChange={(next) => {
                                setFilters(next);
                                setOffset(0);
                            }}
                            onSort={(value) => {
                                setSort(value);
                                setOffset(0);
                            }}
                            onRefresh={() => void history.refetch()}
                        />
                        {history.data?.items.length === 0 && !hasFilters ? (
                            <SurfaceCard>
                                <EmptyState
                                    icon={Video}
                                    title="No videos scored yet"
                                    description="Quick Score works without a product. Product-Aware Score adds verified Product Context when you need commerce-specific checks."
                                    action={
                                        <Button asChild>
                                            <Link to="/tiktok-scorer/new">
                                                Score your first video
                                            </Link>
                                        </Button>
                                    }
                                />
                            </SurfaceCard>
                        ) : filtered.length === 0 ? (
                            <SurfaceCard>
                                <EmptyState
                                    icon={SlidersHorizontal}
                                    title="No analyses match these filters"
                                    description="Clear the filters to return to every real score run in this page."
                                    action={
                                        <Button
                                            type="button"
                                            variant="secondary"
                                            onClick={() => setFilters(INITIAL_FILTERS)}
                                        >
                                            Clear filters
                                        </Button>
                                    }
                                />
                            </SurfaceCard>
                        ) : (
                            <HistoryTable runs={filtered} />
                        )}
                        <HistoryPagination
                            offset={offset}
                            limit={limit}
                            total={history.data?.total ?? 0}
                            disabled={history.isFetching}
                            onOffset={setOffset}
                        />
                    </>
                )}
            </div>
        </AppShell>
    );
}

function HistoryFilters({
    filters,
    products,
    sort,
    stale,
    onChange,
    onSort,
    onRefresh,
}: {
    filters: HistoryFilters;
    products: Array<{ value: string; label: string }>;
    sort: string;
    stale: boolean;
    onChange: (filters: HistoryFilters) => void;
    onSort: (value: string) => void;
    onRefresh: () => void;
}) {
    const update = (key: keyof HistoryFilters, value: string) =>
        onChange({ ...filters, [key]: value });
    return (
        <SurfaceCard padding="sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="relative min-w-[220px] flex-1">
                    <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-text-tertiary" />
                    <Input
                        aria-label="Search score history"
                        value={filters.search}
                        onChange={(event) => update("search", event.target.value)}
                        placeholder="Search video or product"
                        className="pl-9"
                    />
                </div>
                <Button type="button" variant="secondary" onClick={onRefresh} disabled={stale}>
                    <RefreshCw className={stale ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
                    {stale ? "Syncing" : "Refresh"}
                </Button>
            </div>
            <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
                <FilterSelect
                    label="Status"
                    value={filters.status}
                    onChange={(value) => update("status", value)}
                    options={[
                        ["all", "All statuses"],
                        ["queued", "Queued"],
                        ["scoring", "Processing"],
                        ["completed", "Completed"],
                        ["partial_evidence", "Partial evidence"],
                        ["failed", "Failed"],
                    ]}
                />
                <FilterSelect
                    label="Mode"
                    value={filters.mode}
                    onChange={(value) => update("mode", value)}
                    options={[
                        ["all", "All modes"],
                        ["quick", "Quick"],
                        ["product_aware", "Product-Aware"],
                        ["usage_aware", "Usage-Aware"],
                    ]}
                />
                <FilterSelect
                    label="Profile"
                    value={filters.profile}
                    onChange={(value) => update("profile", value)}
                    options={[
                        ["all", "All profiles"],
                        ["general_tiktok_v1", "General"],
                        ["product_led_demo_v1", "Product-led demo"],
                        ["creator_review_v1", "Creator review"],
                        ["story_led_pov_v1", "Story-led POV"],
                        ["tutorial_howto_v1", "Tutorial"],
                        ["unboxing_reaction_v1", "Unboxing"],
                        ["comment_reply_faq_v1", "Comment reply"],
                        ["offer_led_shop_v1", "Offer-led"],
                    ]}
                />
                <FilterSelect
                    label="Product"
                    value={filters.product}
                    onChange={(value) => update("product", value)}
                    options={[
                        ["all", "All products"],
                        ...products.map(
                            (product) => [product.value, product.label] as [string, string],
                        ),
                    ]}
                />
                <FilterSelect
                    label="Intended use"
                    value={filters.intendedUse}
                    onChange={(value) => update("intendedUse", value)}
                    options={[
                        ["all", "All uses"],
                        ["tiktok_organic", "TikTok organic"],
                        ["tiktok_shop_affiliate", "Shop affiliate"],
                        ["ugc_paid_candidate", "UGC paid candidate"],
                        ["spark_candidate", "Spark candidate"],
                    ]}
                />
                <FilterSelect
                    label="Decision"
                    value={filters.decision}
                    onChange={(value) => update("decision", value)}
                    options={[
                        ["all", "All decisions"],
                        ["request_better_media", "Better media"],
                        ["blocked", "Blocked"],
                        ["revise", "Revise"],
                        ["usable_with_improvements", "Usable"],
                        ["structurally_ready", "Structurally ready"],
                    ]}
                />
                <FilterSelect
                    label="Date"
                    value={filters.date}
                    onChange={(value) => update("date", value)}
                    options={[
                        ["all", "Any date"],
                        ["7d", "Last 7 days"],
                        ["30d", "Last 30 days"],
                        ["90d", "Last 90 days"],
                    ]}
                />
                <FilterSelect
                    label="Sort"
                    value={sort}
                    onChange={onSort}
                    options={[
                        ["updated_at_desc", "Recently updated"],
                        ["created_at_desc", "Newest created"],
                        ["created_at_asc", "Oldest created"],
                        ["score_desc", "Highest score"],
                        ["score_asc", "Lowest score"],
                    ]}
                />
            </div>
        </SurfaceCard>
    );
}

function FilterSelect({
    label,
    value,
    onChange,
    options,
}: {
    label: string;
    value: string;
    onChange: (value: string) => void;
    options: Array<[string, string]>;
}) {
    return (
        <Select value={value} onValueChange={onChange}>
            <SelectTrigger aria-label={label}>
                <SelectValue />
            </SelectTrigger>
            <SelectContent>
                {options.map(([option, text]) => (
                    <SelectItem key={option} value={option}>
                        {text}
                    </SelectItem>
                ))}
            </SelectContent>
        </Select>
    );
}

function HistoryTable({ runs }: { runs: TikTokScoreRun[] }) {
    return (
        <SurfaceCard padding="none" className="overflow-hidden">
            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead className="min-w-48 px-4">Video</TableHead>
                        <TableHead>Product</TableHead>
                        <TableHead>Mode / profile</TableHead>
                        <TableHead>Decision</TableHead>
                        <TableHead>Confidence</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Revisions</TableHead>
                        <TableHead>Updated</TableHead>
                        <TableHead>
                            <span className="sr-only">Open</span>
                        </TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {runs.map((run) => (
                        <HistoryRow key={run.id} run={run} />
                    ))}
                </TableBody>
            </Table>
        </SurfaceCard>
    );
}

function HistoryRow({ run }: { run: TikTokScoreRun }) {
    const comparisonId = run.comparisonIds.at(-1);
    const comparisonBaseScoreId = run.parentScoreRunId ?? run.id;
    const videoLabel = run.productName ? `${run.productName} video` : "TikTok video";
    const playback = useQuery({
        queryKey: queryKeys.tiktokScores.playback(
            run.workspaceId ?? undefined,
            run.assetId,
            run.assetVersionId,
        ),
        queryFn: () => getAssetPlayback(run.workspaceId!, run.assetId!, run.assetVersionId),
        enabled: Boolean(run.workspaceId && run.assetId && run.assetVersionId),
        retry: 0,
        staleTime: 5 * 60 * 1_000,
    });
    const mediaUrl = playback.data?.videoUrl ?? run.mediaUrl;
    return (
        <TableRow>
            <TableCell className="px-4">
                <div className="flex items-center gap-3">
                    <VideoThumbnail run={run} mediaUrl={mediaUrl} />
                    <div className="min-w-0">
                        <Link
                            to="/tiktok-scorer/$scoreId"
                            params={{ scoreId: run.id }}
                            search={{ jobId: undefined }}
                            className="font-medium text-text-primary hover:text-primary"
                        >
                            {videoLabel}
                        </Link>
                        <p className="mt-0.5 truncate text-xs text-text-tertiary">
                            {run.assetName}
                        </p>
                        <p className="mt-1 text-xs text-text-secondary">
                            {run.score === null
                                ? stageLabel(run.currentStage || run.status)
                                : `${Math.round(run.score)}/100 structural score`}
                        </p>
                    </div>
                </div>
            </TableCell>
            <TableCell>
                {run.productName ?? <span className="text-text-tertiary">No product</span>}
            </TableCell>
            <TableCell>
                <p className="text-text-primary">{humanize(run.scoreMode)}</p>
                <p className="text-xs text-text-tertiary">{run.profile.label}</p>
            </TableCell>
            <TableCell>
                <StatusChip tone={decisionTone(run.decision)}>{humanize(run.decision)}</StatusChip>
            </TableCell>
            <TableCell>
                <ConfidenceBadge level={run.confidence} />
            </TableCell>
            <TableCell>
                <StatusChip dot tone={statusTone(run.status)}>
                    {humanize(run.status)}
                </StatusChip>
            </TableCell>
            <TableCell>
                {run.revisionCount}
                {comparisonId && (
                    <Link
                        to="/tiktok-scorer/$scoreId/compare/$comparisonId"
                        params={{ scoreId: comparisonBaseScoreId, comparisonId }}
                        search={{ jobId: undefined }}
                        className="ml-2 text-xs text-primary hover:underline"
                    >
                        Compare
                    </Link>
                )}
            </TableCell>
            <TableCell className="whitespace-nowrap text-xs text-text-secondary">
                {run.updatedAt ? formatUtcDateTime(run.updatedAt) : "—"}
            </TableCell>
            <TableCell>
                <Button asChild size="icon" variant="ghost">
                    <Link
                        to="/tiktok-scorer/$scoreId"
                        params={{ scoreId: run.id }}
                        search={{ jobId: undefined }}
                        aria-label={`Open ${run.assetName}`}
                    >
                        <ArrowRight className="h-4 w-4" />
                    </Link>
                </Button>
            </TableCell>
        </TableRow>
    );
}

function VideoThumbnail({ run, mediaUrl }: { run: TikTokScoreRun; mediaUrl: string | null }) {
    return (
        <div className="relative h-16 w-10 shrink-0 overflow-hidden rounded-xl border border-divider bg-surface-soft shadow-soft-card">
            {mediaUrl ? (
                <video
                    src={mediaUrl}
                    aria-label={`Preview of ${run.assetName}`}
                    className="h-full w-full object-cover"
                    muted
                    playsInline
                    preload="metadata"
                />
            ) : (
                <div className="grid h-full w-full place-items-center bg-gradient-to-b from-primary-softer to-surface-soft text-primary">
                    <Video className="h-4 w-4" />
                </div>
            )}
            <span className="absolute bottom-1 left-1 rounded bg-black/65 px-1 text-[9px] font-medium uppercase text-white">
                9:16
            </span>
        </div>
    );
}

function HistoryPagination({
    offset,
    limit,
    total,
    disabled,
    onOffset,
}: {
    offset: number;
    limit: number;
    total: number;
    disabled: boolean;
    onOffset: (value: number) => void;
}) {
    if (total <= limit && offset === 0) return null;
    return (
        <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-text-secondary">
            <p>
                Showing {Math.min(offset + 1, total)}–{Math.min(offset + limit, total)} of {total}
            </p>
            <div className="flex gap-2">
                <Button
                    type="button"
                    variant="secondary"
                    disabled={disabled || offset === 0}
                    onClick={() => onOffset(Math.max(0, offset - limit))}
                >
                    Previous
                </Button>
                <Button
                    type="button"
                    variant="secondary"
                    disabled={disabled || offset + limit >= total}
                    onClick={() => onOffset(offset + limit)}
                >
                    Next
                </Button>
            </div>
        </div>
    );
}

function historyStartDate(value: string): string | undefined {
    const days = value === "7d" ? 7 : value === "30d" ? 30 : value === "90d" ? 90 : null;
    if (days === null) return undefined;
    return new Date(Date.now() - days * 24 * 60 * 60 * 1_000).toISOString();
}

function humanize(value: string) {
    return value
        .replace(/_v\d+$/, "")
        .replace(/_/g, " ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function stageLabel(value: string) {
    return value === "retrying"
        ? "Retrying analysis"
        : value === "processing"
          ? "Analyzing video"
          : humanize(value);
}
function statusTone(status: string) {
    return status === "failed" || status === "cancelled"
        ? ("destructive" as const)
        : status === "partial_evidence"
          ? ("warn" as const)
          : status === "completed"
            ? ("ok" as const)
            : ("info" as const);
}
function decisionTone(decision: string) {
    return decision === "blocked"
        ? ("destructive" as const)
        : decision === "revise" || decision === "request_better_media"
          ? ("warn" as const)
          : decision === "structurally_ready"
            ? ("ok" as const)
            : ("info" as const);
}
