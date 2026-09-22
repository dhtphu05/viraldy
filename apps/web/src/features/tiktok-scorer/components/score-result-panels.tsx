import { CheckCircle2, ShieldCheck, Video } from "lucide-react";

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
        <SurfaceCard padding={compact ? "sm" : "lg"}>
            <div
                className={
                    compact ? "mx-auto max-w-[180px]" : "grid gap-5 md:grid-cols-[220px_1fr]"
                }
            >
                <div className="relative aspect-[9/16] overflow-hidden rounded-2xl border border-divider bg-surface-soft shadow-soft-card">
                    {mediaUrl ? (
                        <video
                            src={mediaUrl}
                            aria-label={`Preview of ${run.assetName}`}
                            className="h-full w-full object-cover"
                            controls={!compact}
                            muted={compact}
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
    return (
        <SurfaceCard
            variant={run.decision === "blocked" ? "critical" : "raised"}
            padding="lg"
            highlight
        >
            <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_auto]">
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
                    <h1 className="mt-3 text-2xl font-semibold text-text-primary">
                        {decisionTitle(run.decision)}
                    </h1>
                    <p className="mt-2 max-w-3xl text-sm text-text-secondary">
                        Structural diagnosis for {run.profile.label}. It does not predict
                        distribution or commercial performance.
                    </p>
                </div>
                <div className="min-w-40 rounded-2xl bg-surface-soft p-5 text-center">
                    <p className="text-xs font-medium uppercase text-text-tertiary">
                        Structural score
                    </p>
                    <p className="mt-1 text-4xl font-semibold tabular-nums text-text-primary">
                        {run.score === null ? "—" : Math.round(run.score)}
                    </p>
                    <p className="text-xs text-text-tertiary">out of 100</p>
                </div>
            </div>
            <dl className="mt-5 grid gap-3 border-t border-divider pt-5 sm:grid-cols-2 lg:grid-cols-5">
                <SummaryItem label="Mode" value={humanize(run.scoreMode)} />
                <SummaryItem label="Intended use" value={humanize(run.intendedUse)} />
                <SummaryItem
                    label="Profile"
                    value={run.profile.label}
                    hint={run.profile.reason ?? undefined}
                />
                <SummaryItem label="Paid-use rights" value={humanize(run.paidUseRightsStatus)} />
                <SummaryItem
                    label="Final paid readiness"
                    value={humanize(run.finalPaidReadiness)}
                />
            </dl>
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
            <SurfaceCard>
                <h2 className="font-semibold text-text-primary">Strengths to preserve</h2>
                {run.strengths.length ? (
                    <ul className="mt-3 space-y-2">
                        {run.strengths.map((strength) => (
                            <li
                                key={strength.code}
                                className="flex gap-2 text-sm text-text-secondary"
                            >
                                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-ok" />
                                <span>{strength.title}</span>
                            </li>
                        ))}
                    </ul>
                ) : (
                    <p className="mt-3 text-sm text-text-secondary">
                        No evidence-linked strength was returned.
                    </p>
                )}
            </SurfaceCard>
            <SurfaceCard variant={blockers.length ? "critical" : "plain"}>
                <h2 className="font-semibold text-text-primary">Hard blockers</h2>
                {blockers.length ? (
                    <div className="mt-3 space-y-2">
                        {blockers.map((finding) => (
                            <button
                                key={finding.id}
                                type="button"
                                onClick={() => onFinding?.(finding)}
                                className="w-full rounded-xl bg-destructive-soft p-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            >
                                <p className="font-medium text-text-primary">{finding.title}</p>
                                <p className="mt-1 text-sm text-text-secondary">{finding.reason}</p>
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
            <h2 className="text-xl font-semibold text-text-primary">Dimension breakdown</h2>
            <p className="mt-1 text-sm text-text-secondary">
                Not evaluated and insufficient evidence remain separate from a score of zero.
            </p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {dimensions.map((dimension) => (
                    <button
                        key={dimension.code}
                        type="button"
                        onClick={() => onOpen?.(dimension)}
                        className="rounded-2xl border border-control-border bg-surface p-4 text-left shadow-soft-card transition-colors hover:bg-surface-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                        <div className="flex items-start justify-between gap-3">
                            <h3 className="font-medium text-text-primary">{dimension.label}</h3>
                            <span className="text-xl font-semibold tabular-nums text-text-primary">
                                {dimension.score ?? "—"}
                            </span>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-2">
                            <StatusChip
                                tone={dimension.applicability === "applicable" ? "info" : "neutral"}
                            >
                                {humanize(dimension.applicability)}
                            </StatusChip>
                            <StatusChip
                                tone={dimension.evidenceStatus === "insufficient" ? "warn" : "ok"}
                            >
                                {humanize(dimension.evidenceStatus)} evidence
                            </StatusChip>
                        </div>
                        <p className="mt-3 text-sm text-text-secondary">{dimension.reason}</p>
                    </button>
                ))}
            </div>
        </section>
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
