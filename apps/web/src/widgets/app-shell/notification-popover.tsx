import { Popover, PopoverContent, PopoverTrigger } from "@/shared/ui/popover";
import { StatusChip } from "@/shared/ui/status-chip";
import { ViraldyIcon } from "@/shared/ui/viraldy-icon";
import { useState } from "react";

const items = [
    {
        id: "n1",
        title: "Spark code received",
        body: "@theresa_pets shared a Spark code for asset 04.",
        time: "12m",
        tone: "ok" as const,
    },
    {
        id: "n2",
        title: "Revision requested",
        body: "3 UGC videos for Kitchen Organizer need a hook rewrite.",
        time: "1h",
        tone: "warn" as const,
    },
    {
        id: "n3",
        title: "Recommendation ready",
        body: "New Scale recommendation for Nest & Nook.",
        time: "3h",
        tone: "info" as const,
    },
];

export function NotificationPopover() {
    const [allRead, setAllRead] = useState(false);

    return (
        <Popover>
            <PopoverTrigger asChild>
                <button
                    type="button"
                    aria-label="Notifications"
                    className="relative inline-flex h-9 w-9 items-center justify-center rounded-md text-text-secondary transition-colors hover:bg-surface-soft hover:text-text-primary focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                >
                    <ViraldyIcon name="notifications" size="md" />
                    {!allRead && (
                        <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-primary" />
                    )}
                </button>
            </PopoverTrigger>
            <PopoverContent align="end" className="w-[340px] p-0">
                <div className="flex items-center justify-between border-b border-hairline px-4 py-3">
                    <p className="text-sm font-semibold text-text-primary">Notifications</p>
                    <button
                        type="button"
                        disabled={allRead}
                        onClick={() => setAllRead(true)}
                        className="text-xs text-text-tertiary hover:text-text-primary disabled:text-text-disabled"
                    >
                        {allRead ? "All read" : "Mark all read"}
                    </button>
                </div>
                <ul className="max-h-[360px] divide-y divide-hairline overflow-y-auto">
                    {items.map((n) => (
                        <li
                            key={n.id}
                            className="flex flex-col gap-1 px-4 py-3 hover:bg-surface-soft/60"
                        >
                            <div className="flex items-center justify-between gap-2">
                                <p className="text-sm font-medium text-text-primary">{n.title}</p>
                                <span className="text-[11px] text-text-tertiary">{n.time}</span>
                            </div>
                            <p className="text-xs text-text-secondary">{n.body}</p>
                            <StatusChip tone={n.tone} className="mt-1 w-fit">
                                {n.tone === "ok"
                                    ? "Ready"
                                    : n.tone === "warn"
                                      ? "Attention"
                                      : "Info"}
                            </StatusChip>
                        </li>
                    ))}
                </ul>
            </PopoverContent>
        </Popover>
    );
}
