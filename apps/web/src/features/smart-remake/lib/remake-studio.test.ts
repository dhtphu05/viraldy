import { describe, expect, it } from "vitest";

import type { SmartRemakeCompileResult } from "@/shared/api/smart-remake";
import {
    getContainedMediaSize,
    getRemakeScenes,
    getSceneRange,
    updateRemakeScene,
} from "./remake-studio";

function compiledFixture(): SmartRemakeCompileResult {
    return {
        success: true,
        mode: "smart_remake",
        renderSubmitted: false,
        inputSummary: { targetDuration: 16, aspectRatio: "9:16", language: "vi" },
        referenceAnalysis: {},
        analyzeOutput: {},
        productLock: { productReference: { characterName: "Product" } },
        sceneMap: {
            targetDuration: 16,
            sceneCount: 2,
            scenes: [
                {
                    displayOrder: 0,
                    chainType: "ROOT",
                    parentSceneId: null,
                    characterNames: ["Product"],
                    textOverlay: "Mở hộp sản phẩm",
                    prompt: "Scene one master prompt",
                    imagePrompt: "Scene one first frame",
                    videoPrompt: "Scene one movement",
                    sourceSegment: { sourceTimeRange: { startSecond: 0, endSecond: 11.4 } },
                    shotPlan: {
                        shots: [
                            { action: "Mở hộp" },
                            { physicalAction: "Nhấc sản phẩm", action: "Show product" },
                        ],
                    },
                },
                {
                    displayOrder: 1,
                    chainType: "ROOT",
                    parentSceneId: null,
                    characterNames: ["Product"],
                    prompt: "Scene two master prompt",
                    imagePrompt: "Scene two first frame",
                    videoPrompt: "Scene two movement",
                    sourceSegment: { sourceTimeRange: { startSecond: 11.4, endSecond: 25 } },
                },
            ],
        },
        compiledPrompts: [
            {
                displayOrder: 1,
                prompt: "Scene two master prompt",
                imagePrompt: "Scene two first frame",
                videoPrompt: "Scene two movement",
                retained: true,
            },
            {
                displayOrder: 0,
                prompt: "Scene one master prompt",
                imagePrompt: "Scene one first frame",
                videoPrompt: "Scene one movement",
            },
        ],
        compilerDiagnostics: {},
        diagnostics: {},
        versions: { compiler: "v2" },
        warnings: [],
    };
}

describe("getRemakeScenes", () => {
    it("keeps logical canonical prompts immutable when editing a provider fragment", () => {
        const value = compiledFixture();
        value.sourceSceneMap = {
            fps: 24,
            timingMode: "fit_target",
            sourceStartFrame: 0,
            sourceFrameCount: 720,
            scenes: [],
        };
        const original = value.compiledPrompts;
        const result = updateRemakeScene(value, 1, { videoPrompt: "Edited provider fragment" });
        expect(result.sceneMap.scenes[1].videoPrompt).toBe("Edited provider fragment");
        expect(result.compiledPrompts).toEqual(original);
    });
    it("reads real compiler fields and uses generated timing rather than reference timing", () => {
        expect(getRemakeScenes(compiledFixture())).toEqual([
            {
                id: "scene-1",
                index: 0,
                start: 0,
                end: 8,
                title: "Mở hộp sản phẩm",
                description: "Mở hộp · Nhấc sản phẩm",
                prompt: "Scene one master prompt",
                imagePrompt: "Scene one first frame",
                videoPrompt: "Scene one movement",
            },
            {
                id: "scene-2",
                index: 1,
                start: 8,
                end: 16,
                title: "Cảnh 2",
                description: "",
                prompt: "Scene two master prompt",
                imagePrompt: "Scene two first frame",
                videoPrompt: "Scene two movement",
            },
        ]);
    });

    it("returns an empty scene list before compilation", () => {
        expect(getRemakeScenes(null)).toEqual([]);
        expect(getRemakeScenes(undefined)).toEqual([]);
    });

    it("preserves prompt spaces and newlines while displaying a controlled editor draft", () => {
        const compiled = compiledFixture();
        compiled.sceneMap.scenes[0] = {
            ...compiled.sceneMap.scenes[0],
            prompt: "  User typing ",
            imagePrompt: "First frame\n",
            videoPrompt: "Motion \n ",
        };
        expect(getRemakeScenes(compiled)[0]).toMatchObject({
            prompt: "  User typing ",
            imagePrompt: "First frame\n",
            videoPrompt: "Motion \n ",
        });
    });

    it("does not display objects as user-facing text for optional unknown fields", () => {
        const compiled = compiledFixture();
        compiled.sceneMap.scenes[0] = {
            displayOrder: 0,
            textOverlay: {},
            shotPlan: { shots: [{ action: {} }] },
        };
        expect(getRemakeScenes(compiled)[0]).toEqual({
            id: "scene-1",
            index: 0,
            start: 0,
            end: 8,
            title: "Cảnh 1",
            description: "",
            prompt: "",
            imagePrompt: "",
            videoPrompt: "",
        });
    });
});

describe("updateRemakeScene", () => {
    it("updates only the selected scene and matches the compiled mirror by displayOrder", () => {
        const compiled = compiledFixture();
        const original = structuredClone(compiled);
        const updated = updateRemakeScene(compiled, 0, {
            imagePrompt: "  New first frame  ",
            videoPrompt: "New motion",
        });

        expect(updated.sceneMap.scenes[0]).toEqual({
            ...compiled.sceneMap.scenes[0],
            promptEdited: true,
            originalPrompt: "Scene one master prompt",
            originalImagePrompt: "Scene one first frame",
            originalVideoPrompt: "Scene one movement",
            imagePrompt: "New first frame",
            videoPrompt: "New motion",
        });
        expect(updated.compiledPrompts[1]).toEqual({
            ...compiled.compiledPrompts[1],
            promptEdited: true,
            originalPrompt: "Scene one master prompt",
            originalImagePrompt: "Scene one first frame",
            originalVideoPrompt: "Scene one movement",
            imagePrompt: "New first frame",
            videoPrompt: "New motion",
        });
        expect(updated.sceneMap.scenes[1]).toBe(compiled.sceneMap.scenes[1]);
        expect(updated.compiledPrompts[0]).toBe(compiled.compiledPrompts[0]);
        expect(updated.productLock).toBe(compiled.productLock);
        expect(updated.versions).toBe(compiled.versions);
        expect(updated.inputSummary).toBe(compiled.inputSummary);
        expect(compiled).toEqual(original);
    });

    it("keeps the master prompt distinct from image and video generation instructions", () => {
        const updated = updateRemakeScene(compiledFixture(), 1, { prompt: "New master prompt" });
        expect(getRemakeScenes(updated)[1]).toMatchObject({
            prompt: "New master prompt",
            imagePrompt: "Scene two first frame",
            videoPrompt: "Scene two movement",
        });
    });

    it("marks only actual prompt changes as edited so unchanged scene drafts keep the shot plan", () => {
        const compiled = compiledFixture();
        const unchanged = updateRemakeScene(compiled, 0, {
            prompt: "Scene one master prompt",
            imagePrompt: "Scene one first frame",
            videoPrompt: "Scene one movement",
        });
        expect(unchanged).toBe(compiled);
        expect(unchanged.sceneMap.scenes[0].promptEdited).toBeUndefined();
    });

    it("keeps all original prompt snapshots across successive prompt edits", () => {
        const compiled = compiledFixture();
        const firstEdit = updateRemakeScene(compiled, 0, { imagePrompt: "New frame" });
        const secondEdit = updateRemakeScene(firstEdit, 0, { videoPrompt: "New motion" });
        const thirdEdit = updateRemakeScene(secondEdit, 0, {
            prompt: "New master prompt",
            videoPrompt: "Another motion",
        });
        expect(thirdEdit.sceneMap.scenes[0]).toMatchObject({
            promptEdited: true,
            originalPrompt: "Scene one master prompt",
            originalImagePrompt: "Scene one first frame",
            originalVideoPrompt: "Scene one movement",
            prompt: "New master prompt",
            imagePrompt: "New frame",
            videoPrompt: "Another motion",
        });
        expect(thirdEdit.compiledPrompts[1]).toMatchObject({
            originalPrompt: "Scene one master prompt",
            originalImagePrompt: "Scene one first frame",
            originalVideoPrompt: "Scene one movement",
            prompt: "New master prompt",
            videoPrompt: "Another motion",
        });
        expect(compiled.sceneMap.scenes[0].originalVideoPrompt).toBeUndefined();
    });

    it("does not create an edit snapshot for whitespace-only changes", () => {
        const compiled = compiledFixture();
        expect(updateRemakeScene(compiled, 0, { videoPrompt: "  Scene one movement\n " })).toBe(
            compiled,
        );
        expect(compiled.sceneMap.scenes[0].originalVideoPrompt).toBeUndefined();
    });

    it("recreates a missing compiled mirror with all required prompt fields", () => {
        const compiled = compiledFixture();
        compiled.compiledPrompts = [];
        expect(
            updateRemakeScene(compiled, 1, { videoPrompt: "New motion" }).compiledPrompts,
        ).toEqual([
            {
                displayOrder: 1,
                promptEdited: true,
                originalPrompt: "Scene two master prompt",
                originalImagePrompt: "Scene two first frame",
                originalVideoPrompt: "Scene two movement",
                prompt: "Scene two master prompt",
                imagePrompt: "Scene two first frame",
                videoPrompt: "New motion",
            },
        ]);
    });

    it.each(["prompt", "imagePrompt", "videoPrompt"] as const)(
        "rejects an empty %s before rendering",
        (field) => {
            expect(() => updateRemakeScene(compiledFixture(), 0, { [field]: " \n " })).toThrow(
                "không được để trống",
            );
        },
    );

    it.each([-1, 2, 0.5, NaN])("rejects a nonexistent selected scene (%s)", (index) => {
        expect(() => updateRemakeScene(compiledFixture(), index, { prompt: "New prompt" })).toThrow(
            "Cảnh không tồn tại",
        );
    });
});

describe("media geometry", () => {
    it("contains portrait media without stretching", () => {
        expect(getContainedMediaSize(1080, 1920, 600, 500)).toEqual({ width: 281.25, height: 500 });
    });

    it("contains landscape media and supports a larger preview", () => {
        expect(getContainedMediaSize(1920, 1080, 500, 600)).toEqual({ width: 500, height: 281.25 });
        expect(getContainedMediaSize(100, 100, 200, 300)).toEqual({ width: 200, height: 200 });
    });

    it.each([0, -1, NaN, Infinity])("waits for valid media metadata (%s)", (width) => {
        expect(getContainedMediaSize(width, 1920, 600, 500)).toEqual({ width: 0, height: 0 });
    });

    it("uses the fixed eight-second scene boundaries", () => {
        expect(getSceneRange(0)).toEqual({ start: 0, end: 8 });
        expect(getSceneRange(1)).toEqual({ start: 8, end: 16 });
    });
});

describe("timeline scene timing", () => {
    it("uses planned target lengths instead of fixed eight-second generated clip lengths", () => {
        const compiled = compiledFixture();
        compiled.schemaVersion = 2;
        compiled.renderPlan = {
            fps: 24,
            provider: "kie",
            units: [48, 144].map((frames, index) => ({
                id: `unit-${index}`,
                sourceSceneId: `source-${index}`,
                sceneIndex: index,
                rawDurationFrames: 192,
                targetDurationFrames: frames,
                prompt: "master",
                imagePrompt: "image",
                videoPrompt: "motion",
            })),
        };
        expect(getRemakeScenes(compiled).map(({ id, start, end }) => ({ id, start, end }))).toEqual(
            [
                { id: "unit-0", start: 0, end: 2 },
                { id: "unit-1", start: 2, end: 8 },
            ],
        );
    });
});
