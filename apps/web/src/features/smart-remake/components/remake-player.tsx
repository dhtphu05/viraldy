import { useEffect, useRef, useState, type CSSProperties } from "react";
import { AlertCircle, LoaderCircle, Pause, Play, Volume2, VolumeX } from "lucide-react";

import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import {
    clampRemakePreviewTime,
    getComparisonPlaybackTime,
    type RemakePreviewScope,
} from "../lib/remake-preview";

export interface RemakePlayerProps {
    url: string;
    compareUrl?: string;
    poster?: string;
    scope: { start: number; end: number } | null;
    compareScope?: RemakePreviewScope;
    versionLabel?: string;
    compareLabel?: string;
    onError?(): void;
    onMetadata?(durationSeconds: number): void;
}

type MediaInfo = { source: string; width: number; height: number; duration: number };
type MediaFailure = { source: string; message: string };

function formatTime(seconds: number) {
    const milliseconds = Math.max(0, Math.round(seconds * 1000));
    const total = Math.floor(milliseconds / 1000);
    const fraction = milliseconds % 1000;
    return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}${fraction ? `.${String(fraction).padStart(3, "0")}` : ""}`;
}

function nativeFrameStyle(info: MediaInfo | null): CSSProperties {
    if (!info) return { width: "100%", maxWidth: 360, height: "min(45dvh, 360px)" };
    const ratio = info.width / info.height;
    return {
        aspectRatio: `${info.width} / ${info.height}`,
        width: `min(100%, ${58 * ratio}dvh, ${640 * ratio}px)`,
        maxHeight: "min(58dvh, 640px)",
    };
}

export function RemakePlayer(props: RemakePlayerProps) {
    // A new output starts paused; comparison/layout changes retain the same video elements.
    return <PlayerSession key={props.url} {...props} />;
}

function PlayerSession({
    url,
    compareUrl,
    poster,
    scope,
    compareScope,
    versionLabel = "Bản đang dùng",
    compareLabel = "Bản mới",
    onError,
    onMetadata,
}: RemakePlayerProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const videoRef = useRef<HTMLVideoElement>(null);
    const comparisonRef = useRef<HTMLVideoElement>(null);
    const playbackRequest = useRef(0);
    const [containerWidth, setContainerWidth] = useState(0);
    const [info, setInfo] = useState<MediaInfo | null>(null);
    const [comparisonInfo, setComparisonInfo] = useState<MediaInfo | null>(null);
    const [failure, setFailure] = useState<MediaFailure | null>(null);
    const [comparisonFailure, setComparisonFailure] = useState<MediaFailure | null>(null);
    const [playing, setPlaying] = useState(false);
    const [muted, setMuted] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [activeVersion, setActiveVersion] = useState<"current" | "compare">("current");
    const [playbackError, setPlaybackError] = useState<string | null>(null);

    const primaryInfo = info?.source === url ? info : null;
    const secondaryInfo = comparisonInfo?.source === compareUrl ? comparisonInfo : null;
    const primaryFailure = failure?.source === url ? failure.message : null;
    const secondaryFailure =
        comparisonFailure && comparisonFailure.source === compareUrl
            ? comparisonFailure.message
            : null;
    const hasComparison = Boolean(compareUrl);
    const active = hasComparison ? activeVersion : "current";
    const wideComparison = hasComparison && containerWidth >= 640;
    const duration = primaryInfo?.duration ?? 0;
    const requestedStart = scope && Number.isFinite(scope.start) ? scope.start : 0;
    const requestedEnd = scope && Number.isFinite(scope.end) ? scope.end : duration;
    const start = Math.min(duration, Math.max(0, requestedStart));
    const end = Math.min(duration, Math.max(0, requestedEnd));
    const invalidScope = Boolean(primaryInfo && end <= start);
    const requestedComparisonStart =
        compareScope === undefined ? requestedStart : (compareScope?.start ?? 0);
    const requestedComparisonEnd =
        compareScope === undefined
            ? requestedEnd
            : (compareScope?.end ?? secondaryInfo?.duration ?? 0);
    const comparisonStart = Math.min(
        secondaryInfo?.duration ?? 0,
        Math.max(0, requestedComparisonStart),
    );
    const comparisonEnd = Math.min(
        secondaryInfo?.duration ?? 0,
        Math.max(0, requestedComparisonEnd),
    );
    const comparisonShorter = Boolean(
        secondaryInfo && comparisonEnd - comparisonStart < end - start,
    );
    const comparisonTime = (time: number) =>
        getComparisonPlaybackTime(time, start, comparisonStart, comparisonEnd);
    const canPlay = Boolean(primaryInfo && !primaryFailure && !invalidScope);
    const singleFrame = Boolean(
        scope && requestedEnd > requestedStart && requestedEnd - requestedStart <= 1 / 24 + 1e-6,
    );
    const lastTime = Math.max(start, end - 1 / 24);
    const safeTime = clampRemakePreviewTime(currentTime, start, end);

    useEffect(() => {
        const container = containerRef.current;
        if (!container) return;
        const measure = () => setContainerWidth(container.getBoundingClientRect().width);
        measure();
        if (typeof ResizeObserver === "undefined") {
            window.addEventListener("resize", measure);
            return () => window.removeEventListener("resize", measure);
        }
        const observer = new ResizeObserver(measure);
        observer.observe(container);
        return () => observer.disconnect();
    }, []);

    useEffect(() => {
        const video = videoRef.current;
        if (!video || !primaryInfo || invalidScope) return;
        if (video.currentTime < start || video.currentTime >= end) {
            video.currentTime = start;
        }
        if (comparisonRef.current && secondaryInfo) {
            comparisonRef.current.currentTime = getComparisonPlaybackTime(
                video.currentTime,
                start,
                comparisonStart,
                comparisonEnd,
            );
        }
    }, [start, end, primaryInfo, secondaryInfo, invalidScope, comparisonStart, comparisonEnd]);

    useEffect(() => {
        const video = videoRef.current;
        if (!video || !playing || !canPlay) return;
        let callback = 0;
        const usesVideoFrames = typeof video.requestVideoFrameCallback === "function";
        const check = (mediaTime: number) => {
            if (mediaTime + 1e-6 >= lastTime) {
                playbackRequest.current += 1;
                video.pause();
                video.currentTime = lastTime;
                const comparison = comparisonRef.current;
                if (comparison) {
                    comparison.pause();
                    comparison.currentTime = getComparisonPlaybackTime(
                        lastTime,
                        start,
                        comparisonStart,
                        comparisonEnd,
                    );
                }
                setCurrentTime(lastTime);
                setPlaying(false);
                return;
            }
            schedule();
        };
        const schedule = () => {
            callback = usesVideoFrames
                ? video.requestVideoFrameCallback((_, metadata) => check(metadata.mediaTime))
                : requestAnimationFrame(() => check(video.currentTime));
        };
        schedule();
        return () => {
            if (usesVideoFrames) video.cancelVideoFrameCallback(callback);
            else cancelAnimationFrame(callback);
        };
    }, [playing, canPlay, lastTime, start, comparisonStart, comparisonEnd]);

    function pauseBoth() {
        playbackRequest.current += 1;
        videoRef.current?.pause();
        comparisonRef.current?.pause();
        setPlaying(false);
    }

    function seek(time: number) {
        const next = clampRemakePreviewTime(time, start, end);
        if (videoRef.current) videoRef.current.currentTime = next;
        if (comparisonRef.current && secondaryInfo) {
            comparisonRef.current.currentTime = comparisonTime(next);
        }
        setCurrentTime(next);
    }

    async function togglePlayback() {
        if (playing) {
            pauseBoth();
            return;
        }
        const video = videoRef.current;
        if (!video || !canPlay || singleFrame) return;
        setPlaybackError(null);
        if (video.currentTime >= end - 0.05 || video.currentTime < start) seek(start);
        const request = ++playbackRequest.current;
        const comparison = comparisonRef.current;
        try {
            const players = [video];
            if (comparison && secondaryInfo && comparisonTime(video.currentTime) < comparisonEnd) {
                comparison.currentTime = comparisonTime(video.currentTime);
                players.push(comparison);
            }
            await Promise.all(players.map((player) => player.play()));
            if (request !== playbackRequest.current) players.forEach((player) => player.pause());
        } catch {
            if (request !== playbackRequest.current) return;
            pauseBoth();
            setPlaybackError("Chưa phát được video. Hãy bấm Phát để thử lại.");
        }
    }

    function readMetadata(video: HTMLVideoElement, comparison: boolean) {
        const source = comparison ? compareUrl! : url;
        if (
            !Number.isFinite(video.duration) ||
            video.duration <= 0 ||
            video.videoWidth <= 0 ||
            video.videoHeight <= 0
        ) {
            reportFailure(source, comparison, "Không đọc được thời lượng hoặc kích thước video.");
            return;
        }
        const next = {
            source,
            width: video.videoWidth,
            height: video.videoHeight,
            duration: video.duration,
        };
        if (comparison) {
            setComparisonInfo(next);
            setComparisonFailure(null);
            video.currentTime = getComparisonPlaybackTime(
                videoRef.current?.currentTime ?? requestedStart,
                requestedStart,
                Math.min(video.duration, Math.max(0, requestedComparisonStart)),
                Math.min(
                    video.duration,
                    Math.max(
                        0,
                        compareScope === undefined
                            ? requestedEnd
                            : (compareScope?.end ?? video.duration),
                    ),
                ),
            );
        } else {
            setInfo(next);
            setFailure(null);
            onMetadata?.(video.duration);
        }
    }

    function reportFailure(source: string, comparison: boolean, message: string) {
        if (comparison) setComparisonFailure({ source, message });
        else setFailure({ source, message });
        pauseBoth();
        onError?.();
    }

    function updateTime(video: HTMLVideoElement) {
        const time = clampRemakePreviewTime(video.currentTime, start, end);
        setCurrentTime(time);
        if (canPlay && video.currentTime >= end) {
            pauseBoth();
            video.currentTime = lastTime;
        }
        const comparison = comparisonRef.current;
        if (!comparison || !secondaryInfo) return;
        const mappedTime = comparisonTime(time);
        if (mappedTime >= Math.max(comparisonStart, comparisonEnd - 1 / 24)) {
            comparison.pause();
            comparison.currentTime = mappedTime;
            return;
        }
        if (Math.abs(comparison.currentTime - mappedTime) > 0.15)
            comparison.currentTime = mappedTime;
        if (comparison.paused && !video.paused) {
            void comparison.play().catch(() => {
                pauseBoth();
                setPlaybackError("Chưa đồng bộ được hai video. Hãy bấm Phát để thử lại.");
            });
        }
    }

    function selectVersion(version: "current" | "compare") {
        if (version === "compare" && secondaryFailure) return;
        const comparison = comparisonRef.current;
        if (comparison && secondaryInfo) {
            comparison.currentTime = comparisonTime(videoRef.current?.currentTime ?? start);
        }
        setActiveVersion(version);
    }

    function frame(comparison: boolean) {
        const metadata = comparison ? secondaryInfo : primaryInfo;
        const error = comparison ? secondaryFailure : primaryFailure;
        const label = comparison ? compareLabel : versionLabel;
        const visible = !hasComparison || wideComparison || (active === "compare") === comparison;
        return (
            <figure className={cn("min-w-0 flex-1", !visible && "hidden")}>
                <div
                    className="relative mx-auto overflow-hidden rounded-xl bg-black"
                    style={nativeFrameStyle(metadata)}
                >
                    <video
                        ref={comparison ? comparisonRef : videoRef}
                        src={comparison ? compareUrl : url}
                        poster={comparison ? undefined : poster}
                        playsInline
                        preload="metadata"
                        muted={muted || (comparison ? active !== "compare" : active === "compare")}
                        className="h-full w-full object-contain"
                        aria-label={`Video ${label}`}
                        onLoadedMetadata={(event) => readMetadata(event.currentTarget, comparison)}
                        onError={() =>
                            reportFailure(
                                comparison ? compareUrl! : url,
                                comparison,
                                "Không tải được video. Hãy kiểm tra kết nối hoặc mở lại dự án.",
                            )
                        }
                        onPlay={comparison ? undefined : () => setPlaying(true)}
                        onWaiting={comparison ? undefined : () => comparisonRef.current?.pause()}
                        onPlaying={
                            comparison ? undefined : (event) => updateTime(event.currentTarget)
                        }
                        onPause={
                            comparison
                                ? undefined
                                : () => {
                                      comparisonRef.current?.pause();
                                      setPlaying(false);
                                  }
                        }
                        onEnded={comparison ? undefined : pauseBoth}
                        onTimeUpdate={
                            comparison ? undefined : (event) => updateTime(event.currentTarget)
                        }
                    />
                    {(!metadata || error) && (
                        <div
                            className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-slate-950/90 px-5 text-center text-sm text-white"
                            role={error ? "alert" : "status"}
                        >
                            {error ? (
                                <AlertCircle aria-hidden className="size-6" />
                            ) : (
                                <LoaderCircle
                                    aria-hidden
                                    className="size-6 motion-safe:animate-spin"
                                />
                            )}
                            <span>{error ?? "Đang đọc thông tin video"}</span>
                        </div>
                    )}
                </div>
                <figcaption className="mt-3 text-center text-xs font-medium text-text-secondary">
                    {label}
                    {metadata && (
                        <span className="ml-2 text-text-tertiary">
                            {metadata.width} × {metadata.height}
                        </span>
                    )}
                </figcaption>
            </figure>
        );
    }

    return (
        <div ref={containerRef} className="min-w-0 space-y-4">
            {hasComparison && (
                <div
                    className="flex flex-wrap items-center justify-center gap-2"
                    role="group"
                    aria-label="Chọn phiên bản để xem và nghe"
                >
                    {(["current", "compare"] as const).map((version) => (
                        <Button
                            key={version}
                            type="button"
                            variant={active === version ? "default" : "outline"}
                            className="min-h-11 whitespace-normal px-4"
                            aria-pressed={active === version}
                            disabled={
                                version === "compare" &&
                                (!secondaryInfo || Boolean(secondaryFailure))
                            }
                            onClick={() => selectVersion(version)}
                        >
                            {version === "current" ? versionLabel : compareLabel}
                        </Button>
                    ))}
                </div>
            )}

            <div className="flex items-start justify-center gap-4">
                {frame(false)}
                {hasComparison && frame(true)}
            </div>

            <div className="rounded-xl bg-surface-soft p-3">
                <div className="flex items-center gap-2">
                    <Button
                        type="button"
                        variant="outline"
                        className="size-11 shrink-0 px-0"
                        disabled={!canPlay || singleFrame}
                        onClick={() => void togglePlayback()}
                        aria-label={playing ? "Tạm dừng video" : "Phát video"}
                    >
                        {playing ? <Pause aria-hidden /> : <Play aria-hidden />}
                    </Button>
                    <span className="min-w-0 flex-1 text-xs tabular-nums text-text-secondary">
                        {primaryInfo ? `${formatTime(safeTime)} / ${formatTime(end)}` : "— / —"}
                        <span className="mt-0.5 block text-text-tertiary">
                            {scope
                                ? singleFrame
                                    ? "Một frame được chọn"
                                    : `Đoạn được chọn${primaryInfo ? ` · ${formatTime(start)}–${formatTime(end)}` : ""}`
                                : "Toàn bộ video"}
                        </span>
                    </span>
                    <Button
                        type="button"
                        variant="ghost"
                        className="size-11 shrink-0 px-0"
                        aria-label={muted ? "Bật âm thanh" : "Tắt âm thanh"}
                        aria-pressed={!muted}
                        onClick={() => setMuted((value) => !value)}
                    >
                        {muted ? <VolumeX aria-hidden /> : <Volume2 aria-hidden />}
                    </Button>
                </div>
                <input
                    type="range"
                    min={start}
                    max={lastTime}
                    step={0.05}
                    value={safeTime}
                    disabled={!canPlay}
                    onChange={(event) => seek(Number(event.target.value))}
                    aria-label="Vị trí phát video"
                    aria-valuetext={`${formatTime(safeTime)} trên ${formatTime(end)}`}
                    className="mt-1 h-11 w-full cursor-pointer accent-primary disabled:cursor-default"
                />
                {hasComparison && (
                    <p className="text-xs text-text-tertiary">
                        {scope && compareScope
                            ? `Hai đoạn phát cùng nhịp cảnh · ${formatTime(scope.start)}–${formatTime(scope.end)} ↔ ${formatTime(compareScope.start)}–${formatTime(compareScope.end)}.`
                            : wideComparison
                              ? "Hai bản phát cùng thời điểm."
                              : "Đổi bản để so sánh tại cùng thời điểm."}{" "}
                        Âm thanh: {active === "compare" ? compareLabel : versionLabel}.
                    </p>
                )}
                {comparisonShorter && (
                    <p className="mt-2 text-xs text-text-secondary">
                        Đoạn so sánh dài {formatTime(comparisonEnd - comparisonStart)}; phần còn lại
                        chỉ có ở bản đang dùng.
                    </p>
                )}
                {secondaryFailure && (
                    <p role="alert" className="mt-2 text-sm text-destructive">
                        {compareLabel}: {secondaryFailure}
                    </p>
                )}
                {invalidScope && (
                    <p role="alert" className="text-sm text-destructive">
                        Đoạn được chọn nằm ngoài thời lượng video. Hãy chọn cảnh khác hoặc xem toàn
                        bộ video.
                    </p>
                )}
                {playbackError && (
                    <p role="alert" className="text-sm text-destructive">
                        {playbackError}
                    </p>
                )}
            </div>
        </div>
    );
}
