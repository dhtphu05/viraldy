import { SectionWrapper } from "./section-wrapper";

export function PhilosophySection() {
    return (
        <SectionWrapper id="philosophy" background="surface">
            <div className="mx-auto max-w-3xl text-center">
                <h2 className="text-2xl font-bold text-text-primary sm:text-3xl">
                    More content is not the goal.
                </h2>
                <h3 className="mt-2 text-xl font-semibold text-text-secondary">
                    Better creative decisions are.
                </h3>
                <p className="mt-6 text-sm leading-relaxed text-text-secondary">
                    Viraldy does not promise that a video will go viral. Viraldy does not guarantee
                    GMV. Viraldy helps you make the creative workflow less subjective by connecting
                    product context, creative evidence, production requirements, video execution,
                    seller decisions, and &mdash; over time &mdash; performance outcomes. So every
                    creative test can become more useful than the last.
                </p>
            </div>
        </SectionWrapper>
    );
}
