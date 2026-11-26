// @vitest-environment jsdom
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { cleanup, fireEvent, render as renderDom } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { SmartRemakeRenderPlan } from "@/shared/api/smart-remake";
import { RemakeRenderGroups } from "./remake-render-groups";

afterEach(cleanup);

function fixedPlan(
    durations: number[],
    sourceIds = durations.map((_, index) => `source-${index}`),
): SmartRemakeRenderPlan {
    const units = durations.map((targetDurationFrames, index) => ({
        id: `unit-${index}`,
        sourceSceneId: sourceIds[index],
        sceneIndex: index,
        fragmentIndex: sourceIds.slice(0, index).filter((id) => id === sourceIds[index]).length,
        fragmentCount: sourceIds.filter((id) => id === sourceIds[index]).length,
        rawDurationFrames: 192,
        targetDurationFrames,
        prompt: "Product and scene",
        imagePrompt: "Opening frame",
        videoPrompt: "Scene action",
    }));
    const groups: NonNullable<SmartRemakeRenderPlan["groups"]> = [];
    for (const unit of units) {
        let group = groups.at(-1);
        if (!group || group.targetDurationFrames === 192) {
            group = {
                id: `group-${groups.length}`,
                renderUnitIds: [],
                rawDurationFrames: 192,
                targetDurationFrames: 0,
                segments: [],
            };
            groups.push(group);
        }
        const inFrame = group.targetDurationFrames;
        group.renderUnitIds.push(unit.id);
        group.targetDurationFrames += unit.targetDurationFrames;
        group.segments.push({
            renderUnitId: unit.id,
            inFrame,
            outFrame: group.targetDurationFrames,
        });
    }
    return {
        fps: 24,
        provider: "kie",
        videoModel: "veo3_lite",
        groupingPolicy: "fixed_provider_windows",
        units,
        groups,
    };
}

function render(plan: SmartRemakeRenderPlan, dirty = false) {
    return renderToStaticMarkup(
        createElement(RemakeRenderGroups, {
            plan,
            breaks: plan.units.slice(1).map((_, index) => index + 1),
            onBreaksChange: vi.fn(),
            dirty,
            disabled: false,
        }),
    );
}

describe("fixed provider window presentation", () => {
    it.each([
        [8, 16, 1],
        [16, 32, 2],
    ])(
        "shows %s-second output with twelve source scenes and %s-frame units",
        (seconds, frames, calls) => {
            const html = render(fixedPlan(Array.from({ length: 12 }, () => frames)), true);
            expect(html).toContain(`12 cảnh · ${calls} lượt tạo video`);
            expect(html).toContain(`Video hoàn chỉnh ${seconds} giây`);
            expect(html).toContain(`KIE tạo ${calls} clip 8 giây`);
            expect(html.match(/<article /g)).toHaveLength(calls);
            expect(html).not.toContain("Chọn cảnh cần tạo riêng");
            expect(html).not.toContain("Tách nhóm sau");
            expect(html).not.toContain('type="checkbox"');
        },
    );

    it("keeps uneven 5+5+6 timing at two frozen requests and distinguishes the split source scene", () => {
        const plan = fixedPlan([120, 72, 48, 144], ["first", "second", "second", "third"]);
        const html = render(plan, true);
        expect(html).toContain("3 cảnh · 4 đoạn render · 2 lượt tạo video");
        expect(html).toContain("Cảnh 2 · đoạn 1/2: 5–8 giây");
        expect(html).toContain("Cảnh 2 · đoạn 2/2: 0–2 giây");
        expect(html).toContain("Cảnh 3: 2–8 giây");
        expect(html).toContain("2 đoạn render · 1 lượt tạo");
        expect(html.match(/<article /g)).toHaveLength(2);
        expect(html).not.toContain("Chọn cảnh cần tạo riêng");
        expect(html).not.toContain("4 cảnh");
    });

    it("keeps legacy saved plans viewable with their existing group editing behavior", () => {
        const plan = fixedPlan([96, 96]);
        const html = render({ ...plan, groupingPolicy: undefined }, true);
        expect(html).toContain("2 cảnh · 2 lượt tạo video");
        expect(html).toContain("Chọn cảnh cần tạo riêng");
        expect(html).toContain("Tách nhóm sau cảnh 1");
    });

    it("continues to apply and remove explicit breaks for a legacy saved plan", () => {
        const plan = { ...fixedPlan([96, 96]), groupingPolicy: undefined };
        const onBreaksChange = vi.fn();
        const props = { plan, breaks: [], onBreaksChange, disabled: false };
        const view = renderDom(createElement(RemakeRenderGroups, props));
        fireEvent.click(view.getByRole("checkbox", { name: "Tách nhóm sau cảnh 1" }));
        expect(onBreaksChange).toHaveBeenLastCalledWith([1]);
        view.rerender(createElement(RemakeRenderGroups, { ...props, breaks: [1] }));
        fireEvent.click(view.getByRole("checkbox", { name: "Tách nhóm sau cảnh 1" }));
        expect(onBreaksChange).toHaveBeenLastCalledWith([]);
    });
});
