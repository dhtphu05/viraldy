import { cn } from "@/shared/lib/utils";

type DemoMarker = {
    at: number;
    tone?: "ok" | "warn" | "info" | "destructive" | "neutral";
};

const toneClass: Record<NonNullable<DemoMarker["tone"]>, string> = {
    ok: "bg-ok",
    warn: "bg-warn",
    info: "bg-info",
    destructive: "bg-destructive",
    neutral: "bg-text-tertiary",
};

export function DemoVisualTile({
    seed,
    label,
    badges = [],
    score,
    markers = [],
    aspect = "4 / 5",
    className,
}: {
    seed: string;
    label?: string;
    badges?: string[];
    score?: string | number;
    markers?: DemoMarker[];
    aspect?: string;
    className?: string;
}) {
    return (
        <div
            aria-hidden
            data-demo-seed={seed}
            className={cn("relative overflow-hidden bg-surface-muted", className)}
            style={{ aspectRatio: aspect }}
        >
            <div className="absolute inset-x-0 bottom-0 h-20 bg-black/40" />
            {badges.length > 0 && (
                <div className="absolute left-2.5 top-2.5 flex flex-wrap items-center gap-1.5">
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
            {label && (
                <div className="absolute inset-x-3 bottom-8">
                    <p className="line-clamp-2 text-xs font-medium leading-snug text-white drop-shadow-sm">
                        {label}
                    </p>
                </div>
            )}
            {score !== undefined && (
                <span className="absolute bottom-2.5 right-2.5 rounded-md bg-white/90 px-2 py-0.5 text-[11px] font-semibold tabular text-text-primary shadow-sm-card">
                    {score}
                </span>
            )}
            {markers.length > 0 && (
                <div className="absolute inset-x-3 bottom-3 h-1 rounded-full bg-white/35">
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
