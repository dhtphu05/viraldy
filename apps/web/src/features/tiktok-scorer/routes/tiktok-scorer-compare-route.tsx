import { useQuery } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";
import {
    AlertTriangle,
    ArrowLeft,
    ArrowRight,
    CheckCircle2,
    CircleAlert,
    RefreshCw,
    ShieldAlert,
    VideoOff,
} from "lucide-react";
import { useEffect, useRef } from "react";

import { ScorerErrorState, ScorerLoadingState } from "../components/scorer-route-state";
import { useScorerWorkspace } from "../hooks/use-scorer-workspace";
import type { TikTokComparisonFinding, TikTokScoreComparison, TikTokScoreRun } from "../types";
import { queryKeys } from "@/shared/api/query-keys";
import {
    getAssetPlayback,
    getTikTokScore,
    getTikTokScoreComparison,
    trackTikTokScoreEvent,
} from "@/shared/api/tiktok-scores";
import { Alert, AlertDescription, AlertTitle } from "@/shared/ui/alert";
import { Button } from "@/shared/ui/button";
import { EmptyState } from "@/shared/ui/empty-state";
import { StatusChip } from "@/shared/ui/status-chip";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table";
import { AppShell } from "@/widgets/app-shell/app-shell";

export const Route = createFileRoute("/tiktok-scorer/$scoreId/compare/$comparisonId")({
    head: () => ({ meta: [{ title: "Revision comparison — TikTok Scorer — Viraldy" }] }),
    component: TikTokScorerCompareRoute,
});

function TikTokScorerCompareRoute() {
    const { scoreId, comparisonId } = Route.useParams();
    const { workspaceId, workspaces } = useScorerWorkspace();
    const tracked = useRef<string | null>(null);
    const comparison = useQuery({
        queryKey: queryKeys.tiktokScores.comparison(workspaceId, scoreId, comparisonId),
        queryFn: () => getTikTokScoreComparison(workspaceId!, scoreId, comparisonId),
        enabled: Boolean(workspaceId),
        retry: 1,
        refetchInterval: (query) =>
            ["completed", "failed"].includes(query.state.data?.status ?? "") ? false : 2_000,
    });
    const beforeId = comparison.data?.beforeScoreRunId ?? scoreId;
    const afterId = comparison.data?.afterScoreRunId ?? null;
    const before = useQuery({
        queryKey: queryKeys.tiktokScores.detail(workspaceId, beforeId),
        queryFn: () => getTikTokScore(workspaceId!, beforeId),
        enabled: Boolean(workspaceId && beforeId),
        retry: 1,
    });
    const after = useQuery({
        queryKey: queryKeys.tiktokScores.detail(workspaceId, afterId),
        queryFn: () => getTikTokScore(workspaceId!, afterId!),
        enabled: Boolean(workspaceId && afterId),
        retry: 1,
    });

    useEffect(() => {
        if (!workspaceId || !comparison.data || tracked.current === comparisonId) return;
        tracked.current = comparisonId;
        void trackTikTokScoreEvent({
            eventType: "tiktok_comparison_viewed",
            workspaceId,
            scoreRunId: scoreId,
            comparisonId,
            assetVersionId: comparison.data.afterAssetVersionId,
        });
    }, [comparison.data, comparisonId, scoreId, workspaceId]);

    if (workspaces.isLoading || comparison.isLoading) {
        return (
            <AppShell>
                <ScorerLoadingState label="Loading revision comparison" />
            </AppShell>
        );
    }
    if (workspaces.isError) {
        return (
            <AppShell>
                <ScorerErrorState
                    error={workspaces.error}
                    onRetry={() => void workspaces.refetch()}
                    resource="Workspace"
                />
            </AppShell>
        );
    }
    if (comparison.isError || !comparison.data) {
        return (
            <AppShell>
                <ScorerErrorState
                    error={comparison.error}
                    onRetry={() => void comparison.refetch()}
                    resource="Comparison"
                />
            </AppShell>
        );
    }
    const data = comparison.data;
    if (data.status === "failed") {
        return (
            <AppShell>
                <SurfaceCard variant="critical">
                    <EmptyState
                        icon={AlertTriangle}
                        title="Comparison failed"
                        description="Both score runs remain unchanged. Retry after both revision analyses are complete."
                        action={
                            <Button
                                type="button"
                                variant="secondary"
                                onClick={() => void comparison.refetch()}
                            >
                                <RefreshCw className="h-4 w-4" />
                                Try again
                            </Button>
                        }
                    />
                </SurfaceCard>
            </AppShell>
        );
    }
    if (data.status !== "completed") {
        return (
            <AppShell>
                <SurfaceCard padding="lg">
                    <h1 className="text-xl font-semibold text-text-primary">
                        Comparing Draft 1 and Draft 2
                    </h1>
                    <p className="mt-2 text-sm text-text-secondary">
                        Action verification and regression checks are processing on the backend.
                        This page refreshes from the real comparison state.
                    </p>
                    <StatusChip tone="info" className="mt-4" dot>
                        {humanize(data.status)}
                    </StatusChip>
                </SurfaceCard>
            </AppShell>
        );
    }

    return (
        <AppShell>
            <div className="flex flex-col gap-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <Button asChild variant="ghost" size="sm">
                        <Link
                            to="/tiktok-scorer/$scoreId"
                            params={{ scoreId }}
                            search={{ jobId: undefined }}
                        >
                            <ArrowLeft className="h-4 w-4" />
                            Back to score
                        </Link>
                    </Button>
                    {comparison.isFetching && (
                        <StatusChip tone="info">
                            <RefreshCw className="h-3 w-3 animate-spin" />
                            Syncing
                        </StatusChip>
                    )}
                </div>
                {!data.likeForLike && (
                    <Alert>
                        <AlertTriangle className="h-4 w-4" />
                        <AlertTitle>Not a like-for-like comparison</AlertTitle>
                        <AlertDescription>
                            {data.warning ??
                                "Profile, Product Context, or intended use changed between drafts. Interpret score movement cautiously."}
                        </AlertDescription>
                    </Alert>
                )}
                <ComparisonHero data={data} />
                <div className="grid gap-5 lg:grid-cols-2">
                    <DraftPreview
                        label="Draft 1"
                        run={before.data ?? null}
                        workspaceId={workspaceId!}
                        assetVersionId={data.beforeAssetVersionId}
                    />
                    <DraftPreview
                        label="Draft 2"
                        run={after.data ?? null}
                        workspaceId={workspaceId!}
                        assetVersionId={data.afterAssetVersionId}
                    />
                </div>
                <div className="grid gap-5 lg:grid-cols-3">
                    <FindingGroup
                        title="Resolved blockers"
                        items={data.resolved}
                        tone="ok"
                        empty="No blocker was marked resolved."
                    />
                    <FindingGroup
                        title="Unresolved blockers"
                        items={data.unresolved}
                        tone="warn"
                        empty="No blocker remains unresolved."
                    />
                    <FindingGroup
                        title="New regressions"
                        items={data.regressions}
                        tone="destructive"
                        empty="No new regression was detected."
                    />
                </div>
                <DimensionChanges data={data} />
                <ActionVerification data={data} />
                <EvidenceAndStrengths data={data} />
                <SurfaceCard
                    variant={data.finalNextAction === "no_required_changes" ? "plain" : "critical"}
                    padding="lg"
                >
                    <p className="text-xs font-medium uppercase text-text-tertiary">
                        Final next action
                    </p>
                    <h2 className="mt-2 text-xl font-semibold text-text-primary">
                        {nextAction(data.finalNextAction)}
                    </h2>
                    <p className="mt-2 text-sm text-text-secondary">
                        This recommendation is based on action-level verification, unresolved
                        blockers, and regressions—not only the score delta.
                    </p>
                </SurfaceCard>
            </div>
        </AppShell>
    );
}

function ComparisonHero({ data }: { data: TikTokScoreComparison }) {
    return (
        <SurfaceCard padding="lg" highlight>
            <div className="flex flex-col items-center justify-between gap-5 text-center sm:flex-row sm:text-left">
                <div>
                    <StatusChip
                        tone={
                            data.regressions.length
                                ? "warn"
                                : data.unresolved.length
                                  ? "warn"
                                  : "ok"
                        }
                    >
                        {data.regressions.length
                            ? "Regression detected"
                            : data.unresolved.length
                              ? "Actions remain"
                              : "Mandatory actions resolved"}
                    </StatusChip>
                    <h1 className="mt-3 text-2xl font-semibold text-text-primary">
                        Draft-to-draft verification
                    </h1>
                    <p className="mt-2 text-sm text-text-secondary">
                        {data.actions.filter((action) => action.status === "verified").length} of{" "}
                        {data.actions.length} tracked actions verified
                    </p>
                </div>
                <div className="flex items-center gap-4">
                    <ScoreBox label="Draft 1" value={data.beforeScore} />
                    <ArrowRight className="h-5 w-5 text-text-tertiary" />
                    <ScoreBox label="Draft 2" value={data.afterScore} />
                    <StatusChip tone={(data.scoreDelta ?? 0) >= 0 ? "ok" : "warn"}>
                        {data.scoreDelta === null
                            ? "No delta"
                            : `${data.scoreDelta >= 0 ? "+" : ""}${data.scoreDelta}`}
                    </StatusChip>
                </div>
            </div>
        </SurfaceCard>
    );
}

function DraftPreview({
    label,
    run,
    workspaceId,
    assetVersionId,
}: {
    label: string;
    run: TikTokScoreRun | null;
    workspaceId: string;
    assetVersionId: string;
}) {
    const playback = useQuery({
        queryKey: queryKeys.tiktokScores.playback(
            workspaceId,
            run?.assetId ?? null,
            assetVersionId,
        ),
        queryFn: () => getAssetPlayback(workspaceId, run!.assetId!, assetVersionId),
        enabled: Boolean(run?.assetId),
        retry: 0,
    });
    const mediaUrl = playback.data?.videoUrl ?? run?.mediaUrl ?? null;
    return (
        <SurfaceCard>
            <div className="flex items-center justify-between">
                <div>
                    <p className="text-xs font-medium uppercase text-text-tertiary">{label}</p>
                    <h2 className="mt-1 font-semibold text-text-primary">
                        {run?.assetName ?? `Asset version ${assetVersionId}`}
                    </h2>
                </div>
                <StatusChip tone="neutral">
                    {run?.profile.label ?? "Profile unavailable"}
                </StatusChip>
            </div>
            <div className="mx-auto mt-4 aspect-[9/16] max-h-[480px] overflow-hidden rounded-xl bg-black text-white">
                {mediaUrl ? (
                    <video
                        src={mediaUrl}
                        controls
                        playsInline
                        preload="metadata"
                        className="h-full w-full object-contain"
                        aria-label={`${label} video`}
                    />
                ) : (
                    <div className="flex h-full flex-col items-center justify-center px-5 text-center">
                        <VideoOff className="h-7 w-7 text-white/70" />
                        <p className="mt-2 text-sm font-medium">Playback unavailable</p>
                        <p className="mt-1 text-xs text-white/60">
                            No server playback URL was provided.
                        </p>
                    </div>
                )}
            </div>
            <p className="mt-3 break-all text-xs text-text-tertiary">
                Immutable version: {assetVersionId}
            </p>
        </SurfaceCard>
    );
}

function FindingGroup({
    title,
    items,
    tone,
    empty,
}: {
    title: string;
    items: TikTokComparisonFinding[];
    tone: "ok" | "warn" | "destructive";
    empty: string;
}) {
    const Icon = tone === "ok" ? CheckCircle2 : tone === "warn" ? CircleAlert : ShieldAlert;
    return (
        <SurfaceCard variant={tone === "destructive" && items.length ? "critical" : "plain"}>
            <h2 className="flex items-center gap-2 font-semibold text-text-primary">
                <Icon
                    className={`h-4 w-4 ${tone === "ok" ? "text-ok" : tone === "warn" ? "text-warn" : "text-destructive"}`}
                />
                {title}
            </h2>
            {items.length ? (
                <ul className="mt-3 space-y-2">
                    {items.map((item, index) => (
                        <li
                            key={`${item.code}-${index}`}
                            className="rounded-xl bg-surface-soft p-3"
                        >
                            <p className="font-medium text-text-primary">{item.title}</p>
                            <p className="mt-1 text-xs text-text-tertiary">
                                Evidence before: {item.beforeEvidenceIds.length} · after:{" "}
                                {item.afterEvidenceIds.length}
                            </p>
                        </li>
                    ))}
                </ul>
            ) : (
                <p className="mt-3 text-sm text-text-secondary">{empty}</p>
            )}
        </SurfaceCard>
    );
}

function DimensionChanges({ data }: { data: TikTokScoreComparison }) {
    return (
        <SurfaceCard padding="none" className="overflow-hidden">
            <div className="p-5">
                <h2 className="font-semibold text-text-primary">Dimension changes</h2>
                <p className="mt-1 text-sm text-text-secondary">
                    Applicability stays visible when a dimension could not be responsibly scored.
                </p>
            </div>
            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead className="px-5">Dimension</TableHead>
                        <TableHead>Draft 1</TableHead>
                        <TableHead>Draft 2</TableHead>
                        <TableHead>Change</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {data.dimensions.map((item) => (
                        <TableRow key={item.code}>
                            <TableCell className="px-5 font-medium text-text-primary">
                                {humanize(item.code)}
                            </TableCell>
                            <TableCell>
                                {item.beforeScore ??
                                    humanize(item.beforeApplicability ?? "not evaluated")}
                            </TableCell>
                            <TableCell>
                                {item.afterScore ??
                                    humanize(item.afterApplicability ?? "not evaluated")}
                            </TableCell>
                            <TableCell>
                                {item.beforeScore !== null && item.afterScore !== null
                                    ? `${item.afterScore - item.beforeScore >= 0 ? "+" : ""}${item.afterScore - item.beforeScore}`
                                    : "—"}
                            </TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </SurfaceCard>
    );
}

function ActionVerification({ data }: { data: TikTokScoreComparison }) {
    return (
        <section>
            <h2 className="text-xl font-semibold text-text-primary">Action verification</h2>
            <p className="mt-1 text-sm text-text-secondary">
                Each accepted action is checked against before-and-after evidence.
            </p>
            <div className="mt-4 space-y-3">
                {data.actions.length ? (
                    data.actions.map((action) => (
                        <SurfaceCard key={action.actionId}>
                            <div className="flex flex-wrap items-start justify-between gap-3">
                                <div>
                                    <h3 className="font-medium text-text-primary">
                                        {humanize(action.sourceFindingCode || action.actionCode)}
                                    </h3>
                                    <p className="mt-1 text-sm text-text-secondary">
                                        {action.reason}
                                    </p>
                                </div>
                                <StatusChip
                                    tone={
                                        action.status === "verified"
                                            ? "ok"
                                            : action.status === "not_verified"
                                              ? "warn"
                                              : "neutral"
                                    }
                                >
                                    {humanize(action.status)}
                                </StatusChip>
                            </div>
                            <div className="mt-4 grid gap-3 md:grid-cols-2">
                                <Observation
                                    label="Before"
                                    value={action.before}
                                    evidence={action.beforeEvidenceIds.length}
                                />
                                <Observation
                                    label="After"
                                    value={action.after}
                                    evidence={action.afterEvidenceIds.length}
                                />
                            </div>
                            <details className="mt-3 text-xs text-text-tertiary">
                                <summary className="cursor-pointer">
                                    Technical action details
                                </summary>
                                <p className="mt-1">Action ID: {action.actionId}</p>
                            </details>
                        </SurfaceCard>
                    ))
                ) : (
                    <SurfaceCard>
                        <p className="text-sm text-text-secondary">
                            No accepted action verification was returned.
                        </p>
                    </SurfaceCard>
                )}
            </div>
        </section>
    );
}

function EvidenceAndStrengths({ data }: { data: TikTokScoreComparison }) {
    return (
        <div className="grid gap-5 lg:grid-cols-2">
            <SurfaceCard>
                <h2 className="font-semibold text-text-primary">Evidence before and after</h2>
                {data.evidence.length ? (
                    <ul className="mt-3 space-y-2">
                        {data.evidence.map((item) => (
                            <li
                                key={item.subjectCode}
                                className="rounded-xl bg-surface-soft p-3 text-sm"
                            >
                                <p className="font-medium text-text-primary">
                                    {humanize(item.subjectCode)}
                                </p>
                                <p className="mt-1 text-text-secondary">
                                    Draft 1: {item.beforeEvidenceIds.length} reference(s) · Draft 2:{" "}
                                    {item.afterEvidenceIds.length} reference(s)
                                </p>
                            </li>
                        ))}
                    </ul>
                ) : (
                    <p className="mt-3 text-sm text-text-secondary">
                        No evidence comparison rows were returned.
                    </p>
                )}
            </SurfaceCard>
            <SurfaceCard>
                <h2 className="font-semibold text-text-primary">Strengths preserved</h2>
                {data.strengths.length ? (
                    <ul className="mt-3 space-y-2">
                        {data.strengths.map((strength) => (
                            <li
                                key={strength.code}
                                className="flex gap-2 text-sm text-text-secondary"
                            >
                                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-ok" />
                                {strength.title}
                            </li>
                        ))}
                    </ul>
                ) : (
                    <p className="mt-3 text-sm text-text-secondary">
                        No preserved strength was verified.
                    </p>
                )}
            </SurfaceCard>
        </div>
    );
}

function Observation({
    label,
    value,
    evidence,
}: {
    label: string;
    value: Record<string, unknown>;
    evidence: number;
}) {
    return (
        <div className="rounded-xl bg-surface-soft p-3">
            <p className="text-xs font-medium uppercase text-text-tertiary">{label}</p>
            <p className="mt-2 text-sm text-text-primary">{formatValue(value)}</p>
            <p className="mt-2 text-xs text-text-tertiary">{evidence} evidence reference(s)</p>
        </div>
    );
}
function ScoreBox({ label, value }: { label: string; value: number | null }) {
    return (
        <div className="text-center">
            <p className="text-xs text-text-tertiary">{label}</p>
            <p className="text-3xl font-semibold tabular-nums text-text-primary">{value ?? "—"}</p>
        </div>
    );
}
function nextAction(value: string) {
    return value === "request_better_media"
        ? "Request a clearer media file"
        : value === "resolve_required_actions"
          ? "Resolve the remaining required actions"
          : value === "address_new_regressions"
            ? "Fix the new regressions before continuing"
            : value === "review_unresolved_blockers"
              ? "Review unresolved blockers"
              : "No required structural changes";
}
function formatValue(value: unknown): string {
    if (value === null || value === undefined) return "Not supplied";
    if (Array.isArray(value)) return value.map(formatValue).join(", ");
    if (typeof value === "object")
        return (
            Object.entries(value as Record<string, unknown>)
                .map(([key, item]) => `${humanize(key)}: ${formatValue(item)}`)
                .join("; ") || "Not supplied"
        );
    return String(value);
}
function humanize(value: string) {
    return value
        .replace(/_v\d+$/, "")
        .replace(/_/g, " ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
