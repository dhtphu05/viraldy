import type {
    CreativeAnalysis,
    DnaEvidence,
    KcaItem,
} from "@/features/creative-library/types/creative";
import { StatusChip } from "@/shared/ui/status-chip";
import { Button } from "@/shared/ui/button";
import { ConfidenceBadge } from "@/shared/ui/confidence-badge";
import { DecisionHero } from "@/shared/ui/decision-hero";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { formatDuration } from "@/features/creative-library/lib/creative-visuals";
import { CheckCircle2, Eye, Package, RefreshCcw, ShieldAlert } from "lucide-react";
import { cn } from "@/shared/lib/utils";
import type { MetricTone } from "@/shared/types";
import { useState } from "react";

const decisionTone: Record<CreativeAnalysis["decision"], MetricTone> = {
    "Strong reference": "ok",
    "Useful with adaptation": "info",
    "Weak product fit": "warn",
    "Analyze before use": "neutral",
};

export function DecisionSummary({
    analysis,
    onAdapt,
    onReviewEvidence,
    linked,
}: {
    analysis: CreativeAnalysis;
    onAdapt: () => void;
    onReviewEvidence: () => void;
    linked?: string;
}) {
    return (
        <DecisionHero
            className="analysis-state-enter"
            eyebrow="Creative decision"
            actionLabel={analysis.decision}
            reason={
                <>
                    <p>{analysis.reason}</p>
                    <p className="mt-2 text-xs text-text-tertiary">
                        {linked ? `Linked to ${linked}` : "No product linked"} ·{" "}
                        {analysis.analysisType}
                    </p>
                </>
            }
            score={analysis.dnaScore}
            scoreLabel="Creative DNA score"
            confidence={analysis.confidence}
            effort={`${analysis.keep.length} reusable ${
                analysis.keep.length === 1 ? "mechanism" : "mechanisms"
            }`}
            statusTone={decisionTone[analysis.decision]}
            primaryAction={
                <Button onClick={onAdapt}>
                    <Package className="h-4 w-4" />
                    Adapt to product
                </Button>
            }
            secondaryAction={
                <Button variant="secondary" onClick={onReviewEvidence}>
                    <Eye className="h-4 w-4" />
                    Review evidence
                </Button>
            }
        />
    );
}

export function DnaElementSections({
    analysis,
    onJumpTo,
}: {
    analysis: CreativeAnalysis;
    onJumpTo?: (t: number) => void;
}) {
    return (
        <SurfaceCard padding="md">
            <h2 className="text-sm font-semibold text-text-primary">Creative DNA</h2>
            <div className="mt-2 divide-y divide-divider">
                {analysis.sections.map((sec) => (
                    <section key={sec.id} className="py-4 first:pt-2 last:pb-0">
                        <h3 className="text-[11px] font-semibold uppercase text-text-tertiary">
                            {sec.title}
                        </h3>
                        <ul className="mt-2 flex flex-col divide-y divide-divider">
                            {sec.elements.map((el) => (
                                <li
                                    key={el.id}
                                    className="flex flex-col gap-2 py-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4"
                                >
                                    <div className="min-w-0 flex-1">
                                        <div className="flex flex-wrap items-center gap-2">
                                            <p className="text-xs font-medium text-text-tertiary">
                                                {el.label}
                                            </p>
                                            {typeof el.timestamp === "number" && onJumpTo && (
                                                <button
                                                    type="button"
                                                    onClick={() => onJumpTo(el.timestamp!)}
                                                    className="min-h-6 tabular text-[11px] text-info hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                                                >
                                                    {formatDuration(el.timestamp)}
                                                </button>
                                            )}
                                        </div>
                                        <p className="mt-0.5 break-words text-sm text-text-primary">
                                            {el.value}
                                        </p>
                                        {typeof el.score === "number" && (
                                            <div className="mt-1.5 h-1 w-full max-w-xs overflow-hidden rounded-full bg-surface-muted">
                                                <div
                                                    className={cn(
                                                        "analysis-score-fill h-full rounded-full",
                                                        el.tone === "warn"
                                                            ? "bg-warn"
                                                            : el.tone === "destructive"
                                                              ? "bg-destructive"
                                                              : "bg-ok",
                                                    )}
                                                    style={{ width: `${el.score}%` }}
                                                />
                                            </div>
                                        )}
                                    </div>
                                    {el.tone && el.tone !== "neutral" && (
                                        <StatusChip
                                            tone={el.tone as MetricTone}
                                            className="self-start sm:shrink-0"
                                        >
                                            {el.tone === "ok"
                                                ? "Strong"
                                                : el.tone === "warn"
                                                  ? "Weak"
                                                  : el.tone === "info"
                                                    ? "Note"
                                                    : "Risk"}
                                        </StatusChip>
                                    )}
                                </li>
                            ))}
                        </ul>
                    </section>
                ))}
            </div>
        </SurfaceCard>
    );
}

export function EvidenceList({
    evidence,
    activeId,
    onJump,
    onMarkUseful,
    onAddNote,
    usefulIds,
}: {
    evidence: DnaEvidence[];
    activeId?: string;
    onJump: (t: number) => void;
    onMarkUseful: (id: string) => void;
    onAddNote: (e: DnaEvidence) => void;
    usefulIds: string[];
}) {
    return (
        <SurfaceCard padding="md">
            <h2 className="text-sm font-semibold text-text-primary">Evidence</h2>
            <ul className="mt-2 flex flex-col divide-y divide-divider">
                {evidence.map((e) => {
                    const useful = usefulIds.includes(e.id);
                    return (
                        <li
                            key={e.id}
                            id={`evidence-${e.id}`}
                            className={cn(
                                "scroll-mt-4 px-1 py-4 transition-colors first:pt-2 last:pb-1",
                                activeId === e.id
                                    ? "rounded-md bg-primary-softer px-3 ring-2 ring-inset ring-primary"
                                    : "bg-transparent",
                            )}
                        >
                            <div className="flex items-start justify-between gap-2">
                                <div className="min-w-0">
                                    <p className="text-sm font-medium text-text-primary">
                                        {e.title}
                                    </p>
                                    {typeof e.timestamp === "number" && (
                                        <button
                                            type="button"
                                            onClick={() => onJump(e.timestamp!)}
                                            className="min-h-6 tabular text-[11px] text-info hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                                        >
                                            Jump to {formatDuration(e.timestamp)}
                                        </button>
                                    )}
                                </div>
                                <ConfidenceBadge level={e.confidence} />
                            </div>
                            <p className="mt-1.5 text-xs text-text-secondary">{e.detail}</p>
                            <p className="mt-2 text-xs text-text-primary">
                                <span className="font-medium">Action:</span> {e.action}
                            </p>
                            <div className="mt-3 flex flex-wrap gap-1">
                                <Button
                                    variant={useful ? "secondary" : "ghost"}
                                    size="sm"
                                    className="h-8 px-2 text-[11px]"
                                    onClick={() => onMarkUseful(e.id)}
                                >
                                    <CheckCircle2 className="h-3 w-3" />
                                    {useful ? "Marked useful" : "Mark useful"}
                                </Button>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-8 whitespace-normal px-2 text-left text-[11px]"
                                    onClick={() => onAddNote(e)}
                                >
                                    Add to adaptation notes
                                </Button>
                            </div>
                        </li>
                    );
                })}
            </ul>
        </SurfaceCard>
    );
}

export function KcaPanel({
    keep,
    change,
    avoid,
}: {
    keep: KcaItem[];
    change: KcaItem[];
    avoid: KcaItem[];
}) {
    return (
        <SurfaceCard padding="md">
            <h2 className="text-sm font-semibold text-text-primary">Keep · Change · Avoid</h2>
            <div className="mt-3 grid gap-5 sm:grid-cols-3">
                <KcaColumn title="Keep" tone="ok" items={keep} />
                <KcaColumn title="Change" tone="info" items={change} />
                <KcaColumn title="Avoid copying" tone="destructive" items={avoid} />
            </div>
        </SurfaceCard>
    );
}

function KcaColumn({ title, tone, items }: { title: string; tone: MetricTone; items: KcaItem[] }) {
    return (
        <div>
            <StatusChip tone={tone} dot>
                {title}
            </StatusChip>
            <ul className="mt-2 flex flex-col divide-y divide-divider">
                {items.map((it) => (
                    <li key={it.id} className="py-2.5">
                        <p className="text-sm font-medium text-text-primary">{it.label}</p>
                        <p className="mt-0.5 text-xs text-text-secondary">{it.detail}</p>
                    </li>
                ))}
            </ul>
        </div>
    );
}

export function TranscriptList({
    items,
    onJump,
}: {
    items: { at: number; text: string }[];
    onJump: (t: number) => void;
}) {
    const [expanded, setExpanded] = useState(false);
    const isLong = items.length > 6;
    const visibleItems = isLong && !expanded ? items.slice(0, 6) : items;

    return (
        <SurfaceCard padding="md">
            <div className="flex items-center justify-between gap-3">
                <h2 className="text-sm font-semibold text-text-primary">Transcript</h2>
                {isLong && (
                    <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setExpanded((value) => !value)}
                    >
                        {expanded ? "Collapse" : `Show all ${items.length}`}
                    </Button>
                )}
            </div>
            <ol className="mt-2 flex flex-col divide-y divide-divider">
                {visibleItems.map((t, i) => (
                    <li key={i} className="grid grid-cols-[64px_1fr] items-start gap-3 py-2">
                        <button
                            type="button"
                            onClick={() => onJump(t.at)}
                            className="min-h-6 tabular text-left text-xs text-info hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        >
                            {formatDuration(t.at)}
                        </button>
                        <p className="text-sm text-text-primary">{t.text}</p>
                    </li>
                ))}
            </ol>
        </SurfaceCard>
    );
}

export function FailedState({ onRetry }: { onRetry: () => void }) {
    return (
        <SurfaceCard
            variant="critical"
            padding="lg"
            className="flex flex-col items-center gap-3 text-center"
        >
            <div className="grid h-11 w-11 place-items-center rounded-full bg-destructive-soft text-destructive">
                <ShieldAlert className="h-5 w-5" />
            </div>
            <div>
                <p className="text-sm font-medium text-text-primary">Analysis failed</p>
                <p className="mt-1 max-w-sm text-sm text-text-secondary">
                    We couldn't complete analysis for this reference. Retry to try again — nothing
                    was persisted.
                </p>
            </div>
            <Button variant="secondary" size="sm" onClick={onRetry}>
                <RefreshCcw className="h-4 w-4" />
                Retry analysis
            </Button>
        </SurfaceCard>
    );
}
