import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { AppShell } from "@/widgets/app-shell/app-shell";
import { PageHeader } from "@/shared/ui/page-header";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { formatUtcDate } from "@/shared/lib/date-format";
import { StatusChip } from "@/shared/ui/status-chip";
import { EmptyState } from "@/shared/ui/empty-state";
import { DemoMediaTile } from "@/shared/ui/demo-media-tile";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
    DialogDescription,
} from "@/shared/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/shared/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import { Label } from "@/shared/ui/label";
import { useAppStore, useAllCampaigns } from "@/app/store/app-store";
import { seedCreators } from "@/features/ugc-review/mocks/creators";
import { demoUploadAssets } from "@/features/ugc-review/mocks/ugcSeed";
import { ugcProcessingSteps } from "@/features/ugc-review/lib/mockUgcAnalysis";
import { Upload, Video, Play, ChevronRight, Sparkles } from "lucide-react";
import { toast } from "sonner";
import type { UgcAsset, UgcDecision, UgcReviewObjective } from "@/features/ugc-review/types/ugc";
import { useEffect, useRef } from "react";
import { DisabledActionHint } from "@/shared/ui/disabled-action-hint";
import { cn } from "@/shared/lib/utils";
import { captureVideoPoster, posterForDemoUploadFilename } from "@/shared/lib/demo-media";

export const Route = createFileRoute("/ugc-review/")({
    head: () => ({
        meta: [
            { title: "UGC Review — Viraldy" },
            {
                name: "description",
                content:
                    "Review creator videos before publishing, approving deliverables, or running Spark Ads.",
            },
        ],
    }),
    component: UgcInbox,
    validateSearch: (s: Record<string, unknown>) => ({
        campaignId: typeof s.campaignId === "string" ? s.campaignId : undefined,
        upload:
            s.upload === true || s.upload === "true" || s.upload === "1" || s.upload === 1
                ? true
                : undefined,
    }),
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

type UploadFileMeta = {
    width?: number;
    height?: number;
    durationSec?: number;
    aspectRatio?: UgcAsset["mediaAspectRatio"];
};

function UgcInbox() {
    const { campaignId, upload } = Route.useSearch();
    const navigate = useNavigate();
    const assets = useAppStore((s) => s.ugcAssets);
    const campaigns = useAllCampaigns();
    const startAnalysis = useAppStore((s) => s.startUgcAnalysis);
    const completeAnalysis = useAppStore((s) => s.completeUgcAnalysis);
    const jobs = useAppStore((s) => s.ugcJobs);
    const [query, setQuery] = useState("");
    const [filter, setFilter] = useState<"all" | "awaiting" | "revision" | "organic" | "spark">(
        "all",
    );
    const [uploadOpen, setUploadOpen] = useState(!!upload);

    useEffect(() => {
        if (upload) setUploadOpen(true);
    }, [upload]);

    const setUploadDialogOpen = (open: boolean) => {
        setUploadOpen(open);
        if (!open && upload) {
            void navigate({
                to: "/ugc-review",
                search: campaignId ? { campaignId } : {},
                replace: true,
            });
        }
    };

    // Drive processing jobs forward deterministically.
    const advance = useAppStore((s) => s.advanceUgcJob);
    useEffect(() => {
        const active = Object.keys(jobs);
        if (active.length === 0) return;
        const t = window.setInterval(() => {
            const state = useAppStore.getState();
            for (const id of Object.keys(state.ugcJobs)) {
                const j = state.ugcJobs[id];
                if (!j) continue;
                if (j.step >= j.total - 1) completeAnalysis(id);
                else advance(id);
            }
        }, 700);
        return () => window.clearInterval(t);
    }, [jobs, advance, completeAnalysis]);

    const handoffCampaign = useMemo(
        () => campaigns.find((c) => c.id === campaignId),
        [campaigns, campaignId],
    );

    const summary = useMemo(() => {
        const nonArchived = assets.filter((a) => !a.archived);
        return {
            awaiting: nonArchived.filter(
                (a) => a.decision === "awaiting-analysis" || a.decision === "processing",
            ).length,
            revision: nonArchived.filter(
                (a) => a.decision === "request-revision" || a.decision === "reject",
            ).length,
            organic: nonArchived.filter((a) => a.decision === "organic-ready").length,
            spark: nonArchived.filter(
                (a) => a.decision === "spark-ready" || a.decision === "small-spark-test",
            ).length,
        };
    }, [assets]);

    const filtered = useMemo(() => {
        return assets.filter((a) => {
            if (a.archived) return false;
            if (campaignId && a.campaignId !== campaignId) return false;
            if (
                filter === "awaiting" &&
                a.decision !== "awaiting-analysis" &&
                a.decision !== "processing"
            )
                return false;
            if (
                filter === "revision" &&
                a.decision !== "request-revision" &&
                a.decision !== "reject"
            )
                return false;
            if (filter === "organic" && a.decision !== "organic-ready") return false;
            if (
                filter === "spark" &&
                a.decision !== "spark-ready" &&
                a.decision !== "small-spark-test"
            )
                return false;
            if (query) {
                const q = query.toLowerCase();
                const creator =
                    seedCreators.find((c) => c.id === a.creatorId)?.name.toLowerCase() ?? "";
                if (!a.title.toLowerCase().includes(q) && !creator.includes(q)) return false;
            }
            return true;
        });
    }, [assets, campaignId, filter, query]);

    return (
        <AppShell>
            <div className="flex flex-col gap-6">
                <PageHeader
                    title="UGC Review"
                    description="Review creator videos before publishing, approving deliverables, or running Spark Ads."
                    actions={
                        <>
                            <Button variant="secondary" size="sm" asChild>
                                <Link to="/campaigns">View campaigns</Link>
                            </Button>
                            <Button size="sm" onClick={() => setUploadOpen(true)}>
                                <Upload className="mr-1.5 h-4 w-4" />
                                Upload UGC
                            </Button>
                        </>
                    }
                />

                {handoffCampaign && (
                    <SurfaceCard
                        padding="md"
                        className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between"
                    >
                        <div className="min-w-0">
                            <p className="text-xs uppercase tracking-wider text-text-tertiary">
                                Campaign handoff
                            </p>
                            <p className="mt-0.5 truncate text-sm font-medium text-text-primary">
                                {handoffCampaign.name}
                            </p>
                            <p className="mt-0.5 text-xs text-text-secondary">
                                {handoffCampaign.product} ·{" "}
                                {handoffCampaign.objective ?? "Campaign"} ·{" "}
                                {handoffCampaign.deliverables ?? 0} deliverables
                            </p>
                        </div>
                        <div className="flex gap-2">
                            <Button
                                size="sm"
                                variant="secondary"
                                onClick={() => navigate({ to: "/ugc-review" })}
                            >
                                Clear handoff
                            </Button>
                            <Button size="sm" onClick={() => setUploadOpen(true)}>
                                Upload for this campaign
                            </Button>
                        </div>
                    </SurfaceCard>
                )}

                <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                    <SummaryCard
                        label="Awaiting review"
                        value={summary.awaiting}
                        active={filter === "awaiting"}
                        onClick={() => setFilter(filter === "awaiting" ? "all" : "awaiting")}
                    />
                    <SummaryCard
                        label="Needs revision"
                        value={summary.revision}
                        active={filter === "revision"}
                        onClick={() => setFilter(filter === "revision" ? "all" : "revision")}
                    />
                    <SummaryCard
                        label="Organic-ready"
                        value={summary.organic}
                        active={filter === "organic"}
                        onClick={() => setFilter(filter === "organic" ? "all" : "organic")}
                    />
                    <SummaryCard
                        label="Spark-ready"
                        value={summary.spark}
                        active={filter === "spark"}
                        onClick={() => setFilter(filter === "spark" ? "all" : "spark")}
                    />
                </div>

                <SurfaceCard padding="sm" className="flex flex-wrap items-center gap-2">
                    <Input
                        placeholder="Search assets, creators, campaigns…"
                        aria-label="Search assets, creators, and campaigns"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        className="max-w-xs"
                    />
                    {(query || filter !== "all") && (
                        <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => {
                                setQuery("");
                                setFilter("all");
                            }}
                        >
                            Clear filters
                        </Button>
                    )}
                </SurfaceCard>

                <SurfaceCard padding="none" className="overflow-hidden">
                    {filtered.length === 0 ? (
                        <div className="p-10">
                            <EmptyState
                                icon={Video}
                                title="Review creator content before you spend"
                                description="Upload a creator draft and attach its Campaign Pack. Viraldy will compare the video against the brief, identify blockers, and generate actionable revision notes."
                                action={
                                    <Button size="sm" onClick={() => setUploadOpen(true)}>
                                        Upload UGC
                                    </Button>
                                }
                            />
                        </div>
                    ) : (
                        <ul className="divide-y divide-hairline">
                            {filtered.map((a) => (
                                <UgcRow
                                    key={a.id}
                                    asset={a}
                                    campaignName={
                                        campaigns.find((c) => c.id === a.campaignId)?.name
                                    }
                                    onAnalyze={() => startAnalysis(a.id, ugcProcessingSteps.length)}
                                />
                            ))}
                        </ul>
                    )}
                </SurfaceCard>
            </div>

            <UploadDialog
                open={uploadOpen}
                onOpenChange={setUploadDialogOpen}
                defaultCampaignId={campaignId}
            />
        </AppShell>
    );
}

function SummaryCard({
    label,
    value,
    active,
    onClick,
}: {
    label: string;
    value: number;
    active: boolean;
    onClick: () => void;
}) {
    return (
        <button
            type="button"
            onClick={onClick}
            className={`surface-card inner-top-highlight flex flex-col gap-1 rounded-[14px] p-4 text-left transition-colors hover:bg-surface-soft focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring ${active ? "ring-1 ring-primary" : ""}`}
            aria-pressed={active}
        >
            <span className="text-xs text-text-tertiary">{label}</span>
            <span className="text-2xl font-semibold tracking-tight text-text-primary">{value}</span>
            <span className="text-xs text-text-secondary">
                {active
                    ? "Showing this queue"
                    : value === 0
                      ? "Nothing to review"
                      : "Filter this queue"}
            </span>
        </button>
    );
}

function UgcRow({
    asset,
    campaignName,
    onAnalyze,
}: {
    asset: UgcAsset;
    campaignName?: string;
    onAnalyze: () => void;
}) {
    const meta = decisionMeta[asset.decision];
    const creator = seedCreators.find((c) => c.id === asset.creatorId);
    const submitted = new Date(asset.submittedAt);
    return (
        <li className="flex items-center gap-4 px-4 py-3">
            <DemoMediaTile
                mediaUrl={asset.mediaUrl}
                mediaKind={asset.mediaUrl ? "video" : undefined}
                posterUrl={asset.posterUrl}
                alt={`${asset.title} preview`}
                seed={asset.thumbSeed}
                label={asset.objective}
                badges={[`${asset.durationSec}s`]}
                markers={[
                    { at: 10, tone: "info" },
                    { at: asset.decision === "request-revision" ? 42 : 28, tone: meta.tone },
                    { at: 86, tone: asset.rightsStatus === "complete" ? "ok" : "warn" },
                ]}
                aspect={asset.mediaAspectRatio ?? "3 / 2"}
                fit={asset.mediaAspectRatio === "9:16" ? "contain" : "cover"}
                className="h-16 w-24 shrink-0 rounded-lg bg-black ring-1 ring-hairline"
            />
            <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                    <p className="truncate text-sm font-medium text-text-primary">{asset.title}</p>
                    <StatusChip tone={meta.tone} dot>
                        {meta.label}
                    </StatusChip>
                </div>
                <p className="mt-0.5 truncate text-xs text-text-secondary">
                    {creator?.name ?? "Unknown creator"} · {campaignName ?? "No campaign"} · v
                    {asset.submissionVersion} · {asset.durationSec}s · {formatUtcDate(submitted)}
                </p>
            </div>
            <div className="flex shrink-0 items-center gap-2">
                {asset.decision === "awaiting-analysis" && (
                    <Button size="sm" variant="secondary" onClick={onAnalyze}>
                        <Sparkles className="mr-1 h-3.5 w-3.5" />
                        Analyze
                    </Button>
                )}
                {asset.decision === "failed" && (
                    <Button size="sm" variant="secondary" onClick={onAnalyze}>
                        Retry
                    </Button>
                )}
                <Button size="sm" variant="ghost" asChild>
                    <Link to="/ugc-review/$assetId" params={{ assetId: asset.id }}>
                        Open <ChevronRight className="ml-1 h-3.5 w-3.5" />
                    </Link>
                </Button>
            </div>
        </li>
    );
}

function UploadDialog({
    open,
    onOpenChange,
    defaultCampaignId,
}: {
    open: boolean;
    onOpenChange: (v: boolean) => void;
    defaultCampaignId?: string;
}) {
    const navigate = useNavigate();
    const campaigns = useAllCampaigns();
    const assets = useAppStore((s) => s.ugcAssets);
    const uploadUgc = useAppStore((s) => s.uploadUgc);
    const startAnalysis = useAppStore((s) => s.startUgcAnalysis);
    const [tab, setTab] = useState<"file" | "demo">("file");
    const [title, setTitle] = useState("");
    const [creatorId, setCreatorId] = useState<string>(seedCreators[0].id);
    const [campaignId, setCampaignId] = useState<string>(defaultCampaignId ?? "");
    const [objective, setObjective] = useState<UgcReviewObjective>("TikTok Shop affiliate");
    const [fileName, setFileName] = useState<string>("");
    const [fileUrl, setFileUrl] = useState<string | undefined>();
    const [fileMeta, setFileMeta] = useState<UploadFileMeta | null>(null);
    const [posterUrl, setPosterUrl] = useState<string | undefined>();
    const [revisionOfId, setRevisionOfId] = useState("");
    const [demoId, setDemoId] = useState("demo-sofa");
    const fileRef = useRef<HTMLInputElement>(null);
    const objectUrlRef = useRef<string | undefined>(undefined);

    useEffect(() => {
        if (defaultCampaignId) setCampaignId(defaultCampaignId);
    }, [defaultCampaignId]);

    useEffect(() => {
        if (!open) {
            if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
            objectUrlRef.current = undefined;
            setFileUrl(undefined);
            setFileName("");
            setFileMeta(null);
            setPosterUrl(undefined);
            setRevisionOfId("");
            return;
        }
        setDemoId("demo-sofa");
    }, [open]);

    useEffect(
        () => () => {
            if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
        },
        [],
    );

    useEffect(() => {
        if (!fileUrl) {
            setPosterUrl(undefined);
            return;
        }
        let active = true;
        void captureVideoPoster(fileUrl).then((poster) => {
            if (active) setPosterUrl(poster ?? posterForDemoUploadFilename(fileName));
        });
        return () => {
            active = false;
        };
    }, [fileName, fileUrl]);

    const revisionCandidates = useMemo(
        () =>
            assets.filter(
                (asset) => !asset.archived && (!campaignId || asset.campaignId === campaignId),
            ),
        [assets, campaignId],
    );
    const previousVersion = revisionCandidates.find((asset) => asset.id === revisionOfId);

    useEffect(() => {
        if (revisionOfId && !revisionCandidates.some((asset) => asset.id === revisionOfId)) {
            setRevisionOfId("");
        }
    }, [revisionCandidates, revisionOfId]);

    const handleFile = (f: File | null) => {
        if (!f) return;
        if (!/(mp4|mov|webm)$/i.test(f.name)) {
            toast.error("Unsupported file type. Use mp4, mov, or webm.");
            return;
        }
        setFileName(f.name);
        if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
        objectUrlRef.current = URL.createObjectURL(f);
        setFileUrl(objectUrlRef.current);
        setFileMeta(null);
        setPosterUrl(undefined);
        if (!title) setTitle(f.name.replace(/\.[^.]+$/, ""));
    };

    const updateVideoMeta = (video: HTMLVideoElement) => {
        const ratio = video.videoWidth / Math.max(1, video.videoHeight);
        const aspectRatio: UgcAsset["mediaAspectRatio"] =
            ratio < 0.8 ? "9:16" : ratio > 1.4 ? "16:9" : "4:5";
        setFileMeta({
            width: video.videoWidth,
            height: video.videoHeight,
            durationSec: video.duration,
            aspectRatio,
        });
    };

    const fileBlocker =
        tab === "file"
            ? !fileName
                ? "Choose a creator video first."
                : !title.trim()
                  ? "Add an asset title."
                  : !campaignId
                    ? "Attach this draft to a campaign."
                    : null
            : null;

    const submit = (analyze: boolean) => {
        if (tab === "file") {
            if (fileBlocker) return toast.error(fileBlocker);
            const packId = campaigns.find((c) => c.id === campaignId)?.packId;
            const id = uploadUgc({
                title: title.trim(),
                creatorId,
                campaignId,
                packId,
                submissionVersion: previousVersion ? previousVersion.submissionVersion + 1 : 1,
                previousVersionId: previousVersion?.id,
                thumbSeed: fileName || "custom",
                mediaUrl: objectUrlRef.current,
                posterUrl: posterUrl ?? posterForDemoUploadFilename(fileName),
                mediaAspectRatio: fileMeta?.aspectRatio,
                durationSec: Math.round(fileMeta?.durationSec ?? 24),
                objective,
                isLocalUpload: true,
            });
            objectUrlRef.current = undefined; // ownership transferred to the store
            setFileUrl(undefined);
            if (analyze) startAnalysis(id, ugcProcessingSteps.length);
            toast.success(analyze ? "Analysis started" : "Draft saved");
            onOpenChange(false);
            if (analyze) navigate({ to: "/ugc-review/$assetId", params: { assetId: id } });
        } else {
            // Demo asset — synthesize
            const demo = demoUploadAssets.find((item) => item.id === demoId) ?? demoUploadAssets[0];
            const id = uploadUgc({
                title: demo.title,
                creatorId: demo.creatorId,
                campaignId: demo.campaignId,
                packId: demo.packId,
                submissionVersion: 1,
                thumbSeed: demo.thumbSeed,
                mediaUrl: demo.mediaUrl,
                posterUrl: demo.posterUrl,
                mediaAspectRatio: demo.mediaAspectRatio,
                durationSec: demo.durationSec,
                objective: demo.objective,
                isDemo: true,
            });
            if (analyze) startAnalysis(id, ugcProcessingSteps.length);
            toast.success("Demo asset added");
            onOpenChange(false);
            if (analyze) navigate({ to: "/ugc-review/$assetId", params: { assetId: id } });
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="flex max-h-[calc(100dvh-4rem)] max-w-lg flex-col overflow-hidden">
                <DialogHeader>
                    <DialogTitle>Upload creator draft</DialogTitle>
                    <DialogDescription>
                        Preview locally and attach a Campaign Pack. This runs entirely in your
                        browser.
                    </DialogDescription>
                </DialogHeader>
                <Tabs
                    value={tab}
                    onValueChange={(v) => setTab(v as "file" | "demo")}
                    className="min-h-0"
                >
                    <TabsList className="grid w-full grid-cols-2">
                        <TabsTrigger value="file">Upload file</TabsTrigger>
                        <TabsTrigger value="demo">Choose demo asset</TabsTrigger>
                    </TabsList>
                    <TabsContent
                        value="file"
                        className="max-h-[58dvh] space-y-3 overflow-y-auto pt-3"
                    >
                        <div>
                            <Label htmlFor="ugc-file-input">Video file</Label>
                            <label
                                htmlFor="ugc-file-input"
                                className="mt-1 flex cursor-pointer flex-col items-center justify-center gap-2 rounded-md border border-dashed border-hairline bg-surface-soft/60 px-5 py-7 text-center transition-colors hover:bg-surface-soft"
                            >
                                <Upload className="h-5 w-5 text-text-tertiary" />
                                <span className="text-sm font-medium text-text-primary">
                                    Choose creator video
                                </span>
                                <span className="text-xs text-text-tertiary">
                                    mp4, mov, webm · vertical or horizontal
                                </span>
                            </label>
                            <input
                                id="ugc-file-input"
                                ref={fileRef}
                                type="file"
                                accept="video/mp4,video/quicktime,video/webm"
                                onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
                                className="sr-only"
                            />
                            <div aria-live="polite" className="mt-2 text-xs text-text-tertiary">
                                {fileName
                                    ? `Selected ${fileName}${fileMeta?.aspectRatio ? ` · ${fileMeta.aspectRatio}` : ""}`
                                    : "No video selected yet."}
                            </div>
                        </div>
                        {fileUrl && (
                            <div className="rounded-md border border-hairline bg-black p-2">
                                <video
                                    src={fileUrl}
                                    poster={posterUrl ?? posterForDemoUploadFilename(fileName)}
                                    controls
                                    muted
                                    playsInline
                                    preload="metadata"
                                    className="mx-auto max-h-[360px] w-full rounded bg-black object-contain"
                                    onLoadedMetadata={(event) =>
                                        updateVideoMeta(event.currentTarget)
                                    }
                                />
                                <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-text-tertiary">
                                    <StatusChip tone="info">Preview ready</StatusChip>
                                    {fileMeta?.width && fileMeta.height && (
                                        <span>
                                            {fileMeta.width}×{fileMeta.height}
                                        </span>
                                    )}
                                    {fileMeta?.durationSec && (
                                        <span>{Math.round(fileMeta.durationSec)}s</span>
                                    )}
                                    {fileMeta?.aspectRatio && <span>{fileMeta.aspectRatio}</span>}
                                    {posterUrl && <span>Preview frame captured</span>}
                                </div>
                            </div>
                        )}
                        <div>
                            <Label htmlFor="ugc-title">Asset title</Label>
                            <Input
                                id="ugc-title"
                                value={title}
                                onChange={(e) => setTitle(e.target.value)}
                                placeholder="e.g. Kitchen Organizer Draft V1"
                            />
                        </div>
                        <div>
                            <Label>Campaign</Label>
                            <Select value={campaignId} onValueChange={setCampaignId}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select a campaign" />
                                </SelectTrigger>
                                <SelectContent>
                                    {campaigns.map((c) => (
                                        <SelectItem key={c.id} value={c.id}>
                                            {c.name}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div>
                            <Label>Revision of</Label>
                            <Select
                                value={revisionOfId || "new"}
                                onValueChange={(value) => {
                                    const nextId = value === "new" ? "" : value;
                                    setRevisionOfId(nextId);
                                    const previous = assets.find((asset) => asset.id === nextId);
                                    if (!previous) return;
                                    setCampaignId(previous.campaignId ?? "");
                                    setCreatorId(previous.creatorId);
                                    setObjective(previous.objective);
                                    setTitle(
                                        `${previous.title.replace(/\s+V\d+$/i, "")} V${previous.submissionVersion + 1}`,
                                    );
                                }}
                            >
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="new">New asset</SelectItem>
                                    {revisionCandidates.map((asset) => (
                                        <SelectItem key={asset.id} value={asset.id}>
                                            V{asset.submissionVersion} · {asset.title}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            {previousVersion && (
                                <p className="mt-1 text-xs text-text-tertiary">
                                    Saves as V{previousVersion.submissionVersion + 1} and enables
                                    revision comparison.
                                </p>
                            )}
                        </div>
                        <div>
                            <Label>Creator</Label>
                            <Select value={creatorId} onValueChange={setCreatorId}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {seedCreators.map((c) => (
                                        <SelectItem key={c.id} value={c.id}>
                                            {c.name} · {c.handle}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div>
                            <Label>Review objective</Label>
                            <Select
                                value={objective}
                                onValueChange={(v) => setObjective(v as UgcReviewObjective)}
                            >
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="Organic TikTok">Organic TikTok</SelectItem>
                                    <SelectItem value="TikTok Shop affiliate">
                                        TikTok Shop affiliate
                                    </SelectItem>
                                    <SelectItem value="Spark Ads test">Spark Ads test</SelectItem>
                                    <SelectItem value="Paid UGC asset">Paid UGC asset</SelectItem>
                                    <SelectItem value="Creator deliverable approval">
                                        Creator deliverable approval
                                    </SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </TabsContent>
                    <TabsContent
                        value="demo"
                        className="max-h-[58dvh] space-y-2 overflow-y-auto pt-3"
                    >
                        <p className="text-sm text-text-secondary">
                            Add a fully seeded demo submission to explore the review flow.
                        </p>
                        <ul className="space-y-1.5">
                            {demoUploadAssets.map((d) => (
                                <li key={d.id}>
                                    <button
                                        type="button"
                                        onClick={() => setDemoId(d.id)}
                                        aria-pressed={demoId === d.id}
                                        className={cn(
                                            "grid w-full grid-cols-[76px_minmax(0,1fr)_auto] items-center gap-3 rounded-md border px-3 py-2 text-left text-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
                                            demoId === d.id
                                                ? "border-primary bg-primary-softer"
                                                : "border-hairline bg-surface-soft/60 hover:bg-surface-soft",
                                        )}
                                    >
                                        <DemoMediaTile
                                            mediaUrl={d.mediaUrl}
                                            mediaKind={d.mediaUrl ? "video" : undefined}
                                            posterUrl={d.posterUrl}
                                            seed={d.thumbSeed}
                                            label={d.objective}
                                            badges={[`${d.durationSec}s`]}
                                            aspect={d.mediaAspectRatio ?? "3 / 2"}
                                            fit={
                                                d.mediaAspectRatio === "9:16" ? "contain" : "cover"
                                            }
                                            className="rounded-md bg-black"
                                        />
                                        <span className="min-w-0">
                                            <span className="block truncate font-medium">
                                                {d.title}
                                            </span>
                                            <span className="block text-xs text-text-tertiary">
                                                {d.durationSec}s · {d.objective}
                                            </span>
                                        </span>
                                        <Play className="h-4 w-4 text-text-tertiary" />
                                    </button>
                                </li>
                            ))}
                        </ul>
                    </TabsContent>
                </Tabs>
                <DialogFooter>
                    <Button variant="ghost" onClick={() => onOpenChange(false)}>
                        Cancel
                    </Button>
                    {tab === "file" ? (
                        <>
                            <DisabledActionHint reason={fileBlocker} className="items-end">
                                <Button
                                    variant="secondary"
                                    onClick={() => submit(false)}
                                    disabled={!!fileBlocker}
                                >
                                    Save draft
                                </Button>
                            </DisabledActionHint>
                            <DisabledActionHint reason={fileBlocker} className="items-end">
                                <Button onClick={() => submit(true)} disabled={!!fileBlocker}>
                                    Upload and analyze
                                </Button>
                            </DisabledActionHint>
                        </>
                    ) : (
                        <>
                            <Button variant="secondary" onClick={() => submit(false)}>
                                Save draft
                            </Button>
                            <Button onClick={() => submit(true)}>Upload and analyze</Button>
                        </>
                    )}
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
