import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/shared/ui/dialog";
import { Button } from "@/shared/ui/button";
import { useAppStore } from "@/app/store/app-store";
import { useMemo, useState } from "react";
import { Folder, Check } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/shared/lib/utils";

export function MoveToBoardDialog({
    open,
    onOpenChange,
    creativeId,
}: {
    open: boolean;
    onOpenChange: (v: boolean) => void;
    creativeId: string;
}) {
    const allBoards = useAppStore((s) => s.boards);
    const boards = useMemo(() => allBoards.filter((b) => !b.system), [allBoards]);
    const move = useAppStore((s) => s.moveCreativeToBoard);
    const [choice, setChoice] = useState<string | null>(null);

    function confirm() {
        if (!choice) return;
        move(creativeId, choice);
        onOpenChange(false);
        toast.success("Added to board");
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[420px]">
                <DialogHeader>
                    <DialogTitle>Move to board</DialogTitle>
                    <DialogDescription>Pick a destination board.</DialogDescription>
                </DialogHeader>
                <ul className="max-h-64 overflow-y-auto rounded-md border border-hairline/70">
                    {boards.length === 0 ? (
                        <li className="p-4 text-sm text-text-tertiary">No custom boards yet.</li>
                    ) : (
                        boards.map((b) => {
                            const active = choice === b.id;
                            return (
                                <li key={b.id}>
                                    <button
                                        type="button"
                                        onClick={() => setChoice(b.id)}
                                        className={cn(
                                            "flex w-full items-center gap-3 px-3 py-2.5 text-left text-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-inset focus-visible:ring-ring",
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
                        })
                    )}
                </ul>
                <DialogFooter>
                    <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
                        Cancel
                    </Button>
                    <Button type="button" disabled={!choice} onClick={confirm}>
                        Move
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
