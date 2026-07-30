import { Link } from "@tanstack/react-router";
import { ChevronRight, MoreHorizontal } from "lucide-react";
import { StatusChip } from "@/shared/ui/status-chip";
import type { SeedCampaign } from "@/features/campaigns/mocks/campaigns";
import type { CampaignPackStatus } from "@/features/campaigns/types/campaign";
import type { MetricTone } from "@/shared/types";
import { cn } from "@/shared/lib/utils";
import { RelativeTime } from "@/shared/ui/relative-time";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/shared/ui/dropdown-menu";

const packStatusTone: Record<CampaignPackStatus, MetricTone> = {
    Draft: "neutral",
    "Ready for creator": "info",
    "Creator production": "info",
    "Awaiting UGC": "warn",
    Active: "ok",
    Completed: "ok",
    Archived: "neutral",
};

export function CampaignListRow({
    campaign,
    onDuplicate,
    onRename,
    onArchive,
    onDelete,
    onChangeStatus,
    className,
}: {
    campaign: SeedCampaign;
    onDuplicate?: () => void;
    onRename?: () => void;
    onArchive?: () => void;
    onDelete?: () => void;
    onChangeStatus?: () => void;
    className?: string;
}) {
    const status = (campaign.packStatus ?? "Draft") as CampaignPackStatus;
    return (
        <div
            className={cn(
                "group grid w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 px-4 py-3 text-left transition-colors hover:bg-surface-soft/60 md:grid-cols-[minmax(0,2.4fr)_minmax(0,1fr)_minmax(0,1.4fr)_auto] xl:grid-cols-[minmax(0,2.4fr)_minmax(0,1fr)_120px_120px_minmax(0,1.4fr)_auto]",
                className,
            )}
        >
            <Link
                to="/campaigns/$campaignId"
                params={{ campaignId: campaign.id }}
                className="min-w-0 rounded-md focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
                <p className="truncate text-sm font-medium text-text-primary">{campaign.name}</p>
                <p className="truncate text-xs text-text-secondary">
                    {campaign.product}
                    {campaign.market ? ` · ${campaign.market}` : ""}
                </p>
            </Link>
            <div className="col-start-1 row-start-2 mt-2 min-w-0 md:col-start-auto md:row-start-auto md:mt-0">
                <StatusChip tone={packStatusTone[status]} dot>
                    {status}
                </StatusChip>
                {campaign.objective && (
                    <p className="mt-0.5 truncate text-xs text-text-tertiary">
                        {campaign.objective}
                    </p>
                )}
            </div>
            <div className="hidden min-w-0 xl:block">
                <p className="truncate text-sm text-text-primary">{campaign.primaryAngle ?? "—"}</p>
                <p className="text-[10px] uppercase text-text-tertiary">Angle</p>
            </div>
            <div className="hidden xl:block">
                <p className="tabular text-sm text-text-primary">
                    {campaign.referenceCount ?? 0} refs · {campaign.hookCount ?? 0} hooks
                </p>
                <p className="text-[10px] uppercase text-text-tertiary">
                    {campaign.deliverables ?? 0} deliverables
                </p>
            </div>
            <Link
                to="/campaigns/$campaignId"
                params={{ campaignId: campaign.id }}
                className="col-start-1 row-start-3 mt-2 min-w-0 rounded-md focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring md:col-start-auto md:row-start-auto md:mt-0"
            >
                <p className="flex items-center gap-1 text-sm font-semibold text-primary-active">
                    <span className="truncate">{campaign.nextAction}</span>
                    <ChevronRight className="h-3.5 w-3.5 shrink-0" aria-hidden />
                </p>
                <p className="text-[10px] uppercase text-text-tertiary">
                    <RelativeTime value={campaign.updatedAt} />
                </p>
            </Link>
            <div className="col-start-2 row-span-3 row-start-1 flex items-center md:col-start-auto md:row-span-1 md:row-start-auto">
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <button
                            type="button"
                            aria-label="Campaign actions"
                            className="grid h-8 w-8 place-items-center rounded-md text-text-tertiary hover:bg-surface-soft hover:text-text-primary focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                        >
                            <MoreHorizontal className="h-4 w-4" />
                        </button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={onRename}>Rename</DropdownMenuItem>
                        <DropdownMenuItem onClick={onDuplicate}>Duplicate</DropdownMenuItem>
                        <DropdownMenuItem onClick={onChangeStatus}>Change status</DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem onClick={onArchive}>Archive</DropdownMenuItem>
                        {onDelete && (
                            <DropdownMenuItem
                                className="text-destructive focus:text-destructive"
                                onClick={onDelete}
                            >
                                Delete local draft
                            </DropdownMenuItem>
                        )}
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>
        </div>
    );
}
