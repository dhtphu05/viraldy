import { SectionWrapper } from "./section-wrapper";

export function LearningLoop() {
    return (
        <SectionWrapper id="learning-loop">
            <div className="mx-auto max-w-3xl text-center">
                <h2 className="text-2xl font-bold text-text-primary sm:text-3xl">
                    The long-term goal: tell you what to test next.
                </h2>
                <p className="mt-4 text-sm leading-relaxed text-text-secondary">
                    The more creative decisions are connected to actual outcomes, the more useful
                    the next recommendation can become.
                </p>

                <div className="mt-6 rounded-xl bg-surface p-5 text-left">
                    <p className="text-xs font-semibold uppercase text-text-tertiary">
                        Instead of
                    </p>
                    <p className="mt-1 text-sm italic text-text-secondary">
                        &ldquo;Generate 10 more hooks.&rdquo;
                    </p>
                    <p className="mt-4 text-xs font-semibold uppercase text-primary">
                        Viraldy is designed toward
                    </p>
                    <p className="mt-1 text-sm text-text-secondary">
                        Your problem-first demos have consistently been stronger than generic
                        testimonials. Keep the current proof mechanism. Test a new buyer context
                        next. Avoid repeating the fatigued opening used in your last four creatives.
                    </p>
                </div>

                <p className="mt-6 text-sm font-medium text-text-primary">
                    Your creative history should become an advantage &mdash; not another spreadsheet.
                </p>
            </div>
        </SectionWrapper>
    );
}
