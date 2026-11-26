// @vitest-environment jsdom
import { createElement } from "react";
import { act, cleanup, fireEvent, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { RemakePlayer } from "./remake-player";

beforeEach(() => {
    vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => {});
    vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();
});
afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
});

function player(scope = { start: 24 / 24, end: 25 / 24 }) {
    const view = render(
        createElement(RemakePlayer, {
            url: "/bound-evidence.mp4",
            scope,
        }),
    );
    const video = view.container.querySelector("video")!;
    Object.defineProperties(video, {
        duration: { configurable: true, value: 8 },
        videoWidth: { configurable: true, value: 90 },
        videoHeight: { configurable: true, value: 160 },
    });
    fireEvent.loadedMetadata(video);
    return { ...view, video };
}

describe("exclusive-end evidence playback", () => {
    it("shows a subsecond clip duration instead of a zero-length clock", () => {
        const view = player({ start: 0, end: 15 / 24 });
        expect(view.getByText("0:00 / 0:00.625")).toBeTruthy();
        expect(view.getByText("Đoạn được chọn · 0:00–0:00.625")).toBeTruthy();
        expect(view.getByRole("slider").getAttribute("aria-valuetext")).toBe("0:00 trên 0:00.625");
    });
    it("distinguishes fractional boundaries within the same second", () => {
        const view = player({ start: 5 / 24, end: 15 / 24 });
        expect(view.getByText("Đoạn được chọn · 0:00.208–0:00.625")).toBeTruthy();
    });
    it("keeps one-frame durations visible with millisecond precision", () => {
        const view = player({ start: 0, end: 1 / 24 });
        expect(view.getByText("0:00 / 0:00.042")).toBeTruthy();
        expect(view.getByText("Một frame được chọn")).toBeTruthy();
    });
    it("clamps a range seek to the last observed frame instead of the next frame", () => {
        const view = player();
        fireEvent.change(view.getByRole("slider", { name: "Vị trí phát video" }), {
            target: { value: String(25 / 24) },
        });
        expect(view.video.currentTime).toBe(1);
    });
    it("returns an overshooting timeupdate to the last in-range frame", () => {
        const { video } = player();
        video.currentTime = 26 / 24;
        fireEvent.timeUpdate(video);
        expect(video.currentTime).toBe(1);
        expect(video.pause).toHaveBeenCalled();
    });
    it("keeps a single observed frame paused with playback disabled", () => {
        const view = player();
        expect(
            (view.getByRole("button", { name: "Phát video" }) as HTMLButtonElement).disabled,
        ).toBe(true);
        expect(view.getByText("Một frame được chọn")).toBeTruthy();
        expect(view.video.currentTime).toBe(1);
    });
    it("returns to the last frame when a running preview observes its boundary", () => {
        const { video } = player({ start: 1, end: 26 / 24 });
        let frame: VideoFrameRequestCallback | undefined;
        video.requestVideoFrameCallback = vi.fn((callback) => {
            frame = callback;
            return 1;
        });
        video.cancelVideoFrameCallback = vi.fn();
        fireEvent.play(video);
        expect(frame).toBeDefined();
        fireEvent(video, new Event("timeupdate"));
        act(() => frame!(0, { mediaTime: 25 / 24 } as VideoFrameCallbackMetadata));
        expect(video.currentTime).toBeCloseTo(25 / 24, 8);
        expect(video.pause).toHaveBeenCalled();
    });
});
