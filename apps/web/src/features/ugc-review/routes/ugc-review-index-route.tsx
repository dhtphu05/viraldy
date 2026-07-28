import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { AppShell } from "@/widgets/app-shell/app-shell";
import { PageHeader } from "@/shared/ui/page-header";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { StatusChip } from "@/shared/ui/status-chip";
import { EmptyState } from "@/shared/ui/empty-state";
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
        upload: s.upload === "1" || s.upload === 1 ? true : undefined,
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
                onOpenChange={setUploadOpen}
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
                {value === 0 ? "Nothing to review" : "Click to filter"}
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
            <div
                aria-hidden
                className="h-16 w-24 shrink-0 rounded-lg bg-gradient-to-br from-surface-soft to-surface-muted ring-1 ring-hairline"
                style={{
                    background: `linear-gradient(135deg, hsl(${(asset.thumbSeed.charCodeAt(0) * 7) % 360} 60% 60%), hsl(${(asset.thumbSeed.charCodeAt(0) * 11) % 360} 60% 45%))`,
                }}
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
                    {asset.submissionVersion} · {asset.durationSec}s ·{" "}
                    {submitted.toLocaleDateString()}
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
    const uploadUgc = useAppStore((s) => s.uploadUgc);
    const startAnalysis = useAppStore((s) => s.startUgcAnalysis);
    const [tab, setTab] = useState<"file" | "demo">("file");
    const [title, setTitle] = useState("");
    const [creatorId, setCreatorId] = useState<string>(seedCreators[0].id);
    const [campaignId, setCampaignId] = useState<string>(defaultCampaignId ?? "");
    const [objective, setObjective] = useState<UgcReviewObjective>("TikTok Shop affiliate");
    const [fileName, setFileName] = useState<string>("");
    const fileRef = useRef<HTMLInputElement>(null);
    const objectUrlRef = useRef<string | undefined>(undefined);

    useEffect(() => {
        if (defaultCampaignId) setCampaignId(defaultCampaignId);
    }, [defaultCampaignId]);

    useEffect(
        () => () => {
            if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
        },
        [],
    );

    const handleFile = (f: File | null) => {
        if (!f) return;
        if (!/(mp4|mov|webm)$/i.test(f.name)) {
            toast.error("Unsupported file type. Use mp4, mov, or webm.");
            return;
        }
        setFileName(f.name);
        if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
        objectUrlRef.current = URL.createObjectURL(f);
        if (!title) setTitle(f.name.replace(/\.[^.]+$/, ""));
    };

    const submit = (analyze: boolean) => {
        if (tab === "file") {
            if (!title.trim()) return toast.error("Title is required");
            if (!campaignId) return toast.error("Campaign is required");
            const packId = campaigns.find((c) => c.id === campaignId)?.packId;
            const id = uploadUgc({
                title: title.trim(),
                creatorId,
                campaignId,
                packId,
                submissionVersion: 1,
                thumbSeed: fileName || "custom",
                mediaUrl: objectUrlRef.current,
                durationSec: 24,
                objective,
                isLocalUpload: true,
            });
            objectUrlRef.current = undefined; // ownership transferred to the store
            if (analyze) startAnalysis(id, ugcProcessingSteps.length);
            toast.success(analyze ? "Analysis started" : "Draft saved");
            onOpenChange(false);
            if (analyze) navigate({ to: "/ugc-review/$assetId", params: { assetId: id } });
        } else {
            // Demo asset — synthesize
            const demo = demoUploadAssets[0];
            const id = uploadUgc({
                title: demo.title,
                creatorId: demo.creatorId,
                campaignId: demo.campaignId,
                packId: demo.packId,
                submissionVersion: 1,
                thumbSeed: demo.thumbSeed,
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
            <DialogContent className="max-w-lg">
                <DialogHeader>
                    <DialogTitle>Upload creator draft</DialogTitle>
                    <DialogDescription>
                        Preview locally and attach a Campaign Pack. This runs entirely in your
                        browser.
                    </DialogDescription>
                </DialogHeader>
                <Tabs value={tab} onValueChange={(v) => setTab(v as "file" | "demo")}>
                    <TabsList className="grid w-full grid-cols-2">
                        <TabsTrigger value="file">Upload file</TabsTrigger>
                        <TabsTrigger value="demo">Choose demo asset</TabsTrigger>
                    </TabsList>
                    <TabsContent value="file" className="space-y-3 pt-3">
                        <div>
                            <Label>Video file</Label>
                            <input
                                ref={fileRef}
                                type="file"
                                accept="video/mp4,video/quicktime,video/webm"
                                onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
                                className="mt-1 block w-full text-sm"
                            />
                            {fileName && (
                                <p className="mt-1 text-xs text-text-tertiary">
                                    Selected: {fileName}
                                </p>
                            )}
                        </div>
                        <div>
                            <Label>Asset title</Label>
                            <Input
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
                    <TabsContent value="demo" className="space-y-2 pt-3">
                        <p className="text-sm text-text-secondary">
                            Add a fully seeded demo submission to explore the review flow.
                        </p>
                        <ul className="space-y-1.5">
                            {demoUploadAssets.map((d) => (
                                <li
                                    key={d.id}
                                    className="flex items-center justify-between rounded-md bg-surface-soft/60 px-3 py-2 text-sm"
                                >
                                    <div className="min-w-0">
                                        <p className="truncate font-medium">{d.title}</p>
                                        <p className="text-xs text-text-tertiary">
                                            {d.durationSec}s · {d.objective}
                                        </p>
                                    </div>
                                    <Play className="h-4 w-4 text-text-tertiary" />
                                </li>
                            ))}
                        </ul>
                    </TabsContent>
                </Tabs>
                <DialogFooter>
                    <Button variant="ghost" onClick={() => onOpenChange(false)}>
                        Cancel
                    </Button>
                    <Button variant="secondary" onClick={() => submit(false)}>
                        Save draft
                    </Button>
                    <Button onClick={() => submit(true)}>Upload and analyze</Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
