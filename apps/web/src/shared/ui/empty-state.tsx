import { cn } from "@/shared/lib/utils";
import { Inbox } from "lucide-react";
import { useId } from "react";
import { Skeleton } from "@/shared/ui/skeleton";

type EmptyStateTone = "neutral" | "success" | "attention" | "info";

const toneClasses: Record<EmptyStateTone, string> = {
    neutral: "bg-surface-muted text-text-secondary",
    success: "bg-ok-soft text-ok",
    attention: "bg-primary-soft text-primary-active",
    info: "bg-info-soft text-info",
};

export function EmptyState({
    icon: Icon = Inbox,
    title,
    description,
    action,
    className,
    compact = false,
    tone = "neutral",
}: {
    icon?: React.ComponentType<{ className?: string }>;
    title: string;
    description?: string;
    action?: React.ReactNode;
    className?: string;
    compact?: boolean;
    tone?: EmptyStateTone;
}) {
    const titleId = useId();
    const descriptionId = useId();

    return (
        <section
            data-empty-state
            aria-labelledby={titleId}
            aria-describedby={description ? descriptionId : undefined}
            className={cn(
                "flex justify-center gap-3",
                compact
                    ? "items-start p-4 text-left"
                    : "flex-col items-center px-6 py-10 text-center",
                className,
            )}
        >
            <div
                className={cn(
                    "grid shrink-0 place-items-center rounded-full",
                    compact ? "h-9 w-9" : "h-11 w-11",
                    toneClasses[tone],
                )}
            >
                <Icon className="h-5 w-5" />
            </div>
            <div className={cn("min-w-0", compact && "flex-1")}>
                <p
                    id={titleId}
                    className={cn(
                        "font-semibold text-text-primary",
                        compact ? "text-sm" : "text-base",
                    )}
                >
                    {title}
                </p>
                {description && (
                    <p
                        id={descriptionId}
                        className="mt-1 max-w-md text-sm leading-5 text-text-secondary"
                    >
                        {description}
                    </p>
                )}
                {action && (
                    <div
                        className={cn(
                            "flex flex-wrap gap-2",
                            compact ? "mt-3" : "mt-4 justify-center",
                        )}
                    >
                        {action}
                    </div>
                )}
            </div>
        </section>
    );
}

export function LoadingState({
    label = "Loading",
    className,
}: {
    label?: string;
    className?: string;
}) {
    return (
        <div
            role="status"
            aria-live="polite"
            aria-busy="true"
            className={cn("grid gap-3 p-4", className)}
        >
            <span className="sr-only">{label}…</span>
            <Skeleton className="h-4 w-36 max-w-full" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-4/5" />
        </div>
    );
}
