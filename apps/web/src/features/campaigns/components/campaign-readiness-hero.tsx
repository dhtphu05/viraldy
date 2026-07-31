import { Button } from "@/shared/ui/button";
import { DecisionHero } from "@/shared/ui/decision-hero";
import type { CampaignReadiness } from "@/features/campaigns/lib/campaignReadiness";
import type { StepId } from "@/features/campaigns/types/campaign";

export function CampaignReadinessHero({
    readiness,
    onContinue,
    onPreview,
}: {
    readiness: CampaignReadiness;
    onContinue: (step: StepId) => void;
    onPreview: () => void;
}) {
    const creatorReady = readiness.lifecycle === "creator_ready";
    const readyForReview = readiness.lifecycle === "ready_for_review";
    const blocker = readiness.hardBlockers[0];
    const reason = creatorReady
        ? "The approved Campaign Pack is ready to share with a creator."
        : readyForReview
          ? "Required content and coherence checks passed. Review the creator-facing version before approval."
          : (blocker?.label ??
            "Complete the required Campaign Pack sections before creator review.");
    const statusTone = creatorReady
        ? "ok"
        : readyForReview
          ? "info"
          : readiness.hardBlockers.length > 0
            ? "warn"
            : "neutral";

    return (
        <DecisionHero
            eyebrow="Campaign readiness"
            actionLabel={
                creatorReady
                    ? "CREATOR-READY"
                    : readyForReview
                      ? "READY TO REVIEW"
                      : "ACTION REQUIRED"
            }
            reason={reason}
            score={`${readiness.completionPercent}% complete`}
            scoreLabel="Campaign Pack"
            blockerCount={readiness.hardBlockers.length}
            statusTone={statusTone}
            primaryAction={
                creatorReady ? (
                    <Button onClick={onPreview}>Preview for creator</Button>
                ) : readiness.nextAction.step ? (
                    <Button onClick={() => onContinue(readiness.nextAction.step!)}>
                        {readiness.nextAction.label}
                    </Button>
                ) : undefined
            }
        />
    );
}
