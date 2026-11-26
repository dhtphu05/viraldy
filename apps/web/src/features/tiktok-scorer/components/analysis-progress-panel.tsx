import { Check, Eye, Loader2, ScanSearch, VideoOff } from "lucide-react";
import { useState } from "react";

import { buildAnalysisProgress } from "../lib/analysis-progress";
import { buildProcessingSteps } from "../lib/tiktok-score-view-model";
import type { TikTokScoreRun } from "../types";
import { ProcessingStepper } from "@/shared/ui/processing-stepper";
import { Progress } from "@/shared/ui/progress";
import { StatusChip } from "@/shared/ui/status-chip";
import { SurfaceCard } from "@/shared/ui/surface-card";

export function AnalysisProgressPanel({
    run,
    stage,
    progress,
    mediaUrl,
}: {
    run: TikTokScoreRun;
    stage: string;
    progress: number;
    mediaUrl: string | null;
}) {
    const [mediaDurationMs, setMediaDurationMs] = useState<number | null>(
        run.sceneInventory?.durationMs ?? null,
    );
    const view = buildAnalysisProgress(stage, progress, mediaDurationMs);

    return (
        <SurfaceCard padding="none" className="overflow-hidden">
            <div className="grid min-w-0 lg:grid-cols-[minmax(260px,340px)_minmax(0,1fr)]">
                <div className="relative min-h-[420px] overflow-hidden bg-black lg:min-h-[560px]">
                    {mediaUrl ? (
                        <video
                            src={mediaUrl}
                            aria-label="Video currently being analyzed"
                            className="h-full max-h-[70vh] min-h-[420px] w-full object-contain lg:min-h-[560px]"
                            autoPlay
                            muted
                            loop
                            controls
                            playsInline
                            preload="metadata"
                            onLoadedMetadata={(event) =>
                                setMediaDurationMs(Math.round(event.currentTarget.duration * 1_000))
                            }
                        />
                    ) : (
                        <div className="flex h-full min-h-[420px] flex-col items-center justify-center px-8 text-center text-white lg:min-h-[560px]">
                            <VideoOff className="h-9 w-9 text-white/70" />
                            <p className="mt-3 font-medium">Preview is still preparing</p>
                            <p className="mt-1 text-sm text-white/60">
                                Analysis will continue while playback becomes available.
                            </p>
                        </div>
                    )}
                    <div className="pointer-events-none absolute inset-x-3 top-3 flex items-center justify-between gap-2">
                        <span className="inline-flex items-center gap-2 rounded-full bg-black/75 px-3 py-1.5 text-xs font-semibold text-white backdrop-blur">
                            <span className="relative flex h-2 w-2">
                                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-300 opacity-70" />
                                <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
                            </span>
                            Live analysis
                        </span>
                        <span className="rounded-full bg-black/75 px-3 py-1.5 text-xs font-medium tabular-nums text-white backdrop-blur">
                            {view.percent}%
                        </span>
                    </div>
                    <div className="pointer-events-none absolute inset-x-3 bottom-14 rounded-2xl bg-black/75 p-3 text-white shadow-lg backdrop-blur-md">
                        <p className="flex items-center gap-2 text-xs font-medium text-white/70">
                            <Eye className="h-3.5 w-3.5" />
                            Video coverage
                        </p>
                        <p className="mt-1 text-sm font-semibold">{view.coverageLabel}</p>
                    </div>
                </div>

                <div className="min-w-0 p-5 sm:p-7 lg:p-8">
                    <div aria-live="polite">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                            <StatusChip tone="info">Analysis in progress</StatusChip>
                            <span className="text-sm font-semibold tabular-nums text-primary">
                                {view.percent}% complete
                            </span>
                        </div>
                        <h1 className="mt-4 text-balance text-2xl font-semibold text-text-primary sm:text-3xl">
                            {view.title}
                        </h1>
                        <p className="mt-2 max-w-2xl text-pretty text-sm leading-6 text-text-secondary">
                            {view.description}
                        </p>
                        <Progress
                            value={view.percent}
                            className="mt-5 h-2.5"
                            aria-label={`Analysis ${view.percent}% complete`}
                        />
                    </div>

                    {view.active.length > 0 && (
                        <section className="mt-7" aria-labelledby="signals-being-read">
                            <div className="flex items-center gap-2">
                                <span className="grid h-8 w-8 place-items-center rounded-full bg-primary-softer text-primary">
                                    <ScanSearch className="h-4 w-4" />
                                </span>
                                <div>
                                    <h2
                                        id="signals-being-read"
                                        className="text-sm font-semibold text-text-primary"
                                    >
                                        Signals being read now
                                    </h2>
                                    <p className="text-xs text-text-tertiary">
                                        These become confirmed only after the evidence pass
                                        finishes.
                                    </p>
                                </div>
                            </div>
                            <div className="mt-3 grid gap-2 sm:grid-cols-2">
                                {view.active.map((signal) => (
                                    <div
                                        key={signal.label}
                                        className="rounded-xl bg-primary-softer/65 p-3 shadow-[0_1px_0_rgb(0_0_0_/_0.03)]"
                                    >
                                        <div className="flex items-center gap-2">
                                            <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
                                            <p className="text-sm font-semibold text-text-primary">
                                                {signal.label}
                                            </p>
                                        </div>
                                        <p className="mt-1 text-pretty text-xs leading-5 text-text-secondary">
                                            {signal.detail}
                                        </p>
                                    </div>
                                ))}
                            </div>
                        </section>
                    )}

                    <section className="mt-7" aria-labelledby="confirmed-analysis">
                        <h2
                            id="confirmed-analysis"
                            className="text-xs font-semibold uppercase tracking-wide text-text-tertiary"
                        >
                            Confirmed so far
                        </h2>
                        {view.confirmed.length ? (
                            <div className="mt-3 space-y-2">
                                {view.confirmed.map((signal) => (
                                    <div
                                        key={signal.label}
                                        className="flex gap-3 rounded-xl bg-ok-soft/55 p-3 shadow-[0_1px_0_rgb(0_0_0_/_0.03)]"
                                    >
                                        <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-ok text-white">
                                            <Check className="h-3 w-3" />
                                        </span>
                                        <div>
                                            <p className="text-sm font-semibold text-text-primary">
                                                {signal.label}
                                            </p>
                                            <p className="mt-0.5 text-pretty text-xs leading-5 text-text-secondary">
                                                {signal.detail}
                                            </p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="mt-2 text-sm text-text-secondary">
                                The first confirmation will appear after media preparation.
                            </p>
                        )}
                    </section>

                    <details className="group mt-7 rounded-2xl bg-surface-soft p-3 shadow-[0_1px_0_rgb(0_0_0_/_0.02)]">
                        <summary className="cursor-pointer list-none text-sm font-semibold text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                            <span className="flex items-center justify-between gap-3">
                                View all analysis stages
                                <span className="text-xs font-medium text-text-tertiary group-open:hidden">
                                    Show
                                </span>
                                <span className="hidden text-xs font-medium text-text-tertiary group-open:inline">
                                    Hide
                                </span>
                            </span>
                        </summary>
                        <div className="mt-3 rounded-xl bg-surface/70 p-3">
                            <ProcessingStepper steps={buildProcessingSteps(stage)} />
                        </div>
                    </details>

                    <p className="mt-3 text-xs text-text-tertiary">
                        Pipeline progress comes from the processing job. Viraldy does not invent a
                        frame-level position while the evidence provider is still reviewing the full
                        video.
                    </p>
                </div>
            </div>
        </SurfaceCard>
    );
}
