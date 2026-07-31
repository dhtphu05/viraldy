import { cn } from "@/shared/lib/utils";

function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
    return (
        <div
            aria-hidden="true"
            className={cn(
                "animate-pulse rounded-md bg-surface-muted motion-reduce:animate-none",
                className,
            )}
            {...props}
        />
    );
}

export { Skeleton };
