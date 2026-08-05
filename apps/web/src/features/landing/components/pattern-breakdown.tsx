import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowRight, Video, ShieldAlert, Sparkles, CheckCircle2, ChevronRight } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { SectionWrapper } from "./section-wrapper";
import { StatusChip } from "@/shared/ui/status-chip";
import { ConfidenceBadge } from "@/shared/ui/confidence-badge";
import { EvidenceTimeline, type EvidenceTimelineMarker } from "@/shared/ui/evidence-timeline";

export function PatternBreakdown() {
    const [activeMarkerId, setActiveMarkerId] = useState<string>("hook");
    const [currentTime, setCurrentTime] = useState<number>(0);

    const markers: EvidenceTimelineMarker[] = [
        { id: "hook", at: 0, label: "Situational Hook", kind: "hook", preview: "Spoken: 'I was already late and this shirt was still wrinkled.'" },
        { id: "product", at: 1.3, label: "Product Reveal", kind: "product", preview: "Visual: Compact steamer handheld entry." },
        { id: "demo", at: 5.0, label: "Fabric Demo", kind: "demo", preview: "Action: Glide steam over wrinkled sleeve." },
        { id: "proof", at: 11.0, label: "Same-Shirt Proof", kind: "proof", preview: "Evidence: Side-by-side wrinkle check." },
        { id: "cta", at: 20.1, label: "Product Tag CTA", kind: "cta", preview: "Action: Tag link overlay 'Shop now' appears." },
    ];

    const handleSeek = (seconds: number, marker: EvidenceTimelineMarker) => {
        setCurrentTime(seconds);
        setActiveMarkerId(marker.id);
    };

    return (
        <SectionWrapper id="pattern-breakdown" background="surface" className="py-20 border-b border-hairline">
            <div className="mx-auto max-w-4xl text-center mb-12">
                <span className="rounded-full bg-primary-soft px-3 py-1.5 text-xs font-semibold text-primary">
                    Winning Pattern Breakdown
                </span>
                <h2 className="mt-4 text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
                    Viraldy doesn't just summarize the video.
                    <br />
                    It shows why the structure works.
                </h2>
                <p className="mt-4 text-lg text-text-secondary leading-relaxed">
                    The analysis connects what happened, where it happened, and how confident the system is &mdash; without pretending the reference proves sales performance.
                </p>
            </div>

            <div className="grid gap-8 lg:grid-cols-12 lg:items-start">
                {/* Left: Video Mockup & Timeline */}
                <div className="lg:col-span-5 space-y-6">
                    {/* Simulated Phone Video Player */}
                    <div className="relative mx-auto max-w-[280px] aspect-[9/16] rounded-3xl border-[6px] border-text-primary bg-foreground overflow-hidden shadow-lg flex flex-col justify-between p-4">
                        {/* Video Header */}
                        <div className="flex justify-between items-center text-white/80 text-[10px] z-10">
                            <span className="font-semibold flex items-center gap-1">
                                <Video className="h-3 w-3" />
                                Reference Steamer
                            </span>
                            <span>23.4s</span>
                        </div>

                        {/* Middle: Dynamic visual state overlay based on active marker */}
                        <div className="flex-1 flex flex-col items-center justify-center text-center p-4 text-white z-10">
                            {activeMarkerId === "hook" && (
                                <div className="space-y-2 animate-fadeIn">
                                    <span className="text-[10px] bg-info text-white font-bold px-2 py-0.5 rounded-full uppercase">Situational Hook (0.0s)</span>
                                    <p className="text-xs italic">"I was already late and this shirt was still wrinkled."</p>
                                    <div className="text-[10px] text-white/60">Visual: Wrinkled fabric close-up</div>
                                </div>
                            )}
                            {activeMarkerId === "product" && (
                                <div className="space-y-2 animate-fadeIn">
                                    <span className="text-[10px] bg-ok text-white font-bold px-2 py-0.5 rounded-full uppercase">Product Reveal (1.3s)</span>
                                    <p className="text-xs">SwiftPress steamer enters frame</p>
                                    <div className="text-[10px] text-white/60">Visual: Handheld close-up in-use</div>
                                </div>
                            )}
                            {activeMarkerId === "demo" && (
                                <div className="space-y-2 animate-fadeIn">
                                    <span className="text-[10px] bg-info text-white font-bold px-2 py-0.5 rounded-full uppercase">In-Use Demo (5.0s)</span>
                                    <p className="text-xs">Steam gliding over fabric</p>
                                    <div className="text-[10px] text-white/60">Visual: Steam contact area close-up</div>
                                </div>
                            )}
                            {activeMarkerId === "proof" && (
                                <div className="space-y-2 animate-fadeIn">
                                    <span className="text-[10px] bg-ok text-white font-bold px-2 py-0.5 rounded-full uppercase">Same-Shirt Proof (11.0s)</span>
                                    <p className="text-xs font-semibold">Treated vs Untreated</p>
                                    <div className="text-[10px] text-white/60">Visual: Clean half/wrinkled half</div>
                                </div>
                            )}
                            {activeMarkerId === "cta" && (
                                <div className="space-y-2 animate-fadeIn">
                                    <span className="text-[10px] bg-info text-white font-bold px-2 py-0.5 rounded-full uppercase">Product Tag (20.1s)</span>
                                    <p className="text-xs">"It is linked right here."</p>
                                    <div className="inline-block mt-2 px-3 py-1 bg-primary text-white text-[10px] font-bold rounded-lg shadow-sm">
                                        Shop now
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Playback Progress Overlay */}
                        <div className="h-1 w-full bg-white/20 rounded-full overflow-hidden z-10">
                            <div
                                className="h-full bg-primary transition-all duration-300"
                                style={{ width: `${(currentTime / 23.4) * 100}%` }}
                            />
                        </div>
                    </div>

                    {/* Timeline Component */}
                    <div className="space-y-2">
                        <span className="text-[10px] font-bold text-text-tertiary uppercase tracking-wide block">Interactive Evidence Timeline</span>
                        <EvidenceTimeline
                            duration={23.4}
                            currentTime={currentTime}
                            markers={markers}
                            activeId={activeMarkerId}
                            onSeek={handleSeek}
                        />
                    </div>
                </div>

                {/* Right: Detailed Evidence & Signals panel */}
                <div className="lg:col-span-7 space-y-6">
                    {/* Header */}
                    <div className="flex items-center justify-between border-b border-divider pb-3">
                        <span className="text-xs font-bold text-text-tertiary uppercase tracking-wider">
                            Evidence-Backed Creative Breakdown
                        </span>
                        <StatusChip tone="info">Source: home_travel_steamer</StatusChip>
                    </div>

                    {/* Scrollable details */}
                    <div className="space-y-4 max-h-[500px] overflow-y-auto pr-2">
                        {/* 01 Hook */}
                        <div
                            onClick={() => handleSeek(0, markers[0])}
                            className={`p-4 rounded-2xl border transition-all duration-300 cursor-pointer ${
                                activeMarkerId === "hook"
                                    ? "bg-primary-softer border-primary/30 shadow-sm"
                                    : "bg-surface border-hairline hover:border-divider"
                            }`}
                        >
                            <div className="flex justify-between items-start gap-2">
                                <div>
                                    <span className="text-[9px] font-bold text-text-tertiary uppercase tracking-wider">0.0s - 2.0s</span>
                                    <h4 className="text-sm font-bold text-text-primary mt-1">OPENING (Hook type: Situational problem)</h4>
                                </div>
                                <ConfidenceBadge level="high" />
                            </div>
                            <div className="mt-3 grid gap-3 sm:grid-cols-2 text-xs leading-normal">
                                <div>
                                    <span className="text-[10px] font-semibold text-text-tertiary block">Spoken Hook (98% conf):</span>
                                    <p className="text-text-primary italic">"I was already late and this shirt was still wrinkled."</p>
                                </div>
                                <div>
                                    <span className="text-[10px] font-semibold text-text-tertiary block">Opening Visual (95% conf):</span>
                                    <p className="text-text-secondary">Creator holds a wrinkled shirt close to camera.</p>
                                </div>
                            </div>
                            <div className="mt-2 text-[10px] text-text-tertiary">Hook confidence: 93%</div>
                        </div>

                        {/* 02 First Three Seconds & Product Reveal */}
                        <div
                            onClick={() => handleSeek(1.3, markers[1])}
                            className={`p-4 rounded-2xl border transition-all duration-300 cursor-pointer ${
                                activeMarkerId === "product"
                                    ? "bg-primary-softer border-primary/30 shadow-sm"
                                    : "bg-surface border-hairline hover:border-divider"
                            }`}
                        >
                            <div className="flex justify-between items-start gap-2">
                                <div>
                                    <span className="text-[9px] font-bold text-text-tertiary uppercase tracking-wider">1.3s</span>
                                    <h4 className="text-sm font-bold text-text-primary mt-1">PRODUCT (First Appearance)</h4>
                                </div>
                                <ConfidenceBadge level="high" />
                            </div>
                            <p className="mt-2 text-xs text-text-secondary leading-relaxed">
                                First product appearance at <strong>1.3s</strong> (Confidence: 96%). Shot types detected: <strong>Handheld close-up</strong>, <strong>In-use</strong>.
                            </p>
                            <p className="mt-1 text-xs text-text-secondary leading-relaxed">
                                <strong>Narrative (92% conf):</strong> Problem &rarr; Solution &rarr; Transformation. Angle: <em>Last-minute clothing rescue</em>. Buyer pain: <em>Wrinkled clothing immediately before leaving</em>.
                            </p>
                        </div>

                        {/* 03 Demo */}
                        <div
                            onClick={() => handleSeek(5.0, markers[2])}
                            className={`p-4 rounded-2xl border transition-all duration-300 cursor-pointer ${
                                activeMarkerId === "demo"
                                    ? "bg-primary-softer border-primary/30 shadow-sm"
                                    : "bg-surface border-hairline hover:border-divider"
                            }`}
                        >
                            <div className="flex justify-between items-start gap-2">
                                <div>
                                    <span className="text-[9px] font-bold text-text-tertiary uppercase tracking-wider">5.0s</span>
                                    <h4 className="text-sm font-bold text-text-primary mt-1">DEMO (Same-item in-use transformation)</h4>
                                </div>
                                <ConfidenceBadge level="high" />
                            </div>
                            <p className="mt-2 text-xs text-text-secondary">
                                Detected: <strong>Yes</strong> (98% confidence). Mechanism clarity: <strong>Clear</strong>. Result visibility: <strong>Clear</strong>.
                            </p>
                            <ol className="mt-2 list-decimal pl-4 text-xs text-text-secondary space-y-1">
                                <li>Show wrinkled fabric.</li>
                                <li>Apply steam to same area.</li>
                                <li>Show same area after use.</li>
                            </ol>
                        </div>

                        {/* 04 Proof */}
                        <div
                            onClick={() => handleSeek(11.0, markers[3])}
                            className={`p-4 rounded-2xl border transition-all duration-300 cursor-pointer ${
                                activeMarkerId === "proof"
                                    ? "bg-primary-softer border-primary/30 shadow-sm"
                                    : "bg-surface border-hairline hover:border-divider"
                            }`}
                        >
                            <div className="flex justify-between items-start gap-2">
                                <div>
                                    <span className="text-[9px] font-bold text-text-tertiary uppercase tracking-wider">11.0s</span>
                                    <h4 className="text-sm font-bold text-text-primary mt-1">PROOF (Observable visual result)</h4>
                                </div>
                                <ConfidenceBadge level="medium" />
                            </div>
                            <p className="mt-2 text-xs text-text-secondary leading-relaxed">
                                Same-item before/after visible proof (Confidence: 91%). Verifiability: <strong>Medium-high</strong>.
                            </p>
                            <div className="mt-2 p-2 rounded bg-surface-soft border border-divider text-[10px] text-text-secondary flex gap-2 items-start">
                                <ShieldAlert className="h-3.5 w-3.5 text-warn shrink-0 mt-0.5" />
                                <div>
                                    <strong>Uncertainty:</strong> Lighting changes slightly between before and after.
                                </div>
                            </div>
                        </div>

                        {/* 05 Editing & Claims */}
                        <div className="p-4 rounded-2xl border border-hairline bg-surface">
                            <h4 className="text-sm font-bold text-text-primary">CREATOR, PACING &amp; CLAIMS</h4>
                            <div className="mt-3 space-y-3 text-xs leading-relaxed">
                                <div>
                                    <strong className="text-text-primary block">Creator Delivery (90% confidence)</strong>
                                    <p className="text-text-secondary">Casual first-person review. Authenticity cues: Situational context, natural speech, hands-on demonstration.</p>
                                </div>
                                <div>
                                    <strong className="text-text-primary block">Editing Pacing (Fast but readable)</strong>
                                    <p className="text-text-secondary">First 3-second cut count: 2. Pattern interrupts: wrinkled-shirt close-up, fast product hand-entry. Dead air: None observed.</p>
                                </div>
                                <div>
                                    <strong className="text-text-primary block">Observed Claim: "It fixed the wrinkles so fast."</strong>
                                    <p className="text-text-secondary mt-1">
                                        <StatusChip tone="warn" className="text-[9px] mr-1">Risk: Medium</StatusChip>
                                        Visible result supports the direction of the claim, but broad speed language should not be copied into a new product context without support.
                                    </p>
                                </div>
                            </div>
                        </div>

                        {/* 06 CTA */}
                        <div
                            onClick={() => handleSeek(20.1, markers[4])}
                            className={`p-4 rounded-2xl border transition-all duration-300 cursor-pointer ${
                                activeMarkerId === "cta"
                                    ? "bg-primary-softer border-primary/30 shadow-sm"
                                    : "bg-surface border-hairline hover:border-divider"
                            }`}
                        >
                            <div className="flex justify-between items-start gap-2">
                                <div>
                                    <span className="text-[9px] font-bold text-text-tertiary uppercase tracking-wider">20.1s</span>
                                    <h4 className="text-sm font-bold text-text-primary mt-1">COMMERCE CTA (TikTok Shop Product Tag)</h4>
                                </div>
                                <ConfidenceBadge level="high" />
                            </div>
                            <p className="mt-2 text-xs text-text-secondary leading-relaxed">
                                Present: <strong>Yes</strong>. Type: <strong>TikTok Shop product tag</strong>. Start: <strong>20.1s</strong>. Spoken CTA: <em>"It is linked right here."</em> Overlay: <em>"Shop now"</em>.
                            </p>
                        </div>
                    </div>

                    {/* Important Uncertainties Block */}
                    <div className="p-4 rounded-2xl bg-surface-soft border border-divider text-xs space-y-2 text-text-secondary">
                        <h4 className="font-bold text-text-primary uppercase text-[10px] tracking-wider">Important Uncertainties</h4>
                        <ul className="list-disc pl-4 space-y-1">
                            <li>Creator persona inferred from content style, not verified profile data.</li>
                            <li>No performance data is attached, so this does not prove that the creative structure caused sales.</li>
                        </ul>
                    </div>
                </div>
            </div>
        </SectionWrapper>
    );
}
