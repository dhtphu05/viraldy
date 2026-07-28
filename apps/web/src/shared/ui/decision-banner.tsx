import { SurfaceCard } from "@/shared/ui/surface-card";
import { StatusChip } from "@/shared/ui/status-chip";
import { Button } from "@/shared/ui/button";
import { ChevronRight } from "lucide-react";
import type { DecisionItem } from "@/shared/types";
import { cn } from "@/shared/lib/utils";

const severityMap = {
    ok: { tone: "ok" as const, label: "Healthy" },
    info: { tone: "info" as const, label: "Review" },
    warn: { tone: "warn" as const, label: "Attention" },
    destructive: { tone: "destructive" as const, label: "Blocking" },
};

export function DecisionBanner({
    item,
    onOpen,
    className,
}: {
    item: DecisionItem;
    onOpen: () => void;
    className?: string;
}) {
    const sev = severityMap[item.severity];
    return (
        <div
            className={cn(
                "group grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 rounded-md px-4 py-3.5 transition-colors hover:bg-surface-soft/70",
                className,
            )}
        >
            <button
                type="button"
                onClick={onOpen}
                className="grid min-w-0 grid-cols-[auto_minmax(0,1fr)] items-center gap-3 text-left focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring rounded-md"
            >
                <span
                    aria-hidden
                    className={cn(
                        "h-8 w-1 shrink-0 rounded-full",
                        item.severity === "ok" && "bg-ok",
                        item.severity === "info" && "bg-info",
                        item.severity === "warn" && "bg-warn",
                        item.severity === "destructive" && "bg-destructive",
                    )}
                />
                <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                        <StatusChip tone={sev.tone} dot>
                            {sev.label}
                        </StatusChip>
                        <p className="truncate text-sm font-medium text-text-primary">
                            {item.title}
                        </p>
                    </div>
                    <p className="mt-0.5 truncate text-xs text-text-secondary">
                        {item.object} · {item.urgency}
                    </p>
                </div>
            </button>
            <div className="flex shrink-0 items-center gap-2">
                <Button size="sm" variant="secondary" onClick={onOpen}>
                    {item.action}
                    <ChevronRight className="h-4 w-4" />
                </Button>
            </div>
        </div>
    );
}

export function DecisionSeverityDot({ severity }: { severity: DecisionItem["severity"] }) {
    const cls =
        severity === "ok"
            ? "bg-ok"
            : severity === "info"
              ? "bg-info"
              : severity === "warn"
                ? "bg-warn"
                : "bg-destructive";
    return <span className={cn("inline-block h-2 w-2 rounded-full", cls)} />;
}
