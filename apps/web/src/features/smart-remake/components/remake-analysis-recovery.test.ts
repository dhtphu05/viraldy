// @vitest-environment jsdom
import { createElement } from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { SmartRemakeProject } from "@/shared/api/smart-remake";
import { RemakeAnalysisRecovery } from "./remake-analysis-recovery";

afterEach(cleanup);
const failed = (retryDisposition?: "new_analysis" | "reconcile") =>
    ({
        id: "project",
        analysisProgress: {
            operationId: "operation",
            requestKey: "request",
            status: "failed",
            startedAt: "2026-11-26T09:00:00Z",
            updatedAt: "2026-11-26T09:01:00Z",
            retryDisposition,
            scenes: [],
            preliminaryObservations: [{ label: "Sản phẩm", detail: "Một chiếc bình hồng" }],
        },
    }) as unknown as SmartRemakeProject;

it("offers one explicit retry and a secondary saved script without exposing historical facts by default", () => {
    const onRetry = vi.fn();
    const onViewSavedScript = vi.fn();
    render(
        createElement(RemakeAnalysisRecovery, {
            project: failed("new_analysis"),
            onRetry,
            onCheckStatus: vi.fn(),
            onViewSavedScript,
        }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Phân tích lại" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Xem kịch bản đã lưu" }));
    expect(onViewSavedScript).toHaveBeenCalledTimes(1);
    expect(screen.getByText(/Kịch bản đã lưu thuộc lượt phân tích trước/)).toBeTruthy();
    expect(document.querySelector("details")?.open).toBe(false);
    expect(screen.queryByRole("button", { name: "Kiểm tra trạng thái" })).toBeNull();
    expect(screen.queryByRole("status")).toBeNull();
});
it.each(["reconcile", undefined] as const)("keeps %s receipt status-only", (disposition) => {
    const onRetry = vi.fn();
    const onCheckStatus = vi.fn();
    render(
        createElement(RemakeAnalysisRecovery, {
            project: failed(disposition),
            onRetry,
            onCheckStatus,
        }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Kiểm tra trạng thái" }));
    expect(onCheckStatus).toHaveBeenCalledTimes(1);
    expect(onRetry).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Phân tích lại" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Xem kịch bản đã lưu" })).toBeNull();
});
it("disables recovery actions while the explicit action runs", () => {
    const onRetry = vi.fn();
    render(
        createElement(RemakeAnalysisRecovery, {
            project: failed("new_analysis"),
            busy: true,
            onRetry,
            onCheckStatus: vi.fn(),
            onViewSavedScript: vi.fn(),
        }),
    );
    for (const button of screen.getAllByRole("button"))
        expect((button as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Phân tích lại" }));
    expect(onRetry).not.toHaveBeenCalled();
});
it("does not invent a timestamp or render recovery for a completed analysis", () => {
    const project = failed("new_analysis");
    project.analysisProgress = { ...project.analysisProgress!, startedAt: "invalid" };
    const props = { project, onRetry: vi.fn(), onCheckStatus: vi.fn() };
    const view = render(createElement(RemakeAnalysisRecovery, props));
    expect(screen.queryByText(/Lượt phân tích bắt đầu lúc/)).toBeNull();
    project.analysisProgress = { ...project.analysisProgress, status: "completed" };
    view.rerender(createElement(RemakeAnalysisRecovery, { ...props, project: { ...project } }));
    expect(screen.queryByRole("region")).toBeNull();
});
