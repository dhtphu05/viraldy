import { createFileRoute, Link, notFound, useNavigate } from "@tanstack/react-router";
import { useMemo, useState, useEffect, useRef } from "react";
import { AppShell } from "@/widgets/app-shell/app-shell";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { StatusChip } from "@/shared/ui/status-chip";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { Textarea } from "@/shared/ui/textarea";
import { Checkbox } from "@/shared/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/shared/ui/tabs";
import { EmptyState } from "@/shared/ui/empty-state";
import { useAllCampaigns, useAppStore } from "@/app/store/app-store";
import { seedProducts } from "@/features/products/data/products";
import type {
    ActivityEvent,
    AngleConcept,
    CampaignPack,
    Hook,
    HookType,
    ScriptBlock,
    StoryboardScene,
} from "@/features/campaigns/types/campaign";
import { CampaignDetailHeader } from "@/features/campaigns/components/campaign-detail-header";
import { CampaignOverview } from "@/features/campaigns/components/campaign-overview";
import { CampaignPackWorkspace } from "@/features/campaigns/components/campaign-pack-workspace";
import { CampaignActionTray } from "@/features/campaigns/components/campaign-action-tray";
import { CreatorPreviewDialog } from "@/features/campaigns/components/creator-preview-dialog";
import { STEPS, readinessState, stepIsComplete } from "@/features/campaigns/lib/campaignSteps";
import type { StepId } from "@/features/campaigns/types/campaign";
import {
    generateAngles,
    generateOneAngle,
    generateHooks,
    generateOneHook,
    generateScript,
    regenerateScriptSection,
    generateStoryboard,
    regenerateStoryboardScene,
    generateAdaptation,
    checkClaims,
} from "@/features/campaigns/lib/mockCampaignAI";
import {
    Sparkles,
    Play,
    Lock,
    Unlock,
    Trash2,
    Plus,
    RefreshCw,
    Copy,
    Eye,
    AlertTriangle,
    Check,
    ChevronDown,
    ExternalLink,
} from "lucide-react";
import { toast } from "sonner";
import { DemoMediaTile } from "@/shared/ui/demo-media-tile";
import { cn } from "@/shared/lib/utils";
import { formatUtcDateTime, formatUtcTime } from "@/shared/lib/date-format";
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

export const Route = createFileRoute("/campaigns/$campaignId")({
    head: ({ loaderData }) => {
        const name = (loaderData as { name?: string } | undefined)?.name ?? "Campaign";
        return {
            meta: [
                { title: `${name} — Viraldy` },
                { name: "description", content: `Campaign workspace for ${name}.` },
            ],
        };
    },
    component: CampaignDetail,
    notFoundComponent: () => (
        <AppShell>
            <div className="mx-auto max-w-lg pt-12">
                <EmptyState
                    title="Campaign not found"
                    description="This campaign may have been deleted or the link is out of date."
                    action={
                        <Button asChild>
                            <Link to="/campaigns">Back to campaigns</Link>
                        </Button>
                    }
                />
            </div>
        </AppShell>
    ),
});

function useCampaignAndPack(campaignId: string) {
    const campaigns = useAllCampaigns();
    const packs = useAppStore((s) => s.packs);
    const summary = campaigns.find((c) => c.id === campaignId);
    const pack = summary?.packId ? packs[summary.packId] : undefined;
    return { summary, pack };
}

function CampaignDetail() {
    const { campaignId } = Route.useParams();
    const navigate = useNavigate();
    const { summary, pack } = useCampaignAndPack(campaignId);
    const update = useAppStore((s) => s.updateCampaignPack);
    const addActivity = useAppStore((s) => s.addActivity);
    const setPackStatus = useAppStore((s) => s.setPackStatus);
    const duplicate = useAppStore((s) => s.duplicateCampaign);
    const archive = useAppStore((s) => s.archiveCampaign);
    const rename = useAppStore((s) => s.renameCampaign);
    const reviewWarning = useAppStore((s) => s.reviewWarning);
    const activityAll = useAppStore((s) => s.campaignActivity);
    const ugcAssets = useAppStore((s) => s.ugcAssets);
    const autosaveAt = useAppStore((s) => (pack ? s.packAutosaveAt[pack.id] : undefined));

    const [tab, setTab] = useState<"overview" | "pack" | "assets" | "activity">("overview");
    const [step, setStep] = useState<StepId>("product");
    const [previewOpen, setPreviewOpen] = useState(false);
    const [saveState, setSaveState] = useState<"idle" | "saving" | "saved">("idle");
    const saveTimer = useRef<number | null>(null);

    useEffect(() => {
        if (saveState === "saving") {
            const t = window.setTimeout(() => setSaveState("saved"), 400);
            return () => clearTimeout(t);
        }
    }, [saveState]);

    if (!summary || !pack) throw notFound();

    const product = seedProducts.find((p) => p.id === pack.productId);
    const readiness = readinessState(pack);
    const activity = activityAll.filter((e) => e.campaignId === campaignId).slice(0, 30);
    const nextIncomplete = STEPS.find((item) => !stepIsComplete(pack, item.id));
    const hasCampaignAssets = ugcAssets.some(
        (asset) => asset.campaignId === campaignId && !asset.archived,
    );

    function patch(next: Partial<CampaignPack>, activityEvent?: Parameters<typeof addActivity>[0]) {
        if (!pack) return;
        update(pack.id, next);
        setSaveState("saving");
        if (saveTimer.current) window.clearTimeout(saveTimer.current);
        saveTimer.current = window.setTimeout(() => setSaveState("idle"), 1600);
        if (activityEvent) addActivity(activityEvent);
    }

    const saveLabel =
        saveState === "saving"
            ? "Saving…"
            : autosaveAt
              ? `Saved in this browser · ${formatUtcTime(autosaveAt)}`
              : "Saved in this browser";

    function openNextAction() {
        if (readiness.state === "Creator-ready") {
            setPreviewOpen(true);
            return;
        }
        setTab("pack");
        setStep(nextIncomplete?.id ?? "review");
    }

    return (
        <AppShell
            footer={
                tab === "pack" ? (
                    <CampaignActionTray
                        pack={pack}
                        step={step}
                        onStep={setStep}
                        onPreview={() => setPreviewOpen(true)}
                    />
                ) : undefined
            }
        >
            <div className="flex flex-col gap-6">
                <CampaignDetailHeader
                    pack={pack}
                    productName={product?.name ?? "Product"}
                    saveLabel={saveLabel}
                    primaryActionLabel={
                        readiness.state === "Creator-ready"
                            ? "Preview for creator"
                            : `Continue: ${nextIncomplete?.label ?? "Review"}`
                    }
                    onPrimaryAction={openNextAction}
                    onDuplicate={() => {
                        const newId = duplicate(campaignId);
                        if (newId)
                            navigate({
                                to: "/campaigns/$campaignId",
                                params: { campaignId: newId },
                            });
                    }}
                    onRename={(name) => {
                        rename(campaignId, name);
                        patch({ name });
                        toast.success("Renamed");
                    }}
                    onArchive={() => {
                        archive(campaignId);
                        toast.success("Campaign archived");
                    }}
                    onStatusChange={(status) => setPackStatus(pack.id, status)}
                />

                <Tabs value={tab} onValueChange={(v) => setTab(v as typeof tab)}>
                    <TabsList>
                        <TabsTrigger value="overview">Overview</TabsTrigger>
                        <TabsTrigger value="pack">Campaign Pack</TabsTrigger>
                        <TabsTrigger value="assets">Assets</TabsTrigger>
                        <TabsTrigger value="activity">Activity</TabsTrigger>
                    </TabsList>

                    <TabsContent value="overview" className="mt-6">
                        <CampaignOverview
                            pack={pack}
                            readinessState={readiness.state}
                            reasons={readiness.reasons}
                            activity={activity}
                            onContinue={(nextStep) => {
                                setTab("pack");
                                setStep(nextStep);
                            }}
                            onPreview={() => setPreviewOpen(true)}
                        />
                    </TabsContent>

                    <TabsContent value="pack" className="mt-6">
                        <CampaignPackWorkspace pack={pack} step={step} onStep={setStep}>
                            <StepSection
                                pack={pack}
                                step={step}
                                onPatch={patch}
                                campaignId={campaignId}
                                onReviewWarning={(id) => reviewWarning(pack.id, id)}
                            />
                        </CampaignPackWorkspace>
                    </TabsContent>

                    <TabsContent value="assets" className="mt-6">
                        <div className="border-y border-divider bg-surface p-7">
                            <EmptyState
                                title={
                                    hasCampaignAssets
                                        ? "Campaign UGC is ready to review"
                                        : "No creator drafts uploaded yet"
                                }
                                description={
                                    hasCampaignAssets
                                        ? "Review campaign assets, evidence, and publishing readiness in UGC Review."
                                        : "Upload the creator draft to review execution, claims, and publishing readiness."
                                }
                                action={
                                    <Button asChild>
                                        <Link
                                            to="/ugc-review"
                                            search={{ campaignId, upload: true }}
                                        >
                                            {hasCampaignAssets
                                                ? "Review campaign UGC"
                                                : "Upload creator draft"}
                                        </Link>
                                    </Button>
                                }
                            />
                        </div>
                    </TabsContent>

                    <TabsContent value="activity" className="mt-6">
                        <SurfaceCard padding="none" className="divide-y divide-hairline/70">
                            {activity.length === 0 ? (
                                <div className="p-6 text-sm text-text-tertiary">
                                    No activity yet.
                                </div>
                            ) : (
                                activity.map((e) => (
                                    <div
                                        key={e.id}
                                        className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 px-4 py-3"
                                    >
                                        <StatusChip tone="info">
                                            {e.kind.replace(/-/g, " ")}
                                        </StatusChip>
                                        <p className="truncate text-sm text-text-primary">
                                            {e.detail}
                                        </p>
                                        <p className="tabular text-xs text-text-tertiary">
                                            {formatUtcDateTime(e.at)}
                                        </p>
                                    </div>
                                ))
                            )}
                        </SurfaceCard>
                    </TabsContent>
                </Tabs>
            </div>

            <CreatorPreviewDialog
                pack={pack}
                campaignId={campaignId}
                open={previewOpen}
                onOpenChange={setPreviewOpen}
            />
        </AppShell>
    );
}

// -------------------- Step sections --------------------

function StepSection(props: {
    pack: CampaignPack;
    step: StepId;
    onPatch: WorkspaceLayoutProps["onPatch"];
    campaignId: string;
    onReviewWarning: (id: string) => void;
}) {
    const { pack, step, onPatch, campaignId, onReviewWarning } = props;
    switch (step) {
        case "product":
            return <ProductStep pack={pack} onPatch={onPatch} />;
        case "references":
            return <ReferencesStep pack={pack} onPatch={onPatch} />;
        case "adaptation":
            return <AdaptationStep pack={pack} onPatch={onPatch} campaignId={campaignId} />;
        case "angles":
            return <AnglesStep pack={pack} onPatch={onPatch} campaignId={campaignId} />;
        case "hooks":
            return <HooksStep pack={pack} onPatch={onPatch} campaignId={campaignId} />;
        case "script":
            return <ScriptStep pack={pack} onPatch={onPatch} campaignId={campaignId} />;
        case "storyboard":
            return <StoryboardStep pack={pack} onPatch={onPatch} campaignId={campaignId} />;
        case "cta":
            return <CtaStep pack={pack} onPatch={onPatch} onReviewWarning={onReviewWarning} />;
        case "deliverables":
            return <DeliverablesStep pack={pack} onPatch={onPatch} />;
        case "review":
            return <ReviewStep pack={pack} campaignId={campaignId} />;
    }
}

type WorkspaceLayoutProps = {
    onPatch: (next: Partial<CampaignPack>, activity?: Omit<ActivityEvent, "id" | "at">) => void;
};

function SectionShell({
    title,
    description,
    children,
    actions,
}: {
    title: string;
    description: string;
    children: React.ReactNode;
    actions?: React.ReactNode;
}) {
    return (
        <div className="flex min-w-0 flex-col gap-5 [&_[role=combobox]]:min-w-0">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <h2 className="text-lg font-semibold text-text-primary">{title}</h2>
                    <p className="mt-0.5 text-sm text-text-secondary">{description}</p>
                </div>
                {actions}
            </div>
            {children}
        </div>
    );
}

// Product & Goal
function ProductStep({
    pack,
    onPatch,
}: {
    pack: CampaignPack;
    onPatch: WorkspaceLayoutProps["onPatch"];
}) {
    return (
        <SectionShell
            title="Product & Goal"
            description="Set the product, market, and creator direction for this campaign."
        >
            <SurfaceCard padding="lg" className="flex flex-col gap-4">
                <div className="grid gap-3 sm:grid-cols-2">
                    <div className="grid gap-1.5">
                        <Label>Campaign name</Label>
                        <Input
                            value={pack.name}
                            onChange={(e) => onPatch({ name: e.target.value })}
                        />
                    </div>
                    <div className="grid gap-1.5">
                        <Label>Product</Label>
                        <Select
                            value={pack.productId ?? ""}
                            onValueChange={(v) =>
                                onPatch(
                                    { productId: v },
                                    {
                                        campaignId: pack.id,
                                        kind: "product-selected",
                                        detail: `Product changed`,
                                    },
                                )
                            }
                        >
                            <SelectTrigger>
                                <SelectValue placeholder="Select product" />
                            </SelectTrigger>
                            <SelectContent>
                                {seedProducts.map((p) => (
                                    <SelectItem key={p.id} value={p.id}>
                                        {p.name}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="grid gap-1.5">
                        <Label>Objective</Label>
                        <Select
                            value={pack.objective}
                            onValueChange={(v) =>
                                onPatch({ objective: v as CampaignPack["objective"] })
                            }
                        >
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {[
                                    "Organic Product Test",
                                    "TikTok Shop Affiliate",
                                    "UGC Paid Asset",
                                    "Spark Ads Test",
                                    "POD Gift Campaign",
                                    "Dropshipping Product Demo",
                                ].map((o) => (
                                    <SelectItem key={o} value={o}>
                                        {o}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="grid gap-1.5">
                        <Label>Platform</Label>
                        <Select
                            value={pack.platform}
                            onValueChange={(v) =>
                                onPatch({ platform: v as CampaignPack["platform"] })
                            }
                        >
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {[
                                    "TikTok Shop",
                                    "TikTok Organic",
                                    "TikTok Spark Ads",
                                    "Meta UGC Ads",
                                ].map((p) => (
                                    <SelectItem key={p} value={p}>
                                        {p}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="grid gap-1.5">
                        <Label>Market</Label>
                        <Select
                            value={pack.market}
                            onValueChange={(v) => onPatch({ market: v as CampaignPack["market"] })}
                        >
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {["US", "UK", "CA", "AU", "DE"].map((m) => (
                                    <SelectItem key={m} value={m}>
                                        {m}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="grid gap-1.5">
                        <Label>Language</Label>
                        <Input
                            value={pack.language}
                            onChange={(e) => onPatch({ language: e.target.value })}
                        />
                    </div>
                    <div className="grid gap-1.5">
                        <Label>Creator type</Label>
                        <Select
                            value={pack.creatorType}
                            onValueChange={(v) =>
                                onPatch({ creatorType: v as CampaignPack["creatorType"] })
                            }
                        >
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {[
                                    "Micro creator",
                                    "Mid-tier creator",
                                    "UGC-only",
                                    "Product expert",
                                    "Lifestyle",
                                ].map((c) => (
                                    <SelectItem key={c} value={c}>
                                        {c}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="grid gap-1.5">
                        <Label>Creator tone</Label>
                        <Select
                            value={pack.creatorTone}
                            onValueChange={(v) =>
                                onPatch({ creatorTone: v as CampaignPack["creatorTone"] })
                            }
                        >
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {[
                                    "Natural",
                                    "Energetic",
                                    "Conversational",
                                    "Expert",
                                    "Emotional",
                                    "Minimal / Raw UGC",
                                ].map((t) => (
                                    <SelectItem key={t} value={t}>
                                        {t}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="grid gap-1.5 sm:col-span-2">
                        <Label>Buyer segment</Label>
                        <Input
                            value={pack.buyerSegment}
                            placeholder="e.g. Renters 25–35 with small kitchens"
                            onChange={(e) => onPatch({ buyerSegment: e.target.value })}
                        />
                    </div>
                </div>
            </SurfaceCard>
        </SectionShell>
    );
}

// References
function ReferencesStep({
    pack,
    onPatch,
}: {
    pack: CampaignPack;
    onPatch: WorkspaceLayoutProps["onPatch"];
}) {
    const creatives = useAppStore((s) => s.creatives);
    const analyses = useAppStore((s) => s.analyses);
    const [q, setQ] = useState("");
    const analyzed = creatives.filter((c) => c.analysisStatus === "analyzed" && !c.archived);
    const filtered = analyzed.filter(
        (c) =>
            !q ||
            c.title.toLowerCase().includes(q.toLowerCase()) ||
            c.angle.toLowerCase().includes(q.toLowerCase()),
    );
    const refs = pack.referenceCreativeIds;
    function toggle(id: string) {
        onPatch(
            {
                referenceCreativeIds: refs.includes(id)
                    ? refs.filter((r) => r !== id)
                    : refs.length >= 5
                      ? refs
                      : [...refs, id],
            },
            {
                campaignId: pack.id,
                kind: "reference-added",
                detail: `Reference ${refs.includes(id) ? "removed" : "added"}`,
            },
        );
    }
    function move(id: string, dir: -1 | 1) {
        const idx = refs.indexOf(id);
        if (idx < 0) return;
        const next = refs.slice();
        const swap = idx + dir;
        if (swap < 0 || swap >= next.length) return;
        [next[idx], next[swap]] = [next[swap], next[idx]];
        onPatch({ referenceCreativeIds: next });
    }
    return (
        <SectionShell
            title="References"
            description="Select up to 5 analyzed creatives. Order defines priority for adaptation."
        >
            {refs.length > 0 && (
                <SurfaceCard padding="md">
                    <p className="text-xs font-semibold uppercase text-text-tertiary">
                        Selected ({refs.length})
                    </p>
                    <ol className="mt-2 flex flex-col divide-y divide-hairline/60">
                        {refs.map((id, i) => {
                            const c = creatives.find((x) => x.id === id);
                            if (!c) return null;
                            return (
                                <li key={id} className="flex items-center gap-3 py-2">
                                    <span className="grid h-6 w-6 place-items-center rounded-full bg-primary-soft text-xs font-semibold text-primary-active">
                                        {i + 1}
                                    </span>
                                    <div className="min-w-0 flex-1">
                                        <p className="truncate text-sm font-medium text-text-primary">
                                            {c.title}
                                        </p>
                                        <p className="truncate text-xs text-text-secondary">
                                            {c.angle} · DNA {c.dnaScore}
                                        </p>
                                    </div>
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        onClick={() => move(id, -1)}
                                        disabled={i === 0}
                                    >
                                        ↑
                                    </Button>
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        onClick={() => move(id, 1)}
                                        disabled={i === refs.length - 1}
                                    >
                                        ↓
                                    </Button>
                                    <Button size="sm" variant="ghost" onClick={() => toggle(id)}>
                                        <Trash2 className="h-4 w-4" />
                                    </Button>
                                </li>
                            );
                        })}
                    </ol>
                </SurfaceCard>
            )}
            <SurfaceCard padding="md">
                <div className="mb-3 flex items-center gap-2">
                    <Input
                        placeholder="Search analyzed creatives…"
                        value={q}
                        onChange={(e) => setQ(e.target.value)}
                    />
                </div>
                {filtered.length === 0 ? (
                    <EmptyState
                        title="No analyzed creatives"
                        description="Analyze creatives in the Library first."
                        action={
                            <Button asChild variant="secondary">
                                <Link to="/creative-library" search={{ import: undefined }}>
                                    Open Creative Library
                                </Link>
                            </Button>
                        }
                    />
                ) : (
                    <div className="grid gap-2 sm:grid-cols-2">
                        {filtered.map((c) => {
                            const on = refs.includes(c.id);
                            const a = analyses[c.id];
                            return (
                                <button
                                    key={c.id}
                                    type="button"
                                    onClick={() => toggle(c.id)}
                                    className={`rounded-md border px-3 py-2 text-left transition-colors ${
                                        on
                                            ? "border-primary/40 bg-primary-soft"
                                            : "border-hairline/70 bg-surface hover:bg-surface-soft"
                                    }`}
                                >
                                    <p className="truncate text-sm font-medium text-text-primary">
                                        {c.title}
                                    </p>
                                    <p className="truncate text-xs text-text-secondary">
                                        {c.platform} · {c.angle} · DNA {c.dnaScore}
                                    </p>
                                    {a && (
                                        <p className="mt-0.5 truncate text-[11px] text-text-tertiary">
                                            {a.decision}
                                        </p>
                                    )}
                                </button>
                            );
                        })}
                    </div>
                )}
            </SurfaceCard>
        </SectionShell>
    );
}

// Adaptation
function AdaptationStep({
    pack,
    onPatch,
    campaignId,
}: {
    pack: CampaignPack;
    onPatch: WorkspaceLayoutProps["onPatch"];
    campaignId: string;
}) {
    const [busy, setBusy] = useState(false);
    const [variant, setVariant] = useState(0);
    const [sourceOpen, setSourceOpen] = useState(false);
    const sourceCreative = useAppStore((state) =>
        state.creatives.find((creative) => creative.id === pack.referenceCreativeIds[0]),
    );
    async function regenerate() {
        setBusy(true);
        const next = await generateAdaptation(
            pack.productId,
            pack.adaptation.sourceHook,
            variant + 1,
        );
        onPatch(
            { adaptation: { ...pack.adaptation, ...next } },
            { campaignId, kind: "adaptation-regenerated", detail: "Adaptation regenerated" },
        );
        setVariant(variant + 1);
        setBusy(false);
        toast.success("Adaptation regenerated");
    }
    return (
        <SectionShell
            title="Product Adaptation"
            description="See what to keep from the source, what to change, and what to avoid copying."
            actions={
                <div className="flex gap-2">
                    <Button
                        size="sm"
                        variant="secondary"
                        onClick={() =>
                            onPatch({
                                adaptation: { ...pack.adaptation, locked: !pack.adaptation.locked },
                            })
                        }
                    >
                        {pack.adaptation.locked ? (
                            <Unlock className="h-4 w-4" />
                        ) : (
                            <Lock className="h-4 w-4" />
                        )}
                        {pack.adaptation.locked ? "Unlock" : "Lock adaptation"}
                    </Button>
                    <Button
                        size="sm"
                        onClick={regenerate}
                        disabled={busy || pack.adaptation.locked}
                    >
                        <RefreshCw className={`h-4 w-4 ${busy ? "animate-spin" : ""}`} />
                        Regenerate
                    </Button>
                </div>
            }
        >
            <div className="grid gap-4 md:grid-cols-2">
                <SurfaceCard padding="none" className="overflow-hidden">
                    <button
                        type="button"
                        aria-expanded={sourceCreative ? sourceOpen : undefined}
                        disabled={!sourceCreative}
                        onClick={() => setSourceOpen((open) => !open)}
                        className="w-full p-5 text-left transition-colors duration-200 hover:bg-surface-soft/55 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring disabled:cursor-default disabled:hover:bg-transparent"
                    >
                        <span className="flex items-start justify-between gap-3">
                            <span className="min-w-0">
                                <span className="text-xs font-semibold uppercase text-text-tertiary">
                                    Source pattern
                                </span>
                                <span className="mt-2 block text-sm">
                                    <span className="font-medium">Hook:</span>{" "}
                                    {pack.adaptation.sourceHook || "—"}
                                </span>
                                <span className="mt-1 block text-sm">
                                    <span className="font-medium">Angle:</span>{" "}
                                    {pack.adaptation.sourceAngle}
                                </span>
                                <span className="mt-1 block text-sm">
                                    <span className="font-medium">Demo:</span>{" "}
                                    {pack.adaptation.sourceDemo}
                                </span>
                            </span>
                            {sourceCreative ? (
                                <ChevronDown
                                    className={cn(
                                        "mt-0.5 h-4 w-4 shrink-0 text-text-tertiary transition-transform duration-200",
                                        sourceOpen && "rotate-180",
                                    )}
                                />
                            ) : (
                                <span className="shrink-0 text-[10px] font-medium uppercase text-text-tertiary">
                                    No linked media
                                </span>
                            )}
                        </span>
                    </button>
                    {sourceOpen && sourceCreative && (
                        <div className="analysis-state-enter border-t border-hairline p-4">
                            <DemoMediaTile
                                mediaUrl={sourceCreative.mediaUrl}
                                mediaKind={sourceCreative.mediaKind}
                                posterUrl={sourceCreative.posterUrl}
                                seed={sourceCreative.thumbSeed}
                                label={sourceCreative.title}
                                badges={[
                                    sourceCreative.platform,
                                    sourceCreative.mediaAspectRatio ?? "reference",
                                ]}
                                aspect="16 / 9"
                                fit={
                                    sourceCreative.mediaAspectRatio === "9:16" ? "contain" : "cover"
                                }
                                className="rounded-md bg-black"
                            />
                            <Button asChild size="sm" variant="secondary" className="mt-3">
                                <Link
                                    to="/creative-library/$creativeId"
                                    params={{ creativeId: sourceCreative.id }}
                                >
                                    Open source evidence
                                    <ExternalLink className="h-3.5 w-3.5" />
                                </Link>
                            </Button>
                        </div>
                    )}
                </SurfaceCard>
                <SurfaceCard padding="md" className="bg-primary-soft/30">
                    <p className="text-xs font-semibold uppercase text-primary-active">
                        Adapted for product
                    </p>
                    <p className="mt-2 text-sm">
                        <span className="font-medium">Hook:</span> {pack.adaptation.adaptedHook}
                    </p>
                    <p className="mt-1 text-sm">
                        <span className="font-medium">Angle:</span> {pack.adaptation.adaptedAngle}
                    </p>
                    <p className="mt-1 text-sm">
                        <span className="font-medium">Demo:</span> {pack.adaptation.adaptedDemo}
                    </p>
                </SurfaceCard>
            </div>
            <SurfaceCard padding="md">
                <p className="text-xs font-semibold uppercase text-text-tertiary">
                    Why this changed
                </p>
                <p className="mt-1 text-sm text-text-secondary">{pack.adaptation.whyChanged}</p>
            </SurfaceCard>
            <div className="grid gap-4 md:grid-cols-3">
                {(["keep", "change", "avoid"] as const).map((key) => (
                    <SurfaceCard key={key} padding="md">
                        <p
                            className={`text-xs font-semibold uppercase ${key === "keep" ? "text-ok" : key === "change" ? "text-info" : "text-warn"}`}
                        >
                            {key === "keep"
                                ? "Keep"
                                : key === "change"
                                  ? "Change"
                                  : "Avoid copying"}
                        </p>
                        <ul className="mt-2 space-y-1 text-sm text-text-secondary">
                            {pack.adaptation[key].map((x, i) => (
                                <li key={i}>• {x}</li>
                            ))}
                        </ul>
                    </SurfaceCard>
                ))}
            </div>
            <SurfaceCard padding="md">
                <Label
                    htmlFor="notes"
                    className="text-xs font-semibold uppercase text-text-tertiary"
                >
                    Adaptation notes
                </Label>
                <Textarea
                    id="notes"
                    className="mt-2"
                    rows={3}
                    value={pack.adaptation.notes}
                    onChange={(e) =>
                        onPatch({ adaptation: { ...pack.adaptation, notes: e.target.value } })
                    }
                    placeholder="Anything specific to instruct the creator or your team."
                />
            </SurfaceCard>
        </SectionShell>
    );
}

// Angles
function AnglesStep({
    pack,
    onPatch,
    campaignId,
}: {
    pack: CampaignPack;
    onPatch: WorkspaceLayoutProps["onPatch"];
    campaignId: string;
}) {
    const [busy, setBusy] = useState(false);
    const [pendingPrimaryId, setPendingPrimaryId] = useState<string | null>(null);
    async function generate() {
        setBusy(true);
        const next = await generateAngles(pack.productId, pack.id);
        onPatch(
            { angleOptions: next, primaryAngleId: next[0]?.id, secondaryAngleIds: [] },
            { campaignId, kind: "angle-changed", detail: "Angles generated" },
        );
        setBusy(false);
    }
    async function addOne() {
        setBusy(true);
        const one = await generateOneAngle(pack.productId, pack.angleOptions, pack.id);
        onPatch({ angleOptions: [...pack.angleOptions, one] });
        setBusy(false);
    }
    function setPrimary(id: string) {
        if (pack.primaryAngleId === id) return;
        const hasEdits = pack.hookOptions.length > 0 || pack.script.length > 0;
        if (hasEdits) {
            setPendingPrimaryId(id);
            return;
        }
        applyPrimary(id, true);
    }
    function applyPrimary(id: string, keepExisting: boolean) {
        onPatch(
            keepExisting
                ? { primaryAngleId: id }
                : {
                      primaryAngleId: id,
                      hookOptions: [],
                      selectedHookIds: [],
                      script: [],
                      storyboard: [],
                  },
            {
                campaignId,
                kind: "angle-changed",
                detail: keepExisting
                    ? "Primary angle changed"
                    : "Primary angle changed — refreshed sections",
            },
        );
        if (!keepExisting) toast("Refreshed downstream sections");
        setPendingPrimaryId(null);
    }
    function toggleSecondary(id: string) {
        const on = pack.secondaryAngleIds.includes(id);
        onPatch({
            secondaryAngleIds: on
                ? pack.secondaryAngleIds.filter((x) => x !== id)
                : [...pack.secondaryAngleIds, id],
        });
    }
    function archiveAngle(a: AngleConcept) {
        onPatch({
            angleOptions: pack.angleOptions.map((x) =>
                x.id === a.id ? { ...x, archived: true } : x,
            ),
        });
    }
    return (
        <SectionShell
            title="Angles"
            description="Choose the primary angle. Optionally test secondary angles with additional creators."
            actions={
                <div className="flex gap-2">
                    <Button size="sm" variant="secondary" onClick={addOne} disabled={busy}>
                        <Plus className="h-4 w-4" /> Add angle
                    </Button>
                    <Button size="sm" onClick={generate} disabled={busy}>
                        <Sparkles className="h-4 w-4" />{" "}
                        {pack.angleOptions.length ? "Regenerate all" : "Generate"}
                    </Button>
                </div>
            }
        >
            {pack.angleOptions.length === 0 ? (
                <SurfaceCard padding="lg">
                    <EmptyState
                        title="No angles yet"
                        description="Generate angle concepts from your references and product context."
                        action={
                            <Button onClick={generate} disabled={busy}>
                                <Sparkles className="h-4 w-4" />
                                Generate angles
                            </Button>
                        }
                    />
                </SurfaceCard>
            ) : (
                <div className="grid gap-3 md:grid-cols-2">
                    {pack.angleOptions
                        .filter((a) => !a.archived)
                        .map((a) => {
                            const primary = a.id === pack.primaryAngleId;
                            const secondary = pack.secondaryAngleIds.includes(a.id);
                            return (
                                <SurfaceCard
                                    key={a.id}
                                    padding="md"
                                    className={primary ? "ring-1 ring-primary/40" : ""}
                                >
                                    <div className="flex items-start justify-between gap-2">
                                        <div className="min-w-0">
                                            <p className="text-sm font-semibold text-text-primary">
                                                {a.name}
                                            </p>
                                            <StatusChip
                                                tone={
                                                    a.fit === "Strong fit"
                                                        ? "ok"
                                                        : a.fit === "Good test"
                                                          ? "info"
                                                          : "warn"
                                                }
                                                className="mt-1"
                                            >
                                                {a.fit}
                                            </StatusChip>
                                        </div>
                                        <Button
                                            size="sm"
                                            variant="ghost"
                                            onClick={() => archiveAngle(a)}
                                        >
                                            <Trash2 className="h-4 w-4" />
                                        </Button>
                                    </div>
                                    <p className="mt-2 text-xs text-text-secondary">
                                        {a.buyerProblem}
                                    </p>
                                    <p className="mt-1 text-xs text-text-secondary">
                                        <span className="font-medium">Trigger:</span>{" "}
                                        {a.emotionalTrigger}
                                    </p>
                                    <p className="mt-1 text-xs text-text-secondary">
                                        <span className="font-medium">Proof:</span> {a.productProof}
                                    </p>
                                    <p className="mt-1 text-[11px] text-text-tertiary">
                                        {a.reason}
                                    </p>
                                    <div className="mt-3 flex flex-wrap gap-2">
                                        <Button
                                            size="sm"
                                            variant={primary ? "default" : "secondary"}
                                            onClick={() => setPrimary(a.id)}
                                        >
                                            {primary ? "Primary" : "Set as primary"}
                                        </Button>
                                        {!primary && (
                                            <Button
                                                size="sm"
                                                variant="ghost"
                                                onClick={() => toggleSecondary(a.id)}
                                            >
                                                {secondary ? "Remove from test" : "Add as test"}
                                            </Button>
                                        )}
                                    </div>
                                </SurfaceCard>
                            );
                        })}
                </div>
            )}
            <AlertDialog
                open={!!pendingPrimaryId}
                onOpenChange={(open) => {
                    if (!open) setPendingPrimaryId(null);
                }}
            >
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Change the primary angle?</AlertDialogTitle>
                        <AlertDialogDescription>
                            Existing hooks and script may no longer match this direction. Choose
                            whether to keep them or refresh the downstream sections.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel
                            onClick={() => {
                                if (pendingPrimaryId) applyPrimary(pendingPrimaryId, false);
                            }}
                        >
                            Change and refresh
                        </AlertDialogCancel>
                        <AlertDialogAction
                            onClick={() => {
                                if (pendingPrimaryId) applyPrimary(pendingPrimaryId, true);
                            }}
                        >
                            Keep existing content
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </SectionShell>
    );
}

// Hooks
function HooksStep({
    pack,
    onPatch,
    campaignId,
}: {
    pack: CampaignPack;
    onPatch: WorkspaceLayoutProps["onPatch"];
    campaignId: string;
}) {
    const [busy, setBusy] = useState(false);
    const angle = pack.angleOptions.find((a) => a.id === pack.primaryAngleId);
    async function generate() {
        setBusy(true);
        const next = await generateHooks(pack.productId, angle, pack.id);
        onPatch(
            { hookOptions: next, selectedHookIds: next.slice(0, 1).map((h) => h.id) },
            { campaignId, kind: "hook-selected", detail: "Hooks generated" },
        );
        setBusy(false);
    }
    function toggle(id: string) {
        const on = pack.selectedHookIds.includes(id);
        if (!on && pack.selectedHookIds.length >= 3) {
            toast("Select up to 3 primary hooks");
            return;
        }
        onPatch(
            {
                selectedHookIds: on
                    ? pack.selectedHookIds.filter((x) => x !== id)
                    : [...pack.selectedHookIds, id],
            },
            { campaignId, kind: "hook-selected", detail: on ? "Hook deselected" : "Hook selected" },
        );
    }
    async function regenerateOne(h: Hook) {
        setBusy(true);
        const next = await generateOneHook(pack.productId, h.type, pack.hookOptions, pack.id);
        onPatch({ hookOptions: pack.hookOptions.map((x) => (x.id === h.id ? next : x)) });
        setBusy(false);
    }
    function updateHook(id: string, patch: Partial<Hook>) {
        onPatch({
            hookOptions: pack.hookOptions.map((x) => (x.id === id ? { ...x, ...patch } : x)),
        });
    }
    function addManual(type: HookType) {
        const newH: Hook = {
            id: `h-${Date.now()}`,
            text: "New manual hook",
            type,
            creatorStyle: "Talking head",
            fit: "Good test",
            manual: true,
        };
        onPatch({ hookOptions: [...pack.hookOptions, newH] });
    }
    function remove(id: string) {
        onPatch({
            hookOptions: pack.hookOptions.filter((x) => x.id !== id),
            selectedHookIds: pack.selectedHookIds.filter((x) => x !== id),
        });
    }
    const grouped = useMemo(() => {
        const g: Record<string, Hook[]> = {};
        pack.hookOptions.forEach((h) => {
            (g[h.type] ??= []).push(h);
        });
        return g;
    }, [pack.hookOptions]);
    const selectedHooks = pack.hookOptions.filter((h) => pack.selectedHookIds.includes(h.id));

    return (
        <SectionShell
            title="Hooks"
            description="Pick up to 3 primary hooks. You can edit each hook inline."
            actions={
                <Button size="sm" onClick={generate} disabled={busy}>
                    <Sparkles className="h-4 w-4" />{" "}
                    {pack.hookOptions.length ? "Regenerate all" : "Generate"}
                </Button>
            }
        >
            {selectedHooks.length > 0 && (
                <SurfaceCard padding="md" className="bg-primary-soft/30">
                    <p className="text-xs font-semibold uppercase text-primary-active">
                        Selected hooks
                    </p>
                    <ol className="mt-2 list-decimal space-y-0.5 pl-5 text-sm">
                        {selectedHooks.map((h) => (
                            <li key={h.id}>{h.text}</li>
                        ))}
                    </ol>
                </SurfaceCard>
            )}
            {pack.hookOptions.length === 0 ? (
                <SurfaceCard padding="lg">
                    <EmptyState
                        title="No hooks yet"
                        description="Generate hooks from your primary angle."
                        action={
                            <Button onClick={generate} disabled={busy}>
                                <Sparkles className="h-4 w-4" />
                                Generate hooks
                            </Button>
                        }
                    />
                </SurfaceCard>
            ) : (
                <div className="flex flex-col gap-3">
                    {Object.entries(grouped).map(([type, hooks]) => (
                        <SurfaceCard key={type} padding="md">
                            <div className="flex items-center justify-between">
                                <p className="text-xs font-semibold uppercase text-text-tertiary">
                                    {type}
                                </p>
                                <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => addManual(type as HookType)}
                                >
                                    <Plus className="h-4 w-4" /> Add
                                </Button>
                            </div>
                            <ul className="mt-2 flex flex-col divide-y divide-hairline/60">
                                {hooks.map((h) => {
                                    const on = pack.selectedHookIds.includes(h.id);
                                    return (
                                        <li
                                            key={h.id}
                                            className="flex flex-wrap items-center gap-2 py-2"
                                        >
                                            <Checkbox
                                                checked={on}
                                                onCheckedChange={() => toggle(h.id)}
                                                aria-label="Select hook"
                                            />
                                            <Input
                                                className="flex-1 min-w-[220px]"
                                                value={h.text}
                                                onChange={(e) =>
                                                    updateHook(h.id, { text: e.target.value })
                                                }
                                            />
                                            <StatusChip
                                                tone={
                                                    h.fit === "Strong fit"
                                                        ? "ok"
                                                        : h.fit === "Good test"
                                                          ? "info"
                                                          : "warn"
                                                }
                                            >
                                                {h.fit}
                                            </StatusChip>
                                            {h.riskFlag && (
                                                <StatusChip tone="warn">Risk</StatusChip>
                                            )}
                                            <Button
                                                size="sm"
                                                variant="ghost"
                                                onClick={() => regenerateOne(h)}
                                            >
                                                <RefreshCw className="h-4 w-4" />
                                            </Button>
                                            <Button
                                                size="sm"
                                                variant="ghost"
                                                onClick={() =>
                                                    navigator.clipboard
                                                        ?.writeText(h.text)
                                                        .then(() => toast.success("Copied"))
                                                }
                                            >
                                                <Copy className="h-4 w-4" />
                                            </Button>
                                            <Button
                                                size="sm"
                                                variant="ghost"
                                                onClick={() => remove(h.id)}
                                            >
                                                <Trash2 className="h-4 w-4" />
                                            </Button>
                                        </li>
                                    );
                                })}
                            </ul>
                        </SurfaceCard>
                    ))}
                </div>
            )}
        </SectionShell>
    );
}

// Script
function ScriptStep({
    pack,
    onPatch,
    campaignId,
}: {
    pack: CampaignPack;
    onPatch: WorkspaceLayoutProps["onPatch"];
    campaignId: string;
}) {
    const [busy, setBusy] = useState(false);
    const angle = pack.angleOptions.find((a) => a.id === pack.primaryAngleId);
    const firstHook = pack.hookOptions.find((h) => pack.selectedHookIds.includes(h.id));
    async function generate() {
        setBusy(true);
        const next = await generateScript(pack.productId, angle, firstHook, pack.id);
        onPatch(
            { script: next },
            { campaignId, kind: "script-updated", detail: "Script generated" },
        );
        setBusy(false);
    }
    async function regenerateOne(b: ScriptBlock) {
        if (b.locked) return;
        setBusy(true);
        const next = await regenerateScriptSection(pack.productId, b, pack.id);
        onPatch(
            { script: pack.script.map((x) => (x.id === b.id ? next : x)) },
            { campaignId, kind: "script-updated", detail: `${b.kind} regenerated` },
        );
        setBusy(false);
    }
    function updateBlock(id: string, patch: Partial<ScriptBlock>) {
        onPatch({ script: pack.script.map((x) => (x.id === id ? { ...x, ...patch } : x)) });
    }
    function move(id: string, dir: -1 | 1) {
        const idx = pack.script.findIndex((b) => b.id === id);
        const next = pack.script.slice();
        const swap = idx + dir;
        if (swap < 0 || swap >= next.length) return;
        [next[idx], next[swap]] = [next[swap], next[idx]];
        onPatch({ script: next });
    }
    const wordCount = pack.script.reduce(
        (s, b) => s + b.text.split(/\s+/).filter(Boolean).length,
        0,
    );
    const estSec = Math.round(wordCount / 2.6);
    return (
        <SectionShell
            title="Script"
            description="Structured script blocks. Regenerate one section at a time — locked blocks are preserved."
            actions={
                <Button size="sm" onClick={generate} disabled={busy}>
                    <Sparkles className="h-4 w-4" />{" "}
                    {pack.script.length ? "Regenerate all" : "Generate"}
                </Button>
            }
        >
            {pack.script.length === 0 ? (
                <SurfaceCard padding="lg">
                    <EmptyState
                        title="No script yet"
                        description="Generate a starting script from the primary angle and selected hook."
                        action={
                            <Button onClick={generate} disabled={busy}>
                                <Sparkles className="h-4 w-4" />
                                Generate script
                            </Button>
                        }
                    />
                </SurfaceCard>
            ) : (
                <div className="flex flex-col gap-3">
                    <SurfaceCard
                        padding="sm"
                        className="flex flex-wrap items-center justify-between gap-3"
                    >
                        <p className="text-xs text-text-secondary">
                            Estimated read time:{" "}
                            <span className="tabular font-medium">~{estSec}s</span> ({wordCount}{" "}
                            words)
                            {estSec > pack.deliverables.targetDurationSec + 10 && (
                                <span className="ml-2 text-warn">
                                    · longer than target {pack.deliverables.targetDurationSec}s
                                </span>
                            )}
                        </p>
                    </SurfaceCard>
                    {pack.script.map((b, i) => (
                        <SurfaceCard key={b.id} padding="md">
                            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                                <div className="flex items-center gap-2">
                                    <StatusChip tone="neutral">{b.kind}</StatusChip>
                                    {b.locked && <StatusChip tone="warn">Locked</StatusChip>}
                                </div>
                                <div className="flex items-center gap-1">
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        onClick={() => move(b.id, -1)}
                                        disabled={i === 0}
                                    >
                                        ↑
                                    </Button>
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        onClick={() => move(b.id, 1)}
                                        disabled={i === pack.script.length - 1}
                                    >
                                        ↓
                                    </Button>
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        onClick={() => updateBlock(b.id, { locked: !b.locked })}
                                    >
                                        {b.locked ? (
                                            <Unlock className="h-4 w-4" />
                                        ) : (
                                            <Lock className="h-4 w-4" />
                                        )}
                                    </Button>
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        onClick={() => regenerateOne(b)}
                                        disabled={b.locked || busy}
                                    >
                                        <RefreshCw className="h-4 w-4" />
                                    </Button>
                                </div>
                            </div>
                            <Textarea
                                rows={3}
                                value={b.text}
                                onChange={(e) => updateBlock(b.id, { text: e.target.value })}
                                readOnly={b.locked}
                            />
                            <Input
                                className="mt-2"
                                placeholder="Note (optional)"
                                value={b.note ?? ""}
                                onChange={(e) => updateBlock(b.id, { note: e.target.value })}
                            />
                        </SurfaceCard>
                    ))}
                </div>
            )}
        </SectionShell>
    );
}

// Storyboard
function StoryboardStep({
    pack,
    onPatch,
    campaignId,
}: {
    pack: CampaignPack;
    onPatch: WorkspaceLayoutProps["onPatch"];
    campaignId: string;
}) {
    const [busy, setBusy] = useState(false);
    async function generate() {
        setBusy(true);
        const next = await generateStoryboard(pack.productId, pack.id);
        onPatch(
            { storyboard: next },
            { campaignId, kind: "scene-regenerated", detail: "Storyboard generated" },
        );
        setBusy(false);
    }
    async function regenerateOne(s: StoryboardScene) {
        setBusy(true);
        const next = await regenerateStoryboardScene(s, pack.id);
        onPatch(
            { storyboard: pack.storyboard.map((x) => (x.id === s.id ? next : x)) },
            { campaignId, kind: "scene-regenerated", detail: `${s.label} regenerated` },
        );
        setBusy(false);
    }
    function update(id: string, patch: Partial<StoryboardScene>) {
        onPatch({ storyboard: pack.storyboard.map((x) => (x.id === id ? { ...x, ...patch } : x)) });
    }
    function move(id: string, dir: -1 | 1) {
        const idx = pack.storyboard.findIndex((b) => b.id === id);
        const next = pack.storyboard.slice();
        const swap = idx + dir;
        if (swap < 0 || swap >= next.length) return;
        [next[idx], next[swap]] = [next[swap], next[idx]];
        onPatch({ storyboard: next });
    }
    function add() {
        onPatch({
            storyboard: [
                ...pack.storyboard,
                {
                    id: `sc-${Date.now()}`,
                    label: "New scene",
                    durationRange: "3–5s",
                    visualDirection: "Describe the shot",
                    spokenLine: "",
                    productVisibility: "Contextual",
                    framing: "",
                },
            ],
        });
    }
    function remove(id: string) {
        onPatch({ storyboard: pack.storyboard.filter((x) => x.id !== id) });
    }
    return (
        <SectionShell
            title="Storyboard"
            description="Scene-by-scene shooting plan the creator will follow."
            actions={
                <div className="flex gap-2">
                    <Button size="sm" variant="secondary" onClick={add}>
                        <Plus className="h-4 w-4" /> Add scene
                    </Button>
                    <Button size="sm" onClick={generate} disabled={busy}>
                        <Sparkles className="h-4 w-4" />{" "}
                        {pack.storyboard.length ? "Regenerate all" : "Generate"}
                    </Button>
                </div>
            }
        >
            {pack.storyboard.length === 0 ? (
                <SurfaceCard padding="lg">
                    <EmptyState
                        title="No storyboard yet"
                        description="Generate a starting storyboard aligned to your script."
                        action={
                            <Button onClick={generate} disabled={busy}>
                                <Sparkles className="h-4 w-4" />
                                Generate storyboard
                            </Button>
                        }
                    />
                </SurfaceCard>
            ) : (
                <div className="flex flex-col gap-3">
                    {pack.storyboard.map((s, i) => (
                        <SurfaceCard key={s.id} padding="md">
                            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                                <div className="flex items-center gap-2">
                                    <span className="grid h-6 w-6 place-items-center rounded-full bg-primary-soft text-xs font-semibold text-primary-active">
                                        {i + 1}
                                    </span>
                                    <Input
                                        className="h-7 w-[180px]"
                                        value={s.label}
                                        onChange={(e) => update(s.id, { label: e.target.value })}
                                    />
                                    {s.mustShow && <StatusChip tone="ok">Must show</StatusChip>}
                                </div>
                                <div className="flex items-center gap-1">
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        onClick={() => move(s.id, -1)}
                                        disabled={i === 0}
                                    >
                                        ↑
                                    </Button>
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        onClick={() => move(s.id, 1)}
                                        disabled={i === pack.storyboard.length - 1}
                                    >
                                        ↓
                                    </Button>
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        onClick={() => update(s.id, { mustShow: !s.mustShow })}
                                    >
                                        <Check className="h-4 w-4" />
                                    </Button>
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        onClick={() => regenerateOne(s)}
                                        disabled={busy}
                                    >
                                        <RefreshCw className="h-4 w-4" />
                                    </Button>
                                    <Button size="sm" variant="ghost" onClick={() => remove(s.id)}>
                                        <Trash2 className="h-4 w-4" />
                                    </Button>
                                </div>
                            </div>
                            <div className="grid gap-2 sm:grid-cols-2">
                                <div>
                                    <Label className="text-[11px] uppercase text-text-tertiary">
                                        Duration
                                    </Label>
                                    <Input
                                        value={s.durationRange}
                                        onChange={(e) =>
                                            update(s.id, { durationRange: e.target.value })
                                        }
                                    />
                                </div>
                                <div>
                                    <Label className="text-[11px] uppercase text-text-tertiary">
                                        Framing
                                    </Label>
                                    <Input
                                        value={s.framing}
                                        onChange={(e) => update(s.id, { framing: e.target.value })}
                                    />
                                </div>
                                <div className="sm:col-span-2">
                                    <Label className="text-[11px] uppercase text-text-tertiary">
                                        Visual direction
                                    </Label>
                                    <Textarea
                                        rows={2}
                                        value={s.visualDirection}
                                        onChange={(e) =>
                                            update(s.id, { visualDirection: e.target.value })
                                        }
                                    />
                                </div>
                                <div className="sm:col-span-2">
                                    <Label className="text-[11px] uppercase text-text-tertiary">
                                        Spoken line
                                    </Label>
                                    <Textarea
                                        rows={2}
                                        value={s.spokenLine}
                                        onChange={(e) =>
                                            update(s.id, { spokenLine: e.target.value })
                                        }
                                    />
                                </div>
                                <div>
                                    <Label className="text-[11px] uppercase text-text-tertiary">
                                        On-screen text
                                    </Label>
                                    <Input
                                        value={s.onScreenText ?? ""}
                                        onChange={(e) =>
                                            update(s.id, { onScreenText: e.target.value })
                                        }
                                    />
                                </div>
                                <div>
                                    <Label className="text-[11px] uppercase text-text-tertiary">
                                        Product visibility
                                    </Label>
                                    <Select
                                        value={s.productVisibility}
                                        onValueChange={(v) =>
                                            update(s.id, {
                                                productVisibility:
                                                    v as StoryboardScene["productVisibility"],
                                            })
                                        }
                                    >
                                        <SelectTrigger>
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {(["Prominent", "Contextual", "Absent"] as const).map(
                                                (v) => (
                                                    <SelectItem key={v} value={v}>
                                                        {v}
                                                    </SelectItem>
                                                ),
                                            )}
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>
                        </SurfaceCard>
                    ))}
                </div>
            )}
        </SectionShell>
    );
}

// CTA & Claims
function CtaStep({
    pack,
    onPatch,
    onReviewWarning,
}: {
    pack: CampaignPack;
    onPatch: WorkspaceLayoutProps["onPatch"];
    onReviewWarning: (id: string) => void;
}) {
    function setCta(patch: Partial<typeof pack.cta>) {
        onPatch({ cta: { ...pack.cta, ...patch } });
    }
    function scanClaims() {
        const text = [
            pack.script.map((b) => b.text).join(" "),
            pack.cta.offerStatement,
            pack.cta.shipping,
            ...pack.cta.claimsAllowed,
        ].join(" ");
        const warnings = checkClaims(text);
        setCta({ warnings });
        toast(warnings.length ? `${warnings.length} claim warning(s)` : "No claim risks detected");
    }
    return (
        <SectionShell
            title="CTA & Claims"
            description="Set the call to action, review claim risks, and mark warnings you've reviewed."
            actions={
                <Button size="sm" variant="secondary" onClick={scanClaims}>
                    <AlertTriangle className="h-4 w-4" />
                    Scan for risks
                </Button>
            }
        >
            <SurfaceCard padding="md" className="flex flex-col gap-3">
                <div className="grid gap-1.5">
                    <Label>Primary CTA</Label>
                    <Input
                        value={pack.cta.primary}
                        onChange={(e) => setCta({ primary: e.target.value })}
                    />
                </div>
                <div className="grid gap-1.5">
                    <Label>Product tag instruction</Label>
                    <Input
                        value={pack.cta.productTagInstruction}
                        onChange={(e) => setCta({ productTagInstruction: e.target.value })}
                    />
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                    <div className="grid gap-1.5">
                        <Label>Offer statement</Label>
                        <Input
                            value={pack.cta.offerStatement}
                            onChange={(e) => setCta({ offerStatement: e.target.value })}
                        />
                    </div>
                    <div className="grid gap-1.5">
                        <Label>Coupon (optional)</Label>
                        <Input
                            value={pack.cta.coupon}
                            onChange={(e) => setCta({ coupon: e.target.value })}
                        />
                    </div>
                    <div className="grid gap-1.5">
                        <Label>Shipping statement</Label>
                        <Input
                            value={pack.cta.shipping}
                            onChange={(e) => setCta({ shipping: e.target.value })}
                        />
                    </div>
                    <div className="grid gap-1.5">
                        <Label>Product limitations</Label>
                        <Input
                            value={pack.cta.productLimitations}
                            onChange={(e) => setCta({ productLimitations: e.target.value })}
                        />
                    </div>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                    <div className="grid gap-1.5">
                        <Label>Claims allowed (one per line)</Label>
                        <Textarea
                            rows={4}
                            value={pack.cta.claimsAllowed.join("\n")}
                            onChange={(e) =>
                                setCta({
                                    claimsAllowed: e.target.value.split("\n").filter(Boolean),
                                })
                            }
                        />
                    </div>
                    <div className="grid gap-1.5">
                        <Label>Claims to avoid (one per line)</Label>
                        <Textarea
                            rows={4}
                            value={pack.cta.claimsToAvoid.join("\n")}
                            onChange={(e) =>
                                setCta({
                                    claimsToAvoid: e.target.value.split("\n").filter(Boolean),
                                })
                            }
                        />
                    </div>
                </div>
                <div className="grid gap-1.5">
                    <Label>Compliance notes</Label>
                    <Textarea
                        rows={2}
                        value={pack.cta.complianceNotes}
                        onChange={(e) => setCta({ complianceNotes: e.target.value })}
                    />
                </div>
            </SurfaceCard>

            {pack.cta.warnings.length > 0 && (
                <SurfaceCard padding="md">
                    <p className="text-xs font-semibold uppercase text-warn">Claim warnings</p>
                    <ul className="mt-2 flex flex-col divide-y divide-hairline/60">
                        {pack.cta.warnings.map((w) => {
                            const reviewed = pack.reviewedWarningIds.includes(w.id);
                            return (
                                <li key={w.id} className="flex flex-wrap items-center gap-3 py-2">
                                    <StatusChip tone={w.risk === "High" ? "destructive" : "warn"}>
                                        {w.risk} risk
                                    </StatusChip>
                                    <div className="min-w-0 flex-1">
                                        <p className="truncate text-sm text-text-primary">
                                            “{w.phrase}”
                                        </p>
                                        <p className="truncate text-xs text-text-secondary">
                                            {w.reason}
                                        </p>
                                    </div>
                                    <Button
                                        size="sm"
                                        variant={reviewed ? "ghost" : "secondary"}
                                        onClick={() => onReviewWarning(w.id)}
                                        disabled={reviewed}
                                    >
                                        {reviewed ? "Reviewed" : "Mark reviewed"}
                                    </Button>
                                </li>
                            );
                        })}
                    </ul>
                    <p className="mt-2 text-[11px] text-text-tertiary">
                        Warnings are heuristic. Viraldy does not provide legal approval — review
                        before publishing.
                    </p>
                </SurfaceCard>
            )}
        </SectionShell>
    );
}

// Deliverables & Rights
function DeliverablesStep({
    pack,
    onPatch,
}: {
    pack: CampaignPack;
    onPatch: WorkspaceLayoutProps["onPatch"];
}) {
    function setD(patch: Partial<typeof pack.deliverables>) {
        onPatch({ deliverables: { ...pack.deliverables, ...patch } });
    }
    function setR(patch: Partial<typeof pack.rights>) {
        onPatch({ rights: { ...pack.rights, ...patch } });
    }
    function setS(patch: Partial<typeof pack.spark>) {
        onPatch({ spark: { ...pack.spark, ...patch } });
    }
    return (
        <SectionShell
            title="Deliverables & Rights"
            description="What the creator delivers and how you can use it."
        >
            <div className="grid gap-4 md:grid-cols-2">
                <SurfaceCard padding="md" className="flex flex-col gap-3">
                    <p className="text-xs font-semibold uppercase text-text-tertiary">
                        Deliverables
                    </p>
                    <div className="grid gap-3 sm:grid-cols-2">
                        <div className="grid gap-1.5">
                            <Label># of videos</Label>
                            <Input
                                type="number"
                                min={1}
                                value={pack.deliverables.numberOfVideos}
                                onChange={(e) =>
                                    setD({ numberOfVideos: Math.max(1, +e.target.value) })
                                }
                            />
                        </div>
                        <div className="grid gap-1.5">
                            <Label>Target duration (s)</Label>
                            <Input
                                type="number"
                                min={5}
                                value={pack.deliverables.targetDurationSec}
                                onChange={(e) =>
                                    setD({ targetDurationSec: Math.max(5, +e.target.value) })
                                }
                            />
                        </div>
                        <div className="grid gap-1.5">
                            <Label>Aspect ratio</Label>
                            <Select
                                value={pack.deliverables.aspectRatio}
                                onValueChange={(v) =>
                                    setD({ aspectRatio: v as typeof pack.deliverables.aspectRatio })
                                }
                            >
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {(["9:16", "1:1", "4:5", "16:9"] as const).map((v) => (
                                        <SelectItem key={v} value={v}>
                                            {v}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="grid gap-1.5">
                            <Label>Revisions</Label>
                            <Input
                                type="number"
                                min={0}
                                value={pack.deliverables.revisionRounds}
                                onChange={(e) =>
                                    setD({ revisionRounds: Math.max(0, +e.target.value) })
                                }
                            />
                        </div>
                        <div className="grid gap-1.5">
                            <Label>Due date</Label>
                            <Input
                                type="date"
                                value={pack.deliverables.dueDate?.slice(0, 10) ?? ""}
                                onChange={(e) => setD({ dueDate: e.target.value })}
                            />
                        </div>
                    </div>
                    <div className="flex flex-wrap gap-3 pt-1">
                        <label className="flex items-center gap-2 text-sm">
                            <Checkbox
                                checked={pack.deliverables.rawFootageRequired}
                                onCheckedChange={(v) => setD({ rawFootageRequired: !!v })}
                            />
                            Raw footage required
                        </label>
                        <label className="flex items-center gap-2 text-sm">
                            <Checkbox
                                checked={pack.deliverables.captionRequired}
                                onCheckedChange={(v) => setD({ captionRequired: !!v })}
                            />
                            Caption required
                        </label>
                        <label className="flex items-center gap-2 text-sm">
                            <Checkbox
                                checked={pack.deliverables.productTagRequired}
                                onCheckedChange={(v) => setD({ productTagRequired: !!v })}
                            />
                            Product tag required
                        </label>
                    </div>
                </SurfaceCard>

                <SurfaceCard padding="md" className="flex flex-col gap-3">
                    <p className="text-xs font-semibold uppercase text-text-tertiary">
                        Usage rights
                    </p>
                    <div className="grid gap-2">
                        {(
                            [
                                ["tiktokOrganic", "TikTok Organic"],
                                ["tiktokSpark", "TikTok Spark Ads"],
                                ["metaAds", "Meta Ads"],
                                ["website", "Website"],
                                ["email", "Email"],
                                ["editingAllowed", "Editing allowed"],
                                ["rawFootageIncluded", "Raw footage included"],
                                ["creatorAttribution", "Creator attribution"],
                            ] as const
                        ).map(([k, label]) => (
                            <label key={k} className="flex items-center gap-2 text-sm">
                                <Checkbox
                                    checked={pack.rights[k]}
                                    onCheckedChange={(v) =>
                                        setR({ [k]: !!v } as Partial<typeof pack.rights>)
                                    }
                                />
                                {label}
                            </label>
                        ))}
                    </div>
                    <div className="grid gap-1.5">
                        <Label>Usage duration (days)</Label>
                        <Input
                            type="number"
                            min={0}
                            value={pack.rights.usageDurationDays}
                            onChange={(e) =>
                                setR({ usageDurationDays: Math.max(0, +e.target.value) })
                            }
                        />
                    </div>
                </SurfaceCard>
            </div>
            <SurfaceCard padding="md" className="flex flex-col gap-3">
                <p className="text-xs font-semibold uppercase text-text-tertiary">
                    Spark authorization
                </p>
                <div className="grid gap-3 sm:grid-cols-3">
                    <label className="flex items-center gap-2 text-sm">
                        <Checkbox
                            checked={pack.spark.required}
                            onCheckedChange={(v) => setS({ required: !!v })}
                        />
                        Required
                    </label>
                    <div className="grid gap-1.5">
                        <Label>Duration (days)</Label>
                        <Input
                            type="number"
                            min={0}
                            value={pack.spark.durationDays}
                            onChange={(e) => setS({ durationDays: Math.max(0, +e.target.value) })}
                        />
                    </div>
                    <div className="grid gap-1.5">
                        <Label>Request timing</Label>
                        <Input
                            value={pack.spark.requestTiming}
                            onChange={(e) => setS({ requestTiming: e.target.value })}
                        />
                    </div>
                </div>
            </SurfaceCard>
        </SectionShell>
    );
}

// Review
function ReviewStep({ pack, campaignId }: { pack: CampaignPack; campaignId: string }) {
    const readiness = readinessState(pack);
    const [previewOpen, setPreviewOpen] = useState(false);
    const setPackStatus = useAppStore((s) => s.setPackStatus);
    const addActivity = useAppStore((s) => s.addActivity);
    const readinessTone =
        readiness.state === "Creator-ready"
            ? "ok"
            : readiness.state === "Needs review"
              ? "warn"
              : readiness.state === "Blocked"
                ? "destructive"
                : "neutral";
    return (
        <SectionShell
            title="Review"
            description="Confirm the Campaign Pack is complete before sending to a creator."
        >
            <SurfaceCard
                padding="md"
                className={`border-l-4 ${readinessTone === "ok" ? "border-l-ok" : readinessTone === "warn" ? "border-l-warn" : readinessTone === "destructive" ? "border-l-destructive" : "border-l-hairline"}`}
            >
                <StatusChip tone={readinessTone} dot>
                    {readiness.state.toUpperCase()}
                </StatusChip>
                <p className="mt-2 text-base font-semibold text-text-primary">
                    {readiness.state === "Creator-ready"
                        ? "This campaign is ready to send to a creator."
                        : "Fix the items below to reach creator-ready."}
                </p>
                {readiness.reasons.length > 0 && (
                    <ul className="mt-2 space-y-0.5 text-sm text-text-secondary">
                        {readiness.reasons.map((r, i) => (
                            <li key={i}>• {r}</li>
                        ))}
                    </ul>
                )}
                <div className="mt-3 flex flex-wrap gap-2">
                    <Button onClick={() => setPreviewOpen(true)}>
                        <Eye className="h-4 w-4" /> Preview creator brief
                    </Button>
                    <Button
                        variant="secondary"
                        disabled={readiness.state !== "Creator-ready"}
                        onClick={() => {
                            setPackStatus(pack.id, "Ready for creator");
                            addActivity({
                                campaignId,
                                kind: "marked-ready",
                                detail: "Marked ready for creator",
                            });
                            toast.success("Marked ready for creator");
                        }}
                    >
                        <Check className="h-4 w-4" /> Mark ready for creator
                    </Button>
                </div>
            </SurfaceCard>

            <div className="grid gap-4 md:grid-cols-2">
                {STEPS.map((s) => {
                    const done = stepIsComplete(pack, s.id);
                    return (
                        <SurfaceCard key={s.id} padding="sm">
                            <div className="flex items-center justify-between">
                                <p className="text-sm font-medium text-text-primary">{s.label}</p>
                                <StatusChip tone={done ? "ok" : "warn"}>
                                    {done ? "Complete" : "Incomplete"}
                                </StatusChip>
                            </div>
                        </SurfaceCard>
                    );
                })}
            </div>

            <CreatorPreviewDialog
                pack={pack}
                campaignId={campaignId}
                open={previewOpen}
                onOpenChange={setPreviewOpen}
            />
        </SectionShell>
    );
}
