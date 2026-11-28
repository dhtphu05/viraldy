import { useId, useState } from "react";
import { Check, ChevronLeft, ChevronRight, Loader2, Play, Scissors } from "lucide-react";

import type {
    SmartRemakeTimeline,
    SmartRemakeTimelineSelectionInput,
} from "@/shared/api/smart-remake";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import "./remake-trim-tools.css";

const seconds = (frames: number) => Number((frames / 24).toFixed(3)).toLocaleString("vi-VN");

export function RemakeTrimTools({
    item,
    versionId,
    rawFrameCount,
    plannedFrameCount = 192,
    suggestedInFrame,
    busy,
    onSave,
    onPreview,
    sharedClip = false,
}: {
    item: SmartRemakeTimeline["items"][number];
    versionId: string;
    rawFrameCount: number | null;
    plannedFrameCount?: number;
    suggestedInFrame?: number;
    busy: boolean;
    onSave(items: SmartRemakeTimelineSelectionInput[]): Promise<void>;
    onPreview(scope: { start: number; end: number } | null): void;
    sharedClip?: boolean;
}) {
    const id = useId();
    const [inFrame, setInFrame] = useState(
        item.versionId === versionId
            ? item.inFrame
            : (suggestedInFrame ?? (item.versionId === null ? item.inFrame : 0)),
    );
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const length = item.targetDurationFrames;
    const outFrame = inFrame + length;
    const measured = rawFrameCount !== null;
    const max = Math.max(0, (rawFrameCount ?? plannedFrameCount) - length);
    const tooShort = measured && rawFrameCount < length;
    const valid = measured && !tooShort && inFrame >= 0 && outFrame <= rawFrameCount;
    const canTrim = measured && !tooShort;
    const reviewed =
        item.reviewed &&
        item.versionId === versionId &&
        item.inFrame === inFrame &&
        item.outFrame === outFrame;
    const disabled = busy || saving;
    function change(frame: number) {
        const next = Math.max(0, Math.min(max, Math.round(frame)));
        setInFrame(next);
        setError(null);
        onPreview({ start: next / 24, end: (next + length) / 24 });
    }
    async function save() {
        if (disabled || !valid) return;
        setSaving(true);
        setError(null);
        try {
            await onSave([
                { renderUnitId: item.renderUnitId, versionId, inFrame, outFrame, reviewed: true },
            ]);
        } catch {
            setError("Chưa lưu được đoạn này. Lựa chọn của bạn vẫn ở đây; thử lại nhé.");
        } finally {
            setSaving(false);
        }
    }
    return (
        <section aria-label="Chọn đoạn từ clip AI" className="space-y-4 rounded-3xl bg-surface p-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="flex items-center gap-2 font-semibold text-text-primary">
                    <Scissors className="size-4 text-primary" aria-hidden="true" />
                    Đoạn sẽ dùng · {seconds(length)} giây
                </h3>
                <output className="text-xs tabular-nums text-text-secondary">
                    {seconds(inFrame)}–{seconds(outFrame)} giây
                </output>
            </div>
            <div className="remake-trim-window" role="group" aria-label="Dịch đoạn trong clip AI">
                <span
                    aria-hidden="true"
                    style={{
                        left: `${(inFrame / (rawFrameCount || plannedFrameCount)) * 100}%`,
                        width: `${Math.min(100, (length / (rawFrameCount || plannedFrameCount)) * 100)}%`,
                    }}
                >
                    {seconds(length)} giây
                </span>
                <input
                    type="range"
                    min={0}
                    max={max}
                    step={1}
                    value={Math.min(max, inFrame)}
                    disabled={disabled || !canTrim || max === 0}
                    onChange={(event) => change(Number(event.target.value))}
                    aria-label="Điểm bắt đầu trong clip AI, frame"
                    aria-valuetext={`${seconds(inFrame)} giây; kết thúc tại ${seconds(outFrame)} giây`}
                    aria-describedby={canTrim ? `${id}-trim-help` : undefined}
                    className="remake-trim-window__scrub"
                />
            </div>
            {canTrim && (
                <p id={`${id}-trim-help`} className="text-xs leading-relaxed text-text-secondary">
                    {max === 0
                        ? "Đoạn này dùng toàn bộ clip, không cần dịch điểm bắt đầu."
                        : `Kéo vùng chọn để dịch đoạn ${seconds(length)} giây trong clip.`}
                </p>
            )}
            <p role="status" className="flex items-center gap-2 text-xs text-text-secondary">
                {reviewed && <Check className="size-4 text-ok" aria-hidden="true" />}
                {reviewed ? "Đã chọn đoạn · Chưa duyệt nội dung" : "Đoạn cắt mặc định · Chưa chọn"}
            </p>
            {tooShort && (
                <p role="alert" className="text-xs leading-relaxed text-destructive">
                    Clip này chưa đủ {seconds(length)} giây. Chọn phiên bản khác hoặc tạo lại cảnh.
                </p>
            )}
            {!measured && (
                <p className="text-xs text-text-secondary">
                    Đang đọc độ dài clip để kiểm tra đoạn cắt…
                </p>
            )}
            {error && (
                <p role="alert" className="text-xs text-destructive">
                    {error}
                </p>
            )}
            <Button
                type="button"
                variant={reviewed ? "secondary" : "default"}
                className="min-h-12 w-full"
                disabled={disabled || !valid || reviewed}
                onClick={() => void save()}
            >
                {saving ? (
                    <Loader2 className="size-4 motion-safe:animate-spin" aria-hidden="true" />
                ) : (
                    <Check className="size-4" aria-hidden="true" />
                )}
                {reviewed ? "Đã chọn đoạn" : "Dùng đoạn này"}
            </Button>
            <p className="text-xs leading-relaxed text-text-secondary">
                Dùng clip đã có, không tạo thêm video AI.
            </p>
            <details>
                <summary className="min-h-11 cursor-pointer py-3 text-xs font-medium text-text-secondary focus-visible:ring-2 focus-visible:ring-ring">
                    Tinh chỉnh đoạn cắt
                </summary>
                <div className="space-y-4 pt-2">
                    <p className="text-xs font-medium text-text-secondary">
                        Clip AI · {seconds(rawFrameCount ?? plannedFrameCount)} giây
                    </p>
                    <p className="text-xs leading-relaxed text-text-secondary">
                        Độ dài được giữ theo cảnh mẫu; điểm kết thúc tự đi cùng điểm bắt đầu.
                    </p>
                    {sharedClip && (
                        <p className="rounded-xl bg-surface-soft p-3 text-xs leading-relaxed text-text-secondary">
                            Clip chung nhiều cảnh · Gợi ý {seconds(item.inFrame)}–
                            {seconds(item.outFrame)} giây cho cảnh này. Kiểm tra điểm chuyển cảnh
                            thực tế rồi duyệt đoạn sẽ dùng.
                        </p>
                    )}
                    <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-1">
                            <label htmlFor={`${id}-in`} className="text-xs text-text-secondary">
                                Bắt đầu (giây)
                            </label>
                            <Input
                                id={`${id}-in`}
                                type="number"
                                inputMode="decimal"
                                min={0}
                                max={max / 24}
                                step={1 / 24}
                                value={Number((inFrame / 24).toFixed(3))}
                                disabled={disabled || !canTrim}
                                onChange={(event) => change(Number(event.target.value) * 24)}
                                className="h-11 border-0 bg-surface-soft shadow-none"
                            />
                        </div>
                        <div className="space-y-1">
                            <span className="block text-xs text-text-secondary">
                                Kết thúc tự động
                            </span>
                            <p className="flex h-11 items-center rounded-xl bg-surface-soft px-3 text-sm tabular-nums text-text-primary">
                                {seconds(outFrame)} giây
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button
                            type="button"
                            variant="ghost"
                            className="min-h-11 flex-1 bg-surface-soft text-xs"
                            disabled={disabled || !canTrim || inFrame <= 0}
                            aria-label="Lùi điểm bắt đầu 1 frame"
                            onClick={() => change(inFrame - 1)}
                        >
                            <ChevronLeft className="size-4" aria-hidden="true" />1 frame
                        </Button>
                        <Button
                            type="button"
                            variant="ghost"
                            className="min-h-11 flex-1 bg-surface-soft text-xs"
                            disabled={disabled || !canTrim || inFrame >= max}
                            aria-label="Tiến điểm bắt đầu 1 frame"
                            onClick={() => change(inFrame + 1)}
                        >
                            1 frame
                            <ChevronRight className="size-4" aria-hidden="true" />
                        </Button>
                    </div>
                    <div className="flex gap-2">
                        <Button
                            type="button"
                            variant="ghost"
                            className="min-h-11 flex-1 px-2 text-xs"
                            onClick={() => onPreview(null)}
                        >
                            Xem clip gốc
                        </Button>
                        <Button
                            type="button"
                            variant="ghost"
                            className="min-h-11 flex-1 px-2 text-xs"
                            disabled={!valid}
                            onClick={() => onPreview({ start: inFrame / 24, end: outFrame / 24 })}
                        >
                            <Play className="size-3.5" aria-hidden="true" />
                            Xem đoạn chọn
                        </Button>
                    </div>
                </div>
            </details>
        </section>
    );
}
