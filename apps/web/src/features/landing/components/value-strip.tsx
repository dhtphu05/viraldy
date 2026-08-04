import { Check, Circle } from "lucide-react";
import { cn } from "@/shared/lib/utils";
import { SectionWrapper } from "./section-wrapper";

const steps = [
    { label: "Product", sub: "You bring it" },
    { label: "3 Creative Directions", sub: "Viraldy generates" },
    { label: "Creator Pack", sub: "Ready-to-film plan" },
    { label: "Video Review", sub: "Structural check" },
    { label: "Exact Fix Plan", sub: "Edit or reshoot" },
    { label: "Next Version", sub: "Verify the fix" },
];

export function ValueStrip() {
    return (
        <SectionWrapper id="how-it-works" background="surface">
            <div className="text-center">
                <h2 className="text-2xl font-bold text-text-primary sm:text-3xl">
                    From product to a better creative decision.
                </h2>

                <div className="mt-10 overflow-x-auto pb-2">
                    <ol className="mx-auto flex min-w-max max-w-[900px] snap-x snap-mandatory justify-center">
                        {steps.map((step, i) => (
                            <li
                                key={step.label}
                                className="relative flex min-w-32 snap-start flex-col items-center px-3"
                            >
                                {i < steps.length - 1 && (
                                    <span
                                        aria-hidden
                                        className="absolute left-[calc(50%+2rem)] right-0 top-7 h-px bg-gradient-to-r from-primary/30 to-divider"
                                    />
                                )}
                                <span
                                    className={cn(
                                        "relative z-10 grid h-14 w-14 place-items-center rounded-full text-lg font-bold",
                                        i === 0
                                            ? "bg-primary text-primary-foreground shadow-lg shadow-primary/20"
                                            : "bg-surface-muted text-text-tertiary",
                                    )}
                                >
                                    {i + 1}
                                </span>
                                <p className="mt-3 max-w-[120px] text-xs font-semibold leading-tight text-text-primary">
                                    {step.label}
                                </p>
                                <p className="mt-1 text-[10px] text-text-tertiary">{step.sub}</p>
                            </li>
                        ))}
                    </ol>
                </div>

                <p className="mt-8 text-sm text-text-secondary">
                    You bring the product. Viraldy helps you decide what to make and what to fix.
                </p>
            </div>
        </SectionWrapper>
    );
}
