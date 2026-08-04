import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { ShoppingBag, Users, Zap, ShieldAlert, CheckCircle2, UserCheck, AlertTriangle } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { SectionWrapper } from "./section-wrapper";
import { StatusChip } from "@/shared/ui/status-chip";

type UseCaseTab = "tiktok" | "pod" | "dropship" | "agency";

export function UseCases() {
    const [activeTab, setActiveTab] = useState<UseCaseTab>("tiktok");

    return (
        <SectionWrapper id="use-cases" background="default" className="py-20 border-b border-hairline">
            <div className="mx-auto max-w-4xl text-center mb-12">
                <span className="rounded-full bg-primary-soft px-3 py-1.5 text-xs font-semibold text-primary">
                    Use Cases
                </span>
                <h2 className="mt-4 text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
                    Same creative workflow. Different product risks.
                </h2>
                <p className="mt-4 text-lg text-text-secondary leading-relaxed">
                    Viraldy adapts its checker constraints to the business model, catalog type, and compliance needs of your brand.
                </p>
            </div>

            {/* Tab Navigation */}
            <div className="mx-auto max-w-4xl flex justify-center gap-2 border-b border-divider pb-4 mb-8 flex-wrap">
                <button
                    onClick={() => setActiveTab("tiktok")}
                    className={`px-4 py-2 text-xs font-bold border-b-2 transition-all ${
                        activeTab === "tiktok" ? "border-primary text-primary" : "border-transparent text-text-secondary hover:text-text-primary"
                    }`}
                >
                    TikTok Shop
                </button>
                <button
                    onClick={() => setActiveTab("pod")}
                    className={`px-4 py-2 text-xs font-bold border-b-2 transition-all ${
                        activeTab === "pod" ? "border-primary text-primary" : "border-transparent text-text-secondary hover:text-text-primary"
                    }`}
                >
                    POD &amp; Personalization
                </button>
                <button
                    onClick={() => setActiveTab("dropship")}
                    className={`px-4 py-2 text-xs font-bold border-b-2 transition-all ${
                        activeTab === "dropship" ? "border-primary text-primary" : "border-transparent text-text-secondary hover:text-text-primary"
                    }`}
                >
                    Dropshipping
                </button>
                <button
                    onClick={() => setActiveTab("agency")}
                    className={`px-4 py-2 text-xs font-bold border-b-2 transition-all ${
                        activeTab === "agency" ? "border-primary text-primary" : "border-transparent text-text-secondary hover:text-text-primary"
                    }`}
                >
                    Agency / Teams
                </button>
            </div>

            {/* TAB CONTENT PANEL */}
            <div key={activeTab} className="mx-auto max-w-4xl analysis-state-enter">
                {/* TikTok Shop Tab */}
                {activeTab === "tiktok" && (
                    <div className="grid gap-8 lg:grid-cols-12 items-start">
                        <div className="lg:col-span-5 space-y-4">
                            <span className="text-[9px] font-bold text-primary uppercase block">TikTok Shop US</span>
                            <h3 className="text-xl font-bold text-text-primary">TikTok Shop</h3>
                            <p className="text-sm text-text-secondary leading-relaxed">
                                You have a product and creators, but still need to decide which angle is worth filming and whether the resulting video deserves spend.
                            </p>
                            <div className="p-4 rounded-xl bg-surface-soft border border-divider text-xs leading-relaxed space-y-2">
                                <div><strong>Example Product:</strong> SwiftPress Mini Garment Steamer</div>
                                <div><strong>Workflow sequence:</strong> Product &rarr; Creative Directions &rarr; Creator Plan &rarr; Score &amp; Fix &rarr; Revision &rarr; Small Test</div>
                            </div>
                            <div className="pt-2">
                                <Button asChild size="sm">
                                    <Link to="/login">
                                        Launch TikTok Shop Campaign
                                        <ShoppingBag className="ml-1.5 h-4 w-4" />
                                    </Link>
                                </Button>
                            </div>
                        </div>

                        <div className="lg:col-span-7 p-6 rounded-3xl border border-hairline bg-surface shadow-sm text-xs leading-relaxed">
                            <h4 className="font-bold text-text-primary uppercase text-[10px] tracking-wider border-b border-divider pb-2 mb-3">
                                Case Decision Output
                            </h4>
                            <dl className="space-y-3">
                                <div>
                                    <dt className="font-bold text-text-tertiary">Decision Question</dt>
                                    <dd className="text-text-primary font-semibold text-sm">
                                        "What should we make, and is this version ready to test?"
                                    </dd>
                                </div>
                                <div className="p-3 bg-surface-soft border border-divider rounded-xl">
                                    <span className="font-bold text-ok block uppercase text-[8px] tracking-wide mb-1">Grounded Steamer Case Summary</span>
                                    <p className="text-[11px] text-text-secondary leading-relaxed">
                                        SwiftPress Steamer was analyzed under Student/Dorm context, generating the recommended "Late for Class" storyboard plan. Creator draft V1 missed product reveal timing (4.2s) and was revised to 1.4s in V2.
                                    </p>
                                </div>
                            </dl>
                        </div>
                    </div>
                )}

                {/* POD Tab */}
                {activeTab === "pod" && (
                    <div className="grid gap-8 lg:grid-cols-12 items-start">
                        <div className="lg:col-span-5 space-y-4">
                            <span className="text-[9px] font-bold text-primary uppercase block">Print on Demand</span>
                            <h3 className="text-xl font-bold text-text-primary">POD &amp; Personalization</h3>
                            <p className="text-sm text-text-secondary leading-relaxed">
                                A personalized video can look great and still be unusable if the creator shows the wrong name, breed, variant or delivered product.
                            </p>
                            <div className="p-4 rounded-xl bg-surface-soft border border-divider text-xs leading-relaxed space-y-2">
                                <div><strong>Product:</strong> Personalized Dog Mom Crewneck</div>
                                <div><strong>Pattern:</strong> Identity Hook &rarr; Personalization Reveal &rarr; Emotional Payoff &rarr; Ordering Clarity</div>
                                <div><strong>Directions:</strong> Dog Mom Identity | Gift Reaction | How Personalization Works</div>
                            </div>
                        </div>

                        <div className="lg:col-span-7 p-6 rounded-3xl border border-divider bg-surface shadow-sm text-xs leading-relaxed">
                            <div className="flex justify-between items-center border-b border-divider pb-2 mb-3">
                                <h4 className="font-bold text-text-primary uppercase text-[10px] tracking-wider">
                                    Primary Preview Case (Draft: 18.1s)
                                </h4>
                                <StatusChip tone="destructive" className="uppercase text-[9px] font-bold">Reshoot Required</StatusChip>
                            </div>

                            <div className="space-y-3">
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="p-2.5 bg-surface-soft border border-divider rounded-xl">
                                        <span className="font-bold text-text-tertiary uppercase text-[8px] tracking-wide block">Expected Name</span>
                                        <p className="text-sm font-bold text-text-primary mt-0.5">Milo</p>
                                    </div>
                                    <div className="p-2.5 bg-destructive-soft border border-destructive/20 rounded-xl">
                                        <span className="font-bold text-destructive uppercase text-[8px] tracking-wide block">Observed (OCR @ 7.2–9.6s)</span>
                                        <p className="text-sm font-bold text-destructive mt-0.5">Miles</p>
                                    </div>
                                </div>

                                <div className="p-3 bg-destructive-soft/10 border border-destructive/20 rounded-xl text-[11px] leading-snug">
                                    <div className="flex items-center gap-1.5 font-bold text-destructive">
                                        <AlertTriangle className="h-3.5 w-3.5" />
                                        <span>HARD BLOCKER: PERSONALIZATION MISMATCH</span>
                                    </div>
                                    <p className="text-text-secondary mt-1">
                                        <strong>High Priority Fix:</strong> Replace the incorrect product sample or reshoot the personalization close-up using the approved "Milo" version.
                                    </p>
                                </div>

                                <div className="text-[10px] text-text-tertiary">
                                    ✓ Keep: Strong identity hook, Natural creator reaction.
                                </div>
                                <div className="pt-2 border-t border-divider text-center font-semibold text-text-primary text-[11px]">
                                    "A video can be emotionally strong and still show the wrong product."
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Dropshipping Tab */}
                {activeTab === "dropship" && (
                    <div className="grid gap-8 lg:grid-cols-12 items-start">
                        <div className="lg:col-span-5 space-y-4">
                            <span className="text-[9px] font-bold text-primary uppercase block">Dropship Operators</span>
                            <h3 className="text-xl font-bold text-text-primary">Dropshipping</h3>
                            <p className="text-sm text-text-secondary leading-relaxed">
                                Avoid compliance bans. Viraldy screens drafts for universal claims, guaranteed shipping promises, and packaging statements that do not align with governance rules.
                            </p>
                            <div className="p-4 rounded-xl bg-surface-soft border border-divider text-xs leading-relaxed space-y-2">
                                <div><strong>Product:</strong> Rechargeable Mini Bag Sealer</div>
                                <div><strong>Pattern:</strong> Mess Interruption &rarr; One-Handed Demo &rarr; Leak / Seal Proof &rarr; Trust Cue</div>
                                <div><strong>Buyers:</strong> Students, Families, Snack buyers</div>
                            </div>
                        </div>

                        <div className="lg:col-span-7 p-6 rounded-3xl border border-divider bg-surface shadow-sm text-xs leading-relaxed">
                            <div className="flex justify-between items-center border-b border-divider pb-2 mb-3">
                                <h4 className="font-bold text-text-primary uppercase text-[10px] tracking-wider">
                                    Governance Audit (Draft Observations)
                                </h4>
                                <StatusChip tone="warn" className="uppercase text-[9px] font-bold">Revise Before Posting</StatusChip>
                            </div>

                            <dl className="space-y-3">
                                <div className="grid grid-cols-3 gap-2">
                                    <div className="p-2 bg-surface-soft border border-divider rounded-lg">
                                        <strong>Product Reveal:</strong> 1.1s
                                    </div>
                                    <div className="p-2 bg-surface-soft border border-divider rounded-lg">
                                        <strong>One-Handed Demo:</strong> Clear
                                    </div>
                                    <div className="p-2 bg-surface-soft border border-divider rounded-lg">
                                        <strong>Seal Line:</strong> Visible
                                    </div>
                                </div>

                                <div className="p-3 bg-destructive-soft border border-destructive/20 rounded-xl text-[11px] leading-snug">
                                    <span className="font-bold text-destructive block uppercase text-[8px]">Hard Blocker: Spoken claim at 8.9s</span>
                                    <p className="text-text-primary italic mt-0.5">"This makes every bag completely airtight."</p>
                                    <p className="text-text-secondary mt-1.5">
                                        <strong>Why:</strong> Product governance does not support universal airtight guarantees.
                                    </p>
                                    <p className="text-text-primary mt-1 font-semibold">
                                        Replace with: "I use it to reseal supported snack bags after opening."
                                    </p>
                                </div>

                                <div className="p-3 bg-surface-soft border border-divider rounded-xl">
                                    <span className="font-bold text-text-tertiary block uppercase text-[8px]">Shipping Governance check</span>
                                    <p className="text-[11px] text-text-secondary leading-normal mt-0.5">
                                        Authorized Shipping: <strong>7–10 business days</strong>. No shipping claim is present in this draft. Do not introduce delivery language faster than 7–10 days.
                                    </p>
                                </div>
                            </dl>
                            <div className="mt-4 pt-3 border-t border-divider text-center font-semibold text-text-primary text-[11px]">
                                "Viraldy should fix the unsupported claim without destroying the parts of the creative that already work."
                            </div>
                        </div>
                    </div>
                )}

                {/* Agency Tab */}
                {activeTab === "agency" && (
                    <div className="grid gap-8 lg:grid-cols-12 items-start">
                        <div className="lg:col-span-5 space-y-4">
                            <span className="text-[9px] font-bold text-primary uppercase block">Multi-Store Teams</span>
                            <h3 className="text-xl font-bold text-text-primary">Agency &amp; Teams</h3>
                            <p className="text-sm text-text-secondary leading-relaxed">
                                Five reviewers should not produce five completely different revision notes. Viraldy unifies your review parameters under shared expectations.
                            </p>
                            <div className="p-4 rounded-xl bg-surface-soft border border-divider text-xs leading-relaxed space-y-1.5">
                                <span className="font-bold text-text-primary block text-[10px]">Value</span>
                                <div>• Shared product context</div>
                                <div>• Shared creator requirements</div>
                                <div>• Evidence-backed revision requests</div>
                                <div>• History of draft revisions</div>
                            </div>
                        </div>

                        <div className="lg:col-span-7 p-6 rounded-3xl border border-divider bg-surface shadow-sm text-xs leading-relaxed">
                            <h4 className="font-bold text-text-primary uppercase text-[10px] tracking-wider border-b border-divider pb-2 mb-3">
                                Standardizing Feedback Workflows
                            </h4>
                            <div className="grid gap-4 sm:grid-cols-2">
                                <div className="p-3 bg-destructive-soft/10 border border-destructive/10 rounded-xl">
                                    <span className="font-bold text-destructive block uppercase text-[8px] tracking-wide mb-1">Before (Subjective)</span>
                                    <ul className="space-y-1 text-text-secondary text-[11px]">
                                        <li>"This feels weak."</li>
                                        <li>"Can we make it punchier?"</li>
                                        <li>"Maybe show the product sooner?"</li>
                                    </ul>
                                </div>
                                <div className="p-3 bg-ok-soft/15 border border-ok/10 rounded-xl">
                                    <span className="font-bold text-ok block uppercase text-[8px] tracking-wide mb-1">With Viraldy (Objective)</span>
                                    <ul className="space-y-1 text-text-secondary text-[11px]">
                                        <li>"Product reveal missed the 2s window."</li>
                                        <li>"Same-shirt proof is incomplete."</li>
                                        <li>"Natural creator style is preserved."</li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </SectionWrapper>
    );
}
