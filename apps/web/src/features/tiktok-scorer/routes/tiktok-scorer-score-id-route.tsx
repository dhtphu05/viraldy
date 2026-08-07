import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";
import {
    AlertTriangle,
    ArrowLeft,
    Clipboard,
    Loader2,
    MessageSquareText,
    RefreshCw,
    Send,
    Sparkles,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { FixPlan } from "../components/fix-plan";
import { RevisionPanel } from "../components/revision-panel";
import {
    DecisionSummary,
    Dimensions,
    ScoreVideoPreview,
    StrengthsAndBlockers,
} from "../components/score-result-panels";
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
