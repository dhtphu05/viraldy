import { Link } from "@tanstack/react-router";
import { ArrowRight, Users, Eye, Play, Sparkles } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { StatusChip } from "@/shared/ui/status-chip";
import { SectionWrapper } from "./section-wrapper";
import { steamerDirections } from "../demo-data/steamer-demo";

export function FeatureCreativeDirections() {
    return (
        <SectionWrapper id="creative-directions" background="surface" className="py-20 border-b border-hairline">
            <div className="mx-auto max-w-3xl text-center mb-12">
                <span className="rounded-full bg-primary-soft px-3 py-1.5 text-xs font-semibold text-primary">
                    3 Creative Options
                </span>
                <h2 className="mt-4 text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
                    Turn one product into three different creative bets.
                </h2>
                <p className="mt-4 text-lg text-text-secondary leading-relaxed">
                    Viraldy combines your product context with relevant creative patterns and gives you three genuinely different directions. Not 20 random hooks. Not three rewrites of the same script. Three distinct creative directions to test.
                </p>
            </div>

            {/* Grid of Directions */}
            <div className="grid gap-6 md:grid-cols-3">
                {steamerDirections.map((dir) => {
                    const isSelected = dir.conceptId === "late_for_class";
                    return (
                        <div
                            key={dir.number}
                            className={`surface-card p-6 border flex flex-col justify-between shadow-sm transition-all duration-200 ${
                                isSelected
                                    ? "border-primary/30 bg-primary-softer/20 shadow-md ring-2 ring-primary/10"
                                    : "border-hairline bg-surface hover:border-divider"
                            }`}
                        >
                            <div>
                                <div className="flex items-center justify-between">
                                    <span className="text-[10px] font-bold text-text-tertiary uppercase tracking-wider">
                                        Angle {dir.number}
                                    </span>
                                    <StatusChip tone={isSelected ? "info" : "neutral"} className="px-2 py-0.5 text-[9px] font-bold uppercase">
                                        {dir.tag}
                                    </StatusChip>
                                </div>

                                <h4 className="mt-4 text-base font-bold text-text-primary">
                                    {dir.title}
                                </h4>

                                <dl className="mt-4 space-y-3 text-xs leading-relaxed">
                                    <div className="flex gap-2">
                                        <dt className="shrink-0 text-text-tertiary font-medium">Who it's for:</dt>
                                        <dd className="text-text-secondary">{dir.buyer}</dd>
                                    </div>
                                    <div className="flex gap-2">
                                        <dt className="shrink-0 text-text-tertiary font-medium">Opening scene:</dt>
                                        <dd className="text-text-secondary italic">&ldquo;{dir.opening}&rdquo;</dd>
                                    </div>
                                    <div className="flex gap-2">
                                        <dt className="shrink-0 text-text-tertiary font-medium">Product demo:</dt>
                                        <dd className="text-text-secondary">{dir.demo}</dd>
                                    </div>
                                    <div className="flex gap-2">
                                        <dt className="shrink-0 text-text-tertiary font-medium">Result proof:</dt>
                                        <dd className="text-text-secondary">{dir.proof}</dd>
                                    </div>
                                    <div className="flex gap-2">
                                        <dt className="shrink-0 text-text-tertiary font-medium">Creator fit:</dt>
                                        <dd className="text-text-secondary font-medium">{dir.creatorStyle}</dd>
                                    </div>
                                </dl>
                            </div>

                            <div className="mt-6 pt-4 border-t border-divider">
                                <span className="inline-flex items-center gap-1 text-[10px] font-bold text-warn uppercase tracking-wider">
                                    <Sparkles className="h-3 w-3" />
                                    What this tests
                                </span>
                                <p className="mt-1.5 text-xs leading-relaxed text-text-secondary">
                                    {dir.tests}
                                </p>
                            </div>
                        </div>
                    );
                })}
            </div>

            <div className="mt-12 text-center">
                <Button asChild size="sm">
                    <Link to="/login">
                        Generate My Creative Directions
                        <ArrowRight className="ml-2 h-4 w-4" />
                    </Link>
                </Button>
                <p className="mt-3 text-xs text-text-tertiary italic">
                    Selected direction feeds automatically into the Creator Plan storyboard.
                </p>
            </div>
        </SectionWrapper>
    );
}
