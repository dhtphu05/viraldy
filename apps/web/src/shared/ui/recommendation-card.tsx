import { SurfaceCard } from "@/shared/ui/surface-card";
import { StatusChip } from "@/shared/ui/status-chip";
import { Button } from "@/shared/ui/button";
import { Sparkles, Wrench, RefreshCcw, Ban } from "lucide-react";
import type { Recommendation, RecommendationKind, MetricTone } from "@/shared/types";
import { cn } from "@/shared/lib/utils";

const kindMeta: Record<
    RecommendationKind,
    { tone: MetricTone; icon: React.ComponentType<{ className?: string }> }
> = {
    Scale: { tone: "ok", icon: Sparkles },
    Fix: { tone: "warn", icon: Wrench },
    Rehire: { tone: "info", icon: RefreshCcw },
    "Stop testing": { tone: "destructive", icon: Ban },
};

export function RecommendationCard({
    rec,
    onEvidence,
    onPrimary,
    onDismiss,
    className,
}: {
    rec: Recommendation;
    onEvidence: () => void;
    onPrimary: () => void;
    onDismiss: () => void;
    className?: string;
}) {
    const meta = kindMeta[rec.kind];
    const Icon = meta.icon;
    const primaryLabel =
        rec.kind === "Scale"
            ? "Create variants"
            : rec.kind === "Fix"
              ? "Apply fix"
              : rec.kind === "Rehire"
                ? "Draft outreach"
                : "Reallocate budget";
    return (
        <SurfaceCard padding="md" className={cn("flex flex-col gap-4", className)}>
            <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2">
                    <span className="grid h-7 w-7 place-items-center rounded-full bg-surface-soft text-text-primary">
                        <Icon className="h-3.5 w-3.5" />
                    </span>
                    <StatusChip tone={meta.tone} dot>
                        {rec.kind}
                    </StatusChip>
                </div>
                <span className="text-xs text-text-tertiary">Confidence: {rec.confidence}</span>
            </div>

            <div className="min-w-0">
                <h3 className="text-base font-semibold leading-snug text-text-primary">
                    {rec.title}
                </h3>
                <p className="mt-1.5 text-sm text-text-secondary">{rec.summary}</p>
            </div>

            <div className="flex items-baseline gap-2 rounded-md bg-surface-soft px-3 py-2">
                <span className="text-xs text-text-secondary">{rec.metric.label}</span>
                <span className="tabular text-lg font-semibold text-text-primary">
                    {rec.metric.value}
                </span>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={onDismiss}
                    className="text-text-tertiary"
                >
                    Dismiss
                </Button>
                <div className="flex items-center gap-2">
                    <Button variant="secondary" size="sm" onClick={onEvidence}>
                        View evidence
                    </Button>
                    <Button size="sm" onClick={onPrimary}>
                        {primaryLabel}
                    </Button>
                </div>
            </div>
        </SurfaceCard>
    );
}
