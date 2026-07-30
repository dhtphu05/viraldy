import { Button } from "@/shared/ui/button";
import { DecisionHero } from "@/shared/ui/decision-hero";
import {
    STEPS,
    completionPercent,
    stepIsComplete,
    type ReadinessState,
} from "@/features/campaigns/lib/campaignSteps";
import type { CampaignPack, StepId } from "@/features/campaigns/types/campaign";

export function CampaignReadinessHero({
    pack,
    state,
    reasons,
    onContinue,
    onPreview,
}: {
    pack: CampaignPack;
    state: ReadinessState;
    reasons: string[];
    onContinue: (step: StepId) => void;
    onPreview: () => void;
}) {
    const nextIncomplete = STEPS.find((step) => !stepIsComplete(pack, step.id));
    const creatorReady = state === "Creator-ready";
    const missingAngle = !pack.primaryAngleId;
    const missingHooks = pack.selectedHookIds.length === 0;
    const reason = creatorReady
        ? "All required Campaign Pack sections are complete."
        : nextIncomplete?.id === "angles" && missingAngle && missingHooks
          ? "Select a primary angle and at least one hook before creator preview."
          : nextIncomplete?.id === "angles" && missingAngle
            ? "Select the primary creative angle before continuing."
            : nextIncomplete?.id === "hooks" && missingHooks
              ? "Select at least one hook before continuing."
              : reasons[0]
                ? `${reasons[0].replace(/^Missing:\s*/, "Complete ")} before creator preview.`
                : "Continue editing to complete the creator brief.";
    const statusTone =
        state === "Creator-ready"
            ? "ok"
            : state === "Needs review"
              ? "warn"
              : state === "Blocked"
                ? "destructive"
                : "neutral";

    return (
        <DecisionHero
            eyebrow="Campaign readiness"
            actionLabel={creatorReady ? "READY FOR CREATOR" : "CONTINUE CAMPAIGN PACK"}
            reason={reason}
            score={`${completionPercent(pack)}% complete`}
            scoreLabel="Campaign Pack"
            blockerCount={creatorReady ? 0 : reasons.length}
            statusTone={statusTone}
            primaryAction={
                creatorReady ? (
                    <Button onClick={onPreview}>Preview for creator</Button>
                ) : nextIncomplete ? (
                    <Button onClick={() => onContinue(nextIncomplete.id)}>
                        Continue: {nextIncomplete.label}
                    </Button>
                ) : undefined
            }
        />
    );
}
