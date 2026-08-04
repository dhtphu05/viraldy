import { SectionWrapper } from "./section-wrapper";

const audiences = [
    "TikTok Shop sellers",
    "POD & personalization stores",
    "Dropshipping operators",
    "Creator-led ecommerce teams",
    "Creative and ecommerce agencies",
];

export function BuiltFor() {
    return (
        <SectionWrapper id="built-for" background="primary-soft">
            <div className="text-center">
                <h2 className="text-2xl font-bold text-text-primary sm:text-3xl">
                    Built for people selling through short-form creative.
                </h2>

                <div className="mt-8 flex flex-wrap justify-center gap-3">
                    {audiences.map((audience) => (
                        <span
                            key={audience}
                            className="rounded-full border border-primary/20 bg-surface px-4 py-2 text-sm font-medium text-text-primary"
                        >
                            {audience}
                        </span>
                    ))}
                </div>

                <p className="mt-8 mx-auto max-w-2xl text-sm leading-relaxed text-text-secondary">
                    If your growth depends on constantly finding, briefing, reviewing and testing new
                    creatives, Viraldy is built around that workflow.
                </p>
            </div>
        </SectionWrapper>
    );
}
