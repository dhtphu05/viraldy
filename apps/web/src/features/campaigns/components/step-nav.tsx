import { cn } from "@/shared/lib/utils";
import { STEPS, stepIsComplete, completionPercent } from "@/features/campaigns/lib/campaignSteps";
import type { CampaignPack, StepId } from "@/features/campaigns/types/campaign";
import { Check, Circle } from "lucide-react";

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
    if (compact) {
        return (
            <div className="flex snap-x snap-mandatory overflow-x-auto border-b border-divider">
                {STEPS.map((s, i) => {
                    const done = stepIsComplete(pack, s.id);
                    const active = current === s.id;
                    return (
                        <button
                            key={s.id}
                            type="button"
                            onClick={() => onSelect(s.id)}
                            className={cn(
                                "relative flex shrink-0 snap-start items-center gap-1.5 px-3 py-2 text-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring",
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
                                <span className="tabular text-[10px]">{i + 1}</span>
                            )}
                            {s.short}
                        </button>
                    );
                })}
            </div>
        );
    }
    return (
        <nav aria-label="Campaign steps" className="flex flex-col gap-1">
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
            {STEPS.map((s, i) => {
                const done = stepIsComplete(pack, s.id);
                const active = current === s.id;
                return (
                    <button
                        key={s.id}
                        type="button"
                        onClick={() => onSelect(s.id)}
                        aria-current={active ? "step" : undefined}
                        className={cn(
                            "group grid grid-cols-[auto_minmax(0,1fr)] items-center gap-2.5 rounded-md px-2.5 py-1.5 text-left text-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
                            active
                                ? "font-medium text-primary-active"
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
                            {done ? (
                                <Check className="h-3 w-3" />
                            ) : active ? (
                                <Circle className="h-2 w-2 fill-current" />
                            ) : (
                                i + 1
                            )}
                        </span>
                        <span className="truncate">{s.label}</span>
                    </button>
                );
            })}
        </nav>
    );
}
