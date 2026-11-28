import { useEffect, useId, useRef, useState } from "react";
import { Check, Film, Loader2, Plus, Scissors, Target, X } from "lucide-react";

import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { validateSourceCuts } from "../lib/remake-timeline";

const FPS = 24;
const time = (frames: number) => Number((frames / FPS).toFixed(3)).toLocaleString("vi-VN");
const fieldClass =
    "h-11 border-0 bg-surface-soft shadow-none focus-visible:ring-2 focus-visible:ring-ring/60";

export function RemakeExcerptControls({
    durationSeconds,
    targetSeconds,
    startFrame,
    currentSeconds,
    onChange,
    disabled,
}: {
    durationSeconds: number | null;
    targetSeconds: 8 | 12 | 16;
    startFrame: number;
    currentSeconds: number;
    onChange(frame: number): void;
    disabled: boolean;
}) {
    const id = useId();
    const total = durationSeconds === null ? null : Math.floor(durationSeconds * FPS + 0.01);
    const length = targetSeconds * FPS;
    const max = Math.max(0, (total ?? length) - length);
    const tooShort = total !== null && total < length;
    const invalidStart = startFrame < 0 || startFrame > max;
    const unavailable = disabled || total === null || tooShort;
    const setStart = (frame: number) => onChange(Math.max(0, Math.min(max, Math.round(frame))));
    return (
        <div className="mt-4 space-y-3 rounded-2xl bg-surface-soft/70 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="flex items-center gap-2 text-sm font-medium text-text-primary">
                    <Scissors className="size-4 text-primary" aria-hidden="true" />
                    Đoạn mẫu sẽ dùng
                </h3>
                <span className="text-xs tabular-nums text-text-secondary">
                    {time(startFrame)}–{time(startFrame + length)} giây
                </span>
            </div>
            <div className="remake-excerpt-track" aria-hidden="true">
                <span
                    style={{
                        left: `${total ? (startFrame / total) * 100 : 0}%`,
                        width: `${total ? Math.min(100, (length / total) * 100) : 100}%`,
                    }}
                >
                    {targetSeconds} giây
                </span>
            </div>
            <input
                type="range"
                min={0}
                max={max}
                step={1}
                value={Math.min(max, startFrame)}
                disabled={unavailable}
                onChange={(event) => setStart(Number(event.target.value))}
                aria-label="Điểm bắt đầu đoạn mẫu"
                aria-valuetext={`${time(startFrame)} giây; dùng ${targetSeconds} giây tiếp theo`}
                className="h-11 w-full cursor-pointer accent-primary disabled:cursor-default"
            />
            <div className="flex flex-wrap items-end gap-2">
                <div className="min-w-0 flex-1 space-y-1">
                    <label htmlFor={`${id}-start`} className="text-xs text-text-secondary">
                        Bắt đầu tại (giây)
                    </label>
                    <Input
                        id={`${id}-start`}
                        type="number"
                        inputMode="decimal"
                        min={0}
                        max={max / FPS}
                        step={1 / FPS}
                        value={Number((startFrame / FPS).toFixed(3))}
                        disabled={unavailable}
                        onChange={(event) => setStart(Number(event.target.value) * FPS)}
                        className={cn(fieldClass, "bg-surface")}
                    />
                </div>
                <Button
                    type="button"
                    variant="ghost"
                    disabled={unavailable}
                    className="min-h-11 bg-surface px-3 text-xs"
                    onClick={() => setStart(currentSeconds * FPS)}
                >
                    <Target className="size-4" aria-hidden="true" />
                    Dùng vị trí hiện tại
                </Button>
            </div>
            {tooShort ? (
                <p role="alert" className="text-xs leading-relaxed text-destructive">
                    Video mẫu chưa đủ {targetSeconds} giây.{" "}
                    {targetSeconds === 16 && total >= 8 * FPS
                        ? "Chọn 8 giây hoặc đổi video mẫu."
                        : "Hãy chọn video dài hơn."}
                </p>
            ) : invalidStart ? (
                <p role="alert" className="text-xs text-destructive">
                    Đoạn chọn vượt video mẫu. Chọn lại điểm bắt đầu trước khi tiếp tục.
                </p>
            ) : (
                <p className="text-xs leading-relaxed text-text-secondary">
                    {total === null
                        ? "Đang đọc thời lượng video mẫu…"
                        : "Kéo để chọn đoạn bạn thích. Nhịp và thời lượng từng cảnh sẽ được giữ khi dựng."}
                </p>
            )}
        </div>
    );
}

export interface RemakeSourceTimelineProps {
    referenceUrl?: string | null;
    sourceStartFrame: number;
    totalFrames: number;
    sourceCutFrames: number[];
    compiledCutFrames: number[];
    selectedScene: number;
    onSelect(index: number): void;
    onCutsChange?(cuts: number[]): void;
    onRecompile?(): void;
    disabled?: boolean;
    isRecompiling?: boolean;
    thumbnails?: Array<string | undefined>;
}

export function RemakeSourceTimeline({
    referenceUrl,
    sourceStartFrame,
    totalFrames,
    sourceCutFrames: cuts,
    compiledCutFrames,
    selectedScene,
    onSelect,
    onCutsChange,
    onRecompile,
    disabled = false,
    isRecompiling = false,
    thumbnails,
}: RemakeSourceTimelineProps) {
    const seekId = useId();
    const sourceKey = `${referenceUrl}:${sourceStartFrame}:${totalFrames}`;
    const video = useRef<HTMLVideoElement>(null);
    const sceneStrip = useRef<HTMLDivElement>(null);
    const selectedButton = useRef<HTMLButtonElement>(null);
    const [position, setPosition] = useState({ source: sourceKey, frame: 0 });
    const [mediaInfo, setMediaInfo] = useState<{
        source: string;
        ratio: number;
        duration: number;
        failed?: boolean;
    } | null>(null);
    const currentMedia = mediaInfo?.source === sourceKey ? mediaInfo : null;
    const availableFrames = currentMedia
        ? Math.min(
              totalFrames,
              Math.max(0, Math.ceil(currentMedia.duration * FPS) - sourceStartFrame),
          )
        : totalFrames;
    const lastFrame = Math.max(0, availableFrames - 1);
    const playhead = position.source === sourceKey ? Math.min(position.frame, lastFrame) : 0;
    const ratio = currentMedia?.ratio ?? 9 / 16;
    const canSeek = Boolean(
        referenceUrl && currentMedia && !currentMedia.failed && availableFrames > 0,
    );
    const dirty = JSON.stringify(cuts) !== JSON.stringify(compiledCutFrames);
    const lengths = cuts.slice(1).map((end, index) => end - cuts[index]);
    useEffect(() => {
        const strip = sceneStrip.current;
        const button = selectedButton.current;
        if (!strip || !button) return;
        const right = button.offsetLeft + button.offsetWidth;
        if (button.offsetLeft < strip.scrollLeft) strip.scrollLeft = button.offsetLeft;
        else if (right > strip.scrollLeft + strip.clientWidth)
            strip.scrollLeft = right - strip.clientWidth;
    }, [selectedScene, sourceKey, lengths.length]);
    function updatePosition(frame: number) {
        const next = Math.max(0, Math.min(lastFrame, Math.round(frame)));
        setPosition({ source: sourceKey, frame: next });
        const scene = lengths.findIndex(
            (_, index) => next >= cuts[index] && next < cuts[index + 1],
        );
        if (!disabled && scene >= 0 && scene !== selectedScene) onSelect(scene);
        return next;
    }
    function seek(frame: number) {
        if (disabled || !canSeek || !video.current) return;
        const next = updatePosition(frame);
        video.current.pause();
        video.current.currentTime = (sourceStartFrame + next) / FPS;
    }
    function followPlayback(media: HTMLVideoElement) {
        const frame = Math.round(media.currentTime * FPS) - sourceStartFrame;
        const next = updatePosition(frame);
        if (frame < 0 || frame > lastFrame) {
            media.pause();
            media.currentTime = (sourceStartFrame + next) / FPS;
        }
    }
    function select(index: number) {
        if (disabled) return;
        onSelect(index);
        const frame = Math.max(0, Math.min(lastFrame, cuts[index]));
        setPosition({ source: sourceKey, frame });
        if (video.current && canSeek) {
            video.current.pause();
            video.current.currentTime = (sourceStartFrame + frame) / FPS;
        }
    }
    return (
        <section aria-label="Timeline video mẫu" className="rounded-3xl bg-surface p-4 sm:p-6">
            <div className="space-y-4">
                <div className="min-w-0 space-y-4">
                    <div className="flex min-h-56 items-center justify-center rounded-2xl bg-surface-soft p-3">
                        {referenceUrl ? (
                            <video
                                key={sourceKey}
                                ref={video}
                                src={referenceUrl}
                                controls
                                playsInline
                                preload="metadata"
                                aria-label="Video mẫu — xem theo từng cảnh"
                                className="block h-auto max-h-[min(42dvh,320px)] max-w-full rounded-xl bg-black object-contain"
                                style={{
                                    aspectRatio: ratio,
                                    width: `min(100%, calc(min(42dvh, 320px) * ${ratio}))`,
                                }}
                                onLoadedMetadata={(event) => {
                                    const media = event.currentTarget;
                                    setMediaInfo({
                                        source: sourceKey,
                                        ratio:
                                            media.videoWidth && media.videoHeight
                                                ? media.videoWidth / media.videoHeight
                                                : 9 / 16,
                                        duration: media.duration,
                                    });
                                    const frame = Math.max(
                                        0,
                                        Math.min(totalFrames - 1, cuts[selectedScene] ?? 0),
                                    );
                                    setPosition({ source: sourceKey, frame });
                                    media.currentTime = (sourceStartFrame + frame) / FPS;
                                }}
                                onTimeUpdate={(event) => followPlayback(event.currentTarget)}
                                onSeeked={(event) => followPlayback(event.currentTarget)}
                                onError={() =>
                                    setMediaInfo({
                                        source: sourceKey,
                                        ratio: 9 / 16,
                                        duration: 0,
                                        failed: true,
                                    })
                                }
                            />
                        ) : (
                            <div className="py-14 text-center text-text-tertiary">
                                <Film className="mx-auto mb-2 size-8" aria-hidden="true" />
                                <p className="text-sm">Video mẫu tham chiếu</p>
                            </div>
                        )}
                    </div>
                    <div ref={sceneStrip} className="remake-filmstrip-scroll">
                        <div
                            className="remake-filmstrip"
                            role="group"
                            aria-label="Chọn cảnh từ video mẫu"
                            style={{
                                display: "grid",
                                gridAutoFlow: "column",
                                gridAutoColumns: "minmax(100px, 1fr)",
                            }}
                        >
                            {lengths.map((length, index) => (
                                <button
                                    key={index}
                                    ref={selectedScene === index ? selectedButton : undefined}
                                    type="button"
                                    disabled={disabled}
                                    onClick={() => select(index)}
                                    aria-pressed={selectedScene === index}
                                    title={`Cảnh ${index + 1} · ${time(length)} giây`}
                                    className={cn(
                                        "remake-filmstrip-scene",
                                        selectedScene === index && "is-selected",
                                    )}
                                >
                                    <span className="remake-scene-grain" aria-hidden="true">
                                        {!dirty && thumbnails?.[index] ? (
                                            <img
                                                src={thumbnails[index]}
                                                alt=""
                                                loading="lazy"
                                                className="h-full w-full object-contain"
                                            />
                                        ) : (
                                            <Film className="size-5 opacity-40" />
                                        )}
                                    </span>
                                    <strong>Cảnh {index + 1}</strong>
                                    <span>{time(length)} giây</span>
                                </button>
                            ))}
                        </div>
                    </div>
                    <div className="space-y-1">
                        <div className="flex items-center justify-between gap-3 text-xs text-text-secondary">
                            <label htmlFor={seekId}>Vị trí phát</label>
                            <output className="tabular-nums" htmlFor={seekId}>
                                {time(sourceStartFrame + playhead)} /{" "}
                                {time(sourceStartFrame + totalFrames)} giây
                            </output>
                        </div>
                        <input
                            id={seekId}
                            type="range"
                            min={0}
                            max={lastFrame}
                            step={1}
                            value={playhead}
                            disabled={disabled || !canSeek}
                            onChange={(event) => seek(Number(event.target.value))}
                            aria-label="Tua video mẫu"
                            aria-valuetext={`${time(sourceStartFrame + playhead)} giây trong video mẫu`}
                            className="h-11 w-full cursor-pointer rounded-lg accent-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 focus-visible:ring-offset-2 disabled:cursor-default"
                        />
                    </div>
                    {currentMedia?.failed && (
                        <p role="alert" className="text-xs text-destructive">
                            Chưa mở được video mẫu. Thêm lại tư liệu hoặc kiểm tra kết nối nhé.
                        </p>
                    )}
                    <p className="text-xs text-text-secondary">
                        Kéo thanh tua để xem video, hoặc chọn một cảnh để duyệt kịch bản tương ứng.
                    </p>
                </div>
                {dirty && (
                    <p className="text-xs text-warn">
                        Nhịp cắt đang có thay đổi; mở Nâng cao để xem và cập nhật.
                    </p>
                )}
                <details className="rounded-2xl bg-surface-soft/60 p-4">
                    <summary className="min-h-8 cursor-pointer text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                        Nâng cao · Điều chỉnh nhịp cắt
                    </summary>
                    <RemakeBoundaryControls
                        sourceCutFrames={cuts}
                        compiledCutFrames={compiledCutFrames}
                        totalFrames={totalFrames}
                        selectedScene={selectedScene}
                        onCutsChange={onCutsChange}
                        onRecompile={onRecompile}
                        disabled={disabled}
                        isRecompiling={isRecompiling}
                    />
                </details>
            </div>
        </section>
    );
}

export function RemakeBoundaryControls({
    sourceCutFrames: cuts,
    compiledCutFrames,
    totalFrames,
    selectedScene,
    onCutsChange,
    onRecompile,
    disabled = false,
    isRecompiling = false,
}: {
    sourceCutFrames: number[];
    compiledCutFrames?: number[];
    totalFrames: number;
    selectedScene?: number;
    onCutsChange?(cuts: number[]): void;
    onRecompile?(): void;
    disabled?: boolean;
    isRecompiling?: boolean;
}) {
    const lengths = cuts.slice(1).map((end, index) => end - cuts[index]);
    const splitIndex = selectedScene ?? lengths.indexOf(Math.max(...lengths));
    const dirty =
        Boolean(compiledCutFrames) && JSON.stringify(cuts) !== JSON.stringify(compiledCutFrames);
    const error = validateSourceCuts(cuts, totalFrames);
    function updateCut(index: number, frame: number) {
        onCutsChange?.(
            cuts.map((cut, at) =>
                at === index
                    ? Math.max(
                          cuts[index - 1] + 1,
                          Math.min(cuts[index + 1] - 1, Math.round(frame)),
                      )
                    : cut,
            ),
        );
    }
    return (
        <aside className="min-w-0 space-y-4 rounded-2xl bg-surface-soft/60 p-4">
            <div>
                <h3 className="flex items-center gap-2 font-medium text-text-primary">
                    <Scissors className="size-4 text-primary" aria-hidden="true" />
                    Nhịp cắt của bạn
                </h3>
                <p className="mt-2 text-xs leading-relaxed text-text-secondary">
                    Các mốc theo toàn bộ video nguồn. Đổi mốc cắt rồi cập nhật để AI viết lại kịch
                    bản theo nhịp mới; hệ thống tự chia các lượt tạo video phù hợp.
                </p>
            </div>
            {cuts.slice(1, -1).map((frame, index) => (
                <div key={index} className="space-y-1">
                    <label className="text-xs text-text-secondary" htmlFor={`remake-cut-${index}`}>
                        Sau cảnh {index + 1} (giây trong video mẫu)
                    </label>
                    <div className="flex gap-2">
                        <Input
                            id={`remake-cut-${index}`}
                            type="number"
                            inputMode="decimal"
                            min={(cuts[index] + 1) / FPS}
                            max={(cuts[index + 2] - 1) / FPS}
                            step={1 / FPS}
                            value={Number((frame / FPS).toFixed(3))}
                            aria-label={`Mốc cắt sau cảnh ${index + 1}, giây`}
                            disabled={disabled || !onCutsChange}
                            onChange={(event) =>
                                updateCut(index + 1, Number(event.target.value) * FPS)
                            }
                            className={cn(fieldClass, "bg-surface")}
                        />
                        <Button
                            type="button"
                            variant="ghost"
                            className="size-11 shrink-0 p-0"
                            disabled={disabled || !onCutsChange}
                            aria-label={`Bỏ mốc cắt sau cảnh ${index + 1}`}
                            onClick={() => onCutsChange?.(cuts.filter((_, at) => at !== index + 1))}
                        >
                            <X className="size-4" aria-hidden="true" />
                        </Button>
                    </div>
                    <input
                        type="range"
                        min={cuts[index] + 1}
                        max={cuts[index + 2] - 1}
                        step={1}
                        value={frame}
                        disabled={disabled || !onCutsChange}
                        aria-label={`Kéo mốc cắt sau cảnh ${index + 1}`}
                        onChange={(event) => updateCut(index + 1, Number(event.target.value))}
                        className="h-11 w-full cursor-pointer accent-primary"
                    />
                </div>
            ))}
            {lengths.length > 0 && (
                <Button
                    type="button"
                    variant="ghost"
                    className="min-h-11 w-full bg-surface"
                    disabled={
                        disabled ||
                        !onCutsChange ||
                        lengths[Math.min(splitIndex, lengths.length - 1)] < 2
                    }
                    onClick={() => {
                        const index = Math.max(0, Math.min(lengths.length - 1, splitIndex));
                        onCutsChange?.([
                            ...cuts.slice(0, index + 1),
                            cuts[index] + Math.floor(lengths[index] / 2),
                            ...cuts.slice(index + 1),
                        ]);
                    }}
                >
                    <Plus className="size-4" aria-hidden="true" />
                    {selectedScene === undefined ? "Chia cảnh dài nhất" : "Chia cảnh đang chọn"}
                </Button>
            )}
            {error && (
                <p role="alert" className="text-xs leading-relaxed text-destructive">
                    {error}
                </p>
            )}
            {dirty && (
                <p role="status" className="text-xs leading-relaxed text-text-secondary">
                    Mốc cắt đã thay đổi. Cập nhật kịch bản trước khi tạo video.
                </p>
            )}
            {onRecompile && (
                <Button
                    type="button"
                    className="min-h-11 w-full"
                    disabled={disabled || Boolean(error) || !dirty}
                    onClick={onRecompile}
                >
                    {isRecompiling ? (
                        <Loader2 className="size-4 motion-safe:animate-spin" aria-hidden="true" />
                    ) : (
                        <Check className="size-4" aria-hidden="true" />
                    )}
                    Cập nhật kịch bản
                </Button>
            )}
        </aside>
    );
}
