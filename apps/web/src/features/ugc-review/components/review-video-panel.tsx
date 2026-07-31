import { Captions, Film, Play, VideoOff } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { formatEvidenceTime } from "../lib/ugc-review-view-model";
import { seekVideoToEvidence } from "../lib/review-video-seek";
import type { UgcRecommendation } from "../types/ugc-review";
import {
    EvidenceTimeline,
    type EvidenceMarkerKind,
    type EvidenceTimelineMarker,
} from "@/shared/ui/evidence-timeline";
import { StatusChip } from "@/shared/ui/status-chip";
import { SurfaceCard } from "@/shared/ui/surface-card";

export type UgcEvidenceSeekTarget = Readonly<{
    key: string;
    startMs: number;
}>;

export function ReviewVideoPanel({
    mediaUrl,
    durationMs,
    recommendations,
    seekTarget,
}: {
    mediaUrl: string | null;
    durationMs: number | null;
    recommendations: readonly UgcRecommendation[];
    seekTarget: UgcEvidenceSeekTarget | null;
}) {
    const videoRef = useRef<HTMLVideoElement>(null);
    const [currentTime, setCurrentTime] = useState(0);
    const [activeId, setActiveId] = useState<string | null>(null);
    const evidence = useMemo(
        () =>
            recommendations.flatMap((recommendation) =>
                recommendation.evidence.map((item) => ({ recommendation, item })),
            ),
        [recommendations],
    );
    const markers = useMemo<EvidenceTimelineMarker[]>(
        () =>
            evidence.flatMap(({ recommendation, item }) =>
                item.startMs === null
                    ? []
                    : [
                          {
                              id: `${recommendation.id}:${item.id}`,
                              at: item.startMs / 1_000,
                              label: item.observed,
                              kind: markerKind(recommendation.group),
                          },
                      ],
            ),
        [evidence],
    );
    const durationSeconds = durationMs && durationMs > 0 ? durationMs / 1_000 : 0;

    useEffect(() => {
        if (!seekTarget) return;
        const seconds = seekVideoToEvidence(videoRef.current, seekTarget.startMs, durationMs);
        setCurrentTime(seconds);
        setActiveId(seekTarget.key);
    }, [durationMs, seekTarget]);

    function seek(seconds: number, marker: EvidenceTimelineMarker) {
        setCurrentTime(seconds);
        setActiveId(marker.id);
        seekVideoToEvidence(videoRef.current, seconds * 1_000, durationMs);
    }

    return (
        <SurfaceCard padding="lg">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <h2 className="text-lg font-semibold text-text-primary">Video evidence</h2>
                    <p className="mt-1 text-sm text-text-secondary">
                        Select a timestamp to review the exact moment behind a recommendation.
                    </p>
                </div>
                <StatusChip tone="info">
                    <Film className="h-3 w-3" />
                    Server-analyzed evidence
                </StatusChip>
            </div>

            <div className="mt-5 grid min-w-0 gap-5 xl:grid-cols-[minmax(240px,340px)_minmax(0,1fr)] xl:items-start">
                <div className="mx-auto w-full max-w-[340px]">
                    <div className="aspect-[9/16] overflow-hidden rounded-2xl bg-black text-white shadow-soft-card">
                        {mediaUrl ? (
                            <video
                                ref={videoRef}
                                src={mediaUrl}
                                controls
                                playsInline
                                preload="metadata"
                                aria-label="UGC draft under review"
                                onTimeUpdate={(event) =>
                                    setCurrentTime(event.currentTarget.currentTime)
                                }
                                className="h-full w-full object-contain"
                            />
                        ) : (
                            <div className="flex h-full flex-col items-center justify-center px-6 text-center">
                                <VideoOff className="h-9 w-9 text-white/70" />
                                <p className="mt-3 font-medium">Video preview unavailable</p>
                                <p className="mt-2 text-sm text-white/65">
                                    Evidence from the completed review remains available.
                                </p>
                            </div>
                        )}
                    </div>
                    <p className="mt-2 text-xs tabular-nums text-text-tertiary">
                        Selected time {formatEvidenceTime(Math.round(currentTime * 1_000))}
                    </p>
                </div>

                <div className="min-w-0">
                    {durationSeconds > 0 && markers.length > 0 ? (
                        <EvidenceTimeline
                            duration={durationSeconds}
                            currentTime={currentTime}
                            markers={markers}
                            activeId={activeId}
                            onSeek={seek}
                        />
                    ) : (
                        <p className="rounded-2xl bg-surface-soft p-4 text-sm text-text-secondary">
                            No timestamped evidence is available for the timeline. Untimestamped
                            observations are still shown below.
                        </p>
                    )}

                    <div className="mt-4 space-y-2">
                        {evidence.slice(0, 12).map(({ recommendation, item }) => {
                            const key = `${recommendation.id}:${item.id}`;
                            const timestamped = item.startMs !== null;
                            return (
                                <button
                                    key={key}
                                    type="button"
                                    disabled={!timestamped}
                                    onClick={() => {
                                        if (item.startMs === null) return;
                                        seek(item.startMs / 1_000, {
                                            id: key,
                                            at: item.startMs / 1_000,
                                            label: item.observed,
                                            kind: markerKind(recommendation.group),
                                        });
                                    }}
                                    className="flex w-full min-w-0 gap-3 rounded-xl border border-control-border bg-surface p-3 text-left transition-colors duration-[180ms] enabled:hover:bg-surface-soft disabled:cursor-default focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                                >
                                    <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-info-soft text-info">
                                        {item.source === "transcript" || item.source === "ocr" ? (
                                            <Captions className="h-4 w-4" />
                                        ) : (
                                            <Play className="h-4 w-4" />
                                        )}
                                    </span>
                                    <span className="min-w-0">
                                        <span className="block text-sm font-medium text-text-primary">
                                            {item.observed}
                                        </span>
                                        <span className="mt-1 block text-xs text-text-tertiary">
                                            {timestamped
                                                ? formatEvidenceTime(item.startMs)
                                                : "No timestamp"}{" "}
                                            · {item.confidence} confidence
                                        </span>
                                    </span>
                                </button>
                            );
                        })}
                    </div>
                </div>
            </div>
        </SurfaceCard>
    );
}

function markerKind(group: UgcRecommendation["group"]): EvidenceMarkerKind {
    if (group === "fix_first") return "risk";
    if (group === "confirm") return "missing";
    return "demo";
}
