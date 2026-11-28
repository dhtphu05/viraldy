import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { SmartRemakeRenderPlan } from "@/shared/api/smart-remake";
import { previewRenderGroups } from "../lib/remake-groups";
import { RemakeRenderGroups } from "./remake-render-groups";

function plan(): SmartRemakeRenderPlan {
    const value: SmartRemakeRenderPlan = {
        fps: 24,
        provider: "kie",
        videoModel: "veo3_lite",
        imageModel: "gpt-image-2.6-flare",
        imageSize: "720x1280",
        imageQuality: "low",
        renderGroupBreaks: [],
        units: [72, 120, 96, 96].map((length, index) => ({
            id: `unit-${index}`,
            sourceSceneId: `source-${index}`,
            sceneIndex: index,
            rawDurationFrames: 192,
            targetDurationFrames: length,
            prompt: "master",
            imagePrompt: "image",
            videoPrompt: "motion",
        })),
    };
    return { ...value, groups: previewRenderGroups(value, []) };
}

describe("desktop render group plan", () => {
    it("shows two six-second Wan clips with audio for a twelve-second plan", () => {
        const base = plan();
        const units = base.units.map((unit) => ({
            ...unit,
            rawDurationFrames: 144,
            targetDurationFrames: 72,
        }));
        const groups = [0, 2].map((start, index) => ({
            id: `group-${index}`,
            renderUnitIds: units.slice(start, start + 2).map((unit) => unit.id),
            rawDurationFrames: 144,
            targetDurationFrames: 144,
            segments: units.slice(start, start + 2).map((unit, offset) => ({
                renderUnitId: unit.id,
                inFrame: offset * 72,
                outFrame: (offset + 1) * 72,
            })),
        }));
        const html = renderToStaticMarkup(
            createElement(RemakeRenderGroups, {
                plan: {
                    ...base,
                    groupingPolicy: "fixed_provider_windows",
                    videoModel: "wan/3-0-video",
                    videoResolution: "480P",
                    audioRequired: true,
                    units,
                    groups,
                },
                breaks: [],
                disabled: false,
            }),
        );
        expect(html).toContain("Video hoàn chỉnh 12 giây");
        expect(html).toContain("KIE tạo 2 clip 6 giây");
        expect(html).toContain("6 giây mỗi lượt · Có âm thanh");
        expect(html).not.toContain("8 giây mỗi lượt");
    });
    it.each([
        ["wan/3-0-video", "480P", "480P"],
        ["wan/3-0-video", undefined, "720P"],
        ["veo3_lite", undefined, "720P"],
    ] as const)(
        "keeps %s video resolution %s distinct from its image reference size",
        (videoModel, videoResolution, label) => {
            const html = renderToStaticMarkup(
                createElement(RemakeRenderGroups, {
                    plan: { ...plan(), videoModel, videoResolution },
                    breaks: [],
                    disabled: false,
                }),
            );
            expect(html).toContain(`Clip dọc 9:16 · ${label} · 8 giây mỗi lượt`);
            expect(html).toContain("720 × 1280");
            expect(html).toContain("4 cảnh · 2 lượt tạo video");
        },
    );
    it.each([
        ["wan/3-0-video", "Wan 3.0 · KIE"],
        ["another-model", "KIE"],
    ])("shows the saved %s model without relabeling it as Veo", (videoModel, label) => {
        const html = renderToStaticMarkup(
            createElement(RemakeRenderGroups, {
                plan: { ...plan(), videoModel },
                breaks: [],
                disabled: false,
            }),
        );
        expect(html).toContain(`>${label}</p>`);
        expect(html).not.toContain("Veo");
        expect(html).toContain("4 cảnh · 2 lượt tạo video");
        expect(html).toContain("Video hoàn chỉnh 16 giây");
    });
    it("does not count provider fragments as extra analyzed scenes", () => {
        const base = plan();
        const fragmented = {
            ...base,
            units: base.units.map((unit, index) => ({
                ...unit,
                sourceSceneId: index < 2 ? "source-a" : "source-b",
                fragmentIndex: index % 2,
                fragmentCount: 2,
                sourceStartFrame: index * 120,
                sourceEndFrame: (index + 1) * 120,
            })),
        };
        const html = renderToStaticMarkup(
            createElement(RemakeRenderGroups, {
                plan: fragmented,
                breaks: [],
                disabled: false,
                onBreaksChange: vi.fn(),
            }),
        );
        expect(html).toContain("2 cảnh · 4 đoạn render · 2 lượt tạo video");
        expect(html).toContain("Cảnh 1 · đoạn 2/2");
        expect(html).toContain("Tách nhóm sau đoạn render 1");
    });
    it("separates logical scenes from video calls and exposes timestamp instructions", () => {
        const html = renderToStaticMarkup(
            createElement(RemakeRenderGroups, {
                plan: plan(),
                breaks: [],
                disabled: false,
                onBreaksChange: vi.fn(),
            }),
        );
        expect(html).toContain("4 cảnh · 2 lượt tạo video");
        expect(html).toContain("Video hoàn chỉnh 16 giây");
        expect(html).toContain("Veo 3.1 Lite · KIE");
        expect(html).toContain("GPT Image Flare · OpenAI");
        expect(html).toContain("Cảnh 1: 0–3 giây");
        expect(html).toContain("Cảnh 2: 3–8 giây");
        expect(html).toContain("Tách nhóm sau cảnh 1");
        expect(html).toContain("vẫn cần xem và duyệt");
    });
    it("previews forced groups as uncommitted and requires an explicit update", () => {
        const html = renderToStaticMarkup(
            createElement(RemakeRenderGroups, {
                plan: plan(),
                breaks: [1],
                disabled: false,
                onBreaksChange: vi.fn(),
                dirty: true,
                onRecompile: vi.fn(),
            }),
        );
        expect(html).toContain("4 cảnh · 3 lượt tạo video");
        expect(html).toContain("Chưa cập nhật");
        expect(html).toContain("Cập nhật kịch bản");
        expect(html).toContain('checked=""');
        expect(html).not.toContain('disabled=""');
    });
    it.each([
        ["max", "Chất lượng tối đa"],
        ["xhigh", "Chất lượng rất cao"],
        ["high", "Chất lượng cao"],
    ] as const)(
        "shows the current Sunburst image model with %s quality and high complexity",
        (quality, label) => {
            const html = renderToStaticMarkup(
                createElement(RemakeRenderGroups, {
                    plan: {
                        ...plan(),
                        imageModel: "gpt-image-2.6-sunburst",
                        imageQuality: quality,
                        imageComplexity: "high",
                    },
                    breaks: [],
                    disabled: false,
                }),
            );
            expect(html).toContain("GPT Image Sunburst · OpenAI");
            expect(html).toContain(label);
            expect(html).toContain("Suy tính cao");
            expect(html).not.toContain("Tiết kiệm");
        },
    );
    it.each([
        ["low", "Tiết kiệm"],
        ["medium", "Chất lượng vừa"],
        [undefined, "Theo cấu hình"],
    ] as const)("keeps a saved %s quality label accurate", (quality, label) => {
        const html = renderToStaticMarkup(
            createElement(RemakeRenderGroups, {
                plan: { ...plan(), imageQuality: quality },
                breaks: [],
                disabled: false,
            }),
        );
        expect(html).toContain("GPT Image Flare · OpenAI");
        expect(html).toContain(label);
        expect(html).not.toContain("Suy tính cao");
        expect(html).not.toContain("Chất lượng cao");
    });
});
