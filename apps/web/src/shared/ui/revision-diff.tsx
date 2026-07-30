import { ArrowRight, CheckCircle2, CircleAlert, Minus } from "lucide-react";

import { cn } from "@/shared/lib/utils";

export type RevisionDiffStatus = "fixed" | "improved" | "unresolved" | "unchanged";

export type RevisionDiffItem = {
    id: string;
    label: string;
    previous: string;
    current: string;
    status: RevisionDiffStatus;
};

const statusMeta = {
    fixed: { label: "Fixed", icon: CheckCircle2, className: "text-ok" },
    improved: { label: "Improved", icon: ArrowRight, className: "text-info" },
    unresolved: { label: "Unresolved", icon: CircleAlert, className: "text-warn" },
    unchanged: { label: "Unchanged", icon: Minus, className: "text-text-tertiary" },
};

export function RevisionDiff({
    items,
    previousLabel = "Previous observation",
    currentLabel = "Current observation",
    scoreChange,
}: {
    items: RevisionDiffItem[];
    previousLabel?: string;
    currentLabel?: string;
    scoreChange?: string;
}) {
    return (
        <section aria-label="Revision comparison" className="rounded-2xl bg-surface">
            {scoreChange && (
                <p className="mb-3 text-sm font-medium tabular text-text-primary">
                    Score change: {scoreChange}
                </p>
            )}
            <div className="divide-y divide-divider">
                {items.map((item) => {
                    const meta = statusMeta[item.status];
                    const Icon = meta.icon;
                    return (
                        <article
                            key={item.id}
                            className="grid gap-3 py-4 lg:grid-cols-[180px_1fr_24px_1fr]"
                        >
                            <div>
                                <p className="font-medium text-text-primary">{item.label}</p>
                                <p
                                    className={cn(
                                        "mt-1 flex items-center gap-1.5 text-xs font-medium",
                                        meta.className,
                                    )}
                                >
                                    <Icon className="h-3.5 w-3.5" aria-hidden />
                                    {meta.label}
                                </p>
                            </div>
                            <div>
                                <p className="text-[11px] font-medium uppercase text-text-tertiary">
                                    {previousLabel}
                                </p>
                                <p className="mt-1 text-sm text-text-secondary">{item.previous}</p>
                            </div>
                            <ArrowRight
                                className="hidden h-4 w-4 self-center text-text-tertiary lg:block"
                                aria-hidden
                            />
                            <div>
                                <p className="text-[11px] font-medium uppercase text-text-tertiary">
                                    {currentLabel}
                                </p>
                                <p className="mt-1 text-sm text-text-primary">{item.current}</p>
                            </div>
                        </article>
                    );
                })}
            </div>
        </section>
    );
}
