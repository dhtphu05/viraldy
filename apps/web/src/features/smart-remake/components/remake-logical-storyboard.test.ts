// @vitest-environment jsdom
import { createElement } from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { SmartRemakeCompileResult } from "@/shared/api/smart-remake";
import { RemakeLogicalStoryboard } from "./remake-logical-storyboard";

afterEach(cleanup);

function compiled(): SmartRemakeCompileResult {
    return {
        success: true,
        schemaVersion: 2,
        inputSummary: { targetDuration: 16, aspectRatio: "9:16", language: "vi" },
        sourceSceneMap: {
            fps: 24,
            timingMode: "fit_target",
            sourceStartFrame: 0,
            sourceFrameCount: 720,
            scenes: [
                {
                    id: "source-1",
                    startFrame: 0,
                    endFrame: 672,
                    targetDurationFrames: 336,
                    prompt: "Giữ bình và rót nước",
                    imagePrompt: "canonical image 1",
                    videoPrompt: "canonical motion 1",
                    shotPlan: { shots: [{ action: "Mở nắp rồi rót nước" }] },
                },
                {
                    id: "source-2",
                    startFrame: 672,
                    endFrame: 720,
                    targetDurationFrames: 48,
                    prompt: "Đặt bình xuống",
                    imagePrompt: "canonical image 2",
                    videoPrompt: "canonical motion 2",
                },
            ],
        },
        renderPlan: {
            fps: 24,
            provider: "kie",
            units: [
                {
                    id: "unit-1",
                    sourceSceneId: "source-1",
                    sceneIndex: 0,
                    rawDurationFrames: 192,
                    targetDurationFrames: 192,
                    fragmentIndex: 0,
                    fragmentCount: 2,
                    prompt: "fragment 1",
                    imagePrompt: "image 1",
                    videoPrompt: "motion 1",
                },
                {
                    id: "unit-2",
                    sourceSceneId: "source-1",
                    sceneIndex: 1,
                    rawDurationFrames: 192,
                    targetDurationFrames: 144,
                    fragmentIndex: 1,
                    fragmentCount: 2,
                    prompt: "fragment 2",
                    imagePrompt: "image 2",
                    videoPrompt: "motion 2",
                },
                {
                    id: "unit-3",
                    sourceSceneId: "source-2",
                    sceneIndex: 2,
                    rawDurationFrames: 192,
                    targetDurationFrames: 48,
                    prompt: "fragment 3",
                    imagePrompt: "image 3",
                    videoPrompt: "motion 3",
                },
            ],
        },
        sceneMap: { targetDuration: 16, sceneCount: 3, scenes: [] },
        compiledPrompts: [],
        productLock: {},
        referenceAnalysis: {},
        analyzeOutput: {},
        compilerDiagnostics: {},
        diagnostics: {},
        versions: {},
        warnings: [],
        mode: "smart_remake",
        renderSubmitted: false,
    };
}

describe("logical storyboard and provider fragments", () => {
    it("shows restored unit edits while keeping the canonical logical instruction intact", () => {
        const value = compiled();
        value.sceneMap.scenes = [
            {
                prompt: "Edited unit summary",
                imagePrompt: "Edited unit image",
                videoPrompt: "Edited unit motion",
            },
        ];
        render(
            createElement(RemakeLogicalStoryboard, {
                compiled: value,
                selectedScene: 0,
                onSceneChange: vi.fn(),
                disabled: true,
            }),
        );
        expect(
            (screen.getByLabelText("Prompt video đoạn render 1") as HTMLTextAreaElement).value,
        ).toBe("Edited unit motion");
        expect(
            (screen.getByLabelText("Prompt video đoạn render 1") as HTMLTextAreaElement).disabled,
        ).toBe(true);
        expect(
            (screen.getByLabelText("Prompt video của cảnh 1") as HTMLTextAreaElement).value,
        ).toBe("canonical motion 1");
    });
    it("keeps a historical scene readable when optional canonical details are missing", () => {
        const value = compiled();
        const first = value.sourceSceneMap!.scenes[0];
        delete first.prompt;
        delete first.imagePrompt;
        first.shotPlan = { shots: [{ stateBefore: "Unknown action" }, null] };
        render(
            createElement(RemakeLogicalStoryboard, {
                compiled: value,
                selectedScene: 0,
                onSceneChange: vi.fn(),
            }),
        );
        expect(
            screen.getByText("Hành động và cách quay từ cảnh tương ứng trong video mẫu."),
        ).toBeTruthy();
        expect((screen.getByLabelText("Prompt ảnh của cảnh 1") as HTMLTextAreaElement).value).toBe(
            "",
        );
    });
    it("keeps later analyzed scenes accessible beyond the old fourth-scene limit", () => {
        const value = compiled();
        value.sourceSceneMap!.scenes = Array.from({ length: 6 }, (_, index) => ({
            id: `source-${index}`,
            startFrame: index * 120,
            endFrame: (index + 1) * 120,
            targetDurationFrames: 64,
            prompt: `Scene ${index + 1}`,
            imagePrompt: `Image ${index + 1}`,
            videoPrompt: `Motion ${index + 1}`,
        }));
        render(
            createElement(RemakeLogicalStoryboard, {
                compiled: value,
                selectedScene: 5,
                onSceneChange: vi.fn(),
            }),
        );
        expect(screen.getByRole("heading", { name: "Cảnh 6" })).toBeTruthy();
        expect(
            (screen.getByLabelText("Prompt video của cảnh 6") as HTMLTextAreaElement).value,
        ).toBe("Motion 6");
    });
    it("shows one logical scene and canonical prompt despite two provider fragments", () => {
        render(
            createElement(RemakeLogicalStoryboard, {
                compiled: compiled(),
                selectedScene: 0,
                onSceneChange: vi.fn(),
            }),
        );
        expect(screen.getByRole("heading", { name: "Cảnh 1" })).toBeTruthy();
        expect(screen.queryByRole("heading", { name: "Cảnh 3" })).toBeNull();
        expect(screen.getByText("Mở nắp rồi rót nước")).toBeTruthy();
        expect(screen.getByText(/0–28 giây nguồn/)).toBeTruthy();
        expect(screen.getByText(/0–14 giây đầu ra/)).toBeTruthy();
        expect(
            (screen.getByLabelText("Prompt video của cảnh 1") as HTMLTextAreaElement).value,
        ).toBe("canonical motion 1");
    });
    it("edits a provider fragment by its render-unit index without overwriting the logical prompt", () => {
        const onSceneChange = vi.fn();
        render(
            createElement(RemakeLogicalStoryboard, {
                compiled: compiled(),
                selectedScene: 0,
                onSceneChange,
            }),
        );
        fireEvent.change(screen.getByLabelText("Prompt video đoạn render 2"), {
            target: { value: "Slower pour" },
        });
        expect(onSceneChange).toHaveBeenCalledWith(1, { videoPrompt: "Slower pour" });
        expect(
            (screen.getByLabelText("Prompt video của cảnh 1") as HTMLTextAreaElement).readOnly,
        ).toBe(true);
    });
    it("selects the second logical scene independently from its third render unit", () => {
        render(
            createElement(RemakeLogicalStoryboard, {
                compiled: compiled(),
                selectedScene: 1,
                onSceneChange: vi.fn(),
            }),
        );
        expect(screen.getByRole("heading", { name: "Cảnh 2" })).toBeTruthy();
        expect(screen.queryByRole("heading", { name: "Cảnh 1" })).toBeNull();
        expect(
            (screen.getByLabelText("Prompt video của cảnh 2") as HTMLTextAreaElement).value,
        ).toBe("canonical motion 2");
    });
});
