import { SectionWrapper } from "./section-wrapper";
import { Package, ShieldCheck, FileText, AlertTriangle, Ship, Compass } from "lucide-react";
import { StatusChip } from "@/shared/ui/status-chip";

export function StoryIntro() {
    return (
        <SectionWrapper id="story-intro" background="surface" className="py-20 border-b border-hairline">
            <div className="mx-auto max-w-4xl text-center mb-12">
                <span className="rounded-full bg-primary-soft px-3 py-1.5 text-xs font-semibold text-primary">
                    See Viraldy in Action
                </span>
                <h2 className="mt-4 text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
                    One product. From inspiration to a better final video.
                </h2>
                <p className="mt-4 text-lg text-text-secondary leading-relaxed">
                    Follow one product through Viraldy and see exactly what goes in, what Viraldy understands, and what comes out.
                </p>
            </div>

            {/* Rich Product Context Card */}
            <div className="mx-auto max-w-4xl rounded-3xl border border-hairline bg-surface p-6 sm:p-8 shadow-floating-card">
                <div className="flex flex-wrap items-center justify-between border-b border-divider pb-4 mb-6">
                    <div className="flex items-center gap-3">
                        <span className="grid h-10 w-10 place-items-center rounded-xl bg-primary-soft text-primary">
                            <Package className="h-5 w-5" />
                        </span>
                        <div>
                            <h3 className="text-base font-bold text-text-primary">SwiftPress Mini Garment Steamer</h3>
                            <p className="text-xs text-text-tertiary">Product Intelligence Report</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <StatusChip tone="ok" className="text-[10px] font-bold">US Market</StatusChip>
                        <StatusChip tone="info" className="text-[10px] font-bold">Active</StatusChip>
                    </div>
                </div>

                <div className="grid gap-6 md:grid-cols-12">
                    {/* General Specs */}
                    <div className="md:col-span-4 space-y-4">
                        <h4 className="text-xs font-bold text-text-primary uppercase tracking-wider flex items-center gap-1.5 border-b border-divider pb-2">
                            <FileText className="h-3.5 w-3.5 text-text-secondary" />
                            General Specs
                        </h4>
                        <dl className="space-y-3 text-xs leading-relaxed">
                            <div>
                                <dt className="font-bold text-text-tertiary">Category</dt>
                                <dd className="text-text-primary font-medium">Home / travel apparel care</dd>
                            </div>
                            <div>
                                <dt className="font-bold text-text-tertiary">Offer Details</dt>
                                <dd className="text-text-primary font-medium">15% launch discount</dd>
                            </div>
                            <div>
                                <dt className="font-bold text-text-tertiary">Pricing Structure</dt>
                                <dd className="text-text-primary font-medium">Retail: $29.99 | COGS: $8.40</dd>
                            </div>
                            <div>
                                <dt className="font-bold text-text-tertiary flex items-center gap-1">
                                    <Ship className="h-3 w-3" />
                                    Authorized Shipping
                                </dt>
                                <dd className="text-text-primary font-medium">4–6 business days</dd>
                            </div>
                        </dl>
                    </div>

                    {/* Target Audience & Pain */}
                    <div className="md:col-span-4 space-y-4">
                        <h4 className="text-xs font-bold text-text-primary uppercase tracking-wider flex items-center gap-1.5 border-b border-divider pb-2">
                            <Compass className="h-3.5 w-3.5 text-text-secondary" />
                            Target &amp; Pain
                        </h4>
                        <dl className="space-y-3 text-xs leading-relaxed">
                            <div>
                                <dt className="font-bold text-text-tertiary">Primary Buyers</dt>
                                <dd className="text-text-primary font-medium">US college students, Frequent travelers</dd>
                            </div>
                            <div>
                                <dt className="font-bold text-text-tertiary">Primary Pain</dt>
                                <dd className="text-text-secondary leading-normal">
                                    Wrinkled clothing when there is no room or time for a full-size iron.
                                </dd>
                            </div>
                            <div>
                                <dt className="font-bold text-text-tertiary">Desired Outcome</dt>
                                <dd className="text-text-secondary leading-normal">
                                    Presentable clothing with a compact tool.
                                </dd>
                            </div>
                        </dl>
                    </div>

                    {/* Observable Mechanism & Proof */}
                    <div className="md:col-span-4 space-y-4">
                        <h4 className="text-xs font-bold text-text-primary uppercase tracking-wider flex items-center gap-1.5 border-b border-divider pb-2">
                            <ShieldCheck className="h-3.5 w-3.5 text-text-secondary" />
                            Mechanism &amp; Proof
                        </h4>
                        <dl className="space-y-3 text-xs leading-relaxed">
                            <div>
                                <dt className="font-bold text-text-tertiary">Observable Mechanism</dt>
                                <dd className="text-text-primary font-medium">Steam is applied directly to wrinkled fabric.</dd>
                            </div>
                            <div>
                                <dt className="font-bold text-text-tertiary">Observable Proof</dt>
                                <dd className="text-text-primary font-medium">Same fabric area before and after use.</dd>
                            </div>
                            <div>
                                <dt className="font-bold text-text-tertiary">Recommended Proof Method</dt>
                                <dd className="text-text-secondary">Same-fabric before/after, Close-up wrinkle change</dd>
                            </div>
                            <div>
                                <dt className="font-bold text-text-tertiary font-semibold text-warn">Required Disclosure</dt>
                                <dd className="text-text-primary italic">"Results vary by fabric type."</dd>
                            </div>
                        </dl>
                    </div>
                </div>

                {/* Claim Governance & Boundaries */}
                <div className="mt-6 pt-6 border-t border-divider grid gap-6 md:grid-cols-2 text-xs">
                    <div className="p-4 rounded-2xl bg-ok-soft border border-ok/20">
                        <span className="font-bold text-ok tracking-wider uppercase block mb-2 text-[10px]">Allowed Claims</span>
                        <ul className="list-disc pl-4 space-y-1.5 text-text-secondary leading-relaxed">
                            <li>Helps reduce visible wrinkles.</li>
                            <li>Compact for quick touch-ups.</li>
                            <li><strong className="text-ok">Qualified:</strong> Quick wrinkle reduction only when actual result is shown and instant language is avoided.</li>
                        </ul>
                    </div>

                    <div className="p-4 rounded-2xl bg-destructive-soft border border-destructive/20">
                        <span className="font-bold text-destructive tracking-wider uppercase block mb-2 text-[10px]">Prohibited Claims (Do Not Claim)</span>
                        <ul className="list-disc pl-4 space-y-1.5 text-text-secondary leading-relaxed">
                            <li>Removes every wrinkle instantly.</li>
                            <li>Professional dry-cleaning results.</li>
                            <li>Kills bacteria / Sanitization.</li>
                            <li>Safe for every fabric.</li>
                        </ul>
                    </div>
                </div>

                {/* Caveat strip */}
                <div className="mt-4 flex gap-2 items-start p-3 bg-surface-soft rounded-xl border border-divider text-[11px] leading-relaxed text-text-secondary">
                    <AlertTriangle className="h-4 w-4 text-warn shrink-0 mt-0.5" />
                    <div>
                        <strong>Known Missing Fact:</strong> Verified supported-fabric list. Do NOT turn this missing information into a product claim.
                    </div>
                </div>
            </div>
        </SectionWrapper>
    );
}
