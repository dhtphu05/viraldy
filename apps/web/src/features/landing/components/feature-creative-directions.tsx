import { Link } from "@tanstack/react-router";
import { ArrowRight, CheckCircle2, Users } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { StatusChip } from "@/shared/ui/status-chip";
import { SectionWrapper } from "./section-wrapper";

const directions = [
    {
        number: "01",
        title: "Late-for-Class Rescue",
        buyer: "College student",
        opening: "Wrinkled shirt before class",
        demo: "Steam the same section of the shirt",
        proof: "Treated vs untreated area",
        creatorStyle: "Student lifestyle UGC",
        tests: "Whether situational urgency is a stronger angle than generic convenience.",
        color: "primary",
    },
    {
        number: "02",
        title: "Carry-On Clothing Rescue",
        buyer: "Frequent traveler",
        opening: "Wrinkled shirt after unpacking",
        demo: "Compact travel use",
        proof: "Visible result on the same garment",
        tests: "Whether travel relevance creates stronger product intent.",
        color: "info",
    },
    {
        number: "03",
        title: "Small-Space Iron Alternative",
        buyer: "Apartment renter",
        opening: "Bulky ironing setup",
        demo: "Setup, use and storage",
        proof: "Space + product-result comparison",
        tests: "Whether compactness is a stronger purchase driver.",
        color: "ok",
    },
];

export function FeatureCreativeDirections() {
    return (
        <SectionWrapper id="creative-directions">
            <div className="text-center">
                <StatusChip tone="info" dot>Feature 2</StatusChip>
                <h2 className="mt-3 text-2xl font-bold text-text-primary sm:text-3xl">
                    Give us the product.
                </h2>
                <h3 className="mt-1 text-xl font-semibold text-text-secondary">
                    Get three creative directions worth considering.
                </h3>
                <p className="mt-3 mx-auto max-w-2xl text-sm text-text-secondary">
                    Viraldy combines your product context with relevant creative patterns and turns
                    them into three differentiated directions. Not ten random hooks. Not three
                    versions of the same script. Three different creative bets.
                </p>
            </div>

            <div className="mt-8 rounded-xl bg-surface-soft px-5 py-3">
                <p className="text-xs font-semibold uppercase text-text-tertiary">Example</p>
                <div className="mt-1 flex items-center gap-3">
                    <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-primary-soft text-primary">
                        <CheckCircle2 className="h-5 w-5" />
                    </span>
                    <span className="text-sm font-medium text-text-primary">
                        Product: Portable Garment Steamer
                    </span>
                </div>
            </div>

            <div className="mt-6 grid gap-6 md:grid-cols-3">
                {directions.map((dir, i) => (
                    <div key={dir.number} className="surface-card group p-5 transition-shadow duration-200 hover:shadow-hover-card">
                        <div className="flex items-center justify-between">
                            <span className="text-[10px] font-bold text-text-tertiary">
                                DIRECTION {dir.number}
                            </span>
                            <span className="rounded-full bg-primary-soft px-2 py-0.5 text-[10px] font-semibold text-primary">
                                {i === 0 ? "Best fit" : i === 1 ? "Alt angle" : "Contrast"}
                            </span>
                        </div>
                        <h4 className="mt-3 text-base font-semibold text-text-primary">
                            {dir.title}
                        </h4>
                        <dl className="mt-4 space-y-2.5 text-sm">
                            <div className="flex items-start gap-2">
                                <dt className="shrink-0 text-xs text-text-tertiary">Buyer</dt>
                                <dd className="flex items-center gap-1.5 text-text-secondary">
                                    <Users className="h-3 w-3 text-text-tertiary" />
                                    {dir.buyer}
                                </dd>
                            </div>
                            <div className="flex items-start gap-2">
                                <dt className="shrink-0 text-xs text-text-tertiary">Opening</dt>
                                <dd className="text-text-secondary">{dir.opening}</dd>
                            </div>
                            <div className="flex items-start gap-2">
                                <dt className="shrink-0 text-xs text-text-tertiary">Demo</dt>
                                <dd className="text-text-secondary">{dir.demo}</dd>
                            </div>
                            <div className="flex items-start gap-2">
                                <dt className="shrink-0 text-xs text-text-tertiary">Proof</dt>
                                <dd className="text-text-secondary">{dir.proof}</dd>
                            </div>
                        </dl>
                        {dir.creatorStyle && (
                            <StatusChip tone="neutral" className="mt-3">{dir.creatorStyle}</StatusChip>
                        )}
                        <div className="mt-3 border-t border-divider pt-3">
                            <StatusChip tone="warn" dot>What this tests</StatusChip>
                            <p className="mt-1.5 text-xs leading-relaxed text-text-secondary">
                                {dir.tests}
                            </p>
                        </div>
                    </div>
                ))}
            </div>

            <div className="mt-8 text-center">
                <Button asChild size="sm">
                    <Link to="/login">
                        Generate My Creative Directions
                        <ArrowRight className="ml-1 h-4 w-4" />
                    </Link>
                </Button>
                <p className="mt-3 text-xs text-text-tertiary italic">
                    &ldquo;One product. Three different reasons to buy.&rdquo;
                </p>
            </div>
        </SectionWrapper>
    );
}
