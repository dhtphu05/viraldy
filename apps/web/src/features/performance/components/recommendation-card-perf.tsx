import { StatusChip } from "@/shared/ui/status-chip";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { Button } from "@/shared/ui/button";
import type { PerfRecommendation } from "@/features/performance/types/performance";
import { decisionTone } from "@/features/performance/lib/performanceEngine";
import { cn } from "@/shared/lib/utils";

export function RecommendationCardPerf({
    rec,
    onOpen,
    onAccept,
    className,
}: {
    rec: PerfRecommendation;
    onOpen: () => void;
    onAccept: () => void;
    className?: string;
}) {
    return (
        <SurfaceCard padding="none" className={cn("flex flex-col gap-3 p-4", className)}>
            <div className="flex flex-wrap items-center gap-2">
                <StatusChip tone={decisionTone[rec.group]}>{rec.kind}</StatusChip>
                <StatusChip
                    tone={
                        rec.confidence === "High"
                            ? "ok"
                            : rec.confidence === "Medium"
                              ? "info"
                              : "warn"
                    }
                >
                    Confidence: {rec.confidence}
                </StatusChip>
                <span className="ml-auto truncate text-xs text-text-tertiary">{rec.object}</span>
            </div>
            <div>
                <p className="line-clamp-2 text-sm font-medium text-text-primary">{rec.title}</p>
                <p className="mt-1 line-clamp-2 text-xs text-text-secondary">{rec.reason}</p>
            </div>
            <div className="flex flex-wrap gap-3">
                {rec.supportingMetrics.slice(0, 3).map((m) => (
                    <div key={m.label} className="min-w-0">
                        <p className="text-[10px] uppercase tracking-wide text-text-tertiary">
                            {m.label}
                        </p>
                        <p className="tabular text-sm font-semibold text-text-primary">{m.value}</p>
                    </div>
                ))}
            </div>
            <p className="text-xs text-text-secondary">
                <span className="font-medium text-text-primary">Impact:</span> {rec.estimatedImpact}
            </p>
            <div className="flex items-center gap-2">
                <Button size="sm" onClick={onAccept}>
                    Accept
                </Button>
                <Button size="sm" variant="ghost" onClick={onOpen}>
                    View evidence
                </Button>
            </div>
        </SurfaceCard>
    );
}
