import { StatusChip } from "@/shared/ui/status-chip";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { Button } from "@/shared/ui/button";
import type { PerfRecommendation } from "@/features/performance/types/performance";
import { decisionTone } from "@/features/performance/lib/performanceEngine";
import { cn } from "@/shared/lib/utils";
import { DemoMediaTile } from "@/shared/ui/demo-media-tile";

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
    const primaryLabel: Record<PerfRecommendation["group"], string> = {
        Scale: "Accept scale",
        Fix: "Accept fix",
        Rehire: "Accept rehire",
        Hold: "Hold campaign",
        Stop: "Accept stop",
        Refresh: "Refresh hook",
    };

    return (
        <SurfaceCard padding="none" className={cn("flex flex-col gap-3 p-4", className)}>
            {rec.mediaUrl && (
                <DemoMediaTile
                    mediaUrl={rec.mediaUrl}
                    mediaKind={rec.mediaKind}
                    posterUrl={rec.posterUrl}
                    seed={rec.objectId ?? rec.id}
                    label={rec.object}
                    badges={[rec.mediaAspectRatio ?? "media"]}
                    aspect={rec.mediaAspectRatio ?? "16 / 9"}
                    fit={rec.mediaAspectRatio === "9:16" ? "contain" : "cover"}
                    className="rounded-md bg-black"
                />
            )}
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
            <button
                type="button"
                onClick={onOpen}
                className="-mx-1 rounded-md px-1 text-left transition-colors duration-200 hover:bg-surface-soft/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
                <p className="line-clamp-2 text-sm font-medium text-text-primary">{rec.title}</p>
                <p className="mt-1 line-clamp-2 text-xs text-text-secondary">{rec.reason}</p>
            </button>
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
                    {primaryLabel[rec.group]}
                </Button>
                <Button size="sm" variant="ghost" onClick={onOpen}>
                    View evidence
                </Button>
            </div>
        </SurfaceCard>
    );
}
