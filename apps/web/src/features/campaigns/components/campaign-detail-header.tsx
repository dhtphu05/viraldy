import { Link } from "@tanstack/react-router";
import { Archive, ChevronRight, Copy, MoreHorizontal, Pencil } from "lucide-react";
import { Button } from "@/shared/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuRadioGroup,
    DropdownMenuRadioItem,
    DropdownMenuSeparator,
    DropdownMenuSub,
    DropdownMenuSubContent,
    DropdownMenuSubTrigger,
    DropdownMenuTrigger,
} from "@/shared/ui/dropdown-menu";
import { StatusChip } from "@/shared/ui/status-chip";
import { CampaignRenameDialog } from "@/features/campaigns/components/campaign-rename-dialog";
import type {
    CampaignLifecycle,
    CampaignReadiness,
} from "@/features/campaigns/lib/campaignReadiness";
import { campaignLifecycleLabel } from "@/features/campaigns/lib/campaignReadiness";
import type { CampaignPack, CampaignPackStatus } from "@/features/campaigns/types/campaign";
import { useState } from "react";

const STATUSES: CampaignPackStatus[] = [
    "Draft",
    "Ready for creator",
    "Creator production",
    "Awaiting UGC",
    "Active",
    "Completed",
    "Archived",
];

const LIFECYCLE_TONE: Record<
    CampaignLifecycle,
    "ok" | "warn" | "info" | "neutral" | "destructive"
> = {
    draft: "neutral",
    ready_for_review: "info",
    creator_ready: "ok",
    sent: "info",
    creator_production: "info",
    ugc_received: "warn",
    live: "ok",
};

export function CampaignDetailHeader({
    pack,
    readiness,
    productName,
    saveLabel,
    primaryActionLabel,
    onPrimaryAction,
    onDuplicate,
    onRename,
    onArchive,
    onStatusChange,
}: {
    pack: CampaignPack;
    readiness: CampaignReadiness;
    productName: string;
    saveLabel: string;
    primaryActionLabel: string;
    onPrimaryAction: () => void;
    onDuplicate: () => void;
    onRename: (name: string) => void;
    onArchive: () => void;
    onStatusChange: (status: CampaignPackStatus) => void;
}) {
    const [renameOpen, setRenameOpen] = useState(false);

    return (
        <>
            <div className="flex items-center gap-2 text-xs text-text-tertiary">
                <Link to="/campaigns" className="hover:text-text-primary">
                    Campaigns
                </Link>
                <ChevronRight className="h-3 w-3" aria-hidden />
                <span className="truncate text-text-secondary">{pack.name}</span>
            </div>

            <header className="flex flex-col gap-4 border-b border-divider pb-5 sm:flex-row sm:items-end sm:justify-between">
                <div className="min-w-0">
                    <h1 className="text-2xl font-semibold text-text-primary sm:text-[28px]">
                        {pack.name}
                    </h1>
                    <p className="mt-1 text-sm text-text-secondary">
                        {productName} · {pack.objective} · {pack.market} · {pack.platform}
                    </p>
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                        <StatusChip tone={LIFECYCLE_TONE[readiness.lifecycle]} dot>
                            {campaignLifecycleLabel(readiness.lifecycle)}
                        </StatusChip>
                        <span className="text-xs text-text-tertiary">{saveLabel}</span>
                    </div>
                </div>

                <div className="flex shrink-0 items-center gap-2">
                    <Button className="min-w-0 flex-1 sm:flex-none" onClick={onPrimaryAction}>
                        {primaryActionLabel}
                    </Button>
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button
                                variant="secondary"
                                size="icon"
                                className="h-10 w-10"
                                aria-label="More campaign actions"
                                title="More campaign actions"
                            >
                                <MoreHorizontal className="h-4 w-4" />
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-52">
                            <DropdownMenuItem onSelect={onDuplicate}>
                                <Copy className="h-4 w-4" />
                                Duplicate
                            </DropdownMenuItem>
                            <DropdownMenuItem onSelect={() => setRenameOpen(true)}>
                                <Pencil className="h-4 w-4" />
                                Rename
                            </DropdownMenuItem>
                            <DropdownMenuSub>
                                <DropdownMenuSubTrigger>Campaign status</DropdownMenuSubTrigger>
                                <DropdownMenuSubContent className="w-52">
                                    <DropdownMenuRadioGroup
                                        value={pack.status}
                                        onValueChange={(value) =>
                                            onStatusChange(value as CampaignPackStatus)
                                        }
                                    >
                                        {STATUSES.map((status) => (
                                            <DropdownMenuRadioItem
                                                key={status}
                                                value={status}
                                                disabled={
                                                    status !== "Draft" &&
                                                    status !== "Archived" &&
                                                    (!readiness.contentComplete ||
                                                        !readiness.qualityPassed ||
                                                        readiness.hardBlockers.length > 0)
                                                }
                                            >
                                                {status}
                                            </DropdownMenuRadioItem>
                                        ))}
                                    </DropdownMenuRadioGroup>
                                </DropdownMenuSubContent>
                            </DropdownMenuSub>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem onSelect={onArchive}>
                                <Archive className="h-4 w-4" />
                                Archive
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>
            </header>

            <CampaignRenameDialog
                open={renameOpen}
                currentName={pack.name}
                onOpenChange={setRenameOpen}
                onRename={onRename}
            />
        </>
    );
}
