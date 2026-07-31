import { RecommendationSection } from "./recommendation-section";
import type { UgcEvidenceSeekTarget } from "./review-video-panel";
import type {
    UgcRecommendation,
    UgcRecommendationAction,
    UgcReviewResult,
} from "../types/ugc-review";

export function RecommendationGroups({
    result,
    savedActions,
    busyRecommendationId,
    onSeek,
    onAction,
}: {
    result: Pick<
        UgcReviewResult,
        "fixFirst" | "improvements" | "confirmations" | "policyPackVersion"
    >;
    savedActions: Readonly<Record<string, UgcRecommendationAction>>;
    busyRecommendationId: string | null;
    onSeek: (target: UgcEvidenceSeekTarget) => void;
    onAction: (recommendation: UgcRecommendation, action: UgcRecommendationAction) => void;
}) {
    return (
        <>
            <RecommendationSection
                title="Fix first"
                description="High-value changes recommended before the intended use."
                recommendations={result.fixFirst}
                policyPackVersion={result.policyPackVersion}
                savedActions={savedActions}
                busyRecommendationId={busyRecommendationId}
                onSeek={onSeek}
                onAction={onAction}
            />
            <RecommendationSection
                title="Improve"
                description="Optional changes that could make the draft clearer or more useful."
                recommendations={result.improvements}
                policyPackVersion={result.policyPackVersion}
                savedActions={savedActions}
                busyRecommendationId={busyRecommendationId}
                onSeek={onSeek}
                onAction={onAction}
            />
            <RecommendationSection
                title="Confirm"
                description="Seller information or publish-time details that need confirmation."
                recommendations={result.confirmations}
                policyPackVersion={result.policyPackVersion}
                savedActions={savedActions}
                busyRecommendationId={busyRecommendationId}
                onSeek={onSeek}
                onAction={onAction}
            />
        </>
    );
}
