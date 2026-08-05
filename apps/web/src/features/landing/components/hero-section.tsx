import { useState, useEffect } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowRight, Sparkles, Package, Play, CheckCircle2, AlertTriangle, ShieldCheck } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { StatusChip } from "@/shared/ui/status-chip";
import { SectionWrapper } from "./section-wrapper";

type MoneyShotState = "product" | "directions" | "qa" | "revision";

const heroStoryCopy: Record<MoneyShotState, { label: string; question: string; answer: string; chips: string[] }> = {
    product: {
        label: "01 Find the Angle",
        question: "Not sure which angle is actually worth filming?",
        answer: "Turn one product into different creative bets with different buyers, hooks, proof moments, and test hypotheses.",
        chips: ["3 product-specific directions", "Selected angle", "What each test should teach"],
    },
    directions: {
        label: "02 Brief the Creator",
        question: "Know the angle — but not what your creator should actually film?",
        answer: "Turn the selected direction into a shoot-ready plan with scenes, proof requirements, claims to avoid, and CTA requirements.",
        chips: ["Storyboard", "Must-show proof", "Claim guardrails"],
    },
    qa: {
        label: "03 Review the Draft",
        question: "Creator sent the draft. Is it ready, or does it just look okay?",
        answer: "See exactly what can be edited, what needs a creator reshoot, and what is already strong enough to keep.",
        chips: ["Edit vs reshoot", "Evidence-backed finding", "Keep strengths"],
    },
    revision: {
        label: "04 Verify the Revision",
        question: "Version 2 is back. Did it actually fix the important problems?",
        answer: "Compare Draft 1 against Draft 2 so you know whether blockers were resolved before approval or spend.",
        chips: ["71 → 87", "Resolved blockers", "Small paid test"],
    },
};

export function HeroSection() {
    const [activeStep, setActiveStep] = useState<MoneyShotState>("product");
    const [isPaused, setIsPaused] = useState(false);

    useEffect(() => {
        if (isPaused) return;

        const interval = setInterval(() => {
            setActiveStep((prev) => {
                if (prev === "product") return "directions";
                if (prev === "directions") return "qa";
                if (prev === "qa") return "revision";
                return "product";
            });
        }, 3000);

        return () => clearInterval(interval);
    }, [isPaused]);

    const stepsList: { id: MoneyShotState; label: string; desc: string }[] = [
        { id: "product", label: "1. Add Product", desc: "US Market • $29.99 Steamer" },
        { id: "directions", label: "2. Generate Angles", desc: "3 Differentiated Bets" },
        { id: "qa", label: "3. Check Draft 1", desc: "Score 71 • Flag Blockers" },
        { id: "revision", label: "4. Verify Revision", desc: "Score 87 • Blockers Resolved" },
    ];

    return (
        <SectionWrapper id="hero" className="relative overflow-hidden pt-20 pb-16 sm:pt-24 lg:pt-32">
            {/* Background Gradients */}
            <div
                aria-hidden
                className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,var(--primary-soft),transparent)]"
            />
            <div
                aria-hidden
                className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_60%_40%_at_80%_80%,var(--info-soft),transparent)]"
            />

            <div className="relative mx-auto max-w-4xl text-center">
                {/* Eyebrow */}
                <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary-softer px-4 py-1.5 shadow-sm transition-transform duration-300 hover:scale-105">
                    <Sparkles className="h-3.5 w-3.5 text-primary" />
                    <span className="text-xs font-semibold text-primary uppercase tracking-wider">
                        Creative Intelligence for TikTok Shop · POD · Dropshipping
                    </span>
                </div>

                {/* H1 Headline */}
                <h1 className="text-4xl font-bold leading-tight tracking-tight text-text-primary sm:text-5xl lg:text-6xl">
                    Turn your product into
                    <br />
                    <span className="text-primary">
                        creatives worth testing.
                    </span>
                </h1>

                {/* Subheadline */}
                <p className="mt-6 mx-auto max-w-2xl text-base leading-relaxed text-text-secondary sm:text-lg">
                    Viraldy helps sellers find stronger creative angles, turn them into creator-ready plans, and catch exactly what to edit or reshoot before spending more on content.
                </p>

                <div className="mt-6 mx-auto min-h-[142px] max-w-2xl rounded-2xl border border-primary/20 bg-surface p-4 text-left shadow-soft-card sm:p-5">
                    <div key={activeStep} className="analysis-state-enter">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-primary">
                            {heroStoryCopy[activeStep].label}
                        </span>
                        <p className="mt-2 text-lg font-bold leading-snug text-text-primary sm:text-xl">
                            {heroStoryCopy[activeStep].question}
                        </p>
                        <p className="mt-2 text-sm leading-relaxed text-text-secondary">
                            {heroStoryCopy[activeStep].answer}
                        </p>
                        <div className="mt-3 flex flex-wrap gap-2">
                            {heroStoryCopy[activeStep].chips.map((chip) => (
                                <span key={chip} className="rounded-full bg-primary-soft px-2.5 py-1 text-[10px] font-bold text-primary">
                                    {chip}
                                </span>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Breadcrumb Flow Support Line */}
                <div className="mt-8 mx-auto max-w-xl flex flex-wrap items-center justify-center gap-2 text-xs font-bold text-text-tertiary">
                    <span>Product or reference</span>
                    <span>&rarr;</span>
                    <span className="text-primary font-bold">Creative direction</span>
                    <span>&rarr;</span>
                    <span>Creator plan</span>
                    <span>&rarr;</span>
                    <span className="text-info font-bold">Video review</span>
                    <span>&rarr;</span>
                    <span className="text-ok font-bold">Exact fix</span>
                </div>

                {/* CTA Buttons with Microcopy */}
                <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
                    <div className="flex flex-col items-center">
                        <Button asChild size="lg" className="w-full sm:w-auto shadow-lg shadow-primary/20 bg-primary hover:bg-primary-hover font-semibold transition-all duration-300 hover:-translate-y-0.5">
                            <Link to="/login">
                                Plan My Next Creative
                                <ArrowRight className="ml-2 h-4.5 w-4.5" />
                            </Link>
                        </Button>
                        <span className="mt-2 text-[10px] text-text-tertiary">Start with a product</span>
                    </div>

                    <div className="flex flex-col items-center">
                        <Button asChild variant="outline" size="lg" className="w-full sm:w-auto font-semibold transition-all duration-300 hover:-translate-y-0.5">
                            <Link to="/login">
                                Review My Video
                                <ArrowRight className="ml-2 h-4.5 w-4.5" />
                            </Link>
                        </Button>
                        <span className="mt-2 text-[10px] text-text-tertiary">Get an exact fix plan</span>
                    </div>
                </div>

                {/* Bottom Microcopy */}
                <div className="mt-8 max-w-md mx-auto grid grid-cols-3 gap-2 text-[10px] font-semibold text-text-tertiary tracking-wide uppercase">
                    <div>No generic scripts.</div>
                    <div>No vague &ldquo;make hook stronger.&rdquo;</div>
                    <div>No guessing what to tell your creator.</div>
                </div>
            </div>

            {/* Interactive workflow progress bar for Money Shot */}
            <div className="mt-16 mx-auto max-w-[1100px] flex flex-wrap justify-between gap-2 border-b border-divider pb-4 mb-4">
                {stepsList.map((step) => {
                    const isActive = activeStep === step.id;
                    return (
                        <button
                            key={step.id}
                            onClick={() => {
                                setActiveStep(step.id);
                                setIsPaused(true);
                            }}
                            className={`flex-1 text-left px-4 py-2.5 rounded-xl border transition-all duration-300 ${
                                isActive
                                    ? "bg-primary-soft border-primary/30 shadow-sm"
                                    : "bg-surface/50 border-transparent hover:bg-surface"
                            }`}
                        >
                            <span className={`text-[10px] font-bold uppercase tracking-wider block ${isActive ? "text-primary" : "text-text-tertiary"}`}>
                                {step.label}
                            </span>
                            <span className="text-[11px] text-text-secondary truncate block mt-0.5 font-medium">
                                {step.desc}
                            </span>
                        </button>
                    );
                })}
            </div>

            {/* HERO MONEY SHOT: Composition of 3 Connected Panels */}
            <div className="mx-auto max-w-[1100px] rounded-3xl border border-hairline bg-surface/50 p-6 sm:p-8 backdrop-blur-sm shadow-floating-card transition-all duration-500">
                <div className="flex flex-wrap items-center justify-between border-b border-divider pb-4 mb-8">
                    <div className="flex items-center gap-2">
                        <Package className="h-5 w-5 text-primary" />
                        <span className="text-sm font-bold text-text-primary">SwiftPress Mini Garment Steamer</span>
                    </div>
                    <div className="flex items-center gap-2">
                        {isPaused && (
                            <button
                                onClick={() => setIsPaused(false)}
                                className="text-[10px] text-primary font-semibold hover:underline"
                            >
                                Resume Autoplay
                            </button>
                        )}
                        <StatusChip tone="info" dot>Creative Workflow</StatusChip>
                    </div>
                </div>

                <div className="grid gap-6 md:grid-cols-12 items-stretch">
                    {/* PANEL A: Product Input Context Card */}
                    <div
                        className={`md:col-span-3 p-5 rounded-2xl border flex flex-col justify-between shadow-sm bg-surface transition-all duration-500 ${
                            activeStep === "product"
                                ? "border-primary scale-[1.02] ring-4 ring-primary/10 shadow-lg"
                                : "border-divider opacity-60"
                        }`}
                    >
                        <div>
                            <span className="text-[9px] font-bold uppercase tracking-wider text-text-tertiary block">Panel A · Input Context</span>
                            <h4 className="mt-2 text-sm font-bold text-text-primary">SWIFTPRESS</h4>
                            <p className="text-xs text-text-secondary font-medium">Mini Garment Steamer</p>
                            <ul className="mt-4 space-y-2 text-xs text-text-secondary">
                                <li><strong>Price:</strong> $29.99</li>
                                <li><strong>Market:</strong> US Market</li>
                                <li><strong>Channel:</strong> TikTok Shop</li>
                                <li><strong>Buyer:</strong> College student</li>
                                <li><strong>Goal:</strong> Affiliate creative test</li>
                            </ul>
                        </div>
                        <div className="mt-4 pt-3 border-t border-divider text-[10px] text-text-tertiary font-medium">
                            Product Specs Grounded
                        </div>
                    </div>

                    {/* PANEL B: 3 Creative Directions Card */}
                    <div
                        className={`md:col-span-5 p-5 rounded-2xl border flex flex-col justify-between shadow-sm bg-surface transition-all duration-500 ${
                            activeStep === "directions"
                                ? "border-primary bg-primary-softer/20 scale-[1.02] ring-4 ring-primary/10 shadow-lg"
                                : "border-divider opacity-60"
                        }`}
                    >
                        <div>
                            <div className="flex justify-between items-center">
                                <span className="text-[9px] font-bold uppercase tracking-wider text-primary block">Panel B · Creative Output</span>
                                <span className="rounded-full bg-primary-soft px-2 py-0.5 text-[9px] font-bold text-primary">Late-for-Class Rescue</span>
                            </div>
                            <h4 className="mt-2 text-sm font-bold text-text-primary">3 CREATIVE DIRECTIONS</h4>
                            
                            <div className="mt-3 space-y-2 text-xs leading-normal">
                                <div className="p-2.5 rounded-xl bg-surface border border-primary/20 shadow-sm">
                                    <div className="flex justify-between font-semibold text-text-primary">
                                        <span>Late-for-Class Rescue</span>
                                        <span className="text-primary font-bold uppercase text-[9px] tracking-wider">BEST FIT</span>
                                    </div>
                                    <dl className="mt-2 space-y-1.5 text-[11px] text-text-secondary">
                                        <div>
                                            <dt className="font-bold text-text-tertiary">Buyer:</dt>
                                            <dd>College student in a dorm</dd>
                                        </div>
                                        <div>
                                            <dt className="font-bold text-text-tertiary">Opening:</dt>
                                            <dd>Wrinkled shirt before class</dd>
                                        </div>
                                        <div>
                                            <dt className="font-bold text-text-tertiary">Product:</dt>
                                            <dd>Visible before 1.8s</dd>
                                        </div>
                                        <div>
                                            <dt className="font-bold text-text-tertiary">Demo:</dt>
                                            <dd>Steam the same shirt section</dd>
                                        </div>
                                        <div>
                                            <dt className="font-bold text-text-tertiary">Proof:</dt>
                                            <dd>Return to the same area</dd>
                                        </div>
                                    </dl>
                                </div>
                            </div>
                        </div>
                        <div className="mt-4 pt-3 border-t border-divider text-[10px] text-text-tertiary">
                            Isolating testing angles
                        </div>
                    </div>

                    {/* PANEL C: Creator Draft Review Output */}
                    <div
                        className={`md:col-span-4 p-5 rounded-2xl border flex flex-col justify-between shadow-sm bg-surface transition-all duration-500 ${
                            activeStep === "qa" || activeStep === "revision"
                                ? "border-primary scale-[1.02] ring-4 ring-primary/10 shadow-lg"
                                : "border-divider opacity-60"
                        }`}
                    >
                        {activeStep !== "revision" ? (
                            <div className="h-full flex flex-col justify-between">
                                <div>
                                    <div className="flex justify-between items-center">
                                        <span className="text-[9px] font-bold uppercase tracking-wider text-text-tertiary block">Panel C · Review Output</span>
                                        <span className="text-base font-bold text-text-primary">71<span className="text-xs text-text-tertiary">/100</span></span>
                                    </div>
                                    <h4 className="mt-2 text-sm font-bold text-text-primary">CREATOR DRAFT</h4>
                                    
                                    <div className="mt-3 p-2.5 rounded-xl bg-destructive-soft border border-destructive/20 text-[10px] leading-snug space-y-2">
                                        <div className="flex items-center gap-1.5 font-bold text-destructive">
                                            <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                                            <span>REVISE BEFORE PAID USE</span>
                                        </div>
                                        <div>
                                            <strong className="text-text-primary uppercase text-[8px] tracking-wide block">Quick Edit</strong>
                                            <p className="text-text-secondary">Product reveal is late (observed 4.2s vs expected &le; 2.0s).</p>
                                        </div>
                                        <div>
                                            <strong className="text-text-primary uppercase text-[8px] tracking-wide block">Reshoot</strong>
                                            <p className="text-text-secondary">Same-item result comparison missing.</p>
                                        </div>
                                        <div>
                                            <strong className="text-ok uppercase text-[8px] tracking-wide block">Keep</strong>
                                            <p className="text-text-secondary">Natural creator delivery preserved.</p>
                                        </div>
                                    </div>
                                </div>
                                <div className="mt-4 pt-3 border-t border-divider flex items-center justify-between text-[10px] text-text-tertiary">
                                    <span>Status: Fix Pending</span>
                                    <span className="text-primary font-semibold">Verification Draft 1</span>
                                </div>
                            </div>
                        ) : (
                            <div className="h-full flex flex-col justify-between">
                                <div>
                                    <div className="flex justify-between items-center">
                                        <span className="text-[9px] font-bold uppercase tracking-wider text-text-tertiary block">Panel C · Review Output</span>
                                        <span className="text-base font-bold text-ok">87<span className="text-xs text-text-tertiary">/100</span></span>
                                    </div>
                                    <h4 className="mt-2 text-sm font-bold text-text-primary">CREATOR DRAFT</h4>

                                    <div className="mt-3 p-2.5 rounded-xl bg-ok-soft border border-ok/25 text-[10px] leading-snug space-y-2">
                                        <div className="flex items-center gap-1.5 font-bold text-ok">
                                            <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
                                            <span>ALL BLOCKERS RESOLVED</span>
                                        </div>
                                        <div>
                                            <strong className="text-ok uppercase text-[8px] tracking-wide block">Product Reveal</strong>
                                            <p className="text-text-secondary">✓ Shifted to 1.4s (within 2s bound).</p>
                                        </div>
                                        <div>
                                            <strong className="text-ok uppercase text-[8px] tracking-wide block">Proof</strong>
                                            <p className="text-text-secondary">✓ Same-shirt before/after comparison added.</p>
                                        </div>
                                    </div>
                                </div>
                                <div className="mt-4 pt-3 border-t border-divider flex items-center justify-between text-[10px] text-text-tertiary">
                                    <span>Status: Approved</span>
                                    <span className="text-ok font-semibold">Spark Ads Ready</span>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </SectionWrapper>
    );
}
