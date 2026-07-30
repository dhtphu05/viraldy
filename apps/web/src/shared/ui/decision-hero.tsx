import type { ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Info, ShieldAlert } from "lucide-react";

import { cn } from "@/shared/lib/utils";
import type { MetricTone } from "@/shared/types";
import { ConfidenceBadge } from "@/shared/ui/confidence-badge";
import { StatusChip } from "@/shared/ui/status-chip";
import { SurfaceCard } from "@/shared/ui/surface-card";

const toneIcon = {
    neutral: Info,
    ok: CheckCircle2,
    warn: AlertTriangle,
    info: Info,
    destructive: ShieldAlert,
} satisfies Record<MetricTone, typeof Info>;

const toneClass: Record<MetricTone, string> = {
    neutral: "text-text-secondary",
    ok: "text-ok",
    warn: "text-warn",
    info: "text-info",
    destructive: "text-destructive",
};

type DecisionHeroProps = {
    actionLabel: string;
    reason: ReactNode;
    score?: number | string;
    scoreMax?: number;
    scoreLabel?: string;
    confidence?: string;
    blockerCount?: number;
    effort?: string;
    statusTone?: MetricTone;
    eyebrow?: string;
    primaryAction?: ReactNode;
    secondaryAction?: ReactNode;
    media?: ReactNode;
    className?: string;
};

export function DecisionHero({
    actionLabel,
    reason,
    score,
    scoreMax = 100,
    scoreLabel = "Score",
    confidence,
    blockerCount,
    effort,
    statusTone = "info",
    eyebrow = "Recommended decision",
    primaryAction,
    secondaryAction,
    media,
    className,
}: DecisionHeroProps) {
    const Icon = toneIcon[statusTone];
    const hasMeta = confidence || blockerCount !== undefined || effort;

    return (
        <SurfaceCard variant="raised" padding="lg" className={cn("overflow-hidden", className)}>
            <div className={cn("grid gap-6", media && "lg:grid-cols-[minmax(0,1fr)_280px]")}>
                <div className="min-w-0">
                    <p
                        className={cn(
                            "flex items-center gap-2 text-[11px] font-semibold uppercase",
                            toneClass[statusTone],
                        )}
                    >
                        <Icon className="h-4 w-4" aria-hidden />
                        {eyebrow}
                    </p>
                    <h2 className="mt-2 text-xl font-semibold leading-tight text-text-primary sm:text-2xl">
                        {actionLabel}
                    </h2>
                    <div className="mt-2 max-w-3xl text-sm leading-6 text-text-secondary">
                        {reason}
                    </div>

                    {hasMeta && (
                        <div className="mt-4 flex flex-wrap items-center gap-2">
                            {confidence && <ConfidenceBadge level={confidence} />}
                            {blockerCount !== undefined && (
                                <StatusChip tone={blockerCount > 0 ? "warn" : "ok"}>
                                    {blockerCount} {blockerCount === 1 ? "blocker" : "blockers"}
                                </StatusChip>
                            )}
                            {effort && <StatusChip tone="neutral">{effort}</StatusChip>}
                        </div>
                    )}

                    {(primaryAction || secondaryAction) && (
                        <div className="mt-5 flex flex-wrap items-center gap-2">
                            {primaryAction}
                            {secondaryAction}
                        </div>
                    )}
                </div>

                {(media || score !== undefined) && (
                    <div className="flex min-w-0 flex-col gap-3 lg:items-end">
                        {media}
                        {score !== undefined && (
                            <div className="rounded-xl bg-surface-soft px-4 py-3 lg:text-right">
                                <p className="text-[11px] font-medium uppercase text-text-tertiary">
                                    {scoreLabel}
                                </p>
                                <p className="mt-1 text-lg font-semibold tabular text-text-primary">
                                    {score}
                                    {typeof score === "number" ? ` / ${scoreMax}` : ""}
                                </p>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </SurfaceCard>
    );
}
