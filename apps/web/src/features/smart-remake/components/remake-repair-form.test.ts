// @vitest-environment jsdom
import { cleanup, fireEvent, render, waitFor } from "@testing-library/react";
import { createElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type {
    RepairIntent,
    SmartRemakeProject,
    SmartRemakeSceneVersion,
} from "@/shared/api/smart-remake";
import { RemakeRepairForm } from "./remake-repair-form";
const active: SmartRemakeSceneVersion = {
    id: "active",
    parentVersionId: null,
    videoUrl: "/active.mp4",
    prompt: "Keep composition",
    imagePrompt: "Product photo",
    videoPrompt: "Open lid once",
    source: "generated",
    createdAt: "",
    technicalCheck: { status: "passed", findings: [], checkedAt: "", mediaHash: "hash" },
};
const scene: SmartRemakeProject["scenes"][number] = {
    id: "scene",
    index: 0,
    startSecond: 0,
    durationSeconds: 8,
    activeVersionId: "active",
    prompt: "Keep composition",
    imagePrompt: "Product photo",
    videoPrompt: "Open lid once",
    versions: [active],
};
const setup = (extra = {}) => {
    const onRepair = vi.fn().mockResolvedValue(undefined),
        onDraftChange = vi.fn();
    return {
        ...render(
            createElement(RemakeRepairForm, {
                workspaceId: "workspace",
                projectId: "project",
                scene,
                active,
                busy: false,
                onRepair,
                onDraftChange,
                ...extra,
            }),
        ),
        onRepair,
        onDraftChange,
    };
};
beforeEach(() => {
    const values = new Map<string, string>();
    vi.stubGlobal("localStorage", {
        getItem: (key: string) => values.get(key) ?? null,
        setItem: (key: string, value: string) => values.set(key, value),
        removeItem: (key: string) => values.delete(key),
    });
});
afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
});
describe("structured seller repair", () => {
    it.each([
        undefined,
        { ...active, id: "different-version" },
        { ...active, technicalCheck: { ...active.technicalCheck, status: "failed" } },
    ])(
        "cannot submit a repair without a usable active clip even if the form is mounted directly: %s",
        (base) => {
            const view = setup({ active: base });
            const form = view.container.querySelector("form");
            if (form) fireEvent.submit(form);
            expect(view.onRepair).not.toHaveBeenCalled();
            expect(view.queryByRole("button", { name: "Tạo lại cảnh 1" })).toBeNull();
            expect(view.getByText(/Chưa có clip để sửa/)).toBeTruthy();
        },
    );
    it("explains the AI check and new candidate while preserving the current clip without promising a grant form", () => {
        const view = setup();
        expect(
            view.getByText(/AI sẽ kiểm tra yêu cầu trước khi tạo ảnh và video/).textContent,
        ).toContain("một bản mới để bạn so sánh");
        expect(view.getByText(/Bản đang dùng được giữ đến khi bạn áp dụng bản mới/)).toBeTruthy();
        expect(view.queryByText(/xác nhận phạm vi|giới hạn chi phí/)).toBeNull();
    });
    it("sends alternate_take without requiring or rewriting prompts", async () => {
        const view = setup();
        expect(view.getByLabelText("Prompt tạo video").closest("details")?.open).toBe(false);
        fireEvent.click(view.getByRole("button", { name: "Tạo lại cảnh 1" }));
        await waitFor(() =>
            expect(view.onRepair).toHaveBeenCalledWith({
                schemaVersion: 1,
                issues: ["alternate_take"],
                instruction: "",
            }),
        );
    });
    it("sends stable issue codes and plain instruction separately from advanced prompts", async () => {
        const view = setup();
        fireEvent.click(view.getByRole("button", { name: "Sai sản phẩm" }));
        fireEvent.click(view.getByRole("button", { name: "Chuyển động chưa đúng" }));
        fireEvent.change(view.getByLabelText("Bạn muốn thay đổi điều gì? (không bắt buộc)"), {
            target: { value: "Mở nắp chậm hơn" },
        });
        expect((view.getByLabelText("Prompt tạo video") as HTMLTextAreaElement).value).toBe(
            scene.videoPrompt,
        );
        fireEvent.click(view.getByRole("button", { name: "Tạo lại cảnh 1" }));
        await waitFor(() =>
            expect(view.onRepair).toHaveBeenCalledWith({
                schemaVersion: 1,
                issues: ["product_fidelity", "action"],
                instruction: "Mở nắp chậm hơn",
            }),
        );
        expect(view.onDraftChange).toHaveBeenLastCalledWith(
            expect.objectContaining({ instruction: "Mở nắp chậm hơn" }),
        );
    });
    it("keeps explicit advanced edits and supports undo", async () => {
        const view = setup();
        fireEvent.change(view.getByLabelText("Prompt tạo video"), {
            target: { value: "  Advanced motion\n" },
        });
        fireEvent.click(view.getByRole("button", { name: "Tạo lại cảnh 1" }));
        await waitFor(() =>
            expect(view.onRepair).toHaveBeenCalledWith({
                schemaVersion: 1,
                issues: ["alternate_take"],
                instruction: "",
                advancedEdits: { videoPrompt: "  Advanced motion\n" },
            }),
        );
        fireEvent.click(view.getByRole("button", { name: "Hoàn tác bản nháp" }));
        expect((view.getByLabelText("Prompt tạo video") as HTMLTextAreaElement).value).toBe(
            scene.videoPrompt,
        );
        expect(view.onDraftChange).toHaveBeenLastCalledWith({
            schemaVersion: 1,
            issues: [],
            instruction: "",
        });
    });
    it("restores only controlled drafts and never silently reads legacy localStorage", () => {
        localStorage.setItem(
            "viraldy:remake-draft:workspace:project:scene:initial",
            JSON.stringify({ ...scene, instruction: "Unsafe auto-restore" }),
        );
        const view = setup();
        expect(
            (
                view.getByLabelText(
                    "Bạn muốn thay đổi điều gì? (không bắt buộc)",
                ) as HTMLTextAreaElement
            ).value,
        ).toBe("");
        view.unmount();
        const draft: RepairIntent = {
            schemaVersion: 1,
            issues: ["presentation"],
            instruction: "Giữ nền",
            advancedEdits: { imagePrompt: "New image" },
        };
        const restored = setup({ draft, saveStatus: "Đã lưu trên thiết bị này" });
        expect(
            (
                restored.getByLabelText(
                    "Bạn muốn thay đổi điều gì? (không bắt buộc)",
                ) as HTMLTextAreaElement
            ).value,
        ).toBe("Giữ nền");
        expect((restored.getByLabelText("Prompt tạo ảnh") as HTMLTextAreaElement).value).toBe(
            "New image",
        );
        expect(restored.getByRole("status").textContent).toBe("Đã lưu trên thiết bị này");
    });
    it("exposes explicit legacy import and shows only supplied transaction save status", () => {
        const onImportLegacyDraft = vi.fn();
        const view = setup({
            legacyDraftAvailable: true,
            onImportLegacyDraft,
            saveStatus: "Chưa lưu được. Giữ trang này để tiếp tục.",
        });
        expect(onImportLegacyDraft).not.toHaveBeenCalled();
        fireEvent.click(view.getByRole("button", { name: "Khôi phục bản nháp cũ" }));
        expect(onImportLegacyDraft).toHaveBeenCalledTimes(1);
        expect(view.getByRole("status").textContent).toContain("Chưa lưu được");
        expect(view.queryByText("Đã lưu trên thiết bị này")).toBeNull();
    });
    it("blocks an overlong intent or explicit advanced prompt before confirmation", () => {
        const view = setup({
            draft: { schemaVersion: 1, issues: [], instruction: "x".repeat(4001) },
        });
        expect(view.getByRole("alert").textContent).toContain("4.000");
        fireEvent.submit(view.container.querySelector("form")!);
        expect(view.onRepair).not.toHaveBeenCalled();
        view.unmount();
        const advanced = setup({
            draft: {
                schemaVersion: 1,
                issues: [],
                instruction: "",
                advancedEdits: { prompt: "x".repeat(12001) },
            },
        });
        expect(advanced.getByRole("alert").textContent).toContain("12.000");
        expect(
            (advanced.getByRole("button", { name: "Tạo lại cảnh 1" }) as HTMLButtonElement)
                .disabled,
        ).toBe(true);
    });
    it("shows a rejected repair reason beside the instruction and allows a new plain-language request", async () => {
        const failureReason =
            "Yêu cầu đổi màu sản phẩm không khớp ảnh tham chiếu. Hãy giữ màu gốc.";
        const view = setup({ failureReason });
        expect(view.getByRole("alert").textContent).toContain(failureReason);
        expect(view.getByLabelText("Prompt tạo video").closest("details")?.open).toBe(false);
        fireEvent.change(view.getByLabelText("Bạn muốn thay đổi điều gì? (không bắt buộc)"), {
            target: { value: "Giữ màu gốc và mở nắp chậm hơn" },
        });
        expect(
            (view.getByRole("button", { name: "Tạo lại cảnh 1" }) as HTMLButtonElement).disabled,
        ).toBe(false);
        fireEvent.click(view.getByRole("button", { name: "Tạo lại cảnh 1" }));
        await waitFor(() =>
            expect(view.onRepair).toHaveBeenCalledWith({
                schemaVersion: 1,
                issues: ["alternate_take"],
                instruction: "Giữ màu gốc và mở nắp chậm hơn",
            }),
        );
    });
    it("shows the normalization step and disables all input while the action is busy", () => {
        const view = setup({ busy: true });
        expect(view.getByText(/AI sẽ kiểm tra yêu cầu/)).toBeTruthy();
        expect(
            (view.getByRole("button", { name: "Tạo lại cảnh 1" }) as HTMLButtonElement).disabled,
        ).toBe(true);
    });
});
