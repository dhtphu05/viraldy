import { describe, expect, it } from "vitest";
import type { SmartRemakeProject } from "@/shared/api/smart-remake";
import { getRemakeGenerationProgress } from "./remake-generation-progress";

export const generationProject = () =>
    ({
        id: "project",
        targetDuration: 16,
        scenes: [],
        sourceSceneMap: {
            fps: 24,
            sourceStartFrame: 0,
            sourceFrameCount: 480,
            scenes: [
                {
                    id: "source-a",
                    startFrame: 0,
                    endFrame: 240,
                    targetDurationFrames: 192,
                    thumbnailUrl: "/source-a.webp",
                },
                {
                    id: "source-b",
                    startFrame: 240,
                    endFrame: 480,
                    targetDurationFrames: 192,
                    thumbnailUrl: "/source-b.webp",
                },
            ],
        },
        renderPlan: {
            fps: 24,
            provider: "kie",
            groupingPolicy: "fixed_provider_windows",
            groups: [
                {
                    id: "group-a",
                    renderUnitIds: ["unit-a", "unit-b"],
                    rawDurationFrames: 192,
                    targetDurationFrames: 192,
                    segments: [
                        { renderUnitId: "unit-a", inFrame: 0, outFrame: 96 },
                        { renderUnitId: "unit-b", inFrame: 96, outFrame: 192 },
                    ],
                },
                {
                    id: "group-b",
                    renderUnitIds: ["unit-c"],
                    rawDurationFrames: 192,
                    targetDurationFrames: 192,
                    segments: [{ renderUnitId: "unit-c", inFrame: 0, outFrame: 192 }],
                },
            ],
            units: [
                { id: "unit-a", sourceSceneId: "source-a", targetDurationFrames: 96 },
                { id: "unit-b", sourceSceneId: "source-a", targetDurationFrames: 96 },
                { id: "unit-c", sourceSceneId: "source-b", targetDurationFrames: 192 },
            ],
        },
        generationProgress: {
            operationId: "render",
            status: "running",
            startedAt: "2026-11-26T10:00:00Z",
            updatedAt: "2026-11-26T10:01:10Z",
            groups: [
                { groupId: "group-a", stage: "preparing_image", videoSubmitted: false },
                { groupId: "group-b", stage: "queued", videoSubmitted: false },
            ],
        },
    }) as unknown as SmartRemakeProject;

describe("provider window generation progress", () => {
    it("keeps both bookends from one render unit and only presents verified sent prompts", () => {
        const project = generationProject();
        const sent = {
            model: "wan/3-0-video",
            prompt: "Final exact prompt",
            requestHash: "request",
        };
        project.generationProgress!.groups[0] = {
            ...project.generationProgress!.groups[0],
            videoSubmitted: true,
            kieRequest: sent,
            conditioningImages: [
                {
                    renderUnitId: "unit-a",
                    frameRole: "opening",
                    requestHash: "first",
                    url: "/first.png",
                },
                {
                    renderUnitId: "unit-a",
                    frameRole: "ending",
                    requestHash: "last",
                    url: "/last.png",
                },
            ],
        };
        project.generationProgress!.groups[1].kieRequest = { ...sent, prompt: "Unsent" };
        const progress = getRemakeGenerationProgress(project)!;
        expect(progress.groups[0].conditioningImages.map((image) => image.frameRole)).toEqual([
            "opening",
            "ending",
        ]);
        expect(progress.groups[0].kieRequest).toEqual(sent);
        expect(progress.groups[1].kieRequest).toBeUndefined();
    });
    it("projects a saved twelve-second plan into two six-second windows", () => {
        const project = generationProject();
        project.targetDuration = 12;
        project.renderPlan!.groups = project.renderPlan!.groups!.map((group) => ({
            ...group,
            rawDurationFrames: 144,
            targetDurationFrames: 144,
        }));
        const progress = getRemakeGenerationProgress(project)!;
        expect(progress.plannedCount).toBe(2);
        expect(
            progress.groups.map(({ startSecond, endSecond }) => [startSecond, endSecond]),
        ).toEqual([
            [0, 6],
            [6, 12],
        ]);
    });

    it("counts planned groups separately from source scenes/fragments and submitted video calls", () => {
        const progress = getRemakeGenerationProgress(generationProject())!;
        expect(progress.plannedCount).toBe(2);
        expect(progress.submittedCount).toBe(0);
        expect(
            progress.groups.map(({ startSecond, endSecond }) => [startSecond, endSecond]),
        ).toEqual([
            [0, 8],
            [8, 16],
        ]);
        expect(progress.groups[0].sourceSceneIndexes).toEqual([1]);
        expect(progress.groups[0].sourceThumbnailUrl).toBe("/source-a.webp");
        expect(progress.elapsedSeconds).toBe(70);
    });
    it("does not turn a legacy missing projection or incomplete evidence into zero video calls", () => {
        const { generationProgress: _omitted, ...legacy } = generationProject();
        expect(getRemakeGenerationProgress(legacy)!.submittedCount).toBeNull();
        const project = generationProject();
        project.generationProgress!.groups = [project.generationProgress!.groups[0]];
        expect(getRemakeGenerationProgress(project)!.submittedCount).toBeNull();
    });
    it("counts only true submission evidence and binds stages to group IDs, not source scene order", () => {
        const project = generationProject();
        project.generationProgress!.groups = [
            { groupId: "group-b", stage: "generating", videoSubmitted: true },
            {
                groupId: "group-a",
                stage: "checking_image",
                videoSubmitted: false,
                conditioningImageUrl: "/conditioning.webp",
            },
        ];
        const progress = getRemakeGenerationProgress(project)!;
        expect(progress.submittedCount).toBe(1);
        expect(progress.groups.map(({ stage }) => stage)).toEqual(["checking_image", "generating"]);
        expect(progress.groups[0].conditioningImageUrl).toBe("/conditioning.webp");
    });
    it("keeps terminal and uncertain stages static and bounds server elapsed time", () => {
        const project = generationProject();
        project.generationProgress = {
            ...project.generationProgress!,
            status: "failed",
            updatedAt: "2026-12-26T10:01:10Z",
            groups: [
                { groupId: "group-a", stage: "blocked", videoSubmitted: false },
                { groupId: "group-b", stage: "unknown", videoSubmitted: null },
            ],
        };
        const progress = getRemakeGenerationProgress(project)!;
        expect(progress.active).toBe(false);
        expect(progress.submittedCount).toBeNull();
        expect(progress.elapsedSeconds).toBe(86400);
    });
    it("does not invent provider windows for a project lacking an explicit saved group plan", () => {
        expect(getRemakeGenerationProgress(null)).toBeNull();
        const project = generationProject();
        project.renderPlan = { ...project.renderPlan!, groups: undefined };
        expect(getRemakeGenerationProgress(project)).toBeNull();
    });
    it("binds retained KIE diagnostics to the failed group without leaking them into another clip", () => {
        const project = generationProject();
        const failure = {
            groupId: "group-a",
            stage: "blocked" as const,
            videoSubmitted: true,
            errorCode: "KIE_TASK_FAILED",
            providerError: { providerCode: "500", providerMessage: "Internal Error" },
            providerTaskId: "task-a",
        };
        project.generationProgress!.groups = [
            { groupId: "group-b", stage: "queued", videoSubmitted: false },
            failure,
        ];
        const groups = getRemakeGenerationProgress(project)!.groups;
        expect(groups[0].providerError).toEqual(failure.providerError);
        expect(groups[0].providerTaskId).toBe("task-a");
        expect(groups[1].providerError).toBeUndefined();
        expect(groups[1].providerTaskId).toBeUndefined();
    });
});
