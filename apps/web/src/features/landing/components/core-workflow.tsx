import { ArrowDown, CornerDownRight, Check, Sparkles, HelpCircle } from "lucide-react";
import { StatusChip } from "@/shared/ui/status-chip";
import { SectionWrapper } from "./section-wrapper";

export function CoreWorkflow() {
    const steps = [
        {
            num: "01",
            phase: "1. Research & Angles",
            userActionLabel: "YOU BRING",
            userActionVal: "Product URL or winning competitor video link",
            viraldyLabel: "VIRALDY DOES",
            viraldyVal: "Analyzes product context and breaks down reference video structure",
            resultLabel: "YOU GET",
            resultVal: "3 Creative Directions (test hypotheses & hook options)",
            highlight: true,
        },
        {
            num: "02",
            phase: "2. Creator Briefing",
            userActionLabel: "YOU CHOOSE",
            userActionVal: "One creative direction (e.g. 'Late-for-Class Rescue')",
            viraldyLabel: "VIRALDY DOES",
            viraldyVal: "Converts concept into technical script, scene, and compliance requirements",
            resultLabel: "YOU GET",
            resultVal: "Creator Plan (production storyboard ready to copy/send)",
            highlight: false,
        },
        {
            num: "03",
            phase: "3. Creative Checking",
            userActionLabel: "CREATOR SENDS",
            userActionVal: "First video draft",
            viraldyLabel: "VIRALDY DOES",
            viraldyVal: "Checks video timeline (OCR/ASR) against constraints and expected times",
            resultLabel: "YOU GET",
            resultVal: "TikTok Score & Fix plan (clear edit vs reshoot directions)",
            highlight: false,
        },
        {
            num: "04",
            phase: "4. Verification",
            userActionLabel: "NEW DRAFT UPLOADED",
            userActionVal: "Revised video draft from editor or creator",
            viraldyLabel: "VIRALDY DOES",
            viraldyVal: "Compares version 2 against version 1 resolving flagged blockers",
            resultLabel: "YOU GET",
            resultVal: "Revision Compare checkmark list confirming compliance",
            highlight: false,
        },
        {
            num: "05",
            phase: "5. Feedback Loop",
            userActionLabel: "PERFORMANCE EXISTS",
            userActionVal: "TikTok Shop analytics and sales attribution data",
            viraldyLabel: "VIRALDY DOES",
            viraldyVal: "Connects conversion metrics back to specific hooks and creative decisions",
            resultLabel: "YOU GET",
            resultVal: "What to Test Next (recommendation for the next design iteration) [ROADMAP]",
            highlight: false,
        },
    ];

    return (
        <SectionWrapper id="how-it-works" background="default" className="py-20 border-b border-hairline">
            <div className="mx-auto max-w-3xl text-center">
                <span className="rounded-full bg-primary-soft px-3 py-1.5 text-xs font-semibold text-primary">
                    The Connected Workflow
                </span>
                <h2 className="mt-4 text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
                    One product. One connected creative workflow.
                </h2>
                <p className="mt-4 text-lg text-text-secondary">
                    Viraldy is the decision layer between your creative ideas, creator briefs, video review, and campaign execution.
                </p>
            </div>

            {/* Steps Workflow List */}
            <div className="mt-16 max-w-4xl mx-auto space-y-6">
                {steps.map((step, idx) => (
                    <div
                        key={step.num}
                        className={`relative rounded-2xl border p-6 transition-all duration-300 ${
                            step.highlight
                                ? "bg-surface border-primary/30 shadow-md"
                                : "bg-surface border-hairline shadow-sm hover:border-divider"
                        }`}
                    >
                        {/* Step Number & Heading */}
                        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-divider pb-3">
                            <div className="flex items-center gap-3">
                                <span className="text-xs font-bold text-text-tertiary uppercase tracking-wider">
                                    Step {step.num}
                                </span>
                                <h3 className="text-sm font-bold text-text-primary uppercase tracking-wide">
                                    {step.phase}
                                </h3>
                            </div>
                            {step.highlight && (
                                <StatusChip tone="info" className="text-[10px] font-bold">
                                    Case Study Path
                                </StatusChip>
                            )}
                        </div>

                        {/* Workflow Grid */}
                        <div className="mt-4 grid gap-4 sm:grid-cols-3 text-xs leading-relaxed">
                            {/* Input Column */}
                            <div className="p-3 rounded-xl bg-surface-soft border border-divider">
                                <span className="font-bold text-text-tertiary tracking-wide block mb-1">
                                    {step.userActionLabel}
                                </span>
                                <p className="text-text-primary font-medium">{step.userActionVal}</p>
                            </div>

                            {/* Action Column */}
                            <div className="p-3 rounded-xl bg-primary-softer/30 border border-primary/10 flex flex-col justify-center">
                                <span className="font-bold text-primary tracking-wide block mb-1">
                                    {step.viraldyLabel}
                                </span>
                                <p className="text-text-secondary">{step.viraldyVal}</p>
                            </div>

                            {/* Output Column */}
                            <div className="p-3 rounded-xl bg-surface-soft border border-divider">
                                <span className="font-bold text-ok tracking-wide block mb-1">
                                    {step.resultLabel}
                                </span>
                                <p className="text-text-primary font-semibold">{step.resultVal}</p>
                            </div>
                        </div>

                        {/* Arrow connector */}
                        {idx < steps.length - 1 && (
                            <div className="absolute left-1/2 -bottom-4 z-10 -translate-x-1/2 rounded-full border border-divider bg-surface p-1 shadow-sm hidden sm:block">
                                <ArrowDown className="h-3 w-3 text-text-tertiary" />
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </SectionWrapper>
    );
}
