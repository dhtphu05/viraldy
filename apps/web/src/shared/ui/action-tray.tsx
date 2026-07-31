import type { ReactNode } from "react";

import { cn } from "@/shared/lib/utils";

export function ActionTray({
    context,
    primaryAction,
    secondaryAction,
    className,
    sticky = true,
}: {
    context: ReactNode;
    primaryAction: ReactNode;
    secondaryAction?: ReactNode;
    className?: string;
    sticky?: boolean;
}) {
    return (
        <div
            className={cn(
                "flex flex-col gap-3 bg-surface px-4 py-3 sm:flex-row sm:items-center sm:justify-between",
                sticky &&
                    "sticky bottom-3 z-20 mb-[env(safe-area-inset-bottom)] rounded-[18px] shadow-floating-card",
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
