// @vitest-environment jsdom
import { createElement } from "react";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { RemakeTrimTools } from "./remake-trim-tools";

afterEach(cleanup);

const item = {
    id: "item",
    sourceSceneId: "source",
    renderUnitId: "unit",
    targetStartFrame: 0,
    targetDurationFrames: 72,
    versionId: "version",
    inFrame: 0,
    outFrame: 72,
    reviewed: false,
};

function mount(overrides: Partial<Parameters<typeof RemakeTrimTools>[0]> = {}) {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const onPreview = vi.fn();
    const view = render(
        createElement(RemakeTrimTools, {
            item,
            versionId: "version",
            rawFrameCount: 192,
            busy: false,
            onSave,
            onPreview,
            ...overrides,
        }),
    );
    return { ...view, onSave, onPreview };
}

describe("visible clip trim track", () => {
    it("keeps a grouped version's suggested offset on the first save", async () => {
        const { onSave } = mount({
            item: { ...item, versionId: null, inFrame: 40, outFrame: 112 },
            suggestedInFrame: 40,
        });
        expect((screen.getByRole("slider") as HTMLInputElement).value).toBe("40");
        fireEvent.click(screen.getByRole("button", { name: "Dùng đoạn này" }));
        await waitFor(() =>
            expect(onSave).toHaveBeenCalledWith([
                {
                    renderUnitId: "unit",
                    versionId: "version",
                    inFrame: 40,
                    outFrame: 112,
                    reviewed: true,
                },
            ]),
        );
    });

    it("prioritizes a saved trim and uses a replacement's own suggestion for a different version", () => {
        const saved = mount({
            item: { ...item, inFrame: 40, outFrame: 112 },
            suggestedInFrame: 24,
        });
        expect((screen.getByRole("slider") as HTMLInputElement).value).toBe("40");
        saved.unmount();
        mount({
            item: { ...item, versionId: "old", inFrame: 40, outFrame: 112 },
            suggestedInFrame: 0,
        });
        expect((screen.getByRole("slider") as HTMLInputElement).value).toBe("0");
    });

    it("offers the chosen segment before optional precision controls", () => {
        const { onPreview, onSave } = mount();
        const precision = screen.getByText("Tinh chỉnh đoạn cắt").closest("details");
        const use = screen.getByRole("button", { name: "Dùng đoạn này" });
        expect(precision).not.toBeNull();
        expect(precision?.open).toBe(false);
        expect(use.closest("details")).toBeNull();
        expect(
            use.compareDocumentPosition(precision!) & Node.DOCUMENT_POSITION_FOLLOWING,
        ).toBeTruthy();
        expect(screen.getByRole("spinbutton", { name: "Bắt đầu (giây)" }).closest("details")).toBe(
            precision,
        );
        expect(screen.getByRole("button", { name: "Xem clip gốc" }).closest("details")).toBe(
            precision,
        );
        expect(screen.getByText("0–3 giây")).toBeTruthy();
        expect(onPreview).not.toHaveBeenCalled();
        expect(onSave).not.toHaveBeenCalled();
    });

    it("keeps exact frame and preview controls available after expanding precision tools", () => {
        const { onPreview, onSave } = mount();
        fireEvent.click(screen.getByText("Tinh chỉnh đoạn cắt"));
        fireEvent.change(screen.getByRole("spinbutton", { name: "Bắt đầu (giây)" }), {
            target: { value: "2" },
        });
        fireEvent.click(screen.getByRole("button", { name: "Tiến điểm bắt đầu 1 frame" }));
        expect(onPreview).toHaveBeenLastCalledWith({ start: 49 / 24, end: 121 / 24 });
        fireEvent.click(screen.getByRole("button", { name: "Xem clip gốc" }));
        expect(onPreview).toHaveBeenLastCalledWith(null);
        fireEvent.click(screen.getByRole("button", { name: "Xem đoạn chọn" }));
        expect(onPreview).toHaveBeenLastCalledWith({ start: 49 / 24, end: 121 / 24 });
        expect(onSave).not.toHaveBeenCalled();
    });

    it("keeps an unchanged saved segment quiet until the range changes", () => {
        const { onSave } = mount({ item: { ...item, reviewed: true } });
        expect(
            (screen.getByRole("button", { name: "Đã chọn đoạn" }) as HTMLButtonElement).disabled,
        ).toBe(true);
        fireEvent.change(screen.getByRole("slider"), { target: { value: "24" } });
        expect(
            (screen.getByRole("button", { name: "Dùng đoạn này" }) as HTMLButtonElement).disabled,
        ).toBe(false);
        expect(onSave).not.toHaveBeenCalled();
    });

    it("uses the visible selection track to preview and explicitly save the selected frames", async () => {
        const { onPreview, onSave } = mount();
        const track = screen.getByRole("group", { name: "Dịch đoạn trong clip AI" });
        const slider = within(track).getByRole("slider", {
            name: "Điểm bắt đầu trong clip AI, frame",
        });
        expect(slider.closest('[aria-hidden="true"]')).toBeNull();
        expect(screen.getAllByRole("slider")).toHaveLength(1);
        fireEvent.change(slider, { target: { value: "48" } });
        expect(onPreview).toHaveBeenLastCalledWith({ start: 2, end: 5 });
        expect((screen.getByLabelText("Bắt đầu (giây)") as HTMLInputElement).value).toBe("2");
        expect(onSave).not.toHaveBeenCalled();
        fireEvent.click(screen.getByRole("button", { name: "Dùng đoạn này" }));
        await waitFor(() =>
            expect(onSave).toHaveBeenCalledWith([
                {
                    renderUnitId: "unit",
                    versionId: "version",
                    inFrame: 48,
                    outFrame: 120,
                    reviewed: true,
                },
            ]),
        );
    });

    it("keeps the shared clip's suggested offset and locks the selected duration", () => {
        const { onPreview } = mount({
            sharedClip: true,
            item: { ...item, targetDurationFrames: 120, inFrame: 72, outFrame: 192 },
        });
        const slider = within(
            screen.getByRole("group", { name: "Dịch đoạn trong clip AI" }),
        ).getByRole("slider") as HTMLInputElement;
        expect(slider.value).toBe("72");
        expect(slider.max).toBe("72");
        fireEvent.change(slider, { target: { value: "24" } });
        expect(onPreview).toHaveBeenLastCalledWith({ start: 1, end: 6 });
    });

    it("explains a whole-clip selection instead of implying that it has room to move", () => {
        mount({ item: { ...item, targetDurationFrames: 192, outFrame: 192 } });
        expect((screen.getByRole("slider") as HTMLInputElement).disabled).toBe(true);
        expect(
            screen.getByText("Đoạn này dùng toàn bộ clip, không cần dịch điểm bắt đầu."),
        ).toBeTruthy();
        expect(
            (screen.getByRole("button", { name: "Dùng đoạn này" }) as HTMLButtonElement).disabled,
        ).toBe(false);
    });

    it("labels a planned six-second clip while still waiting for measured metadata", () => {
        mount({ rawFrameCount: null, plannedFrameCount: 144 });
        expect(screen.getByText("Clip AI · 6 giây")).toBeTruthy();
        expect((screen.getByRole("slider") as HTMLInputElement).disabled).toBe(true);
        expect(
            (screen.getByRole("button", { name: "Dùng đoạn này" }) as HTMLButtonElement).disabled,
        ).toBe(true);
    });

    it.each([{ busy: true }, { rawFrameCount: null }, { rawFrameCount: 48 }])(
        "keeps the visible track locked when the clip cannot be trimmed: %j",
        (props) => {
            mount(props);
            expect((screen.getByRole("slider") as HTMLInputElement).disabled).toBe(true);
            expect(
                (screen.getByRole("button", { name: "Dùng đoạn này" }) as HTMLButtonElement)
                    .disabled,
            ).toBe(true);
        },
    );
});
