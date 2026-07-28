import { StatusChip } from "@/shared/ui/status-chip";
import { ChevronRight } from "lucide-react";
import type { Campaign, MetricTone } from "@/shared/types";
import { cn } from "@/shared/lib/utils";

const statusTone: Record<Campaign["status"], MetricTone> = {
    Live: "ok",
    Testing: "info",
    Paused: "warn",
    Draft: "neutral",
};

function fmtGmv(n: number) {
    return `$${n.toLocaleString("en-US")}`;
}

function ugcTone(score: number): MetricTone {
    if (score >= 80) return "ok";
    if (score >= 65) return "info";
    return "warn";
}

export function CampaignRow({
    campaign,
    onClick,
    className,
}: {
    campaign: Campaign;
    onClick: () => void;
    className?: string;
}) {
    return (
        <button
            type="button"
            onClick={onClick}
            className={cn(
                "group grid w-full grid-cols-[minmax(0,2.4fr)_minmax(0,1fr)_auto] items-center gap-3 rounded-md px-4 py-3 text-left transition-colors hover:bg-surface-soft/70 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring sm:grid-cols-[minmax(0,2.4fr)_minmax(0,1fr)_100px_100px_120px_auto]",
                className,
            )}
        >
            <div className="min-w-0">
                <p className="truncate text-sm font-medium text-text-primary">{campaign.name}</p>
                <p className="truncate text-xs text-text-secondary">{campaign.product}</p>
            </div>
            <div className="min-w-0">
                <StatusChip tone={statusTone[campaign.status]} dot>
                    {campaign.status}
                </StatusChip>
                <p className="mt-0.5 truncate text-xs text-text-tertiary">
                    {campaign.activeAssets} active assets
                </p>
            </div>
            <div className="hidden sm:block">
                <div className="flex items-center gap-2">
                    <div className="h-1.5 w-14 overflow-hidden rounded-full bg-surface-muted">
                        <div
                            className={cn(
                                "h-full rounded-full",
                                ugcTone(campaign.ugcScore) === "ok"
                                    ? "bg-ok"
                                    : ugcTone(campaign.ugcScore) === "info"
                                      ? "bg-info"
                                      : "bg-warn",
                            )}
                            style={{ width: `${campaign.ugcScore}%` }}
                        />
                    </div>
                    <span className="tabular text-xs text-text-secondary">{campaign.ugcScore}</span>
                </div>
                <p className="mt-0.5 text-[10px] uppercase tracking-wide text-text-tertiary">
                    UGC score
                </p>
            </div>
            <div className="hidden sm:block">
                <p className="tabular text-sm font-medium text-text-primary">
                    {fmtGmv(campaign.gmv)}
                </p>
                <p className="text-[10px] uppercase tracking-wide text-text-tertiary">GMV</p>
            </div>
            <div className="hidden min-w-0 sm:block">
                <p className="truncate text-sm text-text-primary">{campaign.nextAction}</p>
                <p className="text-[10px] uppercase tracking-wide text-text-tertiary">
                    Next action
                </p>
            </div>
            <ChevronRight className="ml-auto h-4 w-4 text-text-tertiary transition-transform group-hover:translate-x-0.5" />
        </button>
    );
}
