import { ArrowRight, Check, Loader2, RefreshCw, ShieldAlert } from "lucide-react";

import type { PatternInstruction, PatternKitDetail } from "@/features/mvp-flow/intelligence-types";
import { Button } from "@/shared/ui/button";
import { StatusChip } from "@/shared/ui/status-chip";
import { humanizeLabel } from "@/shared/lib/display";

export function PatternKitResult({
    detail,
    onContinue,
    continueDisabled = false,
    continuePending = false,
}: {
    detail: PatternKitDetail;
    onContinue: () => void;
    continueDisabled?: boolean;
    continuePending?: boolean;
}) {
    const pattern = detail.latest_version.pattern;
    const grouped = pattern.adaptation_instructions.reduce<
        Partial<Record<PatternInstruction["instruction_type"], PatternInstruction[]>>
    >((groups, instruction) => {
        const current = groups[instruction.instruction_type] ?? [];
        return {
            ...groups,
            [instruction.instruction_type]: [...current, instruction],
        };
    }, {});

    return (
        <div className="flex flex-col gap-5">
            <div className="rounded-2xl bg-gradient-to-br from-primary-soft/80 via-surface to-info-soft/50 p-4 shadow-[0_14px_34px_rgba(15,23,42,0.07)] sm:p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">
                            Reusable mechanism
                        </p>
                        <h3 className="mt-1 text-lg font-semibold text-text-primary">
                            {pattern.name}
                        </h3>
                        <p className="mt-2 max-w-3xl text-sm leading-6 text-text-secondary">
                            {pattern.summary}
                        </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <StatusChip tone="neutral">
                            {pattern.source.source_asset_count} source
                            {pattern.source.source_asset_count === 1 ? "" : "s"}
                        </StatusChip>
                        <StatusChip
                            tone={
                                pattern.performance_summary.evidence_status === "supported"
                                    ? "ok"
                                    : "neutral"
                            }
                        >
                            {humanizeLabel(pattern.performance_summary.evidence_status)} evidence
                        </StatusChip>
                        <StatusChip tone="info">
                            {humanizeLabel(pattern.overall_confidence)} confidence
                        </StatusChip>
                    </div>
                </div>
            </div>

            <section aria-labelledby="pattern-sequence-heading">
                <h4
                    id="pattern-sequence-heading"
                    className="text-sm font-semibold text-text-primary"
                >
                    Sequence timeline
                </h4>
                <ol className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                    {pattern.sequence.map((beat, index) => (
                        <li
                            key={beat.beat_id}
                            className="min-w-0 rounded-2xl bg-surface/95 p-3 shadow-[0_7px_20px_rgba(15,23,42,0.07)]"
                        >
                            <div className="flex items-center justify-between gap-2">
                                <span className="flex min-w-0 items-center gap-2 text-xs font-semibold text-primary">
                                    <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-primary-soft text-primary-active">
                                        {index + 1}
                                    </span>
                                    <span className="truncate">
                                        {humanizeLabel(beat.beat_type)}
                                    </span>
                                </span>
                                <span className="text-[11px] text-text-tertiary">
                                    {formatBeatTiming(
                                        beat.recommended_start_ms_min,
                                        beat.recommended_start_ms_max,
                                    )}
                                </span>
                            </div>
                            <p className="mt-2 text-sm leading-5 text-text-secondary">
                                {beat.purpose}
                            </p>
                        </li>
                    ))}
                </ol>
            </section>

            <div className="grid gap-4 lg:grid-cols-2">
                <ApplicabilityBlock
                    title="Why it may fit"
                    values={[
                        ...pattern.applicability.suitable_categories,
                        ...pattern.applicability.required_product_traits,
                        ...pattern.applicability.buyer_contexts,
                    ]}
                    empty="No supported applicability was supplied."
                />
                <ApplicabilityBlock
                    title="When not to use it"
                    values={[
                        ...pattern.applicability.unsuitable_categories,
                        ...(grouped.avoid ?? []).map((item) => item.instruction),
                    ]}
                    empty="No contraindication was identified from the supplied evidence."
                    warning
                />
            </div>

            <div className="grid gap-3 lg:grid-cols-3">
                <InstructionBlock
                    title="Keep"
                    icon={Check}
                    items={grouped.keep ?? []}
                    empty="No required keep instruction."
                    tone="ok"
                />
                <InstructionBlock
                    title="Change"
                    icon={RefreshCw}
                    items={grouped.change ?? []}
                    empty="No required change instruction."
                    tone="info"
                />
                <InstructionBlock
                    title="Avoid"
                    icon={ShieldAlert}
                    items={grouped.avoid ?? []}
                    empty="No prohibited execution was identified."
                    tone="warn"
                />
            </div>

            {(pattern.uncertainties.length > 0 ||
                pattern.performance_summary.caveats.length > 0) && (
                <div className="rounded-2xl bg-warn-soft/55 p-3 shadow-[inset_0_1px_0_rgba(183,110,0,0.12)]">
                    <p className="text-xs font-semibold uppercase text-text-tertiary">
                        Evidence limits
                    </p>
                    <ul className="mt-2 space-y-1 text-sm text-text-secondary">
                        {[...pattern.uncertainties, ...pattern.performance_summary.caveats].map(
                            (item) => (
                                <li key={item}>{item}</li>
                            ),
                        )}
                    </ul>
                </div>
            )}

            <div>
                <Button onClick={onContinue} disabled={continueDisabled}>
                    {continuePending ? (
                        <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                    ) : (
                        <ArrowRight className="h-4 w-4" aria-hidden />
                    )}
                    {continuePending
                        ? "Generating product concepts..."
                        : "Generate product concepts"}
                </Button>
            </div>
        </div>
    );
}

function ApplicabilityBlock({
    title,
    values,
    empty,
    warning = false,
}: {
    title: string;
    values: string[];
    empty: string;
    warning?: boolean;
}) {
    return (
        <section
            className={
                warning
                    ? "rounded-2xl bg-warn-soft/60 p-4 shadow-[inset_0_1px_0_rgba(183,110,0,0.14)]"
                    : "rounded-2xl bg-info-soft/52 p-4 shadow-[inset_0_1px_0_rgba(37,102,235,0.12)]"
            }
        >
            <h4 className="text-sm font-semibold text-text-primary">{title}</h4>
            <div className="mt-3 flex flex-wrap gap-2">
                {values.length ? (
                    values.map((value) => (
                        <StatusChip key={value} tone={warning ? "warn" : "info"}>
                            {value}
                        </StatusChip>
                    ))
                ) : (
                    <p className="text-sm text-text-secondary">{empty}</p>
                )}
            </div>
        </section>
    );
}

function InstructionBlock({
    title,
    icon: Icon,
    items,
    empty,
    tone,
}: {
    title: string;
    icon: typeof Check;
    items: PatternInstruction[];
    empty: string;
    tone: "ok" | "info" | "warn";
}) {
    const toneClass = {
        ok: "bg-ok-soft/70 text-ok shadow-[inset_0_1px_0_rgba(12,138,74,0.12)]",
        info: "bg-info-soft/52 text-info shadow-[inset_0_1px_0_rgba(37,102,235,0.12)]",
        warn: "bg-warn-soft/60 text-warn shadow-[inset_0_1px_0_rgba(183,110,0,0.14)]",
    }[tone];
    return (
        <section className={`rounded-2xl p-4 ${toneClass}`}>
            <div className="flex items-center gap-2">
                <Icon className="h-4 w-4" />
                <h4 className="text-sm font-semibold text-text-primary">{title}</h4>
            </div>
            {items.length ? (
                <ul className="mt-3 space-y-3">
                    {items.map((item) => (
                        <li key={`${item.element_path}-${item.instruction}`}>
                            <p className="text-sm leading-5 text-text-primary">
                                {item.instruction}
                            </p>
                            <p className="mt-1 text-xs leading-5 text-text-tertiary">
                                {item.rationale}
                            </p>
                        </li>
                    ))}
                </ul>
            ) : (
                <p className="mt-3 text-sm text-text-secondary">{empty}</p>
            )}
        </section>
    );
}

function formatBeatTiming(start: number | null, end: number | null) {
    if (start === null && end === null) return "Flexible";
    if (start === null) return `By ${formatMilliseconds(end!)}`;
    if (end === null || start === end) return formatMilliseconds(start);
    return `${formatMilliseconds(start)}-${formatMilliseconds(end)}`;
}

function formatMilliseconds(value: number) {
    const seconds = value / 1000;
    return `${Number.isInteger(seconds) ? seconds : seconds.toFixed(1)}s`;
}
