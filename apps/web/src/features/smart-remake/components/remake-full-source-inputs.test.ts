// @vitest-environment jsdom
import { createElement } from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { RemakeInputs, type RemakeInputsProps } from "./remake-inputs";
import { RemakeBoundaryControls } from "./remake-source-timeline";

afterEach(cleanup);

function inputProps(): RemakeInputsProps {
    return {
        sourceUrl: "blob:source",
        sourceName: "source.mp4",
        productUrls: ["blob:product"],
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
        language: "vi",
        onLanguage: vi.fn(),
        description: "",
        onDescription: vi.fn(),
        brief: "",
        onBrief: vi.fn(),
        disabled: false,
    };
}

describe("full-source intake", () => {
    it("presents a fixed twelve-second output with two six-second clips and audio", () => {
        render(createElement(RemakeInputs, { ...inputProps(), duration: 12 }));
        expect(screen.getByText("12 giây")).toBeTruthy();
        expect(screen.getByText(/2 clip × 6 giây.*Có âm thanh/)).toBeTruthy();
        expect(screen.queryByRole("button", { name: "8 giây" })).toBeNull();
        expect(screen.queryByRole("button", { name: "16 giây" })).toBeNull();
    });
    it("keeps the full measured video separate from the output duration", () => {
        const onStart = vi.fn();
        render(
            createElement(RemakeInputs, {
                ...inputProps(),
                sourceDurationSeconds: 30,
                onTimelineStartFrameChange: onStart,
            }),
        );
        expect(screen.getByText("Phân tích toàn bộ video")).toBeTruthy();
        expect(screen.getByText(/30 giây tư liệu/)).toBeTruthy();
        expect(screen.getByText("Thời lượng video đầu ra")).toBeTruthy();
        expect(screen.queryByLabelText("Điểm bắt đầu đoạn mẫu")).toBeNull();
        expect(screen.queryByText("Đoạn mẫu sẽ dùng")).toBeNull();
        expect(onStart).not.toHaveBeenCalled();
    });

    it("does not reject a source shorter than the chosen output", () => {
        render(
            createElement(RemakeInputs, {
                ...inputProps(),
                duration: 16,
                sourceDurationSeconds: 4,
            }),
        );
        expect(screen.getByText(/4 giây tư liệu/)).toBeTruthy();
        expect(screen.queryByRole("alert")).toBeNull();
        expect(screen.getByText("16 giây")).toBeTruthy();
        expect(screen.queryByText(/2 clip × 6 giây|Có âm thanh/)).toBeNull();
    });

    it("updates the source duration after media metadata has loaded", () => {
        const onMetadata = vi.fn();
        render(createElement(RemakeInputs, { ...inputProps(), onSourceMetadata: onMetadata }));
        const video = screen.getByLabelText("Xem video mẫu");
        Object.defineProperty(video, "duration", { configurable: true, value: 23.5 });
        fireEvent.loadedMetadata(video);
        expect(onMetadata).toHaveBeenCalledWith(23.5);
        expect(screen.getByText(/23,5 giây tư liệu/)).toBeTruthy();
    });
});

describe("source boundaries independent of provider clips", () => {
    it("allows more than four source scenes and still offers another split", () => {
        const change = vi.fn();
        render(
            createElement(RemakeBoundaryControls, {
                sourceCutFrames: [0, 120, 240, 360, 480, 600, 720],
                totalFrames: 720,
                onCutsChange: change,
            }),
        );
        expect(screen.queryByRole("alert")).toBeNull();
        fireEvent.click(screen.getByRole("button", { name: "Chia cảnh dài nhất" }));
        expect(change).toHaveBeenCalledWith([0, 60, 120, 240, 360, 480, 600, 720]);
    });

    it("allows a source scene longer than eight seconds without forcing a cut", () => {
        render(
            createElement(RemakeBoundaryControls, {
                sourceCutFrames: [0, 480, 720],
                compiledCutFrames: [0, 360, 720],
                totalFrames: 720,
                onCutsChange: vi.fn(),
                onRecompile: vi.fn(),
            }),
        );
        expect(screen.queryByRole("alert")).toBeNull();
        expect(
            (screen.getByRole("button", { name: "Cập nhật kịch bản" }) as HTMLButtonElement)
                .disabled,
        ).toBe(false);
    });

    it("still blocks unordered or incomplete boundaries", () => {
        render(
            createElement(RemakeBoundaryControls, {
                sourceCutFrames: [0, 480, 360, 720],
                totalFrames: 720,
                onCutsChange: vi.fn(),
            }),
        );
        expect(screen.getByRole("alert").textContent).toMatch(/liên tiếp|thứ tự|độ dài/);
    });
});
