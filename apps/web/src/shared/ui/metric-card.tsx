import { SurfaceCard } from "@/shared/ui/surface-card";
import { StatusChip } from "@/shared/ui/status-chip";
import type { Metric } from "@/shared/types";
import { cn } from "@/shared/lib/utils";

export function MetricCard({ metric, className }: { metric: Metric; className?: string }) {
    return (
        <SurfaceCard
            padding="none"
            className={cn("flex min-h-[116px] flex-col justify-between gap-2 px-4 py-4", className)}
        >
            <div className="flex items-center justify-between gap-2">
                <p className="truncate text-xs font-medium uppercase text-text-tertiary">
                    {metric.label}
                </p>
                {metric.delta && (
                    <StatusChip tone={metric.deltaTone ?? "neutral"}>{metric.delta}</StatusChip>
                )}
            </div>
            <div className="flex items-baseline gap-2">
                <span className="tabular text-[28px] font-semibold leading-none text-text-primary">
                    {metric.value}
                </span>
            </div>
            {metric.hint && <p className="truncate text-xs text-text-tertiary">{metric.hint}</p>}
        </SurfaceCard>
    );
}
