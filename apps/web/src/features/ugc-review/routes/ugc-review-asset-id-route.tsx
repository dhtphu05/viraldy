import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { useEffect, useMemo, useState, useRef } from "react";
import { AppShell } from "@/widgets/app-shell/app-shell";
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
import { DemoMediaTile } from "@/shared/ui/demo-media-tile";
import { DecisionHero } from "@/shared/ui/decision-hero";
import {
    EvidenceTimeline,
    type EvidenceMarkerKind,
    type EvidenceTimelineMarker,
} from "@/shared/ui/evidence-timeline";
import { ExpectedObservedTable } from "@/shared/ui/expected-observed-table";
import { ValueReceipt } from "@/shared/ui/value-receipt";
import { ConfidenceBadge } from "@/shared/ui/confidence-badge";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/shared/ui/alert-dialog";
import { cn } from "@/shared/lib/utils";
import { scrollElementIntoView } from "@/shared/lib/scroll";
import { useAppStore, useAllCampaigns } from "@/app/store/app-store";
import { seedCreators } from "@/features/ugc-review/mocks/creators";
import {
    generateRevisionMessage,
    sparkBlockers,
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
    Check,
    Circle,
    Sparkles,
    ScanSearch,
    Save,
} from "lucide-react";
import { toast } from "sonner";
import type {
    UgcAsset,
    UgcDecision,
    UgcIssue,
    UgcRights,
    UgcTimelineKind,
    UgcTimelineMarker,
} from "@/features/ugc-review/types/ugc";

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
                        <Link
                            to="/ugc-review"
                            search={{ campaignId: undefined, upload: undefined }}
                        >
                            Back to UGC Review
                        </Link>
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
const EMPTY_RIGHTS: UgcRights = {
    organic: false,
    sparkAllowed: false,
    metaAllowed: false,
    websiteAllowed: false,
    rawFootage: false,
    editingAllowed: false,
    creatorConfirmed: false,
};

const decisionActionLabel: Record<UgcDecision, string> = {
    "awaiting-analysis": "Analyze UGC",
    processing: "Analysis in progress",
    failed: "Retry analysis",
    "request-revision": "Create revision message",
    reject: "Prepare reshoot request",
    "organic-ready": "Approve organic",
    "small-spark-test": "Review paid readiness",
    "spark-ready": "Open rights / launch preparation",
};

function evidenceKind(kind: UgcTimelineKind): EvidenceMarkerKind {
    return kind === "reveal" ? "product" : kind;
}

function alignmentStatus(status: string) {
    if (status === "Complete") return "Met";
    if (status === "Needs revision") return "Partial";
    return status;
}

function alignmentIssue(requirement: string, issues: UgcIssue[]) {
    const normalized = requirement.toLowerCase();
    return issues.find((issue) => {
        const issueRequirement = issue.packRequirement?.toLowerCase();
        return (
            issueRequirement &&
            (issueRequirement.includes(normalized) || normalized.includes(issueRequirement))
        );
    });
}

function evidenceMarkerForIssue(issue: UgcIssue, markers: UgcTimelineMarker[]) {
    const exact = markers.find((marker) => marker.issueId === issue.id);
    if (exact) return exact;

    const nearest = markers.reduce<UgcTimelineMarker | undefined>((closest, marker) => {
        if (!closest) return marker;
        return Math.abs(marker.timestampSec - issue.timestampSec) <
            Math.abs(closest.timestampSec - issue.timestampSec)
            ? marker
            : closest;
    }, undefined);
    return nearest && Math.abs(nearest.timestampSec - issue.timestampSec) <= 2
        ? nearest
        : undefined;
}

function UgcDetail() {
    const { assetId } = Route.useParams();
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
    const [activeMarkerId, setActiveMarkerId] = useState<string | null>(null);
    const [activeIssueId, setActiveIssueId] = useState<string | null>(null);
    const [evidenceTime, setEvidenceTime] = useState<number | null>(null);
    const [receipt, setReceipt] = useState<"revision" | "reshoot" | "organic" | "spark" | null>(
        null,
    );
    const [reshootConfirmOpen, setReshootConfirmOpen] = useState(false);
    const revisionSectionRef = useRef<HTMLDivElement>(null);

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
    const mustFix = [...blockers, ...highs];
    const resolvedRights = rights ?? EMPTY_RIGHTS;
    const paidUseBlockers = sparkBlockers(resolvedRights);

    const selectedIssues = issues.filter((i) => i.addedToRevision);
    const revisionMessage =
        asset.revisionMessage !== undefined
            ? asset.revisionMessage
            : generateRevisionMessage(
                  creator?.name.split(" ")[0] ?? "",
                  positives.slice(0, 2).map((positive) => positive.title + "."),
                  selectedIssues.map((issue) => issue.fix),
              );

    const openRights = () => {
        rightsTriggerRef.current =
            document.activeElement instanceof HTMLElement ? document.activeElement : null;
        setShowRights(true);
    };

    const jumpTo = (
        sec: number,
        selection?: { markerId?: string | null; issueId?: string | null },
    ) => {
        setCurrentTime(sec);
        setEvidenceTime(sec);
        if (selection?.markerId !== undefined) setActiveMarkerId(selection.markerId);
        if (selection?.issueId !== undefined) setActiveIssueId(selection.issueId);
        if (videoRef.current) {
            videoRef.current.currentTime = sec;
            scrollElementIntoView(videoRef.current, { block: "center" });
        }
    };

    const onMarkSpark = () => {
        const r = markSparkReady(assetId);
        if (r.ok) {
            setShowRights(false);
            setReceipt("spark");
            toast.success("Marked Spark-ready");
            return true;
        }
        openRights();
        return false;
    };

    const approveForOrganic = () => {
        approveOrganic(assetId);
        setReceipt("organic");
        toast.success("Approved for organic publishing");
    };

    const focusRevisionMessage = () => {
        scrollElementIntoView(revisionSectionRef.current, { block: "center" });
        window.setTimeout(
            () => revisionSectionRef.current?.querySelector("textarea")?.focus(),
            250,
        );
    };

    const sendRevisionRequest = () => {
        setRevisionMessage(assetId, revisionMessage);
        markRevisionRequested(assetId);
        setReceipt("revision");
        toast.success("Revision marked as requested");
    };

    const confirmReshootRequest = () => {
        setRevisionMessage(assetId, revisionMessage);
        rejectUgc(assetId);
        setReceipt("reshoot");
        setReshootConfirmOpen(false);
        toast.success("Reshoot request recorded");
    };

    const evidenceMarkers: EvidenceTimelineMarker[] =
        analysis?.markers.map((marker) => {
            const issue = issues.find((candidate) => candidate.id === marker.issueId);
            return {
                id: marker.id,
                at: marker.timestampSec,
                label: marker.label,
                kind: evidenceKind(marker.kind),
                preview: issue ? (
                    <div>
                        <p className="text-sm font-medium text-text-primary">{issue.title}</p>
                        <p className="mt-1 text-xs text-text-secondary">{issue.why}</p>
                    </div>
                ) : undefined,
            };
        }) ?? [];

    const primaryAction = (() => {
        switch (asset.decision) {
            case "awaiting-analysis":
                return (
                    <Button onClick={() => startAnalysis(assetId, ugcProcessingSteps.length)}>
                        <Sparkles aria-hidden />
                        Analyze UGC
                    </Button>
                );
            case "processing":
                return undefined;
            case "failed":
                return <Button onClick={() => retryUgcAnalysis(assetId)}>Retry analysis</Button>;
            case "request-revision":
                return <Button onClick={focusRevisionMessage}>Create revision message</Button>;
            case "reject":
                return (
                    <Button variant="destructive" onClick={focusRevisionMessage}>
                        Prepare reshoot request
                    </Button>
                );
            case "organic-ready":
                return <Button onClick={approveForOrganic}>Approve organic</Button>;
            case "small-spark-test":
                return <Button onClick={openRights}>Review paid readiness</Button>;
            case "spark-ready":
                return <Button onClick={openRights}>Open rights / launch preparation</Button>;
        }
    })();

    return (
        <AppShell>
            <div className="flex flex-col gap-6">
                <div>
                    <Link
                        to="/ugc-review"
                        search={{ campaignId: undefined, upload: undefined }}
                        className="inline-flex items-center gap-1 text-xs text-text-tertiary hover:text-text-primary"
                    >
                        <ArrowLeft className="h-3 w-3" /> UGC Review
                    </Link>
                </div>
                <header className="min-w-0">
                    <h1 className="break-words text-2xl font-semibold text-text-primary sm:text-[28px]">
                        {asset.title}
                    </h1>
                    <p className="mt-1 break-words text-sm text-text-secondary">
                        {creator?.name ?? "Unknown creator"} · {campaign?.name ?? "No campaign"} · v
                        {asset.submissionVersion} · Submitted {formatUtcDateTime(asset.submittedAt)}
                    </p>
                </header>

                <DecisionHero
                    key={asset.decision}
                    actionLabel={decisionActionLabel[asset.decision]}
                    reason={analysis?.reason ?? primaryUgcAction(asset.decision)}
                    score={analysis?.score}
                    confidence={analysis?.confidence}
                    blockerCount={analysis ? mustFix.length : undefined}
                    statusTone={meta.tone}
                    primaryAction={primaryAction}
                    secondaryAction={
                        asset.decision !== "reject" &&
                        asset.decision !== "processing" &&
                        asset.decision !== "awaiting-analysis" ? (
                            <Button variant="ghost" onClick={() => setReshootConfirmOpen(true)}>
                                Request reshoot
                            </Button>
                        ) : undefined
                    }
                />

                {receipt === "organic" && (
                    <ValueReceipt
                        title="Organic approval recorded"
                        description="The asset is approved for organic publishing. Paid usage still follows the rights checklist."
                        items={["Approval saved", "Review activity updated"]}
                    />
                )}
                {receipt === "spark" && (
                    <ValueReceipt
                        title="Spark readiness recorded"
                        description="Paid-use blockers are resolved and the asset is marked Spark-ready."
                        items={["Rights checked", "Spark status saved"]}
                    />
                )}
                {receipt === "reshoot" && (
                    <ValueReceipt
                        title="Reshoot request recorded"
                        description="This draft is held from launch and the creator message is saved with the asset."
                        items={[
                            `${selectedIssues.length} findings included`,
                            "Creator response pending",
                        ]}
                    />
                )}

                <div className="grid gap-6 xl:grid-cols-12">
                    {/* Left: video + evidence */}
                    <div className="flex min-w-0 flex-col gap-4 xl:col-span-8">
                        <div
                            className={`relative overflow-hidden rounded-md bg-black shadow-lg ${verticalMedia ? "mx-auto w-full max-w-[420px]" : ""}`}
                        >
                            <div className="pointer-events-none absolute left-3 top-3 z-10 flex flex-wrap items-center gap-1.5">
                                <span className="rounded-md bg-black/60 px-2 py-0.5 text-[11px] font-medium text-white">
                                    {asset.mediaAspectRatio ?? "16:9"}
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
                                        aria-label={`${asset.title} review video`}
                                        onTimeUpdate={(e) =>
                                            setCurrentTime(e.currentTarget.currentTime)
                                        }
                                        onPlay={() => setPlaying(true)}
                                        onPause={() => setPlaying(false)}
                                    />
                                ) : asset.posterUrl ? (
                                    <img
                                        src={asset.posterUrl}
                                        alt={`${asset.title} preview frame`}
                                        className="h-full w-full object-contain"
                                    />
                                ) : (
                                    <div
                                        className="grid h-full w-full place-items-center bg-surface-muted text-sm text-text-tertiary"
                                        role="img"
                                        aria-label="No video preview is available"
                                    >
                                        No preview frame
                                    </div>
                                )}
                            </div>
                            <div className="flex items-center gap-1 bg-black/40 px-2 py-1.5 text-white">
                                <button
                                    type="button"
                                    aria-label="Back 5s"
                                    onClick={() => jumpTo(Math.max(0, currentTime - 5))}
                                    disabled={!asset.mediaUrl}
                                    className="grid h-10 w-10 place-items-center rounded-md hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white disabled:pointer-events-none disabled:opacity-40"
                                >
                                    <ChevronLeft className="h-4 w-4" />
                                </button>
                                <button
                                    type="button"
                                    aria-label={playing ? "Pause" : "Play"}
                                    disabled={!asset.mediaUrl}
                                    onClick={() => {
                                        if (!videoRef.current) return;
                                        if (playing) {
                                            videoRef.current.pause();
                                        } else {
                                            void videoRef.current.play();
                                        }
                                    }}
                                    className="grid h-10 w-10 place-items-center rounded-md hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white disabled:pointer-events-none disabled:opacity-40"
                                >
                                    {playing ? (
                                        <Pause className="h-4 w-4" />
                                    ) : (
                                        <Play className="h-4 w-4" />
                                    )}
                                </button>
                                <button
                                    type="button"
                                    aria-label="Forward 5s"
                                    disabled={!asset.mediaUrl}
                                    onClick={() =>
                                        jumpTo(Math.min(asset.durationSec, currentTime + 5))
                                    }
                                    className="grid h-10 w-10 place-items-center rounded-md hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white disabled:pointer-events-none disabled:opacity-40"
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

                        {evidenceMarkers.length > 0 && (
                            <EvidenceTimeline
                                duration={asset.durationSec}
                                currentTime={currentTime}
                                markers={evidenceMarkers}
                                activeId={activeMarkerId}
                                onSeek={(time, marker) => {
                                    const sourceMarker = analysis?.markers.find(
                                        (candidate) => candidate.id === marker.id,
                                    );
                                    jumpTo(time, {
                                        markerId: marker.id,
                                        issueId: sourceMarker?.issueId ?? null,
                                    });
                                }}
                                className="rounded-md"
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
                                                type="button"
                                                onClick={() =>
                                                    jumpTo(t.startSec, {
                                                        markerId: null,
                                                        issueId: null,
                                                    })
                                                }
                                                className={cn(
                                                    "block min-h-10 w-full rounded-md px-2 py-2 text-left text-sm hover:bg-surface-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                                                    evidenceTime !== null &&
                                                        evidenceTime >= t.startSec &&
                                                        evidenceTime <= t.endSec &&
                                                        "bg-primary-softer ring-1 ring-primary/30",
                                                )}
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
                                            <button
                                                key={s.id}
                                                type="button"
                                                onClick={() =>
                                                    jumpTo(s.startSec, {
                                                        markerId: null,
                                                        issueId: null,
                                                    })
                                                }
                                                className={cn(
                                                    "w-full rounded-md bg-surface-soft/60 px-3 py-2 text-left text-sm hover:bg-surface-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                                                    evidenceTime !== null &&
                                                        evidenceTime >= s.startSec &&
                                                        evidenceTime <= s.endSec &&
                                                        "bg-primary-softer ring-1 ring-primary/30",
                                                )}
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
                                            </button>
                                        ))}
                                    </TabsContent>
                                    <TabsContent value="onscreen" className="mt-3 space-y-1.5">
                                        {analysis.onScreenText.length === 0 && (
                                            <p className="text-sm text-text-secondary">
                                                No on-screen text detected.
                                            </p>
                                        )}
                                        {analysis.onScreenText.map((o) => (
                                            <button
                                                key={o.id}
                                                type="button"
                                                onClick={() =>
                                                    jumpTo(o.timestampSec, {
                                                        markerId: null,
                                                        issueId: null,
                                                    })
                                                }
                                                className={cn(
                                                    "flex min-h-10 w-full items-center gap-3 rounded-md bg-surface-soft/60 px-3 py-2 text-left text-sm hover:bg-surface-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                                                    evidenceTime === o.timestampSec &&
                                                        "bg-primary-softer ring-1 ring-primary/30",
                                                )}
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
                                            </button>
                                        ))}
                                    </TabsContent>
                                </Tabs>
                            </SurfaceCard>
                        )}
                    </div>

                    <div className="flex min-w-0 flex-col gap-4 xl:col-span-4">
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

                        {issues.some((issue) => !issue.dismissed) && (
                            <SurfaceCard padding="md" className="space-y-4">
                                <div>
                                    <p className="text-sm font-semibold text-text-primary">
                                        Findings
                                    </p>
                                    <p className="mt-0.5 text-xs text-text-tertiary">
                                        Select evidence to seek the video and related transcript or
                                        scene.
                                    </p>
                                </div>
                                {mustFix.length > 0 && (
                                    <IssueGroup
                                        title="Must fix"
                                        issues={mustFix}
                                        activeIssueId={activeIssueId}
                                        onJump={(issue) => {
                                            const marker = evidenceMarkerForIssue(
                                                issue,
                                                analysis?.markers ?? [],
                                            );
                                            jumpTo(issue.timestampSec, {
                                                markerId: marker?.id ?? null,
                                                issueId: issue.id,
                                            });
                                        }}
                                        onToggle={(id) => toggleIssue(assetId, id)}
                                        onDismiss={(id) => dismissIssue(assetId, id, true)}
                                        onReview={(id) => reviewIssue(assetId, id)}
                                    />
                                )}
                                {improvements.length > 0 && (
                                    <IssueGroup
                                        title="Should improve"
                                        issues={improvements}
                                        activeIssueId={activeIssueId}
                                        onJump={(issue) => {
                                            const marker = evidenceMarkerForIssue(
                                                issue,
                                                analysis?.markers ?? [],
                                            );
                                            jumpTo(issue.timestampSec, {
                                                markerId: marker?.id ?? null,
                                                issueId: issue.id,
                                            });
                                        }}
                                        onToggle={(id) => toggleIssue(assetId, id)}
                                        onDismiss={(id) => dismissIssue(assetId, id, true)}
                                        onReview={(id) => reviewIssue(assetId, id)}
                                    />
                                )}
                                {positives.length > 0 && (
                                    <IssueGroup
                                        title="Strengths"
                                        issues={positives}
                                        activeIssueId={activeIssueId}
                                        onJump={(issue) => {
                                            const marker = evidenceMarkerForIssue(
                                                issue,
                                                analysis?.markers ?? [],
                                            );
                                            jumpTo(issue.timestampSec, {
                                                markerId: marker?.id ?? null,
                                                issueId: issue.id,
                                            });
                                        }}
                                        onToggle={(id) => toggleIssue(assetId, id)}
                                        onDismiss={(id) => dismissIssue(assetId, id, true)}
                                        onReview={(id) => reviewIssue(assetId, id)}
                                    />
                                )}
                            </SurfaceCard>
                        )}

                        {(asset.decision === "request-revision" ||
                            asset.decision === "reject" ||
                            selectedIssues.length > 0) && (
                            <div ref={revisionSectionRef}>
                                <SurfaceCard padding="md" className="space-y-3">
                                    <div className="flex flex-wrap items-start justify-between gap-2">
                                        <div>
                                            <p className="text-sm font-semibold text-text-primary">
                                                Creator revision message
                                            </p>
                                            <p className="mt-0.5 text-xs text-text-tertiary">
                                                {selectedIssues.length} included issue
                                                {selectedIssues.length === 1 ? "" : "s"}
                                            </p>
                                        </div>
                                        <StatusChip
                                            tone={selectedIssues.length > 0 ? "warn" : "neutral"}
                                        >
                                            {selectedIssues.length} included
                                        </StatusChip>
                                    </div>
                                    <Textarea
                                        aria-label="Creator revision message"
                                        value={revisionMessage}
                                        onChange={(event) => {
                                            setRevisionMessage(assetId, event.target.value);
                                            setReceipt(null);
                                        }}
                                        rows={8}
                                    />
                                    <div className="flex flex-wrap gap-2">
                                        <Button
                                            size="sm"
                                            variant="secondary"
                                            onClick={() => {
                                                void navigator.clipboard?.writeText(
                                                    revisionMessage,
                                                );
                                                toast.success("Copied to clipboard");
                                            }}
                                        >
                                            <Copy aria-hidden />
                                            Copy
                                        </Button>
                                        <Button
                                            size="sm"
                                            variant="secondary"
                                            onClick={() => {
                                                setRevisionMessage(assetId, revisionMessage);
                                                toast.success("Revision message saved");
                                            }}
                                        >
                                            <Save aria-hidden />
                                            Save
                                        </Button>
                                        <Button
                                            size="sm"
                                            onClick={
                                                asset.decision === "reject"
                                                    ? () => setReshootConfirmOpen(true)
                                                    : sendRevisionRequest
                                            }
                                        >
                                            {asset.decision === "reject"
                                                ? "Review reshoot request"
                                                : "Mark revision requested"}
                                        </Button>
                                    </div>
                                    {receipt === "revision" && (
                                        <ValueReceipt
                                            title="Revision request recorded"
                                            description="The selected findings and message are saved with this asset."
                                            items={[
                                                `${selectedIssues.length} findings included`,
                                                "Review activity updated",
                                            ]}
                                            className="p-4"
                                        />
                                    )}
                                </SurfaceCard>
                            </div>
                        )}

                        <RightsSummary
                            rights={resolvedRights}
                            paidUseBlockers={paidUseBlockers}
                            onEdit={openRights}
                        />

                        {versions.length > 1 && (
                            <SurfaceCard padding="md">
                                <p className="mb-2 text-sm font-semibold">Versions</p>
                                <ul className="space-y-1">
                                    {versions.map((v) => (
                                        <li
                                            key={v.id}
                                            className="flex flex-col items-start gap-2 border-b border-hairline py-2 text-sm last:border-0"
                                        >
                                            <Link
                                                to="/ugc-review/$assetId"
                                                params={{ assetId: v.id }}
                                                className="break-words text-text-primary hover:underline"
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

                {analysis && analysis.packAlignment.length > 0 && (
                    <SurfaceCard variant="outlined" padding="md">
                        <div className="mb-4">
                            <h2 className="text-sm font-semibold text-text-primary">
                                Expected vs Observed
                            </h2>
                            <p className="mt-0.5 text-xs text-text-tertiary">
                                Campaign Pack requirements compared with evidence detected in this
                                version.
                            </p>
                        </div>
                        <ExpectedObservedTable
                            rows={analysis.packAlignment.map((row, index) => {
                                const linkedIssue = alignmentIssue(row.requirement, issues);
                                return {
                                    id: `${index}-${row.requirement}`,
                                    requirement: row.requirement,
                                    observed: row.detected,
                                    status: alignmentStatus(row.status),
                                    evidence: row.evidence ? <p>{row.evidence}</p> : undefined,
                                    action:
                                        row.action || linkedIssue ? (
                                            <div className="mt-2 space-y-2">
                                                {row.action && (
                                                    <p className="text-xs">
                                                        <span className="font-medium text-text-primary">
                                                            Action:
                                                        </span>{" "}
                                                        {row.action}
                                                    </p>
                                                )}
                                                {linkedIssue && (
                                                    <Button
                                                        size="sm"
                                                        variant="ghost"
                                                        onClick={() => {
                                                            const marker = evidenceMarkerForIssue(
                                                                linkedIssue,
                                                                analysis.markers,
                                                            );
                                                            jumpTo(linkedIssue.timestampSec, {
                                                                markerId: marker?.id ?? null,
                                                                issueId: linkedIssue.id,
                                                            });
                                                        }}
                                                    >
                                                        <ScanSearch aria-hidden />
                                                        Evidence at {fmt(linkedIssue.timestampSec)}
                                                    </Button>
                                                )}
                                            </div>
                                        ) : undefined,
                                };
                            })}
                        />
                    </SurfaceCard>
                )}

                {previousVersion && analysis && (
                    <RevisionCompareSlider
                        before={previousVersion}
                        after={asset}
                        beforeScore={analyses[previousVersion.id]?.score}
                        afterScore={analysis.score}
                    />
                )}
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
            <AlertDialog open={reshootConfirmOpen} onOpenChange={setReshootConfirmOpen}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Request a full reshoot?</AlertDialogTitle>
                        <AlertDialogDescription>
                            This keeps the current draft out of launch and records the edited
                            creator message. The media and analysis remain available for evidence.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <div className="max-h-48 overflow-y-auto rounded-md bg-surface-soft p-3 text-sm text-text-secondary">
                        {revisionMessage}
                    </div>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Keep reviewing</AlertDialogCancel>
                        <AlertDialogAction onClick={confirmReshootRequest}>
                            Confirm reshoot request
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </AppShell>
    );
}

function IssueGroup({
    title,
    issues,
    activeIssueId,
    onJump,
    onToggle,
    onDismiss,
    onReview,
}: {
    title: string;
    issues: UgcIssue[];
    activeIssueId: string | null;
    onJump: (issue: UgcIssue) => void;
    onToggle: (id: string) => void;
    onDismiss: (id: string) => void;
    onReview: (id: string) => void;
}) {
    return (
        <div>
            <p className="mb-1.5 text-xs uppercase text-text-tertiary">{title}</p>
            <ul className="space-y-1.5">
                {issues.map((i) => (
                    <li
                        key={i.id}
                        className={cn(
                            "rounded-md px-3 py-3 text-sm",
                            i.severity === "blocker"
                                ? "bg-destructive-soft/50"
                                : i.severity === "high"
                                  ? "bg-warn-soft/40"
                                  : i.severity === "positive"
                                    ? "bg-ok-soft/40"
                                    : "bg-surface-soft/60",
                            activeIssueId === i.id && "ring-2 ring-primary",
                        )}
                    >
                        <div className="flex flex-wrap items-start gap-2">
                            <div className="min-w-32 flex-1">
                                <p className="font-medium text-text-primary">{i.title}</p>
                            </div>
                            {i.reviewed && <StatusChip tone="ok">Reviewed</StatusChip>}
                            <Button
                                size="sm"
                                variant="ghost"
                                className="shrink-0 px-2 text-[11px]"
                                onClick={() => onJump(i)}
                            >
                                <ScanSearch aria-hidden />
                                {fmt(i.timestampSec)}
                            </Button>
                        </div>
                        <p className="mt-1 text-xs text-text-secondary">{i.why}</p>
                        {i.packRequirement && (
                            <p className="mt-1 text-xs text-text-tertiary">
                                <span className="font-medium text-text-secondary">
                                    Campaign Pack:
                                </span>{" "}
                                {i.packRequirement}
                            </p>
                        )}
                        <p className="mt-2 text-xs text-text-secondary">
                            <span className="font-medium text-text-primary">Fix:</span> {i.fix}
                        </p>
                        <div className="mt-2 flex flex-wrap items-center gap-1.5">
                            <ConfidenceBadge level={i.confidence} rationale={i.why} />
                            <Button
                                size="sm"
                                variant={i.addedToRevision ? "default" : "secondary"}
                                onClick={() => onToggle(i.id)}
                            >
                                {i.addedToRevision && <Check aria-hidden />}
                                {i.addedToRevision ? "Remove from revision" : "Add to revision"}
                            </Button>
                            <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => onReview(i.id)}
                                disabled={i.reviewed}
                            >
                                {i.reviewed ? "Reviewed" : "Mark reviewed"}
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

function RightsSummary({
    rights,
    paidUseBlockers,
    onEdit,
}: {
    rights: UgcRights;
    paidUseBlockers: string[];
    onEdit: () => void;
}) {
    const checklist = [
        { label: "Organic", complete: rights.organic },
        { label: "Spark allowed", complete: rights.sparkAllowed },
        { label: "Meta allowed", complete: rights.metaAllowed },
        { label: "Website allowed", complete: rights.websiteAllowed },
        { label: "Raw footage", complete: rights.rawFootage },
        { label: "Editing allowed", complete: rights.editingAllowed },
        { label: "Creator confirmed", complete: rights.creatorConfirmed },
        {
            label: "Expiry",
            complete: Boolean(rights.sparkExpiry),
            detail: rights.sparkExpiry ? formatUtcDateTime(rights.sparkExpiry) : undefined,
        },
    ];
    const status =
        paidUseBlockers.length === 0
            ? "READY FOR SPARK"
            : rights.organic && !rights.sparkAllowed
              ? "ORGANIC ONLY"
              : `${paidUseBlockers.length} PAID-USE BLOCKER${paidUseBlockers.length === 1 ? "" : "S"}`;

    return (
        <SurfaceCard padding="md">
            <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                    <p className="text-sm font-semibold text-text-primary">Rights readiness</p>
                    <StatusChip
                        tone={
                            paidUseBlockers.length === 0 ? "ok" : rights.organic ? "info" : "warn"
                        }
                        className="mt-2"
                    >
                        {status}
                    </StatusChip>
                </div>
                <Button size="sm" variant="secondary" onClick={onEdit}>
                    Review rights
                </Button>
            </div>
            <ul className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-1">
                {checklist.map((item) => (
                    <li
                        key={item.label}
                        className="flex min-w-0 items-start gap-2 text-xs text-text-secondary"
                    >
                        {item.complete ? (
                            <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ok" aria-hidden />
                        ) : (
                            <Circle
                                className="mt-0.5 h-3.5 w-3.5 shrink-0 text-text-tertiary"
                                aria-hidden
                            />
                        )}
                        <span className="min-w-0 break-words">
                            <span className="font-medium text-text-primary">{item.label}</span>
                            {item.detail ? ` · ${item.detail}` : ""}
                            <span className="sr-only">
                                {item.complete ? " complete" : " incomplete"}
                            </span>
                        </span>
                    </li>
                ))}
            </ul>
            {paidUseBlockers.length > 0 && (
                <div className="mt-4 border-t border-hairline pt-3">
                    <p className="text-xs font-medium text-text-primary">Paid-use blockers</p>
                    <ul className="mt-1 space-y-1 text-xs text-text-secondary">
                        {paidUseBlockers.map((blocker) => (
                            <li key={blocker}>· {blocker}</li>
                        ))}
                    </ul>
                </div>
            )}
            <p className="mt-3 text-[11px] text-text-tertiary">
                Confirm final rights with the creator or agreement owner.
            </p>
        </SurfaceCard>
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
                    className="pointer-events-none absolute inset-y-0 w-0.5 -translate-x-1/2 bg-white shadow-sm"
                    style={{ left: `${split}%` }}
                >
                    <span className="absolute left-1/2 top-1/2 h-9 w-5 -translate-x-1/2 -translate-y-1/2 rounded-md border border-white/80 bg-black/65 shadow-md-card" />
                </div>
                <span className="pointer-events-none absolute left-3 top-3 rounded-md bg-black/60 px-2 py-1 text-[10px] font-semibold uppercase text-white">
                    Draft {before.submissionVersion}
                </span>
                <span className="pointer-events-none absolute right-3 top-3 rounded-md bg-white/90 px-2 py-1 text-[10px] font-semibold uppercase text-text-primary shadow-sm">
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
