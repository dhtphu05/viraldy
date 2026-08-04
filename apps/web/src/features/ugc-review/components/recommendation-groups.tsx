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
    const allRecommendations = [
        ...result.fixFirst,
        ...result.improvements,
        ...result.confirmations,
    ];
    const keep = allRecommendations.filter(
        (item) => item.taskKind === "keep" || item.taskKind === "do_not_change",
    );
    const confirmAtPublish = allRecommendations.filter(
        (item) => item.taskKind === "publish_ops_required",
    );
    const sellerInput = allRecommendations.filter(
        (item) => item.taskKind === "seller_input_required",
    );
    const optional = allRecommendations.filter(
        (item) =>
            item.priority === "optional_improvement" &&
            item.taskKind !== "publish_ops_required" &&
            item.taskKind !== "seller_input_required",
    );
    const fixBeforePosting = allRecommendations.filter(
        (item) =>
            item.priority === "fix_before_publish" &&
            item.taskKind !== "publish_ops_required" &&
            item.taskKind !== "seller_input_required",
    );

    return (
        <>
            <RecommendationSection
                title="Fix before posting"
                description="Video edit tasks that should be done before the draft is published."
                recommendations={fixBeforePosting}
                policyPackVersion={result.policyPackVersion}
                savedActions={savedActions}
                busyRecommendationId={busyRecommendationId}
                onSeek={onSeek}
                onAction={onAction}
            />
            <RecommendationSection
                title="Confirm at publish"
                description="Publish-time setup checks. These are operational tasks, not creative failures."
                recommendations={confirmAtPublish}
                policyPackVersion={result.policyPackVersion}
                savedActions={savedActions}
                busyRecommendationId={busyRecommendationId}
                onSeek={onSeek}
                onAction={onAction}
            />
            <RecommendationSection
                title="Seller input required"
                description="Decisions or approved copy the seller must provide before the task can be completed."
                recommendations={sellerInput}
                policyPackVersion={result.policyPackVersion}
                savedActions={savedActions}
                busyRecommendationId={busyRecommendationId}
                onSeek={onSeek}
                onAction={onAction}
            />
            <RecommendationSection
                title="Optional improvements"
                description="Non-blocking changes to consider after required posting work is complete."
                recommendations={optional}
                policyPackVersion={result.policyPackVersion}
                savedActions={savedActions}
                busyRecommendationId={busyRecommendationId}
                onSeek={onSeek}
                onAction={onAction}
            />
            <RecommendationSection
                title="Keep unchanged"
                description="Elements explicitly marked as safe to preserve."
                recommendations={keep}
                policyPackVersion={result.policyPackVersion}
                savedActions={savedActions}
                busyRecommendationId={busyRecommendationId}
                onSeek={onSeek}
                onAction={onAction}
            />
        </>
    );
}
