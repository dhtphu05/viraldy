import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/shared/ui/dialog";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import { StatusChip } from "@/shared/ui/status-chip";
import { Search, Package, ArrowRight, Check } from "lucide-react";
import { seedProducts } from "@/features/products/data/products";
import { useMemo, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useAppStore } from "@/app/store/app-store";
import { toast } from "sonner";
import { cn } from "@/shared/lib/utils";
import type { ProductCategory } from "@/features/creative-library/types/creative";

const categories: ("All" | ProductCategory)[] = [
    "All",
    "Home & Kitchen",
    "Pet",
    "Beauty",
    "POD Gifts",
    "Home Organization",
];

export function AdaptToProductDialog({
    open,
    onOpenChange,
    creativeId,
    creativeTitle,
}: {
    open: boolean;
    onOpenChange: (v: boolean) => void;
    creativeId: string;
    creativeTitle: string;
}) {
    const [query, setQuery] = useState("");
    const [category, setCategory] = useState<"All" | ProductCategory>("All");
    const [selected, setSelected] = useState<string | null>(null);
    const setLastAdaptation = useAppStore((s) => s.setLastAdaptation);
    const updateCreative = useAppStore((s) => s.updateCreative);
    const navigate = useNavigate();

    const products = useMemo(() => {
        const q = query.trim().toLowerCase();
        return seedProducts.filter(
            (p) =>
                (category === "All" || p.category === category) &&
                (q === "" || p.name.toLowerCase().includes(q)),
        );
    }, [query, category]);

    function confirm() {
        if (!selected) return;
        setLastAdaptation({
            creativeId,
            productId: selected,
            createdAt: new Date().toISOString(),
        });
        updateCreative(creativeId, { linkedProductId: selected });
        onOpenChange(false);
        toast.success("Adaptation handoff ready", {
            description: "Product linked and ready to continue from Campaigns.",
        });
        void navigate({ to: "/campaigns" });
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="flex max-h-[calc(100dvh-2rem)] max-w-[calc(100vw-1rem)] flex-col overflow-hidden sm:max-w-[640px]">
                <DialogHeader>
                    <DialogTitle>Adapt pattern to product</DialogTitle>
                    <DialogDescription>
                        Choose the product that should reuse this creative structure. Viraldy will
                        keep the reusable pattern and change the buyer context, proof, and
                        execution.
                    </DialogDescription>
                </DialogHeader>

                <div className="rounded-md bg-surface-soft p-3 text-sm">
                    <p className="text-xs uppercase text-text-tertiary">Reference</p>
                    <p className="mt-0.5 break-words font-medium text-text-primary">
                        {creativeTitle}
                    </p>
                </div>

                <div className="flex flex-col gap-2 sm:flex-row">
                    <div className="relative flex-1">
                        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-tertiary" />
                        <Input
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            placeholder="Search your products"
                            className="pl-9"
                            aria-label="Search products"
                        />
                    </div>
                    <Select
                        value={category}
                        onValueChange={(v) => setCategory(v as typeof category)}
                    >
                        <SelectTrigger className="w-full sm:w-56" aria-label="Filter by category">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            {categories.map((c) => (
                                <SelectItem key={c} value={c}>
                                    {c}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>

                <div
                    role="radiogroup"
                    aria-label="Products"
                    className="min-h-0 flex-1 overflow-y-auto rounded-md border border-control-border"
                >
                    {products.length === 0 ? (
                        <div className="p-8 text-center text-sm text-text-tertiary">
                            No products match. Try clearing the filter.
                        </div>
                    ) : (
                        <ul className="divide-y divide-hairline/60">
                            {products.map((p) => {
                                const active = selected === p.id;
                                return (
                                    <li key={p.id}>
                                        <button
                                            type="button"
                                            onClick={() => setSelected(p.id)}
                                            role="radio"
                                            aria-checked={active}
                                            className={cn(
                                                "flex min-h-16 w-full items-start gap-3 px-3 py-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring sm:items-center",
                                                active
                                                    ? "bg-primary-softer"
                                                    : "hover:bg-surface-soft",
                                            )}
                                        >
                                            {p.imageUrl ? (
                                                <img
                                                    src={p.imageUrl}
                                                    alt={p.imageAlt ?? ""}
                                                    className="h-12 w-12 shrink-0 rounded-md bg-surface-muted object-cover"
                                                />
                                            ) : (
                                                <span
                                                    className="grid h-12 w-12 shrink-0 place-items-center rounded-md bg-surface-muted text-text-tertiary"
                                                    aria-hidden
                                                >
                                                    <Package className="h-4 w-4" />
                                                </span>
                                            )}
                                            <span className="min-w-0 flex-1">
                                                <span className="flex flex-col gap-0.5 sm:flex-row sm:items-center sm:gap-2">
                                                    <span className="break-words text-sm font-medium text-text-primary">
                                                        {p.name}
                                                    </span>
                                                    <span className="tabular text-xs text-text-tertiary">
                                                        ${p.price.toFixed(2)}
                                                    </span>
                                                </span>
                                                <span className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px]">
                                                    <span className="text-text-tertiary">
                                                        {p.category}
                                                    </span>
                                                    <StatusChip
                                                        tone={
                                                            p.readiness === "Ready"
                                                                ? "ok"
                                                                : p.readiness === "Setup needed"
                                                                  ? "warn"
                                                                  : "destructive"
                                                        }
                                                    >
                                                        {p.readiness}
                                                    </StatusChip>
                                                    <StatusChip
                                                        tone={
                                                            p.fulfillmentRisk === "Low"
                                                                ? "ok"
                                                                : p.fulfillmentRisk === "Medium"
                                                                  ? "warn"
                                                                  : "destructive"
                                                        }
                                                    >
                                                        {p.fulfillmentRisk} risk
                                                    </StatusChip>
                                                    {p.linkedCampaignCount > 0 && (
                                                        <span className="text-text-tertiary">
                                                            · {p.linkedCampaignCount} campaign
                                                            {p.linkedCampaignCount > 1 ? "s" : ""}
                                                        </span>
                                                    )}
                                                </span>
                                            </span>
                                            <span
                                                className={cn(
                                                    "grid h-5 w-5 shrink-0 place-items-center rounded-full border transition-all",
                                                    active
                                                        ? "border-primary bg-primary text-primary-foreground"
                                                        : "border-hairline",
                                                )}
                                                aria-hidden
                                            >
                                                {active && <Check className="h-3 w-3" />}
                                            </span>
                                        </button>
                                    </li>
                                );
                            })}
                        </ul>
                    )}
                </div>

                <DialogFooter className="mt-2 shrink-0">
                    <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
                        Cancel
                    </Button>
                    <Button type="button" disabled={!selected} onClick={confirm}>
                        Continue to adaptation
                        <ArrowRight className="h-4 w-4" />
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
