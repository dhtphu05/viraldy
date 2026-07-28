import { createFileRoute, Link, notFound, useNavigate } from "@tanstack/react-router";
import { useMemo, useState, useRef } from "react";
import { AppShell } from "@/widgets/app-shell/app-shell";
import { PageHeader } from "@/shared/ui/page-header";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { StatusChip } from "@/shared/ui/status-chip";
import { Button } from "@/shared/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/shared/ui/tabs";
import { Textarea } from "@/shared/ui/textarea";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
    DialogDescription,
} from "@/shared/ui/dialog";
import { Switch } from "@/shared/ui/switch";
import { Label } from "@/shared/ui/label";
import { Input } from "@/shared/ui/input";
import { EmptyState } from "@/shared/ui/empty-state";
import { useAppStore, useAllCampaigns } from "@/app/store/app-store";
import { seedCreators } from "@/features/ugc-review/mocks/creators";
import { generateRevisionMessage, sparkBlockers } from "@/features/ugc-review/lib/mockUgcAnalysis";
import {
    ArrowLeft,
    Copy,
    Play,
    Pause,
    ChevronLeft,
    ChevronRight,
    Sparkles,
    AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";
import type { UgcDecision, UgcIssue } from "@/features/ugc-review/types/ugc";

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
    const analysis = useAppStore((s) => s.ugcAnalyses[assetId]);
    const issues = useAppStore((s) => s.ugcIssues[assetId] ?? EMPTY_UGC_ISSUES);
    const rights = useAppStore((s) => s.ugcRights[assetId]);
    const ugcAssets = useAppStore((s) => s.ugcAssets);
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

    const [showRights, setShowRights] = useState(false);
    const [showBlockers, setShowBlockers] = useState<string[] | null>(null);
    const videoRef = useRef<HTMLVideoElement>(null);
    const [playing, setPlaying] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);

    if (!asset) throw notFound();

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

    const jumpTo = (sec: number) => {
        setCurrentTime(sec);
        if (videoRef.current) videoRef.current.currentTime = sec;
    };

    const onMarkSpark = () => {
        const r = markSparkReady(assetId);
        if (r.ok) toast.success("Marked Spark-ready");
        else setShowBlockers(r.blockers);
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
                    description={`${creator?.name ?? ""} · ${campaign?.name ?? "No campaign"} · v${asset.submissionVersion} · Submitted ${new Date(asset.submittedAt).toLocaleString()}`}
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

                <div className="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
                    {/* Left: video + evidence */}
                    <div className="flex min-w-0 flex-col gap-4">
                        <div className="relative overflow-hidden rounded-[22px] bg-[#0a0a0f] shadow-lg">
                            <div className="aspect-video">
                                {asset.mediaUrl ? (
                                    <video
                                        ref={videoRef}
                                        src={asset.mediaUrl}
                                        className="h-full w-full object-contain"
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

                        {/* Timeline markers */}
                        {analysis && analysis.markers.length > 0 && (
                            <SurfaceCard padding="sm">
                                <p className="mb-2 text-xs uppercase tracking-wider text-text-tertiary">
                                    Timeline
                                </p>
                                <div className="relative h-8 rounded-md bg-surface-soft">
                                    {analysis.markers.map((m) => (
                                        <button
                                            key={m.id}
                                            type="button"
                                            onClick={() => jumpTo(m.timestampSec)}
                                            className="absolute top-1 h-6 w-6 -translate-x-1/2 rounded-full ring-2 ring-background focus-visible:outline-none focus-visible:ring-primary"
                                            style={{
                                                left: `${Math.min(99, (m.timestampSec / Math.max(1, asset.durationSec)) * 100)}%`,
                                                background: markerColor(m.kind),
                                            }}
                                            aria-label={`${m.label} at ${fmt(m.timestampSec)}`}
                                            title={`${m.label} · ${fmt(m.timestampSec)}`}
                                        />
                                    ))}
                                </div>
                            </SurfaceCard>
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
                    <div className="flex min-w-0 flex-col gap-4 lg:sticky lg:top-20 lg:self-start">
                        <SurfaceCard padding="md">
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
                                <div className="mt-3 flex items-center gap-4 text-xs text-text-secondary">
                                    <span>
                                        <span className="text-text-tertiary">Score</span>{" "}
                                        <b className="text-text-primary">{analysis.score}</b>
                                    </span>
                                    <span>
                                        <span className="text-text-tertiary">Confidence</span>{" "}
                                        {analysis.confidence}
                                    </span>
                                </div>
                            )}
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
                                                    className={`h-1.5 rounded-full ${d.score >= 80 ? "bg-ok" : d.score >= 60 ? "bg-warn" : "bg-destructive"}`}
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
                                    {analysis.packAlignment.map((r, i) => (
                                        <li
                                            key={i}
                                            className="rounded-md bg-surface-soft/60 px-3 py-2"
                                        >
                                            <div className="flex items-center justify-between gap-2">
                                                <span className="font-medium">{r.requirement}</span>
                                                <StatusChip
                                                    tone={
                                                        r.status === "Complete"
                                                            ? "ok"
                                                            : r.status === "Missing"
                                                              ? "destructive"
                                                              : "warn"
                                                    }
                                                >
                                                    {r.status}
                                                </StatusChip>
                                            </div>
                                            <p className="mt-0.5 text-xs text-text-secondary">
                                                Detected: {r.detected}
                                            </p>
                                        </li>
                                    ))}
                                </ul>
                            </SurfaceCard>
                        )}

                        {rights && (
                            <SurfaceCard padding="md">
                                <div className="mb-2 flex items-center justify-between">
                                    <p className="text-sm font-semibold">Rights & Spark</p>
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        onClick={() => setShowRights(true)}
                                    >
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

            {/* Rights dialog */}
            <Dialog open={showRights} onOpenChange={setShowRights}>
                <DialogContent className="max-w-md">
                    <DialogHeader>
                        <DialogTitle>Rights & Spark readiness</DialogTitle>
                        <DialogDescription>
                            Track operational readiness. Confirm final rights with the creator or
                            agreement owner.
                        </DialogDescription>
                    </DialogHeader>
                    {rights && (
                        <div className="space-y-3">
                            <ToggleRow
                                label="Organic usage allowed"
                                value={rights.organic}
                                onChange={(v) => updateRights(assetId, { organic: v })}
                            />
                            <ToggleRow
                                label="Spark Ads allowed"
                                value={rights.sparkAllowed}
                                onChange={(v) => updateRights(assetId, { sparkAllowed: v })}
                            />
                            <ToggleRow
                                label="Meta Ads allowed"
                                value={rights.metaAllowed}
                                onChange={(v) => updateRights(assetId, { metaAllowed: v })}
                            />
                            <ToggleRow
                                label="Website use allowed"
                                value={rights.websiteAllowed}
                                onChange={(v) => updateRights(assetId, { websiteAllowed: v })}
                            />
                            <ToggleRow
                                label="Editing allowed"
                                value={rights.editingAllowed}
                                onChange={(v) => updateRights(assetId, { editingAllowed: v })}
                            />
                            <ToggleRow
                                label="Raw footage included"
                                value={rights.rawFootage}
                                onChange={(v) => updateRights(assetId, { rawFootage: v })}
                            />
                            <ToggleRow
                                label="Creator has confirmed"
                                value={rights.creatorConfirmed}
                                onChange={(v) => updateRights(assetId, { creatorConfirmed: v })}
                            />
                            <div>
                                <Label>Usage duration (days)</Label>
                                <Input
                                    type="number"
                                    value={rights.durationDays ?? ""}
                                    onChange={(e) =>
                                        updateRights(assetId, {
                                            durationDays: e.target.value
                                                ? Number(e.target.value)
                                                : undefined,
                                        })
                                    }
                                />
                            </div>
                            <div>
                                <Label>Spark code</Label>
                                <Input
                                    value={rights.sparkCode ?? ""}
                                    onChange={(e) =>
                                        updateRights(assetId, {
                                            sparkCode: e.target.value || undefined,
                                        })
                                    }
                                />
                            </div>
                        </div>
                    )}
                    <DialogFooter>
                        <Button onClick={() => setShowRights(false)}>Done</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Blockers dialog */}
            <Dialog open={!!showBlockers} onOpenChange={(v) => !v && setShowBlockers(null)}>
                <DialogContent className="max-w-md">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <AlertTriangle className="h-4 w-4 text-warn" /> Not Spark-ready yet
                        </DialogTitle>
                        <DialogDescription>
                            This asset is missing information required before running a Spark test.
                        </DialogDescription>
                    </DialogHeader>
                    <ul className="list-disc space-y-1 pl-5 text-sm">
                        {(showBlockers ?? []).map((b) => (
                            <li key={b}>{b}</li>
                        ))}
                    </ul>
                    <DialogFooter>
                        <Button variant="ghost" onClick={() => setShowBlockers(null)}>
                            Keep organic-ready
                        </Button>
                        <Button
                            onClick={() => {
                                setShowBlockers(null);
                                setShowRights(true);
                            }}
                        >
                            Review rights
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </AppShell>
    );
}

function ToggleRow({
    label,
    value,
    onChange,
}: {
    label: string;
    value: boolean;
    onChange: (v: boolean) => void;
}) {
    return (
        <div className="flex items-center justify-between rounded-md bg-surface-soft/50 px-3 py-2 text-sm">
            <span>{label}</span>
            <Switch checked={value} onCheckedChange={onChange} />
        </div>
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
                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => onJump(i.timestampSec)}
                                className="font-mono text-xs text-text-tertiary hover:text-text-primary focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                            >
                                {fmt(i.timestampSec)}
                            </button>
                            <span className="font-medium">{i.title}</span>
                            {i.reviewed && <StatusChip tone="ok">Reviewed</StatusChip>}
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

function markerColor(kind: string): string {
    switch (kind) {
        case "hook":
            return "#ff385c";
        case "reveal":
            return "#2566eb";
        case "demo":
            return "#0c8a4a";
        case "proof":
            return "#0c8a4a";
        case "offer":
            return "#c2730a";
        case "cta":
            return "#2566eb";
        case "risk":
            return "#d92d20";
        case "missing":
            return "#d92d20";
        default:
            return "#8888aa";
    }
}
