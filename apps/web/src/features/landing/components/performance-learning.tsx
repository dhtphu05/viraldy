import { SectionWrapper } from "./section-wrapper";
import { Link } from "@tanstack/react-router";
import { FlaskConical, BarChart3, HelpCircle, ArrowRight, Clipboard } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { StatusChip } from "@/shared/ui/status-chip";
import { ConfidenceBadge } from "@/shared/ui/confidence-badge";

export function PerformanceLearning() {
    const data = [
        {
            concept: "Late for Class Rescue",
            views: "31,400",
            clicks: "1,180",
            orders: "42",
            gmv: "$1,259.58",
        },
        {
            concept: "Small-Space Alternative",
            views: "28,900",
            clicks: "1,460",
            orders: "37",
            gmv: "$1,109.63",
        },
    ];

    const nextTests = [
        {
            num: "Next Test 01",
            concept: "Late for Class Rescue",
            action: "Create Variant",
            instruction: "Use a different student creator while preserving the same proof mechanism.",
            why: "Test whether the order signal belongs to the angle rather than one creator execution.",
        },
        {
            num: "Next Test 02",
            concept: "Small-Space Alternative",
            action: "Fix and Retest",
            instruction: "Retest with clearer price/value framing after proof.",
            why: "The concept generated strong product-click behavior but fewer observed orders.",
        },
    ];

    return (
        <SectionWrapper id="performance-learning" background="default" className="py-20 border-b border-hairline">
            <div className="mx-auto max-w-4xl text-center mb-12">
                <span className="rounded-full bg-primary-soft px-3 py-1.5 text-xs font-semibold text-primary">
                    Chapter 4: What to Test Next
                </span>
                <h2 className="mt-4 text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
                    Every creative test should make the next one smarter.
                </h2>
                <p className="mt-4 text-lg text-text-secondary leading-relaxed">
                    Viraldy should not call a creative &ldquo;the winner&rdquo; just because one number looks better. It connects performance back to the concept and recommends what should be tested next.
                </p>
            </div>

            <div className="mx-auto max-w-4xl grid gap-8 lg:grid-cols-12 lg:items-start">
                {/* Left: Performance Data Table & Read */}
                <div className="lg:col-span-6 space-y-6">
                    {/* Performance Table */}
                    <div className="rounded-2xl border border-divider bg-surface overflow-hidden shadow-sm">
                        <div className="p-4 border-b border-divider bg-surface-soft flex justify-between items-center">
                            <span className="text-xs font-bold text-text-primary uppercase tracking-wider flex items-center gap-1.5">
                                <BarChart3 className="h-4 w-4 text-primary" />
                                Campaign Performance Data
                            </span>
                            <StatusChip tone="info" className="text-[9px] font-bold">Status: Directional</StatusChip>
                        </div>
                        <table className="w-full text-left text-xs leading-normal">
                            <thead>
                                <tr className="border-b border-divider text-text-tertiary font-bold bg-surface-soft/50">
                                    <th className="p-3">Concept</th>
                                    <th className="p-3">Views</th>
                                    <th className="p-3">Clicks</th>
                                    <th className="p-3">Orders</th>
                                    <th className="p-3">GMV</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-divider text-text-secondary font-medium">
                                {data.map((row) => (
                                    <tr key={row.concept}>
                                        <td className="p-3 font-semibold text-text-primary">{row.concept}</td>
                                        <td className="p-3 tabular">{row.views}</td>
                                        <td className="p-3 tabular text-primary">{row.clicks}</td>
                                        <td className="p-3 tabular">{row.orders}</td>
                                        <td className="p-3 tabular text-ok">{row.gmv}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    {/* Viraldy Performance Read */}
                    <div className="p-5 rounded-2xl bg-surface border border-hairline shadow-sm space-y-4 text-xs leading-relaxed">
                        <h4 className="font-bold text-text-primary uppercase text-[10px] tracking-wider border-b border-divider pb-2 flex justify-between">
                            <span>Viraldy Performance Interpretation</span>
                            <span className="text-[9px] font-semibold text-text-tertiary font-mono">Sample: Early Test Window</span>
                        </h4>
                        <p className="text-text-secondary">
                            <strong>Summary:</strong> Late for Class generated more observed orders and GMV in this test window. Small-Space Alternative generated more product clicks relative to its views. The available sample is not enough to declare either concept a universally winning pattern.
                        </p>

                        <div className="space-y-3">
                            <div className="p-3 rounded-lg bg-surface-soft border border-divider">
                                <div className="flex justify-between items-center">
                                    <strong className="text-text-primary block">Observation 1: Late for Class Rescue</strong>
                                    <ConfidenceBadge level="medium" />
                                </div>
                                <p className="mt-1 text-text-secondary">Higher observed: Orders, GMV</p>
                            </div>

                            <div className="p-3 rounded-lg bg-surface-soft border border-divider">
                                <div className="flex justify-between items-center">
                                    <strong className="text-text-primary block">Observation 2: Small-Space Alternative</strong>
                                    <ConfidenceBadge level="medium" />
                                </div>
                                <p className="mt-1 text-text-secondary">Stronger observed: Product exploration / click behavior</p>
                            </div>
                        </div>

                        <p className="text-[11px] text-text-tertiary">
                            <strong>Diagnosis:</strong> Time-pressure positioning may be stronger for immediate order intent in this sample. Space-saving comparison may create stronger product exploration but needs offer/page validation before concluding it is weaker commercially.
                        </p>
                    </div>
                </div>

                {/* Right: What to Test Next Recommendations */}
                <div className="lg:col-span-6 space-y-6">
                    <div className="flex items-center justify-between border-b border-divider pb-3">
                        <h3 className="text-xs font-bold text-text-tertiary uppercase tracking-wider flex items-center gap-1.5">
                            <FlaskConical className="h-4.5 w-4.5 text-primary" />
                            Next Test Recommendations
                        </h3>
                        <span className="text-[10px] bg-primary-soft text-primary font-bold px-2 py-0.5 rounded-full uppercase">Feedback Loop</span>
                    </div>

                    <div className="space-y-4">
                        {nextTests.map((test) => (
                            <div key={test.num} className="p-5 rounded-2xl border border-hairline bg-surface shadow-sm hover:border-primary/20 transition-all duration-300">
                                <div className="flex justify-between items-center border-b border-divider pb-3 mb-3">
                                    <span className="text-[10px] font-bold text-text-tertiary uppercase">{test.num}</span>
                                    <span className="inline-flex items-center gap-1.5 rounded-full bg-primary-soft px-2.5 py-0.5 text-[10px] font-bold text-primary">
                                        Action: {test.action}
                                    </span>
                                </div>
                                <h4 className="text-sm font-bold text-text-primary uppercase">{test.concept}</h4>
                                <dl className="mt-3 space-y-2 text-xs">
                                    <div>
                                        <dt className="font-bold text-text-tertiary uppercase text-[9px] tracking-wide">Instruction</dt>
                                        <dd className="text-text-secondary mt-0.5">{test.instruction}</dd>
                                    </div>
                                    <div>
                                        <dt className="font-bold text-text-tertiary uppercase text-[9px] tracking-wide font-semibold text-primary">Why</dt>
                                        <dd className="text-text-secondary mt-0.5">{test.why}</dd>
                                    </div>
                                </dl>
                            </div>
                        ))}
                    </div>

                    {/* Bottom Caveat */}
                    <div className="p-3.5 rounded-xl bg-surface-soft border border-divider text-[11px] leading-relaxed text-text-secondary flex gap-2 items-start">
                        <HelpCircle className="h-4.5 w-4.5 text-warn shrink-0 mt-0.5" />
                        <div>
                            This is directional evidence, not causal proof. Do not automatically promote the pattern to &ldquo;supported&rdquo; from this sample.
                        </div>
                    </div>
                </div>
            </div>
        </SectionWrapper>
    );
}
