// @vitest-environment jsdom
import { cleanup, fireEvent, render } from "@testing-library/react";
import { createElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { RemakeResultNextStep } from "./remake-result-next-step";
afterEach(cleanup);
describe("result next step", () => {
    it("keeps scene navigation quiet while completion actions remain primary", () => {
        const scene = {
            kind: "scene" as const,
            label: "Xem cảnh 1 cần xử lý",
            reason: "Xem clip và chọn đoạn sẽ ghép.",
            sceneId: "scene",
        };
        const onAction = vi.fn();
        const view = render(createElement(RemakeResultNextStep, { action: scene, onAction }));
        const jump = view.getByRole("button", { name: scene.label });
        expect(jump.classList.contains("bg-[#e00b41]")).toBe(false);
        fireEvent.click(jump);
        expect(onAction).toHaveBeenCalledWith(scene);
        view.rerender(
            createElement(RemakeResultNextStep, {
                action: {
                    kind: "compose",
                    label: "Ghép bản xem trước",
                    reason: "Các đoạn đã sẵn sàng.",
                },
                onAction,
            }),
        );
        expect(view.getByRole("button").classList.contains("bg-[#e00b41]")).toBe(true);
    });
    it("makes known initial generation failure one recovery action and script navigation only", () => {
        const action = {
            kind: "retry_render" as const,
            label: "Tiếp tục tạo video",
            reason: "Ảnh tham chiếu chưa tạo được.",
            recovery: {
                kind: "retry_initial_render" as const,
                stage: "image" as const,
                errorCode: "OPENAI_RATE_LIMITED",
                requestKey: "failed",
                httpStatus: 429,
            },
        };
        const onAction = vi.fn(),
            onViewScript = vi.fn();
        const view = render(
            createElement(RemakeResultNextStep, {
                action,
                onAction,
                onViewScript,
                budget: { policy: { mode: "unlimited" }, knownActualUsd: "0", exposureUsd: null },
            }),
        );
        expect(view.queryByRole("list", { name: "Các bước hoàn thiện video" })).toBeNull();
        const technical = view.getByText("Chưa gửi lượt tạo video tới KIE.").closest("details");
        expect(technical).not.toBeNull();
        expect(technical?.open).toBe(false);
        expect(view.queryByText("CHUẨN BỊ ẢNH THAM CHIẾU")).toBeNull();
        fireEvent.click(view.getByRole("button", { name: "Xem kịch bản" }));
        expect(onViewScript).toHaveBeenCalledTimes(1);
        expect(onAction).not.toHaveBeenCalled();
        fireEvent.click(view.getByRole("button", { name: "Tiếp tục tạo video" }));
        expect(onAction).toHaveBeenCalledWith(action);
        expect(view.getByText("Chi phí chưa xác định")).toBeTruthy();
    });
    it("names a known image credit blocker and keeps technical costs behind disclosure", () => {
        const action = {
            kind: "retry_render" as const,
            label: "Tiếp tục tạo video",
            reason: "Bổ sung tín dụng cho dịch vụ tạo ảnh rồi tiếp tục từ kịch bản đã lưu.",
            recovery: {
                kind: "retry_initial_render" as const,
                stage: "image" as const,
                errorCode: "OPENAI_IMAGE_CREDITS_EXHAUSTED",
                providerErrorCode: "credit_balance_exhausted",
                requestKey: "failed",
                httpStatus: 429,
            },
        };
        const onAction = vi.fn();
        const view = render(
            createElement(RemakeResultNextStep, {
                action,
                onAction,
                technicalError: "Provider receipt is retained.",
                budget: {
                    policy: { mode: "unlimited" },
                    knownActualUsd: "0.12",
                    exposureUsd: null,
                },
            }),
        );
        expect(view.getByRole("heading", { name: "Cần bổ sung tín dụng tạo ảnh" })).toBeTruthy();
        const cost = view.getByText("Phí đã xác định: 0.12 USD").closest("details");
        expect(cost?.open).toBe(false);
        expect(view.getByText("Chi phí chưa xác định").closest("details")).toBe(cost);
        expect(view.getByText("Provider receipt is retained.").closest("details")).toBe(cost);
        expect(onAction).not.toHaveBeenCalled();
    });
    it("has one clear primary action and candidate dismissal never applies a version", () => {
        const action = {
            kind: "candidate" as const,
            label: "Xem bản mới cảnh 1",
            reason: "Bản đang dùng được giữ.",
            sceneId: "scene",
            versionId: "candidate",
        };
        const onAction = vi.fn(),
            onDismissCandidate = vi.fn();
        const view = render(
            createElement(RemakeResultNextStep, { action, onAction, onDismissCandidate }),
        );
        expect(onAction).not.toHaveBeenCalled();
        fireEvent.click(view.getByRole("button", { name: "Tiếp tục với bản đang dùng" }));
        expect(onDismissCandidate).toHaveBeenCalledTimes(1);
        expect(onAction).not.toHaveBeenCalled();
        fireEvent.click(view.getByRole("button", { name: action.label }));
        expect(onAction).toHaveBeenCalledWith(action);
    });
    it("keeps status checks actionable but disables actions while saving and blocked states", () => {
        const action = {
            kind: "progress" as const,
            label: "Kiểm tra trạng thái",
            reason: "Đối soát yêu cầu cũ.",
        };
        const view = render(createElement(RemakeResultNextStep, { action, onAction: vi.fn() }));
        expect((view.getByRole("button") as HTMLButtonElement).disabled).toBe(false);
        view.rerender(
            createElement(RemakeResultNextStep, { action, onAction: vi.fn(), busy: true }),
        );
        expect((view.getByRole("button") as HTMLButtonElement).disabled).toBe(true);
        view.rerender(
            createElement(RemakeResultNextStep, {
                action: { ...action, kind: "blocked" },
                onAction: vi.fn(),
            }),
        );
        expect((view.getByRole("button") as HTMLButtonElement).disabled).toBe(true);
    });
});
