// @vitest-environment jsdom
import { cleanup, fireEvent, render } from "@testing-library/react";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { SmartRemakeCompileResult } from "@/shared/api/smart-remake";
import { RemakeInputs, type RemakeInputsProps } from "./remake-inputs";
import { RemakeStoryboard } from "./remake-storyboard";

afterEach(cleanup);

const inputs: RemakeInputsProps = {
    sourceUrl: "blob:reference",
    sourceName: "reference.mp4",
    productUrls: ["https://example.com/product.png"],
    primaryIndex: 0,
    onPrimaryChange: vi.fn(),
    onVideo: vi.fn(),
    onImages: vi.fn(),
    onRemoveImage: vi.fn(),
    link: "",
    onLinkChange: vi.fn(),
    onLinkSubmit: vi.fn(),
    isLinkLoading: false,
    duration: 16,
    onDuration: vi.fn(),
    language: "vi",
    onLanguage: vi.fn(),
    description: "Bình giữ nhiệt màu hồng",
    onDescription: vi.fn(),
    brief: "Cho thấy tay cầm ngay đầu video",
    onBrief: vi.fn(),
    disabled: false,
};

describe("RemakeInputs", () => {
    it("shows attempted validation beside its media field and associates it with the visible upload action", () => {
        const view = render(
            createElement(RemakeInputs, {
                ...inputs,
                sourceUrl: null,
                productUrls: [],
                validationErrors: {
                    video: "Chọn video mẫu để tiếp tục.",
                    product: "Thêm ảnh sản phẩm để tiếp tục.",
                },
            }),
        );
        const videoError = view.getByText("Chọn video mẫu để tiếp tục.");
        const productError = view.getByText("Thêm ảnh sản phẩm để tiếp tục.");
        expect(view.getAllByRole("alert")).toHaveLength(2);
        expect(
            view
                .getByRole("button", { name: "Chọn video từ máy" })
                .getAttribute("aria-describedby"),
        ).toBe(videoError.id);
        expect(
            view
                .getByRole("button", { name: "Thêm ảnh sản phẩm" })
                .getAttribute("aria-describedby"),
        ).toBe(productError.id);
        expect(view.getByLabelText("Chọn file video mẫu").getAttribute("aria-invalid")).toBe(
            "true",
        );
        view.rerender(createElement(RemakeInputs, inputs));
        expect(view.queryAllByRole("alert")).toHaveLength(0);
    });
    it("shows full-frame media with controls, visible selection actions and no autoplay", () => {
        const html = renderToStaticMarkup(createElement(RemakeInputs, inputs));
        expect(html).toContain("reference.mp4");
        expect(html).toContain("object-contain");
        expect(html).toContain('controls=""');
        expect(html).not.toContain("autoPlay");
        expect(html).toContain("Chọn video khác");
        expect(html).toContain("Chọn từ kho video");
        expect(html).toContain("Ảnh chính");
        expect(html).toContain("Thêm ảnh sản phẩm");
        expect(html).toContain("Cho thấy tay cầm ngay đầu video");
    });

    it("labels illustrative assets explicitly and keeps upload/import unavailable while busy", () => {
        const html = renderToStaticMarkup(
            createElement(RemakeInputs, { ...inputs, isSample: true, disabled: true }),
        );
        expect(html).toContain("Minh họa");
        expect(html).toContain('disabled=""');
        expect(html).toContain("Dán link sản phẩm");
    });
    it("lets the seller fix initial detected boundaries without a compiled storyboard or second player", () => {
        const html = renderToStaticMarkup(
            createElement(RemakeInputs, {
                ...inputs,
                sourceCutFrames: [0, 384],
                onSourceCutFramesChange: vi.fn(),
            }),
        );
        expect(html).toContain("Nhịp cắt của video mẫu");
        expect(html).toContain("Chia cảnh dài nhất");
        expect(html).not.toContain("Mỗi cảnh tối đa 8 giây");
        expect(html.match(/<video\b/g)).toHaveLength(1);
    });
});

describe("RemakeStoryboard", () => {
    it("keeps automatically compiled prompts in one collapsed optional section", () => {
        const compileResult = {
            inputSummary: { targetDuration: 8, aspectRatio: "9:16", language: "vi" },
            sceneMap: {
                targetDuration: 8,
                sceneCount: 1,
                scenes: [
                    {
                        id: "scene-1",
                        videoPrompt: "ACTUAL_VIDEO_PROMPT",
                        imagePrompt: "ACTUAL_IMAGE_PROMPT",
                        shotPlan: { shots: [{ physicalAction: "Mở nắp bình" }] },
                    },
                ],
            },
            compiledPrompts: [
                {
                    sceneId: "scene-1",
                    videoPrompt: "ACTUAL_VIDEO_PROMPT",
                    imagePrompt: "ACTUAL_IMAGE_PROMPT",
                },
            ],
            productLock: {
                productName: "Bình hồng",
                mustPreserve: ["Tay cầm trắng", "Nắp trong suốt"],
            },
            warnings: [],
        } as unknown as SmartRemakeCompileResult;
        const html = renderToStaticMarkup(
            createElement(RemakeStoryboard, {
                compileResult,
                onSceneChange: vi.fn(),
                referenceUrl: "blob:reference",
                productUrl: "https://example.com/product.png",
            }),
        );
        expect(html).toContain("ACTUAL_VIDEO_PROMPT");
        expect(html).toContain("ACTUAL_IMAGE_PROMPT");
        expect(html).toContain("Chưa tạo video");
        expect(html).toContain("Prompt tạo video");
        expect(html).toContain("Sao chép");
        expect(html).toContain("Cảnh 1");
        expect(html).toContain("Sản phẩm cần giữ đúng");
        expect(html).toContain("Tay cầm trắng");
        expect(html).not.toContain("autoPlay");
        const markup = document.createElement("div");
        markup.innerHTML = html;
        const advanced = markup.querySelector("details");
        expect(markup.querySelectorAll("details")).toHaveLength(1);
        expect(advanced?.open).toBe(false);
        expect(advanced?.querySelectorAll("textarea")).toHaveLength(3);
        expect(
            advanced?.querySelector('button[aria-label="Sao chép prompt cảnh 1"]'),
        ).not.toBeNull();
        expect(advanced?.querySelector("summary")?.textContent).toContain("không bắt buộc");
        expect(markup.textContent).toContain("không cần viết prompt");
    });

    it("opens prefilled prompts only on request and preserves optional edits and their length validation", () => {
        const compileResult = {
            inputSummary: { targetDuration: 8, aspectRatio: "9:16" },
            sceneMap: {
                scenes: [
                    {
                        id: "scene-1",
                        prompt: "AUTO_SCENE_PROMPT",
                        imagePrompt: "AUTO_IMAGE_PROMPT",
                        videoPrompt: "AUTO_VIDEO_PROMPT",
                        shotPlan: { shots: [{ physicalAction: "Mở nắp bình" }] },
                    },
                ],
            },
        } as unknown as SmartRemakeCompileResult;
        const onSceneChange = vi.fn();
        const view = render(createElement(RemakeStoryboard, { compileResult, onSceneChange }));
        const advanced = view.container.querySelector("details")!;
        expect(advanced.open).toBe(false);
        expect(
            view.getAllByRole("textbox").every((field) => field.closest("details") === advanced),
        ).toBe(true);
        expect(view.getByText("Mở nắp bình").closest("details")).toBeNull();
        expect(onSceneChange).not.toHaveBeenCalled();

        fireEvent.click(advanced.querySelector("summary")!);
        expect(advanced.open).toBe(true);
        expect(view.getAllByRole("textbox")).toHaveLength(3);
        const videoPrompt = view.getByLabelText("Prompt tạo video") as HTMLTextAreaElement;
        expect(videoPrompt.value).toBe("AUTO_VIDEO_PROMPT");
        expect((view.getByLabelText("Prompt tạo ảnh") as HTMLTextAreaElement).value).toBe(
            "AUTO_IMAGE_PROMPT",
        );
        expect((view.getByLabelText("Prompt tổng hợp") as HTMLTextAreaElement).value).toBe(
            "AUTO_SCENE_PROMPT",
        );

        const editedPrompt = "A".repeat(12001);
        fireEvent.change(videoPrompt, { target: { value: editedPrompt } });
        expect(onSceneChange).toHaveBeenCalledWith(0, { videoPrompt: editedPrompt });
        const updatedCompile = {
            ...compileResult,
            sceneMap: {
                ...compileResult.sceneMap,
                scenes: [{ ...compileResult.sceneMap.scenes[0], videoPrompt: editedPrompt }],
            },
        };
        view.rerender(
            createElement(RemakeStoryboard, { compileResult: updatedCompile, onSceneChange }),
        );
        expect(view.getByRole("alert").textContent).toContain("tối đa 12.000 ký tự");
        expect(videoPrompt.getAttribute("aria-invalid")).toBe("true");

        fireEvent.click(advanced.querySelector("summary")!);
        expect(advanced.open).toBe(false);
        fireEvent.click(advanced.querySelector("summary")!);
        expect((view.getByLabelText("Prompt tạo video") as HTMLTextAreaElement).value).toBe(
            editedPrompt,
        );
    });

    it("keeps a cleared video prompt empty instead of displaying the generic prompt", () => {
        const compileResult = {
            inputSummary: { targetDuration: 8, aspectRatio: "9:16" },
            sceneMap: { scenes: [{ id: "scene-1", videoPrompt: "", prompt: "GENERIC_FALLBACK" }] },
        } as unknown as SmartRemakeCompileResult;
        const html = renderToStaticMarkup(
            createElement(RemakeStoryboard, { compileResult, onSceneChange: vi.fn() }),
        );
        expect(html).toMatch(/id="[^"]+-video-prompt"[^>]*><\/textarea>/);
        expect(html).toContain("0 / 12.000");
    });

    it("preserves existing long compiled video prompts instead of silently truncating them", () => {
        const prompt = "A".repeat(12050);
        const compileResult = {
            inputSummary: { targetDuration: 8, aspectRatio: "9:16" },
            sceneMap: { scenes: [{ id: "scene-1", videoPrompt: prompt }] },
        } as unknown as SmartRemakeCompileResult;
        const html = renderToStaticMarkup(
            createElement(RemakeStoryboard, { compileResult, onSceneChange: vi.fn() }),
        );
        expect(html).toContain(prompt);
        expect(html).toContain("12.050 / 12.000");
        expect(html).not.toContain("Hãy rút gọn prompt");
    });

    it("keeps image and generic prompt fields available after clearing all prompt text", () => {
        const compileResult = {
            inputSummary: { targetDuration: 8, aspectRatio: "9:16" },
            sceneMap: { scenes: [{ id: "scene-1", videoPrompt: "", imagePrompt: "", prompt: "" }] },
        } as unknown as SmartRemakeCompileResult;
        const html = renderToStaticMarkup(
            createElement(RemakeStoryboard, { compileResult, onSceneChange: vi.fn() }),
        );
        expect(html).toContain("Prompt tạo ảnh");
        expect(html).toContain("Prompt tổng hợp");
        expect(html).toContain("không bắt buộc");
        expect(html.match(/<textarea\b/g)).toHaveLength(3);
        expect(html).toMatch(/id="[^"]+-image-prompt"[^>]*><\/textarea>/);
        expect(html).toMatch(/id="[^"]+-prompt"[^>]*><\/textarea>/);
    });
});
