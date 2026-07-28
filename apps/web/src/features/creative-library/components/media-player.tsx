import { useEffect, useRef, useState } from "react";
import { Play, Pause, Volume2, VolumeX } from "lucide-react";
import { cn } from "@/shared/lib/utils";
import {
    thumbnailGradient,
    thumbnailAccent,
    formatDuration,
} from "@/features/creative-library/lib/creative-visuals";
import type {
    CreativeReference,
    DnaTimelineMarker,
} from "@/features/creative-library/types/creative";

const kindColor: Record<DnaTimelineMarker["kind"], string> = {
    hook: "var(--primary)",
    reveal: "var(--info)",
    demo: "var(--ok)",
    proof: "var(--ok)",
    offer: "var(--warn)",
    cta: "var(--info)",
    risk: "var(--destructive)",
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
    const rafRef = useRef<number | null>(null);
    const lastTsRef = useRef<number | null>(null);

    useEffect(() => {
        if (!playing) {
            if (rafRef.current) cancelAnimationFrame(rafRef.current);
            lastTsRef.current = null;
            return;
        }
        const tick = (ts: number) => {
            if (lastTsRef.current == null) lastTsRef.current = ts;
            const dt = (ts - lastTsRef.current) / 1000;
            lastTsRef.current = ts;
            const next = currentTime + dt;
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
    }, [playing, currentTime, creative.durationSec, onTimeChange]);

    const pct = (currentTime / creative.durationSec) * 100;
    const accent = thumbnailAccent(creative.thumbSeed);

    return (
        <div className="surface-card inner-top-highlight overflow-hidden">
            <div
                className="relative w-full"
                style={{
                    aspectRatio: "16 / 9",
                    backgroundImage: thumbnailGradient(creative.thumbSeed),
                }}
            >
                <div
                    aria-hidden
                    className="absolute inset-0 bg-[radial-gradient(circle_at_30%_25%,rgba(255,255,255,0.35),transparent_55%)]"
                />
                <div className="absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-black/60 to-transparent" />
                <div className="absolute left-4 top-4 flex items-center gap-2">
                    <span className="rounded-md bg-black/45 px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide text-white backdrop-blur-sm">
                        {creative.platform}
                    </span>
                    <span className="rounded-md bg-black/45 px-2 py-0.5 text-[11px] font-medium text-white backdrop-blur-sm">
                        {formatDuration(creative.durationSec)}
                    </span>
                </div>
                <button
                    type="button"
                    onClick={() => setPlaying((p) => !p)}
                    aria-label={playing ? "Pause" : "Play"}
                    className="absolute inset-0 grid place-items-center focus-visible:outline-none"
                >
                    <span
                        className={cn(
                            "grid h-14 w-14 place-items-center rounded-full bg-white/90 text-text-primary shadow-lg transition-opacity",
                            playing && "opacity-0 group-hover:opacity-100",
                        )}
                    >
                        {playing ? (
                            <Pause className="h-5 w-5" />
                        ) : (
                            <Play className="h-5 w-5 fill-current" />
                        )}
                    </span>
                </button>
            </div>

            {/* Controls */}
            <div className="flex flex-col gap-3 p-3.5">
                <div className="flex items-center gap-3 text-sm">
                    <button
                        type="button"
                        onClick={() => setPlaying((p) => !p)}
                        aria-label={playing ? "Pause" : "Play"}
                        className="grid h-8 w-8 place-items-center rounded-full bg-primary text-primary-foreground hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
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
                    <button
                        type="button"
                        onClick={() => setMuted((m) => !m)}
                        aria-label={muted ? "Unmute" : "Mute"}
                        aria-pressed={!muted}
                        className="ml-auto grid h-8 w-8 place-items-center rounded-md text-text-tertiary hover:bg-surface-soft hover:text-text-primary focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    >
                        {muted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
                    </button>
                </div>

                {/* Timeline */}
                <div className="relative pt-3">
                    <div className="relative h-1.5 rounded-full bg-surface-muted">
                        <div
                            className="absolute inset-y-0 left-0 rounded-full"
                            style={{ width: `${pct}%`, backgroundColor: accent }}
                        />
                    </div>
                    <input
                        type="range"
                        min={0}
                        max={creative.durationSec}
                        step={0.1}
                        value={currentTime}
                        aria-label="Seek"
                        onChange={(e) => onTimeChange(Number(e.target.value))}
                        className="absolute inset-x-0 top-2 h-4 w-full cursor-pointer opacity-0"
                    />
                    {/* Markers */}
                    {markers.map((m) => {
                        const left = Math.min(
                            100,
                            Math.max(0, (m.at / creative.durationSec) * 100),
                        );
                        const active = m.id === activeMarkerId;
                        return (
                            <button
                                key={m.id}
                                type="button"
                                onClick={() => {
                                    onTimeChange(m.at);
                                    onMarkerClick?.(m.id);
                                }}
                                aria-label={`${m.label} at ${formatDuration(m.at)}`}
                                className={cn(
                                    "group/marker absolute -translate-x-1/2 focus-visible:outline-none",
                                )}
                                style={{ left: `${left}%`, top: "10px" }}
                            >
                                <span
                                    className={cn(
                                        "block h-3.5 w-3.5 rounded-full border-2 border-surface transition-transform",
                                        active && "scale-125",
                                    )}
                                    style={{ backgroundColor: kindColor[m.kind] }}
                                />
                                <span
                                    className={cn(
                                        "pointer-events-none absolute left-1/2 top-6 -translate-x-1/2 whitespace-nowrap rounded-md bg-surface px-2 py-0.5 text-[10px] font-medium text-text-primary opacity-0 shadow-sm-card transition-opacity group-hover/marker:opacity-100 group-focus-visible/marker:opacity-100",
                                        active && "opacity-100",
                                    )}
                                >
                                    {m.label} · {formatDuration(m.at)}
                                </span>
                            </button>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}
