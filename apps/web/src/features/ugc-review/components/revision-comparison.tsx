import { CheckCircle2, CircleDot, PlusCircle, ShieldCheck } from "lucide-react";

import type { UgcRevisionComparison } from "../types/ugc-review";
import { formatSystemValue } from "@/shared/lib/display";
import { SurfaceCard } from "@/shared/ui/surface-card";

export function RevisionComparison({ comparison }: { comparison: UgcRevisionComparison }) {
    return (
        <section aria-labelledby="revision-comparison-title">
            <div className="mb-3">
                <h2
                    id="revision-comparison-title"
                    className="text-xl font-semibold text-text-primary"
                >
                    Draft 1 → Draft 2
                </h2>
                <p className="mt-1 text-sm text-text-secondary">{comparison.summary}</p>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
                <ComparisonGroup
                    title="Resolved"
                    icon={<CheckCircle2 className="h-4 w-4" />}
                    items={comparison.resolved}
                    empty="No findings were resolved in this revision."
                    tone="text-ok"
                />
                <ComparisonGroup
                    title="Still open"
                    icon={<CircleDot className="h-4 w-4" />}
                    items={comparison.stillOpen}
                    empty="No earlier findings remain open."
                    tone="text-warn"
                />
                <ComparisonGroup
                    title="New in Draft 2"
                    icon={<PlusCircle className="h-4 w-4" />}
                    items={comparison.newFindings}
                    empty="No new findings were introduced."
                    tone="text-info"
                />
                <SurfaceCard padding="md" variant="outlined">
                    <h3 className="flex items-center gap-2 font-semibold text-ok">
                        <ShieldCheck className="h-4 w-4" />
                        Strengths preserved
                    </h3>
                    {comparison.strengthsPreserved.length ? (
                        <ul className="mt-3 space-y-2 text-sm text-text-secondary">
                            {comparison.strengthsPreserved.map((strength) => (
                                <li key={strength}>• {strength}</li>
                            ))}
                        </ul>
                    ) : (
                        <p className="mt-3 text-sm text-text-secondary">
                            No preserved strengths were reported.
                        </p>
                    )}
                </SurfaceCard>
            </div>
        </section>
    );
}

function ComparisonGroup({
    title,
    icon,
    items,
    empty,
    tone,
}: {
    title: string;
    icon: React.ReactNode;
    items: readonly Readonly<Record<string, unknown>>[];
    empty: string;
    tone: string;
}) {
    return (
        <SurfaceCard padding="md" variant="outlined">
            <h3 className={`flex items-center gap-2 font-semibold ${tone}`}>
                {icon}
                {title}
            </h3>
            {items.length ? (
                <ul className="mt-3 space-y-2 text-sm text-text-secondary">
                    {items.map((item, index) => (
                        <li
                            key={`${findingLabel(item)}-${index}`}
                            className="rounded-lg bg-surface-soft p-3"
                        >
                            {findingLabel(item)}
                        </li>
                    ))}
                </ul>
            ) : (
                <p className="mt-3 text-sm text-text-secondary">{empty}</p>
            )}
        </SurfaceCard>
    );
}

function findingLabel(item: Readonly<Record<string, unknown>>): string {
    for (const key of ["title", "recommendation_title", "summary", "reason", "id"]) {
        const value = item[key];
        if (typeof value === "string" && value.trim()) return value;
    }
    return formatSystemValue(item, "Finding details unavailable");
}
