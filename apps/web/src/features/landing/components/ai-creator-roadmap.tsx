import { Link } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { SectionWrapper } from "./section-wrapper";

export function AiCreatorRoadmap() {
    return (
        <SectionWrapper id="ai-creator" background="surface">
            <div className="mx-auto max-w-3xl">
                <p className="text-xs font-semibold uppercase text-primary">
                    Roadmap / Early Access
                </p>
                <h2 className="mt-2 text-2xl font-bold text-text-primary sm:text-3xl">
                    One creative plan. Human creator or AI creator.
                </h2>
                <p className="mt-3 text-sm text-text-secondary">
                    The same creative direction should be executable in more than one way.
                </p>

                <div className="mt-6 grid gap-4 sm:grid-cols-2">
                    <div className="surface-card p-5">
                        <p className="text-xs font-semibold text-text-tertiary">With a human creator</p>
                        <p className="mt-3 text-sm text-text-secondary">
                            Creative Direction &rarr; Creator Pack &rarr; UGC Draft
                        </p>
                    </div>
                    <div className="surface-card border border-primary/20 p-5">
                        <p className="text-xs font-semibold text-primary">With AI production</p>
                        <p className="mt-3 text-sm text-text-secondary">
                            Creative Direction &rarr; Scene Plan &rarr; AI Creator &rarr; AI Video
                            Draft
                        </p>
                    </div>
                </div>

                <p className="mt-4 text-sm text-text-secondary">
                    Both return to the same Viraldy quality layer: Video &rarr; Review &rarr; Fix
                    &rarr; Verify.
                </p>

                <p className="mt-4 text-sm font-medium text-text-primary">
                    AI Creator is part of Viraldy&rsquo;s production roadmap.
                </p>

                <Button asChild size="sm" className="mt-4">
                    <Link to="/login">
                        Join AI Creator Early Access
                        <ArrowRight className="ml-1 h-4 w-4" />
                    </Link>
                </Button>
            </div>
        </SectionWrapper>
    );
}
