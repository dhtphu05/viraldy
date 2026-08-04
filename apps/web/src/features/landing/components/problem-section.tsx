import { SectionWrapper } from "./section-wrapper";
import { ArrowRightCircle, Sparkles } from "lucide-react";

export function ProblemSection() {
    return (
        <SectionWrapper id="problem" background="surface" className="py-20 border-b border-hairline">
            <div className="mx-auto max-w-4xl text-center mb-12">
                <span className="rounded-full bg-destructive-soft px-3 py-1.5 text-xs font-semibold text-destructive">
                    The Pain
                </span>
                <h2 className="mt-4 text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
                    Making more content isn't the hard part.
                    <br />
                    <span className="text-text-secondary">Knowing what's worth making is.</span>
                </h2>
                <p className="mt-6 mx-auto max-w-2xl text-base leading-relaxed text-text-secondary">
                    You can save competitor TikToks. You can ask AI for hooks. You can hire more creators. But somebody still has to decide what is worth making, what the creator should actually film, and whether the video that comes back is good enough to use.
                </p>
            </div>

            {/* Before vs With comparison panel */}
            <div className="mx-auto max-w-4xl grid gap-8 md:grid-cols-2">
                {/* Visual Left: Before Viraldy */}
                <div className="p-6 rounded-3xl border border-divider bg-surface-soft flex flex-col justify-between shadow-sm">
                    <div>
                        <span className="text-[10px] font-bold text-destructive uppercase tracking-wider block mb-4">
                            Before Viraldy
                        </span>
                        <div className="flex flex-col gap-2.5 text-xs text-text-secondary font-medium">
                            <div className="p-2.5 rounded-lg bg-surface border border-hairline">
                                TikTok Saves
                            </div>
                            <div className="flex justify-center text-text-tertiary">
                                <ArrowRightCircle className="h-4 w-4 rotate-90" />
                            </div>
                            <div className="p-2.5 rounded-lg bg-surface border border-hairline">
                                ChatGPT prompts
                            </div>
                            <div className="flex justify-center text-text-tertiary">
                                <ArrowRightCircle className="h-4 w-4 rotate-90" />
                            </div>
                            <div className="p-2.5 rounded-lg bg-surface border border-hairline">
                                Google Drive
                            </div>
                            <div className="flex justify-center text-text-tertiary">
                                <ArrowRightCircle className="h-4 w-4 rotate-90" />
                            </div>
                            <div className="p-2.5 rounded-lg bg-surface border border-hairline">
                                Creator chats
                            </div>
                            <div className="flex justify-center text-text-tertiary">
                                <ArrowRightCircle className="h-4 w-4 rotate-90" />
                            </div>
                            <div className="p-2.5 rounded-lg bg-surface border border-hairline">
                                Spreadsheets
                            </div>
                            <div className="flex justify-center text-text-tertiary">
                                <ArrowRightCircle className="h-4 w-4 rotate-90" />
                            </div>
                            <div className="p-2.5 rounded-lg bg-surface border border-hairline">
                                Manual feedback
                            </div>
                        </div>
                    </div>
                    <div className="mt-6 pt-3 border-t border-divider text-center text-[11px] text-destructive font-semibold">
                        Context gets lost between every step.
                    </div>
                </div>

                {/* Visual Right: With Viraldy */}
                <div className="p-6 rounded-3xl border border-primary/20 bg-primary-softer/20 flex flex-col justify-between shadow-md">
                    <div>
                        <span className="text-[10px] font-bold text-primary uppercase tracking-wider block mb-4 flex items-center gap-1">
                            <Sparkles className="h-3.5 w-3.5" />
                            With Viraldy
                        </span>
                        <div className="flex flex-col gap-2.5 text-xs text-text-primary font-semibold">
                            <div className="p-2.5 rounded-lg bg-surface border border-primary/20 shadow-sm">
                                Product
                            </div>
                            <div className="flex justify-center text-primary">
                                <ArrowRightCircle className="h-4 w-4 rotate-90" />
                            </div>
                            <div className="p-2.5 rounded-lg bg-surface border border-primary/20 shadow-sm">
                                Creative Pattern
                            </div>
                            <div className="flex justify-center text-primary">
                                <ArrowRightCircle className="h-4 w-4 rotate-90" />
                            </div>
                            <div className="p-2.5 rounded-lg bg-surface border border-primary/20 shadow-sm">
                                Creative Direction
                            </div>
                            <div className="flex justify-center text-primary">
                                <ArrowRightCircle className="h-4 w-4 rotate-90" />
                            </div>
                            <div className="p-2.5 rounded-lg bg-surface border border-primary/20 shadow-sm">
                                Creator Plan
                            </div>
                            <div className="flex justify-center text-primary">
                                <ArrowRightCircle className="h-4 w-4 rotate-90" />
                            </div>
                            <div className="p-2.5 rounded-lg bg-surface border border-primary/20 shadow-sm">
                                Draft Review &amp; Exact Fix
                            </div>
                            <div className="flex justify-center text-primary">
                                <ArrowRightCircle className="h-4 w-4 rotate-90" />
                            </div>
                            <div className="p-2.5 rounded-lg bg-surface border border-primary/20 shadow-sm">
                                Revision &amp; Next Test
                            </div>
                        </div>
                    </div>
                    <div className="mt-6 pt-3 border-t border-primary/10 text-center text-[11px] text-primary font-bold">
                        The product context stays connected.
                    </div>
                </div>
            </div>

            <div className="mt-12 text-center text-base font-bold text-text-primary">
                Viraldy turns disconnected creative work into one decision workflow.
            </div>
        </SectionWrapper>
    );
}
