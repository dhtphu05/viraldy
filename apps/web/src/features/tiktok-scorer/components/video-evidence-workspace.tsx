import { Captions, ImageOff, Play, ScanLine, VideoOff, VolumeX } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import type { TikTokEvidence, TikTokScoreRun } from "../types";
import { safeSeekSeconds } from "../lib/tiktok-score-view-model";
import {
    EvidenceTimeline,
    type EvidenceMarkerKind,
    type EvidenceTimelineMarker,
} from "@/shared/ui/evidence-timeline";
import { StatusChip } from "@/shared/ui/status-chip";
import { SurfaceCard } from "@/shared/ui/surface-card";

export type EvidenceSeekTarget = {
    key: string;
    timestampMs: number;
    range: [number, number] | null;
    evidenceId?: string;
};

export function VideoEvidenceWorkspace({
    run,
    mediaUrl,
    seekTarget,
    onEvidenceOpen,
}: {
    run: TikTokScoreRun;
    mediaUrl: string | null;
    seekTarget: EvidenceSeekTarget | null;
    onEvidenceOpen: (evidence: TikTokEvidence) => void;
}) {
    const videoRef = useRef<HTMLVideoElement>(null);
    const [currentTime, setCurrentTime] = useState(0);
    const [activeId, setActiveId] = useState<string | null>(null);
    const [selectedRange, setSelectedRange] = useState<[number, number] | null>(null);
    const durationMs = run.sceneInventory?.durationMs ?? null;
    const durationSeconds = durationMs === null ? 0 : durationMs / 1_000;
    const evidenceById = useMemo(
        () => new Map(run.evidence.map((item) => [item.id, item])),
        [run.evidence],
    );
    const markers = useMemo(() => buildMarkers(run), [run]);

    useEffect(() => {
        if (!seekTarget) return;
        const seconds = safeSeekSeconds(seekTarget.timestampMs, durationMs);
        setCurrentTime(seconds);
        setSelectedRange(seekTarget.range);
        setActiveId(seekTarget.evidenceId ?? seekTarget.key);
        if (videoRef.current) {
            videoRef.current.currentTime = seconds;
            void videoRef.current.play().catch(() => undefined);
        }
    }, [durationMs, seekTarget]);

    function seek(seconds: number, marker: EvidenceTimelineMarker) {
        const safeSeconds = safeSeekSeconds(seconds * 1_000, durationMs);
        setCurrentTime(safeSeconds);
        setActiveId(marker.id);
        const evidence = evidenceById.get(marker.id);
        setSelectedRange(
            evidence && evidence.startMs !== null && evidence.endMs !== null
                ? [evidence.startMs, evidence.endMs]
                : null,
        );
        if (videoRef.current) {
            videoRef.current.currentTime = safeSeconds;
            void videoRef.current.play().catch(() => undefined);
        }
        if (evidence) onEvidenceOpen(evidence);
    }

    const safeZoneSupported = Boolean(run.sceneInventory?.safeZoneObservations.length);

    return (
        <SurfaceCard padding="lg">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <h2 className="text-lg font-semibold text-text-primary">Video and evidence</h2>
                    <p className="mt-1 text-sm text-text-secondary">
                        Every jump uses a server-provided timestamp. No browser-side media analysis
                        is performed.
                    </p>
                </div>
                <div className="flex flex-wrap gap-2">
                    {run.sceneInventory?.audioAvailable === false && (
                        <StatusChip tone="info">
                            <VolumeX className="h-3 w-3" />
                            No audio detected
                        </StatusChip>
                    )}
                    {safeZoneSupported && (
                        <StatusChip tone="neutral">
                            <ScanLine className="h-3 w-3" />
                            Review-aid safe zone
                        </StatusChip>
                    )}
                </div>
            </div>

            <div className="mt-5 grid min-w-0 gap-5 xl:grid-cols-[minmax(260px,380px)_minmax(0,1fr)] xl:items-start">
                <div className="mx-auto w-full max-w-[380px]">
                    <div className="relative aspect-[9/16] overflow-hidden rounded-2xl bg-black text-white shadow-soft-card">
                        {mediaUrl ? (
                            <video
                                ref={videoRef}
                                src={mediaUrl}
                                controls
                                playsInline
                                preload="metadata"
                                aria-label="Scored TikTok video"
                                onTimeUpdate={(event) =>
                                    setCurrentTime(event.currentTarget.currentTime)
                                }
                                className="h-full w-full object-contain"
                            />
                        ) : (
                            <div className="flex h-full flex-col items-center justify-center px-6 text-center">
                                <VideoOff className="h-9 w-9 text-white/70" />
                                <p className="mt-3 font-medium">Video playback unavailable</p>
                                <p className="mt-2 text-sm text-white/65">
                                    The backend did not provide a playback URL. Evidence timestamps
                                    remain selectable below.
                                </p>
                            </div>
                        )}
                        {safeZoneSupported && (
                            <div className="pointer-events-none absolute inset-x-[8%] inset-y-[7%] rounded-xl border border-dashed border-white/55">
                                <span className="absolute left-2 top-2 rounded bg-black/65 px-1.5 py-0.5 text-[10px]">
                                    Review aid
                                </span>
                            </div>
                        )}
                    </div>
                    <div className="mt-2 flex items-center justify-between text-xs text-text-secondary">
                        <span className="tabular-nums">
                            Selected time {formatSeconds(currentTime)}
                        </span>
                        <span>
                            {durationMs === null
                                ? "Duration unavailable"
                                : formatSeconds(durationSeconds)}
                        </span>
                    </div>
                    {selectedRange && (
                        <p className="mt-1 text-xs text-primary" aria-live="polite">
                            Selected evidence range {formatMs(selectedRange[0])}–
                            {formatMs(selectedRange[1])}
                        </p>
                    )}
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
                        <div className="rounded-2xl bg-surface-soft p-4 text-sm text-text-secondary">
                            No server-provided evidence ranges are available for a timeline yet.
                        </div>
                    )}

                    <div className="mt-4 space-y-2">
                        {run.evidence.length ? (
                            run.evidence.map((evidence) => (
                                <button
                                    key={evidence.id}
                                    type="button"
                                    onClick={() => {
                                        const timestamp = evidence.startMs ?? 0;
                                        seek(timestamp / 1_000, {
                                            id: evidence.id,
                                            at: timestamp / 1_000,
                                            label: evidence.summary,
                                            kind: markerKind(evidence.sourceType),
                                        });
                                    }}
                                    className="flex w-full min-w-0 gap-3 rounded-xl border border-control-border bg-surface p-3 text-left transition-colors hover:bg-surface-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                                >
                                    <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-info-soft text-info">
                                        {evidence.frameUrl ? (
                                            <Play className="h-4 w-4" />
                                        ) : evidence.transcript || evidence.ocrText ? (
                                            <Captions className="h-4 w-4" />
                                        ) : (
                                            <ImageOff className="h-4 w-4" />
                                        )}
                                    </span>
                                    <span className="min-w-0 flex-1">
                                        <span className="flex flex-wrap items-center gap-2">
                                            <span className="font-medium text-text-primary">
                                                {evidence.summary}
                                            </span>
                                            {evidence.confidence && (
                                                <StatusChip tone="info">
                                                    {evidence.confidence} confidence
                                                </StatusChip>
                                            )}
                                        </span>
                                        <span className="mt-1 block text-xs text-text-tertiary">
                                            {humanize(evidence.sourceType)} ·{" "}
                                            {evidence.startMs === null
                                                ? "No timestamp"
                                                : formatMs(evidence.startMs)}
                                        </span>
                                        {evidence.transcript && (
                                            <span className="mt-2 block text-sm text-text-secondary">
                                                Transcript: “{evidence.transcript}”
                                            </span>
                                        )}
                                        {evidence.ocrText && (
                                            <span className="mt-1 block text-sm text-text-secondary">
                                                On-screen text: “{evidence.ocrText}”
                                            </span>
                                        )}
                                    </span>
                                </button>
                            ))
                        ) : (
                            <p className="rounded-xl bg-surface-soft p-4 text-sm text-text-secondary">
                                Evidence details are not included in this response. Scene ranges and
                                fix links remain available when supplied by the server.
                            </p>
                        )}
                    </div>
                </div>
            </div>
        </SurfaceCard>
    );
}

function buildMarkers(run: TikTokScoreRun): EvidenceTimelineMarker[] {
    const markers = run.evidence.flatMap((item) =>
        item.startMs === null
            ? []
            : [
                  {
                      id: item.id,
                      at: item.startMs / 1_000,
                      label: item.summary,
                      kind: markerKind(item.sourceType),
                  },
              ],
    );
    for (const scene of run.sceneInventory?.scenes ?? []) {
        if (scene.demoStep)
            markers.push({
                id: `demo-${scene.id}`,
                at: scene.startMs / 1_000,
                label: scene.demoStep,
                kind: "demo",
            });
        if (scene.proofRole)
            markers.push({
                id: `proof-${scene.id}`,
                at: scene.startMs / 1_000,
                label: scene.proofRole,
                kind: "proof",
            });
    }
    for (const [index, item] of (run.sceneInventory?.productRanges ?? []).entries())
        markers.push({
            id: `product-${index}`,
            at: item[0] / 1_000,
            label: "Product appearance",
            kind: "product",
        });
    for (const [index, item] of (run.sceneInventory?.ctaRanges ?? []).entries())
        markers.push({
            id: `cta-${index}`,
            at: item[0] / 1_000,
            label: "CTA evidence",
            kind: "cta",
        });
    for (const [index, item] of (run.sceneInventory?.disclosureRanges ?? []).entries())
        markers.push({
            id: `disclosure-${index}`,
            at: item[0] / 1_000,
            label: "Disclosure evidence",
            kind: "offer",
        });
    return markers.filter(
        (marker, index, all) => all.findIndex((item) => item.id === marker.id) === index,
    );
}

function markerKind(sourceType: string): EvidenceMarkerKind {
    const source = sourceType.toLowerCase();
    if (source.includes("product")) return "product";
    if (source.includes("demo")) return "demo";
    if (source.includes("proof")) return "proof";
    if (source.includes("cta")) return "cta";
    if (source.includes("offer") || source.includes("disclosure")) return "offer";
    if (source.includes("risk") || source.includes("claim")) return "risk";
    return "hook";
}

function formatSeconds(seconds: number) {
    const safe = Math.max(0, seconds);
    return `${Math.floor(safe / 60)}:${String(Math.floor(safe % 60)).padStart(2, "0")}`;
}
function formatMs(ms: number) {
    return formatSeconds(ms / 1_000);
}
function humanize(value: string) {
    return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
