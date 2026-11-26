import { cn } from "@/shared/lib/utils";
import { useAppStore } from "@/app/store/app-store";
import { isWithinDemoDays } from "@/shared/mocks/time";
import {
    Layers,
    Clock,
    Target,
    Utensils,
    Gift,
    Sparkles,
    Package,
    Inbox,
    Folder,
    MoreHorizontal,
    Plus,
} from "lucide-react";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/shared/ui/dropdown-menu";
import type { CreativeBoard } from "@/features/creative-library/types/creative";
import { useMemo } from "react";
import { toast } from "sonner";

const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
    layers: Layers,
    clock: Clock,
    target: Target,
    utensils: Utensils,
    gift: Gift,
    sparkles: Sparkles,
    package: Package,
    inbox: Inbox,
    folder: Folder,
};

const systemLabels: Record<string, string> = {
    all: "Tất cả tư liệu",
    recent: "Mới lưu",
    unassigned: "Chưa phân loại",
};

export function BoardRail({
    activeBoardId,
    onSelect,
    onNewBoard,
    onRenameBoard,
    className,
}: {
    activeBoardId: string;
    onSelect: (id: string) => void;
    onNewBoard: () => void;
    onRenameBoard: (b: CreativeBoard) => void;
    className?: string;
}) {
    const boards = useAppStore((s) => s.boards);
    const creatives = useAppStore((s) => s.creatives);
    const duplicateBoard = useAppStore((s) => s.duplicateBoard);
    const deleteBoard = useAppStore((s) => s.deleteBoard);

    const counts = useMemo(() => {
        const counts: Record<string, number> = {};
        const active = creatives.filter((c) => !c.archived);
        for (const b of boards) {
            if (b.filter === "all") counts[b.id] = active.length;
            else if (b.filter === "recent")
                counts[b.id] = active.filter((c) => isWithinDemoDays(c.savedAt, 7)).length;
            else if (b.filter === "unassigned")
                counts[b.id] = active.filter((c) => c.boardIds.length === 0).length;
            else counts[b.id] = active.filter((c) => c.boardIds.includes(b.id)).length;
        }
        return counts;
    }, [boards, creatives]);

    return (
        <nav aria-label="Bộ sưu tập" className={cn("flex flex-col gap-2", className)}>
            <div className="flex items-center justify-between px-1">
                <p className="text-xs font-semibold text-text-secondary">Bộ sưu tập</p>
                <button
                    type="button"
                    onClick={onNewBoard}
                    aria-label="Tạo bộ sưu tập"
                    className="inline-flex size-11 items-center justify-center rounded-xl text-text-tertiary transition-colors hover:bg-surface-soft hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                    <Plus className="h-3.5 w-3.5" />
                </button>
            </div>
            <ul className="flex flex-col gap-0.5">
                {boards.map((b) => {
                    const Icon = iconMap[b.icon ?? "folder"] ?? Folder;
                    const active = b.id === activeBoardId;
                    const count = counts[b.id] ?? 0;
                    const label = b.system ? (systemLabels[b.filter ?? ""] ?? b.name) : b.name;
                    return (
                        <li key={b.id} className="group/board relative">
                            <button
                                type="button"
                                onClick={() => onSelect(b.id)}
                                aria-current={active ? "page" : undefined}
                                className={cn(
                                    "flex min-h-11 w-full items-center gap-2 rounded-xl px-2.5 py-2 text-left text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                                    !b.system && "pr-14",
                                    active
                                        ? "bg-primary-soft text-primary-active"
                                        : "text-text-secondary hover:bg-surface-soft hover:text-text-primary",
                                )}
                            >
                                <Icon
                                    className={cn(
                                        "h-4 w-4 shrink-0",
                                        active ? "text-primary" : "text-text-tertiary",
                                    )}
                                />
                                <span className="min-w-0 flex-1 truncate" title={label}>
                                    {label}
                                </span>
                                <span
                                    className={cn(
                                        "tabular-nums text-xs",
                                        active ? "text-primary-active/80" : "text-text-tertiary",
                                    )}
                                >
                                    {count}
                                </span>
                            </button>
                            {!b.system && (
                                <DropdownMenu>
                                    <DropdownMenuTrigger asChild>
                                        <button
                                            type="button"
                                            aria-label={`Tùy chọn bộ sưu tập ${b.name}`}
                                            className="absolute right-0 top-1/2 inline-flex size-11 -translate-y-1/2 items-center justify-center rounded-xl text-text-tertiary transition-colors hover:bg-surface-muted hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:opacity-0 sm:group-hover/board:opacity-100 sm:focus-visible:opacity-100"
                                        >
                                            <MoreHorizontal className="h-3.5 w-3.5" />
                                        </button>
                                    </DropdownMenuTrigger>
                                    <DropdownMenuContent align="end" className="w-48 border-0">
                                        <DropdownMenuItem
                                            onSelect={() => onRenameBoard(b)}
                                            className="min-h-11"
                                        >
                                            Đổi tên
                                        </DropdownMenuItem>
                                        <DropdownMenuItem
                                            onSelect={() => {
                                                duplicateBoard(b.id);
                                                toast("Đã nhân bản bộ sưu tập");
                                            }}
                                            className="min-h-11"
                                        >
                                            Nhân bản
                                        </DropdownMenuItem>
                                        <DropdownMenuSeparator />
                                        <DropdownMenuItem
                                            onSelect={() => {
                                                if (count > 0) {
                                                    toast("Bộ sưu tập vẫn còn tư liệu", {
                                                        description:
                                                            "Di chuyển hoặc lưu trữ tư liệu trước khi xóa nhé.",
                                                    });
                                                    return;
                                                }
                                                deleteBoard(b.id);
                                                toast.success("Đã xóa bộ sưu tập");
                                            }}
                                            className="min-h-11 text-destructive focus:text-destructive"
                                        >
                                            Xóa bộ sưu tập
                                        </DropdownMenuItem>
                                    </DropdownMenuContent>
                                </DropdownMenu>
                            )}
                        </li>
                    );
                })}
            </ul>
        </nav>
    );
}
