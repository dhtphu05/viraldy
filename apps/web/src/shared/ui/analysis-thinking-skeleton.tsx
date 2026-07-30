import { Loader2, Sparkles } from "lucide-react";
import { Skeleton } from "@/shared/ui/skeleton";
import { cn } from "@/shared/lib/utils";

export function AnalysisThinkingSkeleton({
    title = "Analyzing media",
    description = "Detecting hook, product reveal, proof, CTA, risks, and campaign alignment.",
    compact = false,
    className,
}: {
    title?: string;
    description?: string;
    compact?: boolean;
    className?: string;
}) {
    return (
        <div
            role="status"
            aria-live="polite"
            className={cn("rounded-md border border-primary/15 bg-primary-soft/30 p-4", className)}
        >
            <div className="flex items-start gap-3">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-primary text-primary-foreground">
                    <Sparkles className="h-4 w-4" />
                </span>
                <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-semibold text-text-primary">{title}</p>
                        <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
                    </div>
                    <p className="mt-0.5 text-xs text-text-secondary">{description}</p>
                </div>
            </div>
            <div
                className={cn(
                    "mt-4 grid gap-3",
                    compact ? "grid-cols-1 sm:grid-cols-3" : "md:grid-cols-[180px_minmax(0,1fr)]",
                )}
            >
                {!compact && (
                    <div className="overflow-hidden rounded-md border border-hairline bg-surface">
                        <Skeleton className="aspect-[9/16] rounded-none" />
                    </div>
                )}
                <div className="grid gap-3">
                    <div className="rounded-md border border-hairline bg-surface p-3">
                        <Skeleton className="h-3 w-28" />
                        <Skeleton className="mt-3 h-2 w-full" />
                        <Skeleton className="mt-2 h-2 w-4/5" />
                    </div>
                    <div className="grid gap-2 sm:grid-cols-3">
                        <Skeleton className="h-16" />
                        <Skeleton className="h-16" />
                        <Skeleton className="h-16" />
                    </div>
                    <div className="rounded-md border border-hairline bg-surface p-3">
                        <Skeleton className="h-2 w-full" />
                        <div className="mt-3 flex justify-between">
                            <Skeleton className="h-5 w-20" />
                            <Skeleton className="h-5 w-24" />
                            <Skeleton className="h-5 w-16" />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
