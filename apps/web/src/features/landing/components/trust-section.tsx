import { ShieldCheck, Info } from "lucide-react";
import { SectionWrapper } from "./section-wrapper";

export function TrustSection() {
    return (
        <SectionWrapper id="trust" background="default" className="py-20 border-b border-hairline">
            <div className="mx-auto max-w-3xl text-center">
                <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-primary-soft text-primary mb-6">
                    <ShieldCheck className="h-6 w-6" />
                </div>
                <h2 className="text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
                    Product Proof &mdash; No Fake Claims
                </h2>
                <p className="mt-4 text-lg leading-relaxed text-text-secondary">
                    Until real customer data is fully anonymized and ready to present, we refuse to inject fake customer names, made-up ROAS numbers, or simulated user testimonials. We believe in transparency.
                </p>

                <div className="mt-8 p-5 rounded-2xl bg-surface border border-hairline text-left flex gap-3 items-start shadow-sm">
                    <Info className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                    <div>
                        <h3 className="text-sm font-bold text-text-primary">
                            Golden Fixture Methodology
                        </h3>
                        <p className="mt-1 text-xs text-text-secondary leading-relaxed">
                            The SwiftPress Garment Steamer, Dog Mom Crewneck, and Bag Sealer examples shown on this page are <strong>actual product test fixtures</strong> built directly into the Viraldy domain codebase. They demonstrate the exact logic and rule verification the system runs in production.
                        </p>
                    </div>
                </div>

                <p className="mt-6 text-sm text-text-tertiary">
                    Viraldy separates what is directly observed, what is expected in a brief, and what needs human review. We provide useful intelligence, not magic bullet promises.
                </p>
            </div>
        </SectionWrapper>
    );
}
