import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { AppShell } from "@/widgets/app-shell/app-shell";
import { PageHeader } from "@/shared/ui/page-header";
import { Button } from "@/shared/ui/button";
import { FolderInput, Images, Megaphone, PanelLeft, Sparkles, X } from "lucide-react";
import { useAppStore } from "@/app/store/app-store";
import { useEffect, useMemo, useState } from "react";
import { BoardRail } from "@/features/creative-library/components/board-rail";
import { CreativeToolbar } from "@/features/creative-library/components/creative-toolbar";
import { CreativeCard } from "@/features/creative-library/components/creative-card";
import { FilterSheet } from "@/features/creative-library/components/filter-sheet";
import { ImportCreativeDialog } from "@/features/creative-library/components/import-creative-dialog";
import { AnalyzeDnaDialog } from "@/features/creative-library/components/analyze-dna-dialog";
import { AdaptToProductDialog } from "@/features/creative-library/components/adapt-to-product-dialog";
import { NewBoardDialog } from "@/features/creative-library/components/new-board-dialog";
import { MoveToBoardDialog } from "@/features/creative-library/components/move-to-board-dialog";
import { ActionTray } from "@/shared/ui/action-tray";
import { EmptyState } from "@/shared/ui/empty-state";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/shared/ui/sheet";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { isWithinDemoDays } from "@/shared/mocks/time";
import type {
    CreativeBoard,
    CreativeFilterState,
    CreativeSort,
} from "@/features/creative-library/types/creative";
import { emptyFilterState } from "@/features/creative-library/types/creative";
import { toast } from "sonner";
import { cn } from "@/shared/lib/utils";
import { ViraldyIcon } from "@/shared/ui/viraldy-icon";
import { TikTokSearchPanel } from "@/features/creative-library/components/tiktok-search-panel";
import { ViralVideoFinder } from "@/features/creative-library/components/viral-video-finder";
import { useApiWorkspace } from "@/shared/hooks/use-workspace";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/shared/ui/tabs";
import { getCreativeMediaKind, matchesCreativeQuery } from "../lib/library-catalog";
import type { CreativeReference } from "../types/creative";
import { CreativePreviewDialog } from "../components/creative-preview-dialog";

export const Route = createFileRoute("/creative-library/")({
    validateSearch: (search: Record<string, unknown>) => ({
        import:
            search.import === true ||
            search.import === "true" ||
            search.import === "1" ||
            search.import === 1
                ? true
                : undefined,
    }),
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
    const routeSearch = Route.useSearch();
    const boards = useAppStore((s) => s.boards);
    const creatives = useAppStore((s) => s.creatives);
    const duplicate = useAppStore((s) => s.duplicateCreative);
    const archive = useAppStore((s) => s.archiveCreative);
    const campaignDraft = useAppStore((s) => s.campaignDraft);
    const setDraft = useAppStore((s) => s.setDraft);
    const { workspaceId } = useApiWorkspace();

    const navigate = useNavigate();

    const [activeBoard, setActiveBoard] = useState<string>("b-all");
    const [query, setQuery] = useState("");
    const [filters, setFilters] = useState<CreativeFilterState>(emptyFilterState);
    const [sort, setSort] = useState<CreativeSort>("recent-saved");
    const [view, setView] = useState<"grid" | "compact">("grid");
    const [section, setSection] = useState("saved");
    const [sourceFilter, setSourceFilter] = useState<"all" | "video" | "image" | "reference">(
        "video",
    );
    const [previewCreative, setPreviewCreative] = useState<CreativeReference | null>(null);
    const [selectMode, setSelectMode] = useState(false);
    const [selected, setSelected] = useState<Set<string>>(new Set());

    const [filtersOpen, setFiltersOpen] = useState(false);
    const [importOpen, setImportOpen] = useState(false);
    const [analyzeOpen, setAnalyzeOpen] = useState(false);
    const [analyzeIds, setAnalyzeIds] = useState<string[]>([]);
    const [adaptFor, setAdaptFor] = useState<{ id: string; title: string } | null>(null);
    const [newBoardOpen, setNewBoardOpen] = useState(false);
    const [renameBoard, setRenameBoard] = useState<CreativeBoard | null>(null);
    const [moveForIds, setMoveForIds] = useState<string[]>([]);
    const [boardSheetOpen, setBoardSheetOpen] = useState(false);

    useEffect(() => {
        const importParam = new URLSearchParams(window.location.search).get("import");
        if (!routeSearch.import && importParam !== "1" && importParam !== "true") return;
        setImportOpen(true);
    }, [routeSearch.import]);

    const filtered = useMemo(() => {
        let list = creatives.filter((c) => !c.archived);
        const board = boards.find((b) => b.id === activeBoard);
        if (board) {
            if (board.filter === "recent") {
                list = list.filter((c) => isWithinDemoDays(c.savedAt, 7));
            } else if (board.filter === "unassigned") {
                list = list.filter((c) => c.boardIds.length === 0);
            } else if (!board.filter) {
                list = list.filter((c) => c.boardIds.includes(board.id));
            }
        }

        list = list.filter((c) => matchesCreativeQuery(c, query));
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

    const shown = filtered.filter(
        (creative) => sourceFilter === "all" || getCreativeMediaKind(creative) === sourceFilter,
    );
    const videoCount = filtered.filter(
        (creative) => getCreativeMediaKind(creative) === "video",
    ).length;
    const referenceCount = filtered.filter(
        (creative) => getCreativeMediaKind(creative) === "reference",
    ).length;
    const imageCount = filtered.filter(
        (creative) => getCreativeMediaKind(creative) === "image",
    ).length;
    const savedCount = creatives.filter((creative) => !creative.archived).length;

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

    function addToCampaign(ids: string[]) {
        if (ids.length === 0) return;
        setDraft({
            referenceCreativeIds: Array.from(
                new Set([...(campaignDraft.referenceCreativeIds ?? []), ...ids]),
            ),
        });
        toast.success(
            ids.length === 1 ? "Đã thêm tư liệu vào bản nháp" : `Đã thêm ${ids.length} tư liệu`,
            {
                description: "Đang mở bản nháp chiến dịch.",
            },
        );
        void navigate({ to: "/campaigns/new" });
    }

    function handleCardAction(id: string, action: string) {
        const c = creatives.find((x) => x.id === id);
        if (!c) return;
        switch (action) {
            case "preview":
            case "remake":
                setPreviewCreative(c);
                break;
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
                addToCampaign([id]);
                break;
            case "move-board":
                setMoveForIds([id]);
                break;
            case "duplicate":
                duplicate(id);
                toast.success("Đã tạo bản sao tư liệu");
                break;
            case "archive":
                archive(id);
                toast("Đã lưu trữ tư liệu");
                break;
        }
    }

    const gridCols =
        view === "compact"
            ? "grid-cols-1 2xl:grid-cols-2"
            : "grid-cols-1 sm:grid-cols-2 2xl:grid-cols-3";

    const emptyBoard =
        shown.length === 0 && !query.trim() && activeFilterCount === 0 && sourceFilter === "all";
    const emptyFilter =
        shown.length === 0 && (query.trim() || activeFilterCount > 0 || sourceFilter !== "all");

    return (
        <AppShell>
            <div className="flex flex-col gap-6">
                <PageHeader
                    title="Kho video"
                    description="Lưu cách mở đầu, góc quay và ý tưởng bạn thích. Xem lại rồi dùng video làm mẫu cho Smart Remake."
                    actions={
                        <Button className="min-h-11" onClick={() => setImportOpen(true)}>
                            <ViraldyIcon name="importCreative" size="sm" />
                            Thêm tư liệu
                        </Button>
                    }
                />

                <Tabs value={section} onValueChange={setSection} className="min-w-0">
                    <TabsList className="mb-5 grid h-auto min-h-12 w-full grid-cols-2 gap-1 rounded-2xl border-0 bg-surface-soft p-1 sm:w-fit">
                        <TabsTrigger value="saved" className="min-h-11 rounded-xl px-5">
                            Đã lưu <span className="ml-2 tabular-nums">{savedCount}</span>
                        </TabsTrigger>
                        <TabsTrigger value="discover" className="min-h-11 rounded-xl px-5">
                            Khám phá video
                        </TabsTrigger>
                    </TabsList>
                    <TabsContent
                        value="saved"
                        forceMount
                        className="m-0 data-[state=inactive]:hidden"
                    >
                        <div className="mb-5 rounded-2xl bg-surface px-4 py-3 text-sm text-text-secondary">
                            Bộ sưu tập lưu trên trình duyệt này. Tư liệu minh họa được gắn nhãn
                            riêng; mục chưa có file vẫn có thể lưu để tham khảo.
                        </div>
                        <div className="flex gap-5">
                            {/* Board rail — desktop only */}
                            <aside
                                aria-label="Bộ sưu tập"
                                className="hidden w-56 shrink-0 lg:block"
                            >
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
                                <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-center">
                                    <Button
                                        variant="secondary"
                                        size="sm"
                                        className="lg:hidden"
                                        onClick={() => setBoardSheetOpen(true)}
                                    >
                                        <PanelLeft className="h-4 w-4" />
                                        Bộ sưu tập
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

                                <div className="space-y-3">
                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                        <h2 className="text-base font-semibold text-text-primary">
                                            Tư liệu đã lưu
                                        </h2>
                                        <p
                                            role="status"
                                            className="text-sm tabular-nums text-text-secondary"
                                        >
                                            {shown.length} kết quả
                                        </p>
                                    </div>
                                    <div
                                        role="group"
                                        aria-label="Loại tư liệu"
                                        className="flex flex-wrap gap-2"
                                    >
                                        {(
                                            [
                                                ["all", "Tất cả", filtered.length],
                                                ["video", "Có nguồn video", videoCount],
                                                ...(imageCount
                                                    ? [["image", "Ảnh", imageCount] as const]
                                                    : []),
                                                ["reference", "Chưa có file", referenceCount],
                                            ] as const
                                        ).map(([value, label, count]) => (
                                            <Button
                                                key={value}
                                                variant="ghost"
                                                className={cn(
                                                    "min-h-11 rounded-xl border-0 bg-surface-soft",
                                                    sourceFilter === value &&
                                                        "bg-primary-soft text-primary-active",
                                                )}
                                                aria-pressed={sourceFilter === value}
                                                onClick={() => setSourceFilter(value)}
                                            >
                                                {label}{" "}
                                                <span className="tabular-nums">{count}</span>
                                            </Button>
                                        ))}
                                    </div>
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
                                                        platforms: f.platforms.filter(
                                                            (x) => x !== p,
                                                        ),
                                                    }))
                                                }
                                            >
                                                Nền tảng: {p}
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
                                                Trạng thái: {s}
                                            </Chip>
                                        ))}
                                        {filters.categories.map((c) => (
                                            <Chip
                                                key={`c-${c}`}
                                                onRemove={() =>
                                                    setFilters((f) => ({
                                                        ...f,
                                                        categories: f.categories.filter(
                                                            (x) => x !== c,
                                                        ),
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
                                                {filters.linkage === "linked"
                                                    ? "Đã gắn sản phẩm"
                                                    : "Chưa gắn sản phẩm"}
                                            </Chip>
                                        )}
                                        {filters.usedInCampaign !== "any" && (
                                            <Chip
                                                onRemove={() =>
                                                    setFilters((f) => ({
                                                        ...f,
                                                        usedInCampaign: "any",
                                                    }))
                                                }
                                            >
                                                {filters.usedInCampaign === "yes"
                                                    ? "Đã dùng trong chiến dịch"
                                                    : "Chưa dùng trong chiến dịch"}
                                            </Chip>
                                        )}
                                        <button
                                            type="button"
                                            onClick={() => setFilters(emptyFilterState)}
                                            className="ml-1 text-xs text-text-secondary underline-offset-2 hover:text-text-primary hover:underline"
                                        >
                                            Xóa bộ lọc
                                        </button>
                                    </div>
                                )}

                                {/* Grid */}
                                {emptyBoard && (
                                    <SurfaceCard padding="lg">
                                        <EmptyState
                                            icon={Images}
                                            title="Bộ sưu tập này chưa có tư liệu"
                                            description="Thêm video từ máy hoặc lưu một ý tưởng để xem lại khi cần."
                                            action={
                                                <Button
                                                    size="sm"
                                                    onClick={() => setImportOpen(true)}
                                                >
                                                    <ViraldyIcon name="importCreative" size="sm" />
                                                    Thêm tư liệu
                                                </Button>
                                            }
                                        />
                                    </SurfaceCard>
                                )}
                                {emptyFilter && (
                                    <SurfaceCard padding="lg">
                                        <EmptyState
                                            title="Chưa tìm thấy tư liệu phù hợp"
                                            description="Thử từ khóa khác, đổi loại tư liệu hoặc tìm trong toàn bộ kho nhé."
                                            action={
                                                <div className="flex gap-2">
                                                    <Button
                                                        variant="secondary"
                                                        size="sm"
                                                        onClick={() => {
                                                            setFilters(emptyFilterState);
                                                            setQuery("");
                                                            setSourceFilter("all");
                                                        }}
                                                    >
                                                        Xóa bộ lọc
                                                    </Button>
                                                    <Button
                                                        size="sm"
                                                        onClick={() => {
                                                            setActiveBoard("b-all");
                                                            setFilters(emptyFilterState);
                                                            setQuery("");
                                                            setSourceFilter("all");
                                                        }}
                                                    >
                                                        Xem toàn bộ kho
                                                    </Button>
                                                </div>
                                            }
                                        />
                                    </SurfaceCard>
                                )}
                                {!emptyBoard && !emptyFilter && (
                                    <div className={cn("grid gap-4", gridCols)}>
                                        {shown.map((c) => (
                                            <CreativeCard
                                                key={c.id}
                                                creative={c}
                                                selected={selected.has(c.id)}
                                                selectable={selectMode}
                                                compact={view === "compact"}
                                                onToggleSelect={() => toggleSelected(c.id)}
                                                onAction={(a) => handleCardAction(c.id, a)}
                                            />
                                        ))}
                                    </div>
                                )}

                                {selectedArr.length > 0 && (
                                    <ActionTray
                                        context={
                                            <span className="font-medium text-text-primary">
                                                Đã chọn {selectedArr.length} tư liệu
                                            </span>
                                        }
                                        primaryAction={
                                            <Button
                                                size="sm"
                                                onClick={() => openAnalyze(selectedEligible)}
                                                disabled={selectedEligible.length === 0}
                                            >
                                                <Sparkles className="h-4 w-4" />
                                                Phân tích cách làm
                                            </Button>
                                        }
                                        secondaryAction={
                                            <>
                                                <Button
                                                    size="sm"
                                                    variant="secondary"
                                                    onClick={() => addToCampaign(selectedArr)}
                                                >
                                                    <Megaphone className="h-4 w-4" />
                                                    Thêm vào chiến dịch
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    variant="secondary"
                                                    onClick={() => setMoveForIds(selectedArr)}
                                                >
                                                    <FolderInput className="h-4 w-4" />
                                                    Chuyển bộ sưu tập
                                                </Button>
                                                <Button
                                                    size="icon"
                                                    variant="ghost"
                                                    aria-label="Bỏ lựa chọn"
                                                    onClick={() => setSelected(new Set())}
                                                >
                                                    <X className="h-4 w-4" />
                                                </Button>
                                            </>
                                        }
                                    />
                                )}
                            </div>
                        </div>
                    </TabsContent>
                    <TabsContent
                        value="discover"
                        forceMount
                        className="m-0 space-y-5 data-[state=inactive]:hidden"
                    >
                        <div className="rounded-2xl bg-surface p-5">
                            <h2 className="text-lg font-semibold text-text-primary">
                                Tìm cách giới thiệu sản phẩm mới
                            </h2>
                            <p className="mt-2 text-sm text-text-secondary">
                                Thử video gợi ý bằng ảnh sản phẩm hoặc tìm dữ liệu tham khảo trên
                                TikTok. Nội dung minh họa và dữ liệu TikTok được ghi rõ ở từng công
                                cụ.
                            </p>
                        </div>
                        <ViralVideoFinder />
                        <TikTokSearchPanel workspaceId={workspaceId} />
                    </TabsContent>
                </Tabs>
            </div>

            {/* Dialogs and sheets */}
            <CreativePreviewDialog
                creative={previewCreative}
                onOpenChange={(open) => {
                    if (!open) setPreviewCreative(null);
                }}
            />
            <FilterSheet
                open={filtersOpen}
                onOpenChange={setFiltersOpen}
                value={filters}
                onApply={setFilters}
            />
            <ImportCreativeDialog
                open={importOpen}
                onOpenChange={(open) => {
                    setImportOpen(open);
                    if (!open && routeSearch.import) {
                        void navigate({
                            to: "/creative-library",
                            replace: true,
                            search: { import: undefined },
                        });
                    }
                }}
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
            {moveForIds.length > 0 && (
                <MoveToBoardDialog
                    open={moveForIds.length > 0}
                    onOpenChange={(v) => !v && setMoveForIds([])}
                    creativeIds={moveForIds}
                    onCreateBoard={() => setNewBoardOpen(true)}
                />
            )}
            <Sheet open={boardSheetOpen} onOpenChange={setBoardSheetOpen}>
                <SheetContent side="left" className="w-full sm:max-w-xs">
                    <SheetHeader className="mb-4">
                        <SheetTitle>Bộ sưu tập</SheetTitle>
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
        <span className="inline-flex min-h-11 items-center gap-1 rounded-full bg-surface-soft pl-3 text-xs text-text-secondary">
            {children}
            <button
                type="button"
                onClick={onRemove}
                aria-label="Bỏ bộ lọc"
                className="grid size-11 place-items-center rounded-full text-text-tertiary hover:bg-surface-muted hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
                <X className="h-3 w-3" />
            </button>
        </span>
    );
}
