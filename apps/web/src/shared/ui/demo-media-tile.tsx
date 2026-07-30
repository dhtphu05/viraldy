import { Play } from "lucide-react";
import { useEffect, useState } from "react";
import { cn } from "@/shared/lib/utils";
import { DemoVisualTile } from "@/shared/ui/demo-visual-tile";
import { normalizeAspectRatio } from "@/shared/lib/media-aspect";
import { Skeleton } from "@/shared/ui/skeleton";

type DemoMarker = {
    at: number;
    tone?: "ok" | "warn" | "info" | "destructive" | "neutral";
};

export type DemoMediaKind = "image" | "video";

const toneClass: Record<NonNullable<DemoMarker["tone"]>, string> = {
    ok: "bg-ok",
    warn: "bg-warn",
    info: "bg-info",
    destructive: "bg-destructive",
    neutral: "bg-text-tertiary",
};

function mediaKindFromUrl(url?: string): DemoMediaKind | undefined {
    if (!url) return undefined;
    return /\.(mp4|mov|webm)(\?|$)/i.test(url) || url.startsWith("blob:") ? "video" : "image";
}

export function DemoMediaTile({
    mediaUrl,
    mediaKind,
    posterUrl,
    alt,
    seed,
    label,
    badges = [],
    score,
    markers = [],
    aspect = "4 / 5",
    fit = "cover",
    controls = false,
    muted = true,
    loop = false,
    showPlay = true,
    className,
}: {
    mediaUrl?: string;
    mediaKind?: DemoMediaKind;
    posterUrl?: string;
    alt?: string;
    seed: string;
    label?: string;
    badges?: string[];
    score?: string | number;
    markers?: DemoMarker[];
    aspect?: string;
    fit?: "cover" | "contain";
    controls?: boolean;
    muted?: boolean;
    loop?: boolean;
    showPlay?: boolean;
    className?: string;
}) {
    const kind = mediaKind ?? mediaKindFromUrl(mediaUrl);
    const resolvedAspect = normalizeAspectRatio(aspect);
    const [loaded, setLoaded] = useState(false);

    useEffect(() => {
        setLoaded(false);
    }, [mediaUrl]);

    if (!mediaUrl || !kind) {
        return (
            <DemoVisualTile
                seed={seed}
                label={label}
                badges={badges}
                score={score}
                markers={markers}
                aspect={resolvedAspect}
                className={className}
            />
        );
    }

    return (
        <div
            className={cn("relative overflow-hidden bg-surface-soft", className)}
            style={{ aspectRatio: resolvedAspect }}
        >
            {!loaded && <Skeleton className="absolute inset-0 rounded-none" />}
            {kind === "image" ? (
                <img
                    src={mediaUrl}
                    alt={alt ?? ""}
                    className={cn(
                        "h-full w-full",
                        fit === "contain" ? "object-contain" : "object-cover",
                        !loaded && "opacity-0",
                    )}
                    loading="lazy"
                    onLoad={() => setLoaded(true)}
                />
            ) : (
                <video
                    src={mediaUrl}
                    poster={posterUrl}
                    className={cn(
                        "h-full w-full",
                        fit === "contain" ? "object-contain" : "object-cover",
                        !loaded && "opacity-0",
                    )}
                    muted={muted}
                    loop={loop}
                    playsInline
                    preload="metadata"
                    controls={controls}
                    aria-label={alt ?? label ?? "Demo video preview"}
                    onLoadedMetadata={() => setLoaded(true)}
                />
            )}
            <div className="pointer-events-none absolute right-2.5 top-2.5 flex items-center gap-1.5">
                <span className="rounded-md bg-white/90 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-text-primary shadow-sm">
                    {kind}
                </span>
            </div>
            <div
                aria-hidden
                className="pointer-events-none absolute inset-x-0 bottom-0 h-20 bg-black/45"
            />
            {badges.length > 0 && (
                <div className="pointer-events-none absolute left-2.5 top-2.5 flex flex-wrap items-center gap-1.5">
                    {badges.map((badge) => (
                        <span
                            key={badge}
                            className="rounded-md bg-black/65 px-1.5 py-0.5 text-[10px] font-medium uppercase text-white"
                        >
                            {badge}
                        </span>
                    ))}
                </div>
            )}
            {kind === "video" && showPlay && !controls && (
                <span className="pointer-events-none absolute bottom-2.5 left-2.5 grid h-8 w-8 place-items-center rounded-full bg-white/85 text-text-primary shadow-md-card">
                    <Play className="h-3.5 w-3.5 fill-current" />
                </span>
            )}
            {label && (
                <div className="pointer-events-none absolute inset-x-3 bottom-8">
                    <p className="line-clamp-2 text-xs font-medium leading-snug text-white drop-shadow-sm">
                        {label}
                    </p>
                </div>
            )}
            {score !== undefined && (
                <span className="pointer-events-none absolute bottom-2.5 right-2.5 rounded-md bg-white/90 px-2 py-0.5 text-[11px] font-semibold tabular text-text-primary shadow-sm-card">
                    {score}
                </span>
            )}
            {markers.length > 0 && (
                <div className="pointer-events-none absolute inset-x-3 bottom-3 h-1 rounded-full bg-white/35">
                    {markers.map((marker, index) => (
                        <span
                            key={`${marker.at}-${index}`}
                            className={cn(
                                "absolute top-1/2 h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full ring-1 ring-white/80",
                                toneClass[marker.tone ?? "neutral"],
                            )}
                            style={{ left: `${Math.min(98, Math.max(2, marker.at))}%` }}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}
