import { SectionWrapper } from "./section-wrapper";

const outputs = [
    { title: "Winning Pattern Breakdown", description: "See the structure behind a reference creative and what is transferable." },
    { title: "3 Creative Directions", description: "Three differentiated creative bets adapted to your product." },
    { title: "Creator Pack", description: "A production-ready brief your creator can film from." },
    { title: "TikTok Score &amp; Fix", description: "A clear decision plus exact edit and reshoot instructions." },
    { title: "Creator Draft Review", description: "Expected vs observed checks against your actual creative plan." },
    { title: "Revision Compare", description: "Verify whether the next draft fixed the blockers." },
    { title: "Next Creative", description: "As performance data is connected, Viraldy can turn past tests into the next creative recommendation." },
];

export function OutputSection() {
    return (
        <SectionWrapper id="output">
            <div className="text-center">
                <h2 className="text-2xl font-bold text-text-primary sm:text-3xl">
                    What do I actually get?
                </h2>
            </div>
            <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {outputs.map((output) => (
                    <div key={output.title} className="surface-card p-5">
                        <h3 className="text-sm font-semibold text-text-primary">{output.title}</h3>
                        <p className="mt-2 text-xs leading-relaxed text-text-secondary">
                            {output.description}
                        </p>
                    </div>
                ))}
            </div>
        </SectionWrapper>
    );
}
