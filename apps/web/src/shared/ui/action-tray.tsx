import type { ReactNode } from "react";

import { cn } from "@/shared/lib/utils";

export function ActionTray({
    context,
    primaryAction,
    secondaryAction,
    className,
}: {
    context: ReactNode;
    primaryAction: ReactNode;
    secondaryAction?: ReactNode;
    className?: string;
}) {
    return (
        <div
            className={cn(
                "sticky bottom-3 z-20 mb-[env(safe-area-inset-bottom)] flex flex-col gap-3 rounded-[18px] bg-surface px-4 py-3 shadow-floating-card sm:flex-row sm:items-center sm:justify-between",
                className,
            )}
        >
            <div className="min-w-0 text-sm text-text-secondary">{context}</div>
            <div className="flex shrink-0 flex-wrap items-center gap-2">
                {secondaryAction}
                {primaryAction}
            </div>
        </div>
    );
}
