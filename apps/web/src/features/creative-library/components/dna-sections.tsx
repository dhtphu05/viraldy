import type {
    CreativeAnalysis,
    DnaEvidence,
    KcaItem,
} from "@/features/creative-library/types/creative";
import { StatusChip } from "@/shared/ui/status-chip";
import { Button } from "@/shared/ui/button";
import { SurfaceCard } from "@/shared/ui/surface-card";
import { formatDuration } from "@/features/creative-library/lib/creative-visuals";
import { CheckCircle2, RefreshCcw, ShieldAlert, Bookmark } from "lucide-react";
import { cn } from "@/shared/lib/utils";
import type { MetricTone } from "@/shared/types";

const decisionTone: Record<CreativeAnalysis["decision"], MetricTone> = {
    "Strong reference": "ok",
    "Useful with adaptation": "info",
    "Weak product fit": "warn",
    "Analyze before use": "neutral",
};

export function DecisionSummary({
    analysis,
    onAdapt,
    linked,
}: {
    analysis: CreativeAnalysis;
    onAdapt: () => void;
    linked?: string;
}) {
    return (
        <SurfaceCard padding="lg" className="analysis-state-enter flex flex-col gap-4">
            <div className="flex flex-wrap items-center gap-2">
                <StatusChip tone={decisionTone[analysis.decision]} dot>
                    {analysis.decision}
                </StatusChip>
                <StatusChip tone="neutral">Confidence: {analysis.confidence}</StatusChip>
                <StatusChip tone="neutral">{analysis.analysisType}</StatusChip>
                <StatusChip tone={linked ? "ok" : "neutral"}>
                    {linked ? `Linked to ${linked}` : "No product linked"}
                </StatusChip>
            </div>
            <div>
                <p className="text-sm leading-relaxed text-text-primary">{analysis.reason}</p>
            </div>
            <div className="flex flex-wrap items-end justify-between gap-4">
                <div>
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-text-tertiary">
                        Creative DNA Score
                    </p>
                    <p className="mt-1 flex items-baseline gap-2">
                        <span className="tabular text-3xl font-semibold text-text-primary">
                            {analysis.dnaScore}
                        </span>
                        <span className="text-xs text-text-tertiary">/ 100</span>
                    </p>
                </div>
                <Button onClick={onAdapt}>
                    <Bookmark className="h-4 w-4" />
                    Adapt to product
                </Button>
            </div>
        </SurfaceCard>
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
        <div className="flex flex-col gap-4">
            {analysis.sections.map((sec) => (
                <SurfaceCard key={sec.id} padding="md">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-text-tertiary">
                        {sec.title}
                    </p>
                    <ul className="mt-3 flex flex-col divide-y divide-hairline/60">
                        {sec.elements.map((el) => (
                            <li
                                key={el.id}
                                className="flex items-start justify-between gap-4 py-2.5"
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
                                                className="tabular text-[10px] text-info hover:underline"
                                            >
                                                {formatDuration(el.timestamp)}
                                            </button>
                                        )}
                                    </div>
                                    <p className="mt-0.5 truncate text-sm text-text-primary">
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
                                    <StatusChip tone={el.tone as MetricTone}>
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
                </SurfaceCard>
            ))}
        </div>
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
            <p className="text-[10px] font-semibold uppercase tracking-wider text-text-tertiary">
                Evidence
            </p>
            <ul className="mt-3 flex flex-col gap-2.5">
                {evidence.map((e) => {
                    const useful = usefulIds.includes(e.id);
                    return (
                        <li
                            key={e.id}
                            id={`evidence-${e.id}`}
                            className={cn(
                                "rounded-md border p-3 transition-colors",
                                activeId === e.id
                                    ? "border-primary bg-primary-softer"
                                    : "border-hairline/60 bg-surface-soft/40",
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
                                            className="tabular text-[11px] text-info hover:underline"
                                        >
                                            Jump to {formatDuration(e.timestamp)}
                                        </button>
                                    )}
                                </div>
                                <StatusChip
                                    tone={
                                        e.confidence === "High"
                                            ? "ok"
                                            : e.confidence === "Medium"
                                              ? "info"
                                              : "warn"
                                    }
                                >
                                    {e.confidence}
                                </StatusChip>
                            </div>
                            <p className="mt-1.5 text-xs text-text-secondary">{e.detail}</p>
                            <p className="mt-2 text-xs text-text-primary">
                                <span className="font-medium">Action:</span> {e.action}
                            </p>
                            <div className="mt-2 flex gap-1">
                                <Button
                                    variant={useful ? "default" : "ghost"}
                                    size="sm"
                                    className="h-7 px-2 text-[11px]"
                                    onClick={() => onMarkUseful(e.id)}
                                >
                                    <CheckCircle2 className="h-3 w-3" />
                                    {useful ? "Marked useful" : "Mark useful"}
                                </Button>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-7 px-2 text-[11px]"
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
            <p className="text-[10px] font-semibold uppercase tracking-wider text-text-tertiary">
                Keep · Change · Avoid
            </p>
            <div className="mt-3 grid gap-4 sm:grid-cols-3">
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
            <ul className="mt-2 flex flex-col gap-2">
                {items.map((it) => (
                    <li
                        key={it.id}
                        className={cn(
                            "rounded-md px-3 py-2",
                            tone === "ok" && "bg-ok-soft/60",
                            tone === "info" && "bg-info-soft/60",
                            tone === "warn" && "bg-warn-soft/60",
                            tone === "destructive" && "bg-destructive-soft/60",
                            tone === "neutral" && "bg-surface-soft",
                        )}
                    >
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
    return (
        <SurfaceCard padding="md">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-text-tertiary">
                Transcript
            </p>
            <ol className="mt-3 flex flex-col divide-y divide-hairline/60">
                {items.map((t, i) => (
                    <li key={i} className="grid grid-cols-[64px_1fr] items-start gap-3 py-2">
                        <button
                            type="button"
                            onClick={() => onJump(t.at)}
                            className="tabular text-left text-xs text-info hover:underline"
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
        <SurfaceCard padding="lg" className="flex flex-col items-center gap-3 text-center">
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
