import { ImageIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { cn } from "@/shared/lib/utils";

export type AnalysisTimelineMarker = {
    id: string;
    at: number;
    endAt?: number;
    label: string;
    kind?: string;
    tone?: "ok" | "warn" | "info" | "destructive" | "neutral";
};

type MarkerTone = NonNullable<AnalysisTimelineMarker["tone"]>;
type TimelineLane = "attention" | "evidence" | "risk";

const kindTone: Record<string, MarkerTone> = {
    hook: "info",
    reveal: "info",
    demo: "ok",
    proof: "ok",
    offer: "warn",
    cta: "info",
    risk: "destructive",
    missing: "destructive",
};

const laneMeta: Array<{ key: TimelineLane; label: string }> = [
    { key: "attention", label: "Attention" },
    { key: "evidence", label: "Evidence" },
    { key: "risk", label: "Risk" },
];

const markerToneClass: Record<MarkerTone, string> = {
    ok: "bg-ok ring-ok/20",
    warn: "bg-warn ring-warn/20",
    info: "bg-info ring-info/20",
    destructive: "bg-destructive ring-destructive/20",
    neutral: "bg-text-tertiary ring-text-tertiary/20",
};

const markerActiveClass: Record<MarkerTone, string> = {
    ok: "border-ok/35 bg-ok-soft/70",
    warn: "border-warn/35 bg-warn-soft/70",
    info: "border-info/35 bg-info-soft/70",
    destructive: "border-destructive/35 bg-destructive-soft/70",
    neutral: "border-text-tertiary/30 bg-surface-soft",
};

const rangeToneClass: Record<MarkerTone, string> = {
    ok: "bg-ok/8",
    warn: "bg-warn/12",
    info: "bg-info/8",
    destructive: "bg-destructive/10",
    neutral: "bg-text-tertiary/8",
};

export function AnalysisTimelineSvg({
    durationSec,
    currentTime = 0,
    markers,
    onJump,
    previewMediaUrl,
    previewPosterUrl,
    previewMediaKind,
    className,
    title = "Analysis timeline",
}: {
    durationSec: number;
    currentTime?: number;
    markers: AnalysisTimelineMarker[];
    onJump?: (time: number, marker: AnalysisTimelineMarker) => void;
    previewMediaUrl?: string;
    previewPosterUrl?: string;
    previewMediaKind?: "image" | "video";
    className?: string;
    title?: string;
}) {
    const [activeFilter, setActiveFilter] = useState("All");
    const [previewMarkerId, setPreviewMarkerId] = useState<string>();
    const duration = Math.max(1, durationSec);
    const progress = clamp(currentTime / duration, 0, 1);
    const allMarkers = [...markers].sort((a, b) => a.at - b.at);
    const filterOptions = [
        "All",
        ...Array.from(new Set(allMarkers.map((marker) => markerCategory(marker)))),
    ];
    const effectiveFilter = filterOptions.includes(activeFilter) ? activeFilter : "All";
    const filteredMarkers =
        effectiveFilter === "All"
            ? allMarkers
            : allMarkers.filter((marker) => markerCategory(marker) === effectiveFilter);
    const activeId = nearestMarker(filteredMarkers, currentTime)?.id;
    const frames = buildFrames(duration, allMarkers);
    const frameImages = useTimelineFrames(
        previewMediaUrl,
        previewMediaKind,
        previewPosterUrl,
        duration,
        frames.length,
    );
    const previewMarker = allMarkers.find((marker) => marker.id === previewMarkerId);

    const showPreview = (marker: AnalysisTimelineMarker) => setPreviewMarkerId(marker.id);
    const hidePreview = () => setPreviewMarkerId(undefined);

    return (
        <section
            className={cn(
                "rounded-md border border-hairline bg-surface p-3 shadow-sm-card",
                className,
            )}
            aria-label={title}
        >
            <header className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <div className="min-w-0">
                    <h3 className="truncate text-xs font-semibold text-text-primary">{title}</h3>
                    <p className="text-[11px] text-text-tertiary">
                        Real frames mapped to attention, evidence, and risk
                    </p>
                </div>
                <div className="flex items-center gap-2 text-xs tabular text-text-secondary">
                    <span>{formatTimelineTime(currentTime)}</span>
                    <span className="h-1 w-1 rounded-full bg-text-disabled" />
                    <span>{Math.round(progress * 100)}%</span>
                </div>
            </header>

            {filterOptions.length > 2 && (
                <div
                    className="mb-2 flex max-w-full gap-1 overflow-x-auto pb-0.5"
                    role="toolbar"
                    aria-label="Filter timeline evidence"
                >
                    {filterOptions.map((filter) => (
                        <button
                            key={filter}
                            type="button"
                            aria-pressed={effectiveFilter === filter}
                            onClick={() => setActiveFilter(filter)}
                            className={cn(
                                "shrink-0 rounded-md px-2 py-1 text-[11px] font-medium text-text-secondary transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                                effectiveFilter === filter
                                    ? "bg-text-primary text-white"
                                    : "bg-surface-soft hover:bg-surface-muted hover:text-text-primary",
                            )}
                        >
                            {filter}
                        </button>
                    ))}
                </div>
            )}

            <div className="relative rounded-md border border-hairline bg-surface-soft/65 p-2.5 sm:p-3">
                <div className="grid grid-cols-6 gap-1.5" aria-hidden="true">
                    {frames.map((frame, index) => {
                        const image = frameImages[index] || previewPosterUrl;
                        const segmentMarker = frame.marker;
                        const tone = segmentMarker ? markerTone(segmentMarker) : "neutral";

                        return (
                            <div
                                key={frame.id}
                                className={cn(
                                    "relative min-w-0 overflow-hidden rounded-[5px] bg-surface-muted",
                                    frame.startAt <= currentTime &&
                                        currentTime < frame.endAt &&
                                        "ring-2 ring-primary ring-offset-1 ring-offset-surface-soft",
                                )}
                            >
                                <div className="aspect-[4/3] sm:aspect-video">
                                    {image ? (
                                        <img
                                            src={image}
                                            alt=""
                                            className="h-full w-full object-cover"
                                        />
                                    ) : (
                                        <span className="grid h-full place-items-center text-text-disabled">
                                            <ImageIcon className="h-4 w-4" />
                                        </span>
                                    )}
                                </div>
                                <div
                                    className={cn(
                                        "absolute inset-x-0 bottom-0 h-0.5",
                                        markerToneClass[tone].split(" ")[0],
                                    )}
                                />
                                <span className="absolute bottom-1 left-1 rounded-[3px] bg-black/65 px-1 py-0.5 text-[9px] font-medium tabular text-white">
                                    {formatTimelineTime(frame.startAt)}
                                </span>
                            </div>
                        );
                    })}
                </div>

                <div className="relative mt-4">
                    <div
                        aria-hidden="true"
                        className="pointer-events-none absolute bottom-0 top-0 z-20 w-px bg-primary/70"
                        style={{ left: `calc(4.5rem + (100% - 4.5rem) * ${progress})` }}
                    >
                        <span className="absolute -left-1 -top-1.5 h-2.5 w-2.5 rounded-full border-2 border-surface bg-primary shadow-sm" />
                    </div>

                    <div className="space-y-1.5">
                        {laneMeta.map((lane) => {
                            const laneMarkers = filteredMarkers.filter(
                                (marker) => laneForMarker(marker) === lane.key,
                            );

                            return (
                                <div
                                    key={lane.key}
                                    className="grid min-h-9 grid-cols-[4rem_minmax(0,1fr)] items-center gap-2"
                                >
                                    <span className="text-[10px] font-medium text-text-tertiary">
                                        {lane.label}
                                    </span>
                                    <div className="relative h-9">
                                        <div className="absolute inset-x-0 top-1/2 h-px bg-hairline" />
                                        <div className="absolute inset-x-0 top-1/2 h-1 -translate-y-1/2 rounded-full bg-surface-muted" />

                                        {laneMarkers
                                            .filter((marker) => marker.endAt !== undefined)
                                            .map((marker) => {
                                                const tone = markerTone(marker);
                                                const start = markerPercent(marker, duration);
                                                const end = clamp(
                                                    ((marker.endAt ?? marker.at) / duration) * 100,
                                                    0,
                                                    100,
                                                );

                                                return (
                                                    <span
                                                        key={`${marker.id}-range`}
                                                        aria-hidden="true"
                                                        className={cn(
                                                            "absolute inset-y-1 rounded-[5px]",
                                                            rangeToneClass[tone],
                                                        )}
                                                        style={{
                                                            left: `${start}%`,
                                                            width: `${Math.max(2, end - start)}%`,
                                                        }}
                                                    />
                                                );
                                            })}

                                        {laneMarkers.map((marker) => {
                                            const tone = markerTone(marker);
                                            const active = marker.id === activeId;

                                            return (
                                                <button
                                                    key={marker.id}
                                                    type="button"
                                                    onClick={() => onJump?.(marker.at, marker)}
                                                    onMouseEnter={() => showPreview(marker)}
                                                    onMouseLeave={hidePreview}
                                                    onFocus={() => showPreview(marker)}
                                                    onBlur={hidePreview}
                                                    aria-label={`${marker.label} at ${formatTimelineTime(marker.at)}`}
                                                    className={cn(
                                                        "group absolute top-1/2 z-10 grid h-8 w-8 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-md transition-transform duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                                                        onJump
                                                            ? "cursor-pointer hover:scale-110"
                                                            : "cursor-default",
                                                    )}
                                                    style={{
                                                        left: `${markerPercent(marker, duration)}%`,
                                                    }}
                                                >
                                                    <span
                                                        className={cn(
                                                            "block h-3 w-3 border-2 border-white shadow-sm ring-4 transition-transform duration-200",
                                                            markerToneClass[tone],
                                                            lane.key === "risk"
                                                                ? "rotate-45 rounded-[3px]"
                                                                : "rounded-full",
                                                            active && "scale-125",
                                                        )}
                                                    />
                                                </button>
                                            );
                                        })}
                                    </div>
                                </div>
                            );
                        })}
                    </div>

                    <div className="ml-[4.5rem] mt-1 flex justify-between text-[9px] tabular text-text-tertiary">
                        <span>00:00</span>
                        <span>{formatTimelineTime(duration)}</span>
                    </div>
                </div>

                {previewMarker && (previewMediaUrl || previewPosterUrl) && (
                    <TimelineFramePreview
                        marker={previewMarker}
                        mediaUrl={previewMediaUrl}
                        posterUrl={previewPosterUrl}
                        mediaKind={previewMediaKind}
                        duration={duration}
                    />
                )}
            </div>

            <div className="mt-2 grid gap-1.5 sm:grid-cols-2">
                {filteredMarkers.slice(0, 6).map((marker) => {
                    const tone = markerTone(marker);
                    const active = marker.id === activeId;

                    return (
                        <button
                            key={marker.id}
                            type="button"
                            onClick={() => onJump?.(marker.at, marker)}
                            onMouseEnter={() => showPreview(marker)}
                            onMouseLeave={hidePreview}
                            onFocus={() => showPreview(marker)}
                            onBlur={hidePreview}
                            className={cn(
                                "flex min-w-0 items-center gap-2 rounded-md border border-hairline bg-surface px-2 py-1.5 text-left text-[11px] text-text-secondary transition-colors duration-200",
                                onJump && "hover:border-primary/40 hover:bg-primary-soft/40",
                                active && markerActiveClass[tone],
                                !onJump && "cursor-default",
                            )}
                        >
                            <span
                                className={cn(
                                    "h-2.5 w-2.5 shrink-0 rounded-full",
                                    markerToneClass[tone].split(" ")[0],
                                )}
                            />
                            <span className="shrink-0 tabular">
                                {formatTimelineTime(marker.at)}
                            </span>
                            <span className="truncate font-medium">{marker.label}</span>
                        </button>
                    );
                })}
            </div>
        </section>
    );
}

function buildFrames(duration: number, markers: AnalysisTimelineMarker[], count = 6) {
    return Array.from({ length: count }).map((_, index) => {
        const startAt = (index / count) * duration;
        const endAt = ((index + 1) / count) * duration;

        return {
            id: `frame-${index}`,
            startAt,
            endAt,
            marker: markers.find((marker) => marker.at >= startAt && marker.at < endAt),
        };
    });
}

function laneForMarker(marker: AnalysisTimelineMarker): TimelineLane {
    const kind = marker.kind?.toLowerCase() ?? "";
    const tone = markerTone(marker);

    if (tone === "destructive" || kind.includes("risk") || kind.includes("missing")) {
        return "risk";
    }
    if (tone === "ok" || kind.includes("proof") || kind.includes("demo")) {
        return "evidence";
    }
    return "attention";
}

function markerTone(marker: AnalysisTimelineMarker): MarkerTone {
    return marker.tone ?? kindTone[marker.kind ?? ""] ?? "neutral";
}

function markerCategory(marker: AnalysisTimelineMarker) {
    const kind = marker.kind?.toLowerCase() ?? "";
    if (kind.includes("hook")) return "Hook";
    if (kind.includes("reveal") || kind.includes("product")) return "Product";
    if (kind.includes("demo") || kind.includes("proof")) return "Demo";
    if (kind.includes("offer")) return "Offer";
    if (kind.includes("cta") || kind.includes("missing")) return "CTA";
    if (kind.includes("risk") || kind.includes("claim")) return "Claim";
    return "Other";
}

function markerPercent(marker: AnalysisTimelineMarker, duration: number) {
    return clamp((marker.at / duration) * 100, 0, 100);
}

function formatTimelineTime(sec: number) {
    const safe = Math.max(0, sec);
    const minutes = Math.floor(safe / 60)
        .toString()
        .padStart(2, "0");
    const seconds = Math.floor(safe % 60)
        .toString()
        .padStart(2, "0");
    return `${minutes}:${seconds}`;
}

function nearestMarker(markers: AnalysisTimelineMarker[], currentTime: number) {
    if (!markers.length) return undefined;
    return markers.reduce((closest, marker) =>
        Math.abs(marker.at - currentTime) < Math.abs(closest.at - currentTime) ? marker : closest,
    );
}

function clamp(value: number, min: number, max: number) {
    return Math.min(max, Math.max(min, value));
}

function TimelineFramePreview({
    marker,
    mediaUrl,
    posterUrl,
    mediaKind,
    duration,
}: {
    marker: AnalysisTimelineMarker;
    mediaUrl?: string;
    posterUrl?: string;
    mediaKind?: "image" | "video";
    duration: number;
}) {
    const left = clamp(14 + (marker.at / duration) * 72, 18, 82);

    return (
        <div
            data-timeline-preview
            aria-hidden="true"
            className="pointer-events-none absolute top-2 z-30 w-36 -translate-x-1/2 overflow-hidden rounded-md border border-white/70 bg-black shadow-lg-card sm:w-44"
            style={{ left: `${left}%` }}
        >
            <div className="aspect-video bg-black">
                {mediaKind === "video" && mediaUrl ? (
                    <PreviewVideo src={mediaUrl} poster={posterUrl} at={marker.at} />
                ) : (
                    <img
                        src={mediaUrl ?? posterUrl}
                        alt=""
                        className="h-full w-full object-cover"
                    />
                )}
            </div>
            <div className="flex items-center justify-between gap-2 bg-black/90 px-2 py-1.5 text-[10px] text-white">
                <span className="truncate font-medium">{marker.label}</span>
                <span className="shrink-0 tabular text-white/70">
                    {formatTimelineTime(marker.at)}
                </span>
            </div>
        </div>
    );
}

function PreviewVideo({ src, poster, at }: { src: string; poster?: string; at: number }) {
    return (
        <video
            key={`${src}-${at}`}
            src={src}
            poster={poster}
            muted
            playsInline
            preload="metadata"
            aria-hidden="true"
            className="h-full w-full object-cover"
            onLoadedMetadata={(event) => {
                event.currentTarget.currentTime = Math.min(
                    Math.max(0, at),
                    Math.max(0, event.currentTarget.duration - 0.05),
                );
            }}
        />
    );
}

function useTimelineFrames(
    mediaUrl: string | undefined,
    mediaKind: "image" | "video" | undefined,
    posterUrl: string | undefined,
    duration: number,
    count: number,
) {
    const [frames, setFrames] = useState<string[]>([]);

    useEffect(() => {
        if (!mediaUrl || mediaKind !== "video") {
            setFrames(mediaUrl && mediaKind === "image" ? Array(count).fill(mediaUrl) : []);
            return;
        }

        let cancelled = false;
        const video = document.createElement("video");
        const canvas = document.createElement("canvas");
        const context = canvas.getContext("2d");
        const captured: string[] = [];
        let index = 0;

        canvas.width = 192;
        canvas.height = 108;
        video.muted = true;
        video.preload = "auto";
        video.playsInline = true;

        const seekNext = () => {
            if (cancelled) return;
            if (index >= count) {
                setFrames(captured);
                return;
            }
            const sourceDuration =
                Number.isFinite(video.duration) && video.duration > 0 ? video.duration : duration;
            video.currentTime = Math.min(
                Math.max(0, ((index + 0.5) / count) * sourceDuration),
                Math.max(0, sourceDuration - 0.05),
            );
        };

        const onSeeked = () => {
            if (!context || cancelled) return;
            try {
                drawVideoCover(context, video, canvas.width, canvas.height);
                captured.push(canvas.toDataURL("image/jpeg", 0.8));
            } catch {
                captured.push(posterUrl ?? "");
            }
            index += 1;
            seekNext();
        };

        const onLoaded = () => seekNext();
        video.addEventListener("loadedmetadata", onLoaded);
        video.addEventListener("seeked", onSeeked);
        video.src = mediaUrl;

        return () => {
            cancelled = true;
            video.removeEventListener("loadedmetadata", onLoaded);
            video.removeEventListener("seeked", onSeeked);
            video.removeAttribute("src");
            video.load();
        };
    }, [count, duration, mediaKind, mediaUrl, posterUrl]);

    return frames;
}

function drawVideoCover(
    context: CanvasRenderingContext2D,
    video: HTMLVideoElement,
    width: number,
    height: number,
) {
    const sourceWidth = video.videoWidth || width;
    const sourceHeight = video.videoHeight || height;
    const scale = Math.max(width / sourceWidth, height / sourceHeight);
    const drawWidth = sourceWidth * scale;
    const drawHeight = sourceHeight * scale;
    context.drawImage(
        video,
        (width - drawWidth) / 2,
        (height - drawHeight) / 2,
        drawWidth,
        drawHeight,
    );
}
