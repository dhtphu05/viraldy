import { Link } from "@tanstack/react-router";
import { ArrowRight, Eye, Lightbulb, ShieldBan } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { StatusChip } from "@/shared/ui/status-chip";
import { SectionWrapper } from "./section-wrapper";

const keepItems = ["Problem-first opening", "Fast visual demonstration", "Same-item proof"];
const adaptItems = ["Buyer", "Setting", "Product mechanism", "Benefit", "Offer"];
const avoidItems = ["Exact script", "Exact scene replication", "Competitor-specific claims", "Brand-specific creative elements"];

const sceneElements = [
    { label: "Hook", at: 0 },
    { label: "Buyer angle", at: 8 },
    { label: "Opening visual", at: 16 },
    { label: "Product reveal", at: 25 },
    { label: "Demo structure", at: 38 },
    { label: "Proof mechanism", at: 50 },
    { label: "Creator style", at: 62 },
    { label: "Offer", at: 72 },
    { label: "CTA", at: 84 },
    { label: "Scene sequence", at: 92 },
    { label: "Commerce signals", at: 98 },
];

export function FeaturePatternBreakdown() {
    return (
        <SectionWrapper id="features" background="surface">
            <div className="grid gap-12 lg:grid-cols-2 lg:items-center">
                <div>
                    <StatusChip tone="info" dot>Feature 1</StatusChip>
                    <h2 className="mt-3 text-2xl font-bold text-text-primary sm:text-3xl">
                        See what is actually happening inside a winning creative.
                    </h2>
                    <h3 className="mt-2 text-lg font-semibold text-text-secondary">
                        Stop copying the surface. Understand the pattern.
                    </h3>
                    <p className="mt-3 text-sm text-text-secondary">
                        Drop in a reference video and Viraldy breaks it down into the parts that
                        matter for execution. You see:
                    </p>

                    <div className="mt-4 flex flex-wrap gap-2">
                        {sceneElements.map((el) => (
                            <span
                                key={el.label}
                                className="rounded-md border border-hairline bg-background px-2.5 py-1 text-xs text-text-secondary"
                            >
                                {el.label}
                            </span>
                        ))}
                    </div>

                    <p className="mt-5 text-sm font-semibold text-text-primary">
                        And Viraldy tells you what to do with it.
                    </p>

                    <div className="mt-4 space-y-4">
                        <div className="flex items-start gap-3">
                            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-ok-soft text-ok">
                                <Eye className="h-4 w-4" />
                            </span>
                            <div>
                                <StatusChip tone="ok">Keep</StatusChip>
                                <ul className="mt-2 space-y-1">
                                    {keepItems.map((item) => (
                                        <li key={item} className="text-sm text-text-secondary">{item}</li>
                                    ))}
                                </ul>
                            </div>
                        </div>

                        <div className="flex items-start gap-3">
                            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-info-soft text-info">
                                <Lightbulb className="h-4 w-4" />
                            </span>
                            <div>
                                <StatusChip tone="info">Adapt</StatusChip>
                                <ul className="mt-2 space-y-1">
                                    {adaptItems.map((item) => (
                                        <li key={item} className="text-sm text-text-secondary">{item}</li>
                                    ))}
                                </ul>
                            </div>
                        </div>

                        <div className="flex items-start gap-3">
                            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-destructive-soft text-destructive">
                                <ShieldBan className="h-4 w-4" />
                            </span>
                            <div>
                                <StatusChip tone="destructive">Avoid</StatusChip>
                                <ul className="mt-2 space-y-1">
                                    {avoidItems.map((item) => (
                                        <li key={item} className="text-sm text-text-secondary">{item}</li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    </div>

                    <Button asChild variant="outline" size="sm" className="mt-5">
                        <Link to="/login">
                            Break Down a Creative
                            <ArrowRight className="ml-1 h-4 w-4" />
                        </Link>
                    </Button>
                </div>

                <div className="surface-card p-5">
                    <p className="text-xs font-semibold uppercase text-text-tertiary">
                        Visual Structure Map
                    </p>
                    <div className="mt-4">
                        <div className="relative h-3 rounded-full bg-surface-muted">
                            <div className="absolute inset-y-0 left-0 h-full rounded-full bg-primary/15" style={{ width: "28%" }} />
                            <div className="absolute inset-y-0 h-full rounded-full bg-info/10" style={{ left: "28%", width: "24%" }} />
                            <div className="absolute inset-y-0 h-full rounded-full bg-ok/10" style={{ left: "52%", width: "20%" }} />
                            <div className="absolute inset-y-0 h-full rounded-full bg-warn/10" style={{ left: "72%", width: "28%" }} />
                        </div>
                        <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-text-tertiary">
                            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-primary/50" />Opening</span>
                            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-info/50" />Product</span>
                            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-ok/50" />Proof</span>
                            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-warn/50" />CTA</span>
                        </div>
                    </div>
                    <div className="mt-5 grid grid-cols-2 gap-2 text-xs">
                        {sceneElements.slice(0, 8).map((el) => (
                            <div key={el.label} className="flex items-center gap-2 rounded-md bg-surface-soft px-2.5 py-1.5">
                                <span className="shrink-0 tabular text-text-tertiary">{el.at}%</span>
                                <span className="truncate text-text-secondary">{el.label}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <p className="mt-6 text-center text-xs text-text-tertiary italic">
                &ldquo;Understand the structure. Rebuild the idea around your product.&rdquo;
            </p>
        </SectionWrapper>
    );
}
