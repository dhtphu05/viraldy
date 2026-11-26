// @vitest-environment jsdom
import { createElement } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { RemakeImagePreview } from "./remake-image-preview";

afterEach(() => {
    cleanup();
    vi.useRealTimers();
});

describe("imported product preview", () => {
    it("settles loading and resets failure when the selected source changes", () => {
        const view = render(
            createElement(RemakeImagePreview, { src: "blob:first", alt: "Sản phẩm" }),
        );
        expect(screen.getByRole("status").textContent).toContain("Đang tải ảnh");
        fireEvent.load(screen.getByAltText("Sản phẩm"));
        expect(screen.queryByRole("status")).toBeNull();
        fireEvent.error(screen.getByAltText("Sản phẩm"));
        expect(screen.getByRole("alert").textContent).toContain("Chưa mở được ảnh");
        view.rerender(createElement(RemakeImagePreview, { src: "blob:second", alt: "Sản phẩm" }));
        expect(screen.queryByRole("alert")).toBeNull();
        expect(screen.getByRole("status").textContent).toContain("Đang tải ảnh");
        expect(screen.getByAltText("Sản phẩm").getAttribute("src")).toBe("blob:second");
    });

    it("ends a stalled loader and can still display an image that arrives late", () => {
        vi.useFakeTimers();
        render(createElement(RemakeImagePreview, { src: "blob:slow", alt: "Sản phẩm" }));
        act(() => vi.advanceTimersByTime(15000));
        expect(screen.queryByRole("status")).toBeNull();
        expect(screen.getByRole("alert")).toBeTruthy();
        fireEvent.load(screen.getByAltText("Sản phẩm"));
        expect(screen.queryByRole("alert")).toBeNull();
        act(() => vi.advanceTimersByTime(15000));
        expect(screen.queryByRole("alert")).toBeNull();
    });

    it("opens the original image in a keyboard-accessible dialog and restores trigger focus", async () => {
        render(
            createElement(RemakeImagePreview, {
                src: "blob:original",
                alt: "Bình hồng",
                enlarge: true,
            }),
        );
        const trigger = screen.getByRole("button", { name: "Phóng to ảnh sản phẩm" });
        trigger.focus();
        fireEvent.click(trigger);
        const dialog = screen.getByRole("dialog", { name: "Ảnh sản phẩm" });
        expect(dialog.querySelector("img")?.getAttribute("src")).toBe("blob:original");
        fireEvent.keyDown(dialog, { key: "Escape" });
        await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
        await waitFor(() => expect(document.activeElement).toBe(trigger));
    });

    it("keeps enlarging unavailable while the input is locked", () => {
        render(
            createElement(RemakeImagePreview, {
                src: "blob:original",
                alt: "Sản phẩm",
                enlarge: true,
                disabled: true,
            }),
        );
        const trigger = screen.getByRole("button", {
            name: "Phóng to ảnh sản phẩm",
        }) as HTMLButtonElement;
        expect(trigger.disabled).toBe(true);
        fireEvent.click(trigger);
        expect(screen.queryByRole("dialog")).toBeNull();
    });
});
