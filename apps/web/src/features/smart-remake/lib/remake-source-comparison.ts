import type { SmartRemakeProject, SmartRemakeTimeline } from "@/shared/api/smart-remake";

export type RemakeSourceComparisonSegment = {
    targetStart: number;
    targetEnd: number;
    sourceStart: number;
    sourceEnd: number;
};

// Use the assembly's frozen output clock; raw provider trims belong to a different clock.
export function getSourceComparisonSegments(
    project: Pick<SmartRemakeProject, "renderPlan" | "sourceSceneMap">,
    timeline: SmartRemakeTimeline,
): RemakeSourceComparisonSegment[] | null {
    const { renderPlan, sourceSceneMap } = project;
    if (!renderPlan || !sourceSceneMap || timeline.fps !== 24 || !timeline.items.length)
        return null;
    const units = new Map(renderPlan.units.map((unit) => [unit.id, unit]));
    const scenes = new Map(sourceSceneMap.scenes.map((scene) => [scene.id, scene]));
    const segments: RemakeSourceComparisonSegment[] = [];
    let cursor = 0;
    for (const item of timeline.items) {
        const unit = units.get(item.renderUnitId);
        const scene = scenes.get(item.sourceSceneId);
        if (!unit || !scene || unit.sourceSceneId !== scene.id) return null;
        const hasBounds = unit.sourceStartFrame !== undefined && unit.sourceEndFrame !== undefined;
        // A legacy unsplit unit can use its scene; a fragment must have its own bounds.
        if (
            !hasBounds &&
            (unit.sourceStartFrame !== undefined ||
                unit.sourceEndFrame !== undefined ||
                (unit.fragmentCount ?? 1) > 1 ||
                renderPlan.units.filter((candidate) => candidate.sourceSceneId === scene.id)
                    .length !== 1)
        )
            return null;
        const sourceStart = hasBounds ? unit.sourceStartFrame! : scene.startFrame;
        const sourceEnd = hasBounds ? unit.sourceEndFrame! : scene.endFrame;
        const targetEnd = item.targetStartFrame + item.targetDurationFrames;
        if (
            ![sourceStart, sourceEnd, item.targetStartFrame, item.targetDurationFrames].every(
                Number.isInteger,
            ) ||
            item.targetStartFrame !== cursor ||
            item.targetDurationFrames <= 0 ||
            sourceStart < sourceSceneMap.sourceStartFrame ||
            sourceEnd <= sourceStart ||
            sourceEnd > sourceSceneMap.sourceFrameCount ||
            sourceStart < scene.startFrame ||
            sourceEnd > scene.endFrame
        )
            return null;
        segments.push({
            targetStart: cursor / 24,
            targetEnd: targetEnd / 24,
            sourceStart: sourceStart / 24,
            sourceEnd: sourceEnd / 24,
        });
        cursor = targetEnd;
    }
    return cursor === timeline.totalFrames ? segments : null;
}

export function getSourceComparisonPlayback(
    segments: readonly RemakeSourceComparisonSegment[],
    time: number,
): { time: number; playbackRate: number } | null {
    if (!segments.length || !Number.isFinite(time)) return null;
    const first = segments[0];
    const last = segments[segments.length - 1];
    const targetTime = Math.max(first.targetStart, Math.min(time, last.targetEnd));
    const segment = segments.find((span) => targetTime < span.targetEnd) ?? last;
    const targetDuration = segment.targetEnd - segment.targetStart;
    const sourceDuration = segment.sourceEnd - segment.sourceStart;
    if (targetDuration <= 0 || sourceDuration <= 0) return null;
    const playbackRate = sourceDuration / targetDuration;
    return {
        time: Math.min(
            segment.sourceEnd - Math.min(1 / 24, sourceDuration),
            segment.sourceStart + (targetTime - segment.targetStart) * playbackRate,
        ),
        playbackRate,
    };
}
