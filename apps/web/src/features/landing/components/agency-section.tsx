import { Link } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { SectionWrapper } from "./section-wrapper";

export function AgencySection() {
    return (
        <SectionWrapper id="agencies">
            <div className="mx-auto max-w-3xl">
                <p className="text-xs font-semibold uppercase text-primary">For teams</p>
                <h2 className="mt-2 text-2xl font-bold text-text-primary sm:text-3xl">
                    Review more creative without turning every decision into another meeting.
                </h2>
                <p className="mt-3 text-sm text-text-secondary">
                    Viraldy gives agencies and ecommerce teams a shared language for creative
                    direction, creator briefs, video QA, revision requests, product-specific
                    requirements, and creative history.
                </p>

                <div className="mt-6 rounded-xl bg-surface-soft p-5">
                    <p className="text-xs uppercase text-text-tertiary">Instead of</p>
                    <p className="mt-1 text-sm italic text-text-secondary">
                        &ldquo;This one feels weak.&rdquo;
                    </p>
                    <p className="mt-4 text-xs uppercase text-primary">Your team can say</p>
                    <p className="mt-1 text-sm text-text-secondary">
                        &ldquo;Product reveal missed the required opening window, proof is
                        incomplete, but creator delivery should be preserved.&rdquo;
                    </p>
                </div>

                <p className="mt-6 text-sm text-text-secondary">
                    That makes creative review faster to communicate and easier to repeat across
                    clients.
                </p>

                <Button asChild size="sm" className="mt-5">
                    <Link to="/login">
                        Explore Viraldy for Teams
                        <ArrowRight className="ml-1 h-4 w-4" />
                    </Link>
                </Button>
            </div>
        </SectionWrapper>
    );
}
