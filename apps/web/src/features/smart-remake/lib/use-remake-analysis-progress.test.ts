// @vitest-environment jsdom
import { createElement, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { SmartRemakeAnalysisProgress, SmartRemakeProject } from "@/shared/api/smart-remake";
import { useRemakeAnalysisProgress } from "./use-remake-analysis-progress";

const readProject = vi.hoisted(() => vi.fn());
vi.mock("@/shared/api/smart-remake", () => ({ getSmartRemakeProject: readProject }));

function progress(
    requestKey = "request",
    stage = "analyzing_source" as SmartRemakeAnalysisProgress["stage"],
): SmartRemakeAnalysisProgress {
    return {
        schemaVersion: 1,
        operationId: "operation",
        requestKey,
        status: "running",
        stage,
        startedAt: "2026-11-26T08:30:00Z",
        updatedAt: "2026-11-26T08:30:05Z",
        scenes: [],
    };
}

function project(value?: SmartRemakeAnalysisProgress): SmartRemakeProject {
    return {
        id: "owned",
        revision: 1,
        status: "draft",
        finalVideoUrl: "",
        targetDuration: 8,
        provider: "kie",
        scenes: [],
        analysisProgress: value,
    };
}

function setup(workspaceId = "workspace") {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
    const wrapper = ({ children }: { children: ReactNode }) =>
        createElement(QueryClientProvider, { client }, children);
    return renderHook(({ workspace }) => useRemakeAnalysisProgress(workspace), {
        wrapper,
        initialProps: { workspace: workspaceId },
    });
}

async function tick(milliseconds = 20) {
    await act(async () => {
        await vi.advanceTimersByTimeAsync(milliseconds);
    });
}

beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-11-26T08:30:00Z"));
    readProject.mockReset().mockResolvedValue(project());
});
afterEach(() => {
    cleanup();
    vi.useRealTimers();
});

describe("read-only compile progress", () => {
    it("starts elapsed time during intake and polls a new intake before any pendingOperation exists", async () => {
        const hook = setup();
        let token = 0;
        act(() => {
            token = hook.result.current.begin();
        });
        expect(hook.result.current.analysisStartedAt).toBe(Date.now());
        expect(hook.result.current.analysisPreparing).toBe(true);
        expect(hook.result.current.canCheckAnalysisStatus).toBe(false);
        expect(readProject).not.toHaveBeenCalled();
        act(() => hook.result.current.track(token, "owned", "request"));
        await tick();
        expect(hook.result.current.analysisPreparing).toBe(false);
        expect(hook.result.current.canCheckAnalysisStatus).toBe(true);
        expect(readProject).toHaveBeenCalledWith(
            "workspace",
            "owned",
            expect.objectContaining({ signal: expect.any(AbortSignal) }),
        );
        expect(hook.result.current.analysisProgress).toBeNull();
        readProject.mockResolvedValue(
            project({
                ...progress("request", "resolving_scenes"),
                sourceDurationSeconds: 30,
                sceneCount: 12,
                scenes: [{ index: 0, startSecond: 0, endSecond: 2.5, action: "Lift the product" }],
            }),
        );
        await tick(2000);
        expect(hook.result.current.analysisProgress?.sceneCount).toBe(12);
        expect(hook.result.current.analysisProgress?.scenes[0].action).toBe("Lift the product");
        readProject.mockResolvedValue(
            project({ ...progress("request", "identifying_product"), sceneCount: 12 }),
        );
        await tick(2000);
        expect(hook.result.current.analysisProgress?.stage).toBe("identifying_product");
    });

    it("ignores previous compile checkpoints instead of displaying stale recognition", async () => {
        readProject.mockResolvedValue(
            project({ ...progress("old"), product: { name: "Old product", details: [] } }),
        );
        const hook = setup();
        act(() => {
            const token = hook.result.current.begin();
            hook.result.current.track(token, "owned", "new");
        });
        await tick();
        expect(hook.result.current.analysisProgress).toBeNull();
        expect(readProject).toHaveBeenCalledTimes(1);
        await tick(2000);
        expect(readProject).toHaveBeenCalledTimes(2);
    });

    it("ignores another project's checkpoint even if its request key matches", async () => {
        readProject.mockResolvedValue({ ...project(progress()), id: "different-project" });
        const hook = setup();
        act(() => {
            const token = hook.result.current.begin();
            hook.result.current.track(token, "owned", "request");
        });
        await tick();
        expect(hook.result.current.analysisProgress).toBeNull();
        expect(hook.result.current.recoveredProject).toBeNull();
    });

    it("restores a current server compile as GET-only tracking after reload", async () => {
        const checkpoint = { ...progress(), startedAt: "2026-11-26T08:29:00Z" };
        readProject.mockResolvedValue(project(checkpoint));
        const hook = setup();
        act(() =>
            hook.result.current.restore({
                ...project(checkpoint),
                pendingOperation: {
                    id: "operation",
                    kind: "compile",
                    status: "running",
                    needsReconciliation: false,
                },
            }),
        );
        await tick();
        expect(hook.result.current.analysisUnresolved).toBe(true);
        expect(hook.result.current.analysisStartedAt).toBe(Date.parse(checkpoint.startedAt));
        expect(hook.result.current.analysisProgress?.requestKey).toBe("request");
        expect(readProject).toHaveBeenCalledTimes(1);
    });

    it.each(["render", "different-operation"])(
        "does not restore an unrelated %s receipt",
        async (kind) => {
            const hook = setup();
            act(() =>
                hook.result.current.restore({
                    ...project(progress()),
                    pendingOperation: {
                        id: kind === "render" ? "operation" : "other-operation",
                        kind: kind === "render" ? "render" : "compile",
                        status: "running",
                        needsReconciliation: false,
                    },
                }),
            );
            await tick();
            expect(hook.result.current.analysisProgress).toBeNull();
            expect(hook.result.current.analysisUnresolved).toBe(false);
            expect(readProject).not.toHaveBeenCalled();
        },
    );

    it("settles a restored compile when another tab has moved the project to rendering", async () => {
        const initial = {
            ...project(progress()),
            pendingOperation: {
                id: "operation",
                kind: "compile",
                status: "running" as const,
                needsReconciliation: false,
            },
        };
        readProject.mockResolvedValue({
            ...project(),
            revision: 2,
            pendingOperation: {
                id: "render-operation",
                kind: "render",
                status: "running",
                needsReconciliation: false,
            },
        });
        const hook = setup();
        act(() => hook.result.current.restore(initial));
        await tick();
        expect(hook.result.current.analysisProgress).toBeNull();
        expect(hook.result.current.analysisUnresolved).toBe(false);
        expect(hook.result.current.recoveredProject).toBeNull();
        expect(hook.result.current.supersedingProject?.pendingOperation?.id).toBe(
            "render-operation",
        );
    });

    it("keeps waiting when a newly committed operation has no kind yet", async () => {
        readProject.mockResolvedValue({
            ...project(),
            pendingOperation: {
                id: "operation",
                status: "running",
                needsReconciliation: false,
            },
        });
        const hook = setup();
        let token = 0;
        act(() => {
            token = hook.result.current.begin();
            hook.result.current.track(token, "owned", "request", 1);
        });
        await tick();
        act(() => hook.result.current.interrupt(token));
        expect(hook.result.current.analysisUnresolved).toBe(true);
        expect(hook.result.current.supersedingProject).toBeNull();
        expect(hook.result.current.analysisProgress).toBeNull();
    });

    it("adopts a newer owned compile only after the interrupted predecessor is proven superseded", async () => {
        const first = {
            ...project(progress("old")),
            pendingOperation: {
                id: "operation",
                kind: "compile",
                status: "running" as const,
                needsReconciliation: false,
            },
        };
        readProject.mockResolvedValue(first);
        const hook = setup();
        act(() => hook.result.current.restore(first));
        await tick();
        const oldToken = hook.result.current.token!;
        const next = {
            ...project({ ...progress("new"), operationId: "new-operation" }),
            revision: 2,
            pendingOperation: {
                id: "new-operation",
                kind: "compile",
                status: "running" as const,
                needsReconciliation: false,
            },
        };
        readProject.mockResolvedValue(next);
        await act(() => hook.result.current.checkAnalysisStatus());
        await tick();
        expect(hook.result.current.supersedingProject?.analysisProgress?.requestKey).toBe("new");
        act(() => hook.result.current.restore(next, oldToken));
        await tick();
        act(() => hook.result.current.complete(oldToken));
        expect(hook.result.current.analysisUnresolved).toBe(true);
        expect(hook.result.current.analysisProgress?.requestKey).toBe("new");
    });

    it("does not reopen a settled request but can follow a genuinely newer server compile", async () => {
        readProject.mockResolvedValue(project());
        const hook = setup();
        let token = 0;
        act(() => {
            token = hook.result.current.begin();
            hook.result.current.track(token, "owned", "old", 1);
        });
        await tick();
        act(() => hook.result.current.complete(token));
        const pending = (key: string, revision: number) => ({
            ...project(progress(key)),
            revision,
            pendingOperation: {
                id: "operation",
                kind: "compile",
                status: "running" as const,
                needsReconciliation: false,
            },
        });
        act(() => hook.result.current.restore(pending("old", 1)));
        expect(hook.result.current.analysisUnresolved).toBe(false);
        const next = pending("new", 2);
        readProject.mockResolvedValue(next);
        act(() => hook.result.current.restore(next));
        await tick();
        expect(hook.result.current.analysisProgress?.requestKey).toBe("new");
        expect(hook.result.current.analysisUnresolved).toBe(true);
    });

    it("does not wait forever on a hanging status GET and allows a manual read after its deadline", async () => {
        readProject.mockReturnValueOnce(new Promise(() => {}));
        const hook = setup();
        act(() => {
            const token = hook.result.current.begin();
            hook.result.current.track(token, "owned", "request");
        });
        await tick();
        expect(hook.result.current.checkingAnalysisStatus).toBe(true);
        await tick(15000);
        expect(hook.result.current.checkingAnalysisStatus).toBe(false);
        expect(hook.result.current.analysisStatusError).toContain("Chưa lấy được tiến trình");
        expect(readProject.mock.calls[0][2].signal.aborted).toBe(true);
        readProject.mockResolvedValue(project(progress()));
        await act(() => hook.result.current.checkAnalysisStatus());
        await tick();
        expect(readProject).toHaveBeenCalledTimes(2);
        expect(hook.result.current.analysisStatusError).toBeNull();
    });

    it("aborts only its status GET on unmount", async () => {
        readProject.mockReturnValueOnce(new Promise(() => {}));
        const hook = setup();
        act(() => {
            const token = hook.result.current.begin();
            hook.result.current.track(token, "owned", "request");
        });
        await tick();
        const signal = readProject.mock.calls[0][2].signal;
        hook.unmount();
        expect(signal.aborted).toBe(true);
        await tick(20000);
        expect(readProject).toHaveBeenCalledTimes(1);
    });

    it("never exposes a late read after the compile POST has completed", async () => {
        let resolve!: (value: SmartRemakeProject) => void;
        readProject.mockReturnValue(
            new Promise<SmartRemakeProject>((done) => {
                resolve = done;
            }),
        );
        const hook = setup();
        let token = 0;
        act(() => {
            token = hook.result.current.begin();
            hook.result.current.track(token, "owned", "request");
        });
        await tick();
        act(() => hook.result.current.complete(token));
        await act(async () => resolve(project(progress())));
        await tick(6000);
        expect(hook.result.current.analysisProgress).toBeNull();
        expect(hook.result.current.analysisUnresolved).toBe(false);
        expect(hook.result.current.recoveredProject).toBeNull();
        expect(readProject).toHaveBeenCalledTimes(1);
    });

    it("isolates a newer request from late progress and completion of its predecessor", async () => {
        let resolveOld!: (value: SmartRemakeProject) => void;
        readProject.mockReturnValueOnce(
            new Promise<SmartRemakeProject>((done) => {
                resolveOld = done;
            }),
        );
        readProject.mockResolvedValue(project(progress("new")));
        const hook = setup();
        let oldToken = 0;
        act(() => {
            oldToken = hook.result.current.begin();
            hook.result.current.track(oldToken, "owned", "old");
        });
        await tick();
        act(() => {
            const next = hook.result.current.begin();
            hook.result.current.track(next, "owned", "new");
        });
        await tick();
        await act(async () => resolveOld(project(progress("old"))));
        act(() => hook.result.current.complete(oldToken));
        await tick();
        expect(hook.result.current.analysisProgress?.requestKey).toBe("new");
    });

    it("shows a read error, stops automatic error polling, and checks the same request manually", async () => {
        readProject.mockRejectedValueOnce(new Error("Offline"));
        const hook = setup();
        act(() => {
            const token = hook.result.current.begin();
            hook.result.current.track(token, "owned", "request");
        });
        await tick();
        expect(hook.result.current.analysisStatusError).toContain("Chưa lấy được tiến trình");
        await tick(6000);
        expect(readProject).toHaveBeenCalledTimes(1);
        readProject.mockResolvedValue(project(progress()));
        await act(async () => {
            await hook.result.current.checkAnalysisStatus();
        });
        await tick();
        expect(readProject).toHaveBeenCalledTimes(2);
        expect(hook.result.current.analysisStatusError).toBeNull();
        expect(hook.result.current.analysisProgress?.requestKey).toBe("request");
    });

    it.each(["completed", "failed"] as const)(
        "stops polling a matching terminal %s checkpoint",
        async (status) => {
            readProject.mockResolvedValue(project({ ...progress(), status, stage: status }));
            const hook = setup();
            act(() => {
                const token = hook.result.current.begin();
                hook.result.current.track(token, "owned", "request");
            });
            await tick(6000);
            expect(readProject).toHaveBeenCalledTimes(1);
            expect(hook.result.current.analysisProgress?.status).toBe(status);
        },
    );

    it("retains a timed-out POST for read-only recovery without inventing a new request", async () => {
        const hook = setup();
        let token = 0;
        act(() => {
            token = hook.result.current.begin();
            hook.result.current.track(token, "owned", "request");
        });
        await tick();
        act(() => hook.result.current.interrupt(token));
        expect(hook.result.current.analysisUnresolved).toBe(true);
        readProject.mockResolvedValue(
            project({ ...progress(), stage: "completed", status: "completed" }),
        );
        await act(async () => {
            await hook.result.current.checkAnalysisStatus();
        });
        await tick();
        expect(hook.result.current.recoveredProject?.analysisProgress?.requestKey).toBe("request");
        expect(readProject.mock.calls.every((args) => args[1] === "owned")).toBe(true);
        act(() => hook.result.current.complete(token));
        expect(hook.result.current.analysisUnresolved).toBe(false);
    });

    it("does not claim an analysis is pending when intake failed before the POST", () => {
        const hook = setup();
        act(() => {
            const token = hook.result.current.begin();
            hook.result.current.interrupt(token);
        });
        expect(hook.result.current.analysisUnresolved).toBe(false);
        expect(readProject).not.toHaveBeenCalled();
    });

    it("stops reading on unmount or workspace change and hides old workspace facts", async () => {
        readProject.mockResolvedValue(project(progress()));
        const hook = setup();
        act(() => {
            const token = hook.result.current.begin();
            hook.result.current.track(token, "owned", "request");
        });
        await tick();
        hook.rerender({ workspace: "different" });
        await tick(6000);
        expect(hook.result.current.analysisProgress).toBeNull();
        expect(hook.result.current.analysisStartedAt).toBeUndefined();
        expect(readProject).toHaveBeenCalledTimes(1);
        hook.unmount();
        await tick(6000);
        expect(readProject).toHaveBeenCalledTimes(1);
    });
});
