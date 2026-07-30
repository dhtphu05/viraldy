import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useMemo, useState, useEffect } from "react";
import { AppShell } from "@/widgets/app-shell/app-shell";
import { PageHeader } from "@/shared/ui/page-header";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import { StatusChip } from "@/shared/ui/status-chip";
import { toast } from "sonner";
import { useAppStore } from "@/app/store/app-store";
import { seedProducts } from "@/features/products/data/products";
import {
    generateAdaptation,
    defaultObjectiveDefaults,
} from "@/features/campaigns/lib/mockCampaignAI";
import { campaignTemplates } from "@/features/campaigns/mocks/campaignTemplates";
import type {
    CampaignMarket,
    CampaignObjective,
    CampaignPack,
    CampaignPlatform,
    CreatorTone,
    CreatorType,
} from "@/features/campaigns/types/campaign";
import { Sparkles, ArrowLeft } from "lucide-react";

export const Route = createFileRoute("/campaigns/new")({
    head: () => ({
        meta: [
            { title: "New campaign — Viraldy" },
            {
                name: "description",
                content: "Start a new creator campaign from a product and references.",
            },
        ],
    }),
    component: NewCampaign,
});

const OBJECTIVES: CampaignObjective[] = [
    "Organic Product Test",
    "TikTok Shop Affiliate",
    "UGC Paid Asset",
    "Spark Ads Test",
    "POD Gift Campaign",
    "Dropshipping Product Demo",
];
const MARKETS: CampaignMarket[] = ["US", "UK", "CA", "AU", "DE"];
const PLATFORMS: CampaignPlatform[] = [
    "TikTok Shop",
    "TikTok Organic",
    "TikTok Spark Ads",
    "Meta UGC Ads",
];
const CREATOR_TYPES: CreatorType[] = [
    "Micro creator",
    "Mid-tier creator",
    "UGC-only",
    "Product expert",
    "Lifestyle",
];
const TONES: CreatorTone[] = [
    "Natural",
    "Energetic",
    "Conversational",
    "Expert",
    "Emotional",
    "Minimal / Raw UGC",
];

function NewCampaign() {
    const navigate = useNavigate();
    const draft = useAppStore((s) => s.campaignDraft);
    const setDraft = useAppStore((s) => s.setDraft);
    const clearDraft = useAppStore((s) => s.clearDraft);
    const createPack = useAppStore((s) => s.createCampaignPack);
    const lastAdaptation = useAppStore((s) => s.lastAdaptation);
    const creatives = useAppStore((s) => s.creatives);
    const analyses = useAppStore((s) => s.analyses);
    const setLastAdaptation = useAppStore((s) => s.setLastAdaptation);

    // Preselect from adaptation handoff
    useEffect(() => {
        if (
            lastAdaptation &&
            (!draft.productId || !draft.referenceCreativeIds?.includes(lastAdaptation.creativeId))
        ) {
            setDraft({
                productId: draft.productId ?? lastAdaptation.productId,
                referenceCreativeIds: Array.from(
                    new Set([...(draft.referenceCreativeIds ?? []), lastAdaptation.creativeId]),
                ),
            });
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const analyzed = useMemo(
        () => creatives.filter((c) => c.analysisStatus === "analyzed"),
        [creatives],
    );

    const [name, setName] = useState(draft.name ?? "");
    const [nameEdited, setNameEdited] = useState(!!draft.name);
    const [error, setError] = useState<string | null>(null);
    const [busy, setBusy] = useState(false);

    const productId = draft.productId ?? "";
    const objective = draft.objective ?? "Organic Product Test";
    const market = draft.market ?? "US";
    const platform = draft.platform ?? "TikTok Shop";
    const creatorType = draft.creatorType ?? "Micro creator";
    const creatorTone = draft.creatorTone ?? "Natural";
    const language = draft.language ?? "English";
    const buyerSegment = draft.buyerSegment ?? "";
    const refs = draft.referenceCreativeIds ?? [];

    const handoffCreative = lastAdaptation
        ? creatives.find((c) => c.id === lastAdaptation.creativeId)
        : undefined;
    const handoffProduct = lastAdaptation
        ? seedProducts.find((p) => p.id === lastAdaptation.productId)
        : undefined;
    const selectedProduct = seedProducts.find((p) => p.id === productId);
    const suggestedName = selectedProduct
        ? `${selectedProduct.name} ${market} ${objective.includes("Affiliate") ? "Affiliate Test" : "Launch"}`
        : "";

    const templateName =
        draft.templateId && campaignTemplates.find((t) => t.id === draft.templateId)?.name;

    useEffect(() => {
        if (!nameEdited && suggestedName) setName(suggestedName);
    }, [nameEdited, suggestedName]);

    async function createCampaign() {
        if (!name.trim()) {
            setError("Give this campaign a name");
            return;
        }
        if (!productId) {
            setError("Select a product");
            return;
        }
        setError(null);
        setBusy(true);
        const packId = `pack-${Date.now()}`;
        const campaignId = `c-${Date.now()}`;
        const now = new Date().toISOString();
        const firstRef = refs[0];
        const sourceHook = firstRef
            ? (creatives.find((c) => c.id === firstRef)?.hookExcerpt ?? "")
            : "";
        const adaptation = await generateAdaptation(productId, sourceHook, 0);
        const defaults = defaultObjectiveDefaults(objective, platform);
        const productName = seedProducts.find((p) => p.id === productId)?.name ?? "Product";
        const pack: CampaignPack = {
            id: packId,
            name: name.trim(),
            status: "Draft",
            objective,
            market,
            platform,
            productId,
            buyerSegment: buyerSegment || "General buyers",
            language,
            creatorType,
            creatorTone,
            referenceCreativeIds: refs,
            adaptation: { ...adaptation, notes: "" },
            angleOptions: [],
            primaryAngleId: undefined,
            secondaryAngleIds: [],
            hookOptions: [],
            selectedHookIds: [],
            script: [],
            storyboard: [],
            cta: {
                primary: "Tap the product tag in my TikTok Shop",
                productTagInstruction: "Pin the product tag so it appears in the first 3 seconds.",
                offerStatement: "Availability shown on the product tag.",
                coupon: "",
                shipping: "",
                claimsAllowed: [
                    `Talk about ${productName} in your own words`,
                    "Show real before-and-after in your space",
                ],
                claimsToAvoid: ["Guaranteed results language", "Health or income claims"],
                productLimitations: "",
                complianceNotes: "",
                warnings: [],
            },
            deliverables: {
                numberOfVideos: 3,
                rawFootageRequired: false,
                aspectRatio: "9:16",
                targetDurationSec: 30,
                captionRequired: true,
                productTagRequired: true,
                revisionRounds: 1,
            },
            rights: defaults.rights,
            spark: defaults.spark,
            reviewedWarningIds: [],
            createdAt: now,
            updatedAt: now,
            savedAt: now,
        };
        createPack({
            campaignId,
            packId,
            pack,
            summary: {
                id: campaignId,
                packId,
                name: pack.name,
                product: productName,
                status: "Draft",
                activeAssets: 0,
                ugcScore: 0,
                gmv: 0,
                nextAction: "Select references and angle",
                objective,
                market,
                platform,
                packStatus: "Draft",
                referenceCount: refs.length,
                hookCount: 0,
                deliverables: 3,
                updatedAt: now,
            },
        });
        clearDraft();
        // clear one-shot adaptation so it doesn't repeatedly re-preselect
        if (lastAdaptation) setLastAdaptation({ ...lastAdaptation, createdAt: "" });
        setBusy(false);
        toast.success("Campaign created");
        navigate({ to: "/campaigns/$campaignId", params: { campaignId } });
    }

    return (
        <AppShell>
            <div className="flex flex-col gap-6">
                <PageHeader
                    title="New campaign"
                    description={
                        templateName
                            ? `Starting from template: ${templateName}`
                            : "Set the product, market, and creator direction. You can refine every section after."
                    }
                    actions={
                        <Button variant="ghost" asChild>
                            <Link to="/campaigns">
                                <ArrowLeft className="h-4 w-4" />
                                Back to campaigns
                            </Link>
                        </Button>
                    }
                />

                {handoffCreative && handoffProduct && (
                    <SurfaceCard padding="md" className="flex flex-wrap items-center gap-3">
                        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md bg-primary-soft text-primary">
                            <Sparkles className="h-4 w-4" />
                        </span>
                        <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-2">
                                <StatusChip tone="info" dot>
                                    Adaptation preselected
                                </StatusChip>
                                <p className="truncate text-sm font-medium text-text-primary">
                                    {handoffCreative.title} → {handoffProduct.name}
                                </p>
                            </div>
                            <p className="mt-0.5 text-xs text-text-secondary">
                                We've selected this product and added the reference. Change either
                                below.
                            </p>
                        </div>
                    </SurfaceCard>
                )}

                <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
                    <SurfaceCard padding="lg" className="flex flex-col gap-5">
                        <div className="grid gap-1.5">
                            <Label htmlFor="name">Campaign name</Label>
                            <Input
                                id="name"
                                placeholder={suggestedName || "e.g. Kitchen Organizer US Launch"}
                                value={name}
                                aria-invalid={!!error && !name.trim()}
                                aria-describedby={
                                    error && !name.trim() ? "campaign-name-error" : undefined
                                }
                                onChange={(e) => {
                                    setNameEdited(true);
                                    setName(e.target.value);
                                }}
                            />
                            {error && !name.trim() && (
                                <p id="campaign-name-error" className="text-xs text-destructive">
                                    {error}
                                </p>
                            )}
                            {suggestedName && name !== suggestedName && (
                                <button
                                    type="button"
                                    onClick={() => {
                                        setNameEdited(false);
                                        setName(suggestedName);
                                    }}
                                    className="w-fit text-xs text-primary hover:underline"
                                >
                                    Use suggested name: {suggestedName}
                                </button>
                            )}
                        </div>

                        <div className="grid gap-1.5">
                            <Label>Product</Label>
                            <Select
                                value={productId}
                                onValueChange={(v) => setDraft({ productId: v })}
                            >
                                <SelectTrigger aria-label="Product">
                                    <SelectValue placeholder="Select a product" />
                                </SelectTrigger>
                                <SelectContent>
                                    {seedProducts.map((p) => (
                                        <SelectItem key={p.id} value={p.id}>
                                            {p.name} · {p.category} · ${p.price.toFixed(0)}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            {error && !productId && (
                                <p className="text-xs text-destructive">Select a product</p>
                            )}
                        </div>

                        <div className="grid gap-3 sm:grid-cols-2">
                            <div className="grid gap-1.5">
                                <Label>Objective</Label>
                                <Select
                                    value={objective}
                                    onValueChange={(v) =>
                                        setDraft({ objective: v as CampaignObjective })
                                    }
                                >
                                    <SelectTrigger aria-label="Objective">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {OBJECTIVES.map((o) => (
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
                                    value={platform}
                                    onValueChange={(v) =>
                                        setDraft({ platform: v as CampaignPlatform })
                                    }
                                >
                                    <SelectTrigger aria-label="Platform">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {PLATFORMS.map((p) => (
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
                                    value={market}
                                    onValueChange={(v) => setDraft({ market: v as CampaignMarket })}
                                >
                                    <SelectTrigger aria-label="Market">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {MARKETS.map((m) => (
                                            <SelectItem key={m} value={m}>
                                                {m}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="grid gap-1.5">
                                <Label htmlFor="campaign-language">Language</Label>
                                <Input
                                    id="campaign-language"
                                    value={language}
                                    onChange={(e) => setDraft({ language: e.target.value })}
                                />
                            </div>
                            <div className="grid gap-1.5">
                                <Label>Creator type</Label>
                                <Select
                                    value={creatorType}
                                    onValueChange={(v) =>
                                        setDraft({ creatorType: v as CreatorType })
                                    }
                                >
                                    <SelectTrigger aria-label="Creator type">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {CREATOR_TYPES.map((c) => (
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
                                    value={creatorTone}
                                    onValueChange={(v) =>
                                        setDraft({ creatorTone: v as CreatorTone })
                                    }
                                >
                                    <SelectTrigger aria-label="Creator tone">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {TONES.map((t) => (
                                            <SelectItem key={t} value={t}>
                                                {t}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        <div className="grid gap-1.5">
                            <Label htmlFor="campaign-buyer-segment">Buyer segment (optional)</Label>
                            <Input
                                id="campaign-buyer-segment"
                                placeholder="e.g. Renters 25–35 with small kitchens"
                                value={buyerSegment}
                                onChange={(e) => setDraft({ buyerSegment: e.target.value })}
                            />
                        </div>

                        <div className="grid gap-1.5">
                            <Label>Creative references (optional)</Label>
                            {analyzed.length === 0 ? (
                                <p className="rounded-md bg-surface-soft/60 p-3 text-xs text-text-secondary">
                                    No analyzed creatives yet.{" "}
                                    <Link
                                        to="/creative-library"
                                        className="text-primary hover:underline"
                                    >
                                        Open Creative Library
                                    </Link>
                                    .
                                </p>
                            ) : (
                                <div className="grid gap-2 sm:grid-cols-2">
                                    {analyzed.slice(0, 10).map((c) => {
                                        const on = refs.includes(c.id);
                                        return (
                                            <button
                                                key={c.id}
                                                type="button"
                                                onClick={() =>
                                                    setDraft({
                                                        referenceCreativeIds: on
                                                            ? refs.filter((r) => r !== c.id)
                                                            : refs.length >= 5
                                                              ? refs
                                                              : [...refs, c.id],
                                                    })
                                                }
                                                className={`rounded-md border px-3 py-2 text-left text-xs transition-colors ${
                                                    on
                                                        ? "border-primary/40 bg-primary-soft text-primary-active"
                                                        : "border-hairline/70 bg-surface hover:bg-surface-soft"
                                                }`}
                                            >
                                                <p className="truncate text-sm font-medium text-text-primary">
                                                    {c.title}
                                                </p>
                                                <p className="truncate text-[11px] text-text-secondary">
                                                    {c.platform} · {c.angle}
                                                    {c.dnaScore ? ` · DNA ${c.dnaScore}` : ""}
                                                    {analyses[c.id]
                                                        ? ` · ${analyses[c.id].decision}`
                                                        : ""}
                                                </p>
                                            </button>
                                        );
                                    })}
                                </div>
                            )}
                            <p className="text-[11px] text-text-tertiary">
                                Select up to 5 references. You can add more from the workspace.
                            </p>
                        </div>

                        <div className="sticky bottom-0 z-10 -mx-7 -mb-7 flex flex-wrap items-center justify-between gap-3 border-t border-hairline/60 bg-surface/95 px-7 py-4 backdrop-blur">
                            <div className="min-w-0 text-xs text-text-secondary">
                                <p className="font-medium text-text-primary">
                                    {selectedProduct?.name ?? "Select a product"}
                                </p>
                                <p className="truncate">
                                    {objective} · {market} · {refs.length} reference
                                    {refs.length === 1 ? "" : "s"}
                                </p>
                            </div>
                            <div className="flex flex-wrap items-center gap-2">
                                <Button
                                    variant="ghost"
                                    onClick={() => {
                                        clearDraft();
                                        setName("");
                                        setNameEdited(false);
                                        setError(null);
                                    }}
                                >
                                    Clear
                                </Button>
                                <Button onClick={createCampaign} disabled={busy}>
                                    {busy ? "Creating…" : "Create campaign"}
                                </Button>
                            </div>
                        </div>
                    </SurfaceCard>

                    <SurfaceCard padding="md" className="h-fit">
                        <p className="text-xs font-semibold uppercase tracking-wide text-text-tertiary">
                            What happens next
                        </p>
                        <ol className="mt-2 flex flex-col gap-2 text-sm text-text-secondary">
                            <li>• Viraldy adapts your references to this product's context</li>
                            <li>• You'll select an angle and hooks</li>
                            <li>• Edit script, storyboard, CTA, deliverables and rights</li>
                            <li>• Review and export a creator-facing brief</li>
                        </ol>
                    </SurfaceCard>
                </div>
            </div>
        </AppShell>
    );
}
