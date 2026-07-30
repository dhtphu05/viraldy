import { cn } from "@/shared/lib/utils";
import { Inbox } from "lucide-react";

export function EmptyState({
    icon: Icon = Inbox,
    title,
    description,
    action,
    className,
}: {
    icon?: React.ComponentType<{ className?: string }>;
    title: string;
    description?: string;
    action?: React.ReactNode;
    className?: string;
}) {
    return (
        <div
            className={cn(
                "flex flex-col items-center justify-center gap-3 rounded-md p-10 text-center",
                className,
            )}
        >
            <div className="grid h-11 w-11 place-items-center rounded-full bg-surface-soft text-text-tertiary">
                <Icon className="h-5 w-5" />
            </div>
            <div>
                <p className="text-sm font-medium text-text-primary">{title}</p>
                {description && (
                    <p className="mt-1 max-w-sm text-sm text-text-secondary">{description}</p>
                )}
            </div>
            {action}
        </div>
    );
}

export function LoadingState({ label = "Loading" }: { label?: string }) {
    return (
        <div className="flex items-center justify-center gap-2 p-8 text-sm text-text-tertiary">
            <span className="h-3 w-3 rounded-full bg-text-tertiary/60" />
            {label}…
        </div>
    );
}
