import { Link } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { SectionWrapper } from "./section-wrapper";

export function EarlyAccessCta() {
    return (
        <SectionWrapper id="cta" background="default" className="py-20 text-center relative overflow-hidden bg-primary text-white">
            {/* Background Accent Gradient */}
            <div
                aria-hidden
                className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.15),transparent_60%)]"
            />
            
            <div className="relative mx-auto max-w-2xl z-10 space-y-6">
                <span className="rounded-full bg-white/20 px-3 py-1.5 text-xs font-semibold text-white uppercase tracking-wider">
                    Start with what you already have
                </span>
                <h2 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
                    Your next creative shouldn't start from a blank prompt.
                </h2>
                <p className="text-base text-white/90 leading-relaxed max-w-lg mx-auto">
                    Bring your product, a creative you want to learn from, or the video you're not sure whether to approve. Viraldy helps you decide what to make, what to fix, and what to test next.
                </p>

                {/* CTA Buttons */}
                <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
                    <div className="flex flex-col items-center w-full sm:w-auto">
                        <Button asChild size="lg" className="w-full sm:w-auto bg-white text-primary hover:bg-white/90 font-bold transition-all duration-300 hover:-translate-y-0.5">
                            <Link to="/login">
                                Plan My Next Creative
                                <ArrowRight className="ml-2 h-4 w-4 text-primary" />
                            </Link>
                        </Button>
                        <span className="mt-2 text-[10px] text-white/70">Start with a product</span>
                    </div>

                    <div className="flex flex-col items-center w-full sm:w-auto">
                        <Button asChild variant="outline" size="lg" className="w-full sm:w-auto border-white text-white hover:bg-white/10 font-bold transition-all duration-300 hover:-translate-y-0.5">
                            <Link to="/login">
                                Review My Video
                                <ArrowRight className="ml-2 h-4 w-4 text-white" />
                            </Link>
                        </Button>
                        <span className="mt-2 text-[10px] text-white/70">Get an exact fix plan</span>
                    </div>
                </div>

                <p className="mt-8 text-xs font-bold tracking-widest text-white/80 uppercase">
                    Product in. Creative direction out. Video checked before you spend.
                </p>
            </div>
        </SectionWrapper>
    );
}
