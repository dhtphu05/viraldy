import { ChevronLeft, ChevronRight, Eye } from "lucide-react";
import { ActionTray } from "@/shared/ui/action-tray";
import { Button } from "@/shared/ui/button";
import { StatusChip } from "@/shared/ui/status-chip";
import { STEPS, completionPercent, stepIsComplete } from "@/features/campaigns/lib/campaignSteps";
import type { CampaignPack, StepId } from "@/features/campaigns/types/campaign";

export function CampaignActionTray({
    pack,
    step,
    onStep,
    onPreview,
}: {
    pack: CampaignPack;
    step: StepId;
    onStep: (step: StepId) => void;
    onPreview: () => void;
}) {
    const currentIndex = STEPS.findIndex((item) => item.id === step);
    const currentStep = STEPS[currentIndex] ?? STEPS[0];
    const previousStep = STEPS[currentIndex - 1];
    const nextStep = STEPS[currentIndex + 1];
    const complete = stepIsComplete(pack, step);

    return (
        <ActionTray
            sticky={false}
            className="rounded-md border border-control-border shadow-none"
            context={
                <div className="flex min-w-0 items-start gap-2">
                    <StatusChip tone={complete ? "ok" : "neutral"} dot>
                        {complete ? "Complete" : "In progress"}
                    </StatusChip>
                    <div className="min-w-0">
                        <p className="font-medium text-text-primary">{currentStep.label}</p>
                        <p className="mt-0.5 text-xs text-text-secondary">
                            {complete ? "Saved in this browser." : blockerForStep(pack, step)}{" "}
                            {completionPercent(pack)}% complete.
                        </p>
                    </div>
                </div>
            }
            secondaryAction={
                previousStep ? (
                    <Button variant="secondary" size="sm" onClick={() => onStep(previousStep.id)}>
                        <ChevronLeft className="h-4 w-4" />
                        Back
                    </Button>
                ) : undefined
            }
            primaryAction={
                nextStep ? (
                    <Button size="sm" onClick={() => onStep(nextStep.id)}>
                        Save and continue
                        <ChevronRight className="h-4 w-4" />
                    </Button>
                ) : (
                    <Button size="sm" onClick={onPreview}>
                        <Eye className="h-4 w-4" />
                        Preview for creator
                    </Button>
                )
            }
        />
    );
}

function blockerForStep(pack: CampaignPack, step: StepId) {
    switch (step) {
        case "product":
            return "Add the campaign name and product.";
        case "references":
            return "Add at least one creative reference.";
        case "adaptation":
            return "Generate or edit the adapted hook and angle.";
        case "angles":
            return "Select one primary angle.";
        case "hooks":
            return "Select at least one hook.";
        case "script":
            return "Complete each required script block.";
        case "storyboard":
            return "Add at least three scenes.";
        case "cta":
            return "Add the primary CTA.";
        case "deliverables":
            return "Set video count and target duration.";
        case "review":
            return pack.status === "Draft"
                ? "Resolve readiness blockers before marking the pack ready."
                : "Review the creator-facing brief.";
    }
}
