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
import { Fragment, useMemo, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useAppStore } from "@/app/store/app-store";
import { toast } from "sonner";
import { cn } from "@/shared/lib/utils";
import type { ProductCategory } from "@/features/creative-library/types/creative";
import { rankProductsByPatternFit } from "@/features/creative-library/lib/product-pattern-fit";

const categories: ("All" | ProductCategory)[] = [
    "All",
    "Home & Kitchen",
    "Pet",
    "Beauty",
    "POD Gifts",
    "Home Organization",
];
const fitGroups = [
    { id: "recommended", label: "Recommended matches" },
    { id: "possible", label: "Possible matches" },
    { id: "low", label: "Low-fit products" },
] as const;

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
    const creative = useAppStore((state) => state.creatives.find((item) => item.id === creativeId));
    const navigate = useNavigate();

    const products = useMemo(() => {
        const q = query.trim().toLowerCase();
        const filtered = seedProducts.filter(
            (p) =>
                (category === "All" || p.category === category) &&
                (q === "" || p.name.toLowerCase().includes(q)),
        );
        if (!creative) {
            return filtered.map((product) => ({
                product,
                fit: {
                    level: "possible" as const,
                    score: 0,
                    reasons: ["Review the source pattern before choosing this product."],
                    risk: "Pattern fit has not been calculated yet.",
                },
            }));
        }
        return rankProductsByPatternFit(creative, filtered);
    }, [category, creative, query]);

    function confirm() {
        if (!selected) return;
        setLastAdaptation({
            creativeId,
            productId: selected,
            createdAt: new Date().toISOString(),
        });
        updateCreative(creativeId, { linkedProductId: selected });
        onOpenChange(false);
        toast.success("Production context selected", {
            description: "Preparing the product and source creative in Production Run.",
        });
        void navigate({
            to: "/mvp",
            search: {
                entryType: "reference-first",
                localProductId: selected,
                sourceCreativeId: creativeId,
                objective: "tiktok_shop_affiliate_test",
                market: "US",
            },
        });
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
                        <div className="flex flex-col items-center px-6 py-8 text-center">
                            <span className="grid h-10 w-10 place-items-center rounded-full bg-surface-muted text-text-secondary">
                                <Package className="h-5 w-5" />
                            </span>
                            <p className="mt-3 text-sm font-semibold text-text-primary">
                                No products match these filters
                            </p>
                            <p className="mt-1 max-w-sm text-xs leading-5 text-text-secondary">
                                Search the full catalog or choose another category.
                            </p>
                            <Button
                                type="button"
                                variant="secondary"
                                size="sm"
                                className="mt-3"
                                onClick={() => {
                                    setQuery("");
                                    setCategory("All");
                                }}
                            >
                                Clear filters
                            </Button>
                        </div>
                    ) : (
                        <ul className="divide-y divide-hairline/60">
                            {fitGroups.map((group) => {
                                const matches = products.filter(
                                    ({ fit }) => fit.level === group.id,
                                );
                                if (matches.length === 0) return null;
                                return (
                                    <Fragment key={group.id}>
                                        <li className="bg-surface-soft px-3 py-2 text-[10px] font-semibold uppercase text-text-tertiary">
                                            {group.label}
                                        </li>
                                        {matches.map(({ product, fit }) => {
                                            const active = selected === product.id;
                                            return (
                                                <li key={product.id}>
                                                    <button
                                                        type="button"
                                                        onClick={() => setSelected(product.id)}
                                                        role="radio"
                                                        aria-checked={active}
                                                        className={cn(
                                                            "flex min-h-16 w-full items-start gap-3 px-3 py-3 text-left transition-colors duration-[180ms] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring motion-reduce:transition-none",
                                                            active
                                                                ? "bg-primary-softer"
                                                                : "hover:bg-surface-soft",
                                                        )}
                                                    >
                                                        {product.imageUrl ? (
                                                            <img
                                                                src={product.imageUrl}
                                                                alt={product.imageAlt ?? ""}
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
                                                            <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
                                                                <span className="break-words text-sm font-medium text-text-primary">
                                                                    {product.name}
                                                                </span>
                                                                <span className="tabular text-xs text-text-tertiary">
                                                                    ${product.price.toFixed(2)}
                                                                </span>
                                                                <StatusChip
                                                                    tone={
                                                                        fit.level === "recommended"
                                                                            ? "ok"
                                                                            : fit.level ===
                                                                                "possible"
                                                                              ? "info"
                                                                              : "warn"
                                                                    }
                                                                >
                                                                    {fit.level === "recommended"
                                                                        ? "High fit"
                                                                        : fit.level === "possible"
                                                                          ? "Possible fit"
                                                                          : "Low fit"}
                                                                </StatusChip>
                                                            </span>
                                                            <span className="mt-1 block text-xs leading-5 text-text-secondary">
                                                                {fit.reasons
                                                                    .slice(0, 2)
                                                                    .join(" · ")}
                                                            </span>
                                                            <span className="mt-1 block text-[11px] leading-4 text-text-tertiary">
                                                                Risk: {fit.risk}
                                                            </span>
                                                            <span className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px]">
                                                                <span className="text-text-tertiary">
                                                                    {product.category}
                                                                </span>
                                                                <StatusChip
                                                                    tone={
                                                                        product.readiness ===
                                                                        "Ready"
                                                                            ? "ok"
                                                                            : product.readiness ===
                                                                                "Setup needed"
                                                                              ? "warn"
                                                                              : "destructive"
                                                                    }
                                                                >
                                                                    {product.readiness}
                                                                </StatusChip>
                                                                <StatusChip
                                                                    tone={
                                                                        product.fulfillmentRisk ===
                                                                        "Low"
                                                                            ? "ok"
                                                                            : product.fulfillmentRisk ===
                                                                                "Medium"
                                                                              ? "warn"
                                                                              : "destructive"
                                                                    }
                                                                >
                                                                    {product.fulfillmentRisk} risk
                                                                </StatusChip>
                                                            </span>
                                                        </span>
                                                        <span
                                                            className={cn(
                                                                "grid h-5 w-5 shrink-0 place-items-center rounded-full border transition-all duration-[180ms] motion-reduce:transition-none",
                                                                active
                                                                    ? "border-primary bg-primary text-primary-foreground"
                                                                    : "border-hairline",
                                                            )}
                                                            aria-hidden
                                                        >
                                                            {active && (
                                                                <Check className="h-3 w-3" />
                                                            )}
                                                        </span>
                                                    </button>
                                                </li>
                                            );
                                        })}
                                    </Fragment>
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
