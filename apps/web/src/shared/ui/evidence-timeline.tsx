import { useMemo, useState, type KeyboardEvent, type ReactNode } from "react";

import { cn } from "@/shared/lib/utils";

export type EvidenceMarkerKind =
    "hook" | "product" | "demo" | "proof" | "offer" | "cta" | "risk" | "missing";

export type EvidenceTimelineMarker = {
    id: string;
    at: number;
    label: string;
    kind: EvidenceMarkerKind;
    preview?: ReactNode;
};

const kindClass: Record<EvidenceMarkerKind, string> = {
    hook: "bg-info text-white",
    product: "bg-ok text-white",
    demo: "bg-info text-white",
    proof: "bg-ok text-white",
    offer: "bg-warn text-white",
    cta: "bg-info text-white",
    risk: "bg-destructive text-white",
    missing: "bg-warn text-white",
};

function formatTime(seconds: number) {
    const minutes = Math.floor(seconds / 60);
    const remainder = Math.max(0, Math.round(seconds % 60));
    return `${minutes}:${String(remainder).padStart(2, "0")}`;
}

export function EvidenceTimeline({
    duration,
    currentTime,
    markers,
    activeId,
    onSeek,
    className,
}: {
    duration: number;
    currentTime: number;
    markers: EvidenceTimelineMarker[];
    activeId?: string | null;
    onSeek: (seconds: number, marker: EvidenceTimelineMarker) => void;
    className?: string;
}) {
    const [previewId, setPreviewId] = useState<string | null>(null);
    const sorted = useMemo(() => [...markers].sort((a, b) => a.at - b.at), [markers]);
    const safeDuration = Math.max(duration, 1);
    const playhead = Math.min(100, Math.max(0, (currentTime / safeDuration) * 100));
    const previewMarker = sorted.find((marker) => marker.id === previewId);

    function moveFocus(event: KeyboardEvent<HTMLButtonElement>, index: number) {
        if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
        event.preventDefault();
        const nextIndex =
            event.key === "ArrowRight"
                ? Math.min(sorted.length - 1, index + 1)
                : Math.max(0, index - 1);
        const next = event.currentTarget
            .closest("[data-evidence-timeline]")
            ?.querySelectorAll<HTMLButtonElement>("[data-marker]")[nextIndex];
        next?.focus();
    }

    return (
        <section
            aria-label="Video evidence timeline"
            data-evidence-timeline
            className={cn("rounded-2xl bg-surface-soft p-4", className)}
        >
            <div className="overflow-x-auto pb-1">
                <div className="relative h-12 min-w-[520px]">
                    <div className="absolute left-0 right-0 top-5 h-1.5 rounded-full bg-surface-muted" />
                    <div
                        aria-hidden
                        className="absolute top-3.5 z-20 h-4 w-0.5 -translate-x-1/2 bg-primary transition-[left] duration-[200ms] motion-reduce:transition-none"
                        style={{ left: `${playhead}%` }}
                    />
                    {sorted.map((marker, index) => {
                        const selected = marker.id === activeId;
                        return (
                            <button
                                key={marker.id}
                                type="button"
                                data-marker
                                aria-label={`${marker.label} at ${formatTime(marker.at)}`}
                                aria-pressed={selected}
                                onClick={() => onSeek(marker.at, marker)}
                                onFocus={() => setPreviewId(marker.id)}
                                onBlur={() => setPreviewId(null)}
                                onMouseEnter={() => setPreviewId(marker.id)}
                                onMouseLeave={() => setPreviewId(null)}
                                onKeyDown={(event) => moveFocus(event, index)}
                                className={cn(
                                    "absolute top-0 z-10 grid h-10 w-10 -translate-x-1/2 place-items-center rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                                    selected && "z-30",
                                )}
                                style={{
                                    left: `${Math.min(
                                        100,
                                        Math.max(0, (marker.at / safeDuration) * 100),
                                    )}%`,
                                }}
                            >
                                <span
                                    className={cn(
                                        "h-3 w-3 rounded-full ring-2 ring-surface transition-transform duration-[180ms] motion-reduce:transition-none",
                                        kindClass[marker.kind],
                                        selected && "scale-125 ring-primary",
                                    )}
                                />
                            </button>
                        );
                    })}
                </div>
            </div>

            {previewMarker?.preview && (
                <div className="mb-3 rounded-xl bg-surface p-3 shadow-soft-card">
                    {previewMarker.preview}
                </div>
            )}

            <div className="flex flex-wrap gap-x-4 gap-y-2">
                {sorted.map((marker) => (
                    <button
                        key={marker.id}
                        type="button"
                        onClick={() => onSeek(marker.at, marker)}
                        className={cn(
                            "inline-flex min-h-10 items-center gap-2 rounded-lg px-1 text-xs text-text-secondary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                            marker.id === activeId && "font-medium text-primary-active",
                        )}
                    >
                        <span className={cn("h-2 w-2 rounded-full", kindClass[marker.kind])} />
                        {marker.label}
                        <span className="tabular text-text-tertiary">{formatTime(marker.at)}</span>
                    </button>
                ))}
            </div>
        </section>
    );
}
