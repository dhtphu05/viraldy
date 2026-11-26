// @vitest-environment jsdom
import { createElement } from "react";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { RemakeSourceTimeline, type RemakeSourceTimelineProps } from "./remake-source-timeline";

const base: RemakeSourceTimelineProps = {
    referenceUrl: "/imported-source.mp4",
    sourceStartFrame: 48,
    totalFrames: 384,
    sourceCutFrames: [0, 168, 384],
    compiledCutFrames: [0, 168, 384],
    selectedScene: 0,
    onSelect: vi.fn(),
};

beforeEach(() => {
    vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => {});
});
afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
});

function mount(props: Partial<RemakeSourceTimelineProps> = {}) {
    const onSelect = vi.fn();
    const view = render(createElement(RemakeSourceTimeline, { ...base, onSelect, ...props }));
    const video = screen.getByLabelText("Video mẫu — xem theo từng cảnh") as HTMLVideoElement;
    Object.defineProperties(video, {
        duration: { configurable: true, value: 30 },
        videoWidth: { configurable: true, value: 720 },
        videoHeight: { configurable: true, value: 1280 },
    });
    fireEvent.loadedMetadata(video);
    return { ...view, video, onSelect };
}

describe("source timeline seeking", () => {
    it("keeps 24 unequal scenes as a chooser while one real time control seeks their true frames", () => {
        const lengths = Array.from({ length: 24 }, (_, index) => 12 + (index % 5) * 6);
        const cuts = lengths.reduce((values, length) => [...values, values.at(-1)! + length], [0]);
        const { video, onSelect, container, rerender } = mount({
            totalFrames: cuts.at(-1)!,
            sourceCutFrames: cuts,
            compiledCutFrames: cuts,
        });
        const scenes = within(
            screen.getByRole("group", { name: "Chọn cảnh từ video mẫu" }),
        ).getAllByRole("button");
        expect(scenes).toHaveLength(24);
        expect(container.querySelector(".remake-playhead")).toBeNull();
        expect(screen.getAllByRole("slider", { name: "Tua video mẫu" })).toHaveLength(1);
        const frame = cuts[23] + 1;
        fireEvent.change(screen.getByRole("slider", { name: "Tua video mẫu" }), {
            target: { value: String(frame) },
        });
        expect(onSelect).toHaveBeenLastCalledWith(23);
        expect(video.currentTime).toBe((48 + frame) / 24);
        const strip = screen.getByRole("group", { name: "Chọn cảnh từ video mẫu" }).parentElement!;
        Object.defineProperty(strip, "clientWidth", { configurable: true, value: 300 });
        Object.defineProperties(scenes[23], {
            offsetLeft: { configurable: true, value: 2392 },
            offsetWidth: { configurable: true, value: 100 },
        });
        rerender(
            createElement(RemakeSourceTimeline, {
                ...base,
                totalFrames: cuts.at(-1)!,
                sourceCutFrames: cuts,
                compiledCutFrames: cuts,
                selectedScene: 23,
                onSelect,
            }),
        );
        expect(strip.scrollLeft).toBe(2192);
        fireEvent.click(scenes[3]);
        expect(onSelect).toHaveBeenLastCalledWith(3);
        expect(video.currentTime).toBe((48 + cuts[3]) / 24);
        Object.defineProperties(scenes[3], {
            offsetLeft: { configurable: true, value: 312 },
            offsetWidth: { configurable: true, value: 100 },
        });
        rerender(
            createElement(RemakeSourceTimeline, {
                ...base,
                totalFrames: cuts.at(-1)!,
                sourceCutFrames: cuts,
                compiledCutFrames: cuts,
                selectedScene: 3,
                onSelect,
            }),
        );
        expect(strip.scrollLeft).toBe(312);
    });

    it("seeks the actual video at frame precision and selects the scene under the playhead", () => {
        const { video, onSelect } = mount();
        const seek = screen.getByRole("slider", { name: "Tua video mẫu" }) as HTMLInputElement;
        fireEvent.change(seek, { target: { value: "204" } });
        expect(video.currentTime).toBe(10.5);
        expect(video.pause).toHaveBeenCalled();
        expect(onSelect).toHaveBeenLastCalledWith(1);
        expect(seek.value).toBe("204");
        expect(video.autoplay).toBe(false);
    });

    it("keeps native playback and native seeking synchronized with the timeline and script scene", () => {
        const { video, onSelect } = mount();
        video.currentTime = 9;
        fireEvent.timeUpdate(video);
        const seek = screen.getByRole("slider", { name: "Tua video mẫu" }) as HTMLInputElement;
        expect(seek.value).toBe("168");
        expect(onSelect).toHaveBeenLastCalledWith(1);
        video.currentTime = 3;
        fireEvent.seeked(video);
        expect(seek.value).toBe("24");
        expect(seek.getAttribute("aria-valuetext")).toContain("3 giây");
    });

    it("clamps playback to the reference span and never seeks into the next source frame", () => {
        const { video } = mount();
        video.currentTime = 25;
        fireEvent.timeUpdate(video);
        expect(video.currentTime).toBeCloseTo(431 / 24);
        expect(
            (screen.getByRole("slider", { name: "Tua video mẫu" }) as HTMLInputElement).value,
        ).toBe("383");
        video.currentTime = 0;
        fireEvent.seeked(video);
        expect(video.currentTime).toBe(2);
    });

    it("resets seeking when the source changes and waits for its metadata", () => {
        const { video, rerender } = mount();
        fireEvent.change(screen.getByRole("slider", { name: "Tua video mẫu" }), {
            target: { value: "204" },
        });
        rerender(
            createElement(RemakeSourceTimeline, { ...base, referenceUrl: "/replacement.mp4" }),
        );
        const seek = screen.getByRole("slider", { name: "Tua video mẫu" }) as HTMLInputElement;
        expect(seek.value).toBe("0");
        expect(seek.disabled).toBe(true);
        expect(screen.getByLabelText("Video mẫu — xem theo từng cảnh")).not.toBe(video);
    });

    it("respects locked controls while retaining the source video preview", () => {
        const { video, onSelect } = mount({ disabled: true });
        expect(
            (screen.getByRole("slider", { name: "Tua video mẫu" }) as HTMLInputElement).disabled,
        ).toBe(true);
        const second = screen.getByRole("button", { name: /Cảnh 2\s*9 giây/ }) as HTMLButtonElement;
        expect(second.disabled).toBe(true);
        fireEvent.click(second);
        expect(onSelect).not.toHaveBeenCalled();
        expect(video.controls).toBe(true);
    });

    it("keeps scene buttons useful without a retained source file but disables continuous seeking", () => {
        const onSelect = vi.fn();
        render(createElement(RemakeSourceTimeline, { ...base, referenceUrl: null, onSelect }));
        expect(
            (screen.getByRole("slider", { name: "Tua video mẫu" }) as HTMLInputElement).disabled,
        ).toBe(true);
        fireEvent.click(screen.getByRole("button", { name: /Cảnh 2\s*9 giây/ }));
        expect(onSelect).toHaveBeenCalledWith(1);
    });
});
