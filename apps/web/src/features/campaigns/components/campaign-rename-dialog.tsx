import { useEffect, useState } from "react";
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

export function CampaignRenameDialog({
    open,
    currentName,
    onOpenChange,
    onRename,
}: {
    open: boolean;
    currentName: string;
    onOpenChange: (open: boolean) => void;
    onRename: (name: string) => void;
}) {
    const [name, setName] = useState(currentName);

    useEffect(() => {
        if (open) setName(currentName);
    }, [currentName, open]);

    const trimmedName = name.trim();

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <form
                    onSubmit={(event) => {
                        event.preventDefault();
                        if (!trimmedName) return;
                        onRename(trimmedName);
                        onOpenChange(false);
                    }}
                >
                    <DialogHeader>
                        <DialogTitle>Rename campaign</DialogTitle>
                        <DialogDescription>
                            Update the name used across the campaign list and Campaign Pack.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="mt-5 grid gap-2">
                        <Label htmlFor="campaign-name">Campaign name</Label>
                        <Input
                            id="campaign-name"
                            value={name}
                            onChange={(event) => setName(event.target.value)}
                            autoFocus
                        />
                    </div>
                    <DialogFooter className="mt-6">
                        <Button
                            type="button"
                            variant="secondary"
                            onClick={() => onOpenChange(false)}
                        >
                            Cancel
                        </Button>
                        <Button type="submit" disabled={!trimmedName}>
                            Save name
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
