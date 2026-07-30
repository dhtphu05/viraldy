import { createFileRoute, Link, notFound, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useState, useRef } from "react";
import { AppShell } from "@/widgets/app-shell/app-shell";
import { PageHeader } from "@/shared/ui/page-header";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { StatusChip } from "@/shared/ui/status-chip";
import { Button } from "@/shared/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/shared/ui/tabs";
import { Textarea } from "@/shared/ui/textarea";
import { Slider } from "@/shared/ui/slider";
import { formatUtcDateTime } from "@/shared/lib/date-format";
import { EmptyState } from "@/shared/ui/empty-state";
import { ProcessingStepper, type Step } from "@/shared/ui/processing-stepper";
import { AnalysisThinkingSkeleton } from "@/shared/ui/analysis-thinking-skeleton";
import { AnalysisTimelineSvg } from "@/shared/ui/analysis-timeline-svg";
import { DemoMediaTile } from "@/shared/ui/demo-media-tile";
import { cn } from "@/shared/lib/utils";
import { useAppStore, useAllCampaigns } from "@/app/store/app-store";
import { seedCreators } from "@/features/ugc-review/mocks/creators";
import {
    generateRevisionMessage,
    ugcProcessingSteps,
} from "@/features/ugc-review/lib/mockUgcAnalysis";
import { RightsReadinessDrawer } from "@/features/ugc-review/components/rights-readiness-drawer";
import {
    ArrowLeft,
    Copy,
    Play,
    Pause,
    ChevronLeft,
    ChevronRight,
    Sparkles,
    ScanSearch,
} from "lucide-react";
import { toast } from "sonner";
import type { UgcAsset, UgcDecision, UgcIssue } from "@/features/ugc-review/types/ugc";

export const Route = createFileRoute("/ugc-review/$assetId")({
    head: () => ({ meta: [{ title: "UGC Review — Asset" }] }),
    component: UgcDetail,
    notFoundComponent: () => (
        <AppShell>
            <EmptyState
                title="Asset not found"
                description="The asset you're looking for may have been deleted."
                action={
                    <Button asChild size="sm">
                        <Link to="/ugc-review">Back to UGC Review</Link>
                    </Button>
                }
            />
        </AppShell>
    ),
});

const decisionMeta: Record<
    UgcDecision,
    { label: string; tone: "neutral" | "ok" | "warn" | "info" | "destructive" }
> = {
    "awaiting-analysis": { label: "Awaiting analysis", tone: "neutral" },
    processing: { label: "Processing", tone: "info" },
    failed: { label: "Analysis failed", tone: "destructive" },
    "request-revision": { label: "Request revision", tone: "warn" },
    reject: { label: "Reject / reshoot", tone: "destructive" },
    "organic-ready": { label: "Organic-ready", tone: "ok" },
    "small-spark-test": { label: "Small Spark test", tone: "info" },
    "spark-ready": { label: "Spark-ready", tone: "ok" },
};

function fmt(sec: number) {
    const m = Math.floor(sec / 60)
        .toString()
        .padStart(2, "0");
    const s = Math.floor(sec % 60)
        .toString()
        .padStart(2, "0");
    return `${m}:${s}`;
}

const EMPTY_UGC_ISSUES: UgcIssue[] = [];

function UgcDetail() {
    const { assetId } = Route.useParams();
    const navigate = useNavigate();
    const asset = useAppStore((s) => s.ugcAssets.find((a) => a.id === assetId));
    const analyses = useAppStore((s) => s.ugcAnalyses);
    const analysis = analyses[assetId];
    const issues = useAppStore((s) => s.ugcIssues[assetId] ?? EMPTY_UGC_ISSUES);
    const rights = useAppStore((s) => s.ugcRights[assetId]);
    const ugcAssets = useAppStore((s) => s.ugcAssets);
    const jobs = useAppStore((s) => s.ugcJobs);
    const versions = useMemo(
        () =>
            ugcAssets.filter(
                (a) =>
                    a.campaignId &&
                    asset?.campaignId &&
                    a.campaignId === asset.campaignId &&
                    a.title.split(" V")[0] === asset.title.split(" V")[0],
            ),
        [asset?.campaignId, asset?.title, ugcAssets],
    );
    const previousVersion = useMemo(() => {
        if (!asset) return undefined;
        if (asset.previousVersionId) {
            return ugcAssets.find((candidate) => candidate.id === asset.previousVersionId);
        }
        return [...versions]
            .filter((candidate) => candidate.submissionVersion < asset.submissionVersion)
            .sort((a, b) => b.submissionVersion - a.submissionVersion)[0];
    }, [asset, ugcAssets, versions]);
    const campaigns = useAllCampaigns();
    const toggleIssue = useAppStore((s) => s.toggleIssueInRevision);
    const dismissIssue = useAppStore((s) => s.dismissIssue);
    const reviewIssue = useAppStore((s) => s.reviewIssue);
    const setRevisionMessage = useAppStore((s) => s.setRevisionMessage);
    const markRevisionRequested = useAppStore((s) => s.markRevisionRequested);
    const approveOrganic = useAppStore((s) => s.approveUgcOrganic);
    const markSparkReady = useAppStore((s) => s.markUgcSparkReady);
    const rejectUgc = useAppStore((s) => s.rejectUgc);
    const updateRights = useAppStore((s) => s.updateUgcRights);
    const retryUgcAnalysis = useAppStore((s) => s.retryUgcAnalysis);
    const startAnalysis = useAppStore((s) => s.startUgcAnalysis);
    const advance = useAppStore((s) => s.advanceUgcJob);
    const completeAnalysis = useAppStore((s) => s.completeUgcAnalysis);

    const [showRights, setShowRights] = useState(false);
    const rightsTriggerRef = useRef<HTMLElement | null>(null);
    const videoRef = useRef<HTMLVideoElement>(null);
    const [playing, setPlaying] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);

    useEffect(() => {
        const active = jobs[assetId];
        if (!active) return;
        const timer = window.setInterval(() => {
            const current = useAppStore.getState().ugcJobs[assetId];
            if (!current) return;
            if (current.step >= current.total - 1) completeAnalysis(assetId);
            else advance(assetId);
        }, 700);
        return () => window.clearInterval(timer);
    }, [advance, assetId, completeAnalysis, jobs]);

    if (!asset) throw notFound();

    const job = jobs[assetId];
    const processingSteps: Step[] = job
        ? ugcProcessingSteps.map((label, index) => ({
              key: label,
              label,
              status: index < job.step ? "done" : index === job.step ? "active" : "pending",
          }))
        : [];
    const mediaAspect =
        asset.mediaAspectRatio === "9:16"
            ? "9 / 16"
            : asset.mediaAspectRatio === "1:1"
              ? "1 / 1"
              : asset.mediaAspectRatio === "4:5"
                ? "4 / 5"
                : "16 / 9";
    const verticalMedia = asset.mediaAspectRatio === "9:16";
    const meta = decisionMeta[asset.decision];
    const creator = seedCreators.find((c) => c.id === asset.creatorId);
    const campaign = campaigns.find((c) => c.id === asset.campaignId);

    const positives = issues.filter((i) => i.severity === "positive" && !i.dismissed);
    const blockers = issues.filter((i) => i.severity === "blocker" && !i.dismissed);
    const highs = issues.filter((i) => i.severity === "high" && !i.dismissed);
    const improvements = issues.filter((i) => i.severity === "improvement" && !i.dismissed);

    const selectedIssues = issues.filter((i) => i.addedToRevision);
    const revisionMessage = useMemo(() => {
        if (asset.revisionMessage) return asset.revisionMessage;
        return generateRevisionMessage(
            creator?.name.split(" ")[0] ?? "",
            positives.slice(0, 2).map((p) => p.title + "."),
            selectedIssues.map((i) => i.fix),
        );
    }, [asset.revisionMessage, creator, positives, selectedIssues]);

    const openRights = () => {
        rightsTriggerRef.current =
            document.activeElement instanceof HTMLElement ? document.activeElement : null;
        setShowRights(true);
    };

    const jumpTo = (sec: number) => {
        setCurrentTime(sec);
        if (videoRef.current) {
            videoRef.current.currentTime = sec;
            videoRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
        }
    };

    const onMarkSpark = () => {
        const r = markSparkReady(assetId);
        if (r.ok) {
            setShowRights(false);
            toast.success("Marked Spark-ready");
            return true;
        }
        openRights();
        return false;
    };

    return (
        <AppShell>
            <div className="flex flex-col gap-6">
                <div>
                    <Link
                        to="/ugc-review"
                        className="inline-flex items-center gap-1 text-xs text-text-tertiary hover:text-text-primary"
                    >
                        <ArrowLeft className="h-3 w-3" /> UGC Review
                    </Link>
                </div>
                <PageHeader
                    title={asset.title}
                    description={`${creator?.name ?? ""} · ${campaign?.name ?? "No campaign"} · v${asset.submissionVersion} · Submitted ${formatUtcDateTime(asset.submittedAt)}`}
                    actions={
                        <>
                            <Button variant="ghost" size="sm" onClick={() => rejectUgc(assetId)}>
                                Request reshoot
                            </Button>
                            {asset.decision === "failed" && (
                                <Button size="sm" onClick={() => retryUgcAnalysis(assetId)}>
                                    Retry analysis
                                </Button>
                            )}
                            {(asset.decision === "organic-ready" ||
                                asset.decision === "small-spark-test") && (
                                <Button
                                    size="sm"
                                    variant="secondary"
                                    onClick={() => approveOrganic(assetId)}
                                >
                                    Approve organic
                                </Button>
                            )}
                            {(asset.decision === "organic-ready" ||
                                asset.decision === "small-spark-test" ||
                                asset.decision === "spark-ready") && (
                                <Button size="sm" onClick={onMarkSpark}>
                                    Mark Spark-ready
                                </Button>
                            )}
                        </>
                    }
                />

                <div className="grid gap-6 lg:grid-cols-12">
                    {/* Left: video + evidence */}
                    <div className="flex min-w-0 flex-col gap-4 lg:col-span-8">
                        <div
                            className={`relative overflow-hidden rounded-[22px] bg-[#0a0a0f] shadow-lg ${verticalMedia ? "mx-auto w-full max-w-[420px]" : ""}`}
                        >
                            <div className="pointer-events-none absolute left-3 top-3 z-10 flex flex-wrap items-center gap-1.5">
                                <span className="rounded-md bg-white/90 px-2 py-0.5 text-[11px] font-semibold text-text-primary shadow-sm">
                                    Real video
                                </span>
                                <span className="rounded-md bg-black/45 px-2 py-0.5 text-[11px] font-medium text-white backdrop-blur-sm">
                                    {asset.mediaAspectRatio ?? "16:9"}
                                </span>
                                <span className="rounded-md bg-black/45 px-2 py-0.5 text-[11px] font-medium text-white backdrop-blur-sm">
                                    {verticalMedia ? "Vertical" : "Landscape"}
                                </span>
                            </div>
                            <div style={{ aspectRatio: mediaAspect }}>
                                {asset.mediaUrl ? (
                                    <video
                                        ref={videoRef}
                                        src={asset.mediaUrl}
                                        poster={asset.posterUrl}
                                        className="h-full w-full object-contain"
                                        playsInline
                                        preload="metadata"
                                        onTimeUpdate={(e) =>
                                            setCurrentTime(e.currentTarget.currentTime)
                                        }
                                        onPlay={() => setPlaying(true)}
                                        onPause={() => setPlaying(false)}
                                    />
                                ) : (
                                    <div
                                        className="h-full w-full"
                                        style={{
                                            background: `linear-gradient(135deg, hsl(${(asset.thumbSeed.charCodeAt(0) * 7) % 360} 60% 40%), hsl(${(asset.thumbSeed.charCodeAt(0) * 11) % 360} 60% 25%))`,
                                        }}
                                    />
                                )}
                            </div>
                            {/* Controls */}
                            <div className="flex items-center gap-3 bg-black/40 px-3 py-2 text-white">
                                <button
                                    aria-label="Back 5s"
                                    onClick={() => jumpTo(Math.max(0, currentTime - 5))}
                                    className="rounded p-1 hover:bg-white/10"
                                >
                                    <ChevronLeft className="h-4 w-4" />
                                </button>
                                <button
                                    aria-label={playing ? "Pause" : "Play"}
                                    onClick={() => {
                                        if (!videoRef.current) return;
                                        if (playing) {
                                            videoRef.current.pause();
                                        } else {
                                            void videoRef.current.play();
                                        }
                                    }}
                                    className="rounded p-1 hover:bg-white/10"
                                >
                                    {playing ? (
                                        <Pause className="h-4 w-4" />
                                    ) : (
                                        <Play className="h-4 w-4" />
                                    )}
                                </button>
                                <button
                                    aria-label="Forward 5s"
                                    onClick={() =>
                                        jumpTo(Math.min(asset.durationSec, currentTime + 5))
                                    }
                                    className="rounded p-1 hover:bg-white/10"
                                >
                                    <ChevronRight className="h-4 w-4" />
                                </button>
                                <span className="text-xs tabular-nums">
                                    {fmt(currentTime)} / {fmt(asset.durationSec)}
                                </span>
                            </div>
                        </div>

                        {job && (
                            <SurfaceCard padding="md" className="space-y-3" aria-live="polite">
                                <div className="flex items-center justify-between gap-3">
                                    <div>
                                        <p className="text-sm font-semibold text-text-primary">
                                            Thinking through this draft
                                        </p>
                                        <p className="mt-0.5 text-xs text-text-tertiary">
                                            Comparing video, transcript, on-screen text, rights, and
                                            campaign requirements.
                                        </p>
                                    </div>
                                    <StatusChip tone="info">Step {job.step + 1}</StatusChip>
                                </div>
                                <ProcessingStepper steps={processingSteps} />
                                <AnalysisThinkingSkeleton
                                    compact
                                    title="Building review modules"
                                    description="Preparing timeline markers, transcript, scene list, issue evidence, and revision notes."
                                />
                            </SurfaceCard>
                        )}

                        {!job && !analysis && (
                            <AnalysisThinkingSkeleton
                                title="Analysis modules are ready to run"
                                description="After analysis, this area fills with timeline markers, transcript, scenes, on-screen text, issues, and campaign alignment."
                            />
                        )}

                        {/* Timeline markers */}
                        {analysis && analysis.markers.length > 0 && (
                            <AnalysisTimelineSvg
                                title="Review timeline"
                                durationSec={asset.durationSec}
                                currentTime={currentTime}
                                previewMediaUrl={asset.mediaUrl}
                                previewPosterUrl={asset.posterUrl}
                                previewMediaKind="video"
                                markers={analysis.markers.map((marker) => {
                                    const issue = issues.find(
                                        (candidate) => candidate.id === marker.issueId,
                                    );
                                    return {
                                        id: marker.id,
                                        at: marker.timestampSec,
                                        endAt: issue
                                            ? (issue.endSec ??
                                              Math.min(asset.durationSec, issue.timestampSec + 1.4))
                                            : undefined,
                                        label: marker.label,
                                        kind: marker.kind,
                                        tone:
                                            issue?.severity === "blocker"
                                                ? ("destructive" as const)
                                                : issue?.severity === "high" ||
                                                    issue?.severity === "improvement"
                                                  ? ("warn" as const)
                                                  : issue?.severity === "positive"
                                                    ? ("ok" as const)
                                                    : undefined,
                                    };
                                })}
                                onJump={(time) => jumpTo(time)}
                            />
                        )}

                        {previousVersion && analysis && (
                            <RevisionCompareSlider
                                before={previousVersion}
                                after={asset}
                                beforeScore={analyses[previousVersion.id]?.score}
                                afterScore={analysis.score}
                            />
                        )}

                        {analysis && analysis.transcript.length > 0 && (
                            <SurfaceCard padding="md">
                                <Tabs defaultValue="transcript">
                                    <TabsList>
                                        <TabsTrigger value="transcript">Transcript</TabsTrigger>
                                        <TabsTrigger value="scenes">Scenes</TabsTrigger>
                                        <TabsTrigger value="onscreen">On-screen text</TabsTrigger>
                                    </TabsList>
                                    <TabsContent value="transcript" className="mt-3 space-y-1.5">
                                        {analysis.transcript.map((t) => (
                                            <button
                                                key={t.id}
                                                onClick={() => jumpTo(t.startSec)}
                                                className="block w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-surface-soft focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                                            >
                                                <span className="mr-2 font-mono text-xs text-text-tertiary">
                                                    {fmt(t.startSec)}
                                                </span>
                                                <span className="text-text-primary">{t.text}</span>
                                            </button>
                                        ))}
                                    </TabsContent>
                                    <TabsContent value="scenes" className="mt-3 space-y-2">
                                        {analysis.scenes.map((s) => (
                                            <div
                                                key={s.id}
                                                className="rounded-md bg-surface-soft/60 px-3 py-2 text-sm"
                                            >
                                                <div className="flex items-center justify-between">
                                                    <span className="font-medium">
                                                        Scene {s.number}: {s.label}
                                                    </span>
                                                    <StatusChip
                                                        tone={
                                                            s.requirementStatus === "Complete"
                                                                ? "ok"
                                                                : s.requirementStatus === "Missing"
                                                                  ? "destructive"
                                                                  : "warn"
                                                        }
                                                    >
                                                        {s.requirementStatus}
                                                    </StatusChip>
                                                </div>
                                                <p className="mt-1 text-xs text-text-secondary">
                                                    {fmt(s.startSec)}–{fmt(s.endSec)} ·{" "}
                                                    {s.productVisibility}
                                                </p>
                                                <p className="mt-1 text-sm">{s.spokenLine}</p>
                                                {s.onScreenText && (
                                                    <p className="mt-1 text-xs text-text-tertiary">
                                                        On-screen: {s.onScreenText}
                                                    </p>
                                                )}
                                            </div>
                                        ))}
                                    </TabsContent>
                                    <TabsContent value="onscreen" className="mt-3 space-y-1.5">
                                        {analysis.onScreenText.length === 0 && (
                                            <p className="text-sm text-text-secondary">
                                                No on-screen text detected.
                                            </p>
                                        )}
                                        {analysis.onScreenText.map((o) => (
                                            <div
                                                key={o.id}
                                                className="flex items-center gap-3 rounded-md bg-surface-soft/60 px-3 py-2 text-sm"
                                            >
                                                <span className="font-mono text-xs text-text-tertiary">
                                                    {fmt(o.timestampSec)}
                                                </span>
                                                <span className="flex-1">{o.text}</span>
                                                <StatusChip
                                                    tone={
                                                        o.ctaFlag
                                                            ? "info"
                                                            : o.offerFlag
                                                              ? "ok"
                                                              : "neutral"
                                                    }
                                                >
                                                    {o.role}
                                                </StatusChip>
                                            </div>
                                        ))}
                                    </TabsContent>
                                </Tabs>
                            </SurfaceCard>
                        )}

                        {/* Issues */}
                        {issues.length > 0 && (
                            <SurfaceCard padding="md" className="space-y-3">
                                <p className="text-sm font-semibold">Issues & evidence</p>
                                {blockers.length > 0 && (
                                    <IssueGroup
                                        title="Blockers"
                                        issues={blockers}
                                        onJump={jumpTo}
                                        onToggle={(id) => toggleIssue(assetId, id)}
                                        onDismiss={(id) => dismissIssue(assetId, id, true)}
                                        onReview={(id) => reviewIssue(assetId, id)}
                                    />
                                )}
                                {highs.length > 0 && (
                                    <IssueGroup
                                        title="High priority"
                                        issues={highs}
                                        onJump={jumpTo}
                                        onToggle={(id) => toggleIssue(assetId, id)}
                                        onDismiss={(id) => dismissIssue(assetId, id, true)}
                                        onReview={(id) => reviewIssue(assetId, id)}
                                    />
                                )}
                                {improvements.length > 0 && (
                                    <IssueGroup
                                        title="Improvements"
                                        issues={improvements}
                                        onJump={jumpTo}
                                        onToggle={(id) => toggleIssue(assetId, id)}
                                        onDismiss={(id) => dismissIssue(assetId, id, true)}
                                        onReview={(id) => reviewIssue(assetId, id)}
                                    />
                                )}
                                {positives.length > 0 && (
                                    <div>
                                        <p className="mb-2 text-xs uppercase tracking-wider text-text-tertiary">
                                            What works
                                        </p>
                                        <ul className="space-y-1.5">
                                            {positives.map((p) => (
                                                <li
                                                    key={p.id}
                                                    className="rounded-md bg-ok-soft/40 px-3 py-2 text-sm"
                                                >
                                                    <span className="mr-2 font-mono text-xs text-ok">
                                                        {fmt(p.timestampSec)}
                                                    </span>
                                                    <span className="font-medium">{p.title}</span>
                                                    <p className="mt-0.5 text-xs text-text-secondary">
                                                        {p.why}
                                                    </p>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </SurfaceCard>
                        )}

                        {/* Revision message */}
                        {(asset.decision === "request-revision" || selectedIssues.length > 0) && (
                            <SurfaceCard padding="md" className="space-y-3">
                                <div className="flex items-center justify-between">
                                    <p className="text-sm font-semibold">
                                        Creator revision message
                                    </p>
                                    <p className="text-xs text-text-tertiary">
                                        {selectedIssues.length} issue
                                        {selectedIssues.length === 1 ? "" : "s"} selected
                                    </p>
                                </div>
                                <Textarea
                                    aria-label="Creator revision message"
                                    value={revisionMessage}
                                    onChange={(e) => setRevisionMessage(assetId, e.target.value)}
                                    rows={8}
                                />
                                <div className="flex flex-wrap gap-2">
                                    <Button
                                        size="sm"
                                        variant="secondary"
                                        onClick={() => {
                                            navigator.clipboard?.writeText(revisionMessage);
                                            toast.success("Copied to clipboard");
                                        }}
                                    >
                                        <Copy className="mr-1 h-3.5 w-3.5" /> Copy
                                    </Button>
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        onClick={() => setRevisionMessage(assetId, "")}
                                    >
                                        Reset
                                    </Button>
                                    <Button
                                        size="sm"
                                        onClick={() => {
                                            markRevisionRequested(assetId);
                                            toast.success("Revision marked as requested");
                                        }}
                                    >
                                        Mark revision requested
                                    </Button>
                                </div>
                            </SurfaceCard>
                        )}
                    </div>

                    {/* Right: decision panel */}
                    <div className="flex min-w-0 flex-col gap-4 lg:col-span-4">
                        <SurfaceCard
                            key={asset.decision}
                            padding="md"
                            className="analysis-state-enter lg:sticky lg:top-20 lg:z-10"
                        >
                            <StatusChip tone={meta.tone} dot className="uppercase tracking-wide">
                                {meta.label}
                            </StatusChip>
                            <h2 className="mt-3 text-lg font-semibold tracking-tight text-text-primary">
                                {analysis?.summary ?? "Analysis pending."}
                            </h2>
                            {analysis?.reason && (
                                <p className="mt-1 text-sm text-text-secondary">
                                    {analysis.reason}
                                </p>
                            )}
                            {analysis?.nextAction && (
                                <div className="mt-3 rounded-md bg-surface-soft/70 px-3 py-2 text-sm">
                                    <p className="text-xs uppercase tracking-wider text-text-tertiary">
                                        Next action
                                    </p>
                                    <p className="mt-1 text-text-primary">{analysis.nextAction}</p>
                                </div>
                            )}
                            {analysis && (
                                <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-text-secondary">
                                    <span>
                                        <span className="text-text-tertiary">Score</span>{" "}
                                        <b className="text-text-primary">{analysis.score}</b>
                                    </span>
                                    <span>
                                        <span className="text-text-tertiary">Confidence</span>{" "}
                                        {analysis.confidence}
                                    </span>
                                    {blockers.length > 0 && (
                                        <StatusChip tone="destructive">
                                            {blockers.length} must fix
                                        </StatusChip>
                                    )}
                                    {positives.length > 0 && (
                                        <StatusChip tone="ok">
                                            {positives.length} strength
                                            {positives.length === 1 ? "" : "s"}
                                        </StatusChip>
                                    )}
                                </div>
                            )}
                        </SurfaceCard>

                        <SurfaceCard padding="md" className="border-primary/20 bg-primary-soft/35">
                            <p className="text-xs font-semibold uppercase tracking-wide text-primary-active">
                                Primary action
                            </p>
                            <p className="mt-1 text-sm text-text-primary">
                                {analysis?.nextAction ?? primaryUgcAction(asset.decision)}
                            </p>
                            <div className="mt-3 flex flex-wrap gap-2">
                                {(asset.decision === "awaiting-analysis" ||
                                    asset.decision === "processing") && (
                                    <Button
                                        size="sm"
                                        onClick={() =>
                                            startAnalysis(assetId, ugcProcessingSteps.length)
                                        }
                                        disabled={asset.decision === "processing"}
                                    >
                                        <Sparkles className="h-4 w-4" />
                                        Analyze now
                                    </Button>
                                )}
                                {asset.decision === "request-revision" && (
                                    <Button
                                        size="sm"
                                        onClick={() => {
                                            markRevisionRequested(assetId);
                                            toast.success("Revision marked as requested");
                                        }}
                                    >
                                        Mark revision requested
                                    </Button>
                                )}
                                {(asset.decision === "organic-ready" ||
                                    asset.decision === "small-spark-test" ||
                                    asset.decision === "spark-ready") && (
                                    <Button size="sm" onClick={onMarkSpark}>
                                        Mark Spark-ready
                                    </Button>
                                )}
                                <Button size="sm" variant="secondary" onClick={openRights}>
                                    Review rights
                                </Button>
                            </div>
                        </SurfaceCard>

                        {analysis && analysis.dimensions.length > 0 && (
                            <SurfaceCard padding="md">
                                <p className="mb-3 text-sm font-semibold">Score breakdown</p>
                                <ul className="space-y-2.5">
                                    {analysis.dimensions.map((d) => (
                                        <li key={d.id}>
                                            <div className="flex items-baseline justify-between text-sm">
                                                <span className="text-text-primary">{d.label}</span>
                                                <span className="tabular-nums text-text-secondary">
                                                    {d.score}
                                                </span>
                                            </div>
                                            <div
                                                className="mt-1 h-1.5 w-full rounded-full bg-surface-soft"
                                                aria-label={`${d.label} ${d.score} of 100`}
                                            >
                                                <div
                                                    className={`analysis-score-fill h-1.5 rounded-full ${d.score >= 80 ? "bg-ok" : d.score >= 60 ? "bg-warn" : "bg-destructive"}`}
                                                    style={{ width: `${Math.max(4, d.score)}%` }}
                                                />
                                            </div>
                                            <p className="mt-1 text-xs text-text-tertiary">
                                                {d.reason}
                                            </p>
                                        </li>
                                    ))}
                                </ul>
                            </SurfaceCard>
                        )}

                        {analysis && analysis.packAlignment.length > 0 && (
                            <SurfaceCard padding="md">
                                <p className="mb-2 text-sm font-semibold">
                                    Campaign Pack alignment
                                </p>
                                <ul className="space-y-1.5 text-sm">
                                    {analysis.packAlignment.map((row, index) => {
                                        const linkedIssue = issues.find(
                                            (issue) =>
                                                issue.packRequirement &&
                                                (issue.packRequirement
                                                    .toLowerCase()
                                                    .includes(row.requirement.toLowerCase()) ||
                                                    row.requirement
                                                        .toLowerCase()
                                                        .includes(
                                                            issue.packRequirement.toLowerCase(),
                                                        )),
                                        );
                                        const tone =
                                            row.status === "Complete"
                                                ? "ok"
                                                : row.status === "Missing"
                                                  ? "destructive"
                                                  : "warn";
                                        return (
                                            <li key={`${row.requirement}-${index}`}>
                                                <button
                                                    type="button"
                                                    disabled={!linkedIssue}
                                                    onClick={() =>
                                                        linkedIssue &&
                                                        jumpTo(linkedIssue.timestampSec)
                                                    }
                                                    className={cn(
                                                        "w-full rounded-md border-l-2 px-3 py-2 text-left transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                                                        row.status === "Complete" &&
                                                            "border-l-ok bg-ok-soft/35",
                                                        row.status === "Needs revision" &&
                                                            "border-l-warn bg-warn-soft/50",
                                                        row.status === "Missing" &&
                                                            "border-l-destructive bg-destructive-soft/55",
                                                        linkedIssue && "hover:bg-primary-soft/45",
                                                    )}
                                                >
                                                    <div className="flex items-start justify-between gap-2">
                                                        <div className="min-w-0">
                                                            <p className="text-[10px] font-semibold uppercase tracking-wide text-text-tertiary">
                                                                Expected
                                                            </p>
                                                            <p className="font-medium text-text-primary">
                                                                {row.requirement}
                                                            </p>
                                                        </div>
                                                        <StatusChip tone={tone}>
                                                            {row.status}
                                                        </StatusChip>
                                                    </div>
                                                    <p className="mt-1 text-[10px] font-semibold uppercase tracking-wide text-text-tertiary">
                                                        Observed
                                                    </p>
                                                    <p className="text-xs text-text-secondary">
                                                        {row.detected}
                                                    </p>
                                                    {linkedIssue && (
                                                        <span className="mt-1.5 inline-flex items-center gap-1 text-[11px] font-medium text-info">
                                                            <ScanSearch className="h-3 w-3" />
                                                            Open evidence at{" "}
                                                            {fmt(linkedIssue.timestampSec)}
                                                        </span>
                                                    )}
                                                </button>
                                            </li>
                                        );
                                    })}
                                </ul>
                            </SurfaceCard>
                        )}

                        {rights && (
                            <SurfaceCard padding="md">
                                <div className="mb-2 flex items-center justify-between">
                                    <p className="text-sm font-semibold">Rights & Spark</p>
                                    <Button size="sm" variant="ghost" onClick={openRights}>
                                        Edit
                                    </Button>
                                </div>
                                <ul className="space-y-1 text-xs text-text-secondary">
                                    <li>Organic: {rights.organic ? "Allowed" : "Not allowed"}</li>
                                    <li>
                                        Spark Ads: {rights.sparkAllowed ? "Allowed" : "Not allowed"}
                                    </li>
                                    <li>Spark code: {rights.sparkCode ?? "—"}</li>
                                    <li>
                                        Usage duration:{" "}
                                        {rights.durationDays ? `${rights.durationDays} days` : "—"}
                                    </li>
                                    <li>
                                        Creator confirmation:{" "}
                                        {rights.creatorConfirmed ? "Confirmed" : "Not yet"}
                                    </li>
                                </ul>
                                <p className="mt-2 text-[11px] text-text-tertiary">
                                    Operational readiness only. Confirm final rights with the
                                    creator or agreement owner.
                                </p>
                            </SurfaceCard>
                        )}

                        {versions.length > 1 && (
                            <SurfaceCard padding="md">
                                <p className="mb-2 text-sm font-semibold">Versions</p>
                                <ul className="space-y-1">
                                    {versions.map((v) => (
                                        <li
                                            key={v.id}
                                            className="flex items-center justify-between text-sm"
                                        >
                                            <Link
                                                to="/ugc-review/$assetId"
                                                params={{ assetId: v.id }}
                                                className="flex-1 truncate hover:underline"
                                            >
                                                V{v.submissionVersion} — {v.title}
                                            </Link>
                                            <StatusChip tone={decisionMeta[v.decision].tone}>
                                                {decisionMeta[v.decision].label}
                                            </StatusChip>
                                        </li>
                                    ))}
                                </ul>
                            </SurfaceCard>
                        )}
                    </div>
                </div>
            </div>

            <RightsReadinessDrawer
                open={showRights}
                onOpenChange={setShowRights}
                rights={rights}
                onUpdate={(patch) => updateRights(assetId, patch)}
                onMarkReady={onMarkSpark}
                onCloseAutoFocus={(event) => {
                    event.preventDefault();
                    rightsTriggerRef.current?.focus();
                }}
            />
        </AppShell>
    );
}

function IssueGroup({
    title,
    issues,
    onJump,
    onToggle,
    onDismiss,
    onReview,
}: {
    title: string;
    issues: UgcIssue[];
    onJump: (s: number) => void;
    onToggle: (id: string) => void;
    onDismiss: (id: string) => void;
    onReview: (id: string) => void;
}) {
    return (
        <div>
            <p className="mb-1.5 text-xs uppercase tracking-wider text-text-tertiary">{title}</p>
            <ul className="space-y-1.5">
                {issues.map((i) => (
                    <li
                        key={i.id}
                        className={`rounded-md px-3 py-2 text-sm ${i.severity === "blocker" ? "bg-destructive-soft/50" : i.severity === "high" ? "bg-warn-soft/40" : "bg-surface-soft/60"}`}
                    >
                        <div className="flex items-start gap-2">
                            <div className="min-w-0 flex-1">
                                <span className="font-medium">{i.title}</span>
                            </div>
                            {i.reviewed && <StatusChip tone="ok">Reviewed</StatusChip>}
                            <Button
                                size="sm"
                                variant="ghost"
                                className="h-7 shrink-0 px-2 text-[11px]"
                                onClick={() => onJump(i.timestampSec)}
                            >
                                <ScanSearch className="h-3 w-3" />
                                {fmt(i.timestampSec)}
                            </Button>
                        </div>
                        <p className="mt-1 text-xs text-text-secondary">{i.why}</p>
                        {i.packRequirement && (
                            <p className="mt-1 text-xs text-text-tertiary">
                                Requirement: {i.packRequirement}
                            </p>
                        )}
                        <p className="mt-1 text-xs">
                            <b>Fix:</b> {i.fix}
                        </p>
                        <div className="mt-1.5 flex flex-wrap gap-1.5">
                            <Button
                                size="sm"
                                variant={i.addedToRevision ? "default" : "secondary"}
                                onClick={() => onToggle(i.id)}
                            >
                                {i.addedToRevision ? "In revision" : "Add to revision"}
                            </Button>
                            <Button size="sm" variant="ghost" onClick={() => onReview(i.id)}>
                                Mark reviewed
                            </Button>
                            <Button size="sm" variant="ghost" onClick={() => onDismiss(i.id)}>
                                Dismiss
                            </Button>
                        </div>
                    </li>
                ))}
            </ul>
        </div>
    );
}

function RevisionCompareSlider({
    before,
    after,
    beforeScore,
    afterScore,
}: {
    before: UgcAsset;
    after: UgcAsset;
    beforeScore?: number;
    afterScore?: number;
}) {
    const [split, setSplit] = useState(50);
    const scoreDelta =
        typeof beforeScore === "number" && typeof afterScore === "number"
            ? afterScore - beforeScore
            : undefined;

    return (
        <SurfaceCard padding="md" className="space-y-3">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <p className="text-sm font-semibold text-text-primary">Revision progress</p>
                    <p className="mt-0.5 text-xs text-text-tertiary">
                        Draft {before.submissionVersion} compared with draft{" "}
                        {after.submissionVersion}
                    </p>
                </div>
                {scoreDelta !== undefined && (
                    <StatusChip tone={scoreDelta >= 0 ? "ok" : "warn"}>
                        {scoreDelta >= 0 ? "+" : ""}
                        {scoreDelta} score
                    </StatusChip>
                )}
            </div>

            <div className="relative aspect-[4/3] overflow-hidden rounded-md bg-black">
                <DemoMediaTile
                    mediaUrl={before.mediaUrl}
                    mediaKind={before.mediaUrl ? "video" : undefined}
                    posterUrl={before.posterUrl}
                    seed={before.thumbSeed}
                    score={beforeScore}
                    aspect="4 / 3"
                    fit="contain"
                    showPlay={false}
                    className="absolute inset-0 rounded-none bg-black"
                />
                <div className="absolute inset-0" style={{ clipPath: `inset(0 0 0 ${split}%)` }}>
                    <DemoMediaTile
                        mediaUrl={after.mediaUrl}
                        mediaKind={after.mediaUrl ? "video" : undefined}
                        posterUrl={after.posterUrl}
                        seed={after.thumbSeed}
                        score={afterScore}
                        aspect="4 / 3"
                        fit="contain"
                        showPlay={false}
                        className="absolute inset-0 rounded-none bg-black"
                    />
                </div>
                <div
                    aria-hidden
                    className="pointer-events-none absolute inset-y-0 w-0.5 -translate-x-1/2 bg-white shadow-[0_0_0_1px_rgba(0,0,0,0.28)]"
                    style={{ left: `${split}%` }}
                >
                    <span className="absolute left-1/2 top-1/2 h-9 w-5 -translate-x-1/2 -translate-y-1/2 rounded-md border border-white/80 bg-black/65 shadow-md-card" />
                </div>
                <span className="pointer-events-none absolute left-3 top-3 rounded-md bg-black/60 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-white backdrop-blur-sm">
                    Draft {before.submissionVersion}
                </span>
                <span className="pointer-events-none absolute right-3 top-3 rounded-md bg-white/90 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-text-primary shadow-sm">
                    Draft {after.submissionVersion}
                </span>
            </div>

            <div className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3">
                <span className="text-xs font-medium text-text-secondary">
                    Draft {before.submissionVersion}
                </span>
                <Slider
                    min={12}
                    max={88}
                    step={1}
                    value={[split]}
                    onValueChange={(value) => setSplit(value[0] ?? 50)}
                    thumbLabel={`Compare draft ${before.submissionVersion} and draft ${after.submissionVersion}`}
                    className="cursor-ew-resize"
                />
                <span className="text-xs font-medium text-text-secondary">
                    Draft {after.submissionVersion}
                </span>
            </div>
        </SurfaceCard>
    );
}

function primaryUgcAction(decision: UgcDecision): string {
    switch (decision) {
        case "awaiting-analysis":
            return "Run analysis before approving or requesting changes.";
        case "processing":
            return "Wait for analysis to finish before making a publishing decision.";
        case "failed":
            return "Retry analysis or inspect the upload before requesting creator changes.";
        case "request-revision":
            return "Send the selected revision notes to the creator.";
        case "reject":
            return "Request a reshoot and keep this version out of paid launch.";
        case "organic-ready":
            return "Approve for organic use or review Spark readiness.";
        case "small-spark-test":
            return "Confirm Spark rights and start with a limited paid test.";
        case "spark-ready":
            return "This asset is ready for a Spark test.";
    }
}
