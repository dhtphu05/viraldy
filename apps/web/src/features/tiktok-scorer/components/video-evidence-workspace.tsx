import { Captions, ImageOff, Play, ScanLine, VideoOff, VolumeX } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import type { TikTokEvidence, TikTokScoreRun } from "../types";
import { safeSeekSeconds } from "../lib/tiktok-score-view-model";
import type { EvidenceMarkerKind, EvidenceTimelineMarker } from "@/shared/ui/evidence-timeline";
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
    const evidenceGroups = useMemo(() => groupEvidence(run.evidence), [run.evidence]);

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
                        <CompactEvidenceTimeline
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

                    <div className="mt-5 space-y-4">
                        {run.evidence.length ? (
                            evidenceGroups.map((group) => (
                                <section
                                    key={group.key}
                                    className="rounded-2xl border border-divider bg-surface p-3"
                                >
                                    <div className="mb-2 flex items-center justify-between gap-2">
                                        <div>
                                            <h3 className="text-sm font-semibold text-text-primary">
                                                {group.title}
                                            </h3>
                                            <p className="text-xs text-text-tertiary">
                                                {group.items.length} evidence item
                                                {group.items.length === 1 ? "" : "s"}
                                            </p>
                                        </div>
                                        <StatusChip tone={group.tone}>{group.label}</StatusChip>
                                    </div>
                                    <div className="space-y-2">
                                        {group.items.map((evidence) => (
                                            <EvidenceButton
                                                key={evidence.id}
                                                evidence={evidence}
                                                onOpen={() => {
                                                    const timestamp = evidence.startMs ?? 0;
                                                    seek(timestamp / 1_000, {
                                                        id: evidence.id,
                                                        at: timestamp / 1_000,
                                                        label: evidence.summary,
                                                        kind: markerKind(evidence.sourceType),
                                                    });
                                                }}
                                            />
                                        ))}
                                    </div>
                                </section>
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

function CompactEvidenceTimeline({
    duration,
    currentTime,
    markers,
    activeId,
    onSeek,
}: {
    duration: number;
    currentTime: number;
    markers: EvidenceTimelineMarker[];
    activeId?: string | null;
    onSeek: (seconds: number, marker: EvidenceTimelineMarker) => void;
}) {
    const sorted = useMemo(() => [...markers].sort((a, b) => a.at - b.at), [markers]);
    const grouped = useMemo(() => groupMarkersForTimeline(sorted), [sorted]);
    const safeDuration = Math.max(duration, 1);
    const playhead = Math.min(100, Math.max(0, (currentTime / safeDuration) * 100));

    return (
        <section
            aria-label="Video evidence timeline"
            className="rounded-2xl border border-divider bg-surface p-4"
        >
            <div className="flex items-center justify-between gap-3">
                <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-text-tertiary">
                        Evidence map
                    </p>
                    <h3 className="mt-1 text-sm font-semibold text-text-primary">
                        Key moments by timestamp
                    </h3>
                </div>
                <StatusChip tone="neutral">{markers.length} markers</StatusChip>
            </div>

            <div className="mt-4 overflow-x-auto pb-1">
                <div className="relative h-12 min-w-[520px]">
                    <div className="absolute left-0 right-0 top-5 h-2 rounded-full bg-surface-soft" />
                    <div
                        aria-hidden
                        className="pointer-events-none absolute top-3.5 z-20 h-5 w-0.5 -translate-x-1/2 bg-primary transition-[left] duration-[200ms] motion-reduce:transition-none"
                        style={{ left: `${playhead}%` }}
                    />
                    {sorted.map((marker) => {
                        const selected = marker.id === activeId;
                        return (
                            <button
                                key={marker.id}
                                type="button"
                                aria-label={`${marker.label} at ${formatMs(marker.at * 1_000)}`}
                                aria-pressed={selected}
                                onClick={() => onSeek(marker.at, marker)}
                                className="absolute top-0 z-10 grid h-10 w-10 -translate-x-1/2 place-items-center rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                                style={{
                                    left: `${Math.min(
                                        100,
                                        Math.max(0, (marker.at / safeDuration) * 100),
                                    )}%`,
                                }}
                            >
                                <span
                                    className={`${markerDotClass(
                                        marker.kind,
                                    )} h-3.5 w-3.5 rounded-full ring-2 ring-surface transition-transform duration-[180ms] motion-reduce:transition-none ${
                                        selected ? "scale-125 ring-primary" : ""
                                    }`}
                                />
                            </button>
                        );
                    })}
                </div>
            </div>

            <div className="mt-4 grid gap-2 md:grid-cols-2">
                {grouped.map((group) => (
                    <button
                        key={group.key}
                        type="button"
                        onClick={() => onSeek(group.primary.at, group.primary)}
                        className={`rounded-xl border p-3 text-left transition-colors hover:bg-surface-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                            group.items.some((item) => item.id === activeId)
                                ? "border-primary bg-primary-soft"
                                : "border-divider bg-surface"
                        }`}
                    >
                        <span className="flex items-center justify-between gap-2">
                            <span className="flex items-center gap-2 text-sm font-semibold text-text-primary">
                                <span
                                    className={`${markerDotClass(
                                        group.primary.kind,
                                    )} h-2.5 w-2.5 rounded-full`}
                                />
                                {formatMs(group.primary.at * 1_000)}
                            </span>
                            <span className="text-xs text-text-tertiary">
                                {group.items.length} cue{group.items.length === 1 ? "" : "s"}
                            </span>
                        </span>
                        <span className="mt-1 block text-xs font-medium text-text-tertiary">
                            {markerKindLabel(group.primary.kind)}
                        </span>
                        <span className="mt-1 line-clamp-2 block text-sm text-text-secondary">
                            {group.label}
                        </span>
                    </button>
                ))}
            </div>
        </section>
    );
}

function EvidenceButton({ evidence, onOpen }: { evidence: TikTokEvidence; onOpen: () => void }) {
    return (
        <button
            type="button"
            onClick={onOpen}
            className="flex w-full min-w-0 gap-3 rounded-xl bg-surface-soft p-3 text-left transition-colors hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
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
                    <span className="font-medium text-text-primary">{evidence.summary}</span>
                    {evidence.confidence && (
                        <StatusChip tone="info">{evidence.confidence} confidence</StatusChip>
                    )}
                </span>
                <span className="mt-1 block text-xs text-text-tertiary">
                    {humanize(evidence.sourceType)} ·{" "}
                    {evidence.startMs === null ? "No timestamp" : formatMs(evidence.startMs)}
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

function groupMarkersForTimeline(markers: EvidenceTimelineMarker[]) {
    const groups = new Map<
        string,
        { key: string; primary: EvidenceTimelineMarker; items: EvidenceTimelineMarker[] }
    >();
    for (const marker of markers) {
        const timeBucket = Math.round(marker.at);
        const key = `${timeBucket}-${marker.kind}`;
        const existing = groups.get(key);
        if (existing) {
            groups.set(key, { ...existing, items: [...existing.items, marker] });
        } else {
            groups.set(key, { key, primary: marker, items: [marker] });
        }
    }
    return Array.from(groups.values()).map((group) => {
        const label = group.items
            .map((item) => cleanMarkerLabel(item.label))
            .filter((label, index, all) => label && all.indexOf(label) === index)
            .slice(0, 2)
            .join(" · ");
        return {
            ...group,
            label: label || markerKindLabel(group.primary.kind),
        };
    });
}

function cleanMarkerLabel(label: string) {
    const trimmed = label.trim();
    if (!trimmed) return "";
    if (/^[a-z0-9_]+$/i.test(trimmed) && trimmed.includes("_")) return humanize(trimmed);
    return trimmed;
}

function markerKindLabel(kind: EvidenceMarkerKind) {
    const labels: Record<EvidenceMarkerKind, string> = {
        hook: "Opening hook",
        product: "Product visibility",
        demo: "Demo action",
        proof: "Proof/outcome",
        offer: "Disclosure or offer",
        cta: "CTA",
        risk: "Claim/disclosure safety",
        missing: "Missing evidence",
    };
    return labels[kind];
}

function markerDotClass(kind: EvidenceMarkerKind) {
    const classes: Record<EvidenceMarkerKind, string> = {
        hook: "bg-info",
        product: "bg-ok",
        demo: "bg-info",
        proof: "bg-ok",
        offer: "bg-warn",
        cta: "bg-info",
        risk: "bg-destructive",
        missing: "bg-warn",
    };
    return classes[kind];
}

function groupEvidence(evidence: TikTokEvidence[]) {
    const groups = [
        { key: "proof", title: "Proof moments", label: "Outcome", tone: "ok" as const },
        { key: "demo", title: "Demo steps", label: "Action", tone: "info" as const },
        { key: "product", title: "Product visibility", label: "Product", tone: "ok" as const },
        { key: "claim", title: "Claims and disclosures", label: "Safety", tone: "warn" as const },
        {
            key: "platform",
            title: "Platform/native cues",
            label: "TikTok fit",
            tone: "neutral" as const,
        },
        { key: "other", title: "Other evidence", label: "Context", tone: "info" as const },
    ];
    return groups.flatMap((group) => {
        const items = evidence.filter((item) => evidenceGroupKey(item.sourceType) === group.key);
        return items.length ? [{ ...group, items }] : [];
    });
}

function evidenceGroupKey(sourceType: string) {
    const source = sourceType.toLowerCase();
    if (source.includes("proof")) return "proof";
    if (source.includes("demo")) return "demo";
    if (source.includes("product")) return "product";
    if (source.includes("claim") || source.includes("transcript") || source.includes("text")) {
        return "claim";
    }
    if (source.includes("platform") || source.includes("editing") || source.includes("cta")) {
        return "platform";
    }
    return "other";
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
