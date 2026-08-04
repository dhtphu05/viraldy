import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowRight, ShoppingCart, ShieldCheck, RefreshCw, BarChart2, Layers } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { SectionWrapper } from "./section-wrapper";

type UseCaseTab = "tiktok-shop" | "pod" | "dropshipping" | "agency";

export function UseCases() {
    const [activeTab, setActiveTab] = useState<UseCaseTab>("tiktok-shop");

    const tabContent = {
        "tiktok-shop": {
            title: "TikTok Shop Sellers",
            description: "Turn competitor and creator references into product-specific angles, creator briefs, and high-converting shop videos.",
            pain: "We have a product and creators, but we do not know which angle is worth filming or whether the final video is structurally ready for TikTok Shop.",
            workflow: "Creative Direction → Creator Plan → Score & Fix → Revision Compare",
            output: "Three creative bets, clear creator storyboard instructions, and exact edits/reshoots plans.",
            decision: "Approve for paid ads or scale shop affiliate partnerships with confidence.",
            caseStudy: "SwiftPress Mini Garment Steamer",
            caseDetails: "US college student lifestyle focus, dead-on hook matching time pressure, and validated before/after proof.",
            icon: ShoppingCart,
        },
        "pod": {
            title: "POD & Personalization",
            description: "Automatically verify that creators used the correct names, product options, and order details.",
            pain: "A creator video can look beautiful but be completely unusable if the personalized name, variant, or ordering instructions are wrong.",
            workflow: "Product-aware Creator Plan → Creator Draft Review → Expected vs Observed → Reshoot / Approve",
            output: "Detailed name matching checks (e.g. expecting 'Milo' but observed 'Miles') and variant alignment reports.",
            decision: "Reject and request creator reshoot before shipment, preventing customer refund claims.",
            caseStudy: "Personalized Dog Mom Crewneck",
            caseDetails: "Identity hook verification and OCR text validation to check personalization correctness.",
            icon: ShieldCheck,
        },
        "dropshipping": {
            title: "Dropshipping Operators",
            description: "Ground your product demonstrations in real facts to avoid policy violations, high returns, or claims risks.",
            pain: "Engagement doesn't equal sales if the creator makes false claims, overstates product compatibility, or misses showing how the product actually works.",
            workflow: "Grounded Product Context → Creator Brief Constraints → Structural Scorer Check → Approved Video",
            output: "Automatic flag alerts on prohibited claims (e.g. 'completely airtight' or 'food fresh forever') and mechanism validation.",
            decision: "Avoid high merchant chargebacks and ad account bans by keeping your copy legally compliant.",
            caseStudy: "Rechargeable Mini Bag Sealer",
            caseDetails: "Prohibiting airtight statements while validating the one-handed mechanical sealing demo.",
            icon: RefreshCw,
        },
        "agency": {
            title: "Agencies & Multi-Store Teams",
            description: "Establish a standardized review language across multiple brand accounts and clients.",
            pain: "Creative feedback is scattered across Slack, spreadsheets, and Drive comments. Hard-learned lessons are forgotten between campaigns.",
            workflow: "Unified Brand Dashboard → Standardized Creator Briefly → Historical Revision Tracking → Performance Feedback",
            output: "Shared creative context, structured review logs, and a central workspace repository for clients.",
            decision: "Scale creative QA capacity without adding management head count.",
            caseStudy: "Multi-Campaign Orchestration",
            caseDetails: "Aligning team reviewers around clear rules (e.g., 'hook timing', 'proof presence') instead of vague opinions.",
            icon: Layers,
        },
    };

    const current = tabContent[activeTab];
    const Icon = current.icon;

    return (
        <SectionWrapper id="use-cases" background="default" className="py-20">
            <div className="mx-auto max-w-4xl text-center">
                <span className="rounded-full bg-primary-soft px-3 py-1.5 text-xs font-semibold text-primary">
                    Use Cases
                </span>
                <h2 className="mt-4 text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
                    Built for the way creator-commerce teams actually work.
                </h2>
                <p className="mt-4 text-lg text-text-secondary">
                    Whether you are scaling a single shop or managing client portfolios, Viraldy bridges the gap between creative research, production, and video quality control.
                </p>
            </div>

            {/* Tab Buttons */}
            <div className="mt-12 flex flex-wrap justify-center gap-2">
                {(Object.keys(tabContent) as UseCaseTab[]).map((tabId) => {
                    const isActive = activeTab === tabId;
                    const TabIcon = tabContent[tabId].icon;
                    return (
                        <button
                            key={tabId}
                            onClick={() => setActiveTab(tabId)}
                            className={`flex items-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold transition-all duration-200 ${
                                isActive
                                    ? "bg-primary text-white shadow-md shadow-primary/20"
                                    : "bg-surface text-text-secondary hover:bg-surface-soft hover:text-text-primary border border-hairline"
                            }`}
                        >
                            <TabIcon className="h-4 w-4" />
                            {tabContent[tabId].title}
                        </button>
                    );
                })}
            </div>

            {/* Tab Panels */}
            <div className="mt-8 grid gap-8 lg:grid-cols-12 lg:items-start">
                {/* Details Column */}
                <div className="lg:col-span-7 space-y-6">
                    <div className="surface-card p-6 border border-hairline shadow-soft-card">
                        <div className="flex items-center gap-3">
                            <span className="grid h-10 w-10 place-items-center rounded-xl bg-primary-soft text-primary">
                                <Icon className="h-5 w-5" />
                            </span>
                            <div>
                                <h3 className="text-xl font-bold text-text-primary">{current.title}</h3>
                                <p className="text-sm text-text-secondary">{current.description}</p>
                            </div>
                        </div>

                        <div className="mt-6 space-y-5 border-t border-divider pt-6">
                            <div>
                                <h4 className="text-xs font-bold uppercase tracking-wider text-text-tertiary">Real Pain</h4>
                                <p className="mt-1 text-sm text-text-secondary leading-relaxed">{current.pain}</p>
                            </div>

                            <div>
                                <h4 className="text-xs font-bold uppercase tracking-wider text-text-tertiary">Viraldy Workflow</h4>
                                <p className="mt-1 text-sm font-semibold text-primary">{current.workflow}</p>
                            </div>

                            <div>
                                <h4 className="text-xs font-bold uppercase tracking-wider text-text-tertiary">What You Receive</h4>
                                <p className="mt-1 text-sm text-text-secondary leading-relaxed">{current.output}</p>
                            </div>

                            <div>
                                <h4 className="text-xs font-bold uppercase tracking-wider text-text-tertiary">Next Creative Decision</h4>
                                <p className="mt-1 text-sm text-text-secondary font-medium leading-relaxed">{current.decision}</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Example Product Column */}
                <div className="lg:col-span-5">
                    <div className="surface-card p-6 border border-primary/10 bg-primary-softer/40 rounded-2xl shadow-soft-card">
                        <span className="text-[10px] font-bold tracking-wider text-primary uppercase">
                            Grounded Case Study
                        </span>
                        <h4 className="mt-1 text-lg font-bold text-text-primary">
                            {current.caseStudy}
                        </h4>
                        <p className="mt-2 text-xs text-text-secondary leading-relaxed">
                            This use case is grounded in our Golden output fixture data, proving Viraldy's exact structural logic.
                        </p>

                        <div className="mt-4 rounded-xl bg-surface p-4 border border-divider">
                            <span className="text-[10px] font-semibold text-text-tertiary uppercase">Fixture Parameters</span>
                            <p className="mt-1 text-xs text-text-secondary font-medium">
                                {current.caseDetails}
                            </p>
                        </div>

                        <div className="mt-6 flex flex-col gap-2">
                            <Button asChild size="sm" className="w-full justify-center">
                                <Link to="/login">
                                    Start With This Case
                                    <ArrowRight className="ml-2 h-4 w-4" />
                                </Link>
                            </Button>
                        </div>
                    </div>
                </div>
            </div>
        </SectionWrapper>
    );
}
