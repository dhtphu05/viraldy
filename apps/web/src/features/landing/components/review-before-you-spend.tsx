import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowRight, AlertTriangle, CheckCircle2, XCircle, Play, Video, HelpCircle } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { StatusChip } from "@/shared/ui/status-chip";
import { SectionWrapper } from "./section-wrapper";
import { steamerFixes, steamerRevisionCompare } from "../demo-data/steamer-demo";
import { podChecks } from "../demo-data/pod-demo";

type ReviewFeature = "score-fix" | "draft-review" | "revision-compare";

export function ReviewBeforeYouSpend() {
    const [activeFeature, setActiveFeature] = useState<ReviewFeature>("score-fix");

    return (
        <SectionWrapper id="tiktok-score" background="surface" className="py-20">
            {/* Header */}
            <div className="mx-auto max-w-4xl text-center">
                <span className="rounded-full bg-warn-soft px-3 py-1.5 text-xs font-semibold text-warn">
                    Chapter 3: Quality Control & Validation
                </span>
                <h2 className="mt-4 text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
                    The creator sent the video. Now what?
                </h2>
                <p className="mt-4 text-lg text-text-secondary">
                    Stop making creative decisions based on gut feel or generic advice. Viraldy reviews drafts against structural commerce requirements, tells you what can be fixed in editing versus what needs a reshoot, and compares revisions automatically.
                </p>
            </div>

            {/* Differentiate Section */}
            <div className="mt-12 mx-auto max-w-4xl rounded-2xl bg-surface-soft border border-hairline p-6 shadow-sm">
                <h3 className="text-sm font-bold uppercase tracking-wider text-text-tertiary">
                    Understanding the Review Features
                </h3>
                <div className="mt-4 grid gap-6 md:grid-cols-2">
                    <div className="p-4 rounded-xl bg-surface border border-divider">
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-neutral-soft px-2 py-0.5 text-xs font-semibold text-text-primary">
                            TikTok Score &amp; Fix
                        </span>
                        <h4 className="mt-2 text-sm font-semibold text-text-primary">Use on: Any video draft or competitor creative</h4>
                        <p className="mt-2 text-xs text-text-secondary leading-relaxed">
                            Checks structural and commerce-readiness. Identifies whether hooks, product reveals, demos, proof, and CTA are present and properly timed.
                        </p>
                        <p className="mt-2 text-xs font-medium text-primary">Output: Edit-or-reshoot fix plan</p>
                    </div>

                    <div className="p-4 rounded-xl bg-surface border border-divider">
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-primary-soft px-2 py-0.5 text-xs font-semibold text-primary">
                            Creator Draft Review
                        </span>
                        <h4 className="mt-2 text-sm font-semibold text-text-primary">Use on: Briefs made from a Creator Plan</h4>
                        <p className="mt-2 text-xs text-text-secondary leading-relaxed">
                            Checks if the creator followed your product and campaign briefs (variants, approved claims, required scenes, name personalizations).
                        </p>
                        <p className="mt-2 text-xs font-medium text-ok">Output: Expected vs Observed compliance audit</p>
                    </div>
                </div>
            </div>

            {/* Interactive Demos Switcher */}
            <div className="mt-12 flex justify-center border-b border-divider">
                <div className="flex gap-6">
                    <button
                        onClick={() => setActiveFeature("score-fix")}
                        className={`pb-4 text-sm font-bold border-b-2 transition-colors ${
                            activeFeature === "score-fix"
                                ? "border-primary text-primary"
                                : "border-transparent text-text-secondary hover:text-text-primary"
                        }`}
                    >
                        1. TikTok Score &amp; Fix
                    </button>
                    <button
                        onClick={() => setActiveFeature("draft-review")}
                        className={`pb-4 text-sm font-bold border-b-2 transition-colors ${
                            activeFeature === "draft-review"
                                ? "border-primary text-primary"
                                : "border-transparent text-text-secondary hover:text-text-primary"
                        }`}
                    >
                        2. Creator Draft Review
                    </button>
                    <button
                        onClick={() => setActiveFeature("revision-compare")}
                        className={`pb-4 text-sm font-bold border-b-2 transition-colors ${
                            activeFeature === "revision-compare"
                                ? "border-primary text-primary"
                                : "border-transparent text-text-secondary hover:text-text-primary"
                        }`}
                    >
                        3. Revision Compare
                    </button>
                </div>
            </div>

            {/* Tab Panels */}
            <div key={activeFeature} className="mt-8 mx-auto max-w-4xl analysis-state-enter">
                {activeFeature === "score-fix" && (
                    <div className="grid gap-8 lg:grid-cols-12 lg:items-start">
                        {/* Explanation */}
                        <div className="lg:col-span-5 space-y-4">
                            <h3 className="text-xl font-bold text-text-primary">Upload any video. Get exact fix recommendations.</h3>
                            <p className="text-sm text-text-secondary leading-relaxed">
                                A simple quality score doesn't tell you how to save a failing draft. Viraldy parses the timeline, flags commercial blockers, and categorizes fixes by effort:
                            </p>
                            <ul className="space-y-2.5 text-xs text-text-secondary">
                                <li className="flex items-start gap-2">
                                    <span className="h-1.5 w-1.5 mt-1.5 shrink-0 rounded-full bg-destructive" />
                                    <span><strong>Blockers</strong>: Critical errors that halt advertising use.</span>
                                </li>
                                <li className="flex items-start gap-2">
                                    <span className="h-1.5 w-1.5 mt-1.5 shrink-0 rounded-full bg-warn" />
                                    <span><strong>Quick Edits</strong>: Timing adjustments you can fix in post-production.</span>
                                </li>
                                <li className="flex items-start gap-2">
                                    <span className="h-1.5 w-1.5 mt-1.5 shrink-0 rounded-full bg-ok" />
                                    <span><strong>Keepers</strong>: Strengths to preserve in the final edit.</span>
                                </li>
                            </ul>
                            <div className="pt-2">
                                <Button asChild size="sm">
                                    <Link to="/login">
                                        Review My Video
                                        <ArrowRight className="ml-2 h-4 w-4" />
                                    </Link>
                                </Button>
                            </div>
                        </div>

                        {/* Scorer UI Representation */}
                        <div className="lg:col-span-7 surface-card p-6 border border-hairline shadow-md">
                            <div className="flex items-center justify-between border-b border-divider pb-4">
                                <div>
                                    <span className="text-[10px] font-bold text-text-tertiary uppercase">Product Case</span>
                                    <h4 className="text-sm font-bold text-text-primary">SwiftPress Mini Garment Steamer</h4>
                                </div>
                                <div className="text-right">
                                    <span className="text-[10px] font-bold text-text-tertiary uppercase block">Creative Score</span>
                                    <span className="text-2xl font-bold text-text-primary">71<span className="text-sm text-text-tertiary font-normal">/100</span></span>
                                </div>
                            </div>

                            <div className="mt-4 flex items-center justify-between">
                                <StatusChip tone="warn" dot>Revise before paid use</StatusChip>
                                <span className="text-xs text-text-tertiary">1 Creator Reshoot • 2 Quick Edits</span>
                            </div>

                            {/* Fix Checklist */}
                            <div className="mt-6 space-y-4">
                                {steamerFixes.slice(0, 2).map((fix) => (
                                    <div key={fix.id} className="p-3.5 rounded-xl bg-surface-soft border border-divider">
                                        <div className="flex items-center justify-between">
                                            <span className="text-[10px] font-bold tracking-wider text-destructive uppercase">Blocker</span>
                                            <StatusChip tone={fix.needsReshoot ? "destructive" : "warn"}>
                                                {fix.needsReshoot ? "Needs Reshoot" : "Edit Fix"}
                                            </StatusChip>
                                        </div>
                                        <h5 className="mt-1 text-sm font-semibold text-text-primary">{fix.title}</h5>
                                        <dl className="mt-2 space-y-1 text-xs">
                                            <div className="flex gap-2">
                                                <dt className="shrink-0 text-text-tertiary font-medium">Expected:</dt>
                                                <dd className="text-text-secondary">{fix.expected}</dd>
                                            </div>
                                            <div className="flex gap-2">
                                                <dt className="shrink-0 text-text-tertiary font-medium">Observed:</dt>
                                                <dd className="text-text-secondary">{fix.observed}</dd>
                                            </div>
                                            <div className="flex gap-2">
                                                <dt className="shrink-0 text-text-tertiary font-medium">Action:</dt>
                                                <dd className="text-primary font-medium">{fix.action}</dd>
                                            </div>
                                        </dl>
                                    </div>
                                ))}
                            </div>

                            {/* Strengths to preserve */}
                            <div className="mt-4 border-t border-divider pt-4">
                                <span className="text-[10px] font-bold text-ok uppercase tracking-wider block">Strengths to Preserve</span>
                                <ul className="mt-2 space-y-1 text-xs text-text-secondary list-disc pl-4">
                                    <li>Natural lifestyle student-creator delivery</li>
                                    <li>Clear shop checkout call to action ('Tap product tag')</li>
                                    <li>Excellent vertical framing and pacing</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                )}

                {activeFeature === "draft-review" && (
                    <div className="grid gap-8 lg:grid-cols-12 lg:items-start">
                        {/* Explanation */}
                        <div className="lg:col-span-5 space-y-4">
                            <h3 className="text-xl font-bold text-text-primary">Did the creator follow your product instructions?</h3>
                            <p className="text-sm text-text-secondary leading-relaxed">
                                Reviewing custom variants, personalization specs, and legal disclosures is a manual bottleneck. Viraldy automates checking drafts against your approved brief parameters.
                            </p>
                            <div className="rounded-xl bg-primary-softer p-4 border border-primary/10">
                                <span className="text-[10px] font-bold text-primary uppercase block">Dog Mom POD Case</span>
                                <p className="mt-1 text-xs text-text-secondary">
                                    The brief required naming the dog <strong>Milo</strong> on the printed crewneck. Creator wore a crewneck displaying <strong>Miles</strong>. Instantly flagged as a personalization blocker.
                                </p>
                            </div>
                            <div className="pt-2">
                                <Button asChild size="sm">
                                    <Link to="/login">
                                        Verify Brief Alignment
                                        <ArrowRight className="ml-2 h-4 w-4" />
                                    </Link>
                                </Button>
                            </div>
                        </div>

                        {/* Expected vs Observed Table */}
                        <div className="lg:col-span-7 surface-card p-6 border border-hairline shadow-md">
                            <span className="text-[10px] font-bold text-text-tertiary uppercase tracking-wider block mb-4">
                                Creator Draft Brief Alignment
                            </span>
                            <div className="space-y-4">
                                {podChecks.map((check) => {
                                    const isBlocked = check.status.includes("fail") || check.status.includes("blocked");
                                    return (
                                        <div key={check.id} className="border-b border-divider pb-4 last:border-b-0 last:pb-0">
                                            <div className="flex items-center justify-between gap-2">
                                                <div className="flex items-center gap-1.5 text-xs">
                                                    <span className="font-semibold text-text-primary">Expected:</span>
                                                    <span className="text-text-secondary">{check.requirement.replace("Approved personalization: ", "")}</span>
                                                </div>
                                                <StatusChip tone={isBlocked ? "destructive" : "ok"}>
                                                    {isBlocked ? "Mismatch" : "Passed"}
                                                </StatusChip>
                                            </div>
                                            <div className="mt-2 pl-3 border-l-2 border-divider space-y-1 text-xs">
                                                <div>
                                                    <span className="text-text-tertiary font-medium">Observed:</span>{" "}
                                                    <span className="text-text-secondary">{check.observed}</span>
                                                </div>
                                                <div>
                                                    <span className="text-text-tertiary font-medium">Evidence:</span>{" "}
                                                    <span className="text-text-secondary italic">{check.evidence}</span>
                                                </div>
                                                <div className="mt-1 font-medium text-text-primary">
                                                    {check.action}
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    </div>
                )}

                {activeFeature === "revision-compare" && (
                    <div className="grid gap-8 lg:grid-cols-12 lg:items-start">
                        {/* Explanation */}
                        <div className="lg:col-span-5 space-y-4">
                            <h3 className="text-xl font-bold text-text-primary">Don't review every revision from zero.</h3>
                            <p className="text-sm text-text-secondary leading-relaxed">
                                When creators upload Version 2, your team shouldn't have to watch the entire video to spot changes. Viraldy tracks previous blockers and reports whether they are fixed, unchanged, or if new regressions appeared.
                            </p>
                            <div className="p-4 rounded-xl bg-ok-soft border border-ok/10 text-xs">
                                <span className="font-bold text-ok uppercase block">Steamer Case Result</span>
                                <p className="mt-1 text-text-secondary">
                                    All mandatory blockers resolved. Strong creator delivery preserved. Ready for launch.
                                </p>
                            </div>
                            <div className="pt-2">
                                <Button asChild size="sm">
                                    <Link to="/login">
                                        Compare Draft Revisions
                                        <ArrowRight className="ml-2 h-4 w-4" />
                                    </Link>
                                </Button>
                            </div>
                        </div>

                        {/* Side-by-side Revision Comparison */}
                        <div className="lg:col-span-7 surface-card p-6 border border-hairline shadow-md">
                            <div className="flex items-center justify-between border-b border-divider pb-4">
                                <span className="text-[10px] font-bold text-text-tertiary uppercase">Draft Revision Compare</span>
                                <span className="text-xs font-semibold text-ok">Score upgrade: +21 pts</span>
                            </div>

                            <div className="mt-4 space-y-3">
                                {steamerRevisionCompare.map((row) => (
                                    <div key={row.id} className="grid grid-cols-12 gap-2 py-2.5 border-b border-divider last:border-b-0 last:pb-0 items-center">
                                        <div className="col-span-4 text-xs font-semibold text-text-primary">
                                            {row.metric}
                                        </div>
                                        <div className="col-span-4 text-[11px] text-text-tertiary line-through truncate">
                                            {row.draft1}
                                        </div>
                                        <div className="col-span-4 flex items-center justify-between gap-1 text-xs text-text-primary pl-2">
                                            <span className="truncate">{row.draft2.replace(" (Resolved)", "")}</span>
                                            {row.status === "fixed" ? (
                                                <CheckCircle2 className="h-4 w-4 text-ok shrink-0" />
                                            ) : (
                                                <span className="text-[10px] text-text-tertiary">Preserved</span>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </SectionWrapper>
    );
}
