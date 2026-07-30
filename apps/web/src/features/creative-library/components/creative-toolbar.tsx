import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuRadioGroup,
    DropdownMenuRadioItem,
    DropdownMenuTrigger,
} from "@/shared/ui/dropdown-menu";
import {
    Search,
    SlidersHorizontal,
    ArrowDownWideNarrow,
    LayoutGrid,
    Rows3,
    CheckSquare,
} from "lucide-react";
import type { CreativeSort } from "@/features/creative-library/types/creative";
import { cn } from "@/shared/lib/utils";

const sortLabels: Record<CreativeSort, string> = {
    "recent-saved": "Recently saved",
    "recent-analyzed": "Recently analyzed",
    "dna-desc": "Highest DNA score",
    duration: "Duration",
    az: "A–Z",
};

export function CreativeToolbar({
    query,
    onQuery,
    onOpenFilters,
    activeFilterCount,
    sort,
    onSort,
    view,
    onView,
    selectMode,
    onSelectMode,
    className,
}: {
    query: string;
    onQuery: (v: string) => void;
    onOpenFilters: () => void;
    activeFilterCount: number;
    sort: CreativeSort;
    onSort: (s: CreativeSort) => void;
    view: "grid" | "compact";
    onView: (v: "grid" | "compact") => void;
    selectMode: boolean;
    onSelectMode: (v: boolean) => void;
    className?: string;
}) {
    return (
        <div className={cn("flex min-w-0 flex-wrap items-center gap-2", className)}>
            <div className="relative min-w-0 basis-full sm:max-w-md sm:flex-1 sm:basis-auto">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-tertiary" />
                <Input
                    value={query}
                    onChange={(e) => onQuery(e.target.value)}
                    placeholder="Search hook, creator, angle, tag…"
                    className="pl-9"
                    aria-label="Search creatives"
                />
            </div>
            <Button variant="secondary" size="sm" onClick={onOpenFilters}>
                <SlidersHorizontal className="h-4 w-4" />
                Filters
                {activeFilterCount > 0 && (
                    <span className="ml-1 rounded-full bg-primary px-1.5 text-[10px] font-semibold text-primary-foreground">
                        {activeFilterCount}
                    </span>
                )}
            </Button>
            <DropdownMenu>
                <DropdownMenuTrigger asChild>
                    <Button variant="secondary" size="sm">
                        <ArrowDownWideNarrow className="h-4 w-4" />
                        <span className="hidden sm:inline">{sortLabels[sort]}</span>
                        <span className="sm:hidden">Sort</span>
                    </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48">
                    <DropdownMenuRadioGroup
                        value={sort}
                        onValueChange={(v) => onSort(v as CreativeSort)}
                    >
                        {(Object.keys(sortLabels) as CreativeSort[]).map((k) => (
                            <DropdownMenuRadioItem key={k} value={k}>
                                {sortLabels[k]}
                            </DropdownMenuRadioItem>
                        ))}
                    </DropdownMenuRadioGroup>
                </DropdownMenuContent>
            </DropdownMenu>
            <div
                role="group"
                aria-label="Creative layout"
                className="inline-flex overflow-hidden rounded-[10px] border border-control-border bg-surface"
            >
                <button
                    type="button"
                    aria-label="Grid view"
                    aria-pressed={view === "grid"}
                    onClick={() => onView("grid")}
                    className={cn(
                        "grid h-9 w-9 place-items-center transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring",
                        view === "grid"
                            ? "bg-primary-soft text-primary-active"
                            : "text-text-tertiary hover:bg-surface-soft",
                    )}
                >
                    <LayoutGrid className="h-4 w-4" />
                </button>
                <button
                    type="button"
                    aria-label="Compact view"
                    aria-pressed={view === "compact"}
                    onClick={() => onView("compact")}
                    className={cn(
                        "grid h-9 w-9 place-items-center border-l border-control-border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring",
                        view === "compact"
                            ? "bg-primary-soft text-primary-active"
                            : "text-text-tertiary hover:bg-surface-soft",
                    )}
                >
                    <Rows3 className="h-4 w-4" />
                </button>
            </div>
            <Button
                variant={selectMode ? "default" : "secondary"}
                size="sm"
                onClick={() => onSelectMode(!selectMode)}
            >
                <CheckSquare className="h-4 w-4" />
                {selectMode ? "Selecting" : "Select"}
            </Button>
        </div>
    );
}
