import { cn } from "@/shared/lib/utils";
import {
    CAMPAIGN_PHASES,
    STEPS,
    completionPercent,
    firstStepForPhase,
    phaseForStep,
    phaseIsComplete,
    stepIsComplete,
} from "@/features/campaigns/lib/campaignSteps";
import type { CampaignPack, StepId } from "@/features/campaigns/types/campaign";
import { Check, ChevronDown } from "lucide-react";

export function StepNav({
    pack,
    current,
    onSelect,
    compact = false,
}: {
    pack: CampaignPack;
    current: StepId;
    onSelect: (id: StepId) => void;
    compact?: boolean;
}) {
    const pct = completionPercent(pack);
    const currentPhase = phaseForStep(current);
    if (compact) {
        return (
            <div className="min-w-0">
                <nav
                    aria-label="Campaign phases"
                    className="flex snap-x snap-mandatory overflow-x-auto border-b border-divider"
                >
                    {CAMPAIGN_PHASES.map((phase, index) => {
                        const done = phaseIsComplete(pack, phase);
                        const active = currentPhase.id === phase.id;
                        return (
                            <button
                                key={phase.id}
                                type="button"
                                onClick={() => onSelect(firstStepForPhase(pack, phase))}
                                aria-current={active ? "step" : undefined}
                                className={cn(
                                    "relative flex min-h-10 shrink-0 snap-start items-center gap-1.5 px-3 py-2 text-xs transition-colors duration-[180ms] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring motion-reduce:transition-none",
                                    active
                                        ? "font-medium text-primary-active after:absolute after:inset-x-2 after:bottom-0 after:h-0.5 after:bg-primary"
                                        : done
                                          ? "text-ok"
                                          : "text-text-tertiary",
                                )}
                            >
                                {done ? (
                                    <Check className="h-3 w-3" aria-hidden />
                                ) : (
                                    <span className="tabular text-[10px]">{index + 1}</span>
                                )}
                                {phase.short}
                            </button>
                        );
                    })}
                </nav>
                {currentPhase.steps.length > 1 && (
                    <nav
                        aria-label={`${currentPhase.label} steps`}
                        className="flex snap-x snap-mandatory gap-1 overflow-x-auto py-2"
                    >
                        {currentPhase.steps.map((step) => {
                            const definition = STEPS.find((item) => item.id === step);
                            const selected = current === step;
                            const complete = stepIsComplete(pack, step);
                            return (
                                <button
                                    key={step}
                                    type="button"
                                    onClick={() => onSelect(step)}
                                    aria-current={selected ? "step" : undefined}
                                    className={cn(
                                        "flex min-h-8 shrink-0 snap-start items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs transition-colors duration-[180ms] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring motion-reduce:transition-none",
                                        selected
                                            ? "bg-primary-soft font-medium text-primary-active"
                                            : "text-text-secondary hover:bg-surface-soft",
                                    )}
                                >
                                    {complete && <Check className="h-3 w-3 text-ok" aria-hidden />}
                                    {definition?.label ?? step}
                                </button>
                            );
                        })}
                    </nav>
                )}
            </div>
        );
    }
    return (
        <nav aria-label="Campaign phases" className="flex flex-col gap-1">
            <div className="mb-3 px-2">
                <p className="text-[10px] font-semibold uppercase text-text-tertiary">Progress</p>
                <p className="mt-1 text-sm font-medium text-text-primary">{pct}% complete</p>
                <div className="mt-2 h-1 overflow-hidden rounded-full bg-surface-muted">
                    <div
                        className="h-full rounded-full bg-primary transition-all"
                        style={{ width: `${pct}%` }}
                    />
                </div>
            </div>
            {CAMPAIGN_PHASES.map((phase, index) => {
                const done = phaseIsComplete(pack, phase);
                const active = currentPhase.id === phase.id;
                return (
                    <div key={phase.id}>
                        <button
                            type="button"
                            onClick={() => onSelect(firstStepForPhase(pack, phase))}
                            aria-current={active ? "step" : undefined}
                            className={cn(
                                "group grid min-h-10 w-full grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-sm transition-colors duration-[180ms] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring motion-reduce:transition-none",
                                active
                                    ? "bg-primary-soft font-medium text-primary-active"
                                    : done
                                      ? "text-text-primary hover:bg-surface-soft"
                                      : "text-text-tertiary hover:bg-surface-soft hover:text-text-primary",
                            )}
                        >
                            <span
                                className={cn(
                                    "grid h-5 w-5 place-items-center rounded-full text-[10px] font-semibold tabular",
                                    done
                                        ? "text-ok"
                                        : active
                                          ? "bg-primary text-primary-foreground"
                                          : "ring-1 ring-divider text-text-tertiary",
                                )}
                            >
                                {done ? <Check className="h-3 w-3" /> : index + 1}
                            </span>
                            <span className="truncate">{phase.label}</span>
                            {phase.steps.length > 1 && (
                                <ChevronDown
                                    className={cn(
                                        "h-3.5 w-3.5 transition-transform duration-[180ms] motion-reduce:transition-none",
                                        active && "rotate-180",
                                    )}
                                    aria-hidden
                                />
                            )}
                        </button>

                        {active && phase.steps.length > 1 && (
                            <div className="ml-7 mt-1 border-l border-divider pl-2">
                                {phase.steps.map((step) => {
                                    const definition = STEPS.find((item) => item.id === step);
                                    const selected = current === step;
                                    const complete = stepIsComplete(pack, step);
                                    return (
                                        <button
                                            key={step}
                                            type="button"
                                            onClick={() => onSelect(step)}
                                            aria-current={selected ? "step" : undefined}
                                            className={cn(
                                                "flex min-h-9 w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs transition-colors duration-[180ms] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring motion-reduce:transition-none",
                                                selected
                                                    ? "font-medium text-primary-active"
                                                    : "text-text-secondary hover:bg-surface-soft hover:text-text-primary",
                                            )}
                                        >
                                            {complete ? (
                                                <Check
                                                    className="h-3.5 w-3.5 text-ok"
                                                    aria-hidden
                                                />
                                            ) : (
                                                <span
                                                    className="h-2 w-2 rounded-full ring-1 ring-divider"
                                                    aria-hidden
                                                />
                                            )}
                                            <span className="truncate">
                                                {definition?.label ?? step}
                                            </span>
                                        </button>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                );
            })}
        </nav>
    );
}
