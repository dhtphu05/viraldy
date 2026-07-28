import { StatusChip } from "@/shared/ui/status-chip";
import { Button } from "@/shared/ui/button";
import { Sparkles, Wrench, RefreshCcw, Ban } from "lucide-react";
import type { Recommendation, RecommendationKind, MetricTone } from "@/shared/types";
import { cn } from "@/shared/lib/utils";

const kindMeta: Record<
    RecommendationKind,
    {
        tone: MetricTone;
        icon: React.ComponentType<{ className?: string }>;
        label: string;
        action: string;
    }
> = {
    Scale: { tone: "ok", icon: Sparkles, label: "Scale", action: "Create variants" },
    Fix: { tone: "warn", icon: Wrench, label: "Fix", action: "Apply fix" },
    Rehire: { tone: "info", icon: RefreshCcw, label: "Rehire", action: "Draft outreach" },
    "Stop testing": {
        tone: "destructive",
        icon: Ban,
        label: "Stop",
        action: "Reallocate",
    },
};

export function RecommendationRow({
    rec,
    onEvidence,
    onPrimary,
    className,
}: {
    rec: Recommendation;
    onEvidence: () => void;
    onPrimary: () => void;
    className?: string;
}) {
    const meta = kindMeta[rec.kind];
    const Icon = meta.icon;
    return (
        <div
            className={cn(
                "grid grid-cols-[auto_minmax(0,1fr)] gap-3 px-4 py-3.5 transition-colors hover:bg-surface-soft/60",
                className,
            )}
        >
            <span
                className={cn(
                    "mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg",
                    meta.tone === "ok" && "bg-ok-soft text-ok",
                    meta.tone === "warn" && "bg-warn-soft text-warn",
                    meta.tone === "info" && "bg-info-soft text-info",
                    meta.tone === "destructive" && "bg-destructive-soft text-destructive",
                )}
            >
                <Icon className="h-4 w-4" />
            </span>
            <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                    <StatusChip tone={meta.tone}>{meta.label}</StatusChip>
                    <span className="text-[11px] text-text-tertiary">
                        Confidence: {rec.confidence}
                    </span>
                </div>
                <p className="mt-1 truncate text-sm font-medium text-text-primary">{rec.title}</p>
                <p className="mt-0.5 line-clamp-2 text-xs text-text-secondary">{rec.reason}</p>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                    <Button size="sm" onClick={onPrimary}>
                        {meta.action}
                    </Button>
                    <Button size="sm" variant="ghost" onClick={onEvidence}>
                        Evidence
                    </Button>
                </div>
            </div>
        </div>
    );
}
