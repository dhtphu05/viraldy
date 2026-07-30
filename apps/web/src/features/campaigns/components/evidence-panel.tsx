import { SurfaceCard } from "@/shared/ui/surface-card";
import { StatusChip } from "@/shared/ui/status-chip";
import { useAppStore } from "@/app/store/app-store";
import type { CampaignPack } from "@/features/campaigns/types/campaign";
import { Link } from "@tanstack/react-router";
import { seedProducts } from "@/features/products/data/products";
import { Info, Sparkles } from "lucide-react";

export function EvidencePanel({ pack }: { pack: CampaignPack }) {
    const creatives = useAppStore((s) => s.creatives);
    const analyses = useAppStore((s) => s.analyses);
    const refs = pack.referenceCreativeIds
        .map((id) => creatives.find((c) => c.id === id))
        .filter(Boolean);
    const product = seedProducts.find((p) => p.id === pack.productId);
    const primaryAngle = pack.angleOptions.find((a) => a.id === pack.primaryAngleId);
    return (
        <SurfaceCard
            padding="none"
            className="divide-y divide-divider overflow-hidden border-y border-divider"
        >
            <section className="p-4">
                <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-primary" />
                    <p className="text-xs font-semibold uppercase text-text-tertiary">
                        Selected direction
                    </p>
                </div>
                <p className="mt-2 text-sm font-medium text-text-primary">
                    {primaryAngle?.name ?? "No angle selected"}
                </p>
                {primaryAngle && (
                    <p className="mt-1 text-xs text-text-secondary">{primaryAngle.buyerProblem}</p>
                )}
                <div className="mt-3 flex flex-wrap gap-1.5">
                    {pack.selectedHookIds.slice(0, 3).map((id) => {
                        const h = pack.hookOptions.find((x) => x.id === id);
                        if (!h) return null;
                        return (
                            <StatusChip key={id} tone="info">
                                {h.type}
                            </StatusChip>
                        );
                    })}
                </div>
            </section>

            <section className="p-4">
                <p className="text-xs font-semibold uppercase text-text-tertiary">Product</p>
                {product ? (
                    <div className="mt-2">
                        <p className="text-sm font-medium text-text-primary">{product.name}</p>
                        <p className="text-xs text-text-secondary">
                            {product.category} · ${product.price.toFixed(2)}
                        </p>
                        <div className="mt-2 flex flex-wrap gap-1.5">
                            <StatusChip tone={product.readiness === "Ready" ? "ok" : "warn"}>
                                {product.readiness}
                            </StatusChip>
                            <StatusChip
                                tone={
                                    product.fulfillmentRisk === "Low"
                                        ? "ok"
                                        : product.fulfillmentRisk === "Medium"
                                          ? "warn"
                                          : "destructive"
                                }
                            >
                                {product.fulfillmentRisk} fulfillment risk
                            </StatusChip>
                        </div>
                    </div>
                ) : (
                    <p className="mt-2 text-xs text-text-secondary">No product selected.</p>
                )}
            </section>

            <section className="p-4">
                <p className="text-xs font-semibold uppercase text-text-tertiary">Reference DNA</p>
                {refs.length === 0 ? (
                    <p className="mt-2 text-xs text-text-secondary">No references selected.</p>
                ) : (
                    <ul className="mt-2 flex flex-col divide-y divide-hairline/60">
                        {refs.map((c) => {
                            if (!c) return null;
                            const a = analyses[c.id];
                            return (
                                <li key={c.id} className="py-2 first:pt-0 last:pb-0">
                                    <Link
                                        to="/creative-library/$creativeId"
                                        params={{ creativeId: c.id }}
                                        className="block rounded-md focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                                    >
                                        <p className="truncate text-sm font-medium text-text-primary">
                                            {c.title}
                                        </p>
                                        <p className="truncate text-xs text-text-secondary">
                                            {c.platform} · {c.angle}{" "}
                                            {c.dnaScore ? `· DNA ${c.dnaScore}` : ""}
                                        </p>
                                        {a && (
                                            <p className="mt-1 truncate text-[11px] text-text-tertiary">
                                                {a.decision}
                                            </p>
                                        )}
                                    </Link>
                                </li>
                            );
                        })}
                    </ul>
                )}
            </section>

            <section className="bg-info-soft/40 p-4">
                <div className="flex items-center gap-2">
                    <Info className="h-4 w-4 text-info" />
                    <p className="text-xs font-semibold uppercase text-info">Why this direction</p>
                </div>
                <p className="mt-2 text-xs text-text-secondary">
                    Viraldy retains the source narrative and reveal pattern, and adapts the buyer
                    problem, proof, and environment to your product to avoid direct copying.
                </p>
            </section>
        </SurfaceCard>
    );
}
