import { StatusChip } from "@/shared/ui/status-chip";
import { Button } from "@/shared/ui/button";
import type { PerfRecommendation } from "@/features/performance/types/performance";
import { decisionTone } from "@/features/performance/lib/performanceEngine";
import { cn } from "@/shared/lib/utils";
import { DemoMediaTile } from "@/shared/ui/demo-media-tile";
import { ViraldyIcon, type ViraldyIconName } from "@/shared/ui/viraldy-icon";

const decisionIcon: Partial<Record<PerfRecommendation["group"], ViraldyIconName>> = {
    Scale: "scale",
    Fix: "fix",
    Rehire: "rehire",
    Stop: "stopTesting",
};

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
    const iconName = decisionIcon[rec.group];

    return (
        <article
            className={cn(
                "grid min-w-0 gap-4 px-4 py-4 sm:px-5",
                rec.mediaUrl
                    ? "sm:grid-cols-[112px_minmax(0,1fr)_auto]"
                    : "sm:grid-cols-[minmax(0,1fr)_auto]",
                className,
            )}
        >
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
                    className="w-full max-w-[180px] rounded-md bg-black sm:w-28"
                />
            )}
            <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                    {iconName && <ViraldyIcon name={iconName} size="xl" />}
                    <StatusChip tone={decisionTone[rec.group]}>{rec.kind}</StatusChip>
                    <span className="text-xs text-text-tertiary">{rec.confidence} confidence</span>
                    <span className="min-w-0 truncate text-xs text-text-tertiary">
                        {rec.object}
                    </span>
                </div>
                <button
                    type="button"
                    onClick={onOpen}
                    className="-mx-1 mt-2 block w-full rounded-md px-1 text-left transition-colors duration-[180ms] hover:bg-surface-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                    <p className="text-sm font-semibold text-text-primary">{rec.title}</p>
                    <p className="mt-1 text-xs leading-5 text-text-secondary">{rec.reason}</p>
                </button>
                <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2">
                    {rec.supportingMetrics.slice(0, 3).map((metric) => (
                        <div key={metric.label} className="min-w-0">
                            <p className="text-[10px] uppercase text-text-tertiary">
                                {metric.label}
                            </p>
                            <p className="tabular text-sm font-semibold text-text-primary">
                                {metric.value}
                            </p>
                        </div>
                    ))}
                </div>
                <p className="mt-3 text-xs text-text-secondary">
                    <span className="font-medium text-text-primary">Demo scenario estimate:</span>{" "}
                    {rec.estimatedImpact}
                </p>
            </div>
            <div className="flex flex-wrap items-start gap-2 sm:flex-col sm:items-stretch">
                <Button size="sm" onClick={onAccept}>
                    {primaryLabel[rec.group]}
                </Button>
                <Button size="sm" variant="secondary" onClick={onOpen}>
                    View evidence
                </Button>
            </div>
        </article>
    );
}
