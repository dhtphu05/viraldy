import { Film } from "lucide-react";
import { useState } from "react";

export function RemakeClipThumbnail({ src, label }: { src: string; label?: string }) {
    const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
    return (
        <span className="remake-output-clip-thumbnail">
            {status !== "error" && (
                <video
                    src={src}
                    muted
                    playsInline
                    preload="metadata"
                    aria-label={label}
                    className="size-full object-contain"
                    style={{ opacity: status === "ready" ? 1 : 0 }}
                    onLoadedMetadata={(event) => {
                        const video = event.currentTarget;
                        if (Number.isFinite(video.duration) && video.duration > 0)
                            video.currentTime = Math.min(0.05, video.duration / 2);
                    }}
                    onLoadedData={() => setStatus("ready")}
                    onSeeked={() => setStatus("ready")}
                    onError={() => setStatus("error")}
                />
            )}
            {status !== "ready" && (
                <>
                    <Film
                        className="remake-output-clip-thumbnail__fallback size-5 opacity-40"
                        aria-hidden="true"
                    />
                    {status === "error" && (
                        <span className="sr-only">
                            {label ?? "Hình xem trước"} · Chưa tải được hình xem trước
                        </span>
                    )}
                </>
            )}
        </span>
    );
}
