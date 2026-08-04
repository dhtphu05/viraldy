import { Link } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { SectionWrapper } from "./section-wrapper";

const podContext = ["Recipient", "Occasion", "Personalization", "Variant", "Gift angle", "Required product details", "Claims and fulfillment constraints"];

export function UseCasePod() {
    return (
        <SectionWrapper id="pod-sellers">
            <div className="grid gap-12 lg:grid-cols-2 lg:items-center">
                <div>
                    <p className="text-xs font-semibold uppercase text-primary">Use Case</p>
                    <h2 className="mt-2 text-2xl font-bold text-text-primary sm:text-3xl">
                        For POD &amp; personalization sellers
                    </h2>
                    <p className="mt-3 text-sm text-text-secondary">
                        A generic creative review can miss the things that matter most. Viraldy can
                        work with product context such as:
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2">
                        {podContext.map((item) => (
                            <span
                                key={item}
                                className="rounded-full border border-hairline bg-background px-3 py-1 text-xs text-text-secondary"
                            >
                                {item}
                            </span>
                        ))}
                    </div>
                    <p className="mt-4 text-sm text-text-secondary">
                        So a video can be reviewed for more than pacing and hooks. It can be
                        reviewed for whether it is showing the right product in the right way.
                    </p>
                    <Button asChild size="sm" className="mt-5">
                        <Link to="/login">
                            Create a POD Creative Plan
                            <ArrowRight className="ml-1 h-4 w-4" />
                        </Link>
                    </Button>
                </div>
            </div>
        </SectionWrapper>
    );
}
