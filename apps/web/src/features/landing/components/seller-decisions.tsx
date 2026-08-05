import { Shield, Compass, DollarSign, Award } from "lucide-react";
import { StatusChip } from "@/shared/ui/status-chip";
import { SectionWrapper } from "./section-wrapper";

export function SellerDecisions() {
    const decisions = [
        {
            title: "Product Readiness",
            question: "Is this product worth testing creatively?",
            description: "Audits your product information, landing page claims, variants, and shipping conditions before creator outreach starts.",
            status: "Available" as const,
            tone: "ok" as const,
            icon: Award,
        },
        {
            title: "Creator Fit Mapping",
            question: "Who is actually a good fit for this product?",
            description: "Connects your product context to the right creator persona constraints, ensuring you outreach to creators who match the required demographic.",
            status: "Beta" as const,
            tone: "info" as const,
            icon: Compass,
        },
        {
            title: "Sample ROI Tracking",
            question: "Who is worth sending a physical sample to?",
            description: "Calculates GMV per sample and identifies creator efficiency trends to guide sample budget allocation.",
            status: "Beta" as const,
            tone: "info" as const,
            icon: DollarSign,
        },
        {
            title: "Rights & Spark Ads",
            question: "Can we safely scale this video with paid budget?",
            description: "Tracks paid-usage requirements, commercial audio notes, and Spark Ad handoff status without promising that every approval risk is eliminated.",
            status: "Coming Soon" as const,
            tone: "warn" as const,
            icon: Shield,
        },
    ];

    return (
        <SectionWrapper id="seller-decisions" background="default" className="py-20">
            <div className="mx-auto max-w-3xl text-center">
                <span className="rounded-full bg-info-soft px-3 py-1.5 text-xs font-semibold text-info">
                    Smarter Operations
                </span>
                <h2 className="mt-4 text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
                    Built around the decisions that cost sellers money.
                </h2>
                <p className="mt-4 text-lg text-text-secondary leading-relaxed">
                    Viraldy extends beyond basic video checking. We help creator-commerce teams analyze their margins, compliance guidelines, and sample shipping risks.
                </p>
            </div>

            <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
                {decisions.map((card) => {
                    const CardIcon = card.icon;
                    return (
                        <div key={card.title} className="surface-card p-6 border border-hairline shadow-soft-card flex flex-col justify-between">
                            <div>
                                <div className="flex items-center justify-between">
                                    <span className="grid h-8 w-8 place-items-center rounded-lg bg-surface-soft text-text-secondary border border-divider">
                                        <CardIcon className="h-4.5 w-4.5" />
                                    </span>
                                    <StatusChip tone={card.tone} className="px-2 py-0.5 text-[10px] uppercase font-bold">
                                        {card.status}
                                    </StatusChip>
                                </div>
                                <h3 className="mt-4 text-xs font-bold uppercase tracking-wider text-text-tertiary">
                                    {card.title}
                                </h3>
                                <h4 className="mt-1 text-sm font-semibold text-text-primary leading-snug">
                                    &ldquo;{card.question}&rdquo;
                                </h4>
                                <p className="mt-3 text-xs leading-relaxed text-text-secondary">
                                    {card.description}
                                </p>
                            </div>
                        </div>
                    );
                })}
            </div>
        </SectionWrapper>
    );
}
