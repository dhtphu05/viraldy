import { cn } from "@/shared/lib/utils";
import type { MetricTone } from "@/shared/types";

const toneClass: Record<MetricTone, string> = {
    neutral: "bg-surface-soft text-text-secondary",
    ok: "bg-ok-soft text-ok",
    warn: "bg-warn-soft text-warn",
    info: "bg-info-soft text-info",
    destructive: "bg-destructive-soft text-destructive",
};

export function StatusChip({
    tone = "neutral",
    children,
    className,
    dot = false,
}: {
    tone?: MetricTone;
    children: React.ReactNode;
    className?: string;
    dot?: boolean;
}) {
    return (
        <span
            className={cn(
                "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium",
                toneClass[tone],
                className,
            )}
        >
            {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
            {children}
        </span>
    );
}
