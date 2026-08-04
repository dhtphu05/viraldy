import { HelpCircle, BarChart3, TrendingUp, Sparkles } from "lucide-react";
import { StatusChip } from "@/shared/ui/status-chip";
import { SectionWrapper } from "./section-wrapper";

export function LearningLoop() {
    return (
        <SectionWrapper id="learning-loop" background="surface" className="py-20 border-b border-hairline">
            <div className="mx-auto max-w-4xl text-center mb-12">
                <span className="rounded-full bg-warn-soft px-3 py-1.5 text-xs font-semibold text-warn">
                    Chapter 4: The Performance Loop (Roadmap)
                </span>
                <h2 className="mt-4 text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
                    Every creative test should make the next one smarter.
                </h2>
                <p className="mt-4 text-lg text-text-secondary leading-relaxed">
                    Viraldy is designed to connect real-world ad performance and shop data back to your original creative options &mdash; turning creative history into a compounding data advantage instead of a scattered spreadsheet.
                </p>
            </div>

            <div className="grid gap-8 lg:grid-cols-12 lg:items-center">
                {/* Left: Copy details */}
                <div className="lg:col-span-5 space-y-4">
                    <div className="flex items-center gap-2">
                        <BarChart3 className="h-5 w-5 text-primary" />
                        <h3 className="text-xl font-bold text-text-primary">Attuned to conversion data</h3>
                    </div>
                    <p className="text-sm text-text-secondary leading-relaxed">
                        When attribution data exists, Viraldy links GMV, hook retention rates, and CTR back to the specific hooks, visual mechanics, and creators that you tested.
                    </p>
                    <div className="p-4 rounded-xl bg-surface border border-divider">
                        <span className="text-[10px] font-bold text-text-tertiary uppercase block">Next Test Target</span>
                        <p className="mt-1 text-xs text-text-secondary">
                            Identifies fatigued hooks and suggests exactly which component of the storyboard to iterate next.
                        </p>
                    </div>
                    <p className="text-[10px] text-text-tertiary leading-relaxed italic">
                        * Note: Performance loop integration is currently in beta. Viraldy operates on structural and execution analysis.
                    </p>
                </div>

                {/* Right: Simulated Performance UI Card */}
                <div className="lg:col-span-7 surface-card p-6 border border-hairline bg-surface shadow-md">
                    <div className="flex items-center justify-between border-b border-divider pb-4 mb-4">
                        <div className="flex items-center gap-1.5">
                            <TrendingUp className="h-4 w-4 text-ok" />
                            <span className="text-xs font-bold text-text-primary uppercase tracking-wider">
                                Performance Intelligence Loop
                            </span>
                        </div>
                        <StatusChip tone="warn" dot>BETA / ROADMAP</StatusChip>
                    </div>

                    <div className="space-y-4 text-xs">
                        {/* What seems to be working */}
                        <div className="p-3 rounded-lg bg-ok-soft/30 border border-ok/10">
                            <span className="text-[10px] font-bold text-ok uppercase tracking-wider block">What Seems to be Working</span>
                            <ul className="mt-1.5 list-disc pl-4 text-text-secondary space-y-0.5">
                                <li>Problem-first opening hooks (1.8× CTR vs median)</li>
                                <li>Same-shirt comparison proof (Higher conversion lift)</li>
                            </ul>
                        </div>

                        {/* What looks weak */}
                        <div className="p-3 rounded-lg bg-destructive-soft/30 border border-destructive/10">
                            <span className="text-[10px] font-bold text-destructive uppercase tracking-wider block">What Looks Weak</span>
                            <ul className="mt-1.5 list-disc pl-4 text-text-secondary space-y-0.5">
                                <li>Generic testimonial angles (Dropped retention at 3.0s)</li>
                            </ul>
                        </div>

                        {/* What to test next */}
                        <div className="p-3 rounded-lg bg-primary-softer border border-primary/20">
                            <span className="text-[10px] font-bold text-primary uppercase tracking-wider block">WHAT TO TEST NEXT</span>
                            <p className="mt-1 text-text-primary font-medium">
                                Keep the stronger demonstration structure and proof mechanism. Test it against another buyer context (e.g. Carry-On traveler angle instead of College student).
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            <div className="mt-8 text-center max-w-2xl mx-auto border-t border-divider pt-6">
                <p className="text-[10px] text-text-tertiary italic leading-relaxed">
                    Disclaimer: Based on available evidence. Viraldy does not guarantee virality, GMV, ROAS, or performance. Success depends on product-market fit, pricing, and distribution parameters.
                </p>
            </div>
        </SectionWrapper>
    );
}
