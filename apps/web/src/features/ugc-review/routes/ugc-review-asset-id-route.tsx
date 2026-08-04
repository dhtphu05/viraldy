import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";
import {
    ArrowLeft,
    Check,
    Clipboard,
    FileUp,
    Loader2,
    MessageSquareText,
    RefreshCw,
    Send,
    ShieldCheck,
    Sparkles,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { toast } from "sonner";

import { RecommendationGroups } from "../components/recommendation-groups";
import { RevisionComparison } from "../components/revision-comparison";
import { ReviewVideoPanel, type UgcEvidenceSeekTarget } from "../components/review-video-panel";
import { useUgcWorkspace } from "../hooks/use-ugc-workspace";
import type { UgcRecommendation, UgcRecommendationAction } from "../types/ugc-review";
import { humanizeLabel, humanizeSystemText } from "@/shared/lib/display";
import { queryKeys } from "@/shared/api/query-keys";
import {
    createUgcReviewRevision,
    getLatestUgcRevisionComparison,
    getUgcAssetPlayback,
    getUgcReviewResult,
    getUgcReviewStatus,
    recordUgcRecommendationAction,
    validateUgcVideo,
} from "@/shared/api/ugc-reviews";
import { uploadAssetRevision } from "@/shared/api/uploads";
import { Alert, AlertDescription, AlertTitle } from "@/shared/ui/alert";
import { Button } from "@/shared/ui/button";
import { ConfidenceBadge } from "@/shared/ui/confidence-badge";
import { PageHeader } from "@/shared/ui/page-header";
import { Progress } from "@/shared/ui/progress";
import { StatusChip } from "@/shared/ui/status-chip";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { AppShell } from "@/widgets/app-shell/app-shell";

export const Route = createFileRoute("/ugc-review/$assetId")({
    validateSearch: (search: Record<string, unknown>): { workspaceId?: string } => ({
        workspaceId: typeof search.workspaceId === "string" ? search.workspaceId : undefined,
    }),
    head: () => ({ meta: [{ title: "UGC Review result — Viraldy" }] }),
    component: UgcReviewResultRoute,
});

function UgcReviewResultRoute() {
    const { assetId: reviewId } = Route.useParams();
    const { workspaceId: linkedWorkspaceId } = Route.useSearch();
    const { workspaceId, workspaces } = useUgcWorkspace(linkedWorkspaceId);
    const queryClient = useQueryClient();
    const [seekTarget, setSeekTarget] = useState<UgcEvidenceSeekTarget | null>(null);
    const [savedActions, setSavedActions] = useState<
        Readonly<Record<string, UgcRecommendationAction>>
    >({});
    const [busyRecommendationId, setBusyRecommendationId] = useState<string | null>(null);
    const [revisionReviewId, setRevisionReviewId] = useState<string | null>(null);

    const status = useQuery({
        queryKey: queryKeys.ugcReviews.status(workspaceId, reviewId),
        queryFn: () => getUgcReviewStatus(workspaceId!, reviewId),
        enabled: Boolean(workspaceId),
        retry: 1,
        refetchInterval: (query) =>
            ["completed", "failed"].includes(query.state.data?.status ?? "") ? false : 2_000,
    });
    const review = useQuery({
        queryKey: queryKeys.ugcReviews.detail(workspaceId, reviewId),
        queryFn: () => getUgcReviewResult(workspaceId!, reviewId),
        enabled: Boolean(workspaceId && status.data?.status === "completed"),
        retry: 1,
    });
    const result = review.data;
    const playback = useQuery({
        queryKey: queryKeys.ugcReviews.playback(
            workspaceId,
            result?.assetId ?? null,
            result?.assetVersionId ?? null,
        ),
        queryFn: () => getUgcAssetPlayback(workspaceId!, result!.assetId, result!.assetVersionId),
        enabled: Boolean(workspaceId && result?.assetId && result.assetVersionId),
        retry: 0,
    });
    const childStatus = useQuery({
        queryKey: queryKeys.ugcReviews.status(workspaceId, revisionReviewId),
        queryFn: () => getUgcReviewStatus(workspaceId!, revisionReviewId!),
        enabled: Boolean(workspaceId && revisionReviewId),
        retry: 1,
        refetchInterval: (query) =>
            ["completed", "failed"].includes(query.state.data?.status ?? "") ? false : 2_000,
    });
    const comparison = useQuery({
        queryKey: queryKeys.ugcReviews.comparison(workspaceId, reviewId),
        queryFn: () => getLatestUgcRevisionComparison(workspaceId!, reviewId),
        enabled: Boolean(workspaceId && result),
        retry: false,
        refetchInterval: (query) =>
            childStatus.data?.status === "completed" && !query.state.data ? 2_000 : false,
    });

    useEffect(() => {
        if (childStatus.data?.status !== "completed") return;
        void queryClient.invalidateQueries({
            queryKey: queryKeys.ugcReviews.comparison(workspaceId, reviewId),
        });
    }, [childStatus.data?.status, queryClient, reviewId, workspaceId]);

    const actionMutation = useMutation({
        mutationFn: ({
            recommendation,
            action,
        }: {
            recommendation: UgcRecommendation;
            action: UgcRecommendationAction;
        }) => {
            setBusyRecommendationId(recommendation.id);
            return recordUgcRecommendationAction(workspaceId!, reviewId, recommendation.id, action);
        },
        onSuccess: (_receipt, variables) => {
            setSavedActions((current) => ({
                ...current,
                [variables.recommendation.id]: variables.action,
            }));
            toast.success("Recommendation action saved");
        },
        onError: () => toast.error("That action could not be saved. Please try again."),
        onSettled: () => setBusyRecommendationId(null),
    });

    if (workspaces.isLoading || (workspaceId && status.isLoading)) {
        return (
            <ReviewRouteFrame>
                <ReviewProcessing progress={0} stage="Preparing your review" />
            </ReviewRouteFrame>
        );
    }

    if (workspaces.isError || !workspaceId || status.isError || status.data?.status === "failed") {
        return (
            <ReviewRouteFrame>
                <RecoverableReviewState
                    workspaceId={workspaceId}
                    onRetry={() => {
                        void workspaces.refetch();
                        void status.refetch();
                    }}
                />
            </ReviewRouteFrame>
        );
    }

    if (status.data?.status !== "completed" || !result) {
        if (review.isError) {
            return (
                <ReviewRouteFrame>
                    <RecoverableReviewState
                        workspaceId={workspaceId}
                        onRetry={() => void review.refetch()}
                    />
                </ReviewRouteFrame>
            );
        }
        return (
            <ReviewRouteFrame>
                <ReviewProcessing
                    progress={status.data?.progress ?? 0}
                    stage={status.data?.stage ?? "Reviewing your draft"}
                />
            </ReviewRouteFrame>
        );
    }

    const recommendations = [...result.fixFirst, ...result.improvements, ...result.confirmations];
    const durationMs = provenanceDuration(result.provenance);

    return (
        <ReviewRouteFrame>
            <div className="flex flex-col gap-7">
                <PageHeader
                    title={result.headline}
                    description={result.summary}
                    actions={
                        <Button asChild variant="secondary" size="sm">
                            <Link to="/ugc-review" search={{ workspaceId }}>
                                <ArrowLeft className="h-4 w-4" />
                                Review another draft
                            </Link>
                        </Button>
                    }
                />

                <div className="flex flex-wrap items-center gap-2">
                    <StatusChip tone="info">
                        Recommended next action: {humanizeLabel(result.recommendedNextAction)}
                    </StatusChip>
                    <ConfidenceBadge level={result.overallConfidence} />
                </div>

                <section aria-labelledby="keep-title">
                    <SurfaceCard padding="lg" className="border-l-4 border-l-ok">
                        <div className="flex items-start gap-3">
                            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-ok-soft text-ok">
                                <ShieldCheck className="h-5 w-5" />
                            </span>
                            <div>
                                <h2
                                    id="keep-title"
                                    className="text-xl font-semibold text-text-primary"
                                >
                                    Keep
                                </h2>
                                <p className="mt-1 text-sm text-text-secondary">
                                    Preserve these strengths while making changes.
                                </p>
                            </div>
                        </div>
                        {result.strengths.length ? (
                            <ul className="mt-5 grid gap-3 md:grid-cols-2">
                                {result.strengths.map((strength) => (
                                    <li
                                        key={strength}
                                        className="flex gap-2 rounded-xl bg-ok-soft/60 p-3 text-sm text-text-primary"
                                    >
                                        <Check className="mt-0.5 h-4 w-4 shrink-0 text-ok" />
                                        {strength}
                                    </li>
                                ))}
                            </ul>
                        ) : (
                            <p className="mt-4 text-sm text-text-secondary">
                                The review did not identify a specific strength to preserve.
                            </p>
                        )}
                    </SurfaceCard>
                </section>

                <ReviewVideoPanel
                    mediaUrl={playback.data?.videoUrl ?? null}
                    durationMs={durationMs}
                    recommendations={recommendations}
                    seekTarget={seekTarget}
                />

                <RecommendationGroups
                    result={result}
                    savedActions={savedActions}
                    busyRecommendationId={busyRecommendationId}
                    onSeek={setSeekTarget}
                    onAction={(recommendation, action) =>
                        actionMutation.mutate({ recommendation, action })
                    }
                />

                <CreatorRevisionMessage
                    message={result.message}
                    recommendations={recommendations}
                    workspaceId={workspaceId}
                    reviewId={reviewId}
                    onActionsSaved={(ids) =>
                        setSavedActions((current) =>
                            ids.reduce<Readonly<Record<string, UgcRecommendationAction>>>(
                                (next, id) => ({ ...next, [id]: "sent_to_creator" }),
                                current,
                            ),
                        )
                    }
                />

                <RevisionUploader
                    workspaceId={workspaceId}
                    reviewId={reviewId}
                    assetId={result.assetId}
                    childStatus={childStatus.data ?? null}
                    onRevisionStarted={setRevisionReviewId}
                />

                {childStatus.data?.status === "failed" && (
                    <Alert>
                        <AlertTitle>The revised draft review needs another try</AlertTitle>
                        <AlertDescription>
                            Your original review is unchanged. Upload the revised draft again when
                            you are ready.
                        </AlertDescription>
                    </Alert>
                )}
                {comparison.data && <RevisionComparison comparison={comparison.data} />}
            </div>
        </ReviewRouteFrame>
    );
}

function ReviewRouteFrame({ children }: { children: React.ReactNode }) {
    return (
        <AppShell>
            <div className="mx-auto w-full max-w-6xl">{children}</div>
        </AppShell>
    );
}

function ReviewProcessing({ progress, stage }: { progress: number; stage: string }) {
    return (
        <div className="mx-auto max-w-2xl py-12">
            <SurfaceCard padding="lg" variant="raised">
                <div className="flex items-start gap-3">
                    <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-primary-softer text-primary">
                        <Sparkles className="h-5 w-5" />
                    </span>
                    <div className="min-w-0 flex-1">
                        <h1 className="text-xl font-semibold text-text-primary">
                            Reviewing your creator draft
                        </h1>
                        <p className="mt-1 text-sm text-text-secondary">
                            Viraldy is matching observed evidence to the context you supplied.
                        </p>
                    </div>
                </div>
                <Progress value={progress} className="mt-6" />
                <div className="mt-3 flex items-center justify-between gap-3 text-sm">
                    <span className="text-text-secondary">{humanizeSystemText(stage)}</span>
                    <span className="tabular-nums text-text-tertiary">{Math.round(progress)}%</span>
                </div>
            </SurfaceCard>
        </div>
    );
}

function RecoverableReviewState({
    workspaceId,
    onRetry,
}: {
    workspaceId?: string;
    onRetry: () => void;
}) {
    return (
        <div className="mx-auto max-w-2xl py-12">
            <SurfaceCard padding="lg">
                <RefreshCw className="h-8 w-8 text-primary" />
                <h1 className="mt-4 text-xl font-semibold text-text-primary">
                    This review needs another try
                </h1>
                <p className="mt-2 text-sm text-text-secondary">
                    The draft remains safely uploaded. Retry the review or return to start a new
                    one.
                </p>
                <div className="mt-5 flex flex-wrap gap-2">
                    <Button type="button" onClick={onRetry}>
                        <RefreshCw className="h-4 w-4" />
                        Try again
                    </Button>
                    <Button asChild variant="secondary">
                        <Link to="/ugc-review" search={{ workspaceId }}>
                            Back to UGC Review
                        </Link>
                    </Button>
                </div>
            </SurfaceCard>
        </div>
    );
}

function CreatorRevisionMessage({
    message,
    recommendations,
    workspaceId,
    reviewId,
    onActionsSaved,
}: {
    message: string;
    recommendations: readonly UgcRecommendation[];
    workspaceId: string;
    reviewId: string;
    onActionsSaved: (recommendationIds: readonly string[]) => void;
}) {
    const [copied, setCopied] = useState(false);
    const shareable = useMemo(
        () => recommendations.filter((item) => item.owner === "creator" || item.owner === "editor"),
        [recommendations],
    );
    const sent = useMutation({
        mutationFn: async () => {
            await Promise.all(
                shareable.map((recommendation) =>
                    recordUgcRecommendationAction(
                        workspaceId,
                        reviewId,
                        recommendation.id,
                        "sent_to_creator",
                    ),
                ),
            );
            return shareable.map((item) => item.id);
        },
        onSuccess: (ids) => {
            onActionsSaved(ids);
            toast.success("Revision message marked as sent");
        },
        onError: () => toast.error("Sent status could not be saved. Please try again."),
    });

    async function copy() {
        try {
            await navigator.clipboard.writeText(message);
            setCopied(true);
            toast.success("Revision message copied");
        } catch {
            toast.error("Copy was not available. Select the message and copy it manually.");
        }
    }

    return (
        <section aria-labelledby="creator-message-title">
            <SurfaceCard padding="lg" variant="raised">
                <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-primary-softer text-primary">
                            <MessageSquareText className="h-5 w-5" />
                        </span>
                        <div>
                            <h2
                                id="creator-message-title"
                                className="text-xl font-semibold text-text-primary"
                            >
                                Creator revision message
                            </h2>
                            <p className="mt-1 text-sm text-text-secondary">
                                Ready to copy and send to the creator.
                            </p>
                        </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <Button type="button" size="sm" variant="secondary" onClick={copy}>
                            <Clipboard className="h-4 w-4" />
                            {copied ? "Copied" : "Copy message"}
                        </Button>
                        <Button
                            type="button"
                            size="sm"
                            disabled={!shareable.length || sent.isPending}
                            onClick={() => sent.mutate()}
                        >
                            {sent.isPending ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                                <Send className="h-4 w-4" />
                            )}
                            Mark as sent
                        </Button>
                    </div>
                </div>
                <div className="mt-5 whitespace-pre-wrap rounded-2xl bg-surface-soft p-5 text-sm leading-7 text-text-primary">
                    {message}
                </div>
            </SurfaceCard>
        </section>
    );
}

function RevisionUploader({
    workspaceId,
    reviewId,
    assetId,
    childStatus,
    onRevisionStarted,
}: {
    workspaceId: string;
    reviewId: string;
    assetId: string;
    childStatus: Awaited<ReturnType<typeof getUgcReviewStatus>> | null;
    onRevisionStarted: (reviewId: string) => void;
}) {
    const [file, setFile] = useState<File | null>(null);
    const [fileError, setFileError] = useState<string | null>(null);
    const [progress, setProgress] = useState(0);
    const inputRef = useRef<HTMLInputElement>(null);
    const revision = useMutation({
        mutationFn: async () => {
            if (!file) throw new Error("Choose a revised draft first.");
            const validationError = validateUgcVideo(file);
            if (validationError) throw new Error(validationError);
            const version = await uploadAssetRevision(workspaceId, assetId, file, setProgress);
            return createUgcReviewRevision(workspaceId, reviewId, version.id);
        },
        onSuccess: (created) => {
            onRevisionStarted(created.reviewId);
            toast.success("Draft 2 uploaded. The comparison will appear after review.");
        },
        onError: () => toast.error("The revised draft could not be uploaded. Please try again."),
    });

    function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        const validationError = file ? validateUgcVideo(file) : "Choose a revised video.";
        setFileError(validationError);
        if (!validationError && !revision.isPending) revision.mutate();
    }

    return (
        <section aria-labelledby="upload-revision-title">
            <SurfaceCard padding="lg">
                <div className="flex items-start gap-3">
                    <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-info-soft text-info">
                        <FileUp className="h-5 w-5" />
                    </span>
                    <div>
                        <h2
                            id="upload-revision-title"
                            className="text-xl font-semibold text-text-primary"
                        >
                            Upload revised draft
                        </h2>
                        <p className="mt-1 text-sm text-text-secondary">
                            Draft 2 will be reviewed independently and compared with this result.
                        </p>
                    </div>
                </div>
                <form onSubmit={submit} className="mt-5">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                        <input
                            ref={inputRef}
                            type="file"
                            accept="video/mp4,video/quicktime,.mp4,.mov"
                            aria-label="Choose revised UGC video"
                            className="min-w-0 flex-1 text-sm text-text-secondary file:mr-3 file:rounded-lg file:border file:border-control-border file:bg-surface file:px-3 file:py-2 file:text-sm file:font-medium file:text-text-primary"
                            onChange={(event) => {
                                const next = event.target.files?.item(0) ?? null;
                                setFile(next);
                                setFileError(next ? validateUgcVideo(next) : null);
                            }}
                        />
                        <Button type="submit" disabled={revision.isPending || !file}>
                            {revision.isPending ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                                <FileUp className="h-4 w-4" />
                            )}
                            Upload Draft 2
                        </Button>
                    </div>
                    {fileError && (
                        <p className="mt-2 text-sm text-destructive" role="alert">
                            {fileError}
                        </p>
                    )}
                    {revision.isPending && (
                        <div className="mt-4" aria-live="polite">
                            <Progress value={progress} />
                            <p className="mt-2 text-xs text-text-secondary">
                                {progress < 100
                                    ? `Uploading Draft 2 · ${Math.max(1, progress)}%`
                                    : "Starting the Draft 2 review"}
                            </p>
                        </div>
                    )}
                    {childStatus &&
                        childStatus.status !== "completed" &&
                        childStatus.status !== "failed" && (
                            <div className="mt-4 rounded-xl bg-info-soft p-4" aria-live="polite">
                                <p className="text-sm font-medium text-info">
                                    Reviewing Draft 2 · {Math.round(childStatus.progress)}%
                                </p>
                                <p className="mt-1 text-xs text-text-secondary">
                                    {humanizeSystemText(childStatus.stage)}
                                </p>
                            </div>
                        )}
                </form>
            </SurfaceCard>
        </section>
    );
}

function provenanceDuration(provenance: Readonly<Record<string, unknown>>): number | null {
    const value = provenance.media_duration_ms;
    return typeof value === "number" && Number.isFinite(value) && value > 0 ? value : null;
}
