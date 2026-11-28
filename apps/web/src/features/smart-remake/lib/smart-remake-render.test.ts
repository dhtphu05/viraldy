import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/shared/api/errors";

import {
    renderSmartRemake,
    type SmartRemakeCompileResult,
    type SmartRemakeHealth,
    type SmartRemakeRenderResult,
    type SmartRemakeProject,
} from "@/shared/api/smart-remake";
import {
    getRemakeProjectPollInterval,
    getRemakeProjectError,
    getRemakeErrorMessage,
    getRemakeGenerationSetupError,
    prepareRemakeRenderAttempt,
    prepareRemakeRenderRetry,
    hasRemakeRepairClip,
    renderSmartRemakeVideo,
} from "./smart-remake-render";

vi.mock("@/shared/api/smart-remake", () => ({ renderSmartRemake: vi.fn() }));

const compileResult: SmartRemakeCompileResult = {
    success: true,
    mode: "smart_remake",
    renderSubmitted: false,
    inputSummary: { targetDuration: 8, aspectRatio: "9:16", language: "vi" },
    referenceAnalysis: {},
    analyzeOutput: {},
    productLock: {},
    sceneMap: { targetDuration: 8, sceneCount: 0, scenes: [] },
    compiledPrompts: [],
    compilerDiagnostics: {},
    diagnostics: {},
    versions: {},
    warnings: [],
    expectationsVersion: 1,
    expectationsHash: "a".repeat(64),
    renderPlan: { fps: 24, provider: "kie", groupingPolicy: "fixed_provider_windows", units: [] },
};
const productImage = { name: "product.jpg", type: "image/jpeg" } as File;
const health: SmartRemakeHealth = {
    enabled: true,
    mode: "live",
    providers: ["unifically", "flowkit"],
    unificallyConfigured: true,
    flowkitUrlSet: false,
    limits: { referenceVideoBytes: 30_000_000, productImageBytes: 10_000_000 },
};

const apiResult: SmartRemakeRenderResult = {
    success: true,
    mode: "smart_remake",
    provider: "unifically",
    finalVideoUrl: "https://media.example/video.mp4",
    targetDuration: 8,
    sceneCount: 1,
    renderSubmitted: true,
    status: "completed",
    warnings: [],
};

describe("renderSmartRemakeVideo", () => {
    it.each([
        ["SMART_REMAKE_GROUP_REPAIR_STALE", /đoạn cắt.*thay đổi.*mở lại yêu cầu sửa clip/],
        ["SMART_REMAKE_GROUP_REPAIR_UNAVAILABLE", /Wan 12 giây.*hai clip 6 giây/],
        ["SMART_REMAKE_GROUP_REPAIR_ANCHOR_REQUIRED", /chọn lại Clip 1 hoặc Clip 2/],
    ])("explains clip repair recovery for %s", (code, expected) => {
        const message = getRemakeErrorMessage(
            new ApiError(code as string, "PRIVATE_OPERATION_PAYLOAD", 409),
        );
        expect(message).toMatch(expected as RegExp);
        expect(message).not.toContain("PRIVATE_OPERATION_PAYLOAD");
    });
    it("keeps provider setup instructions valid for a saved Wan plan", async () => {
        const message =
            "Timeline cần kết nối KIE để tạo các clip theo nhóm cảnh. Nhờ quản trị viên kiểm tra nhé.";
        expect(
            getRemakeErrorMessage(
                new ApiError("SMART_REMAKE_TIMELINE_PROVIDER_REQUIRED", "internal", 503),
            ),
        ).toBe(message);
        await expect(
            renderSmartRemakeVideo("workspace", {
                compileResult: {
                    ...compileResult,
                    schemaVersion: 2,
                    projectId: "saved",
                    revision: 1,
                    renderPlan: { ...compileResult.renderPlan!, videoModel: "wan/3-0-video" },
                },
                health,
            }),
        ).rejects.toThrow(message);
        expect(renderSmartRemake).not.toHaveBeenCalled();
    });
    it.each(["source_rhythm", "fit_target"] as const)(
        "requires an explicit update before submitting an old %s plan with extra video calls",
        async (timingMode) => {
            const old = {
                ...compileResult,
                schemaVersion: 2,
                projectId: "owned",
                revision: 1,
                inputSummary: { targetDuration: 16 },
                sourceSceneMap: { timingMode },
                renderPlan: {
                    groups: [{ id: "one" }, { id: "two" }, { id: "three" }, { id: "four" }],
                },
            } as SmartRemakeCompileResult;
            expect(getRemakeGenerationSetupError(old, health)).toContain("Cập nhật kịch bản");
            await expect(
                renderSmartRemakeVideo("workspace", {
                    compileResult: old,
                    health: { ...health, kieConfigured: true },
                }),
            ).rejects.toThrow("Cập nhật kịch bản");
            expect(renderSmartRemake).not.toHaveBeenCalled();
            expect(
                getRemakeGenerationSetupError(
                    {
                        ...old,
                        renderPlan: {
                            ...old.renderPlan!,
                            groupingPolicy: "fixed_provider_windows",
                            groups: old.renderPlan!.groups!.slice(0, 2),
                        },
                    },
                    health,
                ),
            ).toBeNull();
        },
    );
    afterEach(() => {
        vi.unstubAllGlobals();
        vi.resetAllMocks();
    });

    it("returns a labeled sample only when demo mode is explicitly requested", async () => {
        vi.stubGlobal(
            "fetch",
            vi
                .fn()
                .mockResolvedValue(
                    new Response(null, { headers: { "Content-Type": "video/mp4" } }),
                ),
        );

        await expect(
            renderSmartRemakeVideo("ws-1", { compileResult, health, demo: true }),
        ).resolves.toEqual({
            finalVideoUrl: "/smart-remake/02_After.mp4",
            status: "completed",
            isDemo: true,
        });
        expect(renderSmartRemake).not.toHaveBeenCalled();
    });

    it.each([404, 200])(
        "rejects a missing sample instead of submitting a paid render (HTML %s)",
        async (status) => {
            vi.stubGlobal(
                "fetch",
                vi
                    .fn()
                    .mockResolvedValue(
                        new Response(null, { status, headers: { "Content-Type": "text/html" } }),
                    ),
            );

            await expect(
                renderSmartRemakeVideo("ws-1", { compileResult, productImage, health, demo: true }),
            ).rejects.toThrow("Video mẫu");
            expect(renderSmartRemake).not.toHaveBeenCalled();
        },
    );

    it("uses the live API even when the optional local demo video exists", async () => {
        const fetch = vi
            .fn()
            .mockResolvedValue(new Response(null, { headers: { "Content-Type": "video/mp4" } }));
        vi.stubGlobal("fetch", fetch);
        vi.mocked(renderSmartRemake).mockResolvedValue(apiResult);

        await expect(
            renderSmartRemakeVideo("ws-1", { compileResult, productImage, health }),
        ).resolves.toEqual(apiResult);
        expect(fetch).not.toHaveBeenCalled();
        expect(renderSmartRemake).toHaveBeenCalledWith("ws-1", {
            compileResult,
            productImage,
            provider: "unifically",
            projectName: "Smart Remake",
        });
    });

    it("uses FlowKit and preserves submitted status without inventing output", async () => {
        const submitted = {
            ...apiResult,
            provider: "flowkit",
            finalVideoUrl: "",
            status: "submitted" as const,
        };
        vi.mocked(renderSmartRemake).mockResolvedValue(submitted);

        await expect(
            renderSmartRemakeVideo("ws-1", {
                compileResult,
                productImage,
                health: { ...health, unificallyConfigured: false, flowkitUrlSet: true },
            }),
        ).resolves.toEqual(submitted);
        expect(renderSmartRemake).toHaveBeenCalledWith(
            "ws-1",
            expect.objectContaining({ provider: "flowkit" }),
        );
    });

    it("prefers configured KIE and keeps its saved pending project for recovery", async () => {
        const pending: SmartRemakeRenderResult = {
            ...apiResult,
            provider: "kie",
            status: "submitted",
            finalVideoUrl: "",
            repairProject: {
                id: "kie-project",
                revision: 0,
                status: "incomplete",
                finalVideoUrl: "",
                targetDuration: 8,
                provider: "kie",
                pendingOperation: {
                    id: "kie-operation",
                    status: "running",
                    needsReconciliation: false,
                },
                scenes: [],
            },
        };
        vi.mocked(renderSmartRemake).mockResolvedValue(pending);

        await expect(
            renderSmartRemakeVideo("ws-1", {
                compileResult,
                productImage,
                health: { ...health, kieConfigured: true, flowkitUrlSet: true },
                idempotencyKey: "render-attempt-1",
            }),
        ).resolves.toEqual(pending);
        expect(renderSmartRemake).toHaveBeenCalledExactlyOnceWith("ws-1", {
            compileResult,
            productImage,
            provider: "kie",
            projectName: "Smart Remake",
            idempotencyKey: "render-attempt-1",
        });
    });

    it("does not switch paid providers when KIE fails", async () => {
        vi.mocked(renderSmartRemake).mockRejectedValue(new Error("KIE chưa phản hồi"));
        await expect(
            renderSmartRemakeVideo("ws-1", {
                compileResult,
                productImage,
                health: { ...health, kieConfigured: true, flowkitUrlSet: true },
                idempotencyKey: "same-attempt",
            }),
        ).rejects.toThrow("KIE chưa phản hồi");
        expect(renderSmartRemake).toHaveBeenCalledExactlyOnceWith(
            "ws-1",
            expect.objectContaining({ provider: "kie", idempotencyKey: "same-attempt" }),
        );
    });

    it("uses the fixture backend and retains its honest no-output response", async () => {
        const fixture = {
            ...apiResult,
            provider: "fixture",
            finalVideoUrl: "",
            renderSubmitted: false,
            status: "submitted" as const,
            warnings: ["Fixture renderer is not configured with an output video."],
        };
        vi.mocked(renderSmartRemake).mockResolvedValue(fixture);

        await expect(
            renderSmartRemakeVideo("ws-1", {
                compileResult,
                health: { ...health, mode: "fixture", kieConfigured: true },
            }),
        ).resolves.toEqual(fixture);
        expect(renderSmartRemake).toHaveBeenCalledWith(
            "ws-1",
            expect.objectContaining({ provider: "fixture" }),
        );
    });

    it("retains the persisted scene project and backend warnings", async () => {
        const repairProject = {
            id: "repair-1",
            revision: 1,
            status: "ready" as const,
            finalVideoUrl: apiResult.finalVideoUrl,
            targetDuration: 8 as const,
            provider: "unifically" as const,
            scenes: [],
        };
        const result = { ...apiResult, repairProject, warnings: ["Review the generated scene."] };
        vi.mocked(renderSmartRemake).mockResolvedValue(result);

        await expect(
            renderSmartRemakeVideo("ws-1", { compileResult, productImage, health }),
        ).resolves.toEqual(result);
    });

    it("passes a product link to the backend without requiring another image upload", async () => {
        vi.mocked(renderSmartRemake).mockResolvedValue(apiResult);
        const productUrl = "https://shop.example/product";

        await expect(
            renderSmartRemakeVideo("ws-1", { compileResult, productUrl, health }),
        ).resolves.toEqual(apiResult);
        expect(renderSmartRemake).toHaveBeenCalledWith("ws-1", {
            compileResult,
            productUrl,
            provider: "unifically",
            projectName: "Smart Remake",
        });
    });

    it.each([undefined, { ...health, enabled: false }, { ...health, unificallyConfigured: false }])(
        "explains when a rendering service is unavailable",
        async (health) => {
            await expect(
                renderSmartRemakeVideo("ws-1", { compileResult, productImage, health }),
            ).rejects.toThrow("dịch vụ tạo video");
            expect(renderSmartRemake).not.toHaveBeenCalled();
        },
    );

    it.each([undefined, "", "  "])(
        "requires a product source for live rendering (%s)",
        async (productUrl) => {
            await expect(
                renderSmartRemakeVideo("ws-1", { compileResult, productUrl, health }),
            ).rejects.toThrow("ảnh hoặc liên kết sản phẩm");
            expect(renderSmartRemake).not.toHaveBeenCalled();
        },
    );

    it("propagates real rendering failures instead of substituting demo output", async () => {
        vi.mocked(renderSmartRemake).mockRejectedValue(new Error("Provider failed"));
        await expect(
            renderSmartRemakeVideo("ws-1", { compileResult, productImage, health }),
        ).rejects.toThrow("Provider failed");
    });
});

describe("saved KIE project polling", () => {
    const pending: NonNullable<SmartRemakeRenderResult["repairProject"]> = {
        id: "project",
        revision: 0,
        status: "incomplete",
        finalVideoUrl: "",
        provider: "kie",
        targetDuration: 8,
        scenes: [],
        pendingOperation: { id: "operation", status: "running", needsReconciliation: false },
    };

    it("checks a running KIE project every five seconds", () => {
        expect(getRemakeProjectPollInterval(pending)).toBe(5000);
    });
    it.each(["pending", "processing"] as const)(
        "keeps reading a %s preview after rendering has finished",
        (status) => {
            const value = {
                ...pending,
                pendingOperation: undefined,
                preview: { schemaVersion: 1 as const, status },
            };
            expect(getRemakeProjectPollInterval(value)).toBe(5000);
            expect(
                getRemakeProjectPollInterval({
                    ...value,
                    lastOperation: {
                        id: "uncertain",
                        status: "failed",
                        needsReconciliation: true,
                    },
                }),
            ).toBe(false);
        },
    );
    it.each(["ready", "failed", "stale"] as const)(
        "stops reading a terminal %s preview",
        (status) => {
            expect(
                getRemakeProjectPollInterval({
                    ...pending,
                    pendingOperation: undefined,
                    preview: { schemaVersion: 1, status },
                }),
            ).toBe(false);
        },
    );

    it("stops when complete, missing, or waiting for manual reconciliation", () => {
        expect(getRemakeProjectPollInterval(null)).toBe(false);
        expect(getRemakeProjectPollInterval({ ...pending, pendingOperation: undefined })).toBe(
            false,
        );
        expect(
            getRemakeProjectPollInterval({
                ...pending,
                pendingOperation: { ...pending.pendingOperation!, needsReconciliation: true },
            }),
        ).toBe(false);
    });

    it("keeps existing providers on their explicit refresh path", () => {
        expect(getRemakeProjectPollInterval({ ...pending, provider: "flowkit" })).toBe(false);
        expect(getRemakeProjectPollInterval({ ...pending, provider: "unifically" })).toBe(false);
    });

    it("polls persisted project inspections independently of video provider", () => {
        expect(
            getRemakeProjectPollInterval({ ...pending, provider: "unifically", phase: "compiled" }),
        ).toBe(5000);
        expect(
            getRemakeProjectPollInterval({
                ...pending,
                provider: "flowkit",
                pendingOperation: { ...pending.pendingOperation!, kind: "inspection" },
            }),
        ).toBe(5000);
    });

    it("stops on terminal failure and exposes the latest actionable reason", () => {
        const failed = {
            ...pending,
            pendingOperation: undefined,
            lastOperation: {
                id: "operation",
                status: "failed" as const,
                errorCode: "KIE_CREDITS_EXHAUSTED",
            },
        };
        expect(getRemakeProjectPollInterval(failed)).toBe(false);
        expect(getRemakeProjectError(failed)).toContain("hết lượt sử dụng");
    });

    it("clears the prior failure when a newer operation runs or completes", () => {
        const failed = {
            id: "old-operation",
            status: "failed" as const,
            errorCode: "KIE_AUTH_FAILED",
        };
        expect(getRemakeProjectError({ ...pending, lastOperation: failed })).toBeNull();
        expect(
            getRemakeProjectError({
                ...pending,
                pendingOperation: undefined,
                lastOperation: { id: "new-operation", status: "completed" },
            }),
        ).toBeNull();
        expect(getRemakeProjectError(null)).toBeNull();
    });

    it("uses a safe fallback when no failure code is available", () => {
        const message = getRemakeProjectError({
            ...pending,
            pendingOperation: undefined,
            lastOperation: { id: "operation", status: "failed", errorCode: null },
        });
        expect(message).toContain("Chưa hoàn tất yêu cầu");
        expect(message).not.toContain("KIE");
    });

    it("explains the saved KIE failure after a project reload using the retained provider reason", () => {
        expect(
            getRemakeProjectError({
                ...pending,
                pendingOperation: undefined,
                lastOperation: {
                    id: "operation",
                    status: "failed",
                    errorCode: "KIE_TASK_FAILED",
                    providerTaskId: "kie-saved-task",
                    providerError: { providerCode: "500", providerMessage: "Internal Error" },
                },
            }),
        ).toContain("Lỗi từ nhà cung cấp kie.ai");
    });
});

describe("KIE render attempt identity", () => {
    it("reuses a key when the same compile and product are retried", () => {
        const first = prepareRemakeRenderAttempt(null, { compileResult, productImage });
        const retry = prepareRemakeRenderAttempt(first, {
            compileResult: JSON.parse(JSON.stringify(compileResult)),
            productImage,
        });
        expect(retry).toBe(first);
        expect(retry.idempotencyKey).toMatch(/^[\da-f-]{36}$/);
    });

    it("assigns a new identity when a prompt, product image, or product link changes", () => {
        const first = prepareRemakeRenderAttempt(null, { compileResult, productImage });
        const edited = {
            ...compileResult,
            sceneMap: { ...compileResult.sceneMap, scenes: [{ videoPrompt: "new motion" }] },
        };
        const nextPrompt = prepareRemakeRenderAttempt(first, {
            compileResult: edited,
            productImage,
        });
        const nextImage = prepareRemakeRenderAttempt(first, {
            compileResult,
            productImage: { ...productImage } as File,
        });
        const nextLink = prepareRemakeRenderAttempt(first, {
            compileResult,
            productUrl: "https://shop.example/new-product",
        });
        expect(nextPrompt.idempotencyKey).not.toBe(first.idempotencyKey);
        expect(nextImage.idempotencyKey).not.toBe(first.idempotencyKey);
        expect(nextLink.idempotencyKey).not.toBe(first.idempotencyKey);
    });

    it("starts a fresh logical request after the acknowledged attempt is cleared", () => {
        const first = prepareRemakeRenderAttempt(null, { compileResult, productImage });
        const acknowledged = prepareRemakeRenderAttempt(null, { compileResult, productImage });
        expect(acknowledged.idempotencyKey).not.toBe(first.idempotencyKey);
    });
});

describe("confirmed initial generation retry", () => {
    const input = { compileResult, productImage };
    it("reuses a transport-unknown key and does not silently change its payload", () => {
        const first = prepareRemakeRenderAttempt(null, input);
        expect(prepareRemakeRenderRetry(first, input)).toBe(first);
        expect(() =>
            prepareRemakeRenderRetry(first, {
                ...input,
                compileResult: { ...compileResult, revision: 2 },
            }),
        ).toThrow("Chưa xác định");
    });
    it("starts a fresh explicit intent only for the exact failed request confirmed by the server", () => {
        const first = prepareRemakeRenderAttempt(null, input);
        const recovery = {
            kind: "retry_initial_render" as const,
            stage: "image" as const,
            errorCode: "OPENAI_IMAGE_CREDITS_EXHAUSTED",
            requestKey: first.idempotencyKey,
        };
        expect(
            prepareRemakeRenderRetry(first, input, { ...recovery, requestKey: "another-request" }),
        ).toBe(first);
        const retry = prepareRemakeRenderRetry(
            first,
            { ...input, compileResult: { ...compileResult, revision: 2 } },
            recovery,
        );
        expect(retry.idempotencyKey).not.toBe(first.idempotencyKey);
        expect(retry.compileSnapshot).toContain('"revision":2');
    });
    it("creates the first request without a failed request key", () => {
        expect(prepareRemakeRenderRetry(null, input).idempotencyKey).toMatch(/^[\da-f-]{36}$/);
    });
});

describe("OpenAI image failure reasons", () => {
    it.each([
        undefined,
        "insufficient_quota",
        "billing_hard_limit_reached",
        "project_spend_limit_exceeded",
        "organization_spend_limit_exceeded",
        "organization_usage_limit_exceeded",
    ])("does not diagnose an exhausted wallet from quota reason %s", (providerErrorCode) => {
        const message = getRemakeErrorMessage(
            new ApiError("OPENAI_IMAGE_CREDITS_EXHAUSTED", "", 429, { providerErrorCode }),
        );
        expect(message).toMatch(/chi tiêu|quota/);
        expect(message).not.toMatch(/nạp|không đủ credit|hết (credit|số dư)/i);
    });
    it("suggests adding credit only when the provider confirms an exhausted credit balance", () => {
        expect(
            getRemakeErrorMessage(
                new ApiError("OPENAI_IMAGE_CREDITS_EXHAUSTED", "", 429, {
                    providerErrorCode: "credit_balance_exhausted",
                }),
            ),
        ).toContain("Nạp thêm credit");
    });
    it("distinguishes account credit limits from a known request-rate limit", () => {
        expect(
            getRemakeErrorMessage(new ApiError("OPENAI_IMAGE_CREDITS_EXHAUSTED", "", 429)),
        ).toMatch(/credit|hạn mức/);
        expect(
            getRemakeErrorMessage(
                new ApiError("OPENAI_IMAGE_RATE_LIMITED", "", 429, {
                    providerErrorCode: "rate_limit_exceeded",
                }),
            ),
        ).toContain("tần suất");
    });
    it("keeps a body-less legacy 429 ambiguous instead of claiming the service is busy", () => {
        const message = getRemakeErrorMessage(new ApiError("OPENAI_IMAGE_RATE_LIMITED", "", 429));
        expect(message).toBe(
            "OpenAI từ chối tạo ảnh (429). Kiểm tra credit/hạn mức trước khi thử lại.",
        );
        expect(message).not.toContain("đang bận");
    });
    it("maps a missing clip to continuing initial generation", () => {
        expect(
            getRemakeErrorMessage(new ApiError("SMART_REMAKE_BASE_VERSION_REQUIRED", "", 409)),
        ).toBe("Cảnh này chưa có clip để sửa. Tiếp tục tạo video trước.");
    });
    it.each([undefined, "rate_limit_exceeded", "slow_down"])(
        "retains the actual provider rate reason %s when reading a failed project",
        (providerErrorCode) => {
            const failed = {
                lastOperation: {
                    id: "failed",
                    status: "failed",
                    errorCode: "OPENAI_IMAGE_RATE_LIMITED",
                },
                generationRecovery: {
                    kind: "retry_initial_render",
                    stage: "image",
                    errorCode: "OPENAI_IMAGE_RATE_LIMITED",
                    requestKey: "known-failed",
                    providerErrorCode,
                    httpStatus: 429,
                },
            } as SmartRemakeProject;
            expect(getRemakeProjectError(failed)).toContain(
                providerErrorCode ? "tần suất" : "credit/hạn mức",
            );
        },
    );
});

describe("repair base clip availability", () => {
    const scene = {
        activeVersionId: "active",
        versions: [{ id: "active", videoUrl: "/clip.mp4" }],
    } as SmartRemakeProject["scenes"][number];
    it("requires the selected active version to contain a playable clip", () => {
        expect(hasRemakeRepairClip(undefined)).toBe(false);
        expect(hasRemakeRepairClip({ ...scene, activeVersionId: null })).toBe(false);
        expect(hasRemakeRepairClip({ ...scene, activeVersionId: "missing" })).toBe(false);
        expect(
            hasRemakeRepairClip({ ...scene, versions: [{ ...scene.versions[0], videoUrl: "  " }] }),
        ).toBe(false);
        expect(hasRemakeRepairClip(scene)).toBe(true);
    });
});

describe("seller-facing KIE errors", () => {
    it.each([
        ["KIE_NOT_CONFIGURED", "Dịch vụ tạo video chưa sẵn sàng"],
        ["KIE_AUTH_FAILED", "Dịch vụ tạo video chưa sẵn sàng"],
        ["KIE_CREDITS_EXHAUSTED", "hết lượt sử dụng"],
        ["KIE_RATE_LIMITED", "đang bận"],
        ["KIE_SUBMISSION_UNCERTAIN", "tránh gửi trùng"],
        ["KIE_POLL_TIMEOUT", "tránh gửi trùng"],
        ["KIE_TASK_FAILED", "Chưa tạo được video"],
        ["KIE_UPLOAD_FAILED", "tải ảnh tham chiếu"],
        ["KIE_VALIDATION_FAILED", "prompt từng cảnh"],
        ["KIE_OUTPUT_DOWNLOAD_FAILED", "chưa tải về được"],
        ["KIE_INVALID_RESPONSE", "kiểm tra lại dự án"],
        ["KIE_UNAVAILABLE", "kiểm tra lại dự án"],
        ["SMART_REMAKE_OPERATION_UNRESOLVED", "Kiểm tra lại"],
    ])("explains %s without displaying provider details", (code, phrase) => {
        const message = getRemakeErrorMessage(
            new ApiError(code, "PRIVATE_PROVIDER_MESSAGE", 503, {
                token: "fake-token",
            }),
        );
        expect(message).toContain(phrase);
        if (code.startsWith("KIE_")) expect(message).toMatch(/kie/i);
        expect(message).not.toContain("PRIVATE_");
        expect(message).not.toContain("fake-token");
    });

    it.each([
        ["The input content was flagged for containing a prominent public figure.", "bộ lọc"],
        ["Internal Error, Please try again later.", "lỗi nội bộ"],
        ["Server exception, please try again later or contact customer service", "lỗi nội bộ"],
    ])(
        "explains the retained KIE reason without inventing a cause: %s",
        (providerMessage, phrase) => {
            const failed = getRemakeErrorMessage(
                new ApiError("KIE_TASK_FAILED", "PRIVATE_MESSAGE", 503, {
                    providerError: { providerMessage },
                }),
            );
            expect(failed).toContain("Lỗi từ nhà cung cấp kie.ai");
            expect(failed).toContain(phrase);
            expect(failed).not.toMatch(/hoàn tiền|không tính phí|prompt quá dài|PRIVATE_MESSAGE/);
        },
    );

    it("does not turn a generic KIE 500 into a public-figure or prompt-length diagnosis", () => {
        const message = getRemakeErrorMessage(
            new ApiError("KIE_TASK_FAILED", "private", 503, {
                providerError: { providerCode: 500 },
            }),
        );
        expect(message).toContain("Lỗi từ nhà cung cấp kie.ai");
        expect(message).not.toMatch(/nhân vật công chúng|prompt quá dài/);
    });

    it("preserves actionable local validation messages", () => {
        expect(getRemakeErrorMessage(new Error("Thêm ảnh sản phẩm nhé."))).toBe(
            "Thêm ảnh sản phẩm nhé.",
        );
        expect(getRemakeErrorMessage(null)).toContain("thử lại");
    });
});

describe("saved timeline generation", () => {
    afterEach(() => vi.resetAllMocks());

    it("requires KIE for v2 without falling back to a different paid provider", async () => {
        const timeline = {
            ...compileResult,
            schemaVersion: 2 as const,
            projectId: "saved",
            revision: 2,
        };
        await expect(
            renderSmartRemakeVideo("ws", { compileResult: timeline, health }),
        ).rejects.toThrow("KIE");
        expect(renderSmartRemake).not.toHaveBeenCalled();
    });

    it("uses the persisted project and revision without reuploading product media", async () => {
        const timeline = {
            ...compileResult,
            schemaVersion: 2 as const,
            projectId: "saved",
            revision: 2,
        };
        vi.mocked(renderSmartRemake).mockResolvedValue(apiResult);
        await renderSmartRemakeVideo("ws", {
            compileResult: timeline,
            health: { ...health, kieConfigured: true },
            idempotencyKey: "stable",
        });
        expect(renderSmartRemake).toHaveBeenCalledExactlyOnceWith(
            "ws",
            expect.objectContaining({
                projectId: "saved",
                expectedRevision: 2,
                provider: "kie",
                idempotencyKey: "stable",
            }),
        );
    });

    it("rejects an incomplete saved-plan identity before calling the backend", async () => {
        await expect(
            renderSmartRemakeVideo("ws", {
                compileResult: { ...compileResult, schemaVersion: 2 },
                health: { ...health, kieConfigured: true },
            }),
        ).rejects.toThrow("kịch bản");
        expect(renderSmartRemake).not.toHaveBeenCalled();
    });

    it("exposes actionable timeline conflicts without overwriting another tab", () => {
        expect(
            getRemakeErrorMessage(new ApiError("SMART_REMAKE_REVISION_CONFLICT", "private", 409)),
        ).toContain("tab");
        expect(
            getRemakeErrorMessage(new ApiError("SMART_REMAKE_COMPOSE_FAILED", "private", 503)),
        ).toContain("ghép");
    });
});

describe("seller-facing timeline errors", () => {
    it.each([
        ["SMART_REMAKE_RETENTION_UNAVAILABLE", "Kho lưu video"],
        ["SMART_REMAKE_FIXTURE_MODE", "kiểm thử"],
        ["SMART_REMAKE_SOURCE_RANGE_INVALID", "độ dài"],
        ["SMART_REMAKE_SOURCE_REUPLOAD_REQUIRED", "Thêm lại"],
        ["SMART_REMAKE_SOURCE_ANALYSIS_INCOMPLETE", "phân tích lại"],
        ["SMART_REMAKE_EXPECTATIONS_REQUIRED", "Cập nhật kịch bản"],
        ["SMART_REMAKE_ASSEMBLY_EXPECTATIONS_REQUIRED", "Ghép lại"],
        ["SMART_REMAKE_PRODUCT_ANALYSIS_INCOMPLETE", "ảnh sản phẩm"],
        ["SMART_REMAKE_SOURCE_UNSUPPORTED", "video mẫu"],
        ["COMPILER_OUTPUT_INVALID", "yêu cầu cảnh"],
        ["SMART_REMAKE_SOURCE_INVALID", "video mẫu"],
        ["SMART_REMAKE_TIMELINE_SCENE_TOO_LONG", "mốc cắt"],
        ["SMART_REMAKE_TIMELINE_SCENE_LIMIT", "toàn bộ video"],
        ["SMART_REMAKE_TIMELINE_DENSITY_UNSUPPORTED", "khung hình"],
        ["SMART_REMAKE_OUTPUT_DENSITY_UNSUPPORTED", "khung hình"],
        ["SMART_REMAKE_PROVIDER_PROMPT_TOO_LARGE", "yêu cầu bổ sung"],
        ["SMART_REMAKE_PROVIDER_PLAN_UPDATE_REQUIRED", "Cập nhật kịch bản"],
        ["SMART_REMAKE_TIMELINE_CUTS_INVALID", "tăng dần"],
        ["SMART_REMAKE_TIMELINE_PROVIDER_REQUIRED", "KIE"],
        ["SMART_REMAKE_TIMELINE_UNREVIEWED", "duyệt"],
        ["SMART_REMAKE_TIMELINE_SAVE_FAILED", "Lựa chọn"],
        ["SMART_REMAKE_RENDER_ALREADY_STARTED", "Xem & ghép"],
        ["SMART_REMAKE_MEDIA_CHANGED", "clip"],
        ["SMART_REMAKE_ASSEMBLY_CHECK_FAILED", "ghép lại"],
        ["SMART_REMAKE_FUTURE_CODE", "Kiểm tra"],
    ])("localizes %s without exposing backend details", (code, expected) => {
        const message = getRemakeErrorMessage(new ApiError(code, "INTERNAL_STORAGE_ERROR", 503));
        expect(message).toContain(expected);
        expect(message).not.toContain("INTERNAL_");
    });
});

describe("generation expectations compatibility", () => {
    it("requires an updated saved plan without submitting old generation directions", async () => {
        vi.resetAllMocks();
        const oldPlan = {
            ...compileResult,
            schemaVersion: 2 as const,
            projectId: "saved",
            revision: 2,
            expectationsVersion: undefined,
            expectationsHash: undefined,
        };
        expect(getRemakeGenerationSetupError(oldPlan, health)).toContain("Cập nhật kịch bản");
        await expect(
            renderSmartRemakeVideo("ws", {
                compileResult: oldPlan,
                health: { ...health, kieConfigured: true },
            }),
        ).rejects.toThrow("Cập nhật kịch bản");
        expect(renderSmartRemake).not.toHaveBeenCalled();
    });
    it("accepts the current contract and rejects malformed binding metadata", () => {
        const current = { ...compileResult, schemaVersion: 2 as const };
        expect(getRemakeGenerationSetupError(current, health)).toBeNull();
        expect(
            getRemakeGenerationSetupError({ ...current, expectationsHash: "short" }, health),
        ).toContain("Cập nhật kịch bản");
    });
});

describe("timeline fixture safety", () => {
    afterEach(() => vi.resetAllMocks());
    it("explains test mode before any render API request", async () => {
        await expect(
            renderSmartRemakeVideo("ws", {
                compileResult: {
                    ...compileResult,
                    schemaVersion: 2,
                    projectId: "draft",
                    revision: 1,
                },
                health: { ...health, mode: "fixture", kieConfigured: true },
            }),
        ).rejects.toThrow("Đang ở chế độ kiểm thử nên chưa tạo clip AI");
        expect(renderSmartRemake).not.toHaveBeenCalled();
    });
});

describe("direct OpenAI image setup", () => {
    afterEach(() => vi.resetAllMocks());
    const timeline = {
        ...compileResult,
        schemaVersion: 2 as const,
        projectId: "saved",
        revision: 2,
        renderPlan: {
            groupingPolicy: "fixed_provider_windows" as const,
            fps: 24 as const,
            provider: "kie" as const,
            units: [],
            groups: [],
            imageModel: "gpt-image-2.6-flare",
        },
    };
    it("requires the OpenAI image connection for a new grouped image plan", async () => {
        await expect(
            renderSmartRemakeVideo("ws", {
                compileResult: timeline,
                health: { ...health, kieConfigured: true, openaiImagesConfigured: false },
            }),
        ).rejects.toThrow("OpenAI");
        expect(renderSmartRemake).not.toHaveBeenCalled();
    });
    it("submits once when both KIE and direct OpenAI images are configured", async () => {
        vi.mocked(renderSmartRemake).mockResolvedValue(apiResult);
        await renderSmartRemakeVideo("ws", {
            compileResult: timeline,
            health: { ...health, kieConfigured: true, openaiImagesConfigured: true },
        });
        expect(renderSmartRemake).toHaveBeenCalledOnce();
    });
    it.each([
        "OPENAI_IMAGES_NOT_CONFIGURED",
        "OPENAI_IMAGE_NOT_CONFIGURED",
        "OPENAI_IMAGE_NOT_LIVE",
        "OPENAI_IMAGE_VALIDATION_FAILED",
        "OPENAI_IMAGE_SUBMISSION_UNRESOLVED",
        "OPENAI_IMAGE_AUTH_FAILED",
        "OPENAI_IMAGE_PERMISSION_DENIED",
        "OPENAI_IMAGE_RATE_LIMITED",
        "OPENAI_IMAGE_REQUEST_REJECTED",
        "SMART_REMAKE_IMAGE_ASSET_INVALID",
        "OPENAI_IMAGE_OUTPUT_INVALID",
    ])("does not surface raw image provider details for %s", (code) => {
        const message = getRemakeErrorMessage(new ApiError(code, "PRIVATE_PROVIDER_PAYLOAD", 503));
        expect(message).not.toContain("PRIVATE_PROVIDER");
        expect(message).toContain("ảnh");
    });
});
