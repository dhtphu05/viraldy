import {
    Sheet,
    SheetContent,
    SheetDescription,
    SheetFooter,
    SheetHeader,
    SheetTitle,
} from "@/shared/ui/sheet";
import { Button } from "@/shared/ui/button";
import { Checkbox } from "@/shared/ui/checkbox";
import { Label } from "@/shared/ui/label";
import { cn } from "@/shared/lib/utils";
import type {
    CreativeFilterState,
    CreativePlatform,
    CreativeAnalysisStatus,
    ProductCategory,
    CreativeAngle,
} from "@/features/creative-library/types/creative";
import { emptyFilterState } from "@/features/creative-library/types/creative";
import { useState, useEffect } from "react";

const platforms: CreativePlatform[] = ["TikTok", "Meta", "YouTube Shorts", "UGC", "Other"];
const statuses: CreativeAnalysisStatus[] = [
    "unanalyzed",
    "ready",
    "processing",
    "analyzed",
    "failed",
];
const categories: ProductCategory[] = [
    "Home & Kitchen",
    "Pet",
    "Beauty",
    "POD Gifts",
    "Home Organization",
];
const angles: CreativeAngle[] = [
    "Problem–solution",
    "Before-and-after",
    "Testimonial",
    "Gift reaction",
    "Product demonstration",
    "Comparison",
    "Social proof",
    "Day-in-the-life",
];

const statusLabel: Record<CreativeAnalysisStatus, string> = {
    unanalyzed: "Unanalyzed",
    ready: "Ready to analyze",
    processing: "Processing",
    analyzed: "Analyzed",
    failed: "Failed",
};

function toggle<T>(arr: T[], v: T): T[] {
    return arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v];
}

export function FilterSheet({
    open,
    onOpenChange,
    value,
    onApply,
}: {
    open: boolean;
    onOpenChange: (v: boolean) => void;
    value: CreativeFilterState;
    onApply: (v: CreativeFilterState) => void;
}) {
    const [draft, setDraft] = useState<CreativeFilterState>(value);
    useEffect(() => {
        if (open) setDraft(value);
    }, [open, value]);

    return (
        <Sheet open={open} onOpenChange={onOpenChange}>
            <SheetContent className="flex w-full flex-col p-0 sm:max-w-md">
                <SheetHeader className="border-b border-hairline px-6 py-4">
                    <SheetTitle className="text-base font-semibold">Filters</SheetTitle>
                    <SheetDescription className="text-xs">
                        Narrow the library by platform, status, product fit, and more.
                    </SheetDescription>
                </SheetHeader>

                <div className="flex-1 overflow-y-auto px-6 py-5">
                    <div className="flex flex-col gap-6">
                        <FilterGroup title="Platform">
                            {platforms.map((p) => (
                                <CheckOption
                                    key={p}
                                    id={`f-p-${p}`}
                                    checked={draft.platforms.includes(p)}
                                    onCheckedChange={() =>
                                        setDraft((d) => ({
                                            ...d,
                                            platforms: toggle(d.platforms, p),
                                        }))
                                    }
                                    label={p}
                                />
                            ))}
                        </FilterGroup>

                        <FilterGroup title="Analysis status">
                            {statuses.map((s) => (
                                <CheckOption
                                    key={s}
                                    id={`f-s-${s}`}
                                    checked={draft.status.includes(s)}
                                    onCheckedChange={() =>
                                        setDraft((d) => ({ ...d, status: toggle(d.status, s) }))
                                    }
                                    label={statusLabel[s]}
                                />
                            ))}
                        </FilterGroup>

                        <FilterGroup title="Product category">
                            {categories.map((c) => (
                                <CheckOption
                                    key={c}
                                    id={`f-c-${c}`}
                                    checked={draft.categories.includes(c)}
                                    onCheckedChange={() =>
                                        setDraft((d) => ({
                                            ...d,
                                            categories: toggle(d.categories, c),
                                        }))
                                    }
                                    label={c}
                                />
                            ))}
                        </FilterGroup>

                        <FilterGroup title="Angle">
                            {angles.map((a) => (
                                <CheckOption
                                    key={a}
                                    id={`f-a-${a}`}
                                    checked={draft.angles.includes(a)}
                                    onCheckedChange={() =>
                                        setDraft((d) => ({ ...d, angles: toggle(d.angles, a) }))
                                    }
                                    label={a}
                                />
                            ))}
                        </FilterGroup>

                        <FilterGroup title="Product linkage">
                            {(["any", "linked", "unlinked"] as const).map((v) => (
                                <RadioOption
                                    key={v}
                                    id={`f-link-${v}`}
                                    checked={draft.linkage === v}
                                    onChange={() => setDraft((d) => ({ ...d, linkage: v }))}
                                    label={
                                        v === "any"
                                            ? "Any"
                                            : v === "linked"
                                              ? "Linked to a product"
                                              : "Not linked"
                                    }
                                />
                            ))}
                        </FilterGroup>

                        <FilterGroup title="Campaign usage">
                            {(["any", "yes", "no"] as const).map((v) => (
                                <RadioOption
                                    key={v}
                                    id={`f-camp-${v}`}
                                    checked={draft.usedInCampaign === v}
                                    onChange={() => setDraft((d) => ({ ...d, usedInCampaign: v }))}
                                    label={
                                        v === "any"
                                            ? "Any"
                                            : v === "yes"
                                              ? "Used in a campaign"
                                              : "Not yet used"
                                    }
                                />
                            ))}
                        </FilterGroup>
                    </div>
                </div>

                <SheetFooter className="flex-row items-center justify-between gap-2 border-t border-hairline px-6 py-3">
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setDraft({ ...emptyFilterState, boardId: draft.boardId })}
                    >
                        Clear all
                    </Button>
                    <Button
                        size="sm"
                        onClick={() => {
                            onApply(draft);
                            onOpenChange(false);
                        }}
                    >
                        Apply filters
                    </Button>
                </SheetFooter>
            </SheetContent>
        </Sheet>
    );
}

function FilterGroup({ title, children }: { title: string; children: React.ReactNode }) {
    return (
        <div>
            <p className="mb-2 text-[10px] font-semibold uppercase text-text-tertiary">{title}</p>
            <div className="flex flex-col gap-1.5">{children}</div>
        </div>
    );
}

function CheckOption({
    id,
    checked,
    onCheckedChange,
    label,
}: {
    id: string;
    checked: boolean;
    onCheckedChange: () => void;
    label: string;
}) {
    return (
        <label
            htmlFor={id}
            className={cn(
                "flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-surface-soft",
            )}
        >
            <Checkbox id={id} checked={checked} onCheckedChange={onCheckedChange} />
            <span>{label}</span>
        </label>
    );
}

function RadioOption({
    id,
    checked,
    onChange,
    label,
}: {
    id: string;
    checked: boolean;
    onChange: () => void;
    label: string;
}) {
    return (
        <label
            htmlFor={id}
            className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-surface-soft"
        >
            <input
                id={id}
                type="radio"
                className="h-3.5 w-3.5 accent-primary"
                checked={checked}
                onChange={onChange}
            />
            <span>{label}</span>
        </label>
    );
}

export { Label as _L };
