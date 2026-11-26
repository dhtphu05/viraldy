import type { SmartRemakeSceneVersion, SmartRemakeTimeline } from "@/shared/api/smart-remake";

export type RemakePreviewScope = { start: number; end: number } | null;

export function clampRemakePreviewTime(time: number, start: number, end: number): number {
    return Math.max(start, Math.min(Math.max(start, end - 1 / 24), time));
}

export function getTimelinePreviewScope(
    item: SmartRemakeTimeline["items"][number] | undefined,
    version: SmartRemakeSceneVersion,
    override: RemakePreviewScope | undefined,
    targetDurationFrames?: number,
): RemakePreviewScope {
    if (override !== undefined) return override;
    const inFrame =
        item?.versionId === version.id
            ? item.inFrame
            : (version.suggestedInFrame ?? (targetDurationFrames ? 0 : undefined));
    const outFrame =
        item?.versionId === version.id
            ? item.outFrame
            : (version.suggestedOutFrame ?? targetDurationFrames);
    return typeof inFrame === "number" &&
        typeof outFrame === "number" &&
        Number.isInteger(inFrame) &&
        Number.isInteger(outFrame) &&
        inFrame >= 0 &&
        outFrame > inFrame
        ? { start: inFrame / 24, end: outFrame / 24 }
        : null;
}

export function getComparisonPlaybackTime(
    time: number,
    primaryStart: number,
    comparisonStart: number,
    comparisonEnd: number,
): number {
    return clampRemakePreviewTime(
        comparisonStart + Math.max(0, time - primaryStart),
        comparisonStart,
        comparisonEnd,
    );
}
