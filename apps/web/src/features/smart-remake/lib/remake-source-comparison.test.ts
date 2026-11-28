import { describe, expect, it } from "vitest";
import type { SmartRemakeProject, SmartRemakeTimeline } from "@/shared/api/smart-remake";
import {
    getSourceComparisonPlayback,
    getSourceComparisonSegments,
} from "./remake-source-comparison";

function fixture() {
    const unit = (id: string, sourceSceneId: string, start: number, end: number) => ({
        id,
        sourceSceneId,
        sceneIndex: 0,
        sourceStartFrame: start,
        sourceEndFrame: end,
        rawDurationFrames: 144,
        targetDurationFrames: 144,
        prompt: "",
        imagePrompt: "",
        videoPrompt: "",
    });
    const project: Pick<SmartRemakeProject, "renderPlan" | "sourceSceneMap"> = {
        sourceSceneMap: {
            fps: 24,
            sourceStartFrame: 120,
            sourceFrameCount: 696,
            scenes: [
                { id: "a", startFrame: 120, endFrame: 504, targetDurationFrames: 192 },
                { id: "b", startFrame: 504, endFrame: 696, targetDurationFrames: 96 },
            ],
        },
        renderPlan: {
            fps: 24,
            provider: "kie",
            units: [
                unit("a-first", "a", 120, 408),
                unit("a-last", "a", 408, 504),
                unit("b", "b", 504, 696),
            ],
        },
    };
    const timeline: SmartRemakeTimeline = {
        fps: 24,
        totalFrames: 288,
        items: [
            {
                id: "1",
                sourceSceneId: "a",
                renderUnitId: "a-first",
                targetStartFrame: 0,
                targetDurationFrames: 144,
                versionId: "v1",
                inFrame: 0,
                outFrame: 144,
                reviewed: false,
            },
            {
                id: "2",
                sourceSceneId: "a",
                renderUnitId: "a-last",
                targetStartFrame: 144,
                targetDurationFrames: 48,
                versionId: "v2",
                inFrame: 0,
                outFrame: 48,
                reviewed: false,
            },
            {
                id: "3",
                sourceSceneId: "b",
                renderUnitId: "b",
                targetStartFrame: 192,
                targetDurationFrames: 96,
                versionId: "v3",
                inFrame: 48,
                outFrame: 144,
                reviewed: false,
            },
        ],
    };
    return { project, timeline };
}

describe("source and remake comparison clock", () => {
    it("maps absolute excerpt offsets and fragments across the six-second provider boundary", () => {
        const { project, timeline } = fixture();
        expect(getSourceComparisonSegments(project, timeline)).toEqual([
            { targetStart: 0, targetEnd: 6, sourceStart: 5, sourceEnd: 17 },
            { targetStart: 6, targetEnd: 8, sourceStart: 17, sourceEnd: 21 },
            { targetStart: 8, targetEnd: 12, sourceStart: 21, sourceEnd: 29 },
        ]);
    });

    it("uses the selected assembly clock and never treats provider raw trim as source time", () => {
        const { project, timeline } = fixture();
        timeline.items[2] = { ...timeline.items[2], inFrame: 0, outFrame: 96 };
        const segments = getSourceComparisonSegments(project, timeline)!;
        expect(getSourceComparisonPlayback(segments, 10)).toEqual({ time: 25, playbackRate: 2 });
        expect(getSourceComparisonPlayback(segments, 6)).toEqual({ time: 17, playbackRate: 2 });
    });

    it("changes speed per scene and clamps seeking to the last source frame", () => {
        const segments = [
            { targetStart: 0, targetEnd: 6, sourceStart: 0, sourceEnd: 3 },
            { targetStart: 6, targetEnd: 12, sourceStart: 3, sourceEnd: 21 },
        ];
        expect(getSourceComparisonPlayback(segments, -1)).toEqual({ time: 0, playbackRate: 0.5 });
        expect(getSourceComparisonPlayback(segments, 3)).toEqual({ time: 1.5, playbackRate: 0.5 });
        expect(getSourceComparisonPlayback(segments, 6)).toEqual({ time: 3, playbackRate: 3 });
        expect(getSourceComparisonPlayback(segments, 30)?.time).toBeCloseTo(21 - 1 / 24);
        expect(getSourceComparisonPlayback([], 0)).toBeNull();
        expect(getSourceComparisonPlayback(segments, Number.NaN)).toBeNull();
    });

    it("supports a legacy unfragmented scene without double-adding the excerpt offset", () => {
        const { project, timeline } = fixture();
        project.renderPlan!.units = [
            {
                ...project.renderPlan!.units[2],
                sourceStartFrame: undefined,
                sourceEndFrame: undefined,
            },
        ];
        timeline.items = [{ ...timeline.items[2], targetStartFrame: 0 }];
        timeline.totalFrames = 96;
        expect(getSourceComparisonSegments(project, timeline)).toEqual([
            { targetStart: 0, targetEnd: 4, sourceStart: 21, sourceEnd: 29 },
        ]);
    });

    it.each([
        "gap",
        "missing-unit",
        "missing-fragment-range",
        "outside-source",
        "outside-video",
        "wrong-scene",
        "invalid-frame",
        "wrong-total",
    ])("does not invent correspondence for %s", (invalid) => {
        const { project, timeline } = fixture();
        if (invalid === "gap") timeline.items[1] = { ...timeline.items[1], targetStartFrame: 145 };
        if (invalid === "missing-unit")
            project.renderPlan!.units = project.renderPlan!.units.slice(1);
        if (invalid === "missing-fragment-range")
            project.renderPlan!.units[0] = {
                ...project.renderPlan!.units[0],
                sourceStartFrame: undefined,
                sourceEndFrame: undefined,
            };
        if (invalid === "outside-source")
            project.renderPlan!.units[2] = { ...project.renderPlan!.units[2], sourceEndFrame: 697 };
        if (invalid === "outside-video")
            project.sourceSceneMap = { ...project.sourceSceneMap!, sourceFrameCount: 695 };
        if (invalid === "wrong-scene")
            timeline.items[0] = { ...timeline.items[0], sourceSceneId: "b" };
        if (invalid === "invalid-frame")
            timeline.items[0] = { ...timeline.items[0], targetDurationFrames: 0.5 };
        if (invalid === "wrong-total") timeline.totalFrames = 289;
        expect(getSourceComparisonSegments(project, timeline)).toBeNull();
    });
});
