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
                "flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between",
                className,
            )}
        >
            <div className="min-w-0">
                <h1 className="break-words text-2xl font-semibold text-text-primary sm:text-[28px]">
                    {title}
                </h1>
                {description && (
                    <p className="mt-1 max-w-2xl text-sm text-text-secondary">{description}</p>
                )}
            </div>
            {actions && (
                <div className="flex flex-wrap items-center gap-2 xl:shrink-0">{actions}</div>
            )}
        </div>
    );
}
