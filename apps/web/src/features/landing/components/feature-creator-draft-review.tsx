import { Link } from "@tanstack/react-router";
import { ArrowRight, CheckCircle2, XCircle } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { StatusChip } from "@/shared/ui/status-chip";
import { SectionWrapper } from "./section-wrapper";

const checks = [
    {
        expected: 'Approved personalized name: "Milo"',
        observed: 'Product shown in video: "Miles"',
        decision: "Reshoot required",
        passed: false,
    },
    {
        expected: "Same-item before/after proof",
        observed: "Product shown in use, but no comparable result",
        decision: "Missing requirement",
        passed: false,
    },
    {
        expected: "TikTok Shop CTA",
        observed: "CTA present",
        decision: "Passed",
        passed: true,
    },
];

export function FeatureCreatorDraftReview() {
    return (
        <SectionWrapper id="creator-draft-review" background="surface">
            <div className="grid gap-12 lg:grid-cols-2 lg:items-center">
                <div>
                    <StatusChip tone="ok" dot>Feature 5</StatusChip>
                    <h2 className="mt-2 text-2xl font-bold text-text-primary sm:text-3xl">
                        Review the video against the brief &mdash; not against generic AI advice.
                    </h2>
                    <p className="mt-3 text-sm text-text-secondary">
                        When the video was created from a Viraldy Creator Pack, Viraldy knows what
                        was supposed to happen. That means the review can compare:
                    </p>
                    <p className="mt-4 flex items-center gap-3 text-sm font-semibold text-text-primary">
                        <StatusChip tone="info">EXPECTED</StatusChip>
                        <span className="text-text-tertiary">vs.</span>
                        <StatusChip tone="warn">OBSERVED</StatusChip>
                    </p>
                    <p className="mt-4 text-sm text-text-secondary">
                        The result is a review tied to your actual product and your actual creative
                        plan. Not a generic checklist.
                    </p>
                </div>

                <div className="surface-card p-5">
                    <p className="text-xs font-semibold uppercase text-text-tertiary">
                        Creator Draft Review
                    </p>
                    <div className="mt-4 space-y-3">
                        {checks.map((check) => (
                            <div
                                key={check.expected}
                                className="flex items-start gap-3 border-b border-divider pb-3 last:border-b-0 last:pb-0"
                            >
                                {check.passed ? (
                                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-ok" />
                                ) : (
                                    <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
                                )}
                                <div className="min-w-0">
                                    <p className="text-xs text-text-tertiary">
                                        <span className="font-medium">Expected:</span> {check.expected}
                                    </p>
                                    <p className="text-xs text-text-tertiary">
                                        <span className="font-medium">Observed:</span> {check.observed}
                                    </p>
                                    <p
                                        className={`mt-0.5 text-xs font-semibold ${check.passed ? "text-ok" : "text-destructive"}`}
                                    >
                                        {check.decision}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <div className="mt-8 text-center">
                <Button asChild size="sm">
                    <Link to="/login">
                        Check Creator Draft
                        <ArrowRight className="ml-1 h-4 w-4" />
                    </Link>
                </Button>
            </div>
        </SectionWrapper>
    );
}
