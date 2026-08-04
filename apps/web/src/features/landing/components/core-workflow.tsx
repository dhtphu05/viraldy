import { Check, Circle, Package, Search, Target, Video, Wand, FileCheck } from "lucide-react";
import { StatusChip } from "@/shared/ui/status-chip";
import { SectionWrapper } from "./section-wrapper";
import { cn } from "@/shared/lib/utils";

const steps = [
    {
        num: "01",
        icon: Package,
        title: "Add your product",
        description: "Paste a product URL or choose an existing product. Viraldy builds the context needed to make useful creative decisions.",
        color: "primary",
    },
    {
        num: "02",
        icon: Search,
        title: "Bring inspiration or let Viraldy find the direction",
        description: "Add a reference creative when you have one. Viraldy breaks down the pattern and adapts the transferable parts to your product.",
        color: "info",
    },
    {
        num: "03",
        icon: Target,
        title: "Choose what to make",
        description: "Review three differentiated Creative Directions. Pick the one that fits your buyer, objective and product.",
        color: "warn",
    },
    {
        num: "04",
        icon: Wand,
        title: "Produce it",
        description: "Turn the selected direction into a Creator Pack. Use it with a human creator or send it into an AI Creator workflow.",
        color: "ok",
    },
    {
        num: "05",
        icon: Video,
        title: "Check the result",
        description: "Upload the video. Viraldy finds blockers, shows evidence and tells you what can be edited and what needs to be reshot.",
        color: "info",
    },
    {
        num: "06",
        icon: FileCheck,
        title: "Revise with confidence",
        description: "Upload the next version and verify whether the required fixes were actually completed.",
        color: "ok",
    },
];

const iconColor: Record<string, { bg: string; text: string; border: string }> = {
    primary: { bg: "bg-primary-soft", text: "text-primary", border: "border-primary/20" },
    info: { bg: "bg-info-soft", text: "text-info", border: "border-info/20" },
    warn: { bg: "bg-warn-soft", text: "text-warn", border: "border-warn/20" },
    ok: { bg: "bg-ok-soft", text: "text-ok", border: "border-ok/20" },
};

export function CoreWorkflow() {
    return (
        <SectionWrapper id="core-workflow" background="surface">
            <div className="text-center">
                <StatusChip tone="info">Workflow</StatusChip>
                <h2 className="mt-2 text-2xl font-bold text-text-primary sm:text-3xl">
                    One simple creative workflow.
                </h2>
            </div>

            <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                {steps.map((step, i) => {
                    const Icon = step.icon;
                    const c = iconColor[step.color];
                    return (
                        <div
                            key={step.num}
                            className={cn(
                                "surface-card p-5 transition-shadow duration-200 hover:shadow-hover-card",
                                step.color === "primary" && "border border-primary/20",
                            )}
                        >
                            <div className="flex items-start gap-4">
                                <div className="relative">
                                    <span
                                        className={cn(
                                            "grid h-10 w-10 shrink-0 place-items-center rounded-xl",
                                            c.bg,
                                        )}
                                    >
                                        <Icon className={cn("h-5 w-5", c.text)} />
                                    </span>
                                    {i === 0 && (
                                        <StatusChip tone="info" className="absolute -right-1 -top-1 px-1 py-0 text-[9px]">
                                            Start
                                        </StatusChip>
                                    )}
                                </div>
                                <div className="min-w-0">
                                    <span className="text-[10px] font-bold tabular text-text-tertiary">
                                        {step.num}
                                    </span>
                                    <h3 className="text-sm font-semibold text-text-primary">
                                        {step.title}
                                    </h3>
                                    <p className="mt-1.5 text-xs leading-relaxed text-text-secondary">
                                        {step.description}
                                    </p>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        </SectionWrapper>
    );
}
