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
            <div className="flex snap-x snap-mandatory gap-2 overflow-x-auto pb-1">
                {STEPS.map((s, i) => {
                    const done = stepIsComplete(pack, s.id);
                    const active = current === s.id;
                    return (
                        <button
                            key={s.id}
                            type="button"
                            onClick={() => onSelect(s.id)}
                            className={cn(
                                "shrink-0 snap-start rounded-full border px-3 py-1 text-xs transition-colors",
                                active
                                    ? "border-primary/40 bg-primary-soft text-primary-active"
                                    : done
                                      ? "border-hairline/70 bg-ok-soft/60 text-ok"
                                      : "border-hairline/70 bg-surface text-text-secondary",
                            )}
                        >
                            <span className="mr-1 tabular text-[10px] text-text-tertiary">
                                {i + 1}
                            </span>
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
                <p className="text-[10px] font-semibold uppercase tracking-wider text-text-tertiary">
                    Progress
                </p>
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
                                ? "bg-primary-soft text-primary-active"
                                : "text-text-secondary hover:bg-surface-soft hover:text-text-primary",
                        )}
                    >
                        <span
                            className={cn(
                                "grid h-5 w-5 place-items-center rounded-full text-[10px] font-semibold tabular",
                                done
                                    ? "bg-ok text-ok-foreground"
                                    : active
                                      ? "bg-primary text-primary-foreground"
                                      : "bg-surface-muted text-text-tertiary",
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
