import { Check, ChevronDown, CircleSlash2, Clock3, Send, Sparkles } from "lucide-react";

import type { UgcEvidenceSeekTarget } from "./review-video-panel";
import { formatEvidenceTime } from "../lib/ugc-review-view-model";
import type { UgcRecommendation, UgcRecommendationAction } from "../types/ugc-review";
import { humanizeLabel } from "@/shared/lib/display";
import { Button } from "@/shared/ui/button";
import { ConfidenceBadge } from "@/shared/ui/confidence-badge";
import { StatusChip } from "@/shared/ui/status-chip";
import { SurfaceCard } from "@/shared/ui/surface-card";

export function RecommendationSection({
    title,
    description,
    recommendations,
    policyPackVersion,
    savedActions,
    busyRecommendationId,
    onSeek,
    onAction,
}: {
    title: string;
    description: string;
    recommendations: readonly UgcRecommendation[];
    policyPackVersion: string;
    savedActions: Readonly<Record<string, UgcRecommendationAction>>;
    busyRecommendationId: string | null;
    onSeek: (target: UgcEvidenceSeekTarget) => void;
    onAction: (recommendation: UgcRecommendation, action: UgcRecommendationAction) => void;
}) {
    return (
        <section aria-labelledby={`section-${title.toLowerCase().replaceAll(" ", "-")}`}>
            <div className="mb-3">
                <h2
                    id={`section-${title.toLowerCase().replaceAll(" ", "-")}`}
                    className="text-xl font-semibold text-text-primary"
                >
                    {title}
                </h2>
                <p className="mt-1 text-sm text-text-secondary">{description}</p>
            </div>
            {recommendations.length ? (
                <div className="space-y-4">
                    {recommendations.map((recommendation) => (
                        <RecommendationCard
                            key={recommendation.id}
                            recommendation={recommendation}
                            policyPackVersion={policyPackVersion}
                            savedAction={savedActions[recommendation.id]}
                            busy={busyRecommendationId === recommendation.id}
                            onSeek={onSeek}
                            onAction={(action) => onAction(recommendation, action)}
                        />
                    ))}
                </div>
            ) : (
                <SurfaceCard padding="md" className="text-sm text-text-secondary">
                    Nothing has been recommended in this section.
                </SurfaceCard>
            )}
        </section>
    );
}

function RecommendationCard({
    recommendation,
    policyPackVersion,
    savedAction,
    busy,
    onSeek,
    onAction,
}: {
    recommendation: UgcRecommendation;
    policyPackVersion: string;
    savedAction: UgcRecommendationAction | undefined;
    busy: boolean;
    onSeek: (target: UgcEvidenceSeekTarget) => void;
    onAction: (action: UgcRecommendationAction) => void;
}) {
    const timestamped = recommendation.evidence.filter(
        (item): item is typeof item & { startMs: number } => item.startMs !== null,
    );
    const canSend = recommendation.owner === "creator" || recommendation.owner === "editor";
    const canApply = recommendation.group !== "confirm";

    return (
        <SurfaceCard padding="lg" variant="outlined">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                        <StatusChip tone={recommendation.group === "fix_first" ? "warn" : "info"}>
                            {humanizeLabel(recommendation.fixType ?? recommendation.group)}
                        </StatusChip>
                        <StatusChip tone="neutral">Owner: {recommendation.owner}</StatusChip>
                        <ConfidenceBadge level={recommendation.confidence} />
                    </div>
                    <h3 className="mt-3 text-lg font-semibold text-text-primary">
                        {recommendation.title}
                    </h3>
                    <p className="mt-2 text-sm leading-6 text-text-secondary">
                        {recommendation.reason}
                    </p>
                </div>
                {savedAction && (
                    <StatusChip tone="ok">
                        <Check className="h-3 w-3" />
                        {actionReceipt(savedAction)}
                    </StatusChip>
                )}
            </div>

            {timestamped.length > 0 && (
                <div className="mt-4 flex flex-wrap gap-2">
                    {timestamped.map((evidence) => (
                        <button
                            key={evidence.id}
                            type="button"
                            onClick={() =>
                                onSeek({
                                    key: `${recommendation.id}:${evidence.id}`,
                                    startMs: evidence.startMs,
                                })
                            }
                            className="inline-flex min-h-9 items-center gap-1.5 rounded-full bg-info-soft px-3 text-xs font-medium text-info transition-colors duration-[180ms] hover:bg-info-soft/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        >
                            <Clock3 className="h-3 w-3" />
                            {formatEvidenceTime(evidence.startMs)} · {evidence.observed}
                        </button>
                    ))}
                </div>
            )}

            {recommendation.instructions.length > 0 && (
                <div className="mt-5 rounded-xl bg-surface-soft p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-text-tertiary">
                        What to do
                    </p>
                    <ol className="mt-2 space-y-2 text-sm text-text-primary">
                        {recommendation.instructions.map((instruction, index) => (
                            <li key={instruction} className="flex gap-2">
                                <span className="text-primary">{index + 1}.</span>
                                <span>{instruction}</span>
                            </li>
                        ))}
                    </ol>
                </div>
            )}

            <div className="mt-5 grid gap-4 md:grid-cols-2">
                {recommendation.strengthsToPreserve.length > 0 && (
                    <ListBlock
                        title="Keep unchanged"
                        items={recommendation.strengthsToPreserve}
                        tone="ok"
                    />
                )}
                {recommendation.completionCriteria.length > 0 && (
                    <ListBlock
                        title="Done when"
                        items={recommendation.completionCriteria}
                        tone="neutral"
                    />
                )}
            </div>

            <details className="group mt-5 border-t border-hairline pt-4">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-2 text-sm font-medium text-text-secondary">
                    Why Viraldy recommends this
                    <ChevronDown className="h-4 w-4 transition-transform duration-[180ms] group-open:rotate-180" />
                </summary>
                <div className="mt-3 space-y-2 text-sm text-text-secondary">
                    <p>{recommendation.whyItMatters}</p>
                    {(recommendation.ruleCode || policyPackVersion) && (
                        <p className="text-xs text-text-tertiary">
                            Review reference: {recommendation.ruleCode ?? "General guidance"} ·
                            guidance version {policyPackVersion}
                        </p>
                    )}
                    {recommendation.evidence.map((evidence) => (
                        <p key={evidence.id} className="rounded-lg bg-surface-soft px-3 py-2">
                            {evidence.observed} · {humanizeLabel(evidence.source)}
                        </p>
                    ))}
                </div>
            </details>

            <div className="mt-5 flex flex-wrap gap-2 border-t border-hairline pt-4">
                {canApply && (
                    <Button
                        type="button"
                        size="sm"
                        disabled={busy}
                        onClick={() => onAction("accepted")}
                    >
                        <Sparkles className="h-4 w-4" />
                        Apply recommendation
                    </Button>
                )}
                {canSend && (
                    <Button
                        type="button"
                        size="sm"
                        variant="secondary"
                        disabled={busy}
                        onClick={() => onAction("sent_to_creator")}
                    >
                        <Send className="h-4 w-4" />
                        Send to creator
                    </Button>
                )}
                <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    disabled={busy}
                    onClick={() => onAction("marked_completed")}
                >
                    <Check className="h-4 w-4" />
                    Mark completed
                </Button>
                <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    disabled={busy}
                    onClick={() => onAction("ignored")}
                >
                    Ignore for now
                </Button>
                <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    disabled={busy}
                    onClick={() => onAction("not_applicable")}
                >
                    <CircleSlash2 className="h-4 w-4" />
                    Not applicable
                </Button>
            </div>
        </SurfaceCard>
    );
}

function ListBlock({
    title,
    items,
    tone,
}: {
    title: string;
    items: readonly string[];
    tone: "ok" | "neutral";
}) {
    return (
        <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-text-tertiary">
                {title}
            </p>
            <ul className="mt-2 space-y-2 text-sm text-text-secondary">
                {items.map((item) => (
                    <li key={item} className="flex gap-2">
                        <span
                            className={
                                tone === "ok"
                                    ? "mt-2 h-1.5 w-1.5 bg-ok"
                                    : "mt-2 h-1.5 w-1.5 bg-primary"
                            }
                        />
                        <span>{item}</span>
                    </li>
                ))}
            </ul>
        </div>
    );
}

function actionReceipt(action: UgcRecommendationAction): string {
    const labels: Record<UgcRecommendationAction, string> = {
        accepted: "Applied",
        ignored: "Saved for later",
        not_applicable: "Not applicable",
        sent_to_creator: "Sent to creator",
        marked_completed: "Completed",
    };
    return labels[action];
}
