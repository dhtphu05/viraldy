import {
    Check,
    CheckCircle2,
    Clock3,
    ExternalLink,
    MessageSquareText,
    Scissors,
    Send,
    UserRound,
    Video,
} from "lucide-react";

import { groupFixActions } from "../lib/tiktok-score-view-model";
import type { FixEventType, TikTokFixAction } from "../types";
import { Button } from "@/shared/ui/button";
import { EmptyState } from "@/shared/ui/empty-state";
import { StatusChip } from "@/shared/ui/status-chip";
import { SurfaceCard } from "@/shared/ui/surface-card";

export function FixPlan({
    actions,
    busyFixId,
    onSeek,
    onEvent,
}: {
    actions: TikTokFixAction[];
    busyFixId: string | null;
    onSeek: (fix: TikTokFixAction) => void;
    onEvent: (fix: TikTokFixAction, event: FixEventType) => void;
}) {
    if (!actions.length) {
        return (
            <SurfaceCard padding="lg">
                <EmptyState
                    icon={CheckCircle2}
                    tone="success"
                    title="No required fix actions"
                    description="The server did not return a required edit, reshoot, seller confirmation, or better-media action."
                />
            </SurfaceCard>
        );
    }
    return (
        <section aria-labelledby="fix-plan-title">
            <div>
                <h2 id="fix-plan-title" className="text-xl font-semibold text-text-primary">
                    Detailed fix plan
                </h2>
                <p className="mt-1 text-sm text-text-secondary">
                    Start with the least expensive valid repair path. P0 and P1 actions carry the
                    strongest priority.
                </p>
            </div>
            <div className="mt-4 space-y-6">
                {groupFixActions(actions)
                    .filter((group) => group.actions.length)
                    .map((group) => (
                        <section key={group.key} aria-labelledby={`fix-group-${group.key}`}>
                            <div className="mb-3">
                                <h3
                                    id={`fix-group-${group.key}`}
                                    className="font-semibold text-text-primary"
                                >
                                    {group.title}
                                </h3>
                                <p className="text-sm text-text-secondary">{group.description}</p>
                            </div>
                            <div className="space-y-3">
                                {group.actions.map((action) => (
                                    <FixCard
                                        key={action.id}
                                        action={action}
                                        busy={busyFixId === action.id}
                                        onSeek={() => onSeek(action)}
                                        onEvent={(event) => onEvent(action, event)}
                                    />
                                ))}
                            </div>
                        </section>
                    ))}
            </div>
        </section>
    );
}

function FixCard({
    action,
    busy,
    onSeek,
    onEvent,
}: {
    action: TikTokFixAction;
    busy: boolean;
    onSeek: () => void;
    onEvent: (event: FixEventType) => void;
}) {
    const strong =
        action.priority === "P0" || action.priority === "P1" || action.severity === "hard";
    return (
        <SurfaceCard variant={strong ? "critical" : "plain"} padding="lg">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap gap-2">
                        <StatusChip tone={action.priority === "P0" ? "destructive" : "warn"}>
                            {action.priority}
                        </StatusChip>
                        <StatusChip tone={action.severity === "hard" ? "destructive" : "warn"}>
                            {humanize(action.severity)} severity
                        </StatusChip>
                        <StatusChip tone="info">
                            <UserRound className="h-3 w-3" />
                            {humanize(action.ownerRole)}
                        </StatusChip>
                        <StatusChip tone="neutral">
                            <Clock3 className="h-3 w-3" />
                            {humanize(action.effort)} effort
                        </StatusChip>
                        <StatusChip tone={action.reshootRequired ? "warn" : "ok"}>
                            {action.reshootRequired ? "Reshoot required" : humanize(action.fixType)}
                        </StatusChip>
                    </div>
                    <h4 className="mt-3 text-base font-semibold text-text-primary">
                        {action.title}
                    </h4>
                    <p className="mt-1 text-sm text-text-secondary">{action.whyItMatters}</p>
                </div>
                {action.targetTimeRangeMs && (
                    <Button type="button" size="sm" variant="secondary" onClick={onSeek}>
                        <Video className="h-4 w-4" />
                        View {formatRange(action.targetTimeRangeMs)}
                    </Button>
                )}
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-2">
                <ValuePanel label="Expected" value={action.expected} tone="ok" />
                <ValuePanel label="Observed" value={action.observed} tone="warn" />
            </div>

            <div className="mt-4 grid gap-4 lg:grid-cols-2">
                <ListBlock
                    title="Exact instructions"
                    items={action.instructions}
                    icon={Scissors}
                    empty="No detailed instruction was supplied."
                />
                <ListBlock
                    title="Completion criteria"
                    items={action.completionCriteria}
                    icon={Check}
                    empty="No completion criteria were supplied."
                />
                <ListBlock
                    title="Strengths to preserve"
                    items={action.strengthsToPreserve}
                    icon={CheckCircle2}
                    empty="No specific strength was linked to this action."
                />
                <ListBlock
                    title="Required inputs"
                    items={action.requiredInputs}
                    icon={MessageSquareText}
                    empty="No additional seller input is required."
                />
            </div>

            <div className="mt-4 rounded-xl bg-surface-soft p-3 text-sm">
                <p className="text-xs font-medium uppercase text-text-tertiary">
                    Verification method
                </p>
                <p className="mt-1 text-text-primary">{action.verificationMethod}</p>
                <p className="mt-2 text-xs text-text-tertiary">
                    Evidence references: {action.evidenceIds.length || "None supplied"}
                </p>
            </div>

            <details className="mt-3 text-xs text-text-tertiary">
                <summary className="cursor-pointer rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                    Technical details
                </summary>
                <p className="mt-2">Action code: {action.code || "Unavailable"}</p>
                <p>Source finding: {action.sourceFindingCode || "Unavailable"}</p>
                <p>Operations: {action.operations.length || "None supplied"}</p>
            </details>

            <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-divider pt-4">
                <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    disabled={busy}
                    onClick={() => onEvent("accepted")}
                >
                    <Check className="h-4 w-4" />
                    Accept
                </Button>
                <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    disabled={busy}
                    onClick={() => onEvent("rejected")}
                >
                    Reject
                </Button>
                <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    disabled={busy}
                    onClick={() => onEvent("sent_to_creator")}
                >
                    <Send className="h-4 w-4" />
                    Send to creator
                </Button>
                <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    disabled={busy}
                    onClick={() => onEvent("sent_to_editor")}
                >
                    <ExternalLink className="h-4 w-4" />
                    Send to editor
                </Button>
                <Button
                    type="button"
                    size="sm"
                    disabled={busy}
                    onClick={() => onEvent("marked_completed")}
                >
                    <CheckCircle2 className="h-4 w-4" />
                    Mark completed
                </Button>
                {action.latestEvent && (
                    <StatusChip tone="info" className="ml-auto">
                        Current state: {humanize(action.latestEvent)}
                    </StatusChip>
                )}
            </div>
        </SurfaceCard>
    );
}

function ValuePanel({
    label,
    value,
    tone,
}: {
    label: string;
    value: Record<string, unknown>;
    tone: "ok" | "warn";
}) {
    const entries = Object.entries(value);
    return (
        <div
            className={tone === "ok" ? "rounded-xl bg-ok-soft p-3" : "rounded-xl bg-warn-soft p-3"}
        >
            <p className="text-xs font-medium uppercase text-text-tertiary">{label}</p>
            {entries.length ? (
                <dl className="mt-2 space-y-1">
                    {entries.map(([key, item]) => (
                        <div
                            key={key}
                            className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)] gap-2 text-sm"
                        >
                            <dt className="text-text-secondary">{humanize(key)}</dt>
                            <dd className="break-words text-text-primary">{formatValue(item)}</dd>
                        </div>
                    ))}
                </dl>
            ) : (
                <p className="mt-1 text-sm text-text-secondary">Not supplied</p>
            )}
        </div>
    );
}

function ListBlock({
    title,
    items,
    icon: Icon,
    empty,
}: {
    title: string;
    items: string[];
    icon: typeof Scissors;
    empty: string;
}) {
    return (
        <div>
            <p className="flex items-center gap-2 text-sm font-medium text-text-primary">
                <Icon className="h-4 w-4 text-primary" />
                {title}
            </p>
            {items.length ? (
                <ul className="mt-2 space-y-1.5 text-sm text-text-secondary">
                    {items.map((item, index) => (
                        <li key={`${item}-${index}`} className="flex gap-2">
                            <span aria-hidden>•</span>
                            <span>{item}</span>
                        </li>
                    ))}
                </ul>
            ) : (
                <p className="mt-2 text-sm text-text-tertiary">{empty}</p>
            )}
        </div>
    );
}
function formatRange(value: [number, number]) {
    return `${formatMs(value[0])}–${formatMs(value[1])}`;
}
function formatMs(ms: number) {
    const seconds = Math.max(0, Math.floor(ms / 1_000));
    return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}
function formatValue(value: unknown): string {
    if (value === null || value === undefined || value === "") return "Not supplied";
    if (Array.isArray(value)) return value.map(formatValue).join(", ");
    if (typeof value === "object")
        return Object.entries(value as Record<string, unknown>)
            .map(([key, item]) => `${humanize(key)}: ${formatValue(item)}`)
            .join("; ");
    return String(value);
}
function humanize(value: string) {
    return value
        .replace(/_v\d+$/, "")
        .replace(/_/g, " ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
