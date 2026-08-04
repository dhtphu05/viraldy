import { SectionWrapper } from "./section-wrapper";

const decisions = [
    "Which creative should I learn from?",
    "What part of it actually matters?",
    "How do I adapt it to my product without making a copy?",
    "What should I send to the creator?",
    "Did the creator actually follow the plan?",
    "Can I fix this draft with an edit, or do I need a reshoot?",
    "What should I test next?",
];

export function ProblemSection() {
    return (
        <SectionWrapper id="problem">
            <div className="mx-auto max-w-3xl">
                <h2 className="text-2xl font-bold text-text-primary sm:text-3xl">
                    Making more content is easy.
                </h2>
                <h3 className="mt-2 text-xl font-semibold text-text-secondary sm:text-2xl">
                    Knowing what content is worth making is harder.
                </h3>

                <p className="mt-6 text-sm leading-relaxed text-text-secondary">
                    You can already ask ChatGPT for 20 hooks. You can already generate videos with
                    AI. You can already save competitor ads.
                </p>

                <p className="mt-2 text-sm font-medium text-text-primary">But sellers still have to decide:</p>

                <ul className="mt-4 space-y-2">
                    {decisions.map((item) => (
                        <li key={item} className="flex items-start gap-2 text-sm text-text-secondary">
                            <span className="mt-0.5 shrink-0 text-primary">&mdash;</span>
                            {item}
                        </li>
                    ))}
                </ul>

                <p className="mt-6 text-sm font-medium text-text-primary">
                    Viraldy connects those decisions into one creative workflow.
                </p>
            </div>
        </SectionWrapper>
    );
}
