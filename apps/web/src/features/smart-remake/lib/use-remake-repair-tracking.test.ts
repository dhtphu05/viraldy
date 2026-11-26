// @vitest-environment jsdom
import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { SmartRemakeProject } from "@/shared/api/smart-remake";
import { useRemakeRepairTracking } from "./use-remake-repair-tracking";
const calls = vi.hoisted(() => ({
    list: vi.fn(),
    write: vi.fn(),
    update: vi.fn(),
    receipt: vi.fn(),
    project: vi.fn(),
}));
vi.mock("./remake-draft", () => ({
    remakeDraftStore: {
        listSubmissionMarkers: calls.list,
        writeSubmissionMarker: calls.write,
        updateSubmissionMarker: calls.update,
    },
}));
vi.mock("@/shared/api/smart-remake", () => ({
    getSmartRemakeRepairReceipt: calls.receipt,
    getSmartRemakeProject: calls.project,
}));
const scope = { accountId: "a", workspaceId: "w", draftId: "current" };
const marker = {
    requestKey: "key",
    requestFingerprint: "fingerprint",
    projectId: "p",
    sceneId: "s",
    baseVersionId: "v",
    status: "awaiting_receipt",
    operationId: null,
    candidateVersionId: null,
    needsReconciliation: false,
    disposition: null,
    createdAt: 1,
    updatedAt: 1,
};
const project = {
    id: "p",
    revision: 1,
    scenes: [{ id: "s", activeVersionId: "v", versions: [] }],
} as unknown as SmartRemakeProject;
beforeEach(() => {
    vi.clearAllMocks();
    calls.list.mockResolvedValue([]);
    calls.write.mockImplementation(async (_scope, value) => ({ ...marker, ...value }));
    calls.update.mockImplementation(async (_scope, _key, patch) => ({ ...marker, ...patch }));
    calls.receipt.mockResolvedValue({ receipt: null });
});
afterEach(cleanup);
function harness(current = project) {
    return renderHook(
        ({ p }) => useRemakeRepairTracking({ scope, project: p, onProject: vi.fn() }),
        { initialProps: { p: current } },
    );
}
it("commits a marker before returning permission to POST and rejects failed storage", async () => {
    const hook = harness();
    await waitFor(() => expect(hook.result.current.loaded).toBe(true));
    await act(async () => {
        await hook.result.current.begin({
            requestKey: "key",
            requestFingerprint: "fingerprint",
            projectId: "p",
            sceneId: "s",
            baseVersionId: "v",
        });
    });
    expect(calls.write).toHaveBeenCalledTimes(1);
    calls.write.mockRejectedValueOnce(new Error("QuotaExceededError"));
    await act(async () => {
        await expect(
            hook.result.current.begin({
                requestKey: "other",
                requestFingerprint: "new",
                projectId: "p",
                sceneId: "s",
                baseVersionId: "v",
            }),
        ).rejects.toThrow("Chưa lưu");
    });
});
it("restores an exact receipt and only exposes a candidate present in that scene", async () => {
    calls.list.mockResolvedValue([marker]);
    calls.receipt.mockResolvedValue({
        receipt: {
            operationId: "op",
            sceneId: "s",
            baseVersionId: "v",
            candidateVersionId: "c",
            status: "completed",
            needsReconciliation: false,
        },
    });
    const fresh = {
        ...project,
        revision: 2,
        scenes: [{ ...project.scenes[0], versions: [{ id: "c", parentVersionId: "v" }] }],
    } as SmartRemakeProject;
    calls.project.mockResolvedValue(fresh);
    const hook = harness(fresh);
    await waitFor(() => expect(hook.result.current.candidate?.versionId).toBe("c"));
    expect(calls.receipt).toHaveBeenCalledWith("w", "p", "key");
    await act(() => hook.result.current.acknowledgeCandidate("viewed"));
    expect(hook.result.current.candidate).toBeNull();
    expect(calls.update).toHaveBeenCalledWith(
        scope,
        "key",
        expect.objectContaining({ disposition: "viewed" }),
    );
});
it("keeps a missing receipt unresolved without resubmission or guessed candidates", async () => {
    calls.list.mockResolvedValue([marker]);
    const hook = harness();
    await waitFor(() => expect(calls.receipt).toHaveBeenCalled());
    await waitFor(() => expect(hook.result.current.unresolved).toBe(true));
    expect(hook.result.current.candidate).toBeNull();
    expect(calls.write).not.toHaveBeenCalled();
});
it("does not accept a receipt bound to another scene or base version", async () => {
    calls.list.mockResolvedValue([marker]);
    calls.receipt.mockResolvedValue({
        receipt: {
            operationId: "op",
            sceneId: "other",
            baseVersionId: "v",
            candidateVersionId: "c",
            status: "completed",
            needsReconciliation: false,
        },
    });
    const hook = harness();
    await waitFor(() => expect(hook.result.current.error).toContain("không khớp"));
    expect(hook.result.current.candidate).toBeNull();
});
it("retains a rejected repair reason after receipt lookup without proposing another submission", async () => {
    calls.list.mockResolvedValue([marker]);
    calls.receipt.mockResolvedValue({
        receipt: {
            operationId: "op",
            sceneId: "s",
            baseVersionId: "v",
            candidateVersionId: null,
            status: "failed",
            errorCode: "SMART_REMAKE_REPAIR_INTENT_REJECTED",
            normalizationReason: "Không thể đổi chiếc bình thành ly thủy tinh.",
            needsReconciliation: false,
        },
    });
    const hook = harness();
    await waitFor(() => expect(hook.result.current.failures.s).toContain("Không thể đổi"));
    expect(hook.result.current.unresolved).toBe(false);
    expect(calls.write).not.toHaveBeenCalled();
});
it("refreshes project before exposing a completed candidate absent from its current history", async () => {
    calls.list.mockResolvedValue([marker]);
    calls.receipt.mockResolvedValue({
        receipt: {
            operationId: "op",
            sceneId: "s",
            baseVersionId: "v",
            candidateVersionId: "c",
            status: "completed",
            needsReconciliation: false,
        },
    });
    calls.project.mockResolvedValue({ ...project, revision: 2 });
    const hook = harness();
    await waitFor(() => expect(calls.project).toHaveBeenCalledWith("w", "p"));
    expect(hook.result.current.candidate).toBeNull();
});
it("does not allow marker creation without an account scope", async () => {
    const hook = renderHook(() =>
        useRemakeRepairTracking({ scope: null, project, onProject: vi.fn() }),
    );
    await waitFor(() => expect(hook.result.current.loaded).toBe(true));
    await act(async () => {
        await expect(
            hook.result.current.begin({
                requestKey: "key",
                requestFingerprint: "f",
                projectId: "p",
                sceneId: "s",
                baseVersionId: "v",
            }),
        ).rejects.toThrow("Chưa lưu");
    });
    expect(calls.write).not.toHaveBeenCalled();
});
it("reports receipt retrieval errors while retaining an unresolved marker", async () => {
    calls.list.mockResolvedValue([marker]);
    calls.receipt.mockRejectedValue(new Error("offline"));
    const hook = harness();
    await waitFor(() => expect(hook.result.current.error).toBe("offline"));
    expect(hook.result.current.unresolved).toBe(true);
});
it("does not poll terminal candidates that have already been viewed", async () => {
    calls.list.mockResolvedValue([
        {
            ...marker,
            status: "completed",
            operationId: "op",
            candidateVersionId: "c",
            disposition: "viewed",
        },
    ]);
    const hook = harness();
    await waitFor(() => expect(hook.result.current.loaded).toBe(true));
    await act(() => hook.result.current.refresh());
    expect(calls.receipt).not.toHaveBeenCalled();
    expect(hook.result.current.unresolved).toBe(false);
});
it("blocks another submission if previous markers cannot be read", async () => {
    calls.list.mockRejectedValue(new Error("blocked"));
    const hook = harness();
    await waitFor(() => expect(hook.result.current.loaded).toBe(true));
    await act(async () => {
        await expect(
            hook.result.current.begin({
                requestKey: "new",
                requestFingerprint: "f",
                projectId: "p",
                sceneId: "s",
                baseVersionId: "v",
            }),
        ).rejects.toThrow("Chưa lưu");
    });
    expect(calls.write).not.toHaveBeenCalled();
});
it.each([
    { parentVersionId: "another" },
    { parentVersionId: "v", usedByRevision: 2 },
    { parentVersionId: "v", id: "v" },
])("does not announce an unrelated or previously used candidate: %j", async (versionPatch) => {
    calls.list.mockResolvedValue([
        {
            ...marker,
            status: "completed",
            operationId: "op",
            candidateVersionId: versionPatch.id ?? "c",
        },
    ]);
    const current = {
        ...project,
        scenes: [{ ...project.scenes[0], versions: [{ id: "c", ...versionPatch }] }],
    } as SmartRemakeProject;
    const hook = harness(current);
    await waitFor(() => expect(hook.result.current.loaded).toBe(true));
    expect(hook.result.current.candidate).toBeNull();
});
it("loads only a pending submission's authorized project after reload without a content draft", async () => {
    calls.list.mockResolvedValue([marker]);
    calls.project.mockResolvedValue(project);
    const onProject = vi.fn();
    renderHook(() => useRemakeRepairTracking({ scope, project: null, onProject }));
    await waitFor(() => expect(onProject).toHaveBeenCalledWith(project));
    expect(calls.project).toHaveBeenCalledWith("w", "p");
    expect(calls.write).not.toHaveBeenCalled();
});
it("does not reopen a completed repair that was already viewed", async () => {
    calls.list.mockResolvedValue([
        { ...marker, status: "completed", candidateVersionId: "c", disposition: "viewed" },
    ]);
    const onProject = vi.fn();
    const hook = renderHook(() => useRemakeRepairTracking({ scope, project: null, onProject }));
    await waitFor(() => expect(hook.result.current.loaded).toBe(true));
    await act(() => hook.result.current.refresh());
    expect(calls.project).not.toHaveBeenCalled();
    expect(onProject).not.toHaveBeenCalled();
});
