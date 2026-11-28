// @vitest-environment jsdom
import { createElement } from "react";
import { act, cleanup, fireEvent, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { RemakePlayer, type RemakePlayerProps } from "./remake-player";

const segments = [
    { targetStart: 0, targetEnd: 3, sourceStart: 0, sourceEnd: 6 },
    { targetStart: 3, targetEnd: 6, sourceStart: 10, sourceEnd: 13 },
];
let paused: WeakMap<HTMLMediaElement, boolean>;

beforeEach(() => {
    paused = new WeakMap();
    vi.spyOn(HTMLMediaElement.prototype, "paused", "get").mockImplementation(function (
        this: HTMLMediaElement,
    ) {
        return paused.get(this) ?? true;
    });
    vi.spyOn(HTMLMediaElement.prototype, "play").mockImplementation(function (
        this: HTMLMediaElement,
    ) {
        paused.set(this, false);
        fireEvent.play(this);
        return Promise.resolve();
    });
    vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(function (
        this: HTMLMediaElement,
    ) {
        const wasPlaying = !this.paused;
        paused.set(this, true);
        if (wasPlaying) fireEvent.pause(this);
    });
    vi.stubGlobal(
        "requestAnimationFrame",
        vi.fn(() => 1),
    );
    vi.stubGlobal("cancelAnimationFrame", vi.fn());
});
afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
});

function metadata(video: HTMLVideoElement, duration: number) {
    Object.defineProperties(video, {
        duration: { configurable: true, value: duration },
        videoWidth: { configurable: true, value: 90 },
        videoHeight: { configurable: true, value: 160 },
        readyState: { configurable: true, value: 4 },
    });
    fireEvent.loadedMetadata(video);
    fireEvent.canPlay(video);
}
function setPlay(
    video: HTMLVideoElement,
    implementation: (this: HTMLMediaElement) => Promise<void>,
) {
    Object.defineProperty(video, "play", { configurable: true, value: vi.fn(implementation) });
}
function player(overrides: Partial<RemakePlayerProps> = {}) {
    const props = {
        url: "/remake.mp4",
        scope: null,
        sourceComparison: { url: "/source.mp4", segments },
        ...overrides,
    };
    const view = render(createElement(RemakePlayer, props));
    return {
        ...view,
        props,
        source: view.container.querySelector('video[src="/source.mp4"]')!,
        remake: view.container.querySelector('video[src="/remake.mp4"]')!,
    } as ReturnType<typeof render> & {
        props: RemakePlayerProps;
        source: HTMLVideoElement;
        remake: HTMLVideoElement;
    };
}
async function play(view: ReturnType<typeof player>) {
    await act(async () => fireEvent.click(view.getByRole("button", { name: "Phát video" })));
}

describe("source and remake playback", () => {
    it("keeps the original left and remake right visible together on narrow screens", () => {
        const view = player();
        expect([...view.container.querySelectorAll("video")].map((video) => video.src)).toEqual([
            "http://localhost/source.mp4",
            "http://localhost/remake.mp4",
        ]);
        expect(view.source.closest("figure")?.className).not.toMatch(/\bhidden\b/);
        expect(view.remake.closest("figure")?.className).not.toMatch(/\bhidden\b/);
        expect(view.getByText("Video gốc")).toBeTruthy();
        expect(view.getByText("Bản remake")).toBeTruthy();
        expect(view.getByText(/Video gốc được điều chỉnh tốc độ theo từng cảnh/)).toBeTruthy();
    });
    it("waits for the late source metadata without playing the remake alone", async () => {
        const view = player();
        metadata(view.remake, 6);
        expect(
            (view.getByRole("button", { name: "Phát video" }) as HTMLButtonElement).disabled,
        ).toBe(true);
        expect(view.remake.play).not.toHaveBeenCalled();
        metadata(view.source, 20);
        expect(
            (view.getByRole("button", { name: "Phát video" }) as HTMLButtonElement).disabled,
        ).toBe(false);
        expect(view.remake.play).not.toHaveBeenCalled();
        await play(view);
        expect(view.remake.paused).toBe(false);
        expect(view.source.paused).toBe(false);
    });
    it("seeks both videos and changes source speed at the actual scene boundary", () => {
        const view = player();
        metadata(view.remake, 6);
        metadata(view.source, 20);
        const slider = view.getByRole("slider", { name: "Vị trí phát video" });
        fireEvent.change(slider, { target: { value: "2" } });
        expect(view.remake.currentTime).toBe(2);
        expect(view.source.currentTime).toBe(4);
        expect(view.source.playbackRate).toBe(2);
        fireEvent.change(slider, { target: { value: "4" } });
        expect(view.source.currentTime).toBe(11);
        expect(view.source.playbackRate).toBe(1);
    });
    it("corrects source drift per video frame without waiting for timeupdate", async () => {
        const view = player();
        metadata(view.remake, 6);
        metadata(view.source, 20);
        let frame: VideoFrameRequestCallback | undefined;
        view.remake.requestVideoFrameCallback = vi.fn((callback) => {
            frame = callback;
            return 1;
        });
        view.remake.cancelVideoFrameCallback = vi.fn();
        await play(view);
        view.source.currentTime = 1;
        act(() => frame!(0, { mediaTime: 4 } as VideoFrameCallbackMetadata));
        expect(view.source.currentTime).toBe(11);
        expect(view.source.playbackRate).toBe(1);
        view.unmount();
        expect(view.remake.cancelVideoFrameCallback).toHaveBeenCalled();
        expect(view.source.paused).toBe(true);
        expect(view.remake.paused).toBe(true);
    });
    it("uses animation frames when video-frame callbacks are unavailable and pauses on a native source pause", async () => {
        const view = player();
        metadata(view.remake, 6);
        metadata(view.source, 20);
        await play(view);
        view.remake.currentTime = 4;
        view.source.currentTime = 1;
        const frame = vi.mocked(requestAnimationFrame).mock.calls.at(-1)![0];
        act(() => frame(0));
        expect(view.source.currentTime).toBe(11);
        act(() => view.source.pause());
        expect(view.remake.paused).toBe(true);
        expect(view.source.paused).toBe(true);
    });
    it("buffers both and automatically resumes the same play intent when both are ready", async () => {
        const view = player();
        metadata(view.remake, 6);
        metadata(view.source, 20);
        await play(view);
        fireEvent.waiting(view.source);
        expect(view.source.paused).toBe(true);
        expect(view.remake.paused).toBe(true);
        expect(view.getByRole("button", { name: "Tạm dừng video" })).toBeTruthy();
        await act(async () => fireEvent.canPlay(view.source));
        expect(view.remake.paused).toBe(false);
        expect(view.source.paused).toBe(false);
        fireEvent.waiting(view.remake);
        expect(view.source.paused).toBe(true);
        expect(view.remake.paused).toBe(true);
    });
    it("allows exactly one audio source and retains the mute control", () => {
        const view = player();
        metadata(view.remake, 6);
        metadata(view.source, 20);
        expect(view.source.muted).toBe(true);
        expect(view.remake.muted).toBe(false);
        fireEvent.click(view.getByRole("button", { name: "Nghe video gốc" }));
        expect(view.source.muted).toBe(false);
        expect(view.remake.muted).toBe(true);
        fireEvent.click(view.getByRole("button", { name: "Tắt âm thanh" }));
        expect(view.source.muted).toBe(true);
        expect(view.remake.muted).toBe(true);
        fireEvent.click(view.getByRole("button", { name: "Nghe bản remake" }));
        expect(view.source.muted).toBe(true);
        expect(view.remake.muted).toBe(true);
        fireEvent.click(view.getByRole("button", { name: "Bật âm thanh" }));
        expect(view.remake.muted).toBe(false);
    });
    it("does not seek or pause again when a parent polls with an equivalent mapping", async () => {
        const view = player();
        metadata(view.remake, 6);
        metadata(view.source, 20);
        await play(view);
        view.remake.currentTime = 2;
        let sourceTime = 4.1;
        const seek = vi.fn((value: number) => {
            sourceTime = value;
        });
        Object.defineProperty(view.source, "currentTime", {
            configurable: true,
            get: () => sourceTime,
            set: seek,
        });
        view.rerender(
            createElement(RemakePlayer, {
                ...view.props,
                sourceComparison: {
                    url: "/source.mp4",
                    segments: segments.map((segment) => ({ ...segment })),
                },
            }),
        );
        expect(seek).not.toHaveBeenCalled();
        expect(view.source.paused).toBe(false);
        expect(view.remake.paused).toBe(false);
        expect(view.container.querySelector('video[src="/source.mp4"]')).toBe(view.source);
    });
    it("keeps resumed playback from seeking the source again after a buffering event", async () => {
        const view = player();
        metadata(view.remake, 6);
        metadata(view.source, 20);
        await play(view);
        view.remake.currentTime = 2;
        let sourceTime = 4.05;
        const seek = vi.fn((value: number) => {
            sourceTime = value;
        });
        Object.defineProperty(view.source, "currentTime", {
            configurable: true,
            get: () => sourceTime,
            set: seek,
        });
        fireEvent.waiting(view.source);
        await act(async () => fireEvent.canPlay(view.source));
        expect(seek).not.toHaveBeenCalled();
        expect(view.source.paused).toBe(false);
        expect(view.remake.paused).toBe(false);
    });
    it("lets the user cancel the retained play intent while buffering", async () => {
        const view = player();
        metadata(view.remake, 6);
        metadata(view.source, 20);
        await play(view);
        fireEvent.waiting(view.source);
        fireEvent.click(view.getByRole("button", { name: "Tạm dừng video" }));
        await act(async () => fireEvent.canPlay(view.source));
        expect(view.source.paused).toBe(true);
        expect(view.remake.paused).toBe(true);
        expect(view.getByRole("button", { name: "Phát video" })).toBeTruthy();
    });
    it("offers source retry or explicit remake-only playback after an original fails", async () => {
        const view = player();
        metadata(view.remake, 6);
        fireEvent.error(view.source);
        expect(view.getByRole("button", { name: "Tải lại video gốc" })).toBeTruthy();
        fireEvent.click(view.getByRole("button", { name: "Tải lại video gốc" }));
        expect(view.queryByRole("button", { name: "Tải lại video gốc" })).toBeNull();
        const retried = view.container.querySelector('video[src="/source.mp4"]')!;
        fireEvent.error(retried);
        fireEvent.click(view.getByRole("button", { name: "Chỉ xem bản remake" }));
        expect(view.container.querySelectorAll("video")).toHaveLength(1);
        await play(view);
        expect(view.remake.paused).toBe(false);
    });
    it("treats invalid original metadata as a recoverable source failure", () => {
        const onError = vi.fn();
        const view = player({ onError });
        metadata(view.remake, 6);
        metadata(view.source, 0);
        expect(view.getByRole("button", { name: "Tải lại video gốc" })).toBeTruthy();
        expect(onError).not.toHaveBeenCalled();
        expect(view.remake.paused).toBe(true);
    });
    it("cancels a pending play promise on pause and does not resurrect it", async () => {
        const view = player();
        metadata(view.remake, 6);
        metadata(view.source, 20);
        let resolve!: () => void;
        setPlay(view.source, function (this: HTMLMediaElement) {
            paused.set(this, false);
            return new Promise<void>((done) => {
                resolve = done;
            });
        });
        fireEvent.click(view.getByRole("button", { name: "Phát video" }));
        fireEvent.click(view.getByRole("button", { name: "Tạm dừng video" }));
        await act(async () => resolve());
        expect(view.remake.paused).toBe(true);
        expect(view.source.paused).toBe(true);
    });
    it("does not resurrect either video when a pending play settles after unmount", async () => {
        const view = player();
        metadata(view.remake, 6);
        metadata(view.source, 20);
        let resolve!: () => void;
        setPlay(view.source, function (this: HTMLMediaElement) {
            return new Promise<void>((done) => {
                resolve = () => {
                    paused.set(this, false);
                    done();
                };
            });
        });
        fireEvent.click(view.getByRole("button", { name: "Phát video" }));
        view.unmount();
        await act(async () => resolve());
        expect(view.source.paused).toBe(true);
        expect(view.remake.paused).toBe(true);
    });
    it("keeps its own restart seek from cancelling the new play intent", async () => {
        const view = player();
        metadata(view.remake, 6);
        metadata(view.source, 20);
        view.remake.currentTime = 6 - 1 / 24;
        let resolve!: () => void;
        setPlay(view.source, function (this: HTMLMediaElement) {
            paused.set(this, false);
            return new Promise<void>((done) => {
                resolve = done;
            });
        });
        fireEvent.click(view.getByRole("button", { name: "Phát video" }));
        fireEvent.seeking(view.remake);
        await act(async () => resolve());
        expect(view.remake.currentTime).toBe(0);
        expect(view.source.currentTime).toBe(0);
        expect(view.remake.paused).toBe(false);
        expect(view.source.paused).toBe(false);
    });
    it("pauses the currently mounted retried source on unmount", async () => {
        const view = player();
        metadata(view.remake, 6);
        fireEvent.error(view.source);
        fireEvent.click(view.getByRole("button", { name: "Tải lại video gốc" }));
        const retried = view.container.querySelector(
            'video[src="/source.mp4"]',
        ) as HTMLVideoElement;
        expect(retried).not.toBe(view.source);
        metadata(retried, 20);
        await play(view);
        expect(retried.paused).toBe(false);
        view.unmount();
        expect(retried.paused).toBe(true);
        expect(view.remake.paused).toBe(true);
    });
    it("offers a fallback for rejected source playback without marking the remake as failed", async () => {
        const onError = vi.fn();
        const view = player({ onError });
        metadata(view.remake, 6);
        metadata(view.source, 20);
        setPlay(view.source, () => Promise.reject(new Error("source blocked")));
        await play(view);
        expect(view.getByRole("button", { name: "Chỉ xem bản remake" })).toBeTruthy();
        expect(onError).not.toHaveBeenCalled();
        expect(view.source.paused).toBe(true);
        expect(view.remake.paused).toBe(true);
    });
    it("limits unsupported native playback rates while still seeking to the mapped source time", () => {
        const view = player({
            sourceComparison: {
                url: "/source.mp4",
                segments: [{ targetStart: 0, targetEnd: 1, sourceStart: 0, sourceEnd: 20 }],
            },
        });
        let rate = 1;
        Object.defineProperty(view.source, "playbackRate", {
            configurable: true,
            get: () => rate,
            set: (value: number) => {
                if (value > 4) throw new Error("unsupported rate");
                rate = value;
            },
        });
        metadata(view.remake, 1);
        metadata(view.source, 20);
        fireEvent.change(view.getByRole("slider"), { target: { value: "0.5" } });
        expect(view.source.currentTime).toBe(10);
        expect(view.source.playbackRate).toBe(4);
        expect(view.queryByRole("button", { name: "Chỉ xem bản remake" })).toBeNull();
    });
    it("pauses and maps to the final observed frame when the remake ends", async () => {
        const view = player();
        metadata(view.remake, 6);
        metadata(view.source, 20);
        await play(view);
        view.remake.currentTime = 6;
        fireEvent.ended(view.remake);
        expect(view.source.paused).toBe(true);
        expect(view.remake.paused).toBe(true);
        expect(view.remake.currentTime).toBeCloseTo(6 - 1 / 24);
        expect(view.source.currentTime).toBeCloseTo(13 - 1 / 24);
    });
    it("preserves candidate comparison precedence and single-frame scope behavior", () => {
        const view = player({ compareUrl: "/candidate.mp4", scope: { start: 1, end: 25 / 24 } });
        expect(view.source).toBeNull();
        expect(view.container.querySelector('video[src="/candidate.mp4"]')).toBeTruthy();
        metadata(view.remake, 6);
        expect(
            (view.getByRole("button", { name: "Phát video" }) as HTMLButtonElement).disabled,
        ).toBe(true);
        expect(view.getByText("Một frame được chọn")).toBeTruthy();
    });
});
