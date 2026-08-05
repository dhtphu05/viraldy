import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";
import {
    AlertTriangle,
    ArrowLeft,
    CheckCircle2,
    Clipboard,
    Loader2,
    MessageSquareText,
    RefreshCw,
    Send,
    ShieldCheck,
    Sparkles,
    Video,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { FixPlan } from "../components/fix-plan";
import { RevisionPanel } from "../components/revision-panel";
import { ScorerErrorState, ScorerLoadingState } from "../components/scorer-route-state";
import {
    VideoEvidenceWorkspace,
    type EvidenceSeekTarget,
} from "../components/video-evidence-workspace";
import { useScorerWorkspace } from "../hooks/use-scorer-workspace";
import {
    buildHandoffMessage,
    buildProcessingSteps,
    isTerminalScoreStatus,
} from "../lib/tiktok-score-view-model";
import type {
    FixEventType,
    TikTokDimension,
    TikTokFinding,
    TikTokFixAction,
    TikTokScoreRun,
} from "../types";
import { getJob } from "@/shared/api/jobs";
import { queryKeys } from "@/shared/api/query-keys";
import {
    getAssetPlayback,
    getTikTokScore,
    listTikTokScoreFixes,
    recordTikTokFixAction,
    trackTikTokScoreEvent,
} from "@/shared/api/tiktok-scores";
import { Alert, AlertDescription, AlertTitle } from "@/shared/ui/alert";
import { Button } from "@/shared/ui/button";
import { ConfidenceBadge } from "@/shared/ui/confidence-badge";
import { EmptyState } from "@/shared/ui/empty-state";
import { ProcessingStepper } from "@/shared/ui/processing-stepper";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import { StatusChip } from "@/shared/ui/status-chip";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { AppShell } from "@/widgets/app-shell/app-shell";

export const Route = createFileRoute("/tiktok-scorer/$scoreId")({
    validateSearch: (search: Record<string, unknown>) => ({
        jobId: typeof search.jobId === "string" ? search.jobId : undefined,
    }),
    head: () => ({ meta: [{ title: "Score result — TikTok Scorer — Viraldy" }] }),
    component: TikTokScoreResultRoute,
});

function TikTokScoreResultRoute() {
    const { scoreId } = Route.useParams();
    const { jobId: searchJobId } = Route.useSearch();
    const { workspaceId, workspaces } = useScorerWorkspace();
    const queryClient = useQueryClient();
    const score = useQuery({
        queryKey: queryKeys.tiktokScores.detail(workspaceId, scoreId),
        queryFn: () => getTikTokScore(workspaceId!, scoreId),
        enabled: Boolean(workspaceId),
        retry: 1,
        refetchInterval: (query) =>
            query.state.data && isTerminalScoreStatus(query.state.data.status) ? false : 2_000,
    });
    const run = score.data;
    const jobId = searchJobId ?? run?.jobId ?? null;
    const job = useQuery({
        queryKey: queryKeys.jobs.detail(workspaceId, jobId),
        queryFn: () => getJob(workspaceId!, jobId!),
        enabled: Boolean(workspaceId && jobId && !run?.completedAt),
        retry: 1,
        refetchInterval: (query) =>
            ["succeeded", "completed", "failed", "cancelled"].includes(
                query.state.data?.status ?? "",
            )
                ? false
                : 2_000,
    });
    const terminal = run ? isTerminalScoreStatus(run.status) : false;
    const fixes = useQuery({
        queryKey: queryKeys.tiktokScores.fixes(workspaceId, scoreId),
        queryFn: () => listTikTokScoreFixes(workspaceId!, scoreId),
        enabled: Boolean(workspaceId && terminal && run?.status !== "failed"),
        retry: 1,
    });
    const playback = useQuery({
        queryKey: queryKeys.tiktokScores.playback(
            workspaceId,
            run?.assetId ?? null,
            run?.assetVersionId ?? null,
        ),
        queryFn: () => getAssetPlayback(workspaceId!, run!.assetId!, run!.assetVersionId),
        enabled: Boolean(workspaceId && run?.assetId && run.assetVersionId),
        retry: 0,
    });
    const [seekTarget, setSeekTarget] = useState<EvidenceSeekTarget | null>(null);
    const [busyFixId, setBusyFixId] = useState<string | null>(null);
    const trackedOpen = useRef<string | null>(null);
    const effectiveFixes = fixes.data ?? run?.fixes ?? [];

    useEffect(() => {
        if (!workspaceId || !run || trackedOpen.current === run.id) return;
        trackedOpen.current = run.id;
        void trackTikTokScoreEvent({
            eventType: "tiktok_scorer_opened",
            workspaceId,
            scoreRunId: run.id,
            assetVersionId: run.assetVersionId,
            mode: run.scoreMode,
            profile: run.profile.code,
            intendedUse: run.intendedUse,
        });
    }, [run, workspaceId]);

    const comparisonBaseScoreId = run?.parentScoreRunId ?? run?.id ?? scoreId;

    const fixEvent = useMutation({
        mutationFn: ({ fix, event }: { fix: TikTokFixAction; event: FixEventType }) => {
            setBusyFixId(fix.id);
            return recordTikTokFixAction(workspaceId!, scoreId, fix.id, event, crypto.randomUUID());
        },
        onSuccess: () => {
            void queryClient.invalidateQueries({
                queryKey: queryKeys.tiktokScores.fixes(workspaceId, scoreId),
            });
            void queryClient.invalidateQueries({
                queryKey: queryKeys.tiktokScores.detail(workspaceId, scoreId),
            });
            toast.success("Fix action saved");
        },
        onError: (error) =>
            toast.error(error instanceof Error ? error.message : "Fix action could not be saved"),
        onSettled: () => setBusyFixId(null),
    });

    if (workspaces.isLoading || (workspaceId && score.isLoading)) {
        return (
            <AppShell>
                <ScorerLoadingState label="Loading TikTok score" />
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
    if (score.isError || !run) {
        return (
            <AppShell>
                <ScorerErrorState error={score.error} onRetry={() => void score.refetch()} />
            </AppShell>
        );
    }

    const jobFailed = job.data?.status === "failed";
    if (run.status === "failed" || jobFailed) {
        return (
            <AppShell>
                <FailedRun
                    run={run}
                    message={run.failureMessage ?? job.data?.error_message ?? null}
                    mediaUrl={playback.data?.videoUrl ?? run.mediaUrl}
                    onRetry={() => void score.refetch()}
                />
            </AppShell>
        );
    }
    if (run.status === "cancelled" || job.data?.status === "cancelled") {
        return (
            <AppShell>
                <div className="mx-auto max-w-3xl">
                    <EmptyState
                        icon={AlertTriangle}
                        title="Analysis was cancelled"
                        description="The uploaded asset version is unchanged. Start a new score when you are ready."
                        action={
                            <Button asChild>
                                <Link to="/tiktok-scorer/new">Score another video</Link>
                            </Button>
                        }
                    />
                </div>
            </AppShell>
        );
    }
    if (!terminal) {
        const stage = job.data?.stage ?? run.currentStage ?? run.status;
        return (
            <AppShell>
                <ProcessingRun
                    run={run}
                    stage={stage}
                    syncing={score.isFetching || job.isFetching}
                    mediaUrl={playback.data?.videoUrl ?? run.mediaUrl}
                    onRefresh={() => {
                        void score.refetch();
                        if (jobId) void job.refetch();
                    }}
                />
            </AppShell>
        );
    }

    return (
        <AppShell>
            <div className="flex flex-col gap-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <Button asChild variant="ghost" size="sm">
                        <Link to="/tiktok-scorer">
                            <ArrowLeft className="h-4 w-4" />
                            Score history
                        </Link>
                    </Button>
                    {score.isFetching && (
                        <StatusChip tone="info">
                            <RefreshCw className="h-3 w-3 animate-spin" />
                            Syncing latest result
                        </StatusChip>
                    )}
                </div>
                {run.partialEvidence && (
                    <Alert>
                        <AlertTriangle className="h-4 w-4" />
                        <AlertTitle>Partial evidence</AlertTitle>
                        <AlertDescription>
                            This is not a creative failure. Review the uncertainty and better-media
                            actions before relying on unavailable checks.
                        </AlertDescription>
                    </Alert>
                )}
                <ScoreVideoPreview run={run} mediaUrl={playback.data?.videoUrl ?? run.mediaUrl} />
                <DecisionSummary run={run} />
                <StrengthsAndBlockers
                    run={run}
                    onFinding={(finding) => seekFinding(run, finding, setSeekTarget, workspaceId!)}
                />
                <Dimensions
                    dimensions={run.dimensions}
                    onOpen={(dimension) => seekDimension(run, dimension, setSeekTarget)}
                />
                <FixPlan
                    actions={effectiveFixes}
                    busyFixId={busyFixId}
                    onSeek={(fix) => {
                        if (fix.targetTimeRangeMs)
                            setSeekTarget({
                                key: `fix-${fix.id}-${Date.now()}`,
                                timestampMs: fix.targetTimeRangeMs[0],
                                range: fix.targetTimeRangeMs,
                                evidenceId: fix.evidenceIds[0],
                            });
                        fixEvent.mutate({ fix, event: "viewed" });
                    }}
                    onEvent={(fix, event) => fixEvent.mutate({ fix, event })}
                />
                <VideoEvidenceWorkspace
                    run={run}
                    mediaUrl={playback.data?.videoUrl ?? run.mediaUrl}
                    seekTarget={seekTarget}
                    onEvidenceOpen={(evidence) => {
                        if (!workspaceId) return;
                        void trackTikTokScoreEvent({
                            eventType: "tiktok_evidence_opened",
                            workspaceId,
                            scoreRunId: run.id,
                            assetVersionId: run.assetVersionId,
                            evidenceId: evidence.id,
                            mode: run.scoreMode,
                            profile: run.profile.code,
                            intendedUse: run.intendedUse,
                        });
                    }}
                />
                {run.optionalUpgrades.length > 0 && <CreativeUpgrades run={run} />}
                <HandoffPanel workspaceId={workspaceId!} scoreId={scoreId} fixes={effectiveFixes} />
                <RevisionPanel run={run} workspaceId={workspaceId!} fixes={effectiveFixes} />
                {run.comparisonIds.length > 0 && (
                    <SurfaceCard>
                        <h2 className="font-semibold text-text-primary">Revision comparisons</h2>
                        <div className="mt-3 flex flex-wrap gap-2">
                            {run.comparisonIds.map((comparisonId, index) => (
                                <Button key={comparisonId} asChild variant="secondary">
                                    <Link
                                        to="/tiktok-scorer/$scoreId/compare/$comparisonId"
                                        params={{
                                            scoreId: comparisonBaseScoreId,
                                            comparisonId,
                                        }}
                                        search={{ jobId: undefined }}
                                    >
                                        Compare revision {index + 1}
                                    </Link>
                                </Button>
                            ))}
                        </div>
                    </SurfaceCard>
                )}
            </div>
        </AppShell>
    );
}

function ProcessingRun({
    run,
    stage,
    syncing,
    mediaUrl,
    onRefresh,
}: {
    run: TikTokScoreRun;
    stage: string;
    syncing: boolean;
    mediaUrl: string | null;
    onRefresh: () => void;
}) {
    return (
        <div className="mx-auto flex max-w-5xl flex-col gap-5">
            <div>
                <Button asChild variant="ghost" size="sm">
                    <Link to="/tiktok-scorer">
                        <ArrowLeft className="h-4 w-4" />
                        Score history
                    </Link>
                </Button>
            </div>
            <SurfaceCard padding="lg">
                <div className="grid gap-6 lg:grid-cols-[220px_minmax(0,1fr)]">
                    <ScoreVideoPreview run={run} mediaUrl={mediaUrl} compact />
                    <div>
                        <div className="flex items-start gap-3">
                            <span className="grid h-10 w-10 place-items-center rounded-full bg-primary-soft text-primary">
                                <Loader2 className="h-5 w-5 animate-spin" />
                            </span>
                            <div>
                                <h1 className="text-xl font-semibold text-text-primary">
                                    Analyzing this TikTok
                                </h1>
                                <p className="mt-1 text-sm text-text-secondary">
                                    The scorer is reading the actual video evidence. If a stage
                                    retries, keep this page open or check again in a moment.
                                </p>
                                <p className="mt-2 text-xs text-text-tertiary">{run.assetName}</p>
                            </div>
                        </div>
                        <div className="mt-6">
                            <ProcessingStepper steps={buildProcessingSteps(stage)} />
                        </div>
                        <div className="mt-5 flex justify-end">
                            <Button
                                type="button"
                                variant="secondary"
                                onClick={onRefresh}
                                disabled={syncing}
                            >
                                <RefreshCw
                                    className={syncing ? "h-4 w-4 animate-spin" : "h-4 w-4"}
                                />
                                Check now
                            </Button>
                        </div>
                    </div>
                </div>
            </SurfaceCard>
        </div>
    );
}

function FailedRun({
    run,
    message,
    mediaUrl,
    onRetry,
}: {
    run: TikTokScoreRun;
    message: string | null;
    mediaUrl: string | null;
    onRetry: () => void;
}) {
    return (
        <div className="mx-auto max-w-5xl">
            <SurfaceCard variant="critical" padding="lg">
                <div className="grid gap-6 lg:grid-cols-[220px_minmax(0,1fr)]">
                    <ScoreVideoPreview run={run} mediaUrl={mediaUrl} compact />
                    <div>
                        <EmptyState
                            icon={AlertTriangle}
                            title="This analysis needs a retry"
                            description={
                                message ??
                                "The scorer could not complete this run. The immutable video version remains available."
                            }
                            action={
                                <>
                                    <Button type="button" variant="secondary" onClick={onRetry}>
                                        <RefreshCw className="h-4 w-4" />
                                        Retry status
                                    </Button>
                                    <Button asChild>
                                        <Link to="/tiktok-scorer/new">Start a new score</Link>
                                    </Button>
                                </>
                            }
                        />
                        <p className="text-center text-xs text-text-tertiary">
                            Failure code: {run.failureCode ?? "Not supplied"}
                        </p>
                    </div>
                </div>
            </SurfaceCard>
        </div>
    );
}

function ScoreVideoPreview({
    run,
    mediaUrl,
    compact = false,
}: {
    run: TikTokScoreRun;
    mediaUrl: string | null;
    compact?: boolean;
}) {
    const title = run.productName ? `${run.productName} video` : "TikTok video";
    return (
        <SurfaceCard padding={compact ? "sm" : "lg"}>
            <div
                className={
                    compact ? "mx-auto max-w-[180px]" : "grid gap-5 md:grid-cols-[220px_1fr]"
                }
            >
                <div className="relative aspect-[9/16] overflow-hidden rounded-2xl border border-divider bg-surface-soft shadow-soft-card">
                    {mediaUrl ? (
                        <video
                            src={mediaUrl}
                            aria-label={`Preview of ${run.assetName}`}
                            className="h-full w-full object-cover"
                            controls={!compact}
                            muted={compact}
                            playsInline
                            preload="metadata"
                        />
                    ) : (
                        <div className="grid h-full w-full place-items-center bg-gradient-to-b from-primary-softer to-surface-soft text-primary">
                            <Video className={compact ? "h-8 w-8" : "h-10 w-10"} />
                        </div>
                    )}
                    <span className="absolute bottom-2 left-2 rounded-full bg-black/70 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-white">
                        TikTok 9:16
                    </span>
                </div>
                {!compact && (
                    <div className="flex flex-col justify-center">
                        <p className="text-xs font-semibold uppercase tracking-wide text-text-tertiary">
                            Video under review
                        </p>
                        <h1 className="mt-2 text-2xl font-semibold text-text-primary">{title}</h1>
                        <p className="mt-2 text-sm text-text-secondary">
                            Recommendations are grounded in this uploaded video and verified product
                            context. Filename stays as metadata, not the main object.
                        </p>
                        <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                            <SummaryItem label="File" value={run.assetName} />
                            <SummaryItem
                                label="Product"
                                value={run.productName ?? "No product selected"}
                            />
                            <SummaryItem label="Mode" value={humanize(run.scoreMode)} />
                            <SummaryItem label="Status" value={humanize(run.status)} />
                        </dl>
                    </div>
                )}
            </div>
        </SurfaceCard>
    );
}

function DecisionSummary({ run }: { run: TikTokScoreRun }) {
    return (
        <SurfaceCard
            variant={run.decision === "blocked" ? "critical" : "raised"}
            padding="lg"
            highlight
        >
            <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_auto]">
                <div>
                    <div className="flex flex-wrap gap-2">
                        <StatusChip tone={decisionTone(run.decision)}>
                            {humanize(run.decision)}
                        </StatusChip>
                        <ConfidenceBadge
                            level={run.confidence}
                            rationale="Confidence reflects media and evidence coverage; it is not multiplied into the score."
                        />
                    </div>
                    <h1 className="mt-3 text-2xl font-semibold text-text-primary">
                        {decisionTitle(run.decision)}
                    </h1>
                    <p className="mt-2 max-w-3xl text-sm text-text-secondary">
                        Structural diagnosis for {run.profile.label}. It does not predict
                        distribution or commercial performance.
                    </p>
                </div>
                <div className="min-w-40 rounded-2xl bg-surface-soft p-5 text-center">
                    <p className="text-xs font-medium uppercase text-text-tertiary">
                        Structural score
                    </p>
                    <p className="mt-1 text-4xl font-semibold tabular-nums text-text-primary">
                        {run.score === null ? "—" : Math.round(run.score)}
                    </p>
                    <p className="text-xs text-text-tertiary">out of 100</p>
                </div>
            </div>
            <dl className="mt-5 grid gap-3 border-t border-divider pt-5 sm:grid-cols-2 lg:grid-cols-5">
                <SummaryItem label="Mode" value={humanize(run.scoreMode)} />
                <SummaryItem label="Intended use" value={humanize(run.intendedUse)} />
                <SummaryItem
                    label="Profile"
                    value={run.profile.label}
                    hint={run.profile.reason ?? undefined}
                />
                <SummaryItem label="Paid-use rights" value={humanize(run.paidUseRightsStatus)} />
                <SummaryItem
                    label="Final paid readiness"
                    value={humanize(run.finalPaidReadiness)}
                />
            </dl>
        </SurfaceCard>
    );
}

function StrengthsAndBlockers({
    run,
    onFinding,
}: {
    run: TikTokScoreRun;
    onFinding: (finding: TikTokFinding) => void;
}) {
    const blockers = run.findings.filter(
        (finding) => finding.severity === "hard" || finding.priority === "P0",
    );
    return (
        <div className="grid gap-5 lg:grid-cols-2">
            <SurfaceCard>
                <h2 className="font-semibold text-text-primary">Strengths to preserve</h2>
                {run.strengths.length ? (
                    <ul className="mt-3 space-y-2">
                        {run.strengths.map((strength) => (
                            <li
                                key={strength.code}
                                className="flex gap-2 text-sm text-text-secondary"
                            >
                                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-ok" />
                                <span>{strength.title}</span>
                            </li>
                        ))}
                    </ul>
                ) : (
                    <p className="mt-3 text-sm text-text-secondary">
                        No evidence-linked strength was returned.
                    </p>
                )}
            </SurfaceCard>
            <SurfaceCard variant={blockers.length ? "critical" : "plain"}>
                <h2 className="font-semibold text-text-primary">Hard blockers</h2>
                {blockers.length ? (
                    <div className="mt-3 space-y-2">
                        {blockers.map((finding) => (
                            <button
                                key={finding.id}
                                type="button"
                                onClick={() => onFinding(finding)}
                                className="w-full rounded-xl bg-destructive-soft p-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            >
                                <p className="font-medium text-text-primary">{finding.title}</p>
                                <p className="mt-1 text-sm text-text-secondary">{finding.reason}</p>
                            </button>
                        ))}
                    </div>
                ) : (
                    <p className="mt-3 flex items-center gap-2 text-sm text-text-secondary">
                        <ShieldCheck className="h-4 w-4 text-ok" />
                        No verified hard blocker was returned.
                    </p>
                )}
            </SurfaceCard>
        </div>
    );
}

function Dimensions({
    dimensions,
    onOpen,
}: {
    dimensions: TikTokDimension[];
    onOpen: (dimension: TikTokDimension) => void;
}) {
    return (
        <section>
            <h2 className="text-xl font-semibold text-text-primary">Dimension breakdown</h2>
            <p className="mt-1 text-sm text-text-secondary">
                Not evaluated and insufficient evidence remain separate from a score of zero.
            </p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {dimensions.map((dimension) => (
                    <button
                        key={dimension.code}
                        type="button"
                        onClick={() => onOpen(dimension)}
                        className="rounded-2xl border border-control-border bg-surface p-4 text-left shadow-soft-card transition-colors hover:bg-surface-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                        <div className="flex items-start justify-between gap-3">
                            <h3 className="font-medium text-text-primary">{dimension.label}</h3>
                            <span className="text-xl font-semibold tabular-nums text-text-primary">
                                {dimension.score ?? "—"}
                            </span>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-2">
                            <StatusChip
                                tone={dimension.applicability === "applicable" ? "info" : "neutral"}
                            >
                                {humanize(dimension.applicability)}
                            </StatusChip>
                            <StatusChip
                                tone={dimension.evidenceStatus === "insufficient" ? "warn" : "ok"}
                            >
                                {humanize(dimension.evidenceStatus)} evidence
                            </StatusChip>
                        </div>
                        <p className="mt-3 text-sm text-text-secondary">{dimension.reason}</p>
                    </button>
                ))}
            </div>
        </section>
    );
}

function CreativeUpgrades({ run }: { run: TikTokScoreRun }) {
    return (
        <SurfaceCard padding="lg">
            <div className="flex items-start gap-3">
                <Sparkles className="mt-0.5 h-5 w-5 text-primary" />
                <div>
                    <h2 className="font-semibold text-text-primary">Make this version stronger</h2>
                    <p className="mt-1 text-sm text-text-secondary">
                        Based on your selected Creative Direction. These optional upgrades do not
                        change the current score.
                    </p>
                </div>
            </div>
            <div className="mt-4 space-y-3">
                {run.optionalUpgrades.map((upgrade) => (
                    <div key={upgrade.id} className="rounded-xl bg-primary-softer p-4">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                            <h3 className="font-medium text-text-primary">{upgrade.title}</h3>
                            <StatusChip tone="neutral">Does not affect score</StatusChip>
                        </div>
                        <p className="mt-2 text-sm text-text-secondary">{upgrade.whyItFits}</p>
                    </div>
                ))}
            </div>
        </SurfaceCard>
    );
}

function HandoffPanel({
    workspaceId,
    scoreId,
    fixes,
}: {
    workspaceId: string;
    scoreId: string;
    fixes: TikTokFixAction[];
}) {
    const [target, setTarget] = useState<"creator" | "editor">("creator");
    const message = useMemo(() => buildHandoffMessage(fixes, target), [fixes, target]);
    const send = useMutation({
        mutationFn: () =>
            Promise.all(
                fixes.map((fix) =>
                    recordTikTokFixAction(
                        workspaceId,
                        scoreId,
                        fix.id,
                        target === "creator" ? "sent_to_creator" : "sent_to_editor",
                        crypto.randomUUID(),
                    ),
                ),
            ),
        onSuccess: () => toast.success(`Sent-to-${target} events saved`),
        onError: (error) =>
            toast.error(
                error instanceof Error ? error.message : "Handoff events could not be saved",
            ),
    });
    return (
        <SurfaceCard padding="lg">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <h2 className="font-semibold text-text-primary">Creator/editor message</h2>
                    <p className="mt-1 text-sm text-text-secondary">
                        Built only from structured fix actions and strengths. Copying or sending
                        does not mark an action completed.
                    </p>
                </div>
                <Select
                    value={target}
                    onValueChange={(value) => setTarget(value as "creator" | "editor")}
                >
                    <SelectTrigger className="w-40" aria-label="Message recipient">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="creator">Creator</SelectItem>
                        <SelectItem value="editor">Editor</SelectItem>
                    </SelectContent>
                </Select>
            </div>
            <pre className="mt-4 max-h-80 overflow-auto whitespace-pre-wrap rounded-2xl bg-surface-soft p-4 font-sans text-sm text-text-secondary">
                {message}
            </pre>
            <div className="mt-4 flex flex-wrap justify-end gap-2">
                <Button
                    type="button"
                    variant="secondary"
                    onClick={() =>
                        void navigator.clipboard.writeText(message).then(
                            () => toast.success("Message copied"),
                            () => toast.error("Message could not be copied"),
                        )
                    }
                >
                    <Clipboard className="h-4 w-4" />
                    Copy
                </Button>
                <Button
                    type="button"
                    onClick={() => send.mutate()}
                    disabled={send.isPending || fixes.length === 0}
                >
                    <Send className="h-4 w-4" />
                    Send to {target}
                </Button>
            </div>
        </SurfaceCard>
    );
}

function seekFinding(
    run: TikTokScoreRun,
    finding: TikTokFinding,
    setTarget: (target: EvidenceSeekTarget) => void,
    workspaceId: string,
) {
    const evidence = run.evidence.find(
        (item) => finding.evidenceIds.includes(item.id) && item.startMs !== null,
    );
    let range = finding.targetTimeRangeMs;
    if (!range && evidence && evidence.startMs !== null && evidence.endMs !== null) {
        range = [evidence.startMs, evidence.endMs];
    }
    if (range)
        setTarget({
            key: `finding-${finding.id}-${Date.now()}`,
            timestampMs: range[0],
            range,
            evidenceId: evidence?.id,
        });
    void trackTikTokScoreEvent({
        eventType: "tiktok_finding_viewed",
        workspaceId,
        scoreRunId: run.id,
        assetVersionId: run.assetVersionId,
        findingId: finding.id,
        mode: run.scoreMode,
        profile: run.profile.code,
        intendedUse: run.intendedUse,
    });
}
function seekDimension(
    run: TikTokScoreRun,
    dimension: TikTokDimension,
    setTarget: (target: EvidenceSeekTarget) => void,
) {
    const evidence = run.evidence.find(
        (item) => dimension.evidenceIds.includes(item.id) && item.startMs !== null,
    );
    if (evidence?.startMs !== null && evidence?.startMs !== undefined)
        setTarget({
            key: `dimension-${dimension.code}-${Date.now()}`,
            timestampMs: evidence.startMs,
            range: evidence.endMs === null ? null : [evidence.startMs, evidence.endMs],
            evidenceId: evidence.id,
        });
}
function SummaryItem({ label, value, hint }: { label: string; value: string; hint?: string }) {
    return (
        <div>
            <dt className="text-xs font-medium uppercase text-text-tertiary">{label}</dt>
            <dd className="mt-1 text-sm font-medium text-text-primary">{value}</dd>
            {hint && <p className="mt-1 text-xs text-text-secondary">{hint}</p>}
        </div>
    );
}
function humanize(value: string) {
    return value
        .replace(/_v\d+$/, "")
        .replace(/_/g, " ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
function decisionTone(value: string) {
    return value === "blocked"
        ? ("destructive" as const)
        : value === "revise" || value === "request_better_media"
          ? ("warn" as const)
          : value === "structurally_ready"
            ? ("ok" as const)
            : ("info" as const);
}
function decisionTitle(value: string) {
    return value === "request_better_media"
        ? "Better media is needed before a responsible diagnosis"
        : value === "blocked"
          ? "Resolve verified blockers before publishing"
          : value === "revise"
            ? "Revise the required actions, then upload Draft 2"
            : value === "usable_with_improvements"
              ? "Usable structure with clear improvements available"
              : value === "structurally_ready"
                ? "Creative structure is ready for this context"
                : "Diagnosis pending";
}
