// @vitest-environment jsdom
import { createElement, StrictMode, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { SmartRemakeProject } from "@/shared/api/smart-remake";
import { confirmRemakeMediaRights, hasCurrentRemakeRightsAttestation } from "./remake-intake";
import { useRemakeStudio } from "./use-remake-studio";
import { ApiError } from "@/shared/api/errors";
import { restoreTimelineCompile } from "./remake-timeline";

const calls = vi.hoisted(() => ({
    health: vi.fn(),
    intake: vi.fn(),
    compile: vi.fn(),
    project: vi.fn(),
    render: vi.fn(),
    crawl: vi.fn(),
    preflight: vi.fn(),
    update: vi.fn(),
    repair: vi.fn(),
    inspect: vi.fn(),
    receipt: vi.fn(),
    readDraft: vi.fn(),
    saveDraft: vi.fn(),
    removeDraft: vi.fn(),
    listMarkers: vi.fn(),
    writeMarker: vi.fn(),
    updateMarker: vi.fn(),
}));
vi.mock("@/shared/api/smart-remake", async (original) => ({
    ...(await original<Record<string, unknown>>()),
    getSmartRemakeHealth: calls.health,
    createSmartRemakeProject: calls.intake,
    compileSmartRemake: calls.compile,
    getSmartRemakeProject: calls.project,
    getSmartRemakePreflight: calls.preflight,
    updateSmartRemakeContext: calls.update,
    repairSmartRemakeScene: calls.repair,
    inspectSmartRemakeSubject: calls.inspect,
    getSmartRemakeRepairReceipt: calls.receipt,
}));
vi.mock("./remake-draft", async (original) => ({
    ...(await original<Record<string, unknown>>()),
    remakeDraftStore: {
        read: calls.readDraft,
        save: calls.saveDraft,
        remove: calls.removeDraft,
        listSubmissionMarkers: calls.listMarkers,
        writeSubmissionMarker: calls.writeMarker,
        updateSubmissionMarker: calls.updateMarker,
    },
}));
vi.mock("./remake-media-binding", () => ({
    hashRemakeFile: async (file: File) =>
        file.name === "source.mp4"
            ? "a".repeat(64)
            : file.name === "product.png"
              ? "b".repeat(64)
              : "c".repeat(64),
}));
vi.mock("@/shared/api/products", () => ({ crawlProductPreview: calls.crawl }));
vi.mock("./smart-remake-render", async (original) => ({
    ...(await original<Record<string, unknown>>()),
    renderSmartRemakeVideo: calls.render,
}));

const requirements = {
    intent: "Keep the magenta product and opening action",
    keep: [],
    replace: [],
    forbid: [],
    claims: [],
    requiresCharacter: false,
};
const declaration = {
    basis: "owned" as const,
    declared: true,
    scope: "Internal dev pilot",
    evidenceNote: "Self-authored test artwork and animation",
};
const rights = { source: declaration, product: declaration, providerDisclosureAcknowledged: true };
const budget = { capUsd: "2.50", maxAttempts: 12, maxDurationSeconds: 600 };
const existingClip: SmartRemakeProject["scenes"][number]["versions"][number] = {
    id: "version",
    parentVersionId: null,
    videoUrl: "/clip.mp4",
    prompt: "p",
    imagePrompt: "i",
    videoPrompt: "v",
    source: "generated",
    createdAt: "2026-01-01T00:00:00Z",
    technicalCheck: {
        status: "passed",
        findings: [],
        checkedAt: "2026-01-01T00:00:00Z",
        mediaHash: "c".repeat(64),
    },
};
const project = (phase: "intake" | "compiled" = "intake") =>
    ({
        id: "owned",
        revision: 1,
        phase,
        schemaVersion: 2,
        status: "draft",
        provider: "kie",
        scenes: [],
        finalVideoUrl: "",
        sourceVideoUrl: "/source.mp4",
        productImageUrl: "/product.png",
        targetDuration: 8,
        requirements,
        rights,
        budget: { policy: budget },
        ...(phase === "compiled"
            ? {
                  renderPlan: {
                      fps: 24,
                      provider: "kie",
                      groupingPolicy: "fixed_provider_windows",
                      units: [],
                  },
              }
            : {}),
    }) as SmartRemakeProject;

describe("explicit server project entry", () => {
    it("starts a new project with the twelve-second output", () => {
        const hook = renderHook(() => useRemakeStudio("workspace", "account", undefined, true), {
            wrapper,
        });
        expect(hook.result.current.duration).toBe(12);
    });
    it("retires the previous project's analysis and follows the selected project's own compile", async () => {
        const pending = (id: string, revision: number) =>
            ({
                ...project("compiled"),
                id,
                revision,
                pendingOperation: { id: `compile-${id}`, kind: "compile", status: "running" },
                analysisProgress: {
                    schemaVersion: 1,
                    operationId: `compile-${id}`,
                    requestKey: `request-${id}`,
                    status: "running",
                    stage: "analyzing_source",
                    startedAt: "2026-11-26T10:00:00Z",
                    updatedAt: "2026-11-26T10:00:01Z",
                },
            }) as SmartRemakeProject;
        calls.project.mockImplementation(async (_workspace, id) =>
            pending(id, id === "first" ? 9 : 1),
        );
        const hook = renderHook(({ id }) => useRemakeStudio("workspace", "account", id), {
            wrapper,
            initialProps: { id: "first" },
        });
        await waitFor(() =>
            expect(hook.result.current.analysisProgress?.operationId).toBe("compile-first"),
        );
        hook.rerender({ id: "second" });
        await waitFor(() => expect(hook.result.current.project?.id).toBe("second"));
        await waitFor(() =>
            expect(hook.result.current.analysisProgress?.operationId).toBe("compile-second"),
        );
        expect(calls.compile).not.toHaveBeenCalled();
        expect(calls.render).not.toHaveBeenCalled();
    });
    it.each(["completed", "failed"] as const)(
        "ignores a late %s compile after opening another project",
        async (outcome) => {
            let resolveCompile!: (result: unknown) => void;
            let rejectCompile!: (cause: Error) => void;
            let finishSecond!: (result: SmartRemakeProject) => void;
            calls.compile.mockImplementation(
                () =>
                    new Promise((resolve, reject) => {
                        resolveCompile = resolve;
                        rejectCompile = reject;
                    }),
            );
            calls.project.mockImplementation(async (_workspace, id) =>
                id === "second"
                    ? new Promise<SmartRemakeProject>((resolve) => {
                          finishSecond = resolve;
                      })
                    : {
                          ...project("compiled"),
                          id,
                          budget: { policy: { mode: "unlimited" } },
                      },
            );
            const hook = renderHook(({ id }) => useRemakeStudio("workspace", "account", id), {
                wrapper,
                initialProps: { id: "first" },
            });
            await waitFor(() => expect(hook.result.current.project?.id).toBe("first"));
            act(() => hook.result.current.onSourceMetadata(20));
            let submitted!: Promise<unknown>;
            act(() => {
                submitted = hook.result.current.analyze();
            });
            await waitFor(() => expect(calls.compile).toHaveBeenCalledOnce());
            hook.rerender({ id: "second" });
            await waitFor(() => expect(calls.project).toHaveBeenCalledWith("workspace", "second"));
            const notice = hook.result.current.notice;
            await act(async () => {
                if (outcome === "completed")
                    resolveCompile({
                        success: true,
                        ...restoreTimelineCompile(project("compiled")),
                        projectId: "first",
                    });
                else
                    rejectCompile(
                        new ApiError("OLD_COMPILE_FAILED", "Previous project failed", 422),
                    );
                await submitted;
            });
            expect(hook.result.current.project).toBeNull();
            expect(hook.result.current.busy).toBe("restore");
            expect(hook.result.current.compiled?.projectId).not.toBe("first");
            expect(hook.result.current.notice).toBe(notice);
            expect(hook.result.current.error).toBeNull();
            expect(hook.result.current.analysisProgress).toBeNull();
            await act(async () => finishSecond({ ...project("compiled"), id: "second" }));
            expect(hook.result.current.project?.id).toBe("second");
            expect(hook.result.current.busy).toBeNull();
            expect(calls.compile).toHaveBeenCalledOnce();
            expect(calls.render).not.toHaveBeenCalled();
        },
    );
    it("starts an explicit new intake without reopening or removing an older pending receipt", async () => {
        localStorage.setItem("remake-project:account:workspace", "older-project");
        const hook = renderHook(() => useRemakeStudio("workspace", "account", undefined, true), {
            wrapper,
        });
        await act(async () => {
            await Promise.resolve();
        });
        expect(hook.result.current.project).toBeNull();
        expect(hook.result.current.busy).toBeNull();
        expect(calls.project).not.toHaveBeenCalled();
        expect(calls.listMarkers).not.toHaveBeenCalled();
        expect(localStorage.getItem("remake-project:account:workspace")).toBe("older-project");
        expect(calls.compile).not.toHaveBeenCalled();
        expect(calls.render).not.toHaveBeenCalled();
    });
    it("discards a late read when selecting another project URL", async () => {
        let finishFirst!: (value: SmartRemakeProject) => void;
        calls.project.mockImplementation(async (_workspace, id) =>
            id === "first"
                ? new Promise<SmartRemakeProject>((resolve) => {
                      finishFirst = resolve;
                  })
                : { ...project("compiled"), id },
        );
        const hook = renderHook(({ id }) => useRemakeStudio("workspace", "account", id), {
            wrapper,
            initialProps: { id: "first" },
        });
        await waitFor(() => expect(calls.project).toHaveBeenCalledWith("workspace", "first"));
        hook.rerender({ id: "second" });
        await waitFor(() => expect(hook.result.current.project?.id).toBe("second"));
        await act(async () => {
            finishFirst({ ...project("compiled"), id: "first" });
        });
        expect(hook.result.current.project?.id).toBe("second");
        expect(calls.compile).not.toHaveBeenCalled();
        expect(calls.render).not.toHaveBeenCalled();
    });
    it("reopens safely through StrictMode effect cleanup without submitting AI", async () => {
        calls.project.mockResolvedValue(project("compiled"));
        const hook = renderHook(() => useRemakeStudio("workspace", "account", "owned"), {
            wrapper: ({ children }) =>
                createElement(StrictMode, null, createElement(wrapper, null, children)),
        });
        await waitFor(() => expect(hook.result.current.project?.id).toBe("owned"));
        expect(hook.result.current.busy).toBeNull();
        expect(calls.compile).not.toHaveBeenCalled();
        expect(calls.render).not.toHaveBeenCalled();
    });
    it("opens an unfinished project from its URL without uploading, restoring a device draft or starting AI", async () => {
        calls.project.mockResolvedValue({
            ...project("compiled"),
            generationProgress: {
                operationId: "render",
                status: "failed",
                startedAt: "2026-11-26T10:00:00Z",
                updatedAt: "2026-11-26T10:01:00Z",
                groups: [],
            },
        });
        const hook = renderHook(() => useRemakeStudio("workspace", "account", "owned"), {
            wrapper,
        });
        await waitFor(() => expect(hook.result.current.project?.id).toBe("owned"));
        expect(hook.result.current.step).toBe("result");
        expect(hook.result.current.sourceUrl).toBe("/source.mp4");
        expect(hook.result.current.productUrls).toEqual(["/product.png"]);
        expect(calls.intake).not.toHaveBeenCalled();
        expect(calls.compile).not.toHaveBeenCalled();
        expect(calls.render).not.toHaveBeenCalled();
        expect(calls.readDraft).not.toHaveBeenCalled();
    });
    it("does not fall back to another project when an explicit project is inaccessible", async () => {
        localStorage.setItem("remake-project:account:workspace", "another-project");
        calls.project.mockRejectedValue(new ApiError("SMART_REMAKE_PROJECT_NOT_FOUND", "", 404));
        const hook = renderHook(() => useRemakeStudio("workspace", "account", "missing"), {
            wrapper,
        });
        await waitFor(() => expect(hook.result.current.error).toBeTruthy());
        expect(hook.result.current.project).toBeNull();
        expect(calls.project).toHaveBeenCalledWith("workspace", "missing");
        expect(calls.project).not.toHaveBeenCalledWith("workspace", "another-project");
        expect(calls.compile).not.toHaveBeenCalled();
        expect(calls.render).not.toHaveBeenCalled();
    });
});

function wrapper({ children }: { children: ReactNode }) {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
    return createElement(QueryClientProvider, { client }, children);
}

beforeEach(() => {
    vi.clearAllMocks();
    calls.readDraft.mockResolvedValue(null);
    calls.saveDraft.mockImplementation(async (scope, value) => ({ scope, ...value, revision: 1 }));
    calls.removeDraft.mockResolvedValue(undefined);
    const markers = new Map<string, Record<string, unknown>>();
    calls.listMarkers.mockImplementation(async () => [...markers.values()]);
    calls.receipt.mockResolvedValue({ receipt: null });
    calls.writeMarker.mockImplementation(async (_scope, value) => {
        const marker = {
            ...value,
            status: "awaiting_receipt",
            operationId: null,
            candidateVersionId: null,
            disposition: null,
        };
        markers.set(value.requestKey, marker);
        return marker;
    });
    calls.updateMarker.mockImplementation(async (_scope, requestKey, patch) => {
        const marker = { ...markers.get(requestKey), ...patch };
        markers.set(requestKey, marker);
        return marker;
    });
    const stored = new Map<string, string>();
    vi.stubGlobal("localStorage", {
        clear: () => stored.clear(),
        getItem: (key: string) => stored.get(key) ?? null,
        setItem: (key: string, value: string) => stored.set(key, value),
        removeItem: (key: string) => stored.delete(key),
    });
    localStorage.clear();
    URL.createObjectURL = vi.fn().mockReturnValue("blob:owned");
    URL.revokeObjectURL = vi.fn();
    calls.health.mockResolvedValue({ enabled: true, mode: "live", kieConfigured: true });
    calls.intake.mockImplementation(async (_workspace, input) => ({
        project: { ...project(), budget: { policy: input.metadata.budget } },
    }));
    calls.project.mockResolvedValue(project("compiled"));
    calls.compile.mockResolvedValue({
        success: true,
        projectId: "owned",
        revision: 2,
        schemaVersion: 2,
        renderPlan: {
            fps: 24,
            provider: "kie",
            groupingPolicy: "fixed_provider_windows",
            units: [],
        },
        sceneMap: { scenes: [], sceneCount: 0 },
        warnings: [],
        inputSummary: { targetDuration: 8 },
    });
});
afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
});

async function prepared() {
    const hook = renderHook(() => useRemakeStudio("workspace", "account"), { wrapper });
    await waitFor(() => expect(hook.result.current.health.data?.enabled).toBe(true));
    act(() => {
        hook.result.current.onVideo(new File(["source"], "source.mp4", { type: "video/mp4" }));
        hook.result.current.onImages([new File(["product"], "product.png", { type: "image/png" })]);
        hook.result.current.onSourceMetadata(20);
        hook.result.current.onDuration(8);
    });
    return hook;
}

describe("owned intake studio lifecycle", () => {
    it("requires media rights before the first analysis", async () => {
        const hook = await prepared();
        expect(hook.result.current.canAnalyze).toBe(false);
        await act(() => hook.result.current.analyze());
        expect(calls.intake).not.toHaveBeenCalled();
        expect(calls.compile).not.toHaveBeenCalled();
    });

    it("creates and remembers intake before compile and sends only its owned identity", async () => {
        const hook = await prepared();
        act(() => {
            hook.result.current.onRequirementsChange(requirements);
            hook.result.current.onRightsChange(rights);
            hook.result.current.onBudgetChange(budget);
        });
        await waitFor(() => expect(hook.result.current.canAnalyze).toBe(true));
        await act(() => hook.result.current.analyze());
        expect(calls.intake).toHaveBeenCalledTimes(1);
        expect(calls.intake.mock.invocationCallOrder[0]).toBeLessThan(
            calls.compile.mock.invocationCallOrder[0],
        );
        expect(hook.result.current.project?.id).toBe("owned");
        expect(localStorage.getItem("remake-project:account:workspace")).toBeNull();
        expect(calls.compile).toHaveBeenCalledWith(
            "workspace",
            expect.objectContaining({ projectId: "owned", expectedRevision: 1 }),
        );
        expect(calls.compile.mock.calls[0][1].referenceVideo).toBeUndefined();
        expect(calls.compile.mock.calls[0][1].productImage).toBeUndefined();
        expect(hook.result.current.step).toBe("plan");
    });

    it("starts fresh instead of reopening an old intake or device draft", async () => {
        localStorage.setItem("remake-project:account:workspace", "owned");
        calls.project.mockResolvedValue(project());
        calls.readDraft.mockRejectedValue(new Error("IndexedDB is unavailable"));
        const hook = renderHook(() => useRemakeStudio("workspace", "account"), { wrapper });
        await waitFor(() => expect(hook.result.current.health.data?.enabled).toBe(true));
        expect(hook.result.current.project).toBeNull();
        expect(hook.result.current.compiled).toBeNull();
        expect(hook.result.current.step).toBe("prepare");
        expect(calls.readDraft).not.toHaveBeenCalled();
        expect(calls.saveDraft).not.toHaveBeenCalled();
        expect(calls.compile).not.toHaveBeenCalled();
        expect(calls.intake).not.toHaveBeenCalled();
    });

    it("requires recompiling changed requirements and never generates from unsaved context", async () => {
        const hook = await prepared();
        act(() => {
            hook.result.current.onRequirementsChange(requirements);
            hook.result.current.onRightsChange(rights);
            hook.result.current.onBudgetChange(budget);
        });
        await act(() => hook.result.current.analyze());
        act(() =>
            hook.result.current.onRequirementsChange({
                ...requirements,
                keep: ["New required action"],
            }),
        );
        expect(hook.result.current.sourcePlanDirty).toBe(true);
        await act(() => hook.result.current.generate());
        expect(calls.render).not.toHaveBeenCalled();
    });

    it.each(["language", "prompt", "description"] as const)(
        "changes analysis identity when %s changes after a rejected analysis",
        async (field) => {
            const hook = await prepared();
            act(() => {
                hook.result.current.onRequirementsChange(requirements);
                hook.result.current.onRightsChange(rights);
                hook.result.current.onBudgetChange(budget);
            });
            calls.compile.mockRejectedValueOnce(
                new ApiError("SMART_REMAKE_SOURCE_INVALID", "Analysis rejected", 422),
            );
            await act(() => hook.result.current.analyze());
            const firstKey = calls.compile.mock.calls[0][1].idempotencyKey;
            act(() => {
                if (field === "language") hook.result.current.onLanguage("English");
                else if (field === "prompt") hook.result.current.onBrief("Different instruction");
                else hook.result.current.onDescription("Different description");
            });
            await act(() => hook.result.current.analyze());
            expect(calls.intake).toHaveBeenCalledTimes(1);
            expect(calls.compile).toHaveBeenCalledTimes(2);
            expect(calls.compile.mock.calls[1][1].idempotencyKey).not.toBe(firstKey);
        },
    );
});

describe("analysis retry feedback", () => {
    it("hides the previous attempt while retrying and keeps a new rejection visible", async () => {
        const hook = await prepared();
        act(() => {
            hook.result.current.onRequirementsChange(requirements);
            hook.result.current.onRightsChange(rights);
        });
        calls.intake.mockResolvedValueOnce({
            project: {
                ...project(),
                budget: { policy: { mode: "unlimited" } },
                lastOperation: {
                    id: "previous-compile",
                    status: "failed",
                    errorCode: "SMART_REMAKE_TIMELINE_CUTS_INVALID",
                },
            },
        });
        let rejectCompile!: (error: ApiError) => void;
        calls.compile.mockImplementationOnce(
            () =>
                new Promise((_resolve, reject) => {
                    rejectCompile = reject;
                }),
        );
        expect(hook.result.current.notice).not.toBe("");
        let request!: Promise<unknown>;
        act(() => {
            request = hook.result.current.analyze();
        });
        await waitFor(() => expect(calls.compile).toHaveBeenCalledTimes(1));
        expect(hook.result.current.project?.lastOperation?.id).toBe("previous-compile");
        expect(hook.result.current.busy).toBe("analyze");
        expect(hook.result.current.error).toBeNull();
        expect(hook.result.current.notice).toBe("");
        await act(async () => {
            rejectCompile(
                new ApiError("CURRENT_RETRY_ERROR", "Current analysis was rejected", 400),
            );
            await request;
        });
        expect(hook.result.current.busy).toBeNull();
        expect(hook.result.current.error).toBe("Current analysis was rejected");
        expect(hook.result.current.notice).toBe("");
    });
});

describe("analysis progress while compile is pending", () => {
    async function authorized() {
        const hook = await prepared();
        act(() => {
            hook.result.current.onRequirementsChange(requirements);
            hook.result.current.onRightsChange(rights);
        });
        return hook;
    }
    function checkpoint(status: "running" | "completed" | "failed" = "running") {
        return {
            ...project(status === "completed" ? "compiled" : "intake"),
            revision: status === "completed" ? 7 : 1,
            ...(status === "completed"
                ? { expectationsHash: "a".repeat(64), expectationsVersion: 1 }
                : {}),
            analysisProgress: {
                schemaVersion: 1 as const,
                operationId: "compile-operation",
                requestKey: calls.compile.mock.calls.at(-1)?.[1].idempotencyKey,
                status,
                stage: status === "running" ? ("resolving_scenes" as const) : status,
                startedAt: "2026-11-26T08:30:00Z",
                updatedAt: "2026-11-26T08:30:10Z",
                sourceDurationSeconds: 30,
                sceneCount: 12,
                scenes: [{ index: 0, startSecond: 0, endSecond: 2.5, action: "Lift the product" }],
            },
        };
    }
    it("reads actual scene checkpoints before compile returns without replacing the project", async () => {
        const hook = await authorized();
        let finish!: (value: unknown) => void;
        calls.compile.mockImplementationOnce(
            () =>
                new Promise((resolve) => {
                    finish = resolve;
                }),
        );
        calls.project.mockImplementation(async () => checkpoint());
        let request!: Promise<unknown>;
        act(() => {
            request = hook.result.current.analyze();
        });
        await waitFor(() => expect(hook.result.current.analysisProgress?.sceneCount).toBe(12));
        expect(hook.result.current.busy).toBe("analyze");
        expect(hook.result.current.analysisStartedAt).toEqual(expect.any(Number));
        expect(hook.result.current.project?.revision).toBe(1);
        expect(hook.result.current.step).toBe("prepare");
        calls.project.mockResolvedValue(checkpoint("completed"));
        await act(async () => {
            finish({
                success: true,
                projectId: "owned",
                revision: 7,
                schemaVersion: 2,
                renderPlan: {
                    fps: 24,
                    provider: "kie",
                    groupingPolicy: "fixed_provider_windows",
                    units: [],
                },
                sceneMap: { scenes: [], sceneCount: 0 },
                warnings: [],
                inputSummary: { targetDuration: 8 },
            });
            await request;
        });
        expect(hook.result.current.step).toBe("plan");
        expect(hook.result.current.project?.revision).toBe(7);
        expect(hook.result.current.analysisProgress).toBeNull();
        expect(calls.compile).toHaveBeenCalledTimes(1);
    });
    it("recovers an interrupted compile through GET without sending another analysis", async () => {
        const hook = await authorized();
        let fail!: (cause: Error) => void;
        calls.compile.mockImplementationOnce(
            () =>
                new Promise((_resolve, reject) => {
                    fail = reject;
                }),
        );
        calls.project.mockImplementation(async () => checkpoint());
        let request!: Promise<unknown>;
        act(() => {
            request = hook.result.current.analyze();
        });
        await waitFor(() => expect(hook.result.current.analysisProgress?.sceneCount).toBe(12));
        await act(async () => {
            fail(new Error("Connection timed out"));
            await request;
        });
        expect(hook.result.current.analysisUnresolved).toBe(true);
        await act(() => hook.result.current.analyze());
        expect(calls.compile).toHaveBeenCalledTimes(1);
        calls.project.mockResolvedValue(checkpoint("completed"));
        await act(() => hook.result.current.checkAnalysisStatus());
        await waitFor(() => expect(hook.result.current.step).toBe("plan"));
        expect(hook.result.current.analysisUnresolved).toBe(false);
        expect(hook.result.current.project?.revision).toBe(7);
        expect(calls.compile).toHaveBeenCalledTimes(1);
    });
    it("settles an explicit validation rejection instead of keeping a phantom analysis pending", async () => {
        const hook = await authorized();
        calls.compile.mockRejectedValueOnce(
            new ApiError("SMART_REMAKE_SOURCE_INVALID", "Choose another video", 400),
        );
        await act(() => hook.result.current.analyze());
        expect(hook.result.current.analysisUnresolved).toBe(false);
        expect(hook.result.current.busy).toBeNull();
        expect(hook.result.current.step).toBe("prepare");
    });
    it("finishes from a proved GET result even if the compile POST transport never settles", async () => {
        const hook = await authorized();
        calls.compile.mockReturnValueOnce(new Promise(() => {}));
        calls.project.mockImplementation(async () => checkpoint("completed"));
        let request!: Promise<unknown>;
        act(() => {
            request = hook.result.current.analyze();
        });
        await waitFor(() => expect(hook.result.current.step).toBe("plan"));
        await request;
        expect(hook.result.current.busy).toBeNull();
        expect(hook.result.current.compiled?.revision).toBe(7);
        expect(hook.result.current.analysisUnresolved).toBe(false);
        expect(calls.compile).toHaveBeenCalledTimes(1);
    });
    it("keeps a successful script usable when its final project refresh hangs", async () => {
        const hook = await authorized();
        calls.project.mockReturnValue(new Promise(() => {}));
        vi.useFakeTimers();
        try {
            let request!: Promise<unknown>;
            act(() => {
                request = hook.result.current.analyze();
            });
            await act(async () => {
                await vi.advanceTimersByTimeAsync(20);
            });
            expect(hook.result.current.busy).toBe("analyze");
            expect(hook.result.current.compiled?.revision).toBe(2);
            await act(async () => {
                await vi.advanceTimersByTimeAsync(15000);
            });
            expect(hook.result.current.busy).toBeNull();
            expect(hook.result.current.step).toBe("plan");
            expect(hook.result.current.error).toBeNull();
            await request;
            expect(calls.compile).toHaveBeenCalledTimes(1);
        } finally {
            vi.useRealTimers();
        }
    });
    it("ignores a late POST response after a matching GET has completed the script", async () => {
        const hook = await authorized();
        let finish!: (value: unknown) => void;
        calls.compile.mockImplementationOnce(
            () =>
                new Promise((resolve) => {
                    finish = resolve;
                }),
        );
        calls.project.mockImplementation(async () => checkpoint("completed"));
        act(() => {
            void hook.result.current.analyze();
        });
        await waitFor(() => expect(hook.result.current.compiled?.revision).toBe(7));
        await act(async () =>
            finish({
                success: true,
                projectId: "owned",
                revision: 1,
                sceneMap: { scenes: [], sceneCount: 0 },
                warnings: [],
                inputSummary: { targetDuration: 8 },
            }),
        );
        expect(hook.result.current.compiled?.revision).toBe(7);
        expect(hook.result.current.busy).toBeNull();
        expect(calls.compile).toHaveBeenCalledTimes(1);
    });
    it("unlocks with an error when GET proves failure while the POST never settles", async () => {
        const hook = await authorized();
        calls.compile.mockReturnValueOnce(new Promise(() => {}));
        calls.project.mockImplementation(async () => ({
            ...checkpoint("failed"),
            schemaVersion: 1,
        }));
        let request!: Promise<unknown>;
        act(() => {
            request = hook.result.current.analyze();
        });
        await waitFor(() => expect(hook.result.current.error).toBeTruthy());
        await request;
        expect(hook.result.current.busy).toBeNull();
        expect(hook.result.current.analysisUnresolved).toBe(false);
        expect(hook.result.current.step).toBe("prepare");
        expect(hook.result.current.compiled).toBeNull();
        expect(hook.result.current.notice).not.toContain("sẵn sàng");
        expect(calls.compile).toHaveBeenCalledTimes(1);
    });
    it("keeps the proved failure when a stale POST response arrives later", async () => {
        const hook = await authorized();
        let finish!: (value: unknown) => void;
        calls.compile.mockImplementationOnce(
            () =>
                new Promise((resolve) => {
                    finish = resolve;
                }),
        );
        calls.project.mockImplementation(async () => checkpoint("failed"));
        act(() => {
            void hook.result.current.analyze();
        });
        await waitFor(() => expect(hook.result.current.error).toBeTruthy());
        await act(async () =>
            finish({
                success: true,
                projectId: "owned",
                revision: 7,
                sceneMap: { scenes: [], sceneCount: 0 },
                warnings: [],
                inputSummary: { targetDuration: 8 },
            }),
        );
        expect(hook.result.current.error).toBeTruthy();
        expect(hook.result.current.step).toBe("prepare");
        expect(hook.result.current.compiled).toBeNull();
        expect(calls.compile).toHaveBeenCalledTimes(1);
    });
    it("settles a restored server analysis when its read-only checkpoint fails", async () => {
        const running = {
            ...checkpoint(),
            pendingOperation: {
                id: "compile-operation",
                kind: "compile",
                status: "running" as const,
                needsReconciliation: false,
            },
        };
        running.analysisProgress.requestKey = "restored-key";
        const failed = checkpoint("failed");
        failed.analysisProgress.requestKey = "restored-key";
        localStorage.setItem("remake-project:account:workspace", "owned");
        calls.project.mockResolvedValueOnce(running).mockResolvedValue(failed);
        const hook = renderHook(() => useRemakeStudio("workspace", "account"), { wrapper });
        await waitFor(() => expect(hook.result.current.error).toBeTruthy());
        expect(hook.result.current.busy).toBeNull();
        expect(hook.result.current.analysisUnresolved).toBe(false);
        expect(hook.result.current.project?.pendingOperation).toBeUndefined();
        expect(hook.result.current.compiled).toBeNull();
        expect(calls.compile).not.toHaveBeenCalled();
    });
    it("restores an active compile without POST and follows a newer render from another tab", async () => {
        const running = {
            ...checkpoint(),
            pendingOperation: {
                id: "compile-operation",
                kind: "compile",
                status: "running" as const,
                needsReconciliation: false,
            },
        };
        running.analysisProgress.requestKey = "restored-key";
        const rendering = {
            ...project("compiled"),
            revision: 8,
            status: "rendering" as const,
            pendingOperation: {
                id: "new-render",
                kind: "render",
                status: "running" as const,
                needsReconciliation: false,
            },
        };
        localStorage.setItem("remake-project:account:workspace", "owned");
        calls.project.mockResolvedValueOnce(running).mockResolvedValue(rendering);
        const hook = renderHook(() => useRemakeStudio("workspace", "account"), { wrapper });
        await waitFor(() =>
            expect(hook.result.current.project?.pendingOperation?.id).toBe("new-render"),
        );
        expect(hook.result.current.analysisUnresolved).toBe(false);
        expect(hook.result.current.step).toBe("result");
        expect(calls.compile).not.toHaveBeenCalled();
        expect(calls.intake).not.toHaveBeenCalled();
    });
});

describe("media rights confirmation lifecycle", () => {
    it("can open rights confirmation with media and no budget form but cannot call AI before consent", async () => {
        const hook = await prepared();
        expect(hook.result.current.canConfirmRights).toBe(true);
        act(() => hook.result.current.onBudgetChange(budget));
        expect(hook.result.current.canConfirmRights).toBe(true);
        expect(hook.result.current.canAnalyze).toBe(false);
        await act(() => hook.result.current.analyze());
        expect(calls.intake).not.toHaveBeenCalled();
        expect(calls.compile).not.toHaveBeenCalled();
        act(() =>
            hook.result.current.onRightsChange(
                confirmRemakeMediaRights(hook.result.current.rights),
            ),
        );
        expect(hook.result.current.canAnalyze).toBe(true);
        expect(calls.compile).not.toHaveBeenCalled();
    });
    it.each(["video", "images", "remove", "primary", "character"])(
        "invalidates receipt after %s media changes",
        async (mutation) => {
            const hook = await prepared();
            act(() => {
                hook.result.current.onBudgetChange(budget);
                hook.result.current.onRightsChange(
                    confirmRemakeMediaRights(hook.result.current.rights),
                );
            });
            expect(hasCurrentRemakeRightsAttestation(hook.result.current.rights)).toBe(true);
            act(() => {
                const file = new File(["new"], "new.png", { type: "image/png" });
                if (mutation === "video")
                    hook.result.current.onVideo(
                        new File(["new"], "new.mp4", { type: "video/mp4" }),
                    );
                if (mutation === "images") hook.result.current.onImages([file]);
                if (mutation === "remove") hook.result.current.onRemoveImage(0);
                if (mutation === "primary") hook.result.current.onPrimaryChange(1);
                if (mutation === "character") hook.result.current.onCharacterChange(file);
            });
            expect(hasCurrentRemakeRightsAttestation(hook.result.current.rights)).toBe(false);
            expect(hook.result.current.canAnalyze).toBe(false);
            expect(calls.compile).not.toHaveBeenCalled();
        },
    );
    it.each(["sample", "link"])(
        "invalidates receipt when %s imports replace media",
        async (mutation) => {
            const hook = await prepared();
            act(() =>
                hook.result.current.onRightsChange(
                    confirmRemakeMediaRights(hook.result.current.rights),
                ),
            );
            if (mutation === "sample") {
                vi.stubGlobal(
                    "fetch",
                    vi.fn().mockImplementation((path: string) =>
                        Promise.resolve({
                            ok: true,
                            blob: () =>
                                Promise.resolve(
                                    new Blob(["media"], {
                                        type: path.endsWith("mp4") ? "video/mp4" : "image/webp",
                                    }),
                                ),
                        }),
                    ),
                );
                await act(() => hook.result.current.loadSample());
            } else {
                vi.stubGlobal(
                    "fetch",
                    vi.fn().mockResolvedValue({
                        ok: true,
                        blob: async () => new Blob(["product"], { type: "image/png" }),
                    }),
                );
                calls.crawl.mockResolvedValue({
                    source_url: "https://example.com/item",
                    product_draft: {
                        name: "Product",
                        metadata_json: { image_url: "https://example.com/item.png" },
                    },
                    crawl: {},
                });
                act(() => hook.result.current.onLinkChange("https://example.com/item"));
                await act(() => hook.result.current.importLink());
            }
            expect(hasCurrentRemakeRightsAttestation(hook.result.current.rights)).toBe(false);
            expect(calls.compile).not.toHaveBeenCalled();
        },
    );
    it("does not change media or its receipt while an operation holds the running lock", async () => {
        const hook = await prepared();
        act(() =>
            hook.result.current.onRightsChange(
                confirmRemakeMediaRights(hook.result.current.rights),
            ),
        );
        let finish!: (value: unknown) => void;
        calls.crawl.mockImplementation(
            () =>
                new Promise((resolve) => {
                    finish = resolve;
                }),
        );
        act(() => hook.result.current.onLinkChange("https://example.com/item"));
        let pending!: Promise<void>;
        act(() => {
            pending = hook.result.current.importLink();
        });
        expect(hook.result.current.busy).toBe("link");
        const oldVideo = hook.result.current.video;
        act(() => {
            hook.result.current.onVideo(new File(["new"], "new.mp4", { type: "video/mp4" }));
            hook.result.current.onImages([new File(["new"], "new.png", { type: "image/png" })]);
            hook.result.current.onCharacterChange(
                new File(["new"], "new.png", { type: "image/png" }),
            );
            hook.result.current.onRemoveImage(0);
            hook.result.current.onPrimaryChange(1);
        });
        expect(hook.result.current.video).toBe(oldVideo);
        expect(hook.result.current.primaryIndex).toBe(0);
        expect(hook.result.current.characterFile).toBeNull();
        expect(hasCurrentRemakeRightsAttestation(hook.result.current.rights)).toBe(true);
        await act(async () => {
            finish({
                source_url: "https://example.com/item",
                product_draft: {
                    name: "Product",
                    metadata_json: { image_url: "https://example.com/item.png" },
                },
                crawl: {},
            });
            await pending;
        });
    });
    it("retains consent when invalid media is rejected", async () => {
        const hook = await prepared();
        act(() =>
            hook.result.current.onRightsChange(
                confirmRemakeMediaRights(hook.result.current.rights),
            ),
        );
        act(() =>
            hook.result.current.onImages([
                new File(["wrong"], "wrong.exe", { type: "application/octet-stream" }),
            ]),
        );
        expect(hasCurrentRemakeRightsAttestation(hook.result.current.rights)).toBe(true);
    });
});

describe("action-gated studio lifecycle", () => {
    it("runs once with current media rights and no budget form or grant confirmation", async () => {
        const hook = await prepared();
        act(() => hook.result.current.onRightsChange(confirmRemakeMediaRights(rights)));
        await act(() => hook.result.current.requestAction("analyze"));
        expect(hook.result.current.pendingAction).toBeNull();
        expect(calls.compile).toHaveBeenCalledTimes(1);
        expect(calls.intake.mock.calls[0][1].metadata.budget).toEqual({ mode: "unlimited" });
        expect(calls.preflight.mock.calls[0][1].budgetMode).toBe("unlimited");
    });
    let owned: SmartRemakeProject;
    const proposal = (action: string, revision?: number) => ({
        action,
        contextHash: `context-${revision ?? "new"}`,
        mode: "fixture",
        scope: { targetDuration: 8, sceneCount: 1, groupCount: 1, imageCount: 1 },
        calls: { analysis: 3, image: 0, video: 0, inspection: 0, total: 3 },
        budget: {
            knownActualUsd: "0",
            reservedUsd: "0",
            exposureUsd: "0",
            additionalReservationUsd: "1.50",
            minimumCapUsd: "1.50",
            minimumMaxAttempts: 3,
            minimumDurationSeconds: 1800,
            recommended: { capUsd: "1.50", maxAttempts: 10, maxDurationSeconds: 2000 },
        },
        blockers: [],
    });
    beforeEach(() => {
        owned = project();
        calls.preflight.mockImplementation(async (_workspace, input) =>
            proposal(input.action, input.expectedRevision),
        );
        calls.intake.mockImplementation(async (_workspace, input) => {
            owned = {
                ...project(),
                targetDuration: input.metadata.targetDuration,
                requirements: input.metadata.requirements,
                rights: input.metadata.rights,
                budget: { policy: input.metadata.budget },
            };
            return { project: owned };
        });
        calls.update.mockImplementation(async (_workspace, _id, field, input) => {
            owned = {
                ...owned,
                revision: input.expectedRevision + 1,
                ...(field === "budget"
                    ? { budget: { policy: input.budget } }
                    : { [field]: input[field] }),
            };
            return { project: owned };
        });
        calls.compile.mockImplementation(async () => {
            owned = {
                ...owned,
                revision: owned.revision + 1,
                phase: "compiled",
                renderPlan: {
                    fps: 24,
                    provider: "kie",
                    groupingPolicy: "fixed_provider_windows",
                    units: [],
                },
            };
            return {
                success: true,
                schemaVersion: 2,
                renderPlan: owned.renderPlan,
                expectationsVersion: 1,
                expectationsHash: "a".repeat(64),
                projectId: owned.id,
                revision: owned.revision,
                sceneMap: { scenes: [], sceneCount: 0 },
                warnings: [],
                inputSummary: { targetDuration: 8 },
            };
        });
        calls.project.mockImplementation(async () => owned);
        calls.render.mockImplementation(async () => ({ status: "running", repairProject: owned }));
        calls.repair.mockImplementation(async () => ({
            project: owned,
            status: "running",
            operationId: "repair",
        }));
        calls.inspect.mockImplementation(async () => ({
            project: owned,
            status: "running",
            operationId: "inspect",
        }));
    });
    async function inSessionProject(snapshot = owned) {
        const hook = await prepared();
        act(() => {
            hook.result.current.onRequirementsChange(snapshot.requirements ?? requirements);
            hook.result.current.onRightsChange(snapshot.rights ?? rights);
            hook.result.current.onSourceMetadata(
                (snapshot.sourceSceneMap?.sourceFrameCount ?? 192) / 24,
            );
            hook.result.current.onDuration(snapshot.targetDuration);
        });
        calls.intake.mockResolvedValueOnce({
            project: { ...snapshot, phase: "intake", budget: { policy: { mode: "unlimited" } } },
        });
        calls.compile.mockImplementationOnce(async () => {
            owned = snapshot;
            return restoreTimelineCompile(snapshot)!;
        });
        await act(() => hook.result.current.analyze());
        await waitFor(() => expect(hook.result.current.project?.id).toBe(snapshot.id));
        expect(hook.result.current.compiled).not.toBeNull();
        vi.clearAllMocks();
        return hook;
    }
    async function readyForInitialRender() {
        owned = {
            ...project("compiled"),
            revision: 4,
            rights: confirmRemakeMediaRights(rights),
            budget: { policy: { mode: "unlimited" } },
            expectationsVersion: 1,
            expectationsHash: "a".repeat(64),
            sourceSceneMap: {
                fps: 24,
                sourceStartFrame: 0,
                sourceFrameCount: 192,
                timingMode: "fit_target",
                scenes: [
                    { id: "source-scene", startFrame: 0, endFrame: 192, targetDurationFrames: 192 },
                ],
            },
            renderPlan: {
                fps: 24,
                provider: "kie",
                groupingPolicy: "fixed_provider_windows",
                units: [
                    {
                        id: "scene",
                        sourceSceneId: "source-scene",
                        sceneIndex: 0,
                        rawDurationFrames: 192,
                        targetDurationFrames: 192,
                        prompt: "p",
                        imagePrompt: "i",
                        videoPrompt: "v",
                    },
                ],
            },
            scenes: [
                {
                    id: "scene",
                    index: 0,
                    activeVersionId: null,
                    versions: [],
                    prompt: "p",
                    imagePrompt: "i",
                    videoPrompt: "v",
                    startSecond: 0,
                    durationSeconds: 8,
                },
            ],
        };
        return inSessionProject();
    }
    it.each([false, true])(
        "keeps session media after failed reanalysis and explicitly retries once with requirements edited=%s",
        async (editRequirements) => {
            const hook = await readyForInitialRender();
            const video = hook.result.current.video;
            const imageUrls = hook.result.current.productUrls;
            const savedScript = hook.result.current.compiled;
            calls.compile.mockImplementationOnce(async (_workspace, input) => {
                owned = {
                    ...owned,
                    analysisProgress: {
                        schemaVersion: 1,
                        operationId: "failed-reanalysis",
                        requestKey: input.idempotencyKey,
                        status: "failed",
                        stage: "failed",
                        startedAt: "2026-11-26T10:56:51Z",
                        updatedAt: "2026-11-26T10:59:15Z",
                        errorCode: "SMART_REMAKE_MODEL_ATTEMPT_UNCERTAIN",
                        retryDisposition: "new_analysis",
                        scenes: [],
                    },
                };
                throw new ApiError(
                    "SMART_REMAKE_MODEL_ATTEMPT_UNCERTAIN",
                    "Response unusable",
                    409,
                );
            });
            await act(() => hook.result.current.analyze());
            expect(hook.result.current.step).toBe("prepare");
            expect(hook.result.current.project?.analysisProgress?.retryDisposition).toBe(
                "new_analysis",
            );
            expect(hook.result.current.video).toBe(video);
            expect(hook.result.current.productUrls).toEqual(imageUrls);
            expect(hook.result.current.compiled).toBe(savedScript);
            expect(calls.compile).toHaveBeenCalledTimes(1);
            const failedKey = calls.compile.mock.calls[0][1].idempotencyKey;
            act(() => hook.result.current.viewSavedScript());
            expect(hook.result.current.step).toBe("plan");
            expect(hook.result.current.notice).toContain("kịch bản đã lưu");
            expect(calls.compile).toHaveBeenCalledTimes(1);
            if (editRequirements) {
                act(() =>
                    hook.result.current.onRequirementsChange({
                        ...requirements,
                        keep: ["Show the complete product"],
                    }),
                );
                calls.update.mockImplementationOnce(async (_workspace, _id, field, input) => {
                    owned = {
                        ...owned,
                        revision: input.expectedRevision + 1,
                        analysisProgress: undefined,
                        [field]: input[field],
                    };
                    return { project: owned };
                });
            }
            calls.compile.mockImplementationOnce(async () => {
                owned = { ...owned, revision: owned.revision + 1, analysisProgress: undefined };
                return restoreTimelineCompile(owned)!;
            });
            await act(async () => {
                await Promise.all([
                    hook.result.current.requestAction("reanalyze"),
                    hook.result.current.requestAction("reanalyze"),
                ]);
            });
            expect(calls.compile).toHaveBeenCalledTimes(2);
            expect(calls.compile.mock.calls[1][1].idempotencyKey).not.toBe(failedKey);
            expect(hook.result.current.step).toBe("plan");
            expect(calls.intake).not.toHaveBeenCalled();
            expect(calls.readDraft).not.toHaveBeenCalled();
            expect(calls.saveDraft).not.toHaveBeenCalled();
        },
    );
    it("does not reopen a terminal failed analysis as a project draft after reload", async () => {
        owned = {
            ...project("compiled"),
            analysisProgress: {
                schemaVersion: 1,
                operationId: "failed-reanalysis",
                requestKey: "old-request",
                status: "failed",
                stage: "failed",
                startedAt: "2026-11-26T10:56:51Z",
                updatedAt: "2026-11-26T10:59:15Z",
                retryDisposition: "new_analysis",
                scenes: [],
            },
        };
        localStorage.setItem("remake-project:account:workspace", owned.id);
        const hook = renderHook(() => useRemakeStudio("workspace", "account"), { wrapper });
        await waitFor(() => expect(hook.result.current.health.data?.enabled).toBe(true));
        await waitFor(() => expect(hook.result.current.checkingSubmissionStatus).toBe(false));
        expect(hook.result.current.project).toBeNull();
        expect(hook.result.current.compiled).toBeNull();
        expect(hook.result.current.step).toBe("prepare");
        expect(localStorage.getItem("remake-project:account:workspace")).toBeNull();
        expect(calls.readDraft).not.toHaveBeenCalled();
        expect(calls.compile).not.toHaveBeenCalled();
    });
    it("keeps an analysis submission marker fenced when GET has no operation receipt yet", async () => {
        const marker = JSON.stringify({ projectId: "owned", requestKey: "submitted-analysis" });
        localStorage.setItem("remake-project:account:workspace", marker);
        owned = project();
        const hook = renderHook(() => useRemakeStudio("workspace", "account"), { wrapper });
        await waitFor(() => expect(calls.project).toHaveBeenCalled());
        await waitFor(() => expect(hook.result.current.checkingSubmissionStatus).toBe(false));
        expect(hook.result.current.submissionStatusError).toBeTruthy();
        expect(localStorage.getItem("remake-project:account:workspace")).toBe(marker);
        await act(() => hook.result.current.checkSubmissionStatus());
        expect(calls.project).toHaveBeenCalledWith("workspace", "owned");
        expect(calls.compile).not.toHaveBeenCalled();
        expect(calls.intake).not.toHaveBeenCalled();
        expect(calls.preflight).not.toHaveBeenCalled();
    });
    it("keeps a submitted receipt on GET failure and checks it without saving a draft or submitting AI", async () => {
        localStorage.setItem("remake-project:account:workspace", "owned");
        calls.project.mockRejectedValueOnce(new Error("Network unavailable"));
        const hook = renderHook(() => useRemakeStudio("workspace", "account"), { wrapper });
        await waitFor(() => expect(hook.result.current.submissionStatusError).toBeTruthy());
        act(() => {
            hook.result.current.onVideo(new File(["new"], "source.mp4", { type: "video/mp4" }));
            hook.result.current.onImages([new File(["new"], "product.png", { type: "image/png" })]);
            hook.result.current.onSourceMetadata(8);
        });
        expect(hook.result.current.video?.name).toBe("source.mp4");
        expect(localStorage.getItem("remake-project:account:workspace")).toBe("owned");
        owned = {
            ...project(),
            pendingOperation: { id: "pending", status: "running", needsReconciliation: false },
        };
        await act(() => hook.result.current.checkSubmissionStatus());
        expect(hook.result.current.project?.pendingOperation?.id).toBe("pending");
        expect(hook.result.current.submissionStatusError).toBeNull();
        expect(calls.compile).not.toHaveBeenCalled();
        expect(calls.intake).not.toHaveBeenCalled();
        expect(calls.readDraft).not.toHaveBeenCalled();
        expect(calls.saveDraft).not.toHaveBeenCalled();
    });
    it("retries confirmed failed initial generation through existing preflight using a fresh key and current revision", async () => {
        const hook = await readyForInitialRender();
        calls.render.mockRejectedValueOnce(new Error("Response lost"));
        await act(() => hook.result.current.generate());
        const previousKey = calls.render.mock.calls[0][1].idempotencyKey;
        owned = {
            ...owned,
            revision: 7,
            generationRecovery: {
                kind: "retry_initial_render",
                stage: "image",
                errorCode: "OPENAI_IMAGE_CREDITS_EXHAUSTED",
                requestKey: previousKey,
            },
        };
        await act(() => hook.result.current.refreshProject());
        await act(() => hook.result.current.requestAction("render"));
        expect(calls.preflight).toHaveBeenCalledWith(
            "workspace",
            expect.objectContaining({ action: "render", expectedRevision: 7 }),
        );
        expect(calls.render).toHaveBeenCalledTimes(2);
        expect(calls.render.mock.calls[1][1].idempotencyKey).not.toBe(previousKey);
        expect(calls.render.mock.calls[1][1].compileResult.revision).toBe(7);
        expect(calls.compile).not.toHaveBeenCalled();
        expect(calls.repair).not.toHaveBeenCalled();
    });
    it("does not create a replacement request when the held initial render outcome is still unknown", async () => {
        const hook = await readyForInitialRender();
        calls.render.mockRejectedValueOnce(new Error("Response lost"));
        await act(() => hook.result.current.generate());
        owned = {
            ...owned,
            revision: 7,
            lastOperation: { id: "unknown", status: "failed", needsReconciliation: true },
        };
        await act(() => hook.result.current.refreshProject());
        await act(() => hook.result.current.generate());
        expect(calls.render).toHaveBeenCalledTimes(1);
        expect(hook.result.current.errorCode).toBe("SMART_REMAKE_OPERATION_UNRESOLVED");
    });
    it.each([null, "missing", "empty"])(
        "refuses repair with active version %s before preflight, markers or provider work",
        async (base) => {
            const hook = await readyForInitialRender();
            owned = {
                ...owned,
                scenes: [
                    {
                        ...owned.scenes[0],
                        activeVersionId: base,
                        versions:
                            base === "empty"
                                ? [
                                      {
                                          id: "empty",
                                          videoUrl: "",
                                      } as SmartRemakeProject["scenes"][number]["versions"][number],
                                  ]
                                : [],
                    },
                ],
            };
            await act(() => hook.result.current.refreshProject());
            const intent = {
                schemaVersion: 1 as const,
                issues: [],
                instruction: "Show the product clearly",
            };
            await act(() =>
                hook.result.current.requestAction("repair", {
                    sceneId: "scene",
                    repairIntent: intent,
                }),
            );
            await act(() => hook.result.current.repair("scene", intent));
            expect(hook.result.current.error).toBe(
                "Cảnh này chưa có clip để sửa. Tiếp tục tạo video trước.",
            );
            expect(hook.result.current.errorCode).toBe("SMART_REMAKE_BASE_VERSION_REQUIRED");
            expect(calls.preflight).not.toHaveBeenCalled();
            expect(calls.writeMarker).not.toHaveBeenCalled();
            expect(calls.repair).not.toHaveBeenCalled();
            expect(calls.render).not.toHaveBeenCalled();
        },
    );
    function confirmed(hook: Awaited<ReturnType<typeof prepared>>) {
        return {
            requirements: hook.result.current.requirements,
            rights: confirmRemakeMediaRights(hook.result.current.rights),
            budget: { mode: "unlimited" as const },
        };
    }
    it.each(["inspect", "render"] as const)(
        "continues %s on an exhausted in-session project without reopening it after reload",
        async (action) => {
            owned = {
                ...project("compiled"),
                rights: confirmRemakeMediaRights(rights),
                expectationsVersion: 1,
                expectationsHash: "a".repeat(64),
                sourceSceneMap: {
                    fps: 24,
                    sourceStartFrame: 0,
                    sourceFrameCount: 192,
                    timingMode: "fit_target",
                    scenes: [
                        {
                            id: "source",
                            startFrame: 0,
                            endFrame: 192,
                            targetDurationFrames: 192,
                            prompt: "master",
                            imagePrompt: "image",
                            videoPrompt: "action",
                        },
                    ],
                },
                renderPlan: {
                    fps: 24,
                    provider: "kie",
                    groupingPolicy: "fixed_provider_windows",
                    units: [
                        {
                            id: "scene",
                            sourceSceneId: "source",
                            sceneIndex: 0,
                            rawDurationFrames: 192,
                            targetDurationFrames: 192,
                            prompt: "master",
                            imagePrompt: "image",
                            videoPrompt: "action",
                        },
                    ],
                },
                budget: {
                    policy: { capUsd: "1.50", maxAttempts: 1, maxDurationSeconds: 1 },
                    actualUsd: "1.50",
                    attemptCount: 1,
                    startedAt: "2020-01-01T00:00:00Z",
                },
            };
            const hook = await inSessionProject();
            expect(hook.result.current.budget).toEqual({ mode: "unlimited" });
            act(() => hook.result.current.onRenderGroupBreaksChange([1, 2, 3]));
            expect(hook.result.current.renderGroupBreaks).toEqual([]);
            await act(() =>
                hook.result.current.requestAction(
                    action,
                    action === "inspect"
                        ? {
                              subject: { kind: "image", imageRole: "product" },
                          }
                        : {},
                ),
            );
            expect(hook.result.current.pendingAction).toBeNull();
            expect(calls.preflight.mock.calls[0][1].budgetMode).toBe("unlimited");
            expect(calls.update).toHaveBeenCalledWith(
                "workspace",
                "owned",
                "budget",
                expect.objectContaining({
                    expectedRevision: 1,
                    budget: { mode: "unlimited" },
                }),
            );
            const execution = action === "inspect" ? calls.inspect : calls.render;
            expect(calls.update.mock.invocationCallOrder[0]).toBeLessThan(
                execution.mock.invocationCallOrder[0],
            );
            expect(execution).toHaveBeenCalledTimes(1);
            if (action === "inspect")
                expect(execution.mock.calls[0].at(-1)).toMatchObject({ expectedRevision: 2 });
            else expect(execution.mock.calls[0][1].compileResult.revision).toBe(2);
            hook.unmount();
            const restored = renderHook(() => useRemakeStudio("workspace", "account"), { wrapper });
            await waitFor(() => expect(restored.result.current.health.data?.enabled).toBe(true));
            expect(restored.result.current.project).toBeNull();
            expect(restored.result.current.compiled).toBeNull();
            expect(restored.result.current.budget).toEqual({ mode: "unlimited" });
            expect(execution).toHaveBeenCalledTimes(1);
            expect(calls.update).toHaveBeenCalledTimes(1);
        },
    );
    it.each(["render", "repair"] as const)(
        "keeps an old fitted plan visible but requires an update before a new %s",
        async (action) => {
            owned = {
                ...project("compiled"),
                rights: confirmRemakeMediaRights(rights),
                expectationsVersion: 1,
                expectationsHash: "a".repeat(64),
                sourceSceneMap: {
                    fps: 24,
                    sourceStartFrame: 0,
                    sourceFrameCount: 192,
                    timingMode: "fit_target",
                    scenes: [
                        { id: "source", startFrame: 0, endFrame: 192, targetDurationFrames: 192 },
                    ],
                },
                renderPlan: { fps: 24, provider: "kie", units: [] },
                scenes: [
                    {
                        id: "scene",
                        index: 0,
                        activeVersionId: "version",
                        startSecond: 0,
                        durationSeconds: 8,
                        prompt: "master",
                        imagePrompt: "image",
                        videoPrompt: "motion",
                        versions: [existingClip],
                    },
                ],
            };
            const hook = await inSessionProject();
            await act(() =>
                hook.result.current.requestAction(
                    action,
                    action === "repair"
                        ? {
                              sceneId: "scene",
                              repairIntent: { schemaVersion: 1, issues: [], instruction: "" },
                          }
                        : {},
                ),
            );
            expect(hook.result.current.error).toContain("Cập nhật kịch bản");
            expect(hook.result.current.project?.id).toBe("owned");
            expect(hook.result.current.compiled).not.toBeNull();
            expect(hook.result.current.pendingAction).toBeNull();
            expect(calls.preflight).not.toHaveBeenCalled();
            expect(calls.render).not.toHaveBeenCalled();
            expect(calls.repair).not.toHaveBeenCalled();
            expect(calls.compile).not.toHaveBeenCalled();
        },
    );
    it("opens with unconfirmed rights, then cancels without uploading or saving", async () => {
        const hook = await prepared();
        await act(() => hook.result.current.requestAction("analyze"));
        expect(hook.result.current.pendingAction?.action).toBe("analyze");
        expect(hook.result.current.budget).toEqual({ mode: "unlimited" });
        expect(calls.intake).not.toHaveBeenCalled();
        expect(calls.update).not.toHaveBeenCalled();
        expect(calls.compile).not.toHaveBeenCalled();
        act(() => hook.result.current.cancelAction());
        expect(hook.result.current.rights.source.declared).toBe(false);
        expect(hook.result.current.video).not.toBeNull();
    });
    it("passes the confirmed snapshot through intake and compile exactly once despite double confirm", async () => {
        const hook = await prepared();
        await act(() => hook.result.current.requestAction("analyze"));
        const snapshot = confirmed(hook);
        await act(async () => {
            await Promise.all([
                hook.result.current.confirmAction(snapshot),
                hook.result.current.confirmAction(snapshot),
            ]);
        });
        expect(calls.intake).toHaveBeenCalledTimes(1);
        expect(calls.intake.mock.calls[0][1].metadata.budget).toEqual(snapshot.budget);
        expect(calls.intake.mock.calls[0][1].metadata.rights.attestation.accepted).toBe(true);
        expect(calls.compile).toHaveBeenCalledTimes(1);
        expect(hook.result.current.pendingAction).toBeNull();
        expect(hook.result.current.step).toBe("plan");
    });
    it("uses the returned context revision for render without recompiling metadata-only edits", async () => {
        const hook = await prepared();
        await act(() => hook.result.current.requestAction("analyze"));
        await act(() => hook.result.current.confirmAction(confirmed(hook)));
        const compiledRevision = hook.result.current.compiled!.revision!;
        act(() =>
            hook.result.current.onRightsChange({
                ...hook.result.current.rights,
                product: {
                    ...hook.result.current.rights.product,
                    evidenceNote: "Updated ownership evidence",
                },
            }),
        );
        await act(() => hook.result.current.requestAction("render"));
        expect(calls.compile).toHaveBeenCalledTimes(1);
        expect(calls.render).toHaveBeenCalledWith(
            "workspace",
            expect.objectContaining({
                compileResult: expect.objectContaining({ revision: compiledRevision + 1 }),
            }),
        );
        expect(calls.update).toHaveBeenCalledWith(
            "workspace",
            "owned",
            "rights",
            expect.objectContaining({
                expectedRevision: compiledRevision,
                rights: expect.objectContaining({
                    product: expect.objectContaining({
                        evidenceNote: "Updated ownership evidence",
                    }),
                }),
            }),
        );
    });
    it.each(["repair", "inspect"] as const)(
        "replaces a legacy grant and directly uses its owned revision for %s",
        async (action) => {
            owned = {
                ...project("compiled"),
                rights: confirmRemakeMediaRights(rights),
                scenes: [
                    {
                        id: "scene",
                        index: 0,
                        startSecond: 0,
                        durationSeconds: 8,
                        activeVersionId: "version",
                        prompt: "scene",
                        imagePrompt: "image",
                        videoPrompt: "action",
                        versions: [existingClip],
                    },
                ],
            };
            const hook = await inSessionProject();
            const args =
                action === "repair"
                    ? {
                          sceneId: "scene",
                          draft: { prompt: "scene", imagePrompt: "image", videoPrompt: "action" },
                      }
                    : {
                          subject: {
                              kind: "scene" as const,
                              sceneId: "scene",
                              versionId: "version",
                          },
                      };
            await act(() => hook.result.current.requestAction(action, args));
            const request = action === "repair" ? calls.repair : calls.inspect;
            expect(request).toHaveBeenCalledTimes(1);
            expect(request.mock.calls[0].at(-1)).toMatchObject({ expectedRevision: 2 });
            expect(hook.result.current.lastActionRepairCandidate).toBeNull();
        },
    );
    it("announces a completed confirmed repair candidate and opens comparison only on request", async () => {
        owned = {
            ...project("compiled"),
            rights: confirmRemakeMediaRights(rights),
            scenes: [
                {
                    id: "scene",
                    index: 0,
                    startSecond: 0,
                    durationSeconds: 8,
                    activeVersionId: "version",
                    prompt: "scene",
                    imagePrompt: "image",
                    videoPrompt: "action",
                    versions: [existingClip],
                },
            ],
        };
        calls.repair.mockImplementation(async () => ({
            project: {
                ...owned,
                scenes: [
                    {
                        ...owned.scenes[0],
                        versions: [{ id: "candidate", parentVersionId: "version" }],
                    },
                ],
            },
            status: "completed",
            operationId: "repair",
            candidateVersionId: "candidate",
        }));
        const hook = await inSessionProject();
        const args = {
            sceneId: "scene",
            draft: { prompt: "scene", imagePrompt: "image", videoPrompt: "action" },
        };
        await act(() => hook.result.current.requestAction("repair", args));
        expect(hook.result.current.lastActionRepairCandidate).toBeNull();
        expect(hook.result.current.outputNavigation).toBeNull();
        expect(hook.result.current.unreadRepairCandidate).toEqual({
            projectId: "owned",
            sceneId: "scene",
            versionId: "candidate",
        });
        expect(calls.repair).toHaveBeenCalledTimes(1);
        await act(() => hook.result.current.viewRepairCandidate());
        expect(hook.result.current.outputNavigation).toMatchObject({
            sceneId: "scene",
            view: "compare",
            versionId: "candidate",
        });
        act(() => hook.result.current.cancelAction());
        expect(calls.repair).toHaveBeenCalledTimes(1);
    });
    it("creates a new owned intake when duration changes for the retained local media", async () => {
        const hook = await prepared();
        await act(() => hook.result.current.requestAction("analyze"));
        await act(() => hook.result.current.confirmAction(confirmed(hook)));
        act(() => hook.result.current.onDuration(16));
        await act(() => hook.result.current.requestAction("reanalyze"));
        expect(hook.result.current.pendingAction).toBeNull();
        expect(calls.preflight.mock.calls.at(-1)![1]).toMatchObject({
            action: "analyze",
            targetDuration: 16,
        });
        expect(calls.preflight.mock.calls.at(-1)![1]).not.toHaveProperty("projectId");
        expect(calls.intake).toHaveBeenCalledTimes(2);
        expect(calls.intake.mock.calls[1][1].metadata.targetDuration).toBe(16);
    });
    it("does not turn a completed project pointer into a source-reupload blocker", async () => {
        owned = { ...project("compiled"), rights: confirmRemakeMediaRights(rights) };
        localStorage.setItem("remake-project:account:workspace", owned.id);
        const hook = renderHook(() => useRemakeStudio("workspace", "account"), { wrapper });
        await waitFor(() => expect(hook.result.current.health.data?.enabled).toBe(true));
        act(() => hook.result.current.onDuration(16));
        expect(hook.result.current.project).toBeNull();
        expect(hook.result.current.sourceReuploadRequired).toBe(false);
        expect(hook.result.current.step).toBe("prepare");
        expect(calls.preflight).not.toHaveBeenCalled();
        expect(calls.intake).not.toHaveBeenCalled();
        expect(calls.compile).not.toHaveBeenCalled();
    });
    it("preflights full source separately from output duration without uploading", async () => {
        const hook = await prepared();
        act(() => hook.result.current.onTimelineStartFrameChange(48));
        await act(() => hook.result.current.requestAction("analyze"));
        expect(calls.preflight).toHaveBeenCalledWith(
            "workspace",
            expect.objectContaining({
                action: "analyze",
                referenceStartFrame: 0,
                analysisScope: "full_source",
                sourceDurationSeconds: 20,
                targetDuration: 8,
            }),
        );
        expect(calls.intake).not.toHaveBeenCalled();
    });
    it("allows a short full source to be adapted into a longer chosen output", async () => {
        const hook = await prepared();
        act(() => {
            hook.result.current.onSourceMetadata(4);
            hook.result.current.onDuration(16);
        });
        await act(() => hook.result.current.requestAction("analyze"));
        expect(hook.result.current.sourceExcerptError).toBeNull();
        expect(calls.preflight.mock.calls.at(-1)![1]).toMatchObject({
            analysisScope: "full_source",
            sourceDurationSeconds: 4,
            targetDuration: 16,
        });
        expect(calls.intake).not.toHaveBeenCalled();
    });
    it("keeps a fresh workspace isolated from the previous session media", async () => {
        const first = await prepared();
        const privateVideo = first.result.current.video;
        first.unmount();
        const next = renderHook(() => useRemakeStudio("another-workspace", "account"), { wrapper });
        await waitFor(() => expect(next.result.current.health.data?.enabled).toBe(true));
        expect(privateVideo).not.toBeNull();
        expect(next.result.current.project).toBeNull();
        expect(next.result.current.video).toBeNull();
        expect(next.result.current.rights.source.evidenceNote).toBe("");
        expect(calls.saveDraft).not.toHaveBeenCalled();
    });
    it("ignores a prior workspace project fetch that resolves after switching scopes", async () => {
        localStorage.setItem("remake-project:account:workspace", "owned");
        let finish!: (value: SmartRemakeProject) => void;
        calls.project.mockReturnValueOnce(
            new Promise((resolve) => {
                finish = resolve;
            }),
        );
        const hook = renderHook(({ workspaceId }) => useRemakeStudio(workspaceId, "account"), {
            wrapper,
            initialProps: { workspaceId: "workspace" },
        });
        await waitFor(() => expect(calls.project).toHaveBeenCalled());
        hook.rerender({ workspaceId: "another-workspace" });
        await waitFor(() => expect(hook.result.current.health.data?.enabled).toBe(true));
        await act(async () => {
            finish(project());
        });
        expect(hook.result.current.project).toBeNull();
        expect(hook.result.current.busy).toBeNull();
        expect(localStorage.getItem("remake-project:account:another-workspace")).toBeNull();
    });
    it.each(["QuotaExceededError", "TransactionAbortError", "DatabaseLockedError"])(
        "does not read or save content drafts when device storage would fail with %s",
        async (failure) => {
            calls.readDraft.mockRejectedValue(new Error(failure));
            calls.saveDraft.mockRejectedValue(new Error(failure));
            const hook = await prepared();
            const video = hook.result.current.video;
            act(() => hook.result.current.onRightsChange(confirmRemakeMediaRights(rights)));
            await act(() => hook.result.current.requestAction("analyze"));
            expect(calls.compile).toHaveBeenCalledTimes(1);
            expect(hook.result.current.video).toBe(video);
            expect(calls.readDraft).not.toHaveBeenCalled();
            expect(calls.saveDraft).not.toHaveBeenCalled();
            expect(calls.removeDraft).not.toHaveBeenCalled();
        },
    );
    it("leaves legacy repair draft content untouched and uses only the current session intent", async () => {
        const legacyKey = "viraldy:remake-draft:workspace:owned:scene:version";
        const legacy = JSON.stringify({ instruction: "Old saved repair" });
        localStorage.setItem(legacyKey, legacy);
        const hook = await prepared();
        expect(hook.result.current.repairDrafts).toEqual({});
        expect(localStorage.getItem(legacyKey)).toBe(legacy);
        expect(calls.readDraft).not.toHaveBeenCalled();
        expect(calls.saveDraft).not.toHaveBeenCalled();
        expect(calls.removeDraft).not.toHaveBeenCalled();
        expect(calls.repair).not.toHaveBeenCalled();
    });
    it("keeps structured repair intent immutable across preflight and confirmation", async () => {
        owned = {
            ...project("compiled"),
            rights: confirmRemakeMediaRights(rights),
            scenes: [
                {
                    id: "scene",
                    index: 0,
                    activeVersionId: "version",
                    versions: [existingClip],
                    prompt: "p",
                    imagePrompt: "i",
                    videoPrompt: "v",
                    startSecond: 0,
                    durationSeconds: 8,
                },
            ],
        };
        const hook = await inSessionProject();
        const repairIntent = {
            schemaVersion: 1 as const,
            issues: ["action" as const],
            instruction: "Lift slowly",
        };
        await act(() =>
            hook.result.current.requestAction("repair", { sceneId: "scene", repairIntent }),
        );
        repairIntent.instruction = "Changed outside modal";
        expect(calls.preflight.mock.calls.at(-1)![1].repairIntent.instruction).toBe("Lift slowly");
        expect(calls.repair.mock.calls[0][3]).toMatchObject({
            repairIntent: { instruction: "Lift slowly" },
        });
        expect(calls.writeMarker.mock.invocationCallOrder[0]).toBeLessThan(
            calls.repair.mock.invocationCallOrder[0],
        );
    });
    it("does not POST a repair when the durable submission marker cannot commit", async () => {
        owned = {
            ...project("compiled"),
            rights: confirmRemakeMediaRights(rights),
            scenes: [
                {
                    id: "scene",
                    index: 0,
                    activeVersionId: "version",
                    versions: [existingClip],
                    prompt: "p",
                    imagePrompt: "i",
                    videoPrompt: "v",
                    startSecond: 0,
                    durationSeconds: 8,
                },
            ],
        };
        const hook = await inSessionProject();
        calls.writeMarker.mockRejectedValueOnce(new Error("QuotaExceededError"));
        await act(() =>
            hook.result.current.requestAction("repair", {
                sceneId: "scene",
                repairIntent: { schemaVersion: 1, issues: [], instruction: "" },
            }),
        );
        expect(calls.repair).not.toHaveBeenCalled();
        expect(hook.result.current.actionError).toContain("Chưa lưu");
    });
    it("discovers a queued candidate after reload by the same key without replaying POST", async () => {
        owned = {
            ...project("compiled"),
            rights: confirmRemakeMediaRights(rights),
            scenes: [
                {
                    id: "scene",
                    index: 0,
                    activeVersionId: "version",
                    versions: [existingClip],
                    prompt: "p",
                    imagePrompt: "i",
                    videoPrompt: "v",
                    startSecond: 0,
                    durationSeconds: 8,
                },
            ],
        };
        const hook = await inSessionProject();
        await act(() =>
            hook.result.current.requestAction("repair", {
                sceneId: "scene",
                repairIntent: { schemaVersion: 1, issues: [], instruction: "" },
            }),
        );
        const key = calls.repair.mock.calls[0][3].idempotencyKey;
        hook.unmount();
        owned = {
            ...owned,
            revision: owned.revision + 1,
            scenes: [
                {
                    ...owned.scenes[0],
                    versions: [
                        {
                            id: "candidate",
                            parentVersionId: "version",
                        } as SmartRemakeProject["scenes"][number]["versions"][number],
                    ],
                },
            ],
        };
        calls.receipt.mockResolvedValue({
            receipt: {
                operationId: "repair",
                sceneId: "scene",
                baseVersionId: "version",
                candidateVersionId: "candidate",
                status: "completed",
                needsReconciliation: false,
            },
        });
        const restored = renderHook(() => useRemakeStudio("workspace", "account"), { wrapper });
        await waitFor(() =>
            expect(restored.result.current.unreadRepairCandidate?.versionId).toBe("candidate"),
        );
        expect(calls.receipt).toHaveBeenCalledWith("workspace", "owned", key);
        expect(calls.repair).toHaveBeenCalledTimes(1);
        expect(restored.result.current.outputNavigation).toBeNull();
    });
    it("restores unresolved work to status without opening a new action or submitting", async () => {
        owned = {
            ...project(),
            pendingOperation: { id: "pending", status: "running", needsReconciliation: true },
        };
        localStorage.setItem("remake-project:account:workspace", owned.id);
        const hook = renderHook(() => useRemakeStudio("workspace", "account"), { wrapper });
        await waitFor(() => expect(hook.result.current.busy).toBeNull());
        await waitFor(() => expect(hook.result.current.health.data?.enabled).toBe(true));
        await act(() => hook.result.current.requestAction("reanalyze"));
        expect(hook.result.current.pendingAction).toBeNull();
        expect(hook.result.current.step).toBe("result");
        expect(calls.preflight).not.toHaveBeenCalled();
        expect(calls.compile).not.toHaveBeenCalled();
    });
});
