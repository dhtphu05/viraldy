import { Check, X } from "lucide-react";
import { SectionWrapper } from "./section-wrapper";

interface ComparisonRow {
    feature: string;
    adLibrary: string;
    chatGpt: string;
    videoGen: string;
    viraldy: string;
}

const comparisonData: ComparisonRow[] = [
    {
        feature: "Find inspiration",
        adLibrary: "Primary use",
        chatGpt: "Partial",
        videoGen: "Not core",
        viraldy: "Yes",
    },
    {
        feature: "Understand creative structure",
        adLibrary: "Partial",
        chatGpt: "Prompt-dependent",
        videoGen: "Not core",
        viraldy: "Evidence-backed",
    },
    {
        feature: "Adapt to actual product",
        adLibrary: "Manual",
        chatGpt: "Prompt-dependent",
        videoGen: "Partial",
        viraldy: "Product-aware",
    },
    {
        feature: "Create production requirements",
        adLibrary: "No",
        chatGpt: "Prompt-dependent",
        videoGen: "Partial",
        viraldy: "Creator Plan",
    },
    {
        feature: "Review actual video execution",
        adLibrary: "No",
        chatGpt: "Manual / prompt-dependent",
        videoGen: "Not core",
        viraldy: "Yes",
    },
    {
        feature: "Separate edit vs reshoot",
        adLibrary: "No",
        chatGpt: "Prompt-dependent",
        videoGen: "No",
        viraldy: "Yes",
    },
    {
        feature: "Compare revisions",
        adLibrary: "No",
        chatGpt: "Manual",
        videoGen: "No",
        viraldy: "Yes",
    },
    {
        feature: "Keep product context connected",
        adLibrary: "No",
        chatGpt: "Manual context",
        videoGen: "Partial",
        viraldy: "Core workflow",
    },
];

export function WhyViraldy() {
    return (
        <SectionWrapper id="why-viraldy" background="surface" className="py-20 border-b border-hairline">
            <div className="mx-auto max-w-3xl text-center">
                <span className="rounded-full bg-primary-soft px-3 py-1.5 text-xs font-semibold text-primary">
                    Why Viraldy
                </span>
                <h2 className="mt-4 text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
                    More than another AI content tool.
                </h2>
                <p className="mt-4 text-lg text-text-secondary leading-relaxed">
                    The difference isn't more AI text. It's keeping product context, creative direction, production requirements, video evidence and revisions connected.
                </p>
            </div>

            {/* Matrix Table */}
            <div className="mt-12 overflow-x-auto rounded-3xl border border-divider shadow-sm bg-surface max-w-4xl mx-auto">
                <table className="w-full min-w-[700px] border-collapse text-left text-xs leading-normal">
                    <thead>
                        <tr className="border-b border-divider bg-surface-soft font-bold text-text-primary">
                            <th className="p-4">Workflow Parameter</th>
                            <th className="p-4">Ad Library</th>
                            <th className="p-4">Generic AI</th>
                            <th className="p-4">Video Generator</th>
                            <th className="p-4 text-primary bg-primary-softer/10">Viraldy</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-divider text-text-secondary font-medium">
                        {comparisonData.map((row) => (
                            <tr key={row.feature} className="hover:bg-surface-soft/50 transition-colors">
                                <td className="p-4 font-bold text-text-primary">{row.feature}</td>
                                <td className="p-4">{row.adLibrary}</td>
                                <td className="p-4">{row.chatGpt}</td>
                                <td className="p-4">{row.videoGen}</td>
                                <td className="p-4 font-bold text-primary bg-primary-softer/10">
                                    {row.viraldy}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            <div className="mt-8 text-center max-w-2xl mx-auto text-xs text-text-secondary font-medium">
                Viraldy isn't trying to replace every creative tool. It connects the decisions between them.
            </div>
        </SectionWrapper>
    );
}
