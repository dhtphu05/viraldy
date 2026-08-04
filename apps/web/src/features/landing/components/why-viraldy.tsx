import { Check, X } from "lucide-react";
import { SectionWrapper } from "./section-wrapper";

const chatGptItems = [
    "You describe the product",
    "You write the prompt",
    "You provide the context",
    "AI generates ideas",
    "You decide what is good",
    "You write the creator brief",
    "You review the video manually",
    "You figure out the feedback",
    "Learning stays in chats, spreadsheets and your head",
];

const viraldyItems = [
    "Product context stays connected",
    "Creative references become structured evidence",
    "Patterns are adapted to the product",
    "Three testable directions are generated",
    "The selected direction becomes a Creator Pack",
    "The actual video is checked against the plan",
    "Fixes become actionable revision instructions",
    "Revisions remain connected to the original creative decision",
];

export function WhyViraldy() {
    return (
        <SectionWrapper id="why-viraldy">
            <div className="text-center">
                <h2 className="text-2xl font-bold text-text-primary sm:text-3xl">
                    Not another AI script generator.
                </h2>
                <p className="mt-2 text-sm text-text-secondary">
                    ChatGPT can write a script. Viraldy is built around the decisions surrounding
                    that script.
                </p>
            </div>

            <div className="mt-10 grid gap-6 lg:grid-cols-2">
                <div className="surface-card p-6">
                    <p className="text-xs font-semibold uppercase text-text-tertiary">
                        ChatGPT / Generic AI
                    </p>
                    <ul className="mt-4 space-y-2">
                        {chatGptItems.map((item) => (
                            <li key={item} className="flex items-start gap-2 text-sm text-text-secondary">
                                <X className="mt-0.5 h-4 w-4 shrink-0 text-text-tertiary" />
                                {item}
                            </li>
                        ))}
                    </ul>
                </div>

                <div className="surface-card p-6 border border-primary/20">
                    <p className="text-xs font-semibold uppercase text-primary">Viraldy</p>
                    <ul className="mt-4 space-y-2">
                        {viraldyItems.map((item) => (
                            <li key={item} className="flex items-start gap-2 text-sm text-text-secondary">
                                <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                                {item}
                            </li>
                        ))}
                    </ul>
                </div>
            </div>

            <div className="mt-8 text-center">
                <p className="text-sm font-semibold text-text-primary">
                    The difference is not &ldquo;better text.&rdquo;
                </p>
                <p className="text-sm font-semibold text-text-primary">
                    The difference is a creative decision workflow.
                </p>
            </div>
        </SectionWrapper>
    );
}
