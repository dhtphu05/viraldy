import { Link } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { SectionWrapper } from "./section-wrapper";

export function EarlyAccessCta() {
    return (
        <SectionWrapper id="cta" background="primary-soft">
            <div className="mx-auto max-w-2xl text-center">
                <h2 className="text-2xl font-bold text-text-primary sm:text-3xl">
                    Your next TikTok should not start from a blank prompt.
                </h2>
                <p className="mt-4 text-sm text-text-secondary">
                    Bring a product. Bring a reference. Or bring the video you are not sure whether
                    to approve.
                </p>
                <p className="mt-2 text-sm font-medium text-text-primary">
                    Viraldy helps you decide the next creative action.
                </p>

                <div className="mt-8 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
                    <Button asChild size="lg">
                        <Link to="/login">
                            Try Viraldy
                            <ArrowRight className="ml-1 h-4 w-4" />
                        </Link>
                    </Button>
                    <Button asChild variant="outline" size="lg">
                        <Link to="/login">
                            Review a TikTok
                            <ArrowRight className="ml-1 h-4 w-4" />
                        </Link>
                    </Button>
                </div>

                <p className="mt-6 text-xs text-text-tertiary">
                    Product in. Creative direction out. Video checked before you spend.
                </p>
            </div>
        </SectionWrapper>
    );
}
