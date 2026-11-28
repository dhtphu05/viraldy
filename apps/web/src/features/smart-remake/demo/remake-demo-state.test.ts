import { describe, expect, it } from "vitest";
import type { SmartRemakeProject } from "@/shared/api/smart-remake";
import { applyDemoVersion, selectDemoRanges } from "./remake-demo-state";
import { createRemakePreviewDemo, createRemakeClipRepairDemo } from "./remake-preview-demo";
import { getRemakeClipCandidate, getRemakeClipGroups } from "../lib/remake-clip-groups";
import {
    getCurrentRemakeAssembly,
    getRemakeResultNextAction,
} from "../lib/remake-result-next-action";
import { getRemakeProjectPollInterval } from "../lib/smart-remake-render";

const project = {
    id: "demo",
    expectationsHash: "fixture-source-base-expectations",
    scenes: [
        { id: "scene", activeVersionId: "before", versions: [{ id: "before" }, { id: "after" }] },
    ],
    draftTimeline: {
        fps: 24,
        totalFrames: 384,
        items: [
            {
                id: "item",
                renderUnitId: "scene",
                versionId: "before",
                inFrame: 0,
                outFrame: 33,
                reviewed: false,
            },
        ],
    },
    inspectionSummary: { reports: [{ id: "real-report", status: "failed" }], reviews: [] },
} as unknown as SmartRemakeProject;

describe("local report demo state", () => {
    it("exposes a complete explicitly simulated clip candidate for browser comparison", () => {
        const demo = createRemakeClipRepairDemo(project);
        const group = getRemakeClipGroups(demo.project)[0];
        const candidate = getRemakeClipCandidate(demo.project, group, demo.candidate);
        expect(candidate?.version.videoUrl).toBe(
            "/smart-remake/report-demo/whole-preview-second.mp4",
        );
        expect(demo.candidate.affectedVersions).toHaveLength(group.memberIds.length);
        expect(demo.project.release).toBeUndefined();
    });
    it("prepares a twelve-second whole-video fixture without approving twenty-five scene selections", () => {
        const next = createRemakePreviewDemo(project, "ready");
        expect(next.targetDuration).toBe(12);
        expect(next.renderPlan!.groups).toHaveLength(2);
        expect(next.renderPlan!.groups!.map((group) => group.rawDurationFrames)).toEqual([
            144, 144,
        ]);
        expect(next.draftTimeline!.items).toHaveLength(25);
        expect(next.draftTimeline!.items.every((item) => item.reviewed === false)).toBe(true);
        expect(next.draftTimeline!.totalFrames).toBe(288);
        expect(next.expectationsHash).toBe(project.expectationsHash);
        expect(next.assemblies!.records[0].expectationsHash).toBeTruthy();
        expect(next.assemblies!.records[0].expectationsHash).not.toBe(next.expectationsHash);
        expect(getCurrentRemakeAssembly(next)?.reviewMode).toBe("whole_video");
        expect(getRemakeResultNextAction({ project: next, reviewMode: "whole_video" }).kind).toBe(
            "inspect",
        );
        expect(next.release).toBeUndefined();
        expect(project.inspectionSummary!.reports[0].id).toBe("real-report");
    });
    it("represents pending assembly as read-only progress with the two real local clip URLs", () => {
        const next = createRemakePreviewDemo(project, "processing");
        expect(next.finalVideoUrl).toBe("");
        expect(next.preview?.status).toBe("processing");
        expect(getCurrentRemakeAssembly(next)).toBeUndefined();
        expect(next.generationProgress!.groups.map((group) => group.videoUrl)).toEqual([
            "/smart-remake/report-demo/whole-preview-first.mp4",
            "/smart-remake/report-demo/whole-preview-second.mp4",
        ]);
        expect(getRemakeProjectPollInterval(next)).toBe(5000);
    });
    it("confirms only selected ranges without changing original data or AI findings", () => {
        const next = selectDemoRanges(project, [
            {
                renderUnitId: "scene",
                versionId: "before",
                inFrame: 12,
                outFrame: 45,
                reviewed: true,
            },
        ]);
        expect(next.draftTimeline!.items[0]).toMatchObject({
            inFrame: 12,
            outFrame: 45,
            reviewed: true,
        });
        expect(project.draftTimeline!.items[0]).toMatchObject({ inFrame: 0, reviewed: false });
        expect(next.inspectionSummary).toBe(project.inspectionSummary);
    });
    it("selects an imported version and requires its range to be confirmed again", () => {
        const next = applyDemoVersion(project, "scene", "after");
        expect(next.scenes[0].activeVersionId).toBe("after");
        expect(next.draftTimeline!.items[0]).toMatchObject({ versionId: "after", reviewed: false });
        expect(project.scenes[0].activeVersionId).toBe("before");
        expect(next.inspectionSummary).toBe(project.inspectionSummary);
    });
    it("preserves the project for missing versions and timelines", () => {
        expect(applyDemoVersion(project, "scene", "missing")).toBe(project);
        const noTimeline = { ...project, draftTimeline: undefined };
        expect(selectDemoRanges(noTimeline, [])).toBe(noTimeline);
    });
});
