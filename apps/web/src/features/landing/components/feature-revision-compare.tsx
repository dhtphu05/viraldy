import { Link } from "@tanstack/react-router";
import { ArrowRight, CheckCircle2 } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { StatusChip } from "@/shared/ui/status-chip";
import { SectionWrapper } from "./section-wrapper";

const comparisons = [
    { draft1: "Product appears at 4.2s", draft2: "Product appears at 1.4s", fixed: true },
    { draft1: "No observable proof", draft2: "Same-item proof added", fixed: true },
    { draft1: "CTA present", draft2: "CTA preserved", fixed: true },
    { draft1: "Unsupported claim", draft2: "Claim removed", fixed: true },
];

export function FeatureRevisionCompare() {
    return (
        <SectionWrapper id="revision-compare">
            <div className="grid gap-12 lg:grid-cols-2 lg:items-center">
                <div>
                    <StatusChip tone="info" dot>Feature 6</StatusChip>
                    <h2 className="mt-2 text-2xl font-bold text-text-primary sm:text-3xl">
                        See whether the new version actually fixed the problem.
                    </h2>
                    <p className="mt-3 text-sm text-text-secondary">
                        Upload Draft 2 and Viraldy compares it with the previous version.
                    </p>
                </div>

                <div className="surface-card p-5">
                    <div className="flex items-center justify-center gap-4 text-sm font-semibold text-text-primary">
                        <div className="rounded-lg border border-hairline bg-background px-4 py-2 text-center">
                            <span className="block text-[10px] text-text-tertiary">DRAFT 1</span>
                        </div>
                        <ArrowRight className="h-4 w-4 text-text-tertiary" />
                        <div className="rounded-lg border border-primary/20 bg-primary-softer px-4 py-2 text-center">
                            <span className="block text-[10px] text-primary">DRAFT 2</span>
                        </div>
                    </div>

                    <div className="mt-5 space-y-2.5">
                        {comparisons.map((row) => (
                            <div
                                key={row.draft1}
                                className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 border-b border-divider pb-2.5 last:border-b-0 last:pb-0"
                            >
                                <span className="text-xs text-text-tertiary line-through">{row.draft1}</span>
                                <span className="text-xs text-text-tertiary">&rarr;</span>
                                <span className="flex items-center gap-1.5 text-xs text-text-secondary">
                                    {row.draft2}
                                    {row.fixed && <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-ok" />}
                                </span>
                            </div>
                        ))}
                    </div>

                    <div className="mt-4 rounded-lg bg-ok-soft/50 p-3">
                        <StatusChip tone="ok" className="mb-1">RESULT</StatusChip>
                        <p className="text-xs leading-relaxed text-text-secondary">
                            All mandatory blockers resolved. Strong creator delivery preserved.
                        </p>
                    </div>
                </div>
            </div>

            <div className="mt-8 text-center">
                <Button asChild size="sm">
                    <Link to="/login">
                        Compare Revisions
                        <ArrowRight className="ml-1 h-4 w-4" />
                    </Link>
                </Button>
                <p className="mt-3 text-xs text-text-tertiary italic">
                    &ldquo;Stop reviewing every revision from zero.&rdquo;
                </p>
            </div>
        </SectionWrapper>
    );
}
