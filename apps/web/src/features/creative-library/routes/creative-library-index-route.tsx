import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { AppShell } from "@/widgets/app-shell/app-shell";
import { PageHeader } from "@/shared/ui/page-header";
import { Button } from "@/shared/ui/button";
import { Plus, Sparkles, X, PanelLeft } from "lucide-react";
import { useAppStore } from "@/app/store/app-store";
import { useMemo, useState } from "react";
import { BoardRail } from "@/features/creative-library/components/board-rail";
import { CreativeToolbar } from "@/features/creative-library/components/creative-toolbar";
import { CreativeCard } from "@/features/creative-library/components/creative-card";
import { FilterSheet } from "@/features/creative-library/components/filter-sheet";
import { ImportCreativeDialog } from "@/features/creative-library/components/import-creative-dialog";
import { AnalyzeDnaDialog } from "@/features/creative-library/components/analyze-dna-dialog";
import { AdaptToProductDialog } from "@/features/creative-library/components/adapt-to-product-dialog";
import { NewBoardDialog } from "@/features/creative-library/components/new-board-dialog";
import { MoveToBoardDialog } from "@/features/creative-library/components/move-to-board-dialog";
import { AnalysisJobsRunner } from "@/features/creative-library/components/analysis-jobs-runner";
import { EmptyState } from "@/shared/ui/empty-state";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/shared/ui/sheet";
import type {
    CreativeBoard,
    CreativeFilterState,
    CreativeSort,
} from "@/features/creative-library/types/creative";
import { emptyFilterState } from "@/features/creative-library/types/creative";
import { seedProducts } from "@/features/products/data/products";
import { Images } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/shared/lib/utils";

export const Route = createFileRoute("/creative-library/")({
    head: () => ({
        meta: [
            { title: "Creative Library — Viraldy" },
            {
                name: "description",
                content:
                    "Save, decode, and reuse creative patterns for TikTok Shop, POD, and cross-border products.",
            },
        ],
    }),
    component: CreativeLibraryPage,
});

function CreativeLibraryPage() {
    const boards = useAppStore((s) => s.boards);
    const creatives = useAppStore((s) => s.creatives);
    const duplicate = useAppStore((s) => s.duplicateCreative);
    const archive = useAppStore((s) => s.archiveCreative);

    const navigate = useNavigate();

    const [activeBoard, setActiveBoard] = useState<string>("b-all");
    const [query, setQuery] = useState("");
    const [filters, setFilters] = useState<CreativeFilterState>(emptyFilterState);
    const [sort, setSort] = useState<CreativeSort>("recent-saved");
    const [view, setView] = useState<"grid" | "compact">("grid");
    const [selectMode, setSelectMode] = useState(false);
    const [selected, setSelected] = useState<Set<string>>(new Set());

    const [filtersOpen, setFiltersOpen] = useState(false);
    const [importOpen, setImportOpen] = useState(false);
    const [analyzeOpen, setAnalyzeOpen] = useState(false);
    const [analyzeIds, setAnalyzeIds] = useState<string[]>([]);
    const [adaptFor, setAdaptFor] = useState<{ id: string; title: string } | null>(null);
    const [newBoardOpen, setNewBoardOpen] = useState(false);
    const [renameBoard, setRenameBoard] = useState<CreativeBoard | null>(null);
    const [moveForId, setMoveForId] = useState<string | null>(null);
    const [boardSheetOpen, setBoardSheetOpen] = useState(false);

    const productMap = useMemo(() => {
        const m = new Map<string, string>();
        for (const p of seedProducts) m.set(p.id, p.name);
        return m;
    }, []);

    const filtered = useMemo(() => {
        const q = query.trim().toLowerCase();
        let list = creatives.filter((c) => !c.archived);
        const board = boards.find((b) => b.id === activeBoard);
        if (board) {
            if (board.filter === "recent") {
                list = list.filter(
                    (c) => Date.now() - new Date(c.savedAt).getTime() < 7 * 86_400_000,
                );
            } else if (board.filter === "unassigned") {
                list = list.filter((c) => c.boardIds.length === 0);
            } else if (!board.filter) {
                list = list.filter((c) => c.boardIds.includes(board.id));
            }
        }

        if (q) {
            list = list.filter((c) => {
                const hay = [
                    c.title,
                    c.hookExcerpt,
                    c.brandOrCreator,
                    c.angle,
                    c.category,
                    c.notes ?? "",
                    ...c.tags,
                ]
                    .join(" ")
                    .toLowerCase();
                return hay.includes(q);
            });
        }
        if (filters.platforms.length)
            list = list.filter((c) => filters.platforms.includes(c.platform));
        if (filters.status.length)
            list = list.filter((c) => filters.status.includes(c.analysisStatus));
        if (filters.categories.length)
            list = list.filter((c) => filters.categories.includes(c.category));
        if (filters.angles.length) list = list.filter((c) => filters.angles.includes(c.angle));
        if (filters.linkage === "linked") list = list.filter((c) => !!c.linkedProductId);
        if (filters.linkage === "unlinked") list = list.filter((c) => !c.linkedProductId);
        if (filters.usedInCampaign === "yes") list = list.filter((c) => !!c.usedInCampaignId);
        if (filters.usedInCampaign === "no") list = list.filter((c) => !c.usedInCampaignId);

        switch (sort) {
            case "recent-saved":
                list = [...list].sort((a, b) => +new Date(b.savedAt) - +new Date(a.savedAt));
                break;
            case "recent-analyzed":
                list = [...list].sort(
                    (a, b) => +new Date(b.analyzedAt ?? 0) - +new Date(a.analyzedAt ?? 0),
                );
                break;
            case "dna-desc":
                list = [...list].sort((a, b) => (b.dnaScore ?? -1) - (a.dnaScore ?? -1));
                break;
            case "duration":
                list = [...list].sort((a, b) => a.durationSec - b.durationSec);
                break;
            case "az":
                list = [...list].sort((a, b) => a.title.localeCompare(b.title));
                break;
        }
        return list;
    }, [creatives, boards, activeBoard, query, filters, sort]);

    const activeFilterCount =
        filters.platforms.length +
        filters.status.length +
        filters.categories.length +
        filters.angles.length +
        (filters.linkage !== "any" ? 1 : 0) +
        (filters.usedInCampaign !== "any" ? 1 : 0);

    const selectedArr = Array.from(selected);
    const selectedEligible = selectedArr.filter((id) => {
        const c = creatives.find((x) => x.id === id);
        return c && c.analysisStatus !== "processing";
    });

    function toggleSelected(id: string) {
        setSelected((prev) => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });
    }

    function openAnalyze(ids: string[]) {
        if (ids.length === 0) return;
        setAnalyzeIds(ids);
        setAnalyzeOpen(true);
    }

    function handleCardAction(id: string, action: string) {
        const c = creatives.find((x) => x.id === id);
        if (!c) return;
        switch (action) {
            case "open":
                navigate({ to: "/creative-library/$creativeId", params: { creativeId: id } });
                break;
            case "analyze":
                openAnalyze([id]);
                break;
            case "adapt":
                setAdaptFor({ id, title: c.title });
                break;
            case "add-to-campaign":
                toast("Add to campaign", {
                    description: "Campaign Pack composer arrives in the next phase.",
                });
                break;
            case "move-board":
                setMoveForId(id);
                break;
            case "duplicate":
                duplicate(id);
                toast.success("Reference duplicated");
                break;
            case "archive":
                archive(id);
                toast("Reference archived");
                break;
        }
    }

    const gridCols =
        view === "compact"
            ? "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
            : "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4";

    const emptyBoard = filtered.length === 0 && !query && activeFilterCount === 0;
    const emptyFilter = filtered.length === 0 && (query || activeFilterCount > 0);

    return (
        <AppShell>
            <AnalysisJobsRunner />
            <div className="flex flex-col gap-6">
                <PageHeader
                    title="Creative Library"
                    description="Save, decode, and reuse creative patterns for your products and campaigns."
                    actions={
                        <>
                            <Button
                                variant="secondary"
                                size="sm"
                                onClick={() => openAnalyze(selectedEligible)}
                                disabled={selectedEligible.length === 0}
                            >
                                <Sparkles className="h-4 w-4" />
                                Analyze selected
                                {selectedEligible.length > 0 && (
                                    <span className="ml-1 rounded-full bg-primary-soft px-1.5 text-[10px] font-semibold text-primary-active">
                                        {selectedEligible.length}
                                    </span>
                                )}
                            </Button>
                            <Button size="sm" onClick={() => setImportOpen(true)}>
                                <Plus className="h-4 w-4" />
                                Import creative
                            </Button>
                        </>
                    }
                />

                <div className="flex gap-6">
                    {/* Board rail — desktop only */}
                    <aside aria-label="Boards" className="hidden w-[220px] shrink-0 lg:block">
                        <div className="sticky top-4">
                            <BoardRail
                                activeBoardId={activeBoard}
                                onSelect={setActiveBoard}
                                onNewBoard={() => setNewBoardOpen(true)}
                                onRenameBoard={(b) => setRenameBoard(b)}
                            />
                        </div>
                    </aside>

                    {/* Main */}
                    <div className="flex min-w-0 flex-1 flex-col gap-4">
                        <div className="flex items-center gap-2">
                            <Button
                                variant="secondary"
                                size="sm"
                                className="lg:hidden"
                                onClick={() => setBoardSheetOpen(true)}
                            >
                                <PanelLeft className="h-4 w-4" />
                                Boards
                            </Button>
                            <CreativeToolbar
                                query={query}
                                onQuery={setQuery}
                                onOpenFilters={() => setFiltersOpen(true)}
                                activeFilterCount={activeFilterCount}
                                sort={sort}
                                onSort={setSort}
                                view={view}
                                onView={setView}
                                selectMode={selectMode}
                                onSelectMode={(v) => {
                                    setSelectMode(v);
                                    if (!v) setSelected(new Set());
                                }}
                                className="flex-1"
                            />
                        </div>

                        {/* Active filter chips */}
                        {activeFilterCount > 0 && (
                            <div className="flex flex-wrap items-center gap-1.5">
                                {filters.platforms.map((p) => (
                                    <Chip
                                        key={`p-${p}`}
                                        onRemove={() =>
                                            setFilters((f) => ({
                                                ...f,
                                                platforms: f.platforms.filter((x) => x !== p),
                                            }))
                                        }
                                    >
                                        Platform: {p}
                                    </Chip>
                                ))}
                                {filters.status.map((s) => (
                                    <Chip
                                        key={`s-${s}`}
                                        onRemove={() =>
                                            setFilters((f) => ({
                                                ...f,
                                                status: f.status.filter((x) => x !== s),
                                            }))
                                        }
                                    >
                                        Status: {s}
                                    </Chip>
                                ))}
                                {filters.categories.map((c) => (
                                    <Chip
                                        key={`c-${c}`}
                                        onRemove={() =>
                                            setFilters((f) => ({
                                                ...f,
                                                categories: f.categories.filter((x) => x !== c),
                                            }))
                                        }
                                    >
                                        {c}
                                    </Chip>
                                ))}
                                {filters.angles.map((a) => (
                                    <Chip
                                        key={`a-${a}`}
                                        onRemove={() =>
                                            setFilters((f) => ({
                                                ...f,
                                                angles: f.angles.filter((x) => x !== a),
                                            }))
                                        }
                                    >
                                        {a}
                                    </Chip>
                                ))}
                                {filters.linkage !== "any" && (
                                    <Chip
                                        onRemove={() =>
                                            setFilters((f) => ({ ...f, linkage: "any" }))
                                        }
                                    >
                                        {filters.linkage === "linked" ? "Linked" : "Unlinked"}
                                    </Chip>
                                )}
                                {filters.usedInCampaign !== "any" && (
                                    <Chip
                                        onRemove={() =>
                                            setFilters((f) => ({ ...f, usedInCampaign: "any" }))
                                        }
                                    >
                                        {filters.usedInCampaign === "yes"
                                            ? "In a campaign"
                                            : "Not in a campaign"}
                                    </Chip>
                                )}
                                <button
                                    type="button"
                                    onClick={() => setFilters(emptyFilterState)}
                                    className="ml-1 text-xs text-text-secondary underline-offset-2 hover:text-text-primary hover:underline"
                                >
                                    Clear all
                                </button>
                            </div>
                        )}

                        {/* Grid */}
                        {emptyBoard && (
                            <div className="surface-card inner-top-highlight p-10">
                                <EmptyState
                                    icon={Images}
                                    title="Build this board with useful creative references"
                                    description="Import an ad, creator video, or UGC example, then analyze its Creative DNA."
                                    action={
                                        <Button size="sm" onClick={() => setImportOpen(true)}>
                                            <Plus className="h-4 w-4" />
                                            Import creative
                                        </Button>
                                    }
                                />
                            </div>
                        )}
                        {emptyFilter && (
                            <div className="surface-card inner-top-highlight p-10">
                                <EmptyState
                                    title="No creatives match these filters"
                                    description="Try clearing filters or searching the whole library."
                                    action={
                                        <div className="flex gap-2">
                                            <Button
                                                variant="secondary"
                                                size="sm"
                                                onClick={() => {
                                                    setFilters(emptyFilterState);
                                                    setQuery("");
                                                }}
                                            >
                                                Clear filters
                                            </Button>
                                            <Button
                                                size="sm"
                                                onClick={() => {
                                                    setActiveBoard("b-all");
                                                    setFilters(emptyFilterState);
                                                    setQuery("");
                                                }}
                                            >
                                                Search all creatives
                                            </Button>
                                        </div>
                                    }
                                />
                            </div>
                        )}
                        {!emptyBoard && !emptyFilter && (
                            <div className={cn("grid gap-4", gridCols)}>
                                {filtered.map((c) => (
                                    <CreativeCard
                                        key={c.id}
                                        creative={c}
                                        selected={selected.has(c.id)}
                                        selectable={selectMode}
                                        compact={view === "compact"}
                                        productLabel={
                                            c.linkedProductId
                                                ? productMap.get(c.linkedProductId)
                                                : undefined
                                        }
                                        onToggleSelect={() => toggleSelected(c.id)}
                                        onAction={(a) => handleCardAction(c.id, a)}
                                    />
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Dialogs and sheets */}
            <FilterSheet
                open={filtersOpen}
                onOpenChange={setFiltersOpen}
                value={filters}
                onApply={setFilters}
            />
            <ImportCreativeDialog
                open={importOpen}
                onOpenChange={setImportOpen}
                defaultBoardId={activeBoard}
            />
            <AnalyzeDnaDialog
                open={analyzeOpen}
                onOpenChange={(v) => {
                    setAnalyzeOpen(v);
                    if (!v) setAnalyzeIds([]);
                }}
                creativeIds={analyzeIds}
            />
            {adaptFor && (
                <AdaptToProductDialog
                    open={!!adaptFor}
                    onOpenChange={(v) => !v && setAdaptFor(null)}
                    creativeId={adaptFor.id}
                    creativeTitle={adaptFor.title}
                />
            )}
            <NewBoardDialog
                open={newBoardOpen || !!renameBoard}
                onOpenChange={(v) => {
                    if (!v) {
                        setNewBoardOpen(false);
                        setRenameBoard(null);
                    }
                }}
                renameBoardId={renameBoard?.id}
                initialName={renameBoard?.name}
            />
            {moveForId && (
                <MoveToBoardDialog
                    open={!!moveForId}
                    onOpenChange={(v) => !v && setMoveForId(null)}
                    creativeId={moveForId}
                />
            )}
            <Sheet open={boardSheetOpen} onOpenChange={setBoardSheetOpen}>
                <SheetContent side="left" className="w-full sm:max-w-xs">
                    <SheetHeader className="mb-4">
                        <SheetTitle>Boards</SheetTitle>
                    </SheetHeader>
                    <BoardRail
                        activeBoardId={activeBoard}
                        onSelect={(id) => {
                            setActiveBoard(id);
                            setBoardSheetOpen(false);
                        }}
                        onNewBoard={() => {
                            setBoardSheetOpen(false);
                            setNewBoardOpen(true);
                        }}
                        onRenameBoard={(b) => {
                            setBoardSheetOpen(false);
                            setRenameBoard(b);
                        }}
                    />
                </SheetContent>
            </Sheet>
        </AppShell>
    );
}

function Chip({ children, onRemove }: { children: React.ReactNode; onRemove: () => void }) {
    return (
        <span className="inline-flex items-center gap-1 rounded-full bg-surface-soft px-2 py-0.5 text-xs text-text-secondary">
            {children}
            <button
                type="button"
                onClick={onRemove}
                aria-label="Remove filter"
                className="grid h-4 w-4 place-items-center rounded-full text-text-tertiary hover:bg-surface-muted hover:text-text-primary"
            >
                <X className="h-3 w-3" />
            </button>
        </span>
    );
}
