import { SectionWrapper } from "./section-wrapper";
import { Check, AlertTriangle, AlertCircle } from "lucide-react";

export function PatternApplicability() {
    const worksWell = [
        "Portable garment care",
        "Lint removal",
        "Cleaning tools",
        "Home organization",
        "Visual-transformation gadgets",
    ];

    const requires = [
        "Visible problem",
        "Safe in-use demonstration",
        "Observable short-form result",
    ];

    const poorFit = [
        "Products without observable use",
        "Services",
        "Products requiring long-term outcomes",
    ];

    return (
        <SectionWrapper id="pattern-applicability" background="default" className="py-20 border-b border-hairline">
            <div className="mx-auto max-w-4xl text-center mb-12">
                <span className="rounded-full bg-primary-soft px-3 py-1.5 text-xs font-semibold text-primary">
                    Pattern Applicability
                </span>
                <h2 className="mt-4 text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
                    Know when a structure is appropriate.
                </h2>
                <p className="mt-4 text-lg text-text-secondary leading-relaxed">
                    Viraldy evaluates if a creative pattern matches your product type, catalog characteristics, and visual demonstration potential.
                </p>
            </div>

            <div className="mx-auto max-w-4xl grid gap-6 md:grid-cols-3 text-xs leading-relaxed">
                {/* Works Well For */}
                <div className="p-4 rounded-xl border border-divider bg-surface-soft">
                    <span className="font-bold text-ok uppercase tracking-wider flex items-center gap-1 mb-3 text-[10px]">
                        <Check className="h-4 w-4" />
                        Works Well For
                    </span>
                    <ul className="space-y-2 text-text-secondary">
                        {worksWell.map((item) => <li key={item}>{item}</li>)}
                    </ul>
                </div>

                {/* Requires */}
                <div className="p-4 rounded-xl border border-divider bg-surface-soft">
                    <span className="font-bold text-info uppercase tracking-wider flex items-center gap-1 mb-3 text-[10px]">
                        <AlertCircle className="h-4 w-4" />
                        Requires
                    </span>
                    <ul className="space-y-2 text-text-secondary">
                        {requires.map((item) => <li key={item}>{item}</li>)}
                    </ul>
                </div>

                {/* Poor Fit For */}
                <div className="p-4 rounded-xl border border-divider bg-surface-soft">
                    <span className="font-bold text-warn uppercase tracking-wider flex items-center gap-1 mb-3 text-[10px]">
                        <AlertTriangle className="h-4 w-4" />
                        Poor Fit For
                    </span>
                    <ul className="space-y-2 text-text-secondary">
                        {poorFit.map((item) => <li key={item}>{item}</li>)}
                    </ul>
                </div>
            </div>

            <div className="mt-8 text-center text-xs font-medium text-text-tertiary">
                A reusable structure is a hypothesis, not a guaranteed winning pattern.
            </div>
        </SectionWrapper>
    );
}
