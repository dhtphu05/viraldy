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
    expect(hook.result.current.candidate).toEqual({ projectId: "p", sceneId: "s", versionId: "c" });
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

const affectedVersions = [
    { sceneId: "s", baseVersionId: "v", candidateVersionId: "c" },
    { sceneId: "sibling", baseVersionId: "sibling-base", candidateVersionId: "sibling-candidate" },
];
const repairBaseTimeline = affectedVersions.map((binding, index) => ({
    renderUnitId: binding.sceneId,
    versionId: binding.baseVersionId,
    inFrame: index * 48,
    outFrame: (index + 1) * 48,
}));
const groupReceipt = {
    operationId: "group-op",
    sceneId: "s",
    baseVersionId: "v",
    candidateVersionId: "c",
    status: "completed",
    needsReconciliation: false,
    repairScope: "provider_group",
    renderGroupId: "group",
    affectedVersions,
};
function groupProject() {
    return {
        ...project,
        draftTimeline: {
            fps: 24,
            totalFrames: 96,
            items: repairBaseTimeline.map((item) => ({ ...item })),
        },
        scenes: affectedVersions.map((binding) => ({
            id: binding.sceneId,
            activeVersionId: binding.baseVersionId,
            versions: [
                { id: binding.baseVersionId, parentVersionId: null },
                {
                    id: binding.candidateVersionId,
                    parentVersionId: binding.baseVersionId,
                    providerMetadata: {
                        repairScope: "provider_group",
                        renderGroupId: "group",
                        repairOperationId: "group-op",
                        repairAffectedVersions: affectedVersions,
                        repairBaseTimeline,
                    },
                },
            ],
        })),
    } as unknown as SmartRemakeProject;
}
it("recovers exact provider-group bindings and exposes the whole repair candidate", async () => {
    calls.list.mockResolvedValue([{ ...marker, repairScope: "provider_group" }]);
    calls.receipt.mockResolvedValue({ receipt: groupReceipt });
    const hook = harness(groupProject());
    await waitFor(() =>
        expect(hook.result.current.candidate).toEqual({
            projectId: "p",
            sceneId: "s",
            versionId: "c",
            operationId: "group-op",
            repairScope: "provider_group",
            renderGroupId: "group",
            affectedVersions,
        }),
    );
    expect(calls.update).toHaveBeenCalledWith(
        scope,
        "key",
        expect.objectContaining({
            repairScope: "provider_group",
            renderGroupId: "group",
            affectedVersions,
        }),
    );
    expect(calls.write).not.toHaveBeenCalled();
});
it("upgrades a completed legacy group marker using its exact receipt after reload", async () => {
    calls.list.mockResolvedValue([
        { ...marker, status: "completed", operationId: "group-op", candidateVersionId: "c" },
    ]);
    calls.receipt.mockResolvedValue({ receipt: groupReceipt });
    const hook = harness(groupProject());
    await waitFor(() => expect(calls.receipt).toHaveBeenCalledWith("w", "p", "key"));
    await waitFor(() =>
        expect(hook.result.current.candidate).toMatchObject({
            repairScope: "provider_group",
            affectedVersions,
        }),
    );
    expect(calls.write).not.toHaveBeenCalled();
});
it.each([
    { repairScope: undefined },
    { renderGroupId: "different" },
    {
        affectedVersions: [
            { ...affectedVersions[0], baseVersionId: "different" },
            affectedVersions[1],
        ],
    },
    {
        affectedVersions: [
            affectedVersions[0],
            { ...affectedVersions[1], baseVersionId: "different" },
        ],
    },
    { affectedVersions: [affectedVersions[0], affectedVersions[0]] },
])("rejects a changed provider-group receipt identity before storing: %j", async (patch) => {
    calls.list.mockResolvedValue([
        { ...marker, repairScope: "provider_group", renderGroupId: "group", affectedVersions },
    ]);
    calls.receipt.mockResolvedValue({ receipt: { ...groupReceipt, ...patch } });
    const hook = harness(groupProject());
    await waitFor(() => expect(hook.result.current.error).toContain("không khớp"));
    expect(calls.update).not.toHaveBeenCalled();
    expect(hook.result.current.candidate).toBeNull();
});
it("retains nullable candidate bindings while a group repair is queued", async () => {
    calls.list.mockResolvedValue([{ ...marker, repairScope: "provider_group" }]);
    const queuedBindings = affectedVersions.map((binding) => ({
        ...binding,
        candidateVersionId: null,
    }));
    calls.receipt.mockResolvedValue({
        receipt: {
            ...groupReceipt,
            status: "queued",
            candidateVersionId: null,
            affectedVersions: queuedBindings,
        },
    });
    const hook = harness(groupProject());
    await waitFor(() =>
        expect(calls.update).toHaveBeenCalledWith(
            scope,
            "key",
            expect.objectContaining({ status: "running", affectedVersions: queuedBindings }),
        ),
    );
    expect(hook.result.current.candidate).toBeNull();
    expect(hook.result.current.unresolved).toBe(true);
});
it.each([
    { renderGroupId: "different" },
    { affectedVersions: [affectedVersions[0]] },
    { operationId: "different" },
    { operationId: "" },
    { operationId: undefined },
])(
    "does not bind a first group receipt that contradicts an existing candidate: %j",
    async (patch) => {
        calls.list.mockResolvedValue([{ ...marker, repairScope: "provider_group" }]);
        calls.receipt.mockResolvedValue({ receipt: { ...groupReceipt, ...patch } });
        const hook = harness(groupProject());
        await waitFor(() => expect(hook.result.current.error).toContain("không khớp"));
        expect(calls.update).not.toHaveBeenCalled();
        expect(hook.result.current.candidate).toBeNull();
    },
);
it.each([
    "missing-member",
    "wrong-parent",
    "wrong-operation",
    "wrong-group",
    "wrong-member-bindings",
])("does not expose a group candidate with %s", async (problem) => {
    calls.list.mockResolvedValue([{ ...marker, ...groupReceipt }]);
    const current = groupProject();
    const sibling = current.scenes[1];
    if (problem === "missing-member") sibling.versions = sibling.versions.slice(0, 1);
    if (problem === "wrong-parent") sibling.versions[1].parentVersionId = "unrelated";
    if (problem === "wrong-operation")
        (
            sibling.versions[1] as unknown as { providerMetadata: { repairOperationId: string } }
        ).providerMetadata.repairOperationId = "unrelated";
    if (problem === "wrong-group")
        (
            sibling.versions[1] as unknown as { providerMetadata: { renderGroupId: string } }
        ).providerMetadata.renderGroupId = "unrelated";
    if (problem === "wrong-member-bindings")
        (
            sibling.versions[1] as unknown as {
                providerMetadata: { repairAffectedVersions: unknown[] };
            }
        ).providerMetadata.repairAffectedVersions = [affectedVersions[0]];
    const hook = harness(current);
    await waitFor(() => expect(hook.result.current.loaded).toBe(true));
    expect(hook.result.current.candidate).toBeNull();
});
it("keeps a completed group marker unresolved when its exact receipt is missing", async () => {
    calls.list.mockResolvedValue([
        { ...marker, status: "completed", operationId: "group-op", candidateVersionId: "c" },
    ]);
    const hook = harness(groupProject());
    await waitFor(() => expect(calls.receipt).toHaveBeenCalled());
    await waitFor(() => expect(hook.result.current.unresolved).toBe(true));
    expect(hook.result.current.candidate).toBeNull();
    expect(calls.write).not.toHaveBeenCalled();
});
it.each([0, 1])(
    "does not offer a completed group candidate after member %i trim changes",
    async (memberIndex) => {
        calls.list.mockResolvedValue([{ ...marker, ...groupReceipt }]);
        const current = groupProject();
        const changed = {
            ...current,
            draftTimeline: {
                ...current.draftTimeline!,
                items: current.draftTimeline!.items.map((item, index) =>
                    index === memberIndex
                        ? { ...item, inFrame: item.inFrame + 1, outFrame: item.outFrame + 1 }
                        : item,
                ),
            },
        };
        const hook = harness(changed);
        await waitFor(() => expect(hook.result.current.loaded).toBe(true));
        expect(hook.result.current.candidate).toBeNull();
        expect(hook.result.current.unresolved).toBe(false);
        expect(calls.receipt).not.toHaveBeenCalled();
    },
);
it("records a completed group receipt as terminal even when the current trim is stale", async () => {
    calls.list.mockResolvedValue([{ ...marker, repairScope: "provider_group" }]);
    calls.receipt.mockResolvedValue({ receipt: groupReceipt });
    const current = groupProject();
    const changed = {
        ...current,
        draftTimeline: {
            ...current.draftTimeline!,
            items: current.draftTimeline!.items.map((item) => ({
                ...item,
                inFrame: item.inFrame + 1,
            })),
        },
    };
    const hook = harness(changed);
    await waitFor(() =>
        expect(calls.update).toHaveBeenCalledWith(
            scope,
            "key",
            expect.objectContaining({ status: "completed", affectedVersions }),
        ),
    );
    await waitFor(() => expect(hook.result.current.unresolved).toBe(false));
    expect(hook.result.current.candidate).toBeNull();
});
