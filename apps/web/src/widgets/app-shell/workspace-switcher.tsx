import { Check, ChevronsUpDown } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/shared/ui/popover";
import { useAppStore } from "@/app/store/app-store";
import { workspaces } from "@/shared/mocks/workspaces";
import { cn } from "@/shared/lib/utils";
import { useState } from "react";

export function WorkspaceSwitcher() {
    const [open, setOpen] = useState(false);
    const currentId = useAppStore((s) => s.currentWorkspaceId);
    const setCurrent = useAppStore((s) => s.setCurrentWorkspace);
    const current = workspaces.find((w) => w.id === currentId) ?? workspaces[0];

    return (
        <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
                <button
                    type="button"
                    className="inline-flex h-9 max-w-[220px] items-center gap-2 rounded-md px-2 text-sm font-medium text-text-primary transition-colors hover:bg-surface-soft focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                >
                    <span
                        aria-hidden
                        className="grid h-6 w-6 shrink-0 place-items-center rounded-md text-[10px] font-semibold text-primary-foreground"
                        style={{ backgroundColor: current.color }}
                    >
                        {current.name[0]}
                    </span>
                    <span className="min-w-0 truncate">{current.name}</span>
                    <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 text-text-tertiary" />
                </button>
            </PopoverTrigger>
            <PopoverContent align="start" className="w-[260px] p-1">
                <div className="px-2 py-1.5 text-[10px] font-semibold uppercase text-text-tertiary">
                    Workspaces
                </div>
                <div className="flex flex-col">
                    {workspaces.map((w) => {
                        const active = w.id === currentId;
                        return (
                            <button
                                key={w.id}
                                type="button"
                                onClick={() => {
                                    setCurrent(w.id);
                                    setOpen(false);
                                }}
                                className={cn(
                                    "flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-surface-soft",
                                    active && "bg-primary-softer",
                                )}
                            >
                                <span
                                    aria-hidden
                                    className="grid h-6 w-6 shrink-0 place-items-center rounded-md text-[10px] font-semibold text-primary-foreground"
                                    style={{ backgroundColor: w.color }}
                                >
                                    {w.name[0]}
                                </span>
                                <div className="min-w-0 flex-1 text-left">
                                    <p className="truncate text-text-primary">{w.name}</p>
                                    <p className="truncate text-xs text-text-tertiary">
                                        {w.handle}
                                    </p>
                                </div>
                                {active && <Check className="h-4 w-4 text-primary" />}
                            </button>
                        );
                    })}
                </div>
            </PopoverContent>
        </Popover>
    );
}
