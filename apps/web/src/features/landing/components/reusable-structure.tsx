import { SectionWrapper } from "./section-wrapper";
import { GitCommit, Sparkles } from "lucide-react";
import { ConfidenceBadge } from "@/shared/ui/confidence-badge";

export function ReusableStructure() {
    const beats = [
        {
            num: "Beat 1",
            title: "Problem Hook",
            start: "0–0.3s",
            duration: "0.9–1.8s",
            purpose: "Make the buyer recognize a time-sensitive or socially uncomfortable problem.",
            confidence: "high",
        },
        {
            num: "Beat 2",
            title: "Product Reveal",
            start: "0.9–2.2s",
            duration: "—",
            purpose: "Connect the product directly to the problem before attention decays.",
            confidence: "high",
        },
        {
            num: "Beat 3",
            title: "In-Use Demo",
            start: "2.0–4.5s",
            duration: "—",
            purpose: "Show the mechanism on the actual problem object.",
            confidence: "high",
        },
        {
            num: "Beat 4",
            title: "Observable Proof",
            start: "7–13s",
            duration: "—",
            purpose: "Return to the same item or area and show an observable result.",
            confidence: "medium",
        },
        {
            num: "Beat 5",
            title: "Commerce CTA",
            start: "15–22s",
            duration: "—",
            purpose: "Make the next commerce action explicit without replacing proof with sales language.",
            confidence: "medium",
        },
    ];

    return (
        <SectionWrapper id="reusable-structure" background="default" className="py-20 border-b border-hairline">
            <div className="mx-auto max-w-4xl text-center mb-12">
                <span className="rounded-full bg-primary-soft px-3 py-1.5 text-xs font-semibold text-primary">
                    Pattern Abstraction
                </span>
                <h2 className="mt-4 text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
                    Viraldy separates the pattern from the script.
                </h2>
                <p className="mt-4 text-lg text-text-secondary leading-relaxed">
                    By extracting structural timing bounds from reference videos, you get a reusable blueprint to briefing creators instead of copying competitor words verbatim.
                </p>
            </div>

            {/* Pattern Card Header */}
            <div className="mx-auto max-w-4xl rounded-2xl bg-surface border border-hairline p-5 shadow-sm mb-8">
                <div className="flex flex-wrap items-center justify-between gap-4">
                    <div>
                        <span className="text-[10px] font-bold text-text-tertiary uppercase block">Pattern Name</span>
                        <h3 className="text-base font-bold text-text-primary mt-0.5 flex items-center gap-1.5">
                            <GitCommit className="h-4.5 w-4.5 text-primary shrink-0" />
                            Deadline Pressure &rarr; Fast Product Reveal &rarr; Same-Fabric Proof
                        </h3>
                    </div>
                    <div className="flex gap-4 text-xs text-text-secondary">
                        <div>
                            <strong>Source Evidence:</strong> 2 reference assets
                        </div>
                        <div>
                            <strong>Status:</strong> No linked performance data
                        </div>
                    </div>
                </div>
            </div>

            {/* Reusable Sequence Grid */}
            <div className="mx-auto max-w-4xl grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
                {beats.map((beat) => (
                    <div key={beat.num} className="surface-card p-4 border border-divider shadow-sm flex flex-col justify-between hover:border-primary/20 transition-all duration-300">
                        <div>
                            <div className="flex justify-between items-center">
                                <span className="text-[10px] font-bold text-primary uppercase">{beat.num}</span>
                                <ConfidenceBadge level={beat.confidence} />
                            </div>
                            <h4 className="mt-2 text-xs font-bold text-text-primary uppercase tracking-wide">
                                {beat.title}
                            </h4>
                            <p className="mt-2 text-[11px] leading-relaxed text-text-secondary">
                                {beat.purpose}
                            </p>
                        </div>
                        <div className="mt-4 pt-3 border-t border-divider text-[10px] text-text-tertiary font-medium">
                            <div>Start: {beat.start}</div>
                            {beat.duration !== "—" && <div>Duration: {beat.duration}</div>}
                        </div>
                    </div>
                ))}
            </div>
        </SectionWrapper>
    );
}
