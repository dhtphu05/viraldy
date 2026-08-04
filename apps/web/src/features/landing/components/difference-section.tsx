import { SectionWrapper } from "./section-wrapper";

export function DifferenceSection() {
    return (
        <SectionWrapper id="difference" background="surface">
            <div className="mx-auto max-w-3xl text-center">
                <h2 className="text-2xl font-bold text-text-primary sm:text-3xl">
                    Creative-first on the surface.
                </h2>
                <h3 className="mt-2 text-xl font-semibold text-text-secondary">
                    Product-aware underneath.
                </h3>
                <p className="mt-6 text-sm leading-relaxed text-text-secondary">
                    Viraldy does not analyze every video as if every product were the same. A
                    personalized POD gift is different from a kitchen gadget. A beauty demo is
                    different from an apparel testimonial. A travel product needs different proof
                    from a decorative product. Viraldy is designed around product context so the
                    creative direction and review can become more specific.
                </p>
            </div>
        </SectionWrapper>
    );
}
