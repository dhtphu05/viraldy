import { SectionWrapper } from "./section-wrapper";

export function TrustSection() {
    return (
        <SectionWrapper id="trust">
            <div className="mx-auto max-w-3xl text-center">
                <h2 className="text-2xl font-bold text-text-primary sm:text-3xl">
                    Useful intelligence without fake certainty.
                </h2>
                <p className="mt-4 text-sm leading-relaxed text-text-secondary">
                    Creative performance depends on more than a video. Price, product quality,
                    shipping, product page, creator fit, offer, distribution and market timing can
                    all affect the outcome.
                </p>
                <p className="mt-4 text-sm leading-relaxed text-text-secondary">
                    Viraldy separates what is directly observed, what is inferred, what is missing,
                    and what needs seller confirmation. And it does not present a structural
                    creative score as a guarantee of virality, sales or ROAS.
                </p>
            </div>
        </SectionWrapper>
    );
}
