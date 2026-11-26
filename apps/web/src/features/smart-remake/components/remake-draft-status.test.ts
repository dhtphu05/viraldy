// @vitest-environment jsdom
import { createElement } from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { RemakeDraftStatus } from "./remake-draft-status";
afterEach(cleanup);
it("only describes committed media as saved on the device", () => {
    const { rerender } = render(createElement(RemakeDraftStatus, { status: "saving" }));
    expect(screen.queryByText("Đã lưu trên thiết bị này")).toBeNull();
    rerender(createElement(RemakeDraftStatus, { status: "saved" }));
    expect(screen.getByText("Đã lưu trên thiết bị này")).toBeTruthy();
});
it("preserves stale content for reading and only discards the selected section on click", () => {
    const onDiscard = vi.fn();
    render(
        createElement(RemakeDraftStatus, {
            status: "conflict",
            conflicts: { repair: { value: { instruction: "Nắp xanh" } } },
            onDiscard,
        }),
    );
    expect(screen.getByText(/Nắp xanh/)).toBeTruthy();
    expect(onDiscard).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Bỏ nháp sửa cảnh cũ" }));
    expect(onDiscard).toHaveBeenCalledWith("repair");
});
it("offers explicit retry and local removal without claiming the failed draft was saved", () => {
    const onRetry = vi.fn(),
        onRemove = vi.fn();
    render(
        createElement(RemakeDraftStatus, {
            status: "error",
            error: "Dung lượng đầy",
            onRetry,
            onRemove,
        }),
    );
    expect(screen.getByRole("alert").textContent).toBe("Dung lượng đầy");
    expect(screen.queryByText("Đã lưu trên thiết bị này")).toBeNull();
    expect(onRemove).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Thử lưu lại" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Xóa nháp trên thiết bị này" }));
    expect(onRemove).toHaveBeenCalledTimes(1);
});
