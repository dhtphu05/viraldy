import {
    AlertCircle,
    ArrowRight,
    CheckCircle2,
    PlayCircle,
    ShieldCheck,
    Sparkles,
    Video,
} from "lucide-react";

import type { TikTokDimension, TikTokFinding, TikTokScoreRun } from "../types";
import { ConfidenceBadge } from "@/shared/ui/confidence-badge";
import { StatusChip } from "@/shared/ui/status-chip";
import { SurfaceCard } from "@/shared/ui/surface-card";

export function ScoreVideoPreview({
    run,
    mediaUrl,
    compact = false,
}: {
    run: TikTokScoreRun;
    mediaUrl: string | null;
    compact?: boolean;
}) {
    const title = run.productName ? `${run.productName} video` : "TikTok video";
    return (
        <SurfaceCard
            padding={compact ? "sm" : "lg"}
            className="bg-surface shadow-[0_18px_44px_rgb(15_23_42_/_0.10),0_2px_8px_rgb(15_23_42_/_0.06)]"
        >
            <div
                className={
                    compact ? "mx-auto max-w-[180px]" : "grid gap-5 md:grid-cols-[220px_1fr]"
                }
            >
                <div className="relative aspect-[9/16] overflow-hidden rounded-2xl bg-surface-soft shadow-soft-card">
                    {mediaUrl ? (
                        <video
                            src={mediaUrl}
                            aria-label={`Preview of ${run.assetName}`}
                            className="h-full w-full object-cover"
                            controls
                            autoPlay
                            muted
                            loop
                            playsInline
                            preload="metadata"
                        />
                    ) : (
                        <div className="grid h-full w-full place-items-center bg-gradient-to-b from-primary-softer to-surface-soft text-primary">
                            <Video className={compact ? "h-8 w-8" : "h-10 w-10"} />
                        </div>
                    )}
                    <span className="absolute bottom-2 left-2 rounded-full bg-black/70 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-white">
                        TikTok 9:16
                    </span>
                </div>
                {!compact && (
                    <div className="flex flex-col justify-center">
                        <p className="text-xs font-semibold uppercase tracking-wide text-text-tertiary">
                            Video under review
                        </p>
                        <h1 className="mt-2 text-2xl font-semibold text-text-primary">{title}</h1>
                        <p className="mt-2 text-sm text-text-secondary">
                            Recommendations are grounded in this uploaded video and verified product
                            context. Filename stays as metadata, not the main object.
                        </p>
                        <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                            <SummaryItem label="File" value={run.assetName} />
                            <SummaryItem
                                label="Product"
                                value={run.productName ?? "No product selected"}
                            />
                            <SummaryItem label="Mode" value={humanize(run.scoreMode)} />
                            <SummaryItem label="Status" value={humanize(run.status)} />
                        </dl>
                    </div>
                )}
            </div>
        </SurfaceCard>
    );
}

export function DecisionSummary({ run }: { run: TikTokScoreRun }) {
    const blockers = run.findings.filter(
        (finding) => finding.severity === "hard" || finding.priority === "P0",
    );
    return (
        <SurfaceCard
            variant={run.decision === "blocked" ? "critical" : "raised"}
            padding="lg"
            highlight
            className="bg-surface shadow-[0_24px_56px_rgb(15_23_42_/_0.14),0_3px_10px_rgb(15_23_42_/_0.06)]"
        >
            <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_200px] lg:items-center">
                <div>
                    <div className="flex flex-wrap gap-2">
                        <StatusChip tone={decisionTone(run.decision)}>
                            {humanize(run.decision)}
                        </StatusChip>
                        <ConfidenceBadge
                            level={run.confidence}
                            rationale="Confidence reflects media and evidence coverage; it is not multiplied into the score."
                        />
                    </div>
                    <p className="mt-5 text-xs font-semibold uppercase tracking-[0.16em] text-text-tertiary">
                        Recommended decision
                    </p>
                    <h1 className="mt-2 max-w-3xl text-balance text-2xl font-semibold text-text-primary sm:text-3xl">
                        {decisionTitle(run.decision)}
                    </h1>
                    <p className="mt-3 max-w-3xl text-pretty text-sm leading-6 text-text-secondary">
                        Structural diagnosis for {run.profile.label}. It does not predict
                        distribution or commercial performance.
                    </p>
                    <div className="mt-5 grid gap-2 sm:grid-cols-3">
                        <ResultMetric label="Strengths" value={run.strengths.length} tone="ok" />
                        <ResultMetric label="Hard blockers" value={blockers.length} tone="risk" />
                        <ResultMetric
                            label="Required actions"
                            value={run.fixes.length}
                            tone="info"
                        />
                    </div>
                </div>
                <div className="mx-auto w-full max-w-[190px] rounded-3xl bg-surface p-4 text-center shadow-[0_12px_28px_rgb(15_23_42_/_0.12),0_2px_6px_rgb(15_23_42_/_0.05)]">
                    <div
                        className="mx-auto grid aspect-square w-32 place-items-center rounded-full p-2"
                        style={{
                            background: `conic-gradient(var(--color-primary) ${Math.max(0, Math.min(100, run.score ?? 0))}%, var(--color-surface-soft) 0)`,
                        }}
                    >
                        <div className="grid h-full w-full place-items-center rounded-full bg-surface">
                            <div>
                                <p className="text-4xl font-semibold tabular-nums text-text-primary">
                                    {run.score === null ? "—" : Math.round(run.score)}
                                </p>
                                <p className="text-xs text-text-tertiary">/ 100</p>
                            </div>
                        </div>
                    </div>
                    <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-text-tertiary">
                        Structural score
                    </p>
                </div>
            </div>
            <details className="group mt-6 bg-surface-soft/70 px-4 py-3 sm:rounded-2xl">
                <summary className="cursor-pointer list-none rounded text-sm font-semibold text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                    <span className="flex items-center justify-between gap-3">
                        Analysis context
                        <span className="text-xs font-medium text-text-tertiary group-open:hidden">
                            Show details
                        </span>
                        <span className="hidden text-xs font-medium text-text-tertiary group-open:inline">
                            Hide details
                        </span>
                    </span>
                </summary>
                <dl className="mt-4 grid gap-3 rounded-2xl bg-surface-soft p-4 sm:grid-cols-2 lg:grid-cols-5">
                    <SummaryItem label="Mode" value={humanize(run.scoreMode)} />
                    <SummaryItem label="Intended use" value={humanize(run.intendedUse)} />
                    <SummaryItem
                        label="Profile"
                        value={run.profile.label}
                        hint={run.profile.reason ?? undefined}
                    />
                    <SummaryItem
                        label="Paid-use rights"
                        value={humanize(run.paidUseRightsStatus)}
                    />
                    <SummaryItem
                        label="Final paid readiness"
                        value={humanize(run.finalPaidReadiness)}
                    />
                </dl>
            </details>
        </SurfaceCard>
    );
}

export function StrengthsAndBlockers({
    run,
    onFinding,
}: {
    run: TikTokScoreRun;
    onFinding?: (finding: TikTokFinding) => void;
}) {
    const blockers = run.findings.filter(
        (finding) => finding.severity === "hard" || finding.priority === "P0",
    );
    return (
        <div className="grid gap-5 lg:grid-cols-2">
            <SurfaceCard className="bg-surface shadow-[0_14px_34px_rgb(15_23_42_/_0.10),0_2px_7px_rgb(15_23_42_/_0.05)]">
                <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                        <span className="grid h-9 w-9 place-items-center rounded-full bg-ok-soft text-ok">
                            <Sparkles className="h-4 w-4" />
                        </span>
                        <div>
                            <p className="text-xs font-semibold uppercase tracking-wide text-ok">
                                Keep these
                            </p>
                            <h2 className="font-semibold text-text-primary">
                                Strengths to preserve
                            </h2>
                        </div>
                    </div>
                    <span className="text-2xl font-semibold tabular-nums text-ok">
                        {run.strengths.length}
                    </span>
                </div>
                {run.strengths.length ? (
                    <ul className="mt-4 space-y-2">
                        {run.strengths.map((strength) => (
                            <li
                                key={strength.code}
                                className="flex gap-3 rounded-xl bg-ok-soft/55 p-3 text-sm text-text-secondary"
                            >
                                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-ok" />
                                <span className="font-medium text-text-primary">
                                    {strength.title}
                                </span>
                            </li>
                        ))}
                    </ul>
                ) : (
                    <p className="mt-3 text-sm text-text-secondary">
                        No evidence-linked strength was returned.
                    </p>
                )}
            </SurfaceCard>
            <SurfaceCard
                variant={blockers.length ? "critical" : "plain"}
                className="shadow-[0_14px_34px_rgb(15_23_42_/_0.10),0_2px_7px_rgb(15_23_42_/_0.05)]"
            >
                <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                        <span className="grid h-9 w-9 place-items-center rounded-full bg-destructive-soft text-destructive">
                            <AlertCircle className="h-4 w-4" />
                        </span>
                        <div>
                            <p className="text-xs font-semibold uppercase tracking-wide text-destructive">
                                Fix first
                            </p>
                            <h2 className="font-semibold text-text-primary">Hard blockers</h2>
                        </div>
                    </div>
                    <span className="text-2xl font-semibold tabular-nums text-destructive">
                        {blockers.length}
                    </span>
                </div>
                {blockers.length ? (
                    <div className="mt-4 space-y-2">
                        {blockers.map((finding) => (
                            <button
                                key={finding.id}
                                type="button"
                                onClick={() => onFinding?.(finding)}
                                className="group w-full rounded-xl bg-destructive-soft p-3 text-left shadow-[0_1px_0_rgb(0_0_0_/_0.03)] transition-[background-color,transform,box-shadow] duration-150 hover:bg-destructive-soft/80 hover:shadow-soft-card active:scale-[0.99] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring motion-reduce:transform-none"
                            >
                                <div className="flex items-start justify-between gap-3">
                                    <div>
                                        <div className="flex flex-wrap gap-2">
                                            <StatusChip tone="destructive">
                                                {finding.priority}
                                            </StatusChip>
                                            {finding.targetTimeRangeMs && (
                                                <StatusChip tone="neutral">
                                                    {formatRange(finding.targetTimeRangeMs)}
                                                </StatusChip>
                                            )}
                                        </div>
                                        <p className="mt-2 font-medium text-text-primary">
                                            {finding.title}
                                        </p>
                                        <p className="mt-1 text-pretty text-sm leading-6 text-text-secondary">
                                            {finding.reason}
                                        </p>
                                    </div>
                                    <PlayCircle className="mt-1 h-5 w-5 shrink-0 text-destructive transition-transform duration-150 group-hover:translate-x-0.5 motion-reduce:transform-none" />
                                </div>
                            </button>
                        ))}
                    </div>
                ) : (
                    <p className="mt-3 flex items-center gap-2 text-sm text-text-secondary">
                        <ShieldCheck className="h-4 w-4 text-ok" />
                        No verified hard blocker was returned.
                    </p>
                )}
            </SurfaceCard>
        </div>
    );
}

export function Dimensions({
    dimensions,
    onOpen,
}: {
    dimensions: TikTokDimension[];
    onOpen?: (dimension: TikTokDimension) => void;
}) {
    return (
        <section>
            <div className="flex items-end justify-between gap-3">
                <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-text-tertiary">
                        Why this score
                    </p>
                    <h2 className="mt-1 text-xl font-semibold text-text-primary">
                        Dimension breakdown
                    </h2>
                </div>
                <StatusChip tone="neutral">{dimensions.length} dimensions</StatusChip>
            </div>
            <p className="mt-2 text-pretty text-sm text-text-secondary">
                Not evaluated and insufficient evidence remain separate from a score of zero.
            </p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {dimensions.map((dimension) => {
                    const score = Math.max(0, Math.min(100, dimension.score ?? 0));
                    return (
                        <article
                            key={dimension.code}
                            className="rounded-2xl bg-surface p-4 text-left shadow-[0_10px_24px_rgb(15_23_42_/_0.10),0_1px_4px_rgb(15_23_42_/_0.05)]"
                        >
                            <div className="flex items-start justify-between gap-3">
                                <h3 className="font-medium text-text-primary">{dimension.label}</h3>
                                <span className="text-2xl font-semibold tabular-nums text-text-primary">
                                    {dimension.score ?? "—"}
                                </span>
                            </div>
                            <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-surface-soft">
                                <div
                                    className="h-full rounded-full bg-primary"
                                    style={{ width: `${score}%` }}
                                />
                            </div>
                            <div className="mt-2 flex flex-wrap gap-2">
                                <StatusChip
                                    tone={
                                        dimension.applicability === "applicable"
                                            ? "info"
                                            : "neutral"
                                    }
                                >
                                    {humanize(dimension.applicability)}
                                </StatusChip>
                                <StatusChip
                                    tone={
                                        dimension.evidenceStatus === "insufficient" ? "warn" : "ok"
                                    }
                                >
                                    {humanize(dimension.evidenceStatus)} evidence
                                </StatusChip>
                            </div>
                            <p className="mt-3 text-pretty text-sm leading-6 text-text-secondary">
                                {dimension.reason}
                            </p>
                            {dimension.positiveSignals[0] && (
                                <p className="mt-3 flex gap-2 rounded-lg bg-ok-soft/60 p-2.5 text-xs leading-5 text-text-secondary">
                                    <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ok" />
                                    <span>{dimension.positiveSignals[0]}</span>
                                </p>
                            )}
                            {dimension.missingSignals[0] && (
                                <p className="mt-2 flex gap-2 rounded-lg bg-warn-soft/65 p-2.5 text-xs leading-5 text-text-secondary">
                                    <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-warn" />
                                    <span>{dimension.missingSignals[0]}</span>
                                </p>
                            )}
                            {(dimension.positiveSignals.length > 1 ||
                                dimension.missingSignals.length > 1 ||
                                dimension.uncertainty.length > 0) && (
                                <details className="group mt-3 rounded-xl bg-surface-soft px-3 py-2.5 text-xs">
                                    <summary className="cursor-pointer list-none font-semibold text-text-secondary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                                        More signals
                                    </summary>
                                    <ul className="mt-2 space-y-1.5 text-text-secondary">
                                        {dimension.positiveSignals.slice(1).map((signal) => (
                                            <li key={signal}>+ {signal}</li>
                                        ))}
                                        {dimension.missingSignals.slice(1).map((signal) => (
                                            <li key={signal}>− {signal}</li>
                                        ))}
                                        {dimension.uncertainty.map((item) => (
                                            <li key={item}>? {item}</li>
                                        ))}
                                    </ul>
                                </details>
                            )}
                            {onOpen && dimension.evidenceIds.length > 0 && (
                                <button
                                    type="button"
                                    onClick={() => onOpen(dimension)}
                                    className="mt-4 inline-flex min-h-10 items-center gap-2 rounded-lg px-2 text-sm font-semibold text-primary transition-colors duration-150 hover:bg-primary-softer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                                >
                                    Open evidence
                                    <ArrowRight className="h-4 w-4" />
                                </button>
                            )}
                        </article>
                    );
                })}
            </div>
        </section>
    );
}

function ResultMetric({
    label,
    value,
    tone,
}: {
    label: string;
    value: number;
    tone: "ok" | "risk" | "info";
}) {
    const toneClass =
        tone === "ok"
            ? "bg-ok-soft/60 text-ok"
            : tone === "risk"
              ? "bg-destructive-soft/60 text-destructive"
              : "bg-info-soft/60 text-info";
    return (
        <div className={`rounded-xl p-3 ${toneClass}`}>
            <p className="text-2xl font-semibold tabular-nums">{value}</p>
            <p className="text-xs font-medium text-text-secondary">{label}</p>
        </div>
    );
}

function SummaryItem({ label, value, hint }: { label: string; value: string; hint?: string }) {
    return (
        <div>
            <dt className="text-xs font-medium uppercase text-text-tertiary">{label}</dt>
            <dd className="mt-1 text-sm font-medium text-text-primary">{value}</dd>
            {hint && <p className="mt-1 text-xs text-text-secondary">{hint}</p>}
        </div>
    );
}

function humanize(value: string) {
    return value
        .replace(/_v\d+$/, "")
        .replace(/_/g, " ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function decisionTone(value: string) {
    return value === "blocked"
        ? ("destructive" as const)
        : value === "revise" || value === "request_better_media"
          ? ("warn" as const)
          : value === "structurally_ready"
            ? ("ok" as const)
            : ("info" as const);
}

function decisionTitle(value: string) {
    return value === "request_better_media"
        ? "Better media is needed before a responsible diagnosis"
        : value === "blocked"
          ? "Resolve verified blockers before publishing"
          : value === "revise"
            ? "Revise the required actions, then upload Draft 2"
            : value === "usable_with_improvements"
              ? "Usable structure with clear improvements available"
              : value === "structurally_ready"
                ? "Creative structure is ready for this context"
                : "Diagnosis pending";
}

function formatRange(range: [number, number]) {
    return `${formatMs(range[0])}–${formatMs(range[1])}`;
}

function formatMs(value: number) {
    const seconds = Math.max(0, Math.round(value / 1_000));
    return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}
