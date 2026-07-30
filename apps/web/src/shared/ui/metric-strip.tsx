import type { ReactNode } from "react";

import { cn } from "@/shared/lib/utils";
import type { MetricTone } from "@/shared/types";

export type MetricStripItem = {
    id: string;
    label: string;
    value: ReactNode;
    delta?: ReactNode;
    hint?: ReactNode;
    tone?: MetricTone;
    onClick?: () => void;
};

const deltaClass: Record<MetricTone, string> = {
    neutral: "text-text-secondary",
    ok: "text-ok",
    warn: "text-warn",
    info: "text-info",
    destructive: "text-destructive",
};

export function MetricStrip({
    metrics,
    className,
    ariaLabel = "Outcome metrics",
}: {
    metrics: MetricStripItem[];
    className?: string;
    ariaLabel?: string;
}) {
    return (
        <section
            aria-label={ariaLabel}
            className={cn(
                "grid overflow-hidden rounded-2xl bg-surface sm:grid-cols-2 lg:grid-cols-4",
                className,
            )}
        >
            {metrics.map((metric, index) => {
                const content = (
                    <>
                        <p className="text-[11px] font-medium uppercase text-text-tertiary">
                            {metric.label}
                        </p>
                        <div className="mt-1 flex flex-wrap items-baseline gap-2">
                            <span className="text-xl font-semibold tabular text-text-primary">
                                {metric.value}
                            </span>
                            {metric.delta !== undefined && (
                                <span
                                    className={cn(
                                        "text-xs font-medium",
                                        deltaClass[metric.tone ?? "neutral"],
                                    )}
                                >
                                    {metric.delta}
                                </span>
                            )}
                        </div>
                        {metric.hint && (
                            <div className="mt-1 text-xs text-text-secondary">{metric.hint}</div>
                        )}
                    </>
                );
                const itemClass = cn(
                    "min-w-0 px-4 py-4 text-left",
                    index > 0 && "border-t border-divider sm:border-l",
                    index === 1 && "sm:border-t-0",
                    index > 1 && "lg:border-t-0",
                    metric.onClick &&
                        "transition-colors duration-[180ms] hover:bg-surface-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring",
                );

                return metric.onClick ? (
                    <button
                        key={metric.id}
                        type="button"
                        className={itemClass}
                        onClick={metric.onClick}
                    >
                        {content}
                    </button>
                ) : (
                    <div key={metric.id} className={itemClass}>
                        {content}
                    </div>
                );
            })}
        </section>
    );
}
