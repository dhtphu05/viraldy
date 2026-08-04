import { SectionWrapper } from "./section-wrapper";
import { CheckCircle2, RefreshCw, XCircle } from "lucide-react";

export function KeepChangeAvoid() {
    const keepItems = [
        "Visible problem in the opening",
        "Early product reveal",
        "Same-shirt demonstration",
        "Same-item result continuity",
        "Proof before CTA",
        "Low-pressure product-tag CTA",
    ];

    const changeItems = [
        "Reference creator context → US college student / traveler",
        "Reference script → new product-specific wording",
        "Reference product → SwiftPress product assets",
        "Offer → verified 15% launch discount",
        "Disclosure → Results vary by fabric type.",
    ];

    const avoidItems = [
        "Copying competitor wording",
        "\"Instantly removes every wrinkle\"",
        "Fake countdown / scarcity",
        "Different shirt for result shot",
        "Sanitization claims",
    ];

    return (
        <SectionWrapper id="keep-change-avoid" background="surface" className="py-20 border-b border-hairline">
            <div className="mx-auto max-w-4xl text-center mb-12">
                <span className="rounded-full bg-primary-soft px-3 py-1.5 text-xs font-semibold text-primary">
                    Strategic Separation
                </span>
                <h2 className="mt-4 text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
                    What to preserve, localise, or block.
                </h2>
                <p className="mt-4 text-lg text-text-secondary leading-relaxed">
                    Viraldy highlights precisely which parameters should be carried over from the reference, what must adapt to your product data, and what claims violate safety rules.
                </p>
            </div>

            <div className="mx-auto max-w-4xl grid gap-6 md:grid-cols-3">
                {/* Keep */}
                <div className="p-5 rounded-2xl border border-divider bg-surface shadow-sm">
                    <h3 className="text-sm font-bold text-ok flex items-center gap-2 border-b border-divider pb-3 mb-4 uppercase tracking-wide">
                        <CheckCircle2 className="h-4.5 w-4.5" />
                        KEEP (Preserve)
                    </h3>
                    <ul className="space-y-3 text-xs text-text-secondary">
                        {keepItems.map((item) => (
                            <li key={item} className="flex items-start gap-2">
                                <span className="h-1.5 w-1.5 rounded-full bg-ok mt-1.5 shrink-0" />
                                <span>{item}</span>
                            </li>
                        ))}
                    </ul>
                </div>

                {/* Change */}
                <div className="p-5 rounded-2xl border border-divider bg-surface shadow-sm">
                    <h3 className="text-sm font-bold text-info flex items-center gap-2 border-b border-divider pb-3 mb-4 uppercase tracking-wide">
                        <RefreshCw className="h-4.5 w-4.5" />
                        CHANGE (Localize)
                    </h3>
                    <ul className="space-y-3 text-xs text-text-secondary">
                        {changeItems.map((item) => (
                            <li key={item} className="flex items-start gap-2">
                                <span className="h-1.5 w-1.5 rounded-full bg-info mt-1.5 shrink-0" />
                                <span>{item}</span>
                            </li>
                        ))}
                    </ul>
                </div>

                {/* Avoid */}
                <div className="p-5 rounded-2xl border border-divider bg-surface shadow-sm">
                    <h3 className="text-sm font-bold text-destructive flex items-center gap-2 border-b border-divider pb-3 mb-4 uppercase tracking-wide">
                        <XCircle className="h-4.5 w-4.5" />
                        AVOID (Block)
                    </h3>
                    <ul className="space-y-3 text-xs text-text-secondary">
                        {avoidItems.map((item) => (
                            <li key={item} className="flex items-start gap-2">
                                <span className="h-1.5 w-1.5 rounded-full bg-destructive mt-1.5 shrink-0" />
                                <span>{item}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            </div>

            <div className="mt-8 text-center text-sm font-semibold text-text-primary">
                You're not copying a TikTok. You're learning the structure behind it.
            </div>
        </SectionWrapper>
    );
}
