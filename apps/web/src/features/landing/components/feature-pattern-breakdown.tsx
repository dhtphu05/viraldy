import { Link } from "@tanstack/react-router";
import { ArrowRight, Eye, Lightbulb, ShieldBan, Video } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { StatusChip } from "@/shared/ui/status-chip";
import { SectionWrapper } from "./section-wrapper";

export function FeaturePatternBreakdown() {
    const keepItems = [
        "Problem-first hook (deadline pressure opening)",
        "Fast visual demonstration of the steamer mechanism",
        "Observable same-garment before/after proof",
    ];
    const adaptItems = [
        "Buyer context (college student vs business traveler)",
        "Dorm setting & backpack storage references",
        "Specific steamer mechanism demonstration angles",
    ];
    const avoidItems = [
        "Exact script lines and dialog sequencing",
        "Specific brand competitor claims",
        "Universal fabric compatibility assertions",
    ];

    const timelineEvents = [
        { label: "Spoken Hook", range: "0:00 - 0:02", desc: "Ten minutes before class setup" },
        { label: "Product Reveal", range: "0:01.3", desc: "SwiftPress handheld device appears" },
        { label: "Visual Demo", range: "0:05 - 0:11", desc: "Glide steamer over wrinkled sleeve" },
        { label: "Fabric Proof", range: "0:11 - 0:15", desc: "Treated vs untreated same-shirt area" },
    ];

    return (
        <SectionWrapper id="pattern-breakdown" background="default" className="py-20 border-b border-hairline">
            <div className="mx-auto max-w-4xl text-center mb-12">
                <span className="rounded-full bg-primary-soft px-3 py-1.5 text-xs font-semibold text-primary">
                    Chapter 1: Finding What to Make
                </span>
                <h2 className="mt-4 text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
                    Stop guessing what creative to make next.
                </h2>
                <p className="mt-4 text-lg text-text-secondary leading-relaxed">
                    Finding inspiration isn't the hard part. The hard part is knowing why a video works, whether it fits your specific product context, and what you should build from it.
                </p>
            </div>

            <div className="grid gap-12 lg:grid-cols-12 lg:items-start">
                {/* Left: Pain & Copy */}
                <div className="lg:col-span-5 space-y-4">
                    <span className="text-[10px] font-bold text-primary uppercase tracking-wider block">Pattern Breakdown</span>
                    <h3 className="text-xl font-bold text-text-primary">
                        Found a great TikTok? See what is actually worth learning from it.
                    </h3>
                    <p className="text-sm text-text-secondary leading-relaxed">
                        Paste any reference TikTok link. Viraldy parses the structure and isolates the underlying commerce pattern, so you don't blindly copy surface-level details.
                    </p>

                    <div className="p-4 rounded-xl bg-surface-soft border border-divider">
                        <h4 className="text-xs font-bold text-text-primary uppercase tracking-wider mb-2">The Value: Reuse, Adapt, Don't Copy</h4>
                        <p className="text-xs text-text-secondary leading-relaxed">
                            Viraldy separates what is structurally reusable, what must be adapted to your product, and what constraints you must avoid.
                        </p>
                    </div>

                    <div className="pt-2">
                        <Button asChild size="sm">
                            <Link to="/login">
                                Break Down a Creative
                                <ArrowRight className="ml-2 h-4 w-4" />
                            </Link>
                        </Button>
                    </div>
                </div>

                {/* Right: Simulated Evidence UI */}
                <div className="lg:col-span-7 surface-card p-6 border border-hairline shadow-md">
                    <div className="flex items-center justify-between border-b border-divider pb-3 mb-4">
                        <div className="flex items-center gap-2">
                            <Video className="h-4 w-4 text-text-secondary" />
                            <span className="text-xs font-semibold text-text-primary">Reference Video Breakdown</span>
                        </div>
                        <StatusChip tone="info" className="text-[9px]">Grounded: home_travel_steamer</StatusChip>
                    </div>

                    {/* Timeline representation */}
                    <div className="space-y-4">
                        <span className="text-[10px] font-bold text-text-tertiary uppercase block">Timestamped Evidence</span>
                        <div className="relative h-1.5 rounded-full bg-surface-muted">
                            <div className="absolute inset-y-0 left-0 h-full rounded-full bg-info/40" style={{ width: "20%" }} />
                            <div className="absolute inset-y-0 h-full rounded-full bg-primary/40" style={{ left: "20%", width: "15%" }} />
                            <div className="absolute inset-y-0 h-full rounded-full bg-ok/40" style={{ left: "35%", width: "35%" }} />
                            <div className="absolute inset-y-0 h-full rounded-full bg-warn/40" style={{ left: "70%", width: "30%" }} />
                        </div>

                        <div className="grid gap-3 sm:grid-cols-2 text-xs">
                            {timelineEvents.map((evt) => (
                                <div key={evt.label} className="p-3 rounded-lg bg-surface-soft border border-divider">
                                    <div className="flex justify-between font-semibold text-text-primary">
                                        <span>{evt.label}</span>
                                        <span className="text-primary tabular">{evt.range}</span>
                                    </div>
                                    <p className="mt-1 text-[11px] text-text-secondary leading-snug">{evt.desc}</p>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Keep / Adapt / Avoid Guides */}
                    <div className="mt-6 pt-4 border-t border-divider space-y-4 text-xs">
                        <div className="flex items-start gap-2.5">
                            <span className="grid h-6 w-6 place-items-center rounded bg-ok-soft text-ok shrink-0 mt-0.5">
                                <Eye className="h-3.5 w-3.5" />
                            </span>
                            <div>
                                <strong className="text-ok font-semibold block">KEEP (Preserve)</strong>
                                <ul className="mt-1 list-disc pl-4 text-text-secondary space-y-0.5">
                                    {keepItems.map((item) => <li key={item}>{item}</li>)}
                                </ul>
                            </div>
                        </div>

                        <div className="flex items-start gap-2.5">
                            <span className="grid h-6 w-6 place-items-center rounded bg-info-soft text-info shrink-0 mt-0.5">
                                <Lightbulb className="h-3.5 w-3.5" />
                            </span>
                            <div>
                                <strong className="text-info font-semibold block">ADAPT (Localize)</strong>
                                <ul className="mt-1 list-disc pl-4 text-text-secondary space-y-0.5">
                                    {adaptItems.map((item) => <li key={item}>{item}</li>)}
                                </ul>
                            </div>
                        </div>

                        <div className="flex items-start gap-2.5">
                            <span className="grid h-6 w-6 place-items-center rounded bg-destructive-soft text-destructive shrink-0 mt-0.5">
                                <ShieldBan className="h-3.5 w-3.5" />
                            </span>
                            <div>
                                <strong className="text-destructive font-semibold block">AVOID (Block)</strong>
                                <ul className="mt-1 list-disc pl-4 text-text-secondary space-y-0.5">
                                    {avoidItems.map((item) => <li key={item}>{item}</li>)}
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </SectionWrapper>
    );
}
