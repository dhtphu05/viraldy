import { useEffect, useRef, useState } from "react";
import { Film, Pause, Play, Volume2, VolumeX } from "lucide-react";

import { formatDuration } from "@/features/creative-library/lib/creative-visuals";
import type {
    CreativeReference,
    DnaTimelineMarker,
} from "@/features/creative-library/types/creative";
import { cn } from "@/shared/lib/utils";
import { normalizeAspectRatio } from "@/shared/lib/media-aspect";
import { EvidenceTimeline, type EvidenceMarkerKind } from "@/shared/ui/evidence-timeline";
import { SurfaceCard } from "@/shared/ui/surface-card";

const markerKinds: Record<DnaTimelineMarker["kind"], EvidenceMarkerKind> = {
    hook: "hook",
    reveal: "product",
    demo: "demo",
    proof: "proof",
    offer: "offer",
    cta: "cta",
    risk: "risk",
};

export function MediaPlayer({
    creative,
    markers = [],
    currentTime,
    onTimeChange,
    activeMarkerId,
    onMarkerClick,
}: {
    creative: CreativeReference;
    markers?: DnaTimelineMarker[];
    currentTime: number;
    onTimeChange: (t: number) => void;
    activeMarkerId?: string;
    onMarkerClick?: (id: string) => void;
}) {
    const [playing, setPlaying] = useState(false);
    const [muted, setMuted] = useState(true);
    const videoRef = useRef<HTMLVideoElement>(null);
    const rafRef = useRef<number | null>(null);
    const lastTsRef = useRef<number | null>(null);
    const hasVideo = creative.mediaKind === "video" && !!creative.mediaUrl;
    const hasImage = creative.mediaKind === "image" && !!creative.mediaUrl;
    const stillUrl =
        !hasVideo &&
        (creative.posterUrl ?? creative.thumbnailUrl ?? (hasImage ? creative.mediaUrl : undefined));
    const hasSimulatedPlayback = !hasVideo && !stillUrl;
    const safeDuration = Math.max(creative.durationSec, 0.1);

    useEffect(() => {
        if (!hasSimulatedPlayback) return;
        if (!playing) {
            if (rafRef.current) cancelAnimationFrame(rafRef.current);
            lastTsRef.current = null;
            return;
        }
        const tick = (timestamp: number) => {
            if (lastTsRef.current == null) lastTsRef.current = timestamp;
            const elapsed = (timestamp - lastTsRef.current) / 1000;
            lastTsRef.current = timestamp;
            const next = currentTime + elapsed;
            if (next >= creative.durationSec) {
                onTimeChange(creative.durationSec);
                setPlaying(false);
                return;
            }
            onTimeChange(next);
            rafRef.current = requestAnimationFrame(tick);
        };
        rafRef.current = requestAnimationFrame(tick);
        return () => {
            if (rafRef.current) cancelAnimationFrame(rafRef.current);
        };
    }, [creative.durationSec, currentTime, hasSimulatedPlayback, onTimeChange, playing]);

    useEffect(() => {
        if (!hasVideo || !videoRef.current) return;
        videoRef.current.muted = muted;
    }, [hasVideo, muted]);

    useEffect(() => {
        if (!hasVideo || !videoRef.current) return;
        if (Math.abs(videoRef.current.currentTime - currentTime) > 0.35) {
            videoRef.current.currentTime = currentTime;
        }
    }, [currentTime, hasVideo]);

    function seekTo(value: number) {
        const next = Math.min(creative.durationSec, Math.max(0, value));
        onTimeChange(next);
        if (videoRef.current && Math.abs(videoRef.current.currentTime - next) > 0.2) {
            videoRef.current.currentTime = next;
        }
    }

    function togglePlayback() {
        if (hasSimulatedPlayback) {
            setPlaying((previous) => !previous);
            return;
        }
        if (!videoRef.current) return;
        if (videoRef.current.paused) void videoRef.current.play();
        else videoRef.current.pause();
    }

    const progress = Math.min(100, Math.max(0, (currentTime / safeDuration) * 100));
    const mediaAspect = normalizeAspectRatio(creative.mediaAspectRatio, "16 / 9");
    const vertical = creative.mediaAspectRatio === "9:16";
    const playable = hasVideo || hasSimulatedPlayback;

    return (
        <SurfaceCard padding="none" className="min-w-0 overflow-hidden">
            <div
                className={cn(
                    "group relative w-full overflow-hidden bg-black",
                    vertical && "mx-auto max-w-[420px]",
                )}
                style={{ aspectRatio: mediaAspect }}
            >
                {hasVideo ? (
                    <video
                        ref={videoRef}
                        src={creative.mediaUrl}
                        poster={creative.posterUrl ?? creative.thumbnailUrl}
                        className="h-full w-full object-contain"
                        muted={muted}
                        playsInline
                        preload="metadata"
                        aria-label={`${creative.title} video`}
                        onPlay={() => setPlaying(true)}
                        onPause={() => setPlaying(false)}
                        onEnded={() => setPlaying(false)}
                        onTimeUpdate={(event) => onTimeChange(event.currentTarget.currentTime)}
                    />
                ) : stillUrl ? (
                    <img
                        src={stillUrl}
                        alt={creative.title}
                        className="h-full w-full object-contain"
                    />
                ) : (
                    <div className="absolute inset-0 grid place-items-center bg-surface-muted text-text-tertiary">
                        <div className="flex flex-col items-center gap-2 text-center">
                            <span className="grid h-14 w-14 place-items-center rounded-full bg-surface">
                                <Film className="h-6 w-6" aria-hidden />
                            </span>
                            <span className="text-sm font-medium text-text-secondary">
                                Preview unavailable
                            </span>
                        </div>
                    </div>
                )}

                <div className="pointer-events-none absolute inset-x-0 bottom-0 h-16 bg-black/20" />
                <div className="pointer-events-none absolute left-3 top-3 flex max-w-[calc(100%-1.5rem)] flex-wrap items-center gap-1.5">
                    <span className="rounded-md bg-black/55 px-2 py-0.5 text-[11px] font-medium uppercase text-white">
                        {creative.platform}
                    </span>
                    <span className="rounded-md bg-black/55 px-2 py-0.5 text-[11px] font-medium tabular text-white">
                        {formatDuration(creative.durationSec)}
                    </span>
                    {creative.mediaAspectRatio && (
                        <span className="rounded-md bg-black/55 px-2 py-0.5 text-[11px] font-medium text-white">
                            {creative.mediaAspectRatio}
                        </span>
                    )}
                </div>

                {playable && (
                    <button
                        type="button"
                        onClick={togglePlayback}
                        aria-label={playing ? "Pause" : "Play"}
                        className="absolute inset-0 grid place-items-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
                    >
                        <span
                            className={cn(
                                "grid h-14 w-14 place-items-center rounded-full bg-white/90 text-text-primary shadow-floating-card transition-opacity",
                                playing &&
                                    "opacity-0 group-hover:opacity-100 group-focus-within:opacity-100",
                            )}
                        >
                            {playing ? (
                                <Pause className="h-5 w-5" />
                            ) : (
                                <Play className="h-5 w-5 fill-current" />
                            )}
                        </span>
                    </button>
                )}
            </div>

            <div className="flex min-w-0 flex-col gap-3 p-3.5">
                <div className="flex items-center gap-3 text-sm">
                    <button
                        type="button"
                        onClick={togglePlayback}
                        aria-label={playing ? "Pause" : "Play"}
                        disabled={!playable}
                        className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-primary text-primary-foreground transition-colors hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:bg-surface-muted disabled:text-text-disabled"
                    >
                        {playing ? (
                            <Pause className="h-3.5 w-3.5" />
                        ) : (
                            <Play className="h-3.5 w-3.5 fill-current" />
                        )}
                    </button>
                    <span className="tabular text-xs text-text-secondary">
                        {formatDuration(currentTime)} / {formatDuration(creative.durationSec)}
                    </span>
                    {hasVideo && (
                        <button
                            type="button"
                            onClick={() => setMuted((previous) => !previous)}
                            aria-label={muted ? "Unmute" : "Mute"}
                            aria-pressed={!muted}
                            className="ml-auto grid h-9 w-9 place-items-center rounded-lg text-text-tertiary hover:bg-surface-soft hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        >
                            {muted ? (
                                <VolumeX className="h-4 w-4" />
                            ) : (
                                <Volume2 className="h-4 w-4" />
                            )}
                        </button>
                    )}
                </div>

                <div className="relative py-2" aria-label="Media scrubber">
                    <div className="relative h-1.5 rounded-full bg-surface-muted">
                        <div
                            className="absolute inset-y-0 left-0 rounded-full bg-primary"
                            style={{ width: `${progress}%` }}
                        />
                    </div>
                    <input
                        type="range"
                        min={0}
                        max={safeDuration}
                        step={0.1}
                        value={Math.min(currentTime, safeDuration)}
                        aria-label="Seek media"
                        disabled={!!stillUrl}
                        onChange={(event) => seekTo(Number(event.target.value))}
                        className="absolute inset-x-0 top-0 h-5 w-full cursor-pointer opacity-0 disabled:cursor-default"
                    />
                </div>

                {markers.length > 0 && (
                    <EvidenceTimeline
                        className="rounded-xl"
                        duration={safeDuration}
                        currentTime={currentTime}
                        activeId={activeMarkerId}
                        markers={markers.map((marker) => ({
                            id: marker.id,
                            at: marker.at,
                            label: marker.label,
                            kind: markerKinds[marker.kind],
                        }))}
                        onSeek={(time, marker) => {
                            seekTo(time);
                            onMarkerClick?.(marker.id);
                        }}
                    />
                )}
            </div>
        </SurfaceCard>
    );
}
