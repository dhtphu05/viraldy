import { SectionWrapper } from "./section-wrapper";
import { Link } from "@tanstack/react-router";
import { ClipboardList, Copy, CheckSquare, Check, X, Info } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { StatusChip } from "@/shared/ui/status-chip";

export function CreatorPlan() {
    const hookOptions = [
        {
            label: "Option 1 (Primary · Mandatory)",
            spoken: "I had ten minutes before class and this shirt looked like it came straight out of my backpack.",
            visual: "Wrinkled shirt close-up with phone clock in background.",
            mandatory: true,
        },
        {
            label: "Option 2 (Optional)",
            spoken: "Dorm-room problem: no ironing board and a shirt I cannot wear like this.",
            visual: "Show small dorm space before revealing the product.",
            mandatory: false,
        },
        {
            label: "Option 3 (Optional)",
            spoken: "—",
            overlay: "Last-minute outfit rescue",
            visual: "Shirt first, product enters quickly.",
            mandatory: false,
        },
    ];

    const storyboard = [
        {
            scene: "Scene 01",
            time: "0–2s",
            purpose: "Problem + urgency",
            show: "Visible wrinkled shirt.",
            req: "Product must be clearly visible by 2.0s.",
        },
        {
            scene: "Scene 02",
            time: "2–5s",
            purpose: "Product reveal",
            show: "SwiftPress close-up entering naturally.",
            req: "Target product clearly identifiable.",
        },
        {
            scene: "Scene 03",
            time: "5–10s",
            purpose: "Mechanism",
            show: "Steam one clearly visible section of the same shirt.",
            req: "Keep the treated area visually identifiable.",
        },
        {
            scene: "Scene 04",
            time: "10–14s",
            purpose: "Proof",
            show: "Return to the exact same fabric section.",
            req: "Observable before/after result.",
        },
        {
            scene: "Scene 05",
            time: "14–18s",
            purpose: "Natural reaction",
            show: "Creator response.",
            req: "Do not exaggerate result.",
        },
        {
            scene: "Scene 06",
            time: "16–22s",
            purpose: "Commerce close",
            show: "Natural TikTok Shop product-tag CTA.",
            req: "\"I linked the one I use in the product tag.\"",
        },
    ];

    return (
        <SectionWrapper id="creator-plan" background="default" className="py-20 border-b border-hairline">
            <div className="mx-auto max-w-4xl text-center mb-12">
                <span className="rounded-full bg-primary-soft px-3 py-1.5 text-xs font-semibold text-primary">
                    Chapter 2: Make It Filmable
                </span>
                <h2 className="mt-4 text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
                    Picked the angle?
                    <br />
                    Give your creator a plan they can actually shoot.
                </h2>
                <p className="mt-4 text-lg text-text-secondary leading-relaxed">
                    Viraldy turns the selected creative direction into a production-ready plan &mdash; not just a script. The creator knows exactly what to say, what to show, and what constraints to follow.
                </p>
            </div>

            {/* Creator Plan Header Panel */}
            <div className="mx-auto max-w-4xl rounded-3xl border border-hairline bg-surface p-6 sm:p-8 shadow-soft-card mb-8">
                <div className="flex flex-wrap items-center justify-between border-b border-divider pb-4 mb-6 gap-2">
                    <div className="flex items-center gap-2">
                        <ClipboardList className="h-5 w-5 text-primary" />
                        <h3 className="text-base font-bold text-text-primary">Creative Production Brief</h3>
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                        <strong>Target Duration:</strong> 18–24s
                        <StatusChip tone="info" className="text-[9px] font-bold">Concept: Late for Class</StatusChip>
                    </div>
                </div>

                <div className="grid gap-6 md:grid-cols-12 text-xs leading-relaxed">
                    {/* Metadata & Style */}
                    <div className="md:col-span-4 space-y-4">
                        <h4 className="font-bold text-text-primary uppercase tracking-wider text-[10px] border-b border-divider pb-2">Campaign Target</h4>
                        <dl className="space-y-3">
                            <div>
                                <dt className="text-text-tertiary">Product</dt>
                                <dd className="text-text-primary font-medium">SwiftPress Mini Garment Steamer</dd>
                            </div>
                            <div>
                                <dt className="text-text-tertiary">Audience</dt>
                                <dd className="text-text-primary font-medium">US college students in dorms / shared apartments</dd>
                            </div>
                            <div>
                                <dt className="text-text-tertiary">Creator Persona &amp; Style</dt>
                                <dd className="text-text-primary font-medium">Casual student lifestyle creator</dd>
                            </div>
                            <div>
                                <dt className="text-text-tertiary">Delivery Mode</dt>
                                <dd className="text-text-secondary font-medium">Natural first-person (DO NOT sound like a commercial voice-over).</dd>
                            </div>
                        </dl>
                    </div>

                    {/* Hook Options */}
                    <div className="md:col-span-8 space-y-4">
                        <h4 className="font-bold text-text-primary uppercase tracking-wider text-[10px] border-b border-divider pb-2">Hook Options</h4>
                        <div className="space-y-3">
                            {hookOptions.map((opt, i) => (
                                <div key={i} className="p-3 rounded-xl bg-surface-soft border border-divider">
                                    <div className="flex justify-between items-center font-bold text-[10px] uppercase">
                                        <span className={opt.mandatory ? "text-primary" : "text-text-tertiary"}>{opt.label}</span>
                                    </div>
                                    <div className="mt-1.5 grid gap-2 sm:grid-cols-2">
                                        <div>
                                            <span className="text-[10px] text-text-tertiary font-semibold block">Spoken Hook:</span>
                                            <p className="text-text-primary italic">"{opt.spoken}"</p>
                                            {opt.overlay && (
                                                <p className="mt-1 text-text-secondary"><strong>Overlay:</strong> "{opt.overlay}"</p>
                                            )}
                                        </div>
                                        <div>
                                            <span className="text-[10px] text-text-tertiary font-semibold block">Visual Direction:</span>
                                            <p className="text-text-secondary">{opt.visual}</p>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                        <span className="text-[10px] text-text-tertiary block italic">
                            * Spoken hooks do not need to be duplicated as overlays unless the selected hook explicitly requires overlay text.
                        </span>
                    </div>
                </div>
            </div>

            {/* Storyboard Grid */}
            <div className="mx-auto max-w-4xl mb-8">
                <h3 className="text-sm font-bold uppercase tracking-wider text-text-tertiary mb-4">
                    Production Storyboard (Scene-by-Scene)
                </h3>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {storyboard.map((scene) => (
                        <div key={scene.scene} className="p-4 rounded-2xl border border-divider bg-surface flex flex-col justify-between shadow-sm">
                            <div>
                                <div className="flex justify-between items-center text-[10px] font-bold">
                                    <span className="text-primary uppercase">{scene.scene}</span>
                                    <span className="text-text-tertiary">{scene.time}</span>
                                </div>
                                <h4 className="mt-2 text-xs font-bold text-text-primary uppercase">{scene.purpose}</h4>
                                <p className="mt-2 text-xs text-text-secondary"><strong>Show:</strong> {scene.show}</p>
                            </div>
                            <div className="mt-4 pt-3 border-t border-divider text-[10px] text-text-primary">
                                <strong>Requirement:</strong> {scene.req}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Requirements Rules Panel */}
            <div className="mx-auto max-w-4xl grid gap-6 md:grid-cols-3 text-xs leading-relaxed mb-8">
                {/* Do list */}
                <div className="p-4 rounded-xl border border-divider bg-surface-soft">
                    <span className="font-bold text-ok uppercase tracking-wider flex items-center gap-1 mb-3 text-[10px]">
                        <Check className="h-4 w-4 text-ok" />
                        DO
                    </span>
                    <ul className="space-y-2 text-text-secondary list-disc pl-4">
                        <li>Keep same shirt and similar lighting</li>
                        <li>Speak naturally from personal experience</li>
                        <li>Keep product visible during main demo</li>
                        <li>Show result before mentioning discount</li>
                    </ul>
                </div>

                {/* Do Not list */}
                <div className="p-4 rounded-xl border border-divider bg-surface-soft">
                    <span className="font-bold text-destructive uppercase tracking-wider flex items-center gap-1 mb-3 text-[10px]">
                        <X className="h-4 w-4 text-destructive" />
                        DO NOT
                    </span>
                    <ul className="space-y-2 text-text-secondary list-disc pl-4">
                        <li>Say it removes every wrinkle instantly</li>
                        <li>Say safe on every fabric</li>
                        <li>Claim sanitization / bacteria removal</li>
                        <li>Use different shirt for result shot</li>
                        <li>Invent stock scarcity or faster shipping</li>
                    </ul>
                </div>

                {/* Constraints & Rights */}
                <div className="p-4 rounded-xl border border-divider bg-surface-soft space-y-3">
                    <span className="font-bold text-text-primary uppercase tracking-wider flex items-center gap-1 text-[10px]">
                        <Info className="h-4 w-4 text-text-secondary" />
                        Offers &amp; Governance
                    </span>
                    <dl className="space-y-2.5">
                        <div>
                            <dt className="font-bold text-text-tertiary">Verified Offer</dt>
                            <dd className="text-text-secondary">15% launch discount (Mention only after result is visible).</dd>
                        </div>
                        <div>
                            <dt className="font-bold text-text-tertiary">Required Disclosure</dt>
                            <dd className="text-text-primary italic">"Results vary by fabric type."</dd>
                        </div>
                        <div>
                            <dt className="font-bold text-text-tertiary">Rights Requested</dt>
                            <dd className="text-text-secondary">TikTok organic use, Spark Ads testing, editing of submitted cut. Raw footage preferred.</dd>
                        </div>
                    </dl>
                </div>
            </div>

            {/* CTAs */}
            <div className="mx-auto max-w-4xl flex flex-wrap justify-between items-center gap-4 pt-6 border-t border-divider">
                <div className="flex gap-3">
                    <Button asChild className="bg-primary hover:bg-primary-hover shadow-md shadow-primary/10">
                        <Link to="/login">
                            Copy Creator Plan
                            <Copy className="ml-2 h-4 w-4" />
                        </Link>
                    </Button>
                    <Button asChild variant="outline">
                        <Link to="/login">
                            Preview Creator Brief
                        </Link>
                    </Button>
                </div>
                <div className="text-xs text-text-tertiary italic">
                    Less "make it more catchy." More "here's exactly what we need."
                </div>
            </div>
        </SectionWrapper>
    );
}
