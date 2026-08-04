import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowRight, Lightbulb, CheckCircle2, FlaskConical, Target, ListCollapse } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { SectionWrapper } from "./section-wrapper";
import { StatusChip } from "@/shared/ui/status-chip";
import { ConfidenceBadge } from "@/shared/ui/confidence-badge";

type ConceptTab = "steamer_class" | "steamer_travel" | "steamer_space";

export function CreativeDirections() {
    const [selectedTab, setSelectedTab] = useState<ConceptTab>("steamer_class");

    const concepts = {
        steamer_class: {
            label: "01 · RECOMMENDED FIRST TEST",
            title: "Late for Class Rescue",
            axis: "Time pressure for a college student",
            buyer: "College student in a dorm",
            pain: "A wrinkled shirt immediately before class or an event.",
            outcome: "Look presentable without setting up an ironing board.",
            angle: "A compact last-minute clothing rescue for dorm life.",
            hook: "I had ten minutes before class and this shirt looked like it came straight out of my backpack.",
            openingVisual: "Macro close-up of the wrinkled shirt while a phone clock is visible in the background.",
            productReveal: "Enters frame before 1.8 seconds.",
            creator: "US college lifestyle creator",
            delivery: "Casual first-person demonstration",
            demo: "Steam the same shirt section while keeping the camera close enough to see the fabric.",
            proof: "Return to the same shirt section using similar framing and lighting.",
            offer: "Mention the verified 15% launch discount only after the result is shown.",
            cta: "Natural TikTok Shop product-tag CTA after proof.",
            hypothesis: "A time-pressure student scenario may create stronger relevance and product-click intent among college-age viewers without requiring high-pressure sales language.",
            learning: "Whether urgency from a real dorm situation creates stronger intent than travel or comparison positioning.",
            feasibility: "High",
            confidence: "medium",
        },
        steamer_travel: {
            label: "02 · ALTERNATIVE BUYER CONTEXT",
            title: "Carry-On Clothing Rescue",
            axis: "Travel convenience",
            buyer: "Frequent traveler using carry-on luggage",
            pain: "Clothing becomes wrinkled inside packed luggage.",
            outcome: "Refresh an outfit in a hotel room with a compact tool.",
            angle: "Hotel-room clothes rescue avoiding hotel irons.",
            hook: "This is why I stopped trusting hotel irons.",
            openingVisual: "Open a suitcase and pull out a visibly wrinkled outfit.",
            productReveal: "Enters frame before 2.2 seconds.",
            creator: "US travel creator",
            delivery: "Practical travel tip",
            demo: "Use the steamer on one half of a packed shirt in a hotel-room setting.",
            proof: "Show treated and untreated halves in the same frame.",
            offer: "Optional. Value and portability remain primary.",
            cta: "Natural TikTok Shop product-tag CTA after proof.",
            hypothesis: "Travel context and side-by-side proof may create stronger saves and high-intent comments among frequent travelers than a generic convenience demo.",
            learning: "Whether portability is a stronger purchase driver than time pressure.",
            feasibility: "Medium",
            confidence: "medium",
        },
        steamer_space: {
            label: "03 · CONTRAST TEST",
            title: "Small-Space Iron Alternative",
            axis: "Comparison and space saving",
            buyer: "Apartment renter with limited storage",
            pain: "A full-size iron and board take up too much space.",
            outcome: "Keep a compact clothing-care option in a drawer.",
            angle: "No ironing board setup space saving drawer.",
            hook: "I do not have space for an ironing board, so this lives in my desk drawer.",
            openingVisual: "Show a crowded closet, then open a drawer containing the compact steamer.",
            productReveal: "Visible immediately (0s).",
            creator: "Small-apartment lifestyle creator",
            delivery: "Practical comparison review",
            demo: "Show setup and use while the ironing board remains folded away.",
            proof: "Close-up result + storage-footprint comparison.",
            offer: "15% launch discount as a secondary value cue.",
            cta: "Natural TikTok Shop product-tag CTA after proof.",
            hypothesis: "Immediate product visibility and space-saving comparison may create strong product-click intent among apartment renters without a time-pressure story.",
            learning: "Whether product visibility and storage benefit outperform situational urgency.",
            feasibility: "High",
            confidence: "medium",
        },
    };

    const current = concepts[selectedTab];

    return (
        <SectionWrapper id="creative-directions" background="surface" className="py-20 border-b border-hairline">
            <div className="mx-auto max-w-4xl text-center mb-12">
                <span className="rounded-full bg-primary-soft px-3 py-1.5 text-xs font-semibold text-primary">
                    Chapter 1: Choose What to Make
                </span>
                <h2 className="mt-4 text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
                    Got a product but no clear angle?
                    <br />
                    Here are three different ways to sell it.
                </h2>
                <p className="mt-4 text-lg text-text-secondary leading-relaxed">
                    Viraldy combines your product context with reusable creative structure and turns it into three genuinely different creative bets. Not 20 random hooks. Not three rewrites of the same script.
                </p>
            </div>

            {/* Input Strip Info */}
            <div className="mx-auto max-w-4xl rounded-2xl bg-surface-soft border border-divider p-4 flex flex-wrap gap-x-6 gap-y-2 text-xs text-text-secondary justify-center mb-8">
                <div><strong>Product:</strong> SwiftPress Mini Garment Steamer</div>
                <div><strong>Price:</strong> $29.99</div>
                <div><strong>Offer:</strong> 15% launch discount</div>
                <div><strong>Goal:</strong> TikTok Shop affiliate test</div>
            </div>

            {/* Tab buttons */}
            <div className="mx-auto max-w-4xl flex justify-center gap-2 mb-8 flex-wrap">
                {(Object.keys(concepts) as ConceptTab[]).map((tab) => {
                    const isActive = selectedTab === tab;
                    return (
                        <button
                            key={tab}
                            onClick={() => setSelectedTab(tab)}
                            className={`px-5 py-3 rounded-xl text-xs font-bold transition-all duration-300 border ${
                                isActive
                                    ? "bg-primary text-white border-primary shadow-md shadow-primary/10"
                                    : "bg-surface text-text-secondary hover:bg-surface-soft border-hairline"
                            }`}
                        >
                            {concepts[tab].title}
                        </button>
                    );
                })}
            </div>

            {/* Selected concept card view */}
            <div className="mx-auto max-w-4xl rounded-3xl border border-hairline bg-surface p-6 sm:p-8 shadow-soft-card animate-fadeIn">
                <div className="flex flex-wrap items-center justify-between border-b border-divider pb-4 mb-6 gap-2">
                    <div>
                        <span className="text-[10px] font-bold text-primary tracking-wider uppercase block">
                            {current.label}
                        </span>
                        <h3 className="text-xl font-bold text-text-primary mt-1">
                            {current.title}
                        </h3>
                    </div>
                    <div className="flex items-center gap-2">
                        <ConfidenceBadge level={current.confidence} />
                        <StatusChip tone="info" className="text-[10px] font-bold">Feasibility: {current.feasibility}</StatusChip>
                    </div>
                </div>

                <div className="grid gap-6 md:grid-cols-2 text-xs leading-relaxed">
                    <div className="space-y-4">
                        <div>
                            <span className="font-bold text-text-tertiary uppercase block text-[9px] tracking-wide">Strategic Axis</span>
                            <p className="text-text-primary font-medium text-sm mt-0.5">{current.axis}</p>
                        </div>
                        <div>
                            <span className="font-bold text-text-tertiary uppercase block text-[9px] tracking-wide">Target Buyer</span>
                            <p className="text-text-secondary mt-0.5">{current.buyer}</p>
                        </div>
                        <div>
                            <span className="font-bold text-text-tertiary uppercase block text-[9px] tracking-wide">Buyer Pain</span>
                            <p className="text-text-secondary mt-0.5">{current.pain}</p>
                        </div>
                        <div>
                            <span className="font-bold text-text-tertiary uppercase block text-[9px] tracking-wide">Desired Outcome</span>
                            <p className="text-text-secondary mt-0.5">{current.outcome}</p>
                        </div>
                        <div>
                            <span className="font-bold text-text-tertiary uppercase block text-[9px] tracking-wide">Creative Hook Tactic</span>
                            <p className="text-text-primary italic mt-0.5">"{current.hook}"</p>
                        </div>
                    </div>

                    <div className="space-y-4">
                        <div>
                            <span className="font-bold text-text-tertiary uppercase block text-[9px] tracking-wide">Opening Visual</span>
                            <p className="text-text-secondary mt-0.5">{current.openingVisual}</p>
                        </div>
                        <div>
                            <span className="font-bold text-text-tertiary uppercase block text-[9px] tracking-wide">Product Reveal</span>
                            <p className="text-text-secondary mt-0.5">{current.productReveal}</p>
                        </div>
                        <div>
                            <span className="font-bold text-text-tertiary uppercase block text-[9px] tracking-wide">Creator Persona &amp; Delivery</span>
                            <p className="text-text-secondary mt-0.5">{current.creator} ({current.delivery})</p>
                        </div>
                        <div>
                            <span className="font-bold text-text-tertiary uppercase block text-[9px] tracking-wide">Demo &amp; Proof</span>
                            <p className="text-text-secondary mt-0.5">{current.demo} &rarr; {current.proof}</p>
                        </div>
                        <div>
                            <span className="font-bold text-text-tertiary uppercase block text-[9px] tracking-wide">Hypothesis / Expected Learning</span>
                            <p className="text-text-secondary mt-0.5">
                                <strong>Hypothesis:</strong> {current.hypothesis}
                                <br />
                                <strong>Learning:</strong> {current.learning}
                            </p>
                        </div>
                    </div>
                </div>

                {/* Select CTA */}
                <div className="mt-8 pt-6 border-t border-divider flex flex-wrap justify-between items-center gap-4">
                    <p className="text-xs text-text-secondary">
                        Turn this direction into a creator-ready production plan.
                    </p>
                    <Button asChild className="bg-primary hover:bg-primary-hover shadow-md shadow-primary/10">
                        <Link to="/login">
                            Use {current.title}
                            <ArrowRight className="ml-2 h-4 w-4" />
                        </Link>
                    </Button>
                </div>
            </div>

            {/* Concept Comparison Table */}
            <div className="mx-auto max-w-4xl mt-12">
                <h3 className="text-sm font-bold uppercase tracking-wider text-text-tertiary mb-4 text-center">
                    Concept Comparison Matrix
                </h3>
                <div className="overflow-x-auto rounded-2xl border border-divider bg-surface">
                    <table className="w-full min-w-[640px] text-left text-xs">
                        <thead>
                            <tr className="border-b border-divider bg-surface-soft font-bold text-text-primary">
                                <th className="p-3">Parameter</th>
                                <th className="p-3">Late for Class (01)</th>
                                <th className="p-3">Carry-On (02)</th>
                                <th className="p-3">Small Space (03)</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-divider text-text-secondary">
                            <tr>
                                <td className="p-3 font-semibold text-text-primary">Buyer</td>
                                <td className="p-3">College student</td>
                                <td className="p-3">Traveler</td>
                                <td className="p-3">Apartment renter</td>
                            </tr>
                            <tr>
                                <td className="p-3 font-semibold text-text-primary">Primary Pain</td>
                                <td className="p-3">Time pressure</td>
                                <td className="p-3">Packed wrinkles</td>
                                <td className="p-3">Storage/setup</td>
                            </tr>
                            <tr>
                                <td className="p-3 font-semibold text-text-primary">Hook</td>
                                <td className="p-3">Situation</td>
                                <td className="p-3">Travel reveal</td>
                                <td className="p-3">Comparison</td>
                            </tr>
                            <tr>
                                <td className="p-3 font-semibold text-text-primary">Product first seen</td>
                                <td className="p-3">&lt;1.8s</td>
                                <td className="p-3">&lt;2.2s</td>
                                <td className="p-3">0s</td>
                            </tr>
                            <tr>
                                <td className="p-3 font-semibold text-text-primary">Creator</td>
                                <td className="p-3">Student</td>
                                <td className="p-3">Travel</td>
                                <td className="p-3">Home/lifestyle</td>
                            </tr>
                            <tr>
                                <td className="p-3 font-semibold text-text-primary">Demo</td>
                                <td className="p-3">Same-shirt</td>
                                <td className="p-3">Half-shirt</td>
                                <td className="p-3">Setup + in-use</td>
                            </tr>
                            <tr>
                                <td className="p-3 font-semibold text-text-primary">Proof</td>
                                <td className="p-3">Same-area result</td>
                                <td className="p-3">Treated vs untreated</td>
                                <td className="p-3">Result + footprint</td>
                            </tr>
                            <tr className="bg-primary-softer/10">
                                <td className="p-3 font-semibold text-text-primary">Main learning</td>
                                <td className="p-3 font-medium text-text-primary">Immediate intent</td>
                                <td className="p-3">Travel relevance</td>
                                <td className="p-3">Storage/value</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Experiment Intelligence */}
            <div className="mx-auto max-w-4xl mt-12 grid gap-6 md:grid-cols-2 p-6 rounded-3xl border border-hairline bg-surface shadow-sm">
                <div className="space-y-3">
                    <span className="text-[10px] font-bold text-primary uppercase tracking-wider block">
                        Not Three Random Ideas
                    </span>
                    <h3 className="text-base font-bold text-text-primary">
                        Each creative should teach you something different.
                    </h3>
                    <p className="text-xs text-text-secondary leading-relaxed">
                        If every creative changes everything at once, you learn almost nothing. Viraldy holds key variables constant and changes specific parameters to isolate performance drivers.
                    </p>
                    <div className="pt-2 text-xs">
                        <strong>Recommended Test Order:</strong>
                        <ol className="mt-2 list-decimal pl-4 space-y-1 font-medium text-text-primary">
                            <li>Late for Class Rescue</li>
                            <li>Small-Space Iron Alternative</li>
                            <li>Carry-On Clothing Rescue</li>
                        </ol>
                    </div>
                </div>

                <div className="grid gap-4 sm:grid-cols-2 text-xs leading-relaxed">
                    <div className="p-3 rounded-xl bg-surface-soft border border-divider">
                        <strong className="text-text-primary block mb-2 uppercase text-[9px] tracking-wide">Held Constant</strong>
                        <ul className="list-disc pl-4 space-y-1 text-text-secondary text-[11px]">
                            <li>Product Model</li>
                            <li>$29.99 price</li>
                            <li>15% launch discount</li>
                            <li>18–24s target duration</li>
                            <li>Product-tag CTA</li>
                            <li>Same-item proof</li>
                            <li>Fabric disclosure</li>
                        </ul>
                    </div>

                    <div className="p-3 rounded-xl bg-surface-soft border border-divider">
                        <strong className="text-text-primary block mb-2 uppercase text-[9px] tracking-wide">Intentionally Changed</strong>
                        <ul className="list-disc pl-4 space-y-1 text-text-secondary text-[11px]">
                            <li>Buyer persona</li>
                            <li>Hook mechanism</li>
                            <li>Creator persona</li>
                            <li>Demo framing</li>
                            <li>Proof framing</li>
                        </ul>
                    </div>
                </div>
            </div>
        </SectionWrapper>
    );
}
