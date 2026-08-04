import { Link } from "@tanstack/react-router";
import { ArrowRight, Sparkles, Package, Sparkle, RefreshCw, CheckCircle, AlertTriangle } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { StatusChip } from "@/shared/ui/status-chip";
import { SectionWrapper } from "./section-wrapper";

export function HeroSection() {
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
                <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary-softer px-4 py-1.5 shadow-sm">
                    <Sparkles className="h-3.5 w-3.5 text-primary" />
                    <span className="text-xs font-semibold text-primary">
                        Creative Intelligence for TikTok Shop &amp; Ecommerce
                    </span>
                </div>

                {/* H1 Headline */}
                <h1 className="text-4xl font-bold leading-tight tracking-tight text-text-primary sm:text-5xl lg:text-6xl">
                    Know what TikTok
                    <br />
                    <span className="bg-gradient-to-r from-primary via-warn to-primary bg-clip-text text-transparent">
                        to make next.
                    </span>
                </h1>

                {/* Subheadline */}
                <p className="mt-6 mx-auto max-w-2xl text-base leading-relaxed text-text-secondary sm:text-lg">
                    Viraldy helps TikTok Shop and ecommerce teams turn products and winning creatives into better creative directions, creator-ready plans, and exact video fixes &mdash; before wasting time, samples, or ad spend.
                </p>

                {/* CTA Buttons with Microcopy */}
                <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
                    <div className="flex flex-col items-center">
                        <Button asChild size="lg" className="w-full sm:w-auto shadow-lg shadow-primary/20 bg-primary hover:bg-primary-hover font-semibold">
                            <Link to="/login">
                                Get Creative Directions
                                <ArrowRight className="ml-2 h-4.5 w-4.5" />
                            </Link>
                        </Button>
                        <span className="mt-2 text-[10px] text-text-tertiary">Start with a product</span>
                    </div>

                    <div className="flex flex-col items-center">
                        <Button asChild variant="outline" size="lg" className="w-full sm:w-auto font-semibold">
                            <Link to="/login">
                                Review a Video
                                <ArrowRight className="ml-2 h-4.5 w-4.5" />
                            </Link>
                        </Button>
                        <span className="mt-2 text-[10px] text-text-tertiary">Get an exact fix plan</span>
                    </div>
                </div>

                {/* Micro-tagline */}
                <div className="mt-8 text-xs font-medium tracking-wide text-text-tertiary uppercase">
                    Product in. Creative direction out. Video checked before you spend.
                </div>
            </div>

            {/* HERO MONEY SHOT: Real Product UI Visual composition using Garment Steamer */}
            <div className="mt-16 mx-auto max-w-[1100px] rounded-3xl border border-hairline bg-surface/50 p-6 sm:p-8 backdrop-blur-sm shadow-floating-card">
                <div className="flex flex-wrap items-center justify-between border-b border-divider pb-4 mb-8">
                    <div className="flex items-center gap-2">
                        <Package className="h-5 w-5 text-primary" />
                        <span className="text-sm font-bold text-text-primary">SwiftPress Mini Garment Steamer</span>
                    </div>
                    <StatusChip tone="info" dot>Primary Golden Case Demo</StatusChip>
                </div>

                <div className="grid gap-6 md:grid-cols-12 items-stretch">
                    {/* Left: Product Context Card */}
                    <div className="md:col-span-3 surface-card p-5 border border-divider bg-surface flex flex-col justify-between shadow-sm">
                        <div>
                            <span className="text-[9px] font-bold uppercase tracking-wider text-text-tertiary block">01. Context</span>
                            <h4 className="mt-2 text-sm font-bold text-text-primary">Garment Steamer</h4>
                            <ul className="mt-4 space-y-2 text-xs text-text-secondary">
                                <li><strong>Market</strong>: US</li>
                                <li><strong>Price</strong>: $29.99</li>
                                <li><strong>Buyer</strong>: College student in a dorm</li>
                                <li><strong>Allowed</strong>: Wrinkle removal</li>
                                <li><strong>Prohibited</strong>: 'safe on every fabric'</li>
                            </ul>
                        </div>
                        <div className="mt-4 pt-3 border-t border-divider text-[10px] text-text-tertiary italic">
                            Source: home_travel_steamer
                        </div>
                    </div>

                    {/* Center: 3 Creative Directions Card */}
                    <div className="md:col-span-5 surface-card p-5 border border-primary/25 bg-primary-softer/25 flex flex-col justify-between shadow-sm">
                        <div>
                            <div className="flex justify-between items-center">
                                <span className="text-[9px] font-bold uppercase tracking-wider text-primary block">02. Directions</span>
                                <span className="rounded-full bg-primary-soft px-2 py-0.5 text-[9px] font-bold text-primary">Late-for-Class Rescue</span>
                            </div>
                            <h4 className="mt-2 text-sm font-bold text-text-primary">3 Creative Directions</h4>
                            
                            <div className="mt-3 space-y-2">
                                <div className="p-2.5 rounded-lg bg-surface border border-primary/20 text-xs shadow-sm">
                                    <div className="flex justify-between font-semibold text-text-primary">
                                        <span>Late-for-Class Rescue</span>
                                        <span className="text-primary font-bold">BEST FIT</span>
                                    </div>
                                    <p className="mt-1 text-[11px] text-text-secondary leading-snug">Spoken Hook: 'I had ten minutes before class and this shirt looked like it came straight out of my backpack.'</p>
                                </div>

                                <div className="p-2.5 rounded-lg bg-surface/50 border border-divider text-xs opacity-75">
                                    <span className="font-semibold text-text-primary">Carry-On Clothing Rescue</span>
                                </div>

                                <div className="p-2.5 rounded-lg bg-surface/50 border border-divider text-xs opacity-75">
                                    <span className="font-semibold text-text-primary">Small-Space Alternative</span>
                                </div>
                            </div>
                        </div>
                        <div className="mt-4 pt-3 border-t border-divider text-[10px] text-text-tertiary">
                            Testing: Time pressure vs generic convenience
                        </div>
                    </div>

                    {/* Right: Creator Draft Score & Fix Card */}
                    <div className="md:col-span-4 surface-card p-5 border border-divider bg-surface flex flex-col justify-between shadow-sm">
                        <div>
                            <div className="flex justify-between items-center">
                                <span className="text-[9px] font-bold uppercase tracking-wider text-text-tertiary block">03. Video QA</span>
                                <span className="text-base font-bold text-text-primary">71<span className="text-xs text-text-tertiary">/100</span></span>
                            </div>
                            <h4 className="mt-2 text-sm font-bold text-text-primary">Draft 1 Verification</h4>

                            <div className="mt-3 space-y-2">
                                <div className="p-2 rounded-lg bg-destructive-soft border border-destructive/20 text-[11px] leading-snug">
                                    <div className="flex items-center gap-1 font-semibold text-destructive">
                                        <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                                        <span>REVISION REQUIRED</span>
                                    </div>
                                    <p className="mt-1 text-text-secondary">
                                        <strong>Quick Edit:</strong> Product reveal is late (4.2s vs expected &lt; 2.0s).
                                    </p>
                                    <p className="mt-1 text-text-secondary">
                                        <strong>Reshoot:</strong> Missing same-shirt before/after proof.
                                    </p>
                                </div>
                            </div>
                        </div>
                        <div className="mt-4 pt-3 border-t border-divider flex items-center justify-between text-[10px] text-text-tertiary">
                            <span>Status: Redirection Pending</span>
                            <span className="text-ok font-semibold">Draft 2: Ready (92/100)</span>
                        </div>
                    </div>
                </div>
            </div>
        </SectionWrapper>
    );
}
