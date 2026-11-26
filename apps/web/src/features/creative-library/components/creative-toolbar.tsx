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
    X,
} from "lucide-react";
import type { CreativeSort } from "@/features/creative-library/types/creative";
import { cn } from "@/shared/lib/utils";

const sortLabels: Record<CreativeSort, string> = {
    "recent-saved": "Mới lưu gần đây",
    "recent-analyzed": "Mới phân tích",
    "dna-desc": "Điểm DNA cao nhất",
    duration: "Thời lượng",
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
                <Search
                    aria-hidden="true"
                    className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-tertiary"
                />
                <Input
                    value={query}
                    onChange={(e) => onQuery(e.target.value)}
                    placeholder="Tên video, câu mở đầu, người đăng hoặc từ khóa"
                    className="h-11 border-0 bg-surface-soft pl-9 pr-12 shadow-none"
                    aria-label="Tìm trong kho"
                />
                {query && (
                    <button
                        type="button"
                        onClick={() => onQuery("")}
                        aria-label="Xóa từ khóa tìm kiếm"
                        className="absolute right-0 top-0 grid size-11 place-items-center rounded-[10px] text-text-tertiary hover:bg-surface-muted hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
                    >
                        <X aria-hidden="true" className="size-4" />
                    </button>
                )}
            </div>
            <Button
                variant="ghost"
                className="min-h-11 bg-surface-soft hover:bg-surface-muted"
                onClick={onOpenFilters}
                aria-label={
                    activeFilterCount > 0
                        ? `Bộ lọc, đang áp dụng ${activeFilterCount} bộ lọc`
                        : "Bộ lọc"
                }
            >
                <SlidersHorizontal aria-hidden="true" className="h-4 w-4" />
                Bộ lọc
                {activeFilterCount > 0 && (
                    <span
                        aria-hidden="true"
                        className="ml-1 rounded-full bg-primary px-1.5 text-xs font-semibold text-primary-foreground"
                    >
                        {activeFilterCount}
                    </span>
                )}
            </Button>
            <DropdownMenu>
                <DropdownMenuTrigger asChild>
                    <Button
                        variant="ghost"
                        className="min-h-11 bg-surface-soft hover:bg-surface-muted"
                        aria-label={`Sắp xếp: ${sortLabels[sort]}`}
                    >
                        <ArrowDownWideNarrow aria-hidden="true" className="h-4 w-4" />
                        <span className="hidden sm:inline">{sortLabels[sort]}</span>
                        <span className="sm:hidden">Sắp xếp</span>
                    </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-52 border-0">
                    <DropdownMenuRadioGroup
                        value={sort}
                        onValueChange={(v) => onSort(v as CreativeSort)}
                    >
                        {(Object.keys(sortLabels) as CreativeSort[]).map((k) => (
                            <DropdownMenuRadioItem key={k} value={k} className="min-h-11">
                                {sortLabels[k]}
                            </DropdownMenuRadioItem>
                        ))}
                    </DropdownMenuRadioGroup>
                </DropdownMenuContent>
            </DropdownMenu>
            <div
                role="group"
                aria-label="Cách hiển thị tư liệu"
                className="inline-flex overflow-hidden rounded-[10px] bg-surface-soft"
            >
                <button
                    type="button"
                    aria-label="Hiển thị dạng lưới"
                    aria-pressed={view === "grid"}
                    onClick={() => onView("grid")}
                    className={cn(
                        "grid size-11 place-items-center transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring",
                        view === "grid"
                            ? "bg-primary-soft text-primary-active"
                            : "text-text-tertiary hover:bg-surface-soft",
                    )}
                >
                    <LayoutGrid aria-hidden="true" className="h-4 w-4" />
                </button>
                <button
                    type="button"
                    aria-label="Hiển thị dạng danh sách gọn"
                    aria-pressed={view === "compact"}
                    onClick={() => onView("compact")}
                    className={cn(
                        "grid size-11 place-items-center transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring",
                        view === "compact"
                            ? "bg-primary-soft text-primary-active"
                            : "text-text-tertiary hover:bg-surface-soft",
                    )}
                >
                    <Rows3 aria-hidden="true" className="h-4 w-4" />
                </button>
            </div>
            <Button
                variant="ghost"
                className={cn(
                    "min-h-11",
                    selectMode
                        ? "bg-primary-soft text-primary-active hover:bg-primary-soft"
                        : "bg-surface-soft hover:bg-surface-muted",
                )}
                aria-pressed={selectMode}
                onClick={() => onSelectMode(!selectMode)}
            >
                <CheckSquare aria-hidden="true" className="h-4 w-4" />
                {selectMode ? "Đang chọn" : "Chọn nhiều"}
            </Button>
        </div>
    );
}
