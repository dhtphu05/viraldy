// @vitest-environment jsdom
import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { useRemakeStudioDraft } from "./use-remake-studio-draft";
const calls = vi.hoisted(() => ({ read: vi.fn(), save: vi.fn(), remove: vi.fn() }));
vi.mock("./remake-draft", () => ({
    remakeDraftStore: { read: calls.read, save: calls.save, remove: calls.remove },
}));
const scope = { accountId: "a", workspaceId: "w", draftId: "current" };
const value = { sections: { intake: { baseline: null, value: { brief: "new" } } } };
beforeEach(() => {
    vi.clearAllMocks();
    calls.read.mockResolvedValue(null);
    calls.save.mockResolvedValue({ revision: 1 });
});
afterEach(cleanup);
it("waits for restoration before autosaving and reports saved only after commit", async () => {
    let finish!: () => void;
    const restore = vi.fn(
        () =>
            new Promise<void>((resolve) => {
                finish = resolve;
            }),
    );
    calls.read.mockResolvedValue({ snapshot: { revision: 3 }, files: {} });
    const hook = renderHook(() => useRemakeStudioDraft({ scope, value, onRestore: restore }));
    await waitFor(() => expect(restore).toHaveBeenCalled());
    expect(hook.result.current.loaded).toBe(false);
    expect(calls.save).not.toHaveBeenCalled();
    await act(async () => {
        finish();
    });
    await waitFor(() => expect(hook.result.current.loaded).toBe(true));
    await act(() => hook.result.current.flush());
    expect(calls.save).toHaveBeenCalledWith(scope, value, 3);
    expect(hook.result.current.status).toBe("saved");
});
it("keeps dirty state and reports storage failure without discarding files", async () => {
    calls.save.mockRejectedValue(new Error("quota"));
    const hook = renderHook(() => useRemakeStudioDraft({ scope, value, onRestore: vi.fn() }));
    await waitFor(() => expect(hook.result.current.loaded).toBe(true));
    await act(() => hook.result.current.flush());
    expect(hook.result.current.status).toBe("error");
    expect(hook.result.current.error).toContain("Chưa lưu được");
    expect(calls.remove).not.toHaveBeenCalled();
});
it("does not save without an authenticated scope", async () => {
    const hook = renderHook(() => useRemakeStudioDraft({ scope: null, value, onRestore: vi.fn() }));
    await act(() => hook.result.current.flush());
    expect(calls.read).not.toHaveBeenCalled();
    expect(calls.save).not.toHaveBeenCalled();
});
it("recognizes equivalent values recreated by rendering and saves their committed state", async () => {
    const hook = renderHook(() =>
        useRemakeStudioDraft({
            scope,
            value: { sections: { intake: { baseline: null, value: { brief: "new" } } } },
            onRestore: vi.fn(),
        }),
    );
    await waitFor(() => expect(hook.result.current.loaded).toBe(true));
    await act(() => hook.result.current.flush());
    expect(hook.result.current.status).toBe("saved");
});
it("does not overwrite a draft after its initial read fails", async () => {
    calls.read.mockRejectedValue(new Error("corrupt blob"));
    const hook = renderHook(() => useRemakeStudioDraft({ scope, value, onRestore: vi.fn() }));
    await waitFor(() => expect(hook.result.current.status).toBe("error"));
    await act(() => hook.result.current.flush());
    expect(calls.save).not.toHaveBeenCalled();
});
it("keeps conflicted snapshots intact until they are explicitly resolved", async () => {
    const hook = renderHook(
        ({ suspended }) => useRemakeStudioDraft({ scope, value, suspended, onRestore: vi.fn() }),
        { initialProps: { suspended: true } },
    );
    await waitFor(() => expect(hook.result.current.loaded).toBe(true));
    await act(() => hook.result.current.flush());
    expect(hook.result.current.status).toBe("conflict");
    expect(calls.save).not.toHaveBeenCalled();
    hook.rerender({ suspended: false });
    await act(() => hook.result.current.flush());
    expect(calls.save).toHaveBeenCalledTimes(1);
});
it("serializes overlapping flushes instead of conflicting with its own revision", async () => {
    let finish!: (value: { revision: number }) => void;
    calls.save
        .mockReturnValueOnce(
            new Promise((resolve) => {
                finish = resolve;
            }),
        )
        .mockResolvedValueOnce({ revision: 2 })
        .mockResolvedValueOnce({ revision: 3 });
    const hook = renderHook(() => useRemakeStudioDraft({ scope, value, onRestore: vi.fn() }));
    await waitFor(() => expect(hook.result.current.loaded).toBe(true));
    await act(async () => {
        const first = hook.result.current.flush();
        const second = hook.result.current.flush();
        const third = hook.result.current.flush();
        finish({ revision: 1 });
        await Promise.all([first, second, third]);
    });
    expect(calls.save.mock.calls.map((call) => call[2])).toEqual([null, 1, 2]);
    expect(hook.result.current.status).toBe("saved");
});
it("removes only the local snapshot and waits for an edit before saving again", async () => {
    calls.remove.mockResolvedValue(undefined);
    const hook = renderHook(
        ({ content }) => useRemakeStudioDraft({ scope, value: content, onRestore: vi.fn() }),
        { initialProps: { content: value } },
    );
    await waitFor(() => expect(hook.result.current.loaded).toBe(true));
    await act(() => hook.result.current.remove());
    await act(() => hook.result.current.flush());
    expect(calls.remove).toHaveBeenCalledWith(scope);
    expect(calls.save).not.toHaveBeenCalled();
    hook.rerender({
        content: { sections: { intake: { baseline: null, value: { brief: "edited" } } } },
    });
    await act(() => hook.result.current.flush());
    expect(calls.save).toHaveBeenCalledTimes(1);
    expect(calls.save.mock.calls[0][2]).toBeNull();
});
it("ignores an old account read that resolves after switching scope", async () => {
    let finish!: (value: unknown) => void;
    calls.read
        .mockReturnValueOnce(
            new Promise((resolve) => {
                finish = resolve;
            }),
        )
        .mockResolvedValueOnce(null);
    const restore = vi.fn();
    const hook = renderHook(
        ({ accountId }) =>
            useRemakeStudioDraft({ scope: { ...scope, accountId }, value, onRestore: restore }),
        { initialProps: { accountId: "a" } },
    );
    hook.rerender({ accountId: "b" });
    await waitFor(() => expect(hook.result.current.loaded).toBe(true));
    await act(async () => finish({ snapshot: { revision: 9 }, files: {} }));
    expect(restore).toHaveBeenCalledTimes(1);
    expect(restore.mock.calls[0][0]).toBeNull();
});
it("reports deletion failures without discarding the existing snapshot", async () => {
    calls.remove.mockRejectedValue(new Error("blocked"));
    const hook = renderHook(() => useRemakeStudioDraft({ scope, value, onRestore: vi.fn() }));
    await waitFor(() => expect(hook.result.current.loaded).toBe(true));
    await act(() => hook.result.current.remove());
    expect(hook.result.current.status).toBe("error");
    expect(hook.result.current.error).toContain("Chưa xóa");
});
it("flushes on visibility changes and applies an explicit commit updater", async () => {
    const hook = renderHook(() => useRemakeStudioDraft({ scope, value, onRestore: vi.fn() }));
    await waitFor(() => expect(hook.result.current.loaded).toBe(true));
    await act(async () => {
        document.dispatchEvent(new Event("visibilitychange"));
        await Promise.resolve();
    });
    await waitFor(() => expect(calls.save).toHaveBeenCalled());
    await act(() =>
        hook.result.current.commit((current) => ({
            ...current,
            sections: {
                ...current.sections,
                repair: { baseline: null, value: { instruction: "slow" } },
            },
        })),
    );
    expect(calls.save.mock.calls.at(-1)![1].sections.repair.value.instruction).toBe("slow");
});
it("invalidates a restore callback after its account changes", async () => {
    const guards: Array<() => boolean> = [];
    const restore = vi.fn((_saved, guard: () => boolean) => {
        guards.push(guard);
    });
    const hook = renderHook(
        ({ accountId }) =>
            useRemakeStudioDraft({ scope: { ...scope, accountId }, value, onRestore: restore }),
        { initialProps: { accountId: "a" } },
    );
    await waitFor(() => expect(hook.result.current.loaded).toBe(true));
    expect(guards[0]()).toBe(true);
    hook.rerender({ accountId: "b" });
    await waitFor(() => expect(guards).toHaveLength(2));
    expect(guards[0]()).toBe(false);
    expect(guards[1]()).toBe(true);
});
