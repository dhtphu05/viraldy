import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { AlertCircle, LoaderCircle, Pause, Play, Volume2, VolumeX } from "lucide-react";

import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import {
    clampRemakePreviewTime,
    getComparisonPlaybackTime,
    type RemakePreviewScope,
} from "../lib/remake-preview";
import {
    getSourceComparisonPlayback,
    type RemakeSourceComparisonSegment,
} from "../lib/remake-source-comparison";

export interface RemakePlayerProps {
    url: string;
    compareUrl?: string;
    poster?: string;
    scope: { start: number; end: number } | null;
    compareScope?: RemakePreviewScope;
    sourceComparison?: { url: string; segments: readonly RemakeSourceComparisonSegment[] };
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
    const sourceIdentity = JSON.stringify(props.sourceComparison ?? null);
    const stableSource = useMemo<RemakePlayerProps["sourceComparison"]>(
        () => JSON.parse(sourceIdentity) ?? undefined,
        [sourceIdentity],
    );
    const identity =
        stableSource && !props.compareUrl ? `${props.url}:${sourceIdentity}` : props.url;
    return <PlayerSession key={identity} {...props} sourceComparison={stableSource} />;
}

function PlayerSession({
    url,
    compareUrl,
    poster,
    scope,
    compareScope,
    sourceComparison,
    versionLabel = "Bản đang dùng",
    compareLabel = "Bản mới",
    onError,
    onMetadata,
}: RemakePlayerProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const videoRef = useRef<HTMLVideoElement>(null);
    const comparisonRef = useRef<HTMLVideoElement>(null);
    const playbackRequest = useRef(0);
    const playbackWanted = useRef(false);
    const playPending = useRef(false);
    const bufferState = useRef({ primary: false, secondary: false });
    const internalPauses = useRef(new WeakMap<HTMLMediaElement, number>());
    const [containerWidth, setContainerWidth] = useState(0);
    const [info, setInfo] = useState<MediaInfo | null>(null);
    const [comparisonInfo, setComparisonInfo] = useState<MediaInfo | null>(null);
    const [failure, setFailure] = useState<MediaFailure | null>(null);
    const [comparisonFailure, setComparisonFailure] = useState<MediaFailure | null>(null);
    const [playing, setPlaying] = useState(false);
    const [starting, setStarting] = useState(false);
    const [remakeOnly, setRemakeOnly] = useState(false);
    const [sourceAttempt, setSourceAttempt] = useState(0);
    const [buffering, setBuffering] = useState({ primary: false, secondary: false });
    const [muted, setMuted] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [activeVersion, setActiveVersion] = useState<"current" | "compare">("current");
    const [playbackError, setPlaybackError] = useState<string | null>(null);

    const sourceMode = Boolean(sourceComparison && !compareUrl && !remakeOnly);
    const secondaryUrl = sourceMode ? sourceComparison!.url : compareUrl;
    const primaryInfo = info?.source === url ? info : null;
    const secondaryInfo = comparisonInfo?.source === secondaryUrl ? comparisonInfo : null;
    const primaryFailure = failure?.source === url ? failure.message : null;
    const secondaryFailure =
        comparisonFailure && comparisonFailure.source === secondaryUrl
            ? comparisonFailure.message
            : null;
    const hasComparison = Boolean(compareUrl);
    const active = hasComparison || sourceMode ? activeVersion : "current";
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
        !sourceMode && secondaryInfo && comparisonEnd - comparisonStart < end - start,
    );
    const comparisonTime = useCallback(
        (time: number) =>
            sourceMode
                ? (getSourceComparisonPlayback(sourceComparison!.segments, time)?.time ?? 0)
                : getComparisonPlaybackTime(time, start, comparisonStart, comparisonEnd),
        [sourceMode, sourceComparison, start, comparisonStart, comparisonEnd],
    );
    const canPlay = Boolean(
        primaryInfo &&
        !primaryFailure &&
        !invalidScope &&
        (!sourceMode ||
            (secondaryInfo &&
                !secondaryFailure &&
                !buffering.primary &&
                !buffering.secondary &&
                getSourceComparisonPlayback(sourceComparison!.segments, start))),
    );
    const singleFrame = Boolean(
        scope && requestedEnd > requestedStart && requestedEnd - requestedStart <= 1 / 24 + 1e-6,
    );
    const lastTime = Math.max(start, end - 1 / 24);
    const safeTime = clampRemakePreviewTime(currentTime, start, end);

    const stopPlayers = useCallback(() => {
        for (const player of [videoRef.current, comparisonRef.current]) {
            if (!player) continue;
            if (!player.paused)
                internalPauses.current.set(player, (internalPauses.current.get(player) ?? 0) + 1);
            player.pause();
        }
    }, []);
    const pauseBoth = useCallback(() => {
        playbackWanted.current = false;
        playbackRequest.current += 1;
        playPending.current = false;
        stopPlayers();
        setPlaying(false);
        setStarting(false);
    }, [stopPlayers]);
    const reportFailure = useCallback(
        (source: string, comparison: boolean, message: string) => {
            if (comparison) setComparisonFailure({ source, message });
            else setFailure({ source, message });
            pauseBoth();
            if (!(comparison && sourceMode)) onError?.();
        },
        [pauseBoth, sourceMode, onError],
    );
    const syncSource = useCallback(
        (time: number, force = false) => {
            const comparison = comparisonRef.current;
            const mapped = sourceMode
                ? getSourceComparisonPlayback(sourceComparison!.segments, time)
                : null;
            if (!comparison || !secondaryInfo || !mapped) return false;
            try {
                const rate = Math.min(16, Math.max(0.0625, mapped.playbackRate));
                const speedChanged = comparison.playbackRate !== rate;
                try {
                    comparison.playbackRate = rate;
                } catch {
                    comparison.playbackRate = Math.min(4, Math.max(0.5, rate));
                }
                const mappedTime = Math.min(secondaryInfo.duration - 1 / 24, mapped.time);
                const drift = Math.abs(comparison.currentTime - mappedTime);
                if (drift > (force || speedChanged ? 1e-6 : 0.15))
                    comparison.currentTime = Math.max(0, mappedTime);
                return true;
            } catch {
                reportFailure(
                    secondaryUrl!,
                    true,
                    "Không đồng bộ được video gốc. Thử tải lại hoặc chỉ xem bản remake.",
                );
                return false;
            }
        },
        [sourceMode, sourceComparison, secondaryInfo, secondaryUrl, reportFailure],
    );

    useEffect(() => {
        const video = videoRef.current;
        const comparison = comparisonRef.current;
        return () => {
            playbackWanted.current = false;
            playbackRequest.current += 1;
            video?.pause();
            comparison?.pause();
        };
    }, [sourceAttempt]);

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
            if (sourceMode) syncSource(video.currentTime, true);
            else comparisonRef.current.currentTime = comparisonTime(video.currentTime);
        }
    }, [
        start,
        end,
        primaryInfo,
        secondaryInfo,
        invalidScope,
        comparisonStart,
        comparisonEnd,
        sourceMode,
        comparisonTime,
        syncSource,
    ]);

    useEffect(() => {
        const video = videoRef.current;
        if (!video || !playing || !canPlay) return;
        let callback = 0;
        const usesVideoFrames = typeof video.requestVideoFrameCallback === "function";
        const check = (mediaTime: number) => {
            if (sourceMode) syncSource(Math.min(mediaTime, lastTime));
            if (mediaTime + 1e-6 >= lastTime) {
                playbackWanted.current = false;
                playbackRequest.current += 1;
                video.pause();
                video.currentTime = lastTime;
                const comparison = comparisonRef.current;
                if (comparison) {
                    comparison.pause();
                    comparison.currentTime = comparisonTime(lastTime);
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
    }, [
        playing,
        canPlay,
        lastTime,
        start,
        comparisonStart,
        comparisonEnd,
        sourceMode,
        comparisonTime,
        syncSource,
    ]);

    function seek(time: number, preservePlayback = false) {
        if (starting && !preservePlayback) pauseBoth();
        const next = clampRemakePreviewTime(time, start, end);
        if (videoRef.current) videoRef.current.currentTime = next;
        if (comparisonRef.current && secondaryInfo) {
            if (sourceMode) syncSource(next, true);
            else comparisonRef.current.currentTime = comparisonTime(next);
        }
        setCurrentTime(next);
    }

    async function startPlayback(resuming = false) {
        const video = videoRef.current;
        if (!video || playPending.current || singleFrame) return;
        if (
            sourceMode &&
            (!secondaryInfo || bufferState.current.primary || bufferState.current.secondary)
        )
            return;
        setPlaybackError(null);
        if (video.currentTime >= end - 0.05 || video.currentTime < start) seek(start, true);
        const request = ++playbackRequest.current;
        playbackWanted.current = true;
        playPending.current = true;
        setStarting(true);
        const comparison = comparisonRef.current;
        try {
            const players = [video];
            if (
                comparison &&
                secondaryInfo &&
                (sourceMode || comparisonTime(video.currentTime) < comparisonEnd)
            ) {
                if (sourceMode) {
                    if (!syncSource(video.currentTime, !resuming)) return;
                } else comparison.currentTime = comparisonTime(video.currentTime);
                players.push(comparison);
            }
            await Promise.all(
                players.map(async (player) => {
                    try {
                        await player.play();
                    } catch (error) {
                        if (
                            sourceMode &&
                            player === comparison &&
                            request === playbackRequest.current
                        )
                            setComparisonFailure({
                                source: secondaryUrl!,
                                message:
                                    "Chưa phát được video gốc. Thử tải lại hoặc chỉ xem bản remake.",
                            });
                        throw error;
                    }
                }),
            );
            if (request !== playbackRequest.current) {
                players.forEach((player) => {
                    if (
                        !playbackWanted.current ||
                        (player !== videoRef.current && player !== comparisonRef.current)
                    )
                        player.pause();
                });
                if (bufferState.current.primary || bufferState.current.secondary) stopPlayers();
                return;
            }
            playPending.current = false;
            setStarting(false);
            if (sourceMode) setPlaying(true);
        } catch {
            if (request !== playbackRequest.current) return;
            pauseBoth();
            setPlaybackError("Chưa phát được video. Hãy bấm Phát để thử lại.");
        }
    }
    function togglePlayback() {
        if (playing || starting || playbackWanted.current) pauseBoth();
        else if (canPlay) void startPlayback();
    }
    function waitForMedia(comparison: boolean) {
        if (!sourceMode) {
            if (!comparison) comparisonRef.current?.pause();
            return;
        }
        bufferState.current = {
            ...bufferState.current,
            [comparison ? "secondary" : "primary"]: true,
        };
        setBuffering(bufferState.current);
        if (!playbackWanted.current) return;
        playbackRequest.current += 1;
        playPending.current = false;
        stopPlayers();
        setPlaying(false);
        setStarting(true);
    }
    function mediaReady(comparison: boolean) {
        if (!sourceMode) return;
        bufferState.current = {
            ...bufferState.current,
            [comparison ? "secondary" : "primary"]: false,
        };
        setBuffering(bufferState.current);
        if (
            playbackWanted.current &&
            !bufferState.current.primary &&
            !bufferState.current.secondary &&
            (videoRef.current?.readyState ?? 0) >= 2 &&
            (comparisonRef.current?.readyState ?? 0) >= 2
        )
            void startPlayback(true);
    }
    function readMetadata(video: HTMLVideoElement, comparison: boolean) {
        const source = comparison ? secondaryUrl! : url;
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
            if (
                sourceMode &&
                sourceComparison!.segments.some(
                    (segment) => segment.sourceEnd > video.duration + 1 / 24,
                )
            ) {
                reportFailure(
                    source,
                    true,
                    "Phạm vi kịch bản vượt thời lượng video gốc. Thử tải lại hoặc chỉ xem bản remake.",
                );
                return;
            }
            setComparisonInfo(next);
            setComparisonFailure(null);
            video.currentTime = sourceMode
                ? comparisonTime(videoRef.current?.currentTime ?? requestedStart)
                : getComparisonPlaybackTime(
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

    function updateTime(video: HTMLVideoElement) {
        const time = clampRemakePreviewTime(video.currentTime, start, end);
        setCurrentTime(time);
        if (canPlay && video.currentTime >= end) {
            pauseBoth();
            video.currentTime = lastTime;
        }
        const comparison = comparisonRef.current;
        if (!comparison || !secondaryInfo) return;
        if (sourceMode) {
            syncSource(time);
            return;
        }
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
        const label = sourceMode
            ? comparison
                ? "Video gốc"
                : "Bản remake"
            : comparison
              ? compareLabel
              : versionLabel;
        const visible =
            sourceMode || !hasComparison || wideComparison || (active === "compare") === comparison;
        return (
            <figure className={cn("min-w-0 flex-1", !visible && "hidden")}>
                <div
                    className="relative mx-auto overflow-hidden rounded-xl bg-black"
                    style={nativeFrameStyle(metadata)}
                >
                    <video
                        key={comparison && sourceMode ? sourceAttempt : undefined}
                        ref={comparison ? comparisonRef : videoRef}
                        src={comparison ? secondaryUrl : url}
                        poster={comparison ? undefined : poster}
                        playsInline
                        preload="metadata"
                        muted={muted || (comparison ? active !== "compare" : active === "compare")}
                        className="h-full w-full object-contain"
                        aria-label={sourceMode ? label : `Video ${label}`}
                        onLoadedMetadata={(event) => readMetadata(event.currentTarget, comparison)}
                        onError={() =>
                            reportFailure(
                                comparison ? secondaryUrl! : url,
                                comparison,
                                "Không tải được video. Hãy kiểm tra kết nối hoặc mở lại dự án.",
                            )
                        }
                        onPlay={comparison || sourceMode ? undefined : () => setPlaying(true)}
                        onWaiting={() => waitForMedia(comparison)}
                        onCanPlay={() => mediaReady(comparison)}
                        onPlaying={
                            comparison ? undefined : (event) => updateTime(event.currentTarget)
                        }
                        onPause={
                            comparison && !sourceMode
                                ? undefined
                                : (event) => {
                                      if (sourceMode) {
                                          const count =
                                              internalPauses.current.get(event.currentTarget) ?? 0;
                                          if (count)
                                              internalPauses.current.set(
                                                  event.currentTarget,
                                                  count - 1,
                                              );
                                          else pauseBoth();
                                      } else {
                                          pauseBoth();
                                      }
                                  }
                        }
                        onEnded={
                            sourceMode
                                ? () => {
                                      pauseBoth();
                                      if (!comparison) seek(lastTime);
                                  }
                                : comparison
                                  ? undefined
                                  : pauseBoth
                        }
                        onSeeking={
                            sourceMode && !comparison
                                ? (event) => {
                                      syncSource(event.currentTarget.currentTime, true);
                                  }
                                : undefined
                        }
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
            {sourceMode && (
                <div
                    role="group"
                    aria-label="Chọn âm thanh để nghe"
                    className="flex flex-wrap justify-center gap-2"
                >
                    {(["compare", "current"] as const).map((version) => (
                        <Button
                            key={version}
                            type="button"
                            variant={active === version ? "default" : "outline"}
                            className="min-h-11 min-w-0 whitespace-normal px-3"
                            aria-pressed={active === version}
                            onClick={() => setActiveVersion(version)}
                        >
                            {version === "compare" ? "Nghe video gốc" : "Nghe bản remake"}
                        </Button>
                    ))}
                </div>
            )}
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

            <div
                className={cn(
                    "flex items-start justify-center",
                    sourceMode ? "gap-2 sm:gap-4" : "gap-4",
                )}
            >
                {sourceMode && frame(true)}
                {frame(false)}
                {hasComparison && frame(true)}
            </div>

            <div className="rounded-xl bg-surface-soft p-3">
                <div className="flex items-center gap-2">
                    <Button
                        type="button"
                        variant="outline"
                        className="size-11 shrink-0 px-0"
                        disabled={(!canPlay && !playing && !starting) || singleFrame}
                        onClick={() => void togglePlayback()}
                        aria-label={playing || starting ? "Tạm dừng video" : "Phát video"}
                    >
                        {playing || starting ? <Pause aria-hidden /> : <Play aria-hidden />}
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
                {sourceMode && (
                    <p className="text-xs text-text-tertiary">
                        Video gốc được điều chỉnh tốc độ theo từng cảnh trong kịch bản. Phát, dừng
                        và tua cả hai bằng thanh chung.
                    </p>
                )}
                {sourceMode && (buffering.primary || buffering.secondary) && (
                    <p role="status" className="mt-2 text-xs text-text-secondary">
                        Đang tải khung hình. Hai video sẽ tự phát tiếp khi cùng sẵn sàng.
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
                        {sourceMode ? "Video gốc" : compareLabel}: {secondaryFailure}
                    </p>
                )}
                {sourceMode && secondaryFailure && (
                    <div className="mt-2 flex flex-wrap gap-2">
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => {
                                pauseBoth();
                                setComparisonInfo(null);
                                setComparisonFailure(null);
                                setBuffering({ primary: false, secondary: false });
                                setSourceAttempt((value) => value + 1);
                            }}
                        >
                            Tải lại video gốc
                        </Button>
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => {
                                pauseBoth();
                                setActiveVersion("current");
                                setRemakeOnly(true);
                            }}
                        >
                            Chỉ xem bản remake
                        </Button>
                    </div>
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
