import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/shared/ui/dialog";
import { Button } from "@/shared/ui/button";
import { EmptyState } from "@/shared/ui/empty-state";
import { useAppStore } from "@/app/store/app-store";
import { useMemo, useState } from "react";
import { Folder, Check, FolderPlus } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/shared/lib/utils";

export function MoveToBoardDialog({
    open,
    onOpenChange,
    creativeId,
    creativeIds,
    onCreateBoard,
}: {
    open: boolean;
    onOpenChange: (v: boolean) => void;
    creativeId?: string;
    creativeIds?: string[];
    onCreateBoard?: () => void;
}) {
    const allBoards = useAppStore((s) => s.boards);
    const boards = useMemo(() => allBoards.filter((b) => !b.system), [allBoards]);
    const move = useAppStore((s) => s.moveCreativeToBoard);
    const [choice, setChoice] = useState<string | null>(null);
    const ids = creativeIds ?? (creativeId ? [creativeId] : []);

    function confirm() {
        if (!choice || ids.length === 0) return;
        ids.forEach((id) => move(id, choice));
        onOpenChange(false);
        toast.success(
            ids.length === 1 ? "Added to board" : `${ids.length} creatives added to board`,
        );
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[420px]">
                <DialogHeader>
                    <DialogTitle>Move to board</DialogTitle>
                    <DialogDescription>
                        Pick a destination for{" "}
                        {ids.length === 1 ? "this creative" : `${ids.length} creatives`}.
                    </DialogDescription>
                </DialogHeader>
                {boards.length === 0 ? (
                    <EmptyState
                        compact
                        icon={FolderPlus}
                        title="Create a board before moving creatives"
                        description="Boards group references by product, angle, campaign, or testing theme."
                        action={
                            onCreateBoard ? (
                                <Button
                                    type="button"
                                    size="sm"
                                    onClick={() => {
                                        onOpenChange(false);
                                        onCreateBoard();
                                    }}
                                >
                                    Create board
                                </Button>
                            ) : undefined
                        }
                    />
                ) : (
                    <ul
                        role="radiogroup"
                        aria-label="Destination board"
                        className="max-h-64 overflow-y-auto rounded-md border border-control-border"
                    >
                        {boards.map((b) => {
                            const active = choice === b.id;
                            return (
                                <li key={b.id}>
                                    <button
                                        type="button"
                                        onClick={() => setChoice(b.id)}
                                        role="radio"
                                        aria-checked={active}
                                        className={cn(
                                            "flex min-h-11 w-full items-center gap-3 px-3 py-2.5 text-left text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring",
                                            active
                                                ? "bg-primary-softer text-text-primary"
                                                : "hover:bg-surface-soft",
                                        )}
                                    >
                                        <Folder className="h-4 w-4 text-text-tertiary" />
                                        <span className="min-w-0 flex-1 truncate">{b.name}</span>
                                        {active && <Check className="h-4 w-4 text-primary" />}
                                    </button>
                                </li>
                            );
                        })}
                    </ul>
                )}
                <DialogFooter>
                    <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
                        Cancel
                    </Button>
                    {boards.length > 0 && (
                        <Button
                            type="button"
                            disabled={!choice || ids.length === 0}
                            onClick={confirm}
                        >
                            Move to board
                        </Button>
                    )}
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
