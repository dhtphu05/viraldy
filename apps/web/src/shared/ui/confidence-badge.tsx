import { Info } from "lucide-react";

import { humanizeLabel } from "@/shared/lib/display";
import { StatusChip } from "@/shared/ui/status-chip";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/shared/ui/tooltip";

export type ConfidenceLevel = "low" | "medium" | "high";

type ConfidenceBadgeProps = {
    level: ConfidenceLevel | string;
    dataUsed?: string;
    missingEvidence?: string;
    rationale?: string;
};

export function ConfidenceBadge({
    level,
    dataUsed,
    missingEvidence,
    rationale,
}: ConfidenceBadgeProps) {
    const explanation = [dataUsed, missingEvidence, rationale].filter(Boolean);
    const badge = (
        <StatusChip tone="info" className="gap-1">
            <Info className="h-3 w-3" aria-hidden />
            {humanizeLabel(level)} confidence
        </StatusChip>
    );

    if (!explanation.length) return badge;

    return (
        <TooltipProvider delayDuration={180}>
            <Tooltip>
                <TooltipTrigger asChild>{badge}</TooltipTrigger>
                <TooltipContent
                    side="top"
                    className="max-w-72 bg-text-primary px-3 py-2 text-primary-foreground"
                >
                    <div className="space-y-1">
                        {dataUsed && <p>Data used: {dataUsed}</p>}
                        {missingEvidence && <p>Missing evidence: {missingEvidence}</p>}
                        {rationale && <p>Why: {rationale}</p>}
                    </div>
                </TooltipContent>
            </Tooltip>
        </TooltipProvider>
    );
}
