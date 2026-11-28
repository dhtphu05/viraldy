import { describe, expect, it } from "vitest";
import type { SmartRemakeRenderPlan } from "@/shared/api/smart-remake";
import {
    getRenderGroups,
    getRenderGroupBreaks,
    getRenderTaskCount,
    getRenderWindowFrames,
    previewRenderGroups,
} from "./remake-groups";

function plan(lengths: number[]): SmartRemakeRenderPlan {
    return {
        fps: 24,
        provider: "kie",
        units: lengths.map((length, index) => ({
            id: `unit-${index}`,
            sourceSceneId: `source-${index}`,
            sceneIndex: index,
            targetDurationFrames: length * 24,
            rawDurationFrames: 192,
            prompt: "master",
            imagePrompt: "layout",
            videoPrompt: "motion",
        })),
    };
}

describe("video generation groups", () => {
    it("reads six-second saved windows and preserves the eight-second legacy fallback", () => {
        const value = plan([3, 3, 3, 3]);
        const groups = [0, 1].map((index) => ({
            id: `six-${index}`,
            renderUnitIds: [`unit-${index * 2}`, `unit-${index * 2 + 1}`],
            rawDurationFrames: 144,
            targetDurationFrames: 144,
            segments: [],
        }));
        expect(getRenderWindowFrames({ ...value, groups })).toBe(144);
        expect(getRenderWindowFrames(value)).toBe(192);
        expect(getRenderWindowFrames({ ...value, units: [] })).toBe(192);
        expect(getRenderWindowFrames(undefined)).toBe(192);
    });

    it("keeps frozen provider windows despite stale manual splits", () => {
        const value: SmartRemakeRenderPlan = {
            ...plan([5, 3, 2, 6]),
            groupingPolicy: "fixed_provider_windows" as const,
            renderGroupBreaks: [1, 2, 3],
        };
        value.groups = previewRenderGroups(plan([5, 3, 2, 6]), []);
        expect(getRenderGroupBreaks(value)).toEqual([]);
        expect(previewRenderGroups(value, [1, 2, 3])).toEqual(value.groups);
        expect(getRenderTaskCount(value)).toBe(2);
    });
    it.each([
        [
            [3, 5, 4, 4],
            [2, 2],
        ],
        [[2, 2, 2, 2], [4]],
        [
            [5, 5, 6],
            [1, 1, 1],
        ],
    ])("packs only consecutive whole scenes from %j", (lengths, members) => {
        const groups = previewRenderGroups(plan(lengths), []);
        expect(groups.map((group) => group.renderUnitIds.length)).toEqual(members);
        expect(groups.flatMap((group) => group.renderUnitIds)).toEqual(
            lengths.map((_, i) => `unit-${i}`),
        );
        for (const group of groups) {
            expect(group.targetDurationFrames).toBeLessThanOrEqual(192);
            expect(group.segments[0].inFrame).toBe(0);
            expect(group.segments.at(-1)?.outFrame).toBe(group.targetDurationFrames);
        }
    });
    it("respects an explicit split without modifying the saved plan", () => {
        const value = plan([3, 5, 4, 4]);
        const groups = previewRenderGroups(value, [1]);
        expect(groups.map((group) => group.renderUnitIds)).toEqual([
            ["unit-0"],
            ["unit-1"],
            ["unit-2", "unit-3"],
        ]);
        expect(value.groups).toBeUndefined();
    });
    it("keeps legacy saved tasks per scene rather than silently regrouping them", () => {
        const value = plan([2, 2, 2, 2]);
        expect(getRenderTaskCount(value)).toBe(4);
        expect(getRenderGroups(value).map((group) => group.segments[0])).toEqual(
            value.units.map((unit) => ({ renderUnitId: unit.id, inFrame: 0, outFrame: 48 })),
        );
        expect(getRenderGroupBreaks(value)).toEqual([1, 2, 3]);
        expect(getRenderTaskCount(undefined)).toBe(0);
    });
    it("counts actual saved groups and recovers optional manual splits", () => {
        const value = plan([3, 5, 4, 4]);
        value.groups = previewRenderGroups(value, []);
        expect(getRenderTaskCount(value)).toBe(2);
        expect(getRenderGroupBreaks(value)).toEqual([]);
        value.groups = previewRenderGroups(value, [1]);
        expect(getRenderGroupBreaks(value)).toEqual([1]);
    });
    it("restores explicit saved breaks without altering or inventing group preferences", () => {
        expect(getRenderGroupBreaks(undefined)).toEqual([]);
        const value = { ...plan([3, 5, 4, 4]), renderGroupBreaks: [1] };
        const breaks = getRenderGroupBreaks(value);
        expect(breaks).toEqual([1]);
        expect(breaks).not.toBe(value.renderGroupBreaks);
    });
});
