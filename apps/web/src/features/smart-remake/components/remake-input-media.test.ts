// @vitest-environment jsdom
import { createElement } from "react";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { RemakeInputs, type RemakeInputsProps } from "./remake-inputs";

afterEach(() => {
    cleanup();
    vi.useRealTimers();
});

function inputProps(): RemakeInputsProps {
    return {
        sourceUrl: "blob:video",
        sourceName: "demo.mp4",
        productUrls: [],
        primaryIndex: 0,
        onPrimaryChange: vi.fn(),
        onVideo: vi.fn(),
        onImages: vi.fn(),
        onRemoveImage: vi.fn(),
        link: "",
        onLinkChange: vi.fn(),
        onLinkSubmit: vi.fn(),
        isLinkLoading: false,
        duration: 8,
        onDuration: vi.fn(),
        language: "",
        onLanguage: vi.fn(),
        description: "",
        onDescription: vi.fn(),
        brief: "",
        onBrief: vi.fn(),
        disabled: false,
        onSourceMetadata: vi.fn(),
    };
}

describe("source video preview feedback", () => {
    it("preserves native playback and metadata callbacks while ending the loader", () => {
        const props = inputProps();
        render(createElement(RemakeInputs, props));
        const video = screen.getByLabelText("Xem video mẫu") as HTMLVideoElement;
        expect(video.style.visibility).toBe("hidden");
        expect(screen.getByText("Đang mở video mẫu…")).toBeTruthy();
        Object.defineProperties(video, {
            duration: { value: 12.5 },
            videoWidth: { value: 1920 },
            videoHeight: { value: 1080 },
        });
        fireEvent.loadedMetadata(video);
        expect(props.onSourceMetadata).toHaveBeenCalledWith(12.5);
        expect(screen.queryByText("Đang mở video mẫu…")).toBeNull();
        expect(video.style.visibility).toBe("visible");
        expect(Number.parseFloat(video.style.aspectRatio)).toBeCloseTo(1920 / 1080, 4);
        expect(video.controls).toBe(true);
        expect(video.autoplay).toBe(false);
        expect(screen.getByText("12,5 giây tư liệu")).toBeTruthy();
    });

    it("offers a recovery message for broken media and resets on a new source", () => {
        const props = inputProps();
        const view = render(createElement(RemakeInputs, props));
        const video = screen.getByLabelText("Xem video mẫu") as HTMLVideoElement;
        fireEvent.error(video);
        expect(video.style.visibility).toBe("hidden");
        expect(screen.getByRole("alert").textContent).toContain("Chưa mở được video");
        expect(screen.getByRole("button", { name: "Chọn video khác" })).toBeTruthy();
        view.rerender(createElement(RemakeInputs, { ...props, sourceUrl: "blob:replacement" }));
        expect(screen.queryByRole("alert")).toBeNull();
        expect(screen.getByText("Đang mở video mẫu…")).toBeTruthy();
    });

    it("stops waiting on stalled media without hiding the replace action", () => {
        vi.useFakeTimers();
        render(createElement(RemakeInputs, inputProps()));
        act(() => vi.advanceTimersByTime(15000));
        expect(screen.queryByText("Đang mở video mẫu…")).toBeNull();
        expect(screen.getByRole("alert").textContent).toContain("Chọn lại file");
        expect(
            (screen.getByRole("button", { name: "Chọn video khác" }) as HTMLButtonElement).disabled,
        ).toBe(false);
    });
});
