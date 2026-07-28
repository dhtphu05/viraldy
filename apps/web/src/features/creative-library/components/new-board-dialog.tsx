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
import { Label } from "@/shared/ui/label";
import { useState, useEffect } from "react";
import { useAppStore } from "@/app/store/app-store";
import { toast } from "sonner";

export function NewBoardDialog({
    open,
    onOpenChange,
    renameBoardId,
    initialName,
}: {
    open: boolean;
    onOpenChange: (v: boolean) => void;
    renameBoardId?: string;
    initialName?: string;
}) {
    const createBoard = useAppStore((s) => s.createBoard);
    const renameBoard = useAppStore((s) => s.renameBoard);
    const [name, setName] = useState(initialName ?? "");
    const [err, setErr] = useState<string | null>(null);

    useEffect(() => {
        if (open) {
            setName(initialName ?? "");
            setErr(null);
        }
    }, [open, initialName]);

    const isRename = !!renameBoardId;

    function submit(e: React.FormEvent) {
        e.preventDefault();
        const trimmed = name.trim();
        if (trimmed.length < 2) {
            setErr("Give this board a name (2+ characters).");
            return;
        }
        if (isRename && renameBoardId) {
            renameBoard(renameBoardId, trimmed);
            toast.success("Board renamed");
        } else {
            createBoard(trimmed);
            toast.success("Board created");
        }
        onOpenChange(false);
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[420px]">
                <DialogHeader>
                    <DialogTitle>{isRename ? "Rename board" : "New board"}</DialogTitle>
                    <DialogDescription>
                        {isRename
                            ? "Rename this board. Existing creatives stay attached."
                            : "Group creative references by product, angle, or campaign theme."}
                    </DialogDescription>
                </DialogHeader>
                <form onSubmit={submit} className="flex flex-col gap-3">
                    <div className="grid gap-1.5">
                        <Label htmlFor="board-name">Board name</Label>
                        <Input
                            id="board-name"
                            value={name}
                            autoFocus
                            onChange={(e) => {
                                setName(e.target.value);
                                setErr(null);
                            }}
                            placeholder="e.g. Q4 Gift Angles"
                        />
                        {err && <p className="text-xs text-destructive">{err}</p>}
                    </div>
                    <DialogFooter className="mt-2">
                        <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
                            Cancel
                        </Button>
                        <Button type="submit">{isRename ? "Save" : "Create board"}</Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
