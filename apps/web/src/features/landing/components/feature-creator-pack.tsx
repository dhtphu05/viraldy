import { Link } from "@tanstack/react-router";
import { ArrowRight, Clipboard, Clock } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { StatusChip } from "@/shared/ui/status-chip";
import { SectionWrapper } from "./section-wrapper";

const creatorGets = [
    "Creative concept",
    "Target buyer",
    "Opening shot",
    "Hook options",
    "Talking points",
    "Script guidance",
    "Storyboard",
    "Shot list",
    "Must-show product details",
    "Demo requirements",
    "Proof requirements",
    "Text overlays",
    "CTA",
    "Do / Don't",
    "Claims to avoid",
    "Revision checklist",
];

const shotList = [
    { time: "0–2s", action: "Show the wrinkled shirt and the \"late for class\" situation.", color: "info" },
    { time: "2–5s", action: "Reveal the steamer naturally.", color: "ok" },
    { time: "5–10s", action: "Steam one visible section of the shirt.", color: "info" },
    { time: "10–14s", action: "Show the same section after use.", color: "ok" },
    { time: "14–18s", action: "Natural creator reaction and personal benefit.", color: "warn" },
    { time: "18–21s", action: "TikTok Shop CTA.", color: "info" },
];

const colorMap: Record<string, string> = { info: "bg-info text-white", ok: "bg-ok text-white", warn: "bg-warn text-white" };

export function FeatureCreatorPack() {
    return (
        <SectionWrapper id="creator-pack" background="surface">
            <div className="grid gap-12 lg:grid-cols-2 lg:items-start">
                <div>
                    <StatusChip tone="info" dot>Feature 3</StatusChip>
                    <h2 className="mt-3 text-2xl font-bold text-text-primary sm:text-3xl">
                        Turn a creative direction into something a creator can actually film.
                    </h2>
                    <h3 className="mt-2 text-lg font-semibold text-text-secondary">
                        From idea to ready-to-film TikTok plan.
                    </h3>
                    <p className="mt-3 text-sm text-text-secondary">
                        Choose a direction and Viraldy builds a Creator Pack around it.
                    </p>

                    <div className="mt-5">
                        <div className="flex items-center gap-2">
                            <Clipboard className="h-4 w-4 text-primary" />
                            <p className="text-xs font-semibold uppercase text-text-tertiary">
                                Your creator gets
                            </p>
                        </div>
                        <div className="mt-3 grid grid-cols-2 gap-1.5 sm:grid-cols-3">
                            {creatorGets.map((item) => (
                                <div
                                    key={item}
                                    className="flex items-start gap-1.5 rounded-md px-1.5 py-1 text-xs text-text-secondary"
                                >
                                    <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                                    {item}
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="surface-card p-5">
                    <div className="flex items-center gap-2">
                        <Clock className="h-4 w-4 text-primary" />
                        <p className="text-xs font-semibold uppercase text-text-tertiary">
                            Example Creator Plan
                        </p>
                    </div>
                    <div className="mt-4 space-y-0">
                        {shotList.map((shot, i) => (
                            <div key={shot.time} className="relative flex gap-3 pb-3 pl-6">
                                <span className="absolute left-0 top-0 h-full w-px bg-divider" />
                                <span
                                    className={`absolute left-0 top-1 h-2.5 w-2.5 -translate-x-1/2 rounded-full ${colorMap[shot.color]}`}
                                />
                                <div className="min-w-0">
                                    <span className="text-[10px] font-semibold tabular text-primary">
                                        {shot.time}
                                    </span>
                                    <p className="mt-0.5 text-xs leading-relaxed text-text-secondary">
                                        {shot.action}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <div className="mt-8 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
                <Button asChild size="sm">
                    <Link to="/login">
                        Create Creator Pack
                        <ArrowRight className="ml-1 h-4 w-4" />
                    </Link>
                </Button>
                <Button asChild variant="outline" size="sm">
                    <Link to="/login">Copy for Creator</Link>
                </Button>
            </div>

            <p className="mt-3 text-center text-xs text-text-tertiary italic">
                &ldquo;Less &lsquo;make it more catchy.&rsquo; More &lsquo;here&rsquo;s exactly what we need.&rsquo;&rdquo;
            </p>
        </SectionWrapper>
    );
}
