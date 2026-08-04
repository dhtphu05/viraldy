import { SectionWrapper } from "./section-wrapper";
import { Link } from "@tanstack/react-router";
import { ArrowRight, Video, User, Clock, ArrowRightCircle } from "lucide-react";
import { Button } from "@/shared/ui/button";

export function ReferenceInput() {
    return (
        <SectionWrapper id="reference-input" background="default" className="py-20 border-b border-hairline">
            <div className="grid gap-12 lg:grid-cols-12 lg:items-center">
                {/* Left: Copy Column */}
                <div className="lg:col-span-5 space-y-5">
                    <span className="rounded-full bg-primary-soft px-3 py-1 text-xs font-semibold text-primary">
                        Start with a Creative Reference
                    </span>
                    <h2 className="text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
                        Found a creative you like?
                        <br />
                        See what's actually happening inside it.
                    </h2>
                    <p className="text-base text-text-secondary leading-relaxed">
                        Viraldy does not start by copying the script. It observes the creative, grounds the important moments in evidence, and separates reusable structure from surface execution.
                    </p>
                    <div className="pt-2">
                        <Button asChild size="lg">
                            <Link to="/login">
                                Analyze Reference Creative
                                <ArrowRight className="ml-2 h-5 w-5" />
                            </Link>
                        </Button>
                    </div>
                </div>

                {/* Right: Input Video Card Visual */}
                <div className="lg:col-span-7">
                    <div className="mx-auto max-w-lg rounded-3xl border border-hairline bg-surface p-6 shadow-soft-card">
                        <div className="flex items-center justify-between border-b border-divider pb-4 mb-4">
                            <div className="flex items-center gap-2">
                                <Video className="h-5 w-5 text-primary" />
                                <span className="text-sm font-bold text-text-primary">Reference Video Input</span>
                            </div>
                            <span className="rounded-full bg-surface-muted px-2.5 py-1 text-[10px] font-bold text-text-secondary">
                                External Competitor
                            </span>
                        </div>

                        <div className="space-y-4">
                            {/* Metadata Strip */}
                            <div className="flex gap-4 text-xs text-text-secondary">
                                <span className="flex items-center gap-1">
                                    <Clock className="h-3.5 w-3.5 text-text-tertiary" />
                                    <strong>Duration:</strong> 23.4s
                                </span>
                                <span className="flex items-center gap-1">
                                    <User className="h-3.5 w-3.5 text-text-tertiary" />
                                    <strong>Creator Type:</strong> Student / lifestyle creator
                                </span>
                            </div>

                            {/* Simulated Video Placeholder */}
                            <div className="aspect-video w-full rounded-2xl bg-surface-muted border border-divider flex flex-col items-center justify-center p-4 text-center">
                                <div className="h-10 w-10 rounded-full bg-white/80 flex items-center justify-center text-primary shadow-sm mb-2 hover:scale-105 transition-transform duration-300">
                                    <Video className="h-5 w-5" />
                                </div>
                                <span className="text-xs font-semibold text-text-primary">Portable Steamer Competitor Video</span>
                                <span className="text-[10px] text-text-tertiary mt-1">Grounded Reference for SwiftPress Campaign</span>
                            </div>

                            {/* Observed Flow Panel */}
                            <div className="p-4 rounded-2xl bg-surface-soft border border-divider">
                                <h4 className="text-xs font-bold text-text-primary uppercase tracking-wider mb-3">
                                    Observed Sequence Flow
                                </h4>
                                <div className="flex flex-wrap items-center gap-2 text-xs">
                                    <span className="p-2 rounded-lg bg-surface border border-divider text-text-primary">
                                        Wrinkled shirt problem
                                    </span>
                                    <ArrowRightCircle className="h-4 w-4 text-text-tertiary" />
                                    <span className="p-2 rounded-lg bg-surface border border-divider text-text-primary">
                                        Product reveal
                                    </span>
                                    <ArrowRightCircle className="h-4 w-4 text-text-tertiary" />
                                    <span className="p-2 rounded-lg bg-surface border border-divider text-text-primary">
                                        Steaming demo
                                    </span>
                                    <ArrowRightCircle className="h-4 w-4 text-text-tertiary" />
                                    <span className="p-2 rounded-lg bg-surface border border-divider text-text-primary">
                                        Same-shirt result
                                    </span>
                                    <ArrowRightCircle className="h-4 w-4 text-text-tertiary" />
                                    <span className="p-2 rounded-lg bg-surface border border-divider text-text-primary">
                                        Product-tag CTA
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </SectionWrapper>
    );
}
