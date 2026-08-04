import { SectionWrapper } from "./section-wrapper";
import { Link } from "@tanstack/react-router";
import { CheckCircle2, RefreshCw } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { StatusChip } from "@/shared/ui/status-chip";

export function RevisionCompare() {
    const revisionCompareRows = [
        { id: "rev-1", metric: "Product Reveal", draft1: "First visible at 4.2s (Too late)", draft2: "First visible at 1.4s (Resolved)", status: "resolved" },
        { id: "rev-2", metric: "Same-Item Proof", draft1: "Steam only, no visible comparison", draft2: "Clear side-by-side before/after (2.6s hold)", status: "resolved" },
        { id: "rev-3", metric: "Required Disclosure", draft1: "No disclosure overlay text", draft2: "'Results vary by fabric type.' added (15.2–18.0s)", status: "resolved" },
        { id: "rev-4", metric: "CTA & Delivery", draft1: "TikTok Shop tag present at 18.8s", draft2: "Tag preserved, natural delivery intact", status: "preserved" },
    ];

    return (
        <SectionWrapper id="revision-compare" background="default" className="py-20 border-b border-hairline">
            {/* Header */}
            <div className="mx-auto max-w-4xl text-center mb-12">
                <span className="rounded-full bg-ok-soft px-3 py-1.5 text-xs font-semibold text-ok uppercase">
                    Version 2 is back
                </span>
                <h2 className="mt-4 text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
                    Don't review every revision from zero.
                </h2>
                <p className="mt-4 text-lg text-text-secondary leading-relaxed">
                    Viraldy carries the original requirements, failures and strengths into the next review. You see exactly what changed, what was fixed, and what was preserved.
                </p>
            </div>

            {/* Revision Comparison Table */}
            <div className="mx-auto max-w-4xl grid gap-6 md:grid-cols-12 items-start mb-8">
                {/* Left Table */}
                <div className="md:col-span-8 space-y-4">
                    <h3 className="text-xs font-bold text-text-tertiary uppercase tracking-wider">
                        Revision Comparison
                    </h3>
                    <div className="overflow-hidden rounded-2xl border border-divider bg-surface shadow-sm">
                        <table className="w-full text-left text-xs leading-normal">
                            <thead>
                                <tr className="border-b border-divider bg-surface-soft font-bold text-text-primary">
                                    <th className="p-3">Requirement Metric</th>
                                    <th className="p-3">Draft 1 (Score: 71)</th>
                                    <th className="p-3">Draft 2 (Score: 87)</th>
                                    <th className="p-3">Status</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-divider text-text-secondary font-medium">
                                {revisionCompareRows.map((row) => (
                                    <tr key={row.id}>
                                        <td className="p-3 font-semibold text-text-primary">{row.metric}</td>
                                        <td className="p-3 text-destructive">{row.draft1}</td>
                                        <td className="p-3 text-ok">{row.draft2}</td>
                                        <td className="p-3 font-bold uppercase text-[9px]">
                                            <span className={row.status === "resolved" ? "text-ok" : "text-info"}>
                                                {row.status}
                                            </span>
                                        </td>
                                    </tr>
                                    ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Right: Resolved / Preserved list */}
                <div className="md:col-span-4 space-y-4">
                    <h3 className="text-xs font-bold text-text-tertiary uppercase tracking-wider">
                        Status Delta
                    </h3>
                    <div className="p-4 rounded-xl border border-divider bg-surface shadow-sm space-y-4 text-xs leading-relaxed">
                        <div className="space-y-2">
                            <span className="font-bold text-ok uppercase text-[9px] tracking-wide block">Resolved</span>
                            <ul className="space-y-1 text-text-secondary list-disc pl-4">
                                <li><strong>PRODUCT_REVEAL_LATE:</strong> 4.2s &rarr; 1.4s</li>
                                <li><strong>SAME_ITEM_PROOF_MISSING:</strong> Steam &rarr; 2.6s proof hold</li>
                                <li><strong>REQUIRED_DISCLOSURE_MISSING:</strong> Added at 15.2–18.0s</li>
                            </ul>
                        </div>
                        <div className="space-y-2">
                            <span className="font-bold text-info uppercase text-[9px] tracking-wide block">Preserved</span>
                            <ul className="space-y-1 text-text-secondary list-disc pl-4">
                                <li>Creator authenticity</li>
                                <li>Product-tag CTA</li>
                                <li>Platform pacing</li>
                            </ul>
                        </div>
                        <div className="space-y-1">
                            <span className="font-bold text-text-primary uppercase text-[9px] tracking-wide block">New Issues</span>
                            <p className="text-text-primary font-semibold">0</p>
                        </div>
                        <div className="text-[10px] text-text-tertiary pt-2 border-t border-divider">
                            All mandatory revision blockers were resolved without removing the strongest creator and CTA signals.
                        </div>
                    </div>
                </div>
            </div>

            {/* Revised Decision card */}
            <div className="mx-auto max-w-lg p-6 rounded-3xl border border-ok/20 bg-ok-softer/10 shadow-sm flex flex-col justify-between">
                <div>
                    <div className="flex justify-between items-center border-b border-ok/10 pb-3 mb-4">
                        <h4 className="text-base font-bold text-text-primary">Revised Decision</h4>
                        <div className="flex items-center gap-1">
                            <span className="text-lg font-bold text-ok">87</span>
                            <span className="text-xs text-text-tertiary">/100</span>
                        </div>
                    </div>

                    <span className="inline-flex items-center gap-1.5 rounded-full bg-ok-soft px-3 py-1 text-xs font-bold text-ok mb-4">
                        <CheckCircle2 className="h-4 w-4 shrink-0" />
                        READY FOR A SMALL PAID TEST
                    </span>

                    <dl className="grid gap-4 sm:grid-cols-2 text-xs leading-normal">
                        <div>
                            <dt className="font-bold text-text-tertiary">Confidence</dt>
                            <dd className="text-text-primary font-semibold">High</dd>
                        </div>
                        <div>
                            <dt className="font-bold text-text-tertiary">Hard Blockers</dt>
                            <dd className="text-text-primary font-semibold">0</dd>
                        </div>
                        <div className="sm:col-span-2">
                            <dt className="font-bold text-text-tertiary">Detected Strengths</dt>
                            <dd className="text-text-secondary">
                                Product appears at 1.4s, Same-shirt proof observable, Required disclosure present, Product-tag CTA clear, Creator delivery remains natural.
                            </dd>
                        </div>
                        <div className="sm:col-span-2 p-2 rounded bg-surface border border-divider text-[10px] text-text-tertiary">
                            <strong>Caveats:</strong> Structural readiness does not guarantee sales performance. Confirm Spark and editing rights before paid amplification.
                        </div>
                    </dl>
                </div>

                <div className="mt-6 pt-4 border-t border-ok/10 flex justify-between items-center gap-2">
                    <span className="text-[11px] text-text-secondary">Next Action: Approve organic post + limited paid test after rights.</span>
                    <Button asChild size="sm" className="bg-ok hover:bg-ok-hover text-white shadow-sm font-semibold">
                        <Link to="/login">
                            Approve Revision
                        </Link>
                    </Button>
                </div>
            </div>
        </SectionWrapper>
    );
}
