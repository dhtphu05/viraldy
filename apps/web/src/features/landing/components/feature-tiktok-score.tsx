import { Link } from "@tanstack/react-router";
import { AlertTriangle, ArrowRight, CheckCircle2, Pencil } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { StatusChip } from "@/shared/ui/status-chip";
import { SectionWrapper } from "./section-wrapper";

const fixes = [
    {
        label: "FIX 01",
        title: "Move the product reveal earlier.",
        expected: "Product clearly visible before 2.0 seconds for the selected direction.",
        observed: "First clear appearance at 4.2 seconds.",
        action: "Move the existing close-up to approximately 1.2 seconds.",
        needsReshoot: false,
    },
    {
        label: "FIX 02",
        title: "Add observable product proof.",
        expected: "Same-shirt treated vs untreated comparison.",
        observed: "Steam is visible, but the result cannot be compared.",
        action: "Record one continuous shot showing the same area before and after use.",
        needsReshoot: true,
    },
];

export function FeatureTikTokScore() {
    return (
        <SectionWrapper id="tiktok-score">
            <div className="grid gap-12 lg:grid-cols-2 lg:items-start">
                <div>
                    <StatusChip tone="warn" dot>Feature 4</StatusChip>
                    <h2 className="mt-2 text-2xl font-bold text-text-primary sm:text-3xl">
                        Upload the draft.
                    </h2>
                    <h3 className="mt-1 text-xl font-semibold text-text-secondary">
                        Know exactly what needs to change.
                    </h3>
                    <p className="mt-3 text-sm text-text-secondary">
                        A score alone does not help you fix a video. Viraldy reviews the actual
                        creative and turns the findings into an edit-or-reshoot plan.
                    </p>
                </div>

                <div className="surface-card p-5">
                    <div className="flex items-center justify-between">
                        <StatusChip tone="warn" dot>TikTok Creative Review</StatusChip>
                        <span className="text-3xl font-bold tabular text-text-primary">71<span className="text-lg text-text-tertiary">/100</span></span>
                    </div>

                    <div className="mt-3 flex items-center gap-2">
                        <StatusChip tone="warn">Revise before paid use</StatusChip>
                        <span className="text-xs text-text-tertiary">Decision</span>
                    </div>

                    <div className="mt-3 flex gap-4 text-xs text-text-secondary">
                        <span><strong className="text-text-primary">2</strong> blockers</span>
                        <span><strong className="text-text-primary">1</strong> quick edit</span>
                        <span><strong className="text-text-primary">1</strong> creator reshoot</span>
                    </div>

                    <div className="mt-5 space-y-4">
                        {fixes.map((fix) => (
                            <div key={fix.label} className="border-t border-divider pt-4 first:border-t-0 first:pt-0">
                                <p className="text-xs font-bold text-primary">{fix.label}</p>
                                <p className="mt-1 text-sm font-semibold text-text-primary">
                                    {fix.title}
                                </p>
                                <dl className="mt-2 space-y-1 text-xs">
                                    <div className="flex gap-1.5">
                                        <dt className="shrink-0 font-medium text-text-tertiary">Expected:</dt>
                                        <dd className="text-text-secondary">{fix.expected}</dd>
                                    </div>
                                    <div className="flex gap-1.5">
                                        <dt className="shrink-0 font-medium text-text-tertiary">Observed:</dt>
                                        <dd className="text-text-secondary">{fix.observed}</dd>
                                    </div>
                                    <div className="flex gap-1.5">
                                        <dt className="shrink-0 font-medium text-text-tertiary">Action:</dt>
                                        <dd className="text-text-secondary">{fix.action}</dd>
                                    </div>
                                </dl>
                                <p className="mt-1 flex items-center gap-1.5 text-xs">
                                    <span className="text-text-tertiary">Needs reshoot?</span>
                                    {fix.needsReshoot ? (
                                        <span className="flex items-center gap-1 font-medium text-destructive">
                                            <AlertTriangle className="h-3 w-3" /> Yes
                                        </span>
                                    ) : (
                                        <span className="flex items-center gap-1 font-medium text-ok">
                                            <CheckCircle2 className="h-3 w-3" /> No
                                        </span>
                                    )}
                                </p>
                            </div>
                        ))}
                    </div>

                    <div className="mt-4 border-t border-divider pt-3">
                        <p className="text-xs font-semibold uppercase text-ok">Preserve</p>
                        <ul className="mt-1 space-y-0.5 text-xs text-text-secondary">
                            <li>Natural creator delivery</li>
                            <li>Current setting</li>
                            <li>Existing CTA</li>
                        </ul>
                    </div>
                </div>
            </div>

            <div className="mt-8 text-center">
                <Button asChild size="sm">
                    <Link to="/login">
                        Review My Video
                        <ArrowRight className="ml-1 h-4 w-4" />
                    </Link>
                </Button>
                <p className="mt-3 text-xs text-text-tertiary italic">
                    &ldquo;Know what to edit. Know what to reshoot. Know what to keep.&rdquo;
                </p>
            </div>
        </SectionWrapper>
    );
}
