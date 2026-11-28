import { describe, expect, it } from "vitest";
import type { SmartRemakeProject } from "@/shared/api/smart-remake";
import {
    getSourceExcerptError,
    getTimelinePublishError,
    secondsToFrames,
    validateSourceCuts,
} from "./remake-timeline";

function project(): SmartRemakeProject {
    return {
        id: "project",
        revision: 3,
        schemaVersion: 2,
        status: "ready",
        provider: "kie",
        targetDuration: 8,
        finalVideoUrl: "",
        scenes: [48, 144].map((frames, index) => ({
            id: `unit-${index}`,
            index,
            startSecond: index * 2,
            durationSeconds: frames / 24,
            activeVersionId: `version-${index}`,
            prompt: "master",
            imagePrompt: "image",
            videoPrompt: "motion",
            versions: [
                {
                    id: `version-${index}`,
                    parentVersionId: null,
                    videoUrl: "clip.mp4",
                    prompt: "master",
                    imagePrompt: "image",
                    videoPrompt: "motion",
                    source: "generated",
                    createdAt: "now",
                    rawDurationFrames: 192,
                    technicalCheck: {
                        status: "passed",
                        findings: [],
                        checkedAt: "now",
                        mediaHash: "hash",
                    },
                },
            ],
        })),
        draftTimeline: {
            fps: 24,
            totalFrames: 192,
            items: [48, 144].map((frames, index) => ({
                id: `item-${index}`,
                sourceSceneId: `source-${index}`,
                renderUnitId: `unit-${index}`,
                targetStartFrame: index * 48,
                targetDurationFrames: frames,
                versionId: `version-${index}`,
                inFrame: 24,
                outFrame: 24 + frames,
                reviewed: true,
            })),
        },
    };
}

describe("source excerpt and cuts", () => {
    it("converts selected times to integer frames", () => {
        expect(secondsToFrames(2.125)).toBe(51);
        expect(secondsToFrames(1 / 24)).toBe(1);
    });
    it.each([NaN, Infinity, -1])("rejects invalid selected times %s", (value) => {
        expect(secondsToFrames(value)).toBe(0);
    });
    it("waits for metadata, then rejects a too short source or out of range excerpt", () => {
        expect(getSourceExcerptError(null, 0, 16)).toContain("độ dài");
        expect(getSourceExcerptError(7.9, 0, 8)).toContain("ngắn");
        expect(getSourceExcerptError(20, 120, 16)).toContain("vượt");
        expect(getSourceExcerptError(20, 96, 16)).toBeNull();
    });
    it.each([NaN, -1, 0.5])("rejects malformed excerpt frame %s", (start) => {
        expect(getSourceExcerptError(20, start, 8)).toBeTruthy();
    });
    it("accepts two+six and three+five+four+four seconds without rescaling", () => {
        expect(validateSourceCuts([0, 48, 192], 192)).toBeNull();
        expect(validateSourceCuts([0, 72, 192, 288, 384], 384)).toBeNull();
    });
    it("keeps every source scene and allows source ranges longer than one provider clip", () => {
        expect(validateSourceCuts([0, 48, 96, 144, 192, 240, 720], 720)).toBeNull();
        expect(validateSourceCuts([0, 720], 720)).toBeNull();
    });
    it.each([
        [[1, 192], 192],
        [[0, 191], 192],
        [[0, 48, 48, 192], 192],
        [[0, 48.5, 192], 192],
        [[0, NaN, 192], 192],
    ])("rejects invalid cuts %j", (cuts, total) => {
        expect(validateSourceCuts(cuts, total)).toBeTruthy();
    });
});

describe("publish readiness", () => {
    it("allows one whole-video preview without per-scene review while retaining technical and range gates", () => {
        const value = project();
        value.draftTimeline!.items = value.draftTimeline!.items.map((item) => ({
            ...item,
            reviewed: false,
        }));
        expect(getTimelinePublishError(value)).toContain("Duyệt đoạn");
        expect(getTimelinePublishError(value, "whole_video")).toBeNull();
        value.scenes[0].versions[0].technicalCheck.status = "failed";
        expect(getTimelinePublishError(value, "whole_video")).toContain("Chờ đủ clip");
        value.scenes[0].versions[0].technicalCheck.status = "passed";
        value.draftTimeline!.items[0].outFrame += 1;
        expect(getTimelinePublishError(value, "whole_video")).toContain("Đoạn cắt chưa hợp lệ");
    });

    it("accepts more than four reviewed render units without weakening frame or review gates", () => {
        const value = project();
        value.scenes = Array.from({ length: 6 }, (_, index) => ({
            ...value.scenes[0],
            id: `unit-${index}`,
            index,
            durationSeconds: 32 / 24,
            activeVersionId: `version-${index}`,
            versions: [{ ...value.scenes[0].versions[0], id: `version-${index}` }],
        }));
        value.draftTimeline!.items = value.scenes.map((scene, index) => ({
            ...value.draftTimeline!.items[0],
            id: `item-${index}`,
            sourceSceneId: `source-${index}`,
            renderUnitId: scene.id,
            versionId: scene.activeVersionId,
            targetStartFrame: index * 32,
            targetDurationFrames: 32,
            inFrame: 0,
            outFrame: 32,
        }));
        expect(getTimelinePublishError(value)).toBeNull();
        value.draftTimeline!.items[5].reviewed = false;
        expect(getTimelinePublishError(value)).toContain("Duyệt");
    });
    it("accepts a complete reviewed two+six second draft", () => {
        expect(getTimelinePublishError(project())).toBeNull();
    });
    it("requires explicit review even when a default cut is playable", () => {
        const value = project();
        value.draftTimeline!.items[0].reviewed = false;
        expect(getTimelinePublishError(value)).toContain("Duyệt");
    });
    it("rejects a changed, missing or failed version and bounds beyond the raw clip", () => {
        for (const mutate of [
            (value: SmartRemakeProject) => {
                value.draftTimeline!.items[0].versionId = "stale";
            },
            (value: SmartRemakeProject) => {
                value.scenes[0].versions[0].technicalCheck.status = "failed";
            },
            (value: SmartRemakeProject) => {
                value.draftTimeline!.items[0].inFrame = 180;
                value.draftTimeline!.items[0].outFrame = 228;
            },
            (value: SmartRemakeProject) => {
                value.draftTimeline!.items[0].outFrame = 73;
            },
            (value: SmartRemakeProject) => {
                value.draftTimeline!.items[0].inFrame = 24.5;
            },
        ]) {
            const value = project();
            mutate(value);
            expect(getTimelinePublishError(value)).toBeTruthy();
        }
    });
    it("requires exact timeline coverage and no pending operation", () => {
        const value = project();
        value.draftTimeline!.items[1].targetStartFrame = 49;
        expect(getTimelinePublishError(value)).toBeTruthy();
        value.draftTimeline!.items[1].targetStartFrame = 48;
        value.pendingOperation = { id: "compose", status: "running", needsReconciliation: false };
        expect(getTimelinePublishError(value)).toContain("xử lý");
    });
    it("does not treat a legacy or absent timeline as ready", () => {
        expect(getTimelinePublishError(null)).toBeTruthy();
        expect(getTimelinePublishError({ ...project(), schemaVersion: 1 })).toBeTruthy();
    });
});

describe("saved draft restoration", () => {
    it("restores current server source audio after JSON reload without using another compile's progress", async () => {
        const { restoreTimelineCompile } = await import("./remake-timeline");
        const value = project();
        value.renderPlan = {
            fps: 24,
            provider: "kie",
            units: value.scenes.map((scene, sceneIndex) => ({
                id: scene.id,
                sourceSceneId: `source-${sceneIndex}`,
                sceneIndex,
                rawDurationFrames: 192,
                targetDurationFrames: scene.durationSeconds * 24,
                prompt: scene.prompt,
                imagePrompt: scene.imagePrompt,
                videoPrompt: scene.videoPrompt,
            })),
        };
        const sourceAudio = {
            schemaVersion: 1,
            speech: "present",
            music: "not_detected",
            transcript: "Lời thoại từ bản kịch bản đã lưu",
            language: "vi",
            pace: "medium",
        };
        const restored = restoreTimelineCompile(
            JSON.parse(JSON.stringify({ ...value, sourceAudio })),
        );
        expect(restored?.referenceAnalysis).toEqual({ sourceAudio });
        expect(restored?.renderPlan).toEqual(value.renderPlan);
        expect(restoreTimelineCompile(value)?.referenceAnalysis).toEqual({});
        expect(
            restoreTimelineCompile({
                ...value,
                sourceAudio: { ...sourceAudio, schemaVersion: 99 },
            } as unknown as SmartRemakeProject)?.referenceAnalysis,
        ).toEqual({});
    });
    it("restores one canonical logical prompt independently from two provider fragments", async () => {
        const { restoreTimelineCompile } = await import("./remake-timeline");
        const value = project();
        value.targetDuration = 16;
        value.sourceSceneMap = {
            fps: 24,
            timingMode: "fit_target",
            sourceStartFrame: 0,
            sourceFrameCount: 720,
            scenes: [
                {
                    id: "logical",
                    startFrame: 0,
                    endFrame: 720,
                    targetDurationFrames: 384,
                    prompt: "Canonical scene",
                    imagePrompt: "Canonical image",
                    videoPrompt: "Canonical video",
                },
            ],
        };
        value.renderPlan = {
            fps: 24,
            provider: "kie",
            units: value.scenes.map((scene, index) => ({
                id: scene.id,
                sourceSceneId: "logical",
                sceneIndex: index,
                rawDurationFrames: 192,
                targetDurationFrames: 192,
                sourceStartFrame: index * 360,
                sourceEndFrame: (index + 1) * 360,
                fragmentIndex: index,
                fragmentCount: 2,
                prompt: scene.prompt,
                imagePrompt: scene.imagePrompt,
                videoPrompt: scene.videoPrompt,
            })),
        };
        const restored = restoreTimelineCompile(value)!;
        expect(restored.compiledPrompts).toHaveLength(1);
        expect(restored.compiledPrompts[0]).toMatchObject({
            sourceSceneId: "logical",
            prompt: "Canonical scene",
            videoPrompt: "Canonical video",
        });
        expect(restored.sceneMap.sceneCount).toBe(2);
        expect(restored.sceneMap.scenes).toHaveLength(2);
    });
    it("restores prompt editing and saved render identity without inventing analysis", async () => {
        const { restoreTimelineCompile } = await import("./remake-timeline");
        const value = project();
        value.expectationsVersion = 1;
        value.expectationsHash = "a".repeat(64);
        value.renderPlan = {
            fps: 24,
            provider: "kie",
            units: value.scenes.map((scene, index) => ({
                id: scene.id,
                sourceSceneId: `source-${index}`,
                sceneIndex: index,
                rawDurationFrames: 192,
                targetDurationFrames: scene.durationSeconds * 24,
                prompt: scene.prompt,
                imagePrompt: scene.imagePrompt,
                videoPrompt: scene.videoPrompt,
            })),
        };
        expect(restoreTimelineCompile(value)).toMatchObject({
            schemaVersion: 2,
            projectId: value.id,
            revision: 3,
            expectationsVersion: 1,
            expectationsHash: value.expectationsHash,
            sceneMap: {
                sceneCount: 2,
                scenes: [
                    { id: "unit-0", prompt: "master" },
                    { id: "unit-1", prompt: "master" },
                ],
            },
            referenceAnalysis: {},
        });
        expect(
            restoreTimelineCompile({ ...value, expectationsHash: null })?.expectationsHash,
        ).toBeUndefined();
        expect(restoreTimelineCompile({ ...value, schemaVersion: 1 })).toBeNull();
    });
    it("restores analyzed scene descriptions by ID without exposing model prompts as a summary", async () => {
        const { restoreTimelineCompile } = await import("./remake-timeline");
        const { getRemakeScenes } = await import("./remake-studio");
        const value = project();
        value.renderPlan = {
            fps: 24,
            provider: "kie",
            units: value.scenes.map((scene, sceneIndex) => ({
                id: scene.id,
                sourceSceneId: `source-${sceneIndex}`,
                sceneIndex,
                rawDurationFrames: 192,
                targetDurationFrames: scene.durationSeconds * 24,
                prompt: scene.prompt,
                imagePrompt: scene.imagePrompt,
                videoPrompt: scene.videoPrompt,
            })),
        };
        value.scenes = [
            { ...value.scenes[1], description: "Nhấc bình và rót nước" },
            value.scenes[0],
        ];
        const restored = restoreTimelineCompile(value);
        expect(getRemakeScenes(restored).map((scene) => scene.description)).toEqual([
            "",
            "Nhấc bình và rót nước",
        ]);
        expect(restored?.sceneMap.scenes.map((scene) => scene.videoPrompt)).toEqual([
            value.renderPlan.units[0].videoPrompt,
            value.renderPlan.units[1].videoPrompt,
        ]);
        expect(restored?.referenceAnalysis).toEqual({});
    });
});

describe("durable timeline retry keys", () => {
    it("uses a new key on the first compose retry after its running job is known to have failed", async () => {
        const { settleTimelineOperationKeys } = await import("./remake-timeline");
        const value = project();
        const signature = JSON.stringify({
            kind: "publish",
            projectId: value.id,
            expectedRevision: 3,
        });
        const keys = new Map([[signature, "first-compose-key"]]);
        value.pendingOperation = { id: "compose", status: "running", needsReconciliation: false };
        expect(settleTimelineOperationKeys(keys, value).get(signature)).toBe("first-compose-key");
        value.pendingOperation = undefined;
        value.lastOperation = { id: "compose", kind: "compose", status: "failed" };
        expect(settleTimelineOperationKeys(keys, value).has(signature)).toBe(false);
        expect(keys.get(signature)).toBe("first-compose-key");
    });
    it("preserves the key while the receipt is unknown, and preserves another project's intent", async () => {
        const { settleTimelineOperationKeys } = await import("./remake-timeline");
        const value = project();
        const same = JSON.stringify({ kind: "publish", projectId: value.id, expectedRevision: 3 });
        const other = JSON.stringify({ kind: "publish", projectId: "other", expectedRevision: 3 });
        const keys = new Map([
            [same, "same-key"],
            [other, "other-key"],
        ]);
        expect(settleTimelineOperationKeys(keys, value)).toBe(keys);
        value.lastOperation = { id: "compose", kind: "compose", status: "completed" };
        expect([...settleTimelineOperationKeys(keys, value).values()]).toEqual(["other-key"]);
    });
});

describe("actual clip frame bounds", () => {
    it("uses measured frame count before the planned 192 frame duration", () => {
        const value = project();
        value.scenes[1].versions[0].frameCount = 191;
        value.draftTimeline!.items[1].inFrame = 48;
        value.draftTimeline!.items[1].outFrame = 192;
        expect(getTimelinePublishError(value)).toBeTruthy();
    });
});
