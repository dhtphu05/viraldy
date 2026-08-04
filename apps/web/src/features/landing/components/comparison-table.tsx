import { Check } from "lucide-react";
import { SectionWrapper } from "./section-wrapper";

const tools = [
    {
        name: "Ad Library",
        items: ["Find inspiration"],
        viraldy: false,
    },
    {
        name: "ChatGPT",
        items: ["Generate ideas"],
        viraldy: false,
    },
    {
        name: "Video Generator",
        items: ["Create an asset"],
        viraldy: false,
    },
    {
        name: "Viraldy",
        items: [
            "Understand the reference",
            "Adapt it to the product",
            "Choose a direction",
            "Create the production plan",
            "Review the execution",
            "Fix the draft",
            "Preserve the learning",
        ],
        viraldy: true,
    },
];

export function ComparisonTable() {
    return (
        <SectionWrapper id="comparison" background="surface">
            <div className="mx-auto max-w-3xl text-center">
                <h2 className="text-2xl font-bold text-text-primary sm:text-3xl">
                    Why not just use ChatGPT, an ad library and a video generator?
                </h2>
                <p className="mt-2 text-sm text-text-secondary">
                    Because each one solves one step. Viraldy connects the steps.
                </p>
            </div>

            <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {tools.map((tool) => (
                    <div
                        key={tool.name}
                        className={`surface-card p-5 ${tool.viraldy ? "border border-primary/20" : ""}`}
                    >
                        <p
                            className={`text-xs font-semibold uppercase ${tool.viraldy ? "text-primary" : "text-text-tertiary"}`}
                        >
                            {tool.name}
                        </p>
                        <ul className="mt-3 space-y-1.5">
                            {tool.items.map((item) => (
                                <li
                                    key={item}
                                    className="flex items-start gap-1.5 text-xs text-text-secondary"
                                >
                                    <Check
                                        className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${tool.viraldy ? "text-primary" : "text-text-tertiary"}`}
                                    />
                                    {item}
                                </li>
                            ))}
                        </ul>
                    </div>
                ))}
            </div>

            <p className="mt-8 text-center text-sm font-medium text-text-primary">
                Fewer disconnected creative decisions. More context carried from one step to the
                next.
            </p>
        </SectionWrapper>
    );
}
