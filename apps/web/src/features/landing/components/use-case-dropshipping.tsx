import { Link } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { SectionWrapper } from "./section-wrapper";

const dropContext = [
    "Visual demonstration",
    "Product mechanism",
    "Problem/solution fit",
    "Proof",
    "Buyer context",
    "Offer clarity",
    "Compatibility constraints",
    "Shipping and claim context",
];

export function UseCaseDropshipping() {
    return (
        <SectionWrapper id="dropshipping" background="surface">
            <div className="grid gap-12 lg:grid-cols-2 lg:items-center">
                <div>
                    <p className="text-xs font-semibold uppercase text-primary">Use Case</p>
                    <h2 className="mt-2 text-2xl font-bold text-text-primary sm:text-3xl">
                        For dropshipping operators
                    </h2>
                    <p className="mt-3 text-sm text-text-secondary">
                        A product can look interesting and still be difficult to sell with creative.
                        Viraldy helps structure creatives around:
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2">
                        {dropContext.map((item) => (
                            <span
                                key={item}
                                className="rounded-full border border-hairline bg-background px-3 py-1 text-xs text-text-secondary"
                            >
                                {item}
                            </span>
                        ))}
                    </div>
                    <p className="mt-4 text-sm text-text-secondary">
                        Use winning references as inspiration without turning every product into the
                        same copied TikTok.
                    </p>
                    <Button asChild size="sm" className="mt-5">
                        <Link to="/login">
                            Generate Product Directions
                            <ArrowRight className="ml-1 h-4 w-4" />
                        </Link>
                    </Button>
                </div>
            </div>
        </SectionWrapper>
    );
}
