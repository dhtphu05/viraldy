// @vitest-environment jsdom
import { createElement, useState } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { RemakeActionConfirmation } from "./remake-action-confirmation";
import { confirmRemakeMediaRights, emptyRemakeRights } from "../lib/remake-intake";
import type { SmartRemakePreflight } from "@/shared/api/smart-remake";
import type { RemakeActionIntent } from "../lib/remake-action";

afterEach(cleanup);

const preflight: SmartRemakePreflight = {
    action: "analyze",
    contextHash: "price-and-context",
    mode: "live",
    scope: { targetDuration: 16, sceneCount: 0, groupCount: 0, imageCount: 0 },
    calls: { analysis: 3, image: 0, video: 0, inspection: 0, total: 3 },
    budget: {
        knownActualUsd: "0",
        reservedUsd: "0",
        exposureUsd: "0",
        additionalReservationUsd: "1.50",
        minimumCapUsd: "1.50",
        minimumMaxAttempts: 3,
        minimumDurationSeconds: 1800,
        recommended: { capUsd: "1.50", maxAttempts: 20, maxDurationSeconds: 1800 },
    },
    blockers: [],
};
const snapshot = () => ({
    requirements: {
        intent: "Theo cách quay của video mẫu",
        keep: [],
        replace: [],
        forbid: [],
        claims: [],
        requiresCharacter: false,
    },
    rights: emptyRemakeRights(),
    budget: { mode: "unlimited" as const },
});

describe("action confirmation details and recovery", () => {
    it("confirms one complete six-second provider clip with its two bookend images", () => {
        render(
            createElement(RemakeActionConfirmation, {
                ...props(),
                intent: {
                    action: "repair",
                    fingerprint: "repair-clip-2",
                    sceneId: "anchor",
                    baseVersionId: "base",
                    repairScope: "provider_group",
                    repairIntent: {
                        schemaVersion: 1,
                        issues: ["action"],
                        instruction: "Giữ hai tay tự nhiên",
                    },
                },
                sceneLabel: "Clip 2",
                preflight: {
                    ...preflight,
                    action: "repair",
                    scope: {
                        targetDuration: 6,
                        sceneCount: 12,
                        groupCount: 1,
                        imageCount: 2,
                        repairScope: "provider_group",
                        renderGroupId: "second",
                    },
                    calls: { analysis: 1, image: 2, video: 1, inspection: 0, total: 4 },
                },
            }),
        );
        expect(screen.getByRole("heading", { name: "Tạo lại clip 2?" })).toBeTruthy();
        expect(screen.getByText("Clip tạo lại 6 giây")).toBeTruthy();
        expect(screen.getByText(/hai ảnh đầu\/cuối.*1 lượt Wan/)).toBeTruthy();
        expect(screen.getByRole("button", { name: "Xác nhận và tạo lại clip 2" })).toBeTruthy();
        expect(screen.queryByText(/Xác nhận và tạo lại cảnh/)).toBeNull();
    });
    it("uses the logical scene and fragment label when confirming a repair", () => {
        render(
            createElement(RemakeActionConfirmation, {
                ...props(),
                intent: {
                    action: "repair",
                    fingerprint: "repair-fragment",
                    sceneId: "fragment-1",
                    baseVersionId: "base",
                    repairIntent: { schemaVersion: 1, issues: [], instruction: "" },
                },
                sceneNumber: 2,
                sceneLabel: "Cảnh 1 · đoạn 2/2",
                versionNumber: 1,
            }),
        );
        expect(screen.getByRole("heading", { name: "Tạo lại cảnh 1 · đoạn 2/2?" })).toBeTruthy();
        expect(screen.getByText("Cảnh 1 · đoạn 2/2 · Bản 1")).toBeTruthy();
        expect(screen.queryByRole("heading", { name: "Tạo lại cảnh 2?" })).toBeNull();
    });

    it("distinguishes full-source analysis from the chosen output duration", () => {
        render(
            createElement(RemakeActionConfirmation, {
                ...props(),
                preflight: {
                    ...preflight,
                    scope: {
                        ...preflight.scope,
                        targetDuration: 8,
                        analysisScope: "full_source",
                        sourceStartFrame: 0,
                        sourceEndFrame: 720,
                    },
                },
            }),
        );
        expect(screen.getByText("8 giây đầu ra · Video dọc 9:16")).toBeTruthy();
        expect(screen.getByText("Phân tích toàn bộ video mẫu · 0–30 giây")).toBeTruthy();
        expect(screen.getByText(/Tất cả cảnh.*kịch bản 8 giây/)).toBeTruthy();
        expect(screen.queryByText(/Kịch bản từ đoạn mẫu đã chọn/)).toBeNull();
    });

    it("uses source duration in the waiting view when output duration is different", () => {
        render(
            createElement(RemakeActionConfirmation, {
                ...props(),
                submitting: true,
                analysisPhase: "analyzing",
                preflight: {
                    ...preflight,
                    scope: {
                        ...preflight.scope,
                        targetDuration: 8,
                        analysisScope: "full_source",
                        sourceStartFrame: 0,
                        sourceEndFrame: 720,
                    },
                },
            }),
        );
        expect(screen.getByText(/30 giây tư liệu/)).toBeTruthy();
        expect(screen.queryByText(/8 giây tư liệu/)).toBeNull();
    });

    it.each([
        "SMART_REMAKE_TIMELINE_SCENE_LIMIT",
        "SMART_REMAKE_TIMELINE_CUTS_INVALID",
        "SMART_REMAKE_TIMELINE_SCENE_TOO_LONG",
        "SMART_REMAKE_SOURCE_ANALYSIS_INCOMPLETE",
        "SMART_REMAKE_SOURCE_ANALYSIS_UNSUPPORTED",
        "SMART_REMAKE_TIMELINE_DENSITY_UNSUPPORTED",
        "SMART_REMAKE_PROVIDER_PROMPT_TOO_LARGE",
        "SMART_REMAKE_PROVIDER_PLAN_UPDATE_REQUIRED",
    ])("returns to inputs instead of reconnecting for %s", (errorCode) => {
        const input = props();
        input.snapshot.rights = confirmRemakeMediaRights(emptyRemakeRights());
        render(
            createElement(RemakeActionConfirmation, {
                ...input,
                errorCode,
                error: "Kịch bản cần được cập nhật.",
            }),
        );
        expect(screen.getByText("Quay lại để cập nhật tư liệu hoặc kịch bản.")).toBeTruthy();
        expect(screen.queryByRole("button", { name: "Kết nối lại" })).toBeNull();
        const confirm = screen.getByRole("button", {
            name: "Xác nhận và tạo kịch bản",
        }) as HTMLButtonElement;
        expect(confirm.disabled).toBe(true);
        fireEvent.click(confirm);
        expect(input.onConfirm).not.toHaveBeenCalled();
        fireEvent.click(screen.getByRole("button", { name: "Quay lại" }));
        expect(input.onCancel).toHaveBeenCalledTimes(1);
    });

    it("does not offer reconnection for an input blocker returned by preflight", () => {
        render(
            createElement(RemakeActionConfirmation, {
                ...props(),
                preflight: {
                    ...preflight,
                    blockers: [
                        {
                            code: "SMART_REMAKE_TIMELINE_CUTS_INVALID",
                            message: "Mốc cắt chưa phủ đủ video mẫu.",
                            action: "new_project",
                        },
                    ],
                },
            }),
        );
        expect(screen.getByText("Quay lại để cập nhật tư liệu hoặc kịch bản.")).toBeTruthy();
        expect(screen.queryByRole("button", { name: "Kết nối lại" })).toBeNull();
    });

    it("keeps reconnection available for a service failure", () => {
        const input = props();
        render(
            createElement(RemakeActionConfirmation, {
                ...input,
                errorCode: "SMART_REMAKE_SERVICE_UNAVAILABLE",
                error: "Dịch vụ chưa phản hồi.",
            }),
        );
        fireEvent.click(screen.getByRole("button", { name: "Kết nối lại" }));
        expect(input.onRetry).toHaveBeenCalledTimes(1);
        expect(screen.queryByText("Quay lại để cập nhật tư liệu hoặc kịch bản.")).toBeNull();
    });

    it("allows a fresh confirmation after an input failure has been cleared", () => {
        const input = props();
        input.snapshot.rights = confirmRemakeMediaRights(emptyRemakeRights());
        const view = render(
            createElement(RemakeActionConfirmation, {
                ...input,
                errorCode: "SMART_REMAKE_TIMELINE_CUTS_INVALID",
                error: "Mốc cắt chưa hợp lệ.",
            }),
        );
        view.rerender(
            createElement(RemakeActionConfirmation, {
                ...input,
                errorCode: "SMART_REMAKE_TIMELINE_CUTS_INVALID",
                error: null,
            }),
        );
        expect(
            (screen.getByRole("button", { name: "Xác nhận và tạo kịch bản" }) as HTMLButtonElement)
                .disabled,
        ).toBe(false);
    });

    it("explains structured repair validation before image and video generation", () => {
        render(
            createElement(RemakeActionConfirmation, {
                ...props(),
                intent: {
                    action: "repair",
                    fingerprint: "intent",
                    sceneId: "scene",
                    baseVersionId: "base",
                    repairIntent: {
                        schemaVersion: 1,
                        issues: ["action"],
                        instruction: "Rót chậm hơn",
                    },
                },
            }),
        );
        expect(screen.getByText(/Một lượt AI kiểm tra yêu cầu sửa/).textContent).toMatch(
            /trước khi tạo ảnh và video/,
        );
    });
    it("does not render a closed intent", () => {
        render(createElement(RemakeActionConfirmation, { ...props(), intent: null }));
        expect(screen.queryByRole("dialog")).toBeNull();
    });

    it("makes a new project explicit when selected media or duration requires one", () => {
        render(
            createElement(RemakeActionConfirmation, {
                ...props(),
                intent: {
                    action: "analyze",
                    fingerprint: "different-duration",
                    startsNewProject: true,
                },
            }),
        );
        expect(screen.getByText(/Sẽ tạo dự án mới/).textContent).toMatch(
            /Dự án trước vẫn được giữ/,
        );
    });

    it("reuses complete legacy declarations without replacing their evidence", async () => {
        const input = props();
        input.snapshot.rights = {
            providerDisclosureAcknowledged: true,
            source: {
                basis: "owned",
                declared: true,
                scope: "Video quảng cáo sản phẩm",
                evidenceNote: "Video tự quay",
            },
            product: {
                basis: "licensed",
                declared: true,
                scope: "Ảnh dùng để giới thiệu sản phẩm",
                evidenceNote: "Giấy phép của nhà sản xuất",
            },
        };
        render(createElement(RemakeActionConfirmation, input));
        expect(screen.queryAllByRole("checkbox")).toHaveLength(0);
        fireEvent.click(screen.getByRole("button", { name: "Xác nhận và tạo kịch bản" }));
        await waitFor(() => expect(input.onConfirm).toHaveBeenCalledTimes(1));
        expect(input.onConfirm.mock.calls[0][0].rights).toEqual(input.snapshot.rights);
        expect(input.onConfirm.mock.calls[0][0].rights.attestation).toBeUndefined();
    });

    it.each(["revoked", "missing evidence", "provider not disclosed"])(
        "asks for confirmation when legacy rights are %s",
        (problem) => {
            const input = props();
            input.snapshot.rights = {
                providerDisclosureAcknowledged: problem !== "provider not disclosed",
                source: {
                    basis: "owned",
                    declared: true,
                    scope: "Quảng cáo",
                    evidenceNote: problem === "missing evidence" ? "" : "Tự quay",
                    revoked: problem === "revoked",
                },
                product: {
                    basis: "owned",
                    declared: true,
                    scope: "Quảng cáo",
                    evidenceNote: "Tự chụp",
                },
            };
            render(createElement(RemakeActionConfirmation, input));
            expect(screen.getAllByRole("checkbox")).toHaveLength(2);
            expect(
                (
                    screen.getByRole("button", {
                        name: "Xác nhận và tạo kịch bản",
                    }) as HTMLButtonElement
                ).disabled,
            ).toBe(true);
        },
    );

    it("requires separate character permission, scope and evidence before confirming", async () => {
        const input = props();
        input.snapshot.rights = confirmRemakeMediaRights(emptyRemakeRights());
        input.snapshot.requirements.requiresCharacter = true;
        render(createElement(RemakeActionConfirmation, { ...input, hasCharacter: true }));
        const confirm = screen.getByRole("button", {
            name: "Xác nhận và tạo kịch bản",
        }) as HTMLButtonElement;
        const consent = screen.getByRole("checkbox", { name: /sự đồng ý của nhân vật/ });
        expect((consent as HTMLInputElement).checked).toBe(false);
        expect(confirm.disabled).toBe(true);
        fireEvent.click(consent);
        fireEvent.change(screen.getByLabelText("Phạm vi sử dụng nhân vật"), {
            target: { value: "Quảng cáo chiếc bình tại Việt Nam" },
        });
        expect(confirm.disabled).toBe(true);
        fireEvent.change(screen.getByLabelText("Căn cứ quyền và sự đồng ý của nhân vật"), {
            target: { value: "Văn bản đồng ý của người mẫu" },
        });
        expect(confirm.disabled).toBe(false);
        fireEvent.click(confirm);
        await waitFor(() => expect(input.onConfirm).toHaveBeenCalledTimes(1));
        expect(input.onConfirm.mock.calls[0][0].rights).toMatchObject({
            character: {
                basis: "permission",
                declared: true,
                revoked: false,
                scope: "Quảng cáo chiếc bình tại Việt Nam",
                evidenceNote: "Văn bản đồng ý của người mẫu",
            },
            characterConsent: {
                consented: true,
                scope: "Quảng cáo chiếc bình tại Việt Nam",
                evidenceNote: "Văn bản đồng ý của người mẫu",
            },
        });
        expect(input.snapshot.rights.characterConsent).toBeUndefined();
    });

    it("retains a valid existing character consent and its declared basis", async () => {
        const input = props();
        input.snapshot.requirements.requiresCharacter = true;
        input.snapshot.rights = {
            ...confirmRemakeMediaRights(emptyRemakeRights()),
            character: {
                basis: "licensed",
                declared: true,
                scope: "Video sản phẩm",
                evidenceNote: "Hợp đồng người mẫu",
            },
            characterConsent: {
                consented: true,
                scope: "Video sản phẩm",
                evidenceNote: "Hợp đồng người mẫu",
            },
        };
        render(createElement(RemakeActionConfirmation, { ...input, hasCharacter: true }));
        expect(
            (screen.getByRole("checkbox", { name: /sự đồng ý của nhân vật/ }) as HTMLInputElement)
                .checked,
        ).toBe(true);
        fireEvent.click(screen.getByRole("button", { name: "Xác nhận và tạo kịch bản" }));
        await waitFor(() => expect(input.onConfirm).toHaveBeenCalledTimes(1));
        expect(input.onConfirm.mock.calls[0][0].rights.character.basis).toBe("licensed");
    });

    it("rejects using character requirements without an uploaded character", () => {
        const input = props();
        input.snapshot.rights = confirmRemakeMediaRights(emptyRemakeRights());
        input.snapshot.requirements.requiresCharacter = true;
        render(createElement(RemakeActionConfirmation, input));
        expect(screen.getByRole("alert").textContent).toMatch(/Thêm ảnh nhân vật/);
        expect(
            (screen.getByRole("button", { name: "Xác nhận và tạo kịch bản" }) as HTMLButtonElement)
                .disabled,
        ).toBe(true);
    });

    it("shows the selected source window and product before analysis", () => {
        const input = props();
        render(
            createElement(RemakeActionConfirmation, {
                ...input,
                productUrl: "blob:product-preview",
                preflight: {
                    ...preflight,
                    scope: { ...preflight.scope, sourceStartFrame: 48, sourceEndFrame: 432 },
                },
            }),
        );
        expect(screen.getByText("Đoạn mẫu 2–18 giây")).toBeTruthy();
        expect(screen.getByRole("img", { name: "Sản phẩm sẽ dùng" }).getAttribute("src")).toBe(
            "blob:product-preview",
        );
    });

    it("describes the repair clip duration and keeps other clips unchanged", () => {
        const intent: RemakeActionIntent = {
            action: "repair",
            fingerprint: "repair-scene-2",
            sceneId: "scene-2",
            baseVersionId: "version-1",
            draft: {
                prompt: "Giữ đúng màu sản phẩm",
                imagePrompt: "Giữ đúng màu sản phẩm",
                videoPrompt: "Giữ đúng màu sản phẩm",
            },
        };
        render(
            createElement(RemakeActionConfirmation, {
                ...props(),
                intent,
                sceneNumber: 2,
                preflight: {
                    ...preflight,
                    action: "repair",
                    scope: {
                        ...preflight.scope,
                        targetDuration: 8,
                        sceneId: "scene-2",
                        sceneCount: 1,
                        sourceStartFrame: 0,
                        sourceEndFrame: 48,
                    },
                },
            }),
        );
        expect(screen.getByRole("heading", { name: "Tạo lại cảnh 2?" })).toBeTruthy();
        expect(screen.getByText("Cảnh 2")).toBeTruthy();
        expect(screen.getByText("Clip tạo lại 8 giây")).toBeTruthy();
        expect(screen.getByText(/Chỉ clip đã chọn được tạo lại/)).toBeTruthy();
        expect(screen.getByText(/Các clip khác và bản đang dùng được giữ lại/)).toBeTruthy();
        expect(screen.queryByText(/Đoạn mẫu/)).toBeNull();
        expect(screen.getByRole("button", { name: "Xác nhận và tạo lại cảnh" })).toBeTruthy();
    });

    it.each(["product", "character"] as const)(
        "describes an image inspection for the selected %s image",
        (imageRole) => {
            render(
                createElement(RemakeActionConfirmation, {
                    ...props(),
                    intent: {
                        action: "inspect",
                        fingerprint: `inspect-${imageRole}`,
                        subject: { kind: "image", imageRole },
                    },
                    preflight: { ...preflight, action: "inspect" },
                }),
            );
            expect(
                screen.getByText(
                    imageRole === "product" ? "Ảnh sản phẩm đã chọn" : "Ảnh nhân vật đã chọn",
                ),
            ).toBeTruthy();
            expect(screen.queryByText(/Video dọc/)).toBeNull();
            expect(screen.getByRole("button", { name: "Xác nhận và kiểm tra" })).toBeTruthy();
        },
    );

    it.each([1, 2])("describes %i scene inspection window(s) for the chosen version", (checks) => {
        render(
            createElement(RemakeActionConfirmation, {
                ...props(),
                intent: {
                    action: "inspect",
                    fingerprint: "inspect-scene-1-version-1",
                    subject: { kind: "scene", sceneId: "scene-1", versionId: "version-1" },
                },
                sceneNumber: 1,
                versionNumber: 1,
                preflight: {
                    ...preflight,
                    action: "inspect",
                    scope: {
                        ...preflight.scope,
                        targetDuration: 8,
                        sceneCount: 1,
                        sceneId: "scene-1",
                    },
                    calls: { analysis: 0, image: 0, video: 0, inspection: checks, total: checks },
                },
            }),
        );
        expect(screen.getByText("Cảnh 1 · Bản 1")).toBeTruthy();
        expect(screen.getByText("Clip đã chọn và chuyển cảnh")).toBeTruthy();
        expect(
            screen.getByText(
                checks > 1 ? "2 lượt kiểm tra · Gồm cửa sổ giáp cảnh" : "1 lượt kiểm tra",
            ),
        ).toBeTruthy();
        expect(screen.queryByText("8 giây · Video dọc 9:16")).toBeNull();
        expect(screen.queryByText(/Chỉ clip đã chọn được tạo lại/)).toBeNull();
    });

    it("keeps the full video scope for an assembly inspection", () => {
        render(
            createElement(RemakeActionConfirmation, {
                ...props(),
                intent: {
                    action: "inspect",
                    fingerprint: "inspect-assembly",
                    subject: { kind: "assembly", assemblyId: "assembly-1" },
                },
                preflight: {
                    ...preflight,
                    action: "inspect",
                    scope: { ...preflight.scope, targetDuration: 8, sceneCount: 2 },
                    calls: { analysis: 0, image: 0, video: 0, inspection: 3, total: 3 },
                },
            }),
        );
        expect(screen.getByText("8 giây · Video dọc 9:16")).toBeTruthy();
        expect(screen.getByText("2 cảnh")).toBeTruthy();
        expect(screen.queryByText("Clip đã chọn và chuyển cảnh")).toBeNull();
    });

    it.each([
        ["reanalyze", "Xác nhận và cập nhật kịch bản"],
        ["render", "Xác nhận và tạo video"],
    ] as const)("names the %s action explicitly", (action, label) => {
        render(
            createElement(RemakeActionConfirmation, {
                ...props(),
                intent: { action, fingerprint: action },
                preflight: { ...preflight, action },
            }),
        );
        expect(screen.getByRole("button", { name: label })).toBeTruthy();
    });

    it("keeps confirmation unavailable while preflight loads then offers reconnection on failure", () => {
        const input = props();
        const { rerender } = render(
            createElement(RemakeActionConfirmation, { ...input, preflight: null, loading: true }),
        );
        expect(screen.getByRole("status").textContent).toMatch(/Đang kiểm tra/);
        expect(screen.queryByRole("button", { name: "Kết nối lại" })).toBeNull();
        expect(
            (screen.getByRole("button", { name: "Xác nhận và tạo kịch bản" }) as HTMLButtonElement)
                .disabled,
        ).toBe(true);
        rerender(
            createElement(RemakeActionConfirmation, {
                ...input,
                preflight: null,
                error: "Không thể đọc cấu hình dịch vụ.",
            }),
        );
        expect(screen.getByRole("alert").textContent).toBe("Không thể đọc cấu hình dịch vụ.");
        fireEvent.click(screen.getByRole("button", { name: "Kết nối lại" }));
        expect(input.onRetry).toHaveBeenCalledTimes(1);
        expect(input.onConfirm).not.toHaveBeenCalled();
    });

    it("does not turn a refreshed preflight into project limit controls", () => {
        const input = props();
        const { rerender } = render(createElement(RemakeActionConfirmation, input));
        const fresh: SmartRemakePreflight = {
            ...preflight,
            contextHash: "changed-plan",
            budget: {
                ...preflight.budget!,
                minimumCapUsd: "3.25",
                recommended: { capUsd: "3.25", maxAttempts: 24, maxDurationSeconds: 2100 },
            },
        };
        rerender(createElement(RemakeActionConfirmation, { ...input, preflight: fresh }));
        expect(screen.queryByLabelText("Trần ngân sách dự án (USD)")).toBeNull();
        expect(screen.queryByLabelText("Tối đa lượt xử lý AI")).toBeNull();
        expect(screen.queryByLabelText("Cửa sổ thực hiện (giây)")).toBeNull();
        expect(input.snapshot.budget).toEqual({ mode: "unlimited" });
        expect(input.onConfirm).not.toHaveBeenCalled();
    });

    it("can confirm media rights with no numeric preflight budget", async () => {
        const input = props();
        input.snapshot.rights = confirmRemakeMediaRights(emptyRemakeRights());
        const noGrant = { ...preflight, budget: null };
        render(createElement(RemakeActionConfirmation, { ...input, preflight: noGrant }));
        const confirm = screen.getByRole("button", {
            name: "Xác nhận và tạo kịch bản",
        }) as HTMLButtonElement;
        expect(confirm.disabled).toBe(false);
        fireEvent.click(confirm);
        await waitFor(() => expect(input.onConfirm).toHaveBeenCalledTimes(1));
        expect(input.onConfirm).toHaveBeenCalledWith(
            expect.objectContaining({ budget: { mode: "unlimited" } }),
            noGrant,
        );
    });

    it("labels fixture mode without displaying a budget grant or reservation form", () => {
        render(
            createElement(RemakeActionConfirmation, {
                ...props(),
                preflight: {
                    ...preflight,
                    mode: "fixture",
                    budget: {
                        ...preflight.budget!,
                        knownActualUsd: "0.12500",
                        reservedUsd: "0.70",
                    },
                },
            }),
        );
        expect(screen.queryByText("0.125 USD")).toBeNull();
        expect(screen.queryByText("0.7 USD")).toBeNull();
        expect(screen.queryByText(/Đang giữ chỗ, chưa rõ phí thực/)).toBeNull();
        expect(screen.getByText(/Không gọi AI trả phí/)).toBeTruthy();
    });

    it("keeps the modal open while submitting, then permits cancellation after a failed request", async () => {
        const input = props();
        input.snapshot.rights = confirmRemakeMediaRights(emptyRemakeRights());
        let fail: (error: Error) => void = () => undefined;
        input.onConfirm.mockImplementation(
            () =>
                new Promise((_resolve, reject) => {
                    fail = reject;
                }),
        );
        render(createElement(RemakeActionConfirmation, input));
        fireEvent.click(screen.getByRole("button", { name: "Xác nhận và tạo kịch bản" }));
        expect(screen.queryByRole("button", { name: "Quay lại" })).toBeNull();
        expect(screen.queryByRole("button", { name: "Close" })).toBeNull();
        fireEvent.keyDown(document, { key: "Escape", code: "Escape" });
        expect(input.onCancel).not.toHaveBeenCalled();
        expect(input.onConfirm).toHaveBeenCalledTimes(1);
        await act(async () => fail(new Error("connection interrupted")));
        expect(screen.getByRole("alert").textContent).toMatch(
            /kiểm tra trạng thái trước khi thử lại/,
        );
        fireEvent.click(screen.getByRole("button", { name: "Quay lại" }));
        expect(input.onCancel).toHaveBeenCalledTimes(1);
        expect(input.onConfirm).toHaveBeenCalledTimes(1);
    });

    it("guards dismissal while a parent action is submitting", () => {
        const input = props();
        render(createElement(RemakeActionConfirmation, { ...input, submitting: true }));
        fireEvent.keyDown(document, { key: "Escape", code: "Escape" });
        expect(input.onCancel).not.toHaveBeenCalled();
        expect(screen.queryByRole("button", { name: "Quay lại" })).toBeNull();
        expect(screen.queryByRole("button", { name: "Close" })).toBeNull();
        expect(input.onConfirm).not.toHaveBeenCalled();
    });
});

describe("analysis submission loading", () => {
    it("releases the confirmation dialog when inline analysis starts without cancelling", () => {
        const input = props();
        render(
            createElement(RemakeActionConfirmation, {
                ...input,
                submitting: true,
                analysisPhase: "analyzing",
                analysisInFlight: true,
            }),
        );
        expect(screen.queryByRole("dialog")).toBeNull();
        expect(input.onCancel).not.toHaveBeenCalled();
        expect(input.onConfirm).not.toHaveBeenCalled();
    });
    it("replaces the confirmation form immediately and submits the latest snapshot once", async () => {
        const input = props();
        let finish: () => void = () => undefined;
        input.onConfirm.mockImplementation(
            () =>
                new Promise<void>((resolve) => {
                    finish = resolve;
                }),
        );
        render(createElement(RemakeActionConfirmation, input));
        screen.getAllByRole("checkbox").forEach((checkbox) => fireEvent.click(checkbox));
        const confirm = screen.getByRole("button", { name: "Xác nhận và tạo kịch bản" });
        fireEvent.click(confirm);
        fireEvent.click(confirm);
        expect(screen.getByRole("heading", { name: "Đang chuẩn bị phân tích" })).toBeTruthy();
        expect(screen.queryByText("Trần ngân sách dự án")).toBeNull();
        expect(screen.queryAllByRole("checkbox")).toHaveLength(0);
        expect(screen.queryByRole("button", { name: "Xác nhận và tạo kịch bản" })).toBeNull();
        expect(input.onConfirm).toHaveBeenCalledTimes(1);
        expect(input.onConfirm).toHaveBeenCalledWith(
            expect.objectContaining({
                budget: { mode: "unlimited" },
                rights: expect.objectContaining({ providerDisclosureAcknowledged: true }),
            }),
            preflight,
        );
        await act(async () => finish());
    });

    it("keeps waiting as preparation becomes analysis and restores confirmation on changed preflight", () => {
        const input = props();
        const { rerender } = render(
            createElement(RemakeActionConfirmation, { ...input, submitting: true }),
        );
        expect(screen.getByRole("heading", { name: "Đang chuẩn bị phân tích" })).toBeTruthy();
        rerender(
            createElement(RemakeActionConfirmation, {
                ...input,
                submitting: true,
                analysisPhase: "analyzing",
                productUrl: "blob:selected-product",
            }),
        );
        expect(screen.getByRole("heading", { name: "Đang đọc video mẫu" })).toBeTruthy();
        expect(screen.getByText(/16 giây tư liệu/)).toBeTruthy();
        expect(screen.getByRole("img", { name: "Sản phẩm của bạn" }).getAttribute("src")).toBe(
            "blob:selected-product",
        );
        rerender(
            createElement(RemakeActionConfirmation, {
                ...input,
                error: "Phạm vi hoặc giới hạn dự phòng đã cập nhật. Kiểm tra và xác nhận lại.",
            }),
        );
        expect(
            screen.getByRole("heading", { name: "Tạo kịch bản cho sản phẩm này?" }),
        ).toBeTruthy();
        expect(screen.getByRole("alert").textContent).toMatch(/xác nhận lại/);
        expect(screen.getByRole("button", { name: "Xác nhận và tạo kịch bản" })).toBeTruthy();
        expect(input.onConfirm).not.toHaveBeenCalled();
    });

    it("uses the same waiting experience when updating a script", () => {
        render(
            createElement(RemakeActionConfirmation, {
                ...props(),
                intent: { action: "reanalyze", fingerprint: "update-script" },
                submitting: true,
                analysisPhase: "analyzing",
            }),
        );
        expect(screen.getByRole("heading", { name: "Đang cập nhật kịch bản" })).toBeTruthy();
        expect(screen.queryByText("Trần ngân sách dự án")).toBeNull();
    });

    it.each([
        { action: "render", fingerprint: "render" },
        {
            action: "repair",
            fingerprint: "repair",
            sceneId: "scene-1",
            baseVersionId: "version-1",
            repairIntent: { schemaVersion: 1, issues: [], instruction: "" },
        },
        {
            action: "inspect",
            fingerprint: "inspect",
            subject: { kind: "assembly", assemblyId: "assembly-1" },
        },
    ] satisfies RemakeActionIntent[])(
        "preserves existing pending $action confirmation",
        (intent) => {
            render(
                createElement(RemakeActionConfirmation, { ...props(), intent, submitting: true }),
            );
            expect(screen.queryByText("Trần ngân sách dự án")).toBeNull();
            expect(screen.queryByRole("heading", { name: "Đang chuẩn bị phân tích" })).toBeNull();
        },
    );
});

function props() {
    return {
        intent: { action: "analyze" as const, fingerprint: "selected-inputs" },
        preflight,
        snapshot: snapshot(),
        loading: false,
        submitting: false,
        error: null,
        onConfirm: vi.fn().mockResolvedValue("completed"),
        onCancel: vi.fn(),
        onRetry: vi.fn(),
    };
}

describe("action confirmation", () => {
    it("shows only the action and media rights without saving or submitting on open", () => {
        const input = props();
        render(createElement(RemakeActionConfirmation, input));
        expect(screen.getByRole("dialog")).toBeTruthy();
        expect(screen.getByText(/chưa tạo video/i)).toBeTruthy();
        expect(screen.queryByText("Trần ngân sách dự án")).toBeNull();
        expect(screen.queryByLabelText("Trần ngân sách dự án (USD)")).toBeNull();
        expect(screen.queryByText("Điều chỉnh giới hạn")).toBeNull();
        expect(input.snapshot.budget).toEqual({ mode: "unlimited" });
        expect(input.onConfirm).not.toHaveBeenCalled();
        expect(
            screen.getAllByRole("checkbox").every((node) => !(node as HTMLInputElement).checked),
        ).toBe(true);
        expect(
            screen.getByRole("link", { name: /Chính sách sử dụng tư liệu/ }).getAttribute("target"),
        ).toBe("_blank");
    });

    it("confirms the new media rights snapshot once without an extra save step", async () => {
        const input = props();
        let finish: () => void = () => undefined;
        input.onConfirm.mockImplementation(
            () =>
                new Promise<void>((resolve) => {
                    finish = resolve;
                }),
        );
        render(createElement(RemakeActionConfirmation, input));
        const confirm = screen.getByRole("button", {
            name: "Xác nhận và tạo kịch bản",
        }) as HTMLButtonElement;
        expect(confirm.disabled).toBe(true);
        screen.getAllByRole("checkbox").forEach((node) => fireEvent.click(node));
        expect(confirm.disabled).toBe(false);
        fireEvent.click(confirm);
        fireEvent.click(confirm);
        expect(input.onConfirm).toHaveBeenCalledTimes(1);
        expect(input.onConfirm).toHaveBeenCalledWith(
            expect.objectContaining({
                budget: { mode: "unlimited" },
                rights: expect.objectContaining({
                    providerDisclosureAcknowledged: true,
                    attestation: { policyVersion: "smart-remake-media-rights-v1", accepted: true },
                }),
            }),
            preflight,
        );
        finish();
        await waitFor(() => expect(input.onConfirm).toHaveBeenCalledTimes(1));
    });

    it("ignores historical numeric limits when confirming the current action", async () => {
        const input = props();
        input.snapshot.rights = confirmRemakeMediaRights(emptyRemakeRights());
        render(
            createElement(RemakeActionConfirmation, {
                ...input,
                snapshot: {
                    ...input.snapshot,
                    budget: { capUsd: "", maxAttempts: 0, maxDurationSeconds: 0 },
                },
            }),
        );
        const confirm = screen.getByRole("button", {
            name: "Xác nhận và tạo kịch bản",
        }) as HTMLButtonElement;
        expect(confirm.disabled).toBe(false);
        expect(screen.queryByRole("alert")).toBeNull();
        fireEvent.click(confirm);
        await waitFor(() => expect(input.onConfirm).toHaveBeenCalledTimes(1));
        expect(input.onConfirm.mock.calls[0][0].budget).toEqual({ mode: "unlimited" });
    });

    it("shows existing rights without asking for the same agreement again", () => {
        const input = props();
        input.snapshot.rights = confirmRemakeMediaRights(emptyRemakeRights());
        render(createElement(RemakeActionConfirmation, input));
        expect(screen.getByText(/Đã xác nhận quyền/)).toBeTruthy();
        expect(screen.queryAllByRole("checkbox")).toHaveLength(0);
        expect(
            (screen.getByRole("button", { name: "Xác nhận và tạo kịch bản" }) as HTMLButtonElement)
                .disabled,
        ).toBe(false);
    });

    it("cancel does not accept media rights or submit an action", () => {
        const input = props();
        render(createElement(RemakeActionConfirmation, input));
        fireEvent.click(screen.getAllByRole("checkbox")[0]);
        fireEvent.click(screen.getByRole("button", { name: "Quay lại" }));
        expect(input.onCancel).toHaveBeenCalledTimes(1);
        expect(input.onConfirm).not.toHaveBeenCalled();
        expect(input.snapshot.rights.attestation).toBeUndefined();
    });

    it("returns keyboard focus to the opener on Escape", async () => {
        function Fixture() {
            const [open, setOpen] = useState(false);
            return createElement(
                "div",
                null,
                createElement("button", { onClick: () => setOpen(true) }, "Tạo kịch bản"),
                createElement(RemakeActionConfirmation, {
                    ...props(),
                    intent: open ? props().intent : null,
                    onCancel: () => setOpen(false),
                }),
            );
        }
        render(createElement(Fixture));
        const opener = screen.getByRole("button", { name: "Tạo kịch bản" });
        opener.focus();
        fireEvent.click(opener);
        fireEvent.keyDown(document, { key: "Escape", code: "Escape" });
        await waitFor(() => expect(document.activeElement).toBe(opener));
    });

    it("blocks confirmation on server blockers and offers status refresh", () => {
        const input = props();
        input.preflight = {
            ...preflight,
            blockers: [
                {
                    code: "PENDING",
                    message: "Yêu cầu trước đang chờ kết quả.",
                    action: "reconcile",
                },
            ],
        };
        render(createElement(RemakeActionConfirmation, input));
        expect(screen.getByText("Yêu cầu trước đang chờ kết quả.")).toBeTruthy();
        expect(
            (screen.getByRole("button", { name: "Xác nhận và tạo kịch bản" }) as HTMLButtonElement)
                .disabled,
        ).toBe(true);
        fireEvent.click(screen.getByRole("button", { name: "Kiểm tra trạng thái" }));
        expect(input.onRetry).toHaveBeenCalledTimes(1);
    });
});
