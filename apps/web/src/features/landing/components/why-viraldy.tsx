import { Check, X } from "lucide-react";
import { SectionWrapper } from "./section-wrapper";

interface ComparisonRow {
    feature: string;
    adLibrary: string;
    chatGpt: string;
    videoGen: string;
    viraldy: string;
    hasDetails?: boolean;
}

const comparisonData: ComparisonRow[] = [
    {
        feature: "Find visual references",
        adLibrary: "Primary use",
        chatGpt: "No",
        videoGen: "No",
        viraldy: "Paste any link",
    },
    {
        feature: "Understand creative pattern structure",
        adLibrary: "Manual guess",
        chatGpt: "Prompt-dependent",
        videoGen: "No",
        viraldy: "Automatic breakdown",
    },
    {
        feature: "Adapt pattern to product context",
        adLibrary: "No",
        chatGpt: "Partial (generic script)",
        videoGen: "No",
        viraldy: "Strict rule alignment",
    },
    {
        feature: "Create creator-ready production plan",
        adLibrary: "No",
        chatGpt: "Prompt-dependent",
        videoGen: "No",
        viraldy: "Full creator brief",
    },
    {
        feature: "Review actual video execution",
        adLibrary: "No",
        chatGpt: "ASR transcript only",
        videoGen: "No",
        viraldy: "OCR + ASR + visual checks",
    },
    {
        feature: "Give exact edit/reshoot actions",
        adLibrary: "No",
        chatGpt: "No",
        videoGen: "No",
        viraldy: "Grounded fix plan",
    },
    {
        feature: "Preserve historical revisions",
        adLibrary: "No",
        chatGpt: "No",
        videoGen: "No",
        viraldy: "Draft vs Revision Compare",
    },
    {
        feature: "Learn from test performance",
        adLibrary: "No",
        chatGpt: "No",
        videoGen: "No",
        viraldy: "What to Test Next Loop",
    },
];

export function WhyViraldy() {
    return (
        <SectionWrapper id="why-viraldy" background="default" className="py-20">
            <div className="mx-auto max-w-3xl text-center">
                <span className="rounded-full bg-primary-soft px-3 py-1.5 text-xs font-semibold text-primary">
                    The Difference
                </span>
                <h2 className="mt-4 text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
                    More than another AI copy generator.
                </h2>
                <p className="mt-4 text-lg text-text-secondary leading-relaxed">
                    Sellers don't need another generic AI script. They need a connected decision layer that links inspiration to creator briefing, compliance checking, and historical learning.
                </p>
            </div>

            {/* Matrix Table */}
            <div className="mt-12 overflow-x-auto rounded-2xl border border-hairline shadow-soft-card bg-surface">
                <table className="w-full min-w-[700px] border-collapse text-left text-sm">
                    <thead>
                        <tr className="border-b border-divider bg-surface-soft">
                            <th className="p-4 font-bold text-text-primary">Workflow Step</th>
                            <th className="p-4 font-semibold text-text-secondary">Ad Libraries</th>
                            <th className="p-4 font-semibold text-text-secondary">ChatGPT / Generic AI</th>
                            <th className="p-4 font-semibold text-text-secondary">Video Gen Tools</th>
                            <th className="p-4 font-bold text-primary">Viraldy</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-divider">
                        {comparisonData.map((row) => (
                            <tr key={row.feature} className="hover:bg-surface-soft/50 transition-colors">
                                <td className="p-4 font-medium text-text-primary">{row.feature}</td>
                                <td className="p-4 text-xs text-text-secondary">{row.adLibrary}</td>
                                <td className="p-4 text-xs text-text-secondary">{row.chatGpt}</td>
                                <td className="p-4 text-xs text-text-secondary">{row.videoGen}</td>
                                <td className="p-4 text-xs font-semibold text-primary bg-primary-softer/20">
                                    {row.viraldy}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            <div className="mt-8 text-center max-w-2xl mx-auto">
                <p className="text-sm font-semibold text-text-primary">
                    The difference isn't &ldquo;better text.&rdquo;
                </p>
                <p className="mt-2 text-sm text-text-secondary">
                    It is carrying your product context, brief specifications, and checker logic from one step to the next to eliminate guesswork.
                </p>
            </div>
        </SectionWrapper>
    );
}
