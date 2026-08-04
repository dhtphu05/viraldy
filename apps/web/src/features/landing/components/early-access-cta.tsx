import { Link } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { SectionWrapper } from "./section-wrapper";

export function EarlyAccessCta() {
    return (
        <SectionWrapper id="cta" background="primary-soft" className="py-20 text-center">
            <div className="mx-auto max-w-2xl">
                <h2 className="text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
                    Your next TikTok should not start from a blank prompt.
                </h2>
                <p className="mt-4 text-base text-text-secondary leading-relaxed">
                    Bring a product. Bring a winning reference. Or bring the creator draft you aren't sure whether to approve or reshoot.
                </p>
                <p className="mt-2 text-sm font-semibold text-text-primary">
                    Viraldy helps you decide the next creative action.
                </p>

                {/* CTA Buttons */}
                <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
                    <div className="flex flex-col items-center">
                        <Button asChild size="lg" className="w-full sm:w-auto bg-primary hover:bg-primary-hover font-semibold">
                            <Link to="/login">
                                Get Creative Directions
                                <ArrowRight className="ml-2 h-4 w-4" />
                            </Link>
                        </Button>
                        <span className="mt-2 text-[10px] text-text-tertiary">Start with a product</span>
                    </div>

                    <div className="flex flex-col items-center">
                        <Button asChild variant="outline" size="lg" className="w-full sm:w-auto font-semibold">
                            <Link to="/login">
                                Review a Video
                                <ArrowRight className="ml-2 h-4 w-4" />
                            </Link>
                        </Button>
                        <span className="mt-2 text-[10px] text-text-tertiary">Get an exact fix plan</span>
                    </div>
                </div>

                <p className="mt-8 text-xs font-semibold tracking-wider text-text-tertiary uppercase">
                    Product in. Creative direction out. Video checked before you spend.
                </p>
            </div>
        </SectionWrapper>
    );
}
