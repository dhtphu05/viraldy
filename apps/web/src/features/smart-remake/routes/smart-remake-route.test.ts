// @vitest-environment jsdom
import { createElement, type ComponentType, type ReactNode } from "react";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Route } from "./smart-remake-route";
import { confirmRemakeMediaRights, emptyRemakeRights } from "../lib/remake-intake";
import type { SmartRemakeInspectSubject, RepairIntent } from "@/shared/api/smart-remake";
import * as analysisLoading from "../components/remake-analysis-loading";
import * as resultActions from "../lib/remake-result-next-action";

const state = vi.hoisted(() => ({
    studio: {} as Record<string, unknown>,
    projectId: undefined as string | undefined,
    navigate: vi.fn(),
    hook: vi.fn(),
}));
vi.mock("@tanstack/react-router", () => ({
    createFileRoute: () => (options: unknown) => ({ options }),
    useRouteContext: () => ({ auth: { user: { id: "account" } } }),
    useSearch: () => ({ projectId: state.projectId }),
    useNavigate: () => state.navigate,
}));
vi.mock("@/widgets/app-shell/app-shell", () => ({
    AppShell: ({ children, footer }: { children: ReactNode; footer?: ReactNode }) =>
        createElement("div", null, children, footer ? createElement("footer", null, footer) : null),
}));
vi.mock("@/shared/hooks/use-workspace", () => ({
    useApiWorkspace: () => ({ workspaceId: "workspace", workspaces: {} }),
}));
vi.mock("../lib/use-remake-studio", () => ({
    useRemakeStudio: (...args: unknown[]) => {
        state.hook(...args);
        return state.studio;
    },
}));
vi.mock("../components/remake-inputs", () => ({
    RemakeInputs: () =>
        createElement(
            "div",
            null,
            createElement(
                "section",
                null,
                createElement("button", null, "Thêm video"),
                createElement("input", { "aria-label": "Chọn file video mẫu", type: "file" }),
            ),
            createElement(
                "section",
                null,
                createElement("button", null, "Thêm sản phẩm"),
                createElement("input", { "aria-label": "Chọn ảnh sản phẩm", type: "file" }),
            ),
        ),
}));
vi.mock("../components/remake-journey", () => ({ RemakeJourney: () => null }));
vi.mock("../components/remake-storyboard", () => ({
    RemakeStoryboard: ({
        onRecompile,
        compileResult,
    }: {
        onRecompile(): void;
        compileResult: { productLock?: { productName?: string } };
    }) =>
        createElement(
            "div",
            null,
            createElement("button", { onClick: onRecompile }, "Phân tích lại từ cảnh"),
            compileResult.productLock?.productName,
        ),
}));
vi.mock("../components/remake-project-controls", () => ({
    RemakeProjectControls: () => createElement("section", null, "Duyệt và tải thành phẩm"),
}));
vi.mock("../components/remake-output", () => ({
    RemakeOutput: ({ onRepair }: { onRepair(sceneId: string, draft: RepairIntent): unknown }) =>
        createElement(
            "button",
            {
                onClick: () =>
                    void onRepair("scene", {
                        schemaVersion: 1,
                        issues: ["action"],
                        instruction: "Rót chậm hơn",
                    }),
            },
            "Sửa cảnh",
        ),
}));
vi.mock("../components/remake-inspector", () => ({
    RemakeInspector: ({ onInspect }: { onInspect(subject: SmartRemakeInspectSubject): unknown }) =>
        createElement(
            "div",
            null,
            createElement(
                "button",
                { onClick: () => void onInspect({ kind: "image", imageRole: "product" }) },
                "Kiểm tra tư liệu",
            ),
            createElement(
                "article",
                { "data-inspection-report-id": "report" },
                createElement(
                    "div",
                    { "data-inspection-finding-id": "finding" },
                    "Chi tiết cần xem",
                ),
            ),
        ),
}));

beforeEach(() => {
    state.projectId = undefined;
    state.navigate.mockClear();
    state.hook.mockClear();
    state.studio = {
        step: "prepare",
        busy: null,
        sourceUrl: "blob:source",
        productUrls: ["blob:product"],
        primaryIndex: 0,
        duration: 8,
        requirements: {
            intent: "Theo video mẫu",
            keep: [],
            replace: [],
            forbid: [],
            claims: [],
            requiresCharacter: false,
        },
        rights: emptyRemakeRights(),
        budget: { capUsd: "", maxAttempts: 20, maxDurationSeconds: 1800 },
        health: { data: { enabled: true, mode: "live" }, isError: false, isPending: false },
        canAnalyze: false,
        analyze: vi.fn(),
        generate: vi.fn(),
        inspect: vi.fn(),
        repair: vi.fn(),
        requestAction: vi.fn(),
        cancelAction: vi.fn(),
        confirmAction: vi.fn().mockResolvedValue("completed"),
        retryAction: vi.fn(),
        setStep: vi.fn(),
        refreshProject: vi.fn().mockResolvedValue(undefined),
    };
});
afterEach(cleanup);

describe("server project navigation", () => {
    const identity = "b3fa8422-06ed-51fd-95d1-970b6acc97e2";
    it("validates project bookmarks and passes the owned project selection without starting AI", () => {
        const validate = Route.options.validateSearch as (value: Record<string, unknown>) => {
            projectId?: string;
        };
        expect(validate({ projectId: identity })).toEqual({ projectId: identity });
        expect(validate({ projectId: "../another-workspace" })).toEqual({ projectId: undefined });
        state.projectId = identity;
        renderPage();
        expect(state.hook).toHaveBeenCalledWith("workspace", "account", identity, false);
        expect(state.studio.requestAction).not.toHaveBeenCalled();
    });
    it("writes a newly created server project into the current URL without replacing another explicit selection", () => {
        state.studio.project = { id: identity, targetDuration: 16, scenes: [] };
        const view = render(createElement(Route.options.component as ComponentType));
        expect(state.navigate).toHaveBeenCalledExactlyOnceWith({
            to: "/smart-remake",
            search: { projectId: identity },
            replace: true,
        });
        state.navigate.mockClear();
        state.projectId = "86184744-8a25-493d-b977-cdac41bcc8d2";
        view.rerender(createElement(Route.options.component as ComponentType));
        expect(state.navigate).not.toHaveBeenCalled();
        expect(state.studio.requestAction).not.toHaveBeenCalled();
    });
});
function renderPage() {
    render(createElement(Route.options.component as ComponentType));
    return within(screen.queryByRole("contentinfo") ?? document.body);
}
function plan() {
    state.studio.step = "plan";
    state.studio.compiled = {
        schemaVersion: 2,
        expectationsVersion: 1,
        expectationsHash: "a".repeat(64),
        renderPlan: { groupingPolicy: "fixed_provider_windows", units: [] },
        sceneMap: { sceneCount: 1, scenes: [] },
        inputSummary: { targetDuration: 8 },
        warnings: [],
    };
}

describe("action-driven Smart Remake", () => {
    it("makes failed reanalysis primary instead of presenting the saved script as a new result", () => {
        plan();
        state.studio.project = {
            id: "project",
            revision: 4,
            schemaVersion: 2,
            scenes: [],
            renderPlan: { units: [] },
            analysisProgress: {
                status: "failed",
                operationId: "failed-analysis",
                requestKey: "failed-key",
                retryDisposition: "new_analysis",
                scenes: [],
            },
        };
        renderPage();
        expect(screen.getByRole("heading", { level: 1 }).textContent).toBe(
            "Chưa cập nhật được kịch bản",
        );
        expect(screen.getByRole("button", { name: "Phân tích lại" })).toBeTruthy();
        expect(screen.queryByRole("button", { name: "Tạo kịch bản" })).toBeNull();
        expect(screen.queryByRole("button", { name: /Tạo video/ })).toBeNull();
        expect(screen.queryByText(/AI đã phân tích video mẫu và soạn kịch bản/)).toBeNull();
        fireEvent.click(screen.getByRole("button", { name: "Phân tích lại" }));
        expect(state.studio.requestAction).toHaveBeenCalledExactlyOnceWith("reanalyze");
        expect(state.studio.analyze).not.toHaveBeenCalled();
    });

    it("keeps facts from the failed project visible after the analysis tracker is cleared", () => {
        Object.assign(state.studio, {
            analysisProgress: null,
            analysisUnresolved: false,
            busy: null,
            actionExecutingIntent: null,
            error: "Phân tích chưa hoàn tất.",
            project: {
                id: "failed-analysis-project",
                revision: 3,
                scenes: [],
                analysisProgress: {
                    schemaVersion: 1,
                    operationId: "previous-operation",
                    requestKey: "previous-key",
                    status: "failed",
                    stage: "failed",
                    startedAt: "2026-11-26T09:00:00Z",
                    updatedAt: "2026-11-26T09:02:00Z",
                    scenes: [],
                    preliminaryObservations: [
                        { label: "Hành động", detail: "Mở nắp rồi rót nước." },
                    ],
                    quickSummary: { status: "unavailable", reason: "timeout" },
                },
            },
        });
        renderPage();
        const snapshot = screen.getByRole("region", { name: "Nhận định từ lượt phân tích trước" });
        expect(
            within(snapshot).getByRole("heading", { name: "Từ lượt phân tích trước" }),
        ).toBeTruthy();
        expect(within(snapshot).getByText("Mở nắp rồi rót nước.")).toBeTruthy();
        expect(within(snapshot).queryByLabelText("Thời gian đã chờ")).toBeNull();
        expect(within(snapshot).queryByLabelText("Video mẫu đang phân tích")).toBeNull();
        expect(within(snapshot).queryByRole("button")).toBeNull();
        expect(screen.getByRole("button", { name: "Thêm video" })).toBeTruthy();
        expect(screen.getByRole("button", { name: "Thêm sản phẩm" })).toBeTruthy();
        expect(state.studio.analyze).not.toHaveBeenCalled();
        expect(state.studio.requestAction).not.toHaveBeenCalled();
    });

    it("does not show a past-analysis snapshot without received facts", () => {
        state.studio.project = {
            id: "empty-failed-project",
            revision: 1,
            scenes: [],
            analysisProgress: {
                status: "failed",
                stage: "failed",
                scenes: [],
                quickSummary: { status: "unavailable" },
            },
        };
        renderPage();
        expect(
            screen.queryByRole("region", { name: "Nhận định từ lượt phân tích trước" }),
        ).toBeNull();
    });

    function recoverableOutput() {
        plan();
        state.studio.step = "result";
        state.studio.project = {
            id: "project",
            schemaVersion: 2,
            revision: 2,
            status: "incomplete",
            targetDuration: 16,
            provider: "kie",
            finalVideoUrl: "",
            scenes: [{ id: "scene", index: 0, activeVersionId: null, versions: [] }],
            generationRecovery: {
                kind: "retry_initial_render",
                stage: "image",
                errorCode: "OPENAI_RATE_LIMITED",
                requestKey: "failed",
            },
        };
    }
    it("resumes initial generation through the existing action gate and views the saved script without AI", () => {
        recoverableOutput();
        renderPage();
        expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Video của bạn");
        fireEvent.click(screen.getByRole("button", { name: "Xem kịch bản" }));
        expect(state.studio.setStep).toHaveBeenCalledWith("plan");
        expect(state.studio.requestAction).not.toHaveBeenCalled();
        fireEvent.click(screen.getByRole("button", { name: "Tiếp tục tạo video" }));
        expect(state.studio.requestAction).toHaveBeenCalledWith("render");
        expect(state.studio.requestAction).toHaveBeenCalledTimes(1);
    });
    it("keeps result options collapsed without draft status or a second action footer", () => {
        recoverableOutput();
        state.studio.localDraftStatus = "saved";
        renderPage();
        const options = screen.getByText("Tùy chọn và thông tin").closest("details")!;
        expect(options.open).toBe(false);
        expect(screen.queryByLabelText("Nháp trên thiết bị")).toBeNull();
        expect(screen.queryByRole("contentinfo")).toBeNull();
        const inspection = screen.getByRole("button", { name: "Kiểm tra tư liệu" });
        expect(inspection.closest("details")!.open).toBe(false);
        expect(options.contains(inspection)).toBe(true);
        fireEvent.click(screen.getByRole("button", { name: "Chỉnh tư liệu" }));
        expect(state.studio.setStep).toHaveBeenCalledWith("prepare");
        expect(state.studio.requestAction).not.toHaveBeenCalled();
    });
    it("opens all result option levels when checking an existing operation without another paid request", () => {
        recoverableOutput();
        (state.studio.project as Record<string, unknown>).pendingOperation = { id: "operation" };
        renderPage();
        fireEvent.click(screen.getByRole("button", { name: "Xem tiến trình" }));
        const options = screen.getByText("Tùy chọn và thông tin").closest("details")!;
        const progress = screen
            .getByText("Tiến trình, quyền và thông tin dự án")
            .closest("details")!;
        expect(options.open).toBe(true);
        expect(progress.open).toBe(true);
        expect(state.studio.refreshProject).toHaveBeenCalledTimes(1);
        expect(state.studio.requestAction).not.toHaveBeenCalled();
    });
    it("reveals the exact inspection finding through the collapsed result options", () => {
        recoverableOutput();
        const next = vi.spyOn(resultActions, "getRemakeResultNextAction").mockReturnValue({
            kind: "findings",
            label: "Xem điểm cần duyệt",
            reason: "Xem nội dung kiểm tra.",
            reportId: "report",
            findingId: "finding",
        });
        try {
            renderPage();
            fireEvent.click(screen.getByRole("button", { name: "Xem điểm cần duyệt" }));
            expect(screen.getByText("Tùy chọn và thông tin").closest("details")!.open).toBe(true);
            expect(screen.getByText("Kiểm tra và bằng chứng").closest("details")!.open).toBe(true);
            expect(document.activeElement).toBe(screen.getByText("Chi tiết cần xem"));
            expect(state.studio.requestAction).not.toHaveBeenCalled();
        } finally {
            next.mockRestore();
        }
    });
    it.each(["error", "conflict"])(
        "ignores retired draft %s state instead of showing or blocking it",
        (status) => {
            recoverableOutput();
            state.studio.localDraftStatus = status;
            state.studio.localDraftError = "Nháp cần được xử lý.";
            state.studio.localDraftLoaded = false;
            renderPage();
            expect(screen.queryByText("Nháp cần được xử lý.")).toBeNull();
            expect(screen.queryByLabelText("Nháp trên thiết bị")).toBeNull();
            expect(
                screen.getByRole("button", { name: "Tiếp tục tạo video" }).hasAttribute("disabled"),
            ).toBe(false);
        },
    );
    it("deduplicates only the image failure already explained by the recovery card", () => {
        recoverableOutput();
        state.studio.error = "Dịch vụ tạo ảnh đang bận.";
        state.studio.errorCode = "OPENAI_RATE_LIMITED";
        const view = render(createElement(Route.options.component as ComponentType));
        expect(screen.queryByRole("alert")).toBeNull();
        expect(screen.getByText("Dịch vụ tạo ảnh đang bận.").closest("details")).toBeTruthy();
        state.studio.error = "Chưa lưu được yêu cầu mới.";
        state.studio.errorCode = "SMART_REMAKE_CONTEXT_SAVE_FAILED";
        view.rerender(createElement(Route.options.component as ComponentType));
        expect(screen.getByRole("alert").textContent).toBe("Chưa lưu được yêu cầu mới.");
    });
    it("locks the recovery action during preflight without starting another request", () => {
        recoverableOutput();
        state.studio.actionLoading = true;
        renderPage();
        const button = screen.getByRole("button", {
            name: "Đang kiểm tra…",
        }) as HTMLButtonElement;
        expect(button.disabled).toBe(true);
        fireEvent.click(button);
        expect(state.studio.requestAction).not.toHaveBeenCalled();
    });
    it.each(["inline", "direct", "confirmation"])(
        "keeps all imported product images and the selected primary image in %s loading",
        (presentation) => {
            const productUrls = ["blob:front", "blob:side", "blob:detail"];
            Object.assign(state.studio, {
                productUrls,
                primaryIndex: 1,
                project: {
                    id: "previous-project",
                    revision: 1,
                    scenes: [],
                    productImageUrl: "/previous-product.png",
                },
                ...(presentation === "inline"
                    ? { busy: "analyze" }
                    : presentation === "direct"
                      ? {
                            actionExecutingIntent: { action: "analyze", fingerprint: "current" },
                            actionLoading: true,
                        }
                      : {
                            pendingAction: { action: "analyze", fingerprint: "current" },
                            actionSubmitting: true,
                        }),
            });
            const loading = vi.spyOn(analysisLoading, "RemakeAnalysisLoading");
            try {
                renderPage();
                expect(loading).toHaveBeenCalled();
                expect(loading.mock.calls.at(-1)?.[0]).toMatchObject({
                    productUrls,
                    primaryIndex: 1,
                    productUrl: "blob:side",
                });
                expect(state.studio.analyze).not.toHaveBeenCalled();
            } finally {
                loading.mockRestore();
            }
        },
    );

    it("retains the server product image when no local product images are available", () => {
        Object.assign(state.studio, {
            busy: "analyze",
            productUrls: [],
            project: {
                id: "restored-project",
                revision: 1,
                scenes: [],
                productImageUrl: "/retained-product.png",
            },
        });
        const loading = vi.spyOn(analysisLoading, "RemakeAnalysisLoading");
        try {
            renderPage();
            expect(loading.mock.calls.at(-1)?.[0]).toMatchObject({
                productUrls: [],
                primaryIndex: 0,
                productUrl: "/retained-product.png",
            });
        } finally {
            loading.mockRestore();
        }
    });

    it.each([true, false])(
        "restored preview uses observed product facts only for the matching completed script: %s",
        (matching) => {
            plan();
            Object.assign(state.studio.compiled as object, {
                projectId: "project",
                revision: 7,
                productLock: {},
            });
            state.studio.project = {
                id: "project",
                schemaVersion: 2,
                revision: matching ? 7 : 8,
                scenes: [],
                analysisProgress: {
                    status: "completed",
                    product: { name: "Bình màu hồng", details: ["Nắp trong suốt"] },
                },
            };
            renderPage();
            expect(Boolean(screen.queryByText("Bình màu hồng"))).toBe(matching);
            expect((state.studio.compiled as { productLock: object }).productLock).toEqual({});
        },
    );
    it("offers an explicit update for an old fitted four-call plan without starting AI", () => {
        plan();
        Object.assign(state.studio.compiled as object, {
            sourceSceneMap: { timingMode: "fit_target", scenes: [] },
            renderPlan: { groups: [{ id: "one" }, { id: "two" }, { id: "three" }, { id: "four" }] },
        });
        const footer = renderPage();
        expect(state.studio.requestAction).not.toHaveBeenCalled();
        fireEvent.click(footer.getByRole("button", { name: "Cập nhật kịch bản" }));
        expect(state.studio.requestAction).toHaveBeenCalledWith("reanalyze");
    });
    it("shows only analysis progress for a direct action with already-confirmed rights", () => {
        state.studio.actionExecutingIntent = { action: "analyze", fingerprint: "source" };
        state.studio.actionLoading = true;
        state.studio.pendingAction = null;
        state.studio.sourceDuration = 30;
        renderPage();
        expect(screen.getByRole("dialog")).toBeTruthy();
        expect(screen.getByText("Đang chuẩn bị phân tích")).toBeTruthy();
        expect(screen.queryByText("Trần ngân sách dự án")).toBeNull();
        expect(screen.queryByRole("checkbox")).toBeNull();
        expect(screen.queryByRole("button", { name: "Xác nhận và tạo kịch bản" })).toBeNull();
        expect(
            (screen.getByText("Tạo kịch bản").closest("button") as HTMLButtonElement).disabled,
        ).toBe(true);
    });
    it("shows actual analysis findings inline without keeping the seller in a modal", () => {
        Object.assign(state.studio, {
            busy: "analyze",
            actionExecutingIntent: { action: "analyze", fingerprint: "current-source" },
            analysisStartedAt: Date.now() - 60_000,
            analysisStatusError: "Chưa đọc được cập nhật mới. Yêu cầu vẫn được giữ.",
            checkAnalysisStatus: vi.fn(),
            canCheckAnalysisStatus: true,
            analysisProgress: {
                schemaVersion: 1,
                operationId: "compile-current",
                requestKey: "current",
                status: "running",
                stage: "identifying_product",
                startedAt: new Date().toISOString(),
                updatedAt: new Date().toISOString(),
                sourceDurationSeconds: 30,
                sceneCount: 1,
                scenes: [{ index: 0, startSecond: 0, endSecond: 30, action: "Đặt bình lên bàn" }],
            },
        });
        renderPage();
        expect(screen.queryByRole("dialog")).toBeNull();
        expect(screen.getByText("Đặt bình lên bàn")).toBeTruthy();
        expect(document.querySelector('video[src="blob:source"]')).toBeTruthy();
        fireEvent.click(screen.getByRole("button", { name: "Kiểm tra trạng thái" }));
        expect(state.studio.checkAnalysisStatus).toHaveBeenCalledTimes(1);
        expect(state.studio.requestAction).not.toHaveBeenCalled();
    });
    it("keeps read-only progress available after an interrupted analysis request", () => {
        Object.assign(state.studio, {
            analysisUnresolved: true,
            analysisStartedAt: Date.now() - 60_000,
            analysisStatusError: "Chưa đọc được cập nhật mới. Yêu cầu vẫn được giữ.",
            checkAnalysisStatus: vi.fn(),
            canCheckAnalysisStatus: true,
        });
        renderPage();
        fireEvent.click(screen.getByRole("button", { name: "Kiểm tra trạng thái" }));
        expect(state.studio.checkAnalysisStatus).toHaveBeenCalledTimes(1);
        expect(state.studio.requestAction).not.toHaveBeenCalled();
    });
    it("reconciles pending work from the next step without opening another AI action", () => {
        state.studio.step = "result";
        state.studio.project = {
            id: "project",
            revision: 2,
            scenes: [],
            pendingOperation: { id: "old", needsReconciliation: true },
        };
        state.studio.busy = "restore";
        renderPage();
        const next = screen.getByRole("button", {
            name: "Kiểm tra trạng thái",
        }) as HTMLButtonElement;
        expect(next.disabled).toBe(false);
        fireEvent.click(next);
        expect((document.activeElement as HTMLElement).tabIndex).toBe(0);
        expect(state.studio.refreshProject).toHaveBeenCalledTimes(1);
        expect(state.studio.requestAction).not.toHaveBeenCalled();
    });
    it("introduces a retained candidate without navigating until the seller chooses it", () => {
        state.studio.step = "result";
        state.studio.project = {
            id: "project",
            revision: 2,
            scenes: [
                {
                    id: "scene",
                    index: 0,
                    activeVersionId: "old",
                    versions: [{ id: "new", videoUrl: "/candidate.mp4" }],
                },
            ],
        };
        state.studio.unreadRepairCandidate = {
            projectId: "project",
            sceneId: "scene",
            versionId: "new",
        };
        state.studio.viewRepairCandidate = vi.fn();
        state.studio.dismissRepairCandidate = vi.fn();
        renderPage();
        expect(state.studio.viewRepairCandidate).not.toHaveBeenCalled();
        fireEvent.click(screen.getByRole("button", { name: "Xem bản mới cảnh 1" }));
        expect(state.studio.viewRepairCandidate).toHaveBeenCalledTimes(1);
        expect(state.studio.requestAction).not.toHaveBeenCalled();
    });
    it("sends the seller to a damaged clip before allowing compose or paid inspection", () => {
        state.studio.step = "result";
        state.studio.project = {
            id: "project",
            revision: 2,
            scenes: [{ id: "scene", index: 0, activeVersionId: "old", versions: [] }],
        };
        state.studio.navigateOutput = vi.fn();
        renderPage();
        fireEvent.click(screen.getByRole("button", { name: "Xem cảnh 1 cần xử lý" }));
        expect(state.studio.navigateOutput).toHaveBeenCalledWith("scene", "watch", undefined);
        expect(state.studio.requestAction).not.toHaveBeenCalled();
    });
    it("requires an updated plan for restored changed media instead of presenting old output as ready", () => {
        state.studio.step = "result";
        state.studio.project = {
            id: "project",
            revision: 2,
            scenes: [{ id: "scene", index: 0, versions: [] }],
        };
        state.studio.localMediaNeedsAnalysis = true;
        renderPage();
        fireEvent.click(screen.getByRole("button", { name: "Cập nhật kịch bản" }));
        expect(state.studio.requestAction).toHaveBeenCalledWith("reanalyze");
    });
    it("opens action confirmation with an empty budget instead of disabling the next step", () => {
        state.studio.intakeError = "Nhập trần USD lớn hơn 0";
        const footer = renderPage();
        const next = footer.getByRole("button", { name: "Tạo kịch bản" }) as HTMLButtonElement;
        expect(next.disabled).toBe(false);
        fireEvent.click(next);
        expect(state.studio.requestAction).toHaveBeenCalledWith("analyze");
        expect(state.studio.analyze).not.toHaveBeenCalled();
        expect(footer.queryByText(/Nhập trần USD/)).toBeNull();
        expect(screen.queryByLabelText("Trần chi phí (USD)")).toBeNull();
    });
    it("opens confirmation even when existing rights and budget are valid", () => {
        state.studio.rights = confirmRemakeMediaRights(emptyRemakeRights());
        state.studio.canAnalyze = true;
        const footer = renderPage();
        fireEvent.click(footer.getByRole("button", { name: "Tạo kịch bản" }));
        expect(state.studio.requestAction).toHaveBeenCalledWith("analyze");
        expect(state.studio.analyze).not.toHaveBeenCalled();
    });
    it.each([
        ["source", "Thêm video"],
        ["product", "Thêm sản phẩm"],
    ])("focuses the missing %s media instead of a disabled button", (kind, label) => {
        if (kind === "source") state.studio.sourceUrl = null;
        else state.studio.productUrls = [];
        const footer = renderPage();
        fireEvent.click(footer.getByRole("button", { name: "Tạo kịch bản" }));
        expect(document.activeElement).toBe(screen.getByRole("button", { name: label }));
        expect(state.studio.analyze).not.toHaveBeenCalled();
    });
    it("keeps only an active operation from accepting another click", () => {
        state.studio.busy = "analyze";
        expect(
            (renderPage().getByRole("button", { name: "Tạo kịch bản" }) as HTMLButtonElement)
                .disabled,
        ).toBe(true);
    });
    it("routes a restored pending operation to progress without a new request", () => {
        state.studio.project = {
            id: "project",
            schemaVersion: 2,
            scenes: [],
            pendingOperation: { id: "old" },
        };
        fireEvent.click(renderPage().getByRole("button", { name: "Xem tiến trình" }));
        expect(state.studio.setStep).toHaveBeenCalledWith("result");
        expect(state.studio.refreshProject).toHaveBeenCalledTimes(1);
        expect(state.studio.requestAction).not.toHaveBeenCalled();
    });
    it("opens render and reanalysis confirmation from the plan", () => {
        plan();
        const footer = renderPage();
        fireEvent.click(footer.getByRole("button", { name: /Tạo video/ }));
        fireEvent.click(screen.getByRole("button", { name: "Phân tích lại từ cảnh" }));
        expect(state.studio.requestAction).toHaveBeenNthCalledWith(1, "render");
        expect(state.studio.requestAction).toHaveBeenNthCalledWith(2, "reanalyze");
        expect(state.studio.generate).not.toHaveBeenCalled();
        expect(state.studio.analyze).not.toHaveBeenCalled();
    });
    it.each(["sourcePlanDirty", "legacyExpectations"])(
        "makes updating the plan the next action when required: %s",
        (reason) => {
            plan();
            if (reason === "sourcePlanDirty") state.studio.sourcePlanDirty = true;
            else
                state.studio.compiled = {
                    ...(state.studio.compiled as Record<string, unknown>),
                    expectationsVersion: 0,
                };
            const footer = renderPage();
            fireEvent.click(footer.getByRole("button", { name: "Cập nhật kịch bản" }));
            expect(state.studio.requestAction).toHaveBeenCalledWith("reanalyze");
            expect(state.studio.generate).not.toHaveBeenCalled();
        },
    );
    it.each(["plan", "result"])("shows final approval only in the result step: %s", (step) => {
        plan();
        state.studio.step = step;
        state.studio.project = { id: "project", schemaVersion: 2, scenes: [] };
        renderPage();
        expect(Boolean(screen.queryByText("Duyệt và tải thành phẩm"))).toBe(step === "result");
    });
    it("routes repair and inspection through the same confirmation gate", async () => {
        state.studio.step = "result";
        state.studio.project = { id: "project", schemaVersion: 2, revision: 2, scenes: [] };
        renderPage();
        fireEvent.click(screen.getByRole("button", { name: "Sửa cảnh" }));
        fireEvent.click(screen.getByText("Tùy chọn và thông tin"));
        fireEvent.click(screen.getByText("Kiểm tra và bằng chứng"));
        fireEvent.click(screen.getByRole("button", { name: "Kiểm tra tư liệu" }));
        await waitFor(() => expect(state.studio.requestAction).toHaveBeenCalledTimes(2));
        expect(state.studio.requestAction).toHaveBeenCalledWith("repair", {
            sceneId: "scene",
            repairIntent: { schemaVersion: 1, issues: ["action"], instruction: "Rót chậm hơn" },
        });
        expect(state.studio.requestAction).toHaveBeenCalledWith("inspect", {
            subject: { kind: "image", imageRole: "product" },
        });
        expect(state.studio.repair).not.toHaveBeenCalled();
        expect(state.studio.inspect).not.toHaveBeenCalled();
    });
    it.each([
        [{ isError: true }, "Chưa kết nối được dịch vụ Smart Remake. Bấm Kết nối lại để thử."],
        [{ data: { enabled: false } }, "Smart Remake chưa được bật cho môi trường này."],
        [{ data: undefined, isPending: true }, "Đang kiểm tra dịch vụ tạo video."],
    ])("explains service availability without hiding the action: %s", (health, message) => {
        state.studio.health = { data: undefined, ...health };
        const footer = renderPage();
        expect(footer.getByText(message)).toBeTruthy();
        expect(
            (footer.getByRole("button", { name: "Tạo kịch bản" }) as HTMLButtonElement).disabled,
        ).toBe(false);
    });
});
