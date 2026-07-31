import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/shared/ui/dialog";
import { Button } from "@/shared/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/shared/ui/tabs";
import { DemoMediaTile } from "@/shared/ui/demo-media-tile";
import { toast } from "sonner";
import { Copy, Download, FileJson, Printer } from "lucide-react";
import type { CampaignPack } from "@/features/campaigns/types/campaign";
import { seedProducts } from "@/features/products/data/products";
import { generateCreatorBrief } from "@/features/campaigns/lib/mockCampaignAI";
import {
    copyBriefToClipboard,
    exportBriefJson,
    exportBriefText,
} from "@/features/campaigns/lib/campaignExport";
import { useAppStore } from "@/app/store/app-store";
import { formatUtcDate } from "@/shared/lib/date-format";

export function CreatorPreviewDialog({
    pack,
    campaignId,
    open,
    onOpenChange,
}: {
    pack: CampaignPack;
    campaignId: string;
    open: boolean;
    onOpenChange: (v: boolean) => void;
}) {
    const product = seedProducts.find((p) => p.id === pack.productId);
    const addActivity = useAppStore((s) => s.addActivity);
    const brief = generateCreatorBrief(pack, product?.name ?? "your product");
    const primaryAngle = pack.angleOptions.find((a) => a.id === pack.primaryAngleId);
    const hooks = pack.hookOptions.filter((h) => pack.selectedHookIds.includes(h.id));

    async function copy() {
        try {
            await copyBriefToClipboard(pack);
            addActivity({
                campaignId,
                kind: "brief-copied",
                detail: "Creator brief copied to clipboard",
            });
            toast.success("Brief copied to clipboard");
        } catch {
            toast.error("Clipboard unavailable", {
                description: "Use Download instead to save the brief locally.",
            });
        }
    }

    function downloadText() {
        exportBriefText(pack);
        addActivity({ campaignId, kind: "exported", detail: "Exported creator brief as text" });
        toast.success("Brief downloaded");
    }
    function downloadJson() {
        exportBriefJson(pack);
        addActivity({ campaignId, kind: "exported", detail: "Exported creator brief as JSON" });
        toast.success("JSON downloaded");
    }
    function print() {
        window.print();
    }
    async function share() {
        try {
            await navigator.clipboard.writeText(window.location.href);
            toast.success("Campaign link copied");
        } catch {
            toast.error("Link could not be copied");
        }
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-h-[90vh] w-full max-w-3xl overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Creator brief preview</DialogTitle>
                    <DialogDescription>
                        What the creator sees. Internal analysis and confidence are hidden.
                    </DialogDescription>
                </DialogHeader>
                <div className="flex flex-wrap gap-2">
                    <Button size="sm" onClick={copy}>
                        <Copy className="h-4 w-4" /> Copy brief
                    </Button>
                    <Button size="sm" variant="secondary" onClick={share}>
                        <Copy className="h-4 w-4" /> Share link
                    </Button>
                    <Button size="sm" variant="secondary" onClick={print}>
                        <Printer className="h-4 w-4" /> Download / print PDF
                    </Button>
                </div>
                <Tabs defaultValue="quick" className="mt-3">
                    <TabsList aria-label="Creator brief view">
                        <TabsTrigger value="quick">Quick Brief</TabsTrigger>
                        <TabsTrigger value="full">Full Production Brief</TabsTrigger>
                    </TabsList>
                    <TabsContent value="quick" className="mt-4">
                        <div className="grid gap-5 rounded-lg bg-surface p-4 text-sm text-text-primary sm:grid-cols-[160px_minmax(0,1fr)] sm:p-5">
                            <DemoMediaTile
                                mediaUrl={product?.imageUrl}
                                mediaKind={product?.imageUrl ? "image" : undefined}
                                alt={product?.imageAlt}
                                seed={product?.colorSeed ?? pack.productId ?? pack.id}
                                label={product?.name ?? "Product"}
                                badges={[pack.deliverables.aspectRatio]}
                                aspect="4 / 5"
                                className="w-full rounded-md"
                            />
                            <div className="min-w-0 space-y-4">
                                <section>
                                    <p className="text-[10px] font-semibold uppercase text-text-tertiary">
                                        Product and objective
                                    </p>
                                    <p className="mt-1 text-base font-semibold">
                                        {product?.name ?? "Product"}
                                    </p>
                                    <p className="text-xs text-text-secondary">
                                        {pack.objective} · {pack.market} · {pack.platform}
                                    </p>
                                </section>
                                <section>
                                    <p className="text-[10px] font-semibold uppercase text-text-tertiary">
                                        Core angle
                                    </p>
                                    <p className="mt-1">
                                        {primaryAngle?.name ?? "Select an angle before sharing"}
                                    </p>
                                    <p className="text-xs text-text-secondary">
                                        {primaryAngle?.buyerProblem}
                                    </p>
                                </section>
                                <section>
                                    <p className="text-[10px] font-semibold uppercase text-text-tertiary">
                                        Hook options
                                    </p>
                                    <ol className="mt-1 list-decimal space-y-1 pl-5">
                                        {hooks.slice(0, 3).map((hook) => (
                                            <li key={hook.id}>{hook.text}</li>
                                        ))}
                                    </ol>
                                </section>
                            </div>
                            <section className="sm:col-span-2">
                                <p className="text-[10px] font-semibold uppercase text-text-tertiary">
                                    Required scenes
                                </p>
                                <div className="mt-2 grid gap-2 sm:grid-cols-3">
                                    {pack.storyboard
                                        .filter((scene) => scene.mustShow)
                                        .slice(0, 6)
                                        .map((scene) => (
                                            <div
                                                key={scene.id}
                                                className="rounded-md bg-surface-soft p-3"
                                            >
                                                <p className="text-xs font-semibold">
                                                    {scene.label} · {scene.durationRange}
                                                </p>
                                                <p className="mt-1 line-clamp-2 text-xs text-text-secondary">
                                                    {scene.visualDirection}
                                                </p>
                                            </div>
                                        ))}
                                </div>
                            </section>
                            <section className="grid gap-3 sm:col-span-2 sm:grid-cols-3">
                                <BriefSummaryItem label="CTA" value={pack.cta.primary} />
                                <BriefSummaryItem
                                    label="Don't say"
                                    value={pack.cta.claimsToAvoid.join("; ") || "No blocked claims"}
                                />
                                <BriefSummaryItem
                                    label="Deliverable"
                                    value={`${pack.deliverables.numberOfVideos} videos · ${pack.deliverables.targetDurationSec}s · ${pack.deliverables.aspectRatio}${pack.deliverables.dueDate ? ` · Due ${formatUtcDate(pack.deliverables.dueDate)}` : ""}`}
                                />
                            </section>
                        </div>
                    </TabsContent>
                    <TabsContent value="full" className="mt-4">
                        <div className="flex flex-col gap-5 rounded-lg bg-surface p-5 text-sm text-text-primary">
                            <section>
                                <p className="text-[10px] font-semibold uppercase text-text-tertiary">
                                    Product
                                </p>
                                <p className="mt-1 text-base font-semibold">
                                    {product?.name ?? "Product"}
                                </p>
                                <p className="text-xs text-text-secondary">
                                    {pack.objective} · {pack.market} · {pack.platform}
                                </p>
                            </section>
                            <section>
                                <p className="text-[10px] font-semibold uppercase text-text-tertiary">
                                    Main angle
                                </p>
                                <p className="mt-1">{primaryAngle?.name ?? "—"}</p>
                                {primaryAngle && (
                                    <p className="text-xs text-text-secondary">
                                        {primaryAngle.buyerProblem}
                                    </p>
                                )}
                            </section>
                            <section>
                                <p className="text-[10px] font-semibold uppercase text-text-tertiary">
                                    Hooks
                                </p>
                                <ol className="mt-1 list-decimal space-y-1 pl-5 text-sm">
                                    {hooks.length === 0 ? (
                                        <li className="list-none text-text-tertiary">
                                            No hooks selected
                                        </li>
                                    ) : (
                                        hooks.map((h) => <li key={h.id}>{h.text}</li>)
                                    )}
                                </ol>
                            </section>
                            <section>
                                <p className="text-[10px] font-semibold uppercase text-text-tertiary">
                                    Script
                                </p>
                                <div className="mt-1 space-y-2">
                                    {pack.script.map((b) => (
                                        <div key={b.id}>
                                            <p className="text-[11px] font-semibold text-text-secondary">
                                                {b.kind}
                                            </p>
                                            <p className="text-sm">{b.text}</p>
                                        </div>
                                    ))}
                                </div>
                            </section>
                            <section>
                                <p className="text-[10px] font-semibold uppercase text-text-tertiary">
                                    Storyboard
                                </p>
                                <ol className="mt-1 space-y-2">
                                    {pack.storyboard.map((s, i) => (
                                        <li
                                            key={s.id}
                                            className="rounded-md bg-surface-soft/50 p-2 text-sm"
                                        >
                                            <p className="font-medium">
                                                {i + 1}. {s.label}{" "}
                                                <span className="text-text-tertiary">
                                                    ({s.durationRange})
                                                </span>
                                            </p>
                                            <p className="text-xs text-text-secondary">
                                                {s.visualDirection}
                                            </p>
                                            <p className="text-xs text-text-secondary italic">
                                                “{s.spokenLine}”
                                            </p>
                                        </li>
                                    ))}
                                </ol>
                            </section>
                            <section>
                                <p className="text-[10px] font-semibold uppercase text-text-tertiary">
                                    CTA
                                </p>
                                <p className="mt-1">{pack.cta.primary}</p>
                            </section>
                            <section className="grid gap-3 sm:grid-cols-2">
                                <div>
                                    <p className="text-[10px] font-semibold uppercase text-text-tertiary">
                                        Do
                                    </p>
                                    <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm">
                                        {pack.cta.claimsAllowed.map((c, i) => (
                                            <li key={i}>{c}</li>
                                        ))}
                                    </ul>
                                </div>
                                <div>
                                    <p className="text-[10px] font-semibold uppercase text-text-tertiary">
                                        Don't
                                    </p>
                                    <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm">
                                        {pack.cta.claimsToAvoid.map((c, i) => (
                                            <li key={i}>{c}</li>
                                        ))}
                                    </ul>
                                </div>
                            </section>
                            <section>
                                <p className="text-[10px] font-semibold uppercase text-text-tertiary">
                                    Deliverables & rights
                                </p>
                                <p className="mt-1 text-sm">
                                    {pack.deliverables.numberOfVideos} ×{" "}
                                    {pack.deliverables.targetDurationSec}s{" "}
                                    {pack.deliverables.aspectRatio} ·{" "}
                                    {pack.deliverables.revisionRounds} revision round(s)
                                    {pack.deliverables.rawFootageRequired ? " · raw footage" : ""}
                                </p>
                                <p className="mt-1 text-xs text-text-secondary">
                                    TikTok Organic: {pack.rights.tiktokOrganic ? "yes" : "no"} ·
                                    Spark Ads: {pack.rights.tiktokSpark ? "yes" : "no"} · Meta Ads:{" "}
                                    {pack.rights.metaAds ? "yes" : "no"} · Usage{" "}
                                    {pack.rights.usageDurationDays} days
                                </p>
                                {pack.spark.required && (
                                    <p className="mt-1 text-xs text-text-secondary">
                                        Spark authorization for {pack.spark.durationDays} days.{" "}
                                        {pack.spark.requestTiming}.
                                    </p>
                                )}
                            </section>
                        </div>
                    </TabsContent>
                </Tabs>
                <details className="mt-2 text-xs text-text-tertiary">
                    <summary className="cursor-pointer">Advanced exports</summary>
                    <div className="mt-2 flex flex-wrap gap-2">
                        <Button size="sm" variant="secondary" onClick={downloadText}>
                            <Download className="h-4 w-4" /> Download .txt
                        </Button>
                        <Button size="sm" variant="secondary" onClick={downloadJson}>
                            <FileJson className="h-4 w-4" /> Download .json
                        </Button>
                    </div>
                    <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap rounded bg-surface-soft p-3 text-[11px]">
                        {brief}
                    </pre>
                </details>
            </DialogContent>
        </Dialog>
    );
}

function BriefSummaryItem({ label, value }: { label: string; value: string }) {
    return (
        <div className="rounded-md bg-surface-soft p-3">
            <p className="text-[10px] font-semibold uppercase text-text-tertiary">{label}</p>
            <p className="mt-1 text-xs leading-5 text-text-primary">{value}</p>
        </div>
    );
}
