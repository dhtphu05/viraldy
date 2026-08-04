import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowRight, AlertTriangle, Copy, Cpu, Info } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { StatusChip } from "@/shared/ui/status-chip";
import { SectionWrapper } from "./section-wrapper";
import { ExpectedObservedTable, type ExpectedObservedRow } from "@/shared/ui/expected-observed-table";
import { EvidenceTimeline, type EvidenceTimelineMarker } from "@/shared/ui/evidence-timeline";
import { ConfidenceBadge } from "@/shared/ui/confidence-badge";

export function ReviewBeforeYouSpend() {
    const [currentTime, setCurrentTime] = useState<number>(0);
    const [activeMarkerId, setActiveMarkerId] = useState<string>("hook_gap");

    // Draft 1 Markers
    const d1Markers: EvidenceTimelineMarker[] = [
        { id: "hook_gap", at: 0, label: "Situational Hook", kind: "hook", preview: "Spoken: 'I had ten minutes before class...'" },
        { id: "late_reveal", at: 4.2, label: "Observed Product Reveal (Late)", kind: "risk", preview: "Product first visible at 4.2s (Expected <= 2.0s)." },
        { id: "demo_gap", at: 7.5, label: "Demo & Proof Gap", kind: "missing", preview: "Steam visible, but fabric comparison missing." },
        { id: "cta_tag", at: 18.8, label: "Product Tag CTA", kind: "cta", preview: "Spoken: 'Tap the link right here.'" },
    ];

    const expectedObservedRows: ExpectedObservedRow[] = [
        {
            id: "req-1",
            requirement: <strong>Product reveal</strong>,
            observed: "First visible at 4.2s",
            status: "missing",
            confidence: "high",
            evidence: <p className="text-[10px] text-destructive font-semibold">Hard Blocker: late reveal</p>,
        },
        {
            id: "req-2",
            requirement: <strong>Target product</strong>,
            observed: "SwiftPress product match confirmed",
            status: "met",
            confidence: "high",
            evidence: <p className="text-[10px] text-ok">93% product match confidence</p>,
        },
        {
            id: "req-3",
            requirement: <strong>Same-shirt demo</strong>,
            observed: "Product in use, exact continuity uncertain",
            status: "partial",
            confidence: "medium",
        },
        {
            id: "req-4",
            requirement: <strong>Same-shirt proof</strong>,
            observed: "Steam visibility only, result not comparable",
            status: "missing",
            confidence: "high",
        },
        {
            id: "req-5",
            requirement: <strong>Fabric disclosure</strong>,
            observed: "Not found across 9 text sources",
            status: "missing",
            confidence: "high",
            evidence: <p className="text-[10px] text-destructive font-semibold">Hard Blocker: disclosure missing</p>,
        },
        {
            id: "req-6",
            requirement: <strong>Instant-result claim</strong>,
            observed: "Not detected",
            status: "met",
            confidence: "high",
        },
        {
            id: "req-7",
            requirement: <strong>Product tag</strong>,
            observed: "Present at 18.8s",
            status: "met",
            confidence: "high",
        },
        {
            id: "req-8",
            requirement: <strong>CTA deadline</strong>,
            observed: "18.8s (Expected <= 22s)",
            status: "met",
            confidence: "high",
        },
    ];

    const scoreMetrics = [
        { label: "Hook clarity", val: 82, desc: "Specific last-minute clothing problem appears immediately." },
        { label: "Product visibility", val: 55, desc: "Product is clear but first appears at 4.2s, late for this plan." },
        { label: "Demo clarity", val: 76, desc: "Product used on shirt, but continuity is incomplete." },
        { label: "Proof strength", val: 42, desc: "Steam is visible, but the same-shirt result is not observable." },
        { label: "Creator authenticity", val: 88, desc: "Natural delivery consistent with student persona." },
        { label: "Offer clarity", val: 68, desc: "15% discount appears after demo, but proof is not yet strong enough." },
        { label: "CTA readiness", val: 92, desc: "Product-tag CTA appears at 18.8s." },
        { label: "TikTok native fit", val: 84, desc: "Vertical framing and pacing fit the platform." },
        { label: "Claim safety", val: 72, desc: "No prohibited instant-result claim found, but required disclosure is missing." },
    ];

    return (
        <SectionWrapper id="review-before-you-spend" background="surface" className="py-20 border-b border-hairline">
            {/* Header */}
            <div className="mx-auto max-w-4xl text-center mb-12">
                <span className="rounded-full bg-primary-soft px-3 py-1.5 text-xs font-semibold text-primary">
                    Chapter 3: Score &amp; Fix
                </span>
                <h2 className="mt-4 text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
                    Creator sent the draft?
                    <br />
                    Know exactly what to fix.
                </h2>
                <p className="mt-4 text-lg text-text-secondary leading-relaxed">
                    A score alone doesn't fix a video. Viraldy parses the timeline, flags commercial blockers, and separates what can be fixed in post-editing versus what requires a creator reshoot.
                </p>
            </div>

            {/* Content Progress Grid */}
            <div className="mx-auto max-w-4xl space-y-8">
                {/* Simulated Video Player V1 + Timeline */}
                <div className="grid gap-8 lg:grid-cols-12 items-start">
                    <div className="lg:col-span-5 space-y-4">
                        <span className="text-[10px] font-bold text-text-tertiary uppercase tracking-wider block">Creator Draft · V1</span>
                        <h3 className="text-xl font-bold text-text-primary">Is the video actually good enough to use?</h3>
                        <p className="text-xs text-text-secondary leading-relaxed">
                            A video can feel natural and still miss the exact product, proof or campaign requirements that matter. Viraldy evaluates the draft against the Creator Plan.
                        </p>
                        <div className="p-4 rounded-xl bg-surface-soft border border-divider text-[11px] leading-relaxed space-y-1.5">
                            <div><strong>Duration:</strong> 22.7s</div>
                            <div><strong>Product Reveal:</strong> 4.2s (expected &le; 2.0s)</div>
                            <div><strong>Delivery:</strong> Natural creator delivery</div>
                            <div><strong>CTA:</strong> Product tag present at 18.8s</div>
                        </div>
                    </div>

                    <div className="lg:col-span-7 surface-card p-5 border border-hairline shadow-sm space-y-4">
                        <div className="aspect-video w-full rounded-2xl bg-foreground/95 flex flex-col items-center justify-center p-6 text-center text-white relative">
                            <div className="space-y-2">
                                <span className="text-[9px] bg-destructive text-white font-bold px-2 py-0.5 rounded-full uppercase">Blocker Detected</span>
                                <p className="text-xs font-semibold">Wrinkle result unclear &amp; steam only</p>
                                <p className="text-[10px] text-white/60">Product first visible at 4.2s</p>
                            </div>
                        </div>
                        <EvidenceTimeline
                            duration={22.7}
                            currentTime={currentTime}
                            markers={d1Markers}
                            activeId={activeMarkerId}
                            onSeek={(secs, marker) => {
                                setCurrentTime(secs);
                                setActiveMarkerId(marker.id);
                            }}
                        />
                    </div>
                </div>

                {/* Score Summary Metrics Grid */}
                <div className="grid gap-6 md:grid-cols-12 items-start">
                    {/* Score Summary Card */}
                    <div className="md:col-span-5 space-y-6">
                        <div className="p-5 rounded-2xl bg-surface border border-hairline shadow-sm">
                            <span className="text-[10px] font-bold text-text-tertiary uppercase block">Structural Assessment</span>
                            <div className="mt-4 flex items-baseline gap-2">
                                <span className="text-4xl font-bold text-text-primary">74</span>
                                <span className="text-xs text-text-tertiary">/100</span>
                                <StatusChip tone="warn" className="ml-2 uppercase text-[9px] font-bold">REVISE</StatusChip>
                            </div>

                            <div className="mt-6 grid grid-cols-2 gap-4 text-xs">
                                <div>
                                    <span className="font-bold text-text-tertiary block">Brief Alignment</span>
                                    <p className="text-sm font-semibold text-text-primary mt-0.5">57%</p>
                                </div>
                                <div>
                                    <span className="font-bold text-text-tertiary block">Final Combined Score</span>
                                    <p className="text-sm font-bold text-text-primary mt-0.5">71 / 100</p>
                                </div>
                            </div>
                        </div>

                        {/* Dimensions Scroll Area */}
                        <div className="p-4 rounded-xl border border-divider bg-surface-soft max-h-[250px] overflow-y-auto space-y-3">
                            <span className="text-[9px] font-bold text-text-tertiary uppercase tracking-wider block">Scoring Dimensions</span>
                            {scoreMetrics.map((met) => (
                                <div key={met.label} className="text-xs">
                                    <div className="flex justify-between font-semibold text-text-primary">
                                        <span>{met.label}</span>
                                        <span className={met.val < 60 ? "text-destructive" : met.val < 80 ? "text-warn" : "text-ok"}>{met.val}/100</span>
                                    </div>
                                    <p className="text-[10px] text-text-secondary leading-snug mt-0.5">{met.desc}</p>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Expected vs Observed Table */}
                    <div className="md:col-span-7 space-y-4">
                        <h4 className="text-xs font-bold text-text-tertiary uppercase tracking-wider">Did the creator actually deliver the plan?</h4>
                        <ExpectedObservedTable rows={expectedObservedRows} />
                    </div>
                </div>

                {/* Priorities & Revision Message Box */}
                <div className="grid gap-6 md:grid-cols-2">
                    {/* Fix Priorities */}
                    <div className="p-5 rounded-2xl border border-divider bg-surface shadow-sm text-xs leading-relaxed">
                        <h4 className="font-bold text-text-primary uppercase text-[10px] tracking-wider border-b border-divider pb-2 mb-3">Fix Priorities</h4>
                        <div className="space-y-3">
                            <div className="p-2.5 rounded-lg bg-destructive-soft border border-destructive/25">
                                <span className="font-bold text-destructive block uppercase text-[9px]">1. PRODUCT REVEAL LATE (Edit existing footage)</span>
                                <p className="text-text-secondary mt-0.5">Expected &le; 2.0s, Observed 4.2s. <strong>Instruction:</strong> Move the existing product close-up into the first two seconds.</p>
                            </div>
                            <div className="p-2.5 rounded-lg bg-destructive-soft border border-destructive/25">
                                <span className="font-bold text-destructive block uppercase text-[9px]">2. REQUIRED DISCLOSURE MISSING (Overlay / Spoken text)</span>
                                <p className="text-text-secondary mt-0.5">Expected 'Results vary by fabric type.', Observed Not found. <strong>Instruction:</strong> Add the required disclosure.</p>
                            </div>
                            <div className="p-2.5 rounded-lg bg-warn-soft border border-warn/25">
                                <span className="font-bold text-warn block uppercase text-[9px]">3. SAME-ITEM PROOF MISSING (Creator reshoot)</span>
                                <p className="text-text-secondary mt-0.5">Observed steam only, no fabric smoothing. <strong>Instruction:</strong> Return to the exact shirt section shown in the opening and hold the result long enough for comparison.</p>
                            </div>
                            <div className="p-2 bg-surface-soft border border-divider text-text-tertiary">
                                ✓ Keep: Natural student-creator delivery, Product-tag CTA, Platform pacing.
                            </div>
                        </div>
                    </div>

                    {/* Creator Revision Message */}
                    <div className="p-5 rounded-2xl border border-divider bg-surface shadow-sm text-xs flex flex-col justify-between">
                        <div>
                            <h4 className="font-bold text-text-primary uppercase text-[10px] tracking-wider border-b border-divider pb-2 mb-3">Ready-to-send creator revision</h4>
                            <div className="p-3.5 rounded-xl bg-surface-soft border border-divider font-mono text-[11px] text-text-secondary select-all whitespace-pre-wrap leading-relaxed">
                                The student setup and delivery feel natural, and the product-tag ending works well.{"\n\n"}
                                Please move the product close-up into the first two seconds, return to the exact shirt section after steaming so the result is visible, and add the on-screen or spoken disclosure:{"\n"}
                                "Results vary by fabric type."{"\n\n"}
                                Keep the current tone and CTA.
                            </div>
                        </div>
                        <div className="mt-4 flex gap-2">
                            <Button size="sm" className="bg-primary hover:bg-primary-hover shadow-sm">
                                Copy Revision Message
                                <Copy className="ml-1.5 h-3.5 w-3.5" />
                            </Button>
                            <Button asChild size="sm" variant="outline">
                                <Link to="/login">
                                    Upload Revision
                                </Link>
                            </Button>
                        </div>
                    </div>
                </div>

                {/* Context Callout */}
                <div className="p-4 rounded-2xl bg-surface border border-hairline text-xs grid gap-4 md:grid-cols-4 items-center">
                    <div className="md:col-span-1 space-y-1">
                        <h4 className="font-bold text-text-primary uppercase text-[10px] tracking-wider flex items-center gap-1.5">
                            <Cpu className="h-4 w-4 text-primary animate-pulse" />
                            Context-aware
                        </h4>
                        <p className="text-text-secondary text-[11px] leading-relaxed">Timing checks evaluate against structure and target brief, never blind rules.</p>
                    </div>
                    <div className="p-3 rounded-lg bg-surface-soft border border-divider text-[10px]">
                        <span className="font-bold text-ok block uppercase text-[8px]">Product-Led Demo</span>
                        <p className="text-text-secondary mt-0.5">Early reveal expected. Result: Structurally strong.</p>
                    </div>
                    <div className="p-3 rounded-lg bg-surface-soft border border-divider text-[10px]">
                        <span className="font-bold text-info block uppercase text-[8px]">Story-Led POV</span>
                        <p className="text-text-secondary mt-0.5">Later reveal allowed if story setup demands it.</p>
                    </div>
                    <div className="p-3 rounded-lg bg-surface-soft border border-divider text-[10px]">
                        <span className="font-bold text-warn block uppercase text-[8px]">Low-Quality Media</span>
                        <p className="text-text-secondary mt-0.5">Blurry evidence. Result: Request better media instead of guessing.</p>
                    </div>
                </div>
            </div>
        </SectionWrapper>
    );
}
