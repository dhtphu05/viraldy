import { Link } from "@tanstack/react-router";
import { ArrowRight, ClipboardList, Film, Clock, AlertTriangle, ShieldCheck } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { SectionWrapper } from "./section-wrapper";
import { steamerStoryboard } from "../demo-data/steamer-demo";

export function FeatureCreatorPack() {
    return (
        <SectionWrapper id="creator-pack" background="default" className="py-20 border-b border-hairline">
            <div className="mx-auto max-w-4xl text-center mb-12">
                <span className="rounded-full bg-primary-soft px-3 py-1.5 text-xs font-semibold text-primary">
                    Chapter 2: Make It Filmable
                </span>
                <h2 className="mt-4 text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
                    Give your creator a plan they can actually film.
                </h2>
                <p className="mt-4 text-lg text-text-secondary leading-relaxed">
                    A good creative concept can still become a bad video if the instructions are vague. Viraldy translates the creative direction into a structured production specification &mdash; not just a generic text script.
                </p>
            </div>

            <div className="grid gap-12 lg:grid-cols-12 lg:items-start">
                {/* Left: Production Specification Details */}
                <div className="lg:col-span-5 space-y-6">
                    <div>
                        <span className="text-[10px] font-bold text-primary uppercase tracking-wider block">Production Plan Specs</span>
                        <h3 className="mt-2 text-xl font-bold text-text-primary">The Creator Plan Blueprint</h3>
                    </div>

                    <div className="space-y-4 text-xs">
                        <div className="flex gap-3">
                            <span className="grid h-8 w-8 place-items-center rounded-lg bg-info-soft text-info shrink-0">
                                <Film className="h-4 w-4" />
                            </span>
                            <div>
                                <h4 className="font-bold text-text-primary">What to Film</h4>
                                <p className="mt-1 text-text-secondary leading-relaxed">
                                    Opening scene hooks, specific product close-ups, handheld demo mechanics, and side-by-side comparative proof setups.
                                </p>
                            </div>
                        </div>

                        <div className="flex gap-3">
                            <span className="grid h-8 w-8 place-items-center rounded-lg bg-ok-soft text-ok shrink-0">
                                <ClipboardList className="h-4 w-4" />
                            </span>
                            <div>
                                <h4 className="font-bold text-text-primary">What to Say</h4>
                                <p className="mt-1 text-text-secondary leading-relaxed">
                                    Multiple spoken hooks matched to student dead-line pressure, essential selling talking points, and specific shop-checkout CTAs.
                                </p>
                            </div>
                        </div>

                        <div className="flex gap-3">
                            <span className="grid h-8 w-8 place-items-center rounded-lg bg-destructive-soft text-destructive shrink-0">
                                <AlertTriangle className="h-4 w-4" />
                            </span>
                            <div>
                                <h4 className="font-bold text-text-primary">What NOT to Get Wrong</h4>
                                <p className="mt-1 text-text-secondary leading-relaxed">
                                    Enforced constraints: avoid instant wrinkle claims or universal fabric compatibility. Required text overlay: 'Results vary by fabric type.'
                                </p>
                            </div>
                        </div>

                        <div className="flex gap-3">
                            <span className="grid h-8 w-8 place-items-center rounded-lg bg-primary-soft text-primary shrink-0">
                                <ShieldCheck className="h-4 w-4" />
                            </span>
                            <div>
                                <h4 className="font-bold text-text-primary">What Approval Looks Like</h4>
                                <p className="mt-1 text-text-secondary leading-relaxed">
                                    Preflight validation checks mapping expected hooks, timestamps, variant naming, and disclosures.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Right: Storyboard timeline for Garment Steamer */}
                <div className="lg:col-span-7 surface-card p-6 border border-hairline shadow-md">
                    <div className="flex items-center gap-2 border-b border-divider pb-3 mb-4">
                        <Clock className="h-4 w-4 text-text-secondary" />
                        <span className="text-xs font-bold text-text-primary uppercase tracking-wider">
                            Steamer Storyboard (Late-for-Class Concept)
                        </span>
                    </div>

                    <div className="relative pl-6 space-y-5">
                        {/* Vertical line connector */}
                        <div className="absolute left-2.5 top-2 bottom-2 w-0.5 bg-divider" />

                        {steamerStoryboard.map((shot, idx) => (
                            <div key={idx} className="relative text-xs">
                                {/* Bullet indicator */}
                                <div className="absolute -left-[21px] top-1.5 h-2.5 w-2.5 rounded-full bg-primary border-2 border-surface shadow-sm" />

                                <div className="flex justify-between font-bold text-text-primary">
                                    <span>Shot {idx + 1} ({shot.time})</span>
                                    <span className="text-[10px] text-text-tertiary uppercase tracking-wider">{shot.type}</span>
                                </div>
                                <p className="mt-1 text-text-secondary leading-relaxed">{shot.action}</p>
                                {shot.details && (
                                    <p className="mt-1 text-[11px] font-medium text-primary bg-primary-softer/30 rounded px-2.5 py-1 inline-block">
                                        {shot.details}
                                    </p>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <div className="mt-12 text-center">
                <Button asChild size="sm">
                    <Link to="/login">
                        Create Creator Plan
                        <ArrowRight className="ml-2 h-4 w-4" />
                    </Link>
                </Button>
            </div>
        </SectionWrapper>
    );
}
