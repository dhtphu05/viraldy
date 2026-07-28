import { cn } from "@/shared/lib/utils";

export function PageHeader({
    title,
    description,
    actions,
    className,
}: {
    title: string;
    description?: string;
    actions?: React.ReactNode;
    className?: string;
}) {
    return (
        <div
            className={cn(
                "flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between",
                className,
            )}
        >
            <div className="min-w-0">
                <h1 className="truncate text-2xl font-semibold tracking-tight text-text-primary sm:text-[28px]">
                    {title}
                </h1>
                {description && (
                    <p className="mt-1 max-w-2xl text-sm text-text-secondary">{description}</p>
                )}
            </div>
            {actions && (
                <div className="flex flex-wrap items-center gap-2 sm:shrink-0">{actions}</div>
            )}
        </div>
    );
}
