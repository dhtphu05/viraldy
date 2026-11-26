// @vitest-environment jsdom
import { createElement } from "react";
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { RemakeResultNextAction } from "../lib/remake-result-next-action";
import { RemakeResultNextStep } from "./remake-result-next-step";

afterEach(cleanup);

it.each([
    ["scene", "Duyệt từng cảnh"],
    ["compose", "Ghép bản xem trước"],
    ["assembly_error", "Ghép bản xem trước"],
    ["inspect", "Kiểm tra & duyệt"],
    ["findings", "Kiểm tra & duyệt"],
    ["approve", "Kiểm tra & duyệt"],
    ["export", "Tải video"],
] as const)("locates %s in the actual result workflow", (kind, label) => {
    render(
        createElement(RemakeResultNextStep, {
            action: { kind, label: "Tiếp tục", reason: "Công việc hiện tại" },
            onAction: vi.fn(),
        }),
    );
    const workflow = screen.getByRole("list", { name: "Các bước hoàn thiện video" });
    expect(workflow.classList.contains("sr-only")).toBe(true);
    expect(within(workflow).getAllByRole("listitem")).toHaveLength(4);
    expect(workflow.querySelector('[aria-current="step"]')?.textContent).toContain(label);
    expect(within(workflow).queryByRole("button")).toBeNull();
});

it.each(["progress", "blocked"] as RemakeResultNextAction["kind"][])(
    "does not invent a current milestone for %s",
    (kind) => {
        render(
            createElement(RemakeResultNextStep, {
                action: { kind, label: "Kiểm tra trạng thái", reason: "Đang đối soát yêu cầu" },
                onAction: vi.fn(),
            }),
        );
        const workflow = screen.getByRole("list", { name: "Các bước hoàn thiện video" });
        expect(workflow.querySelector("[aria-current]")).toBeNull();
        expect(workflow.textContent).not.toMatch(/hoàn tất|đã duyệt/i);
    },
);
