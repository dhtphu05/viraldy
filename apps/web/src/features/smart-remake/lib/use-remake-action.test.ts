// @vitest-environment jsdom
import { act, cleanup, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { SmartRemakePreflight, SmartRemakePreflightAction } from "@/shared/api/smart-remake";
import { useRemakeAction } from "./use-remake-action";
import type { RemakeActionIntent, RemakeActionSnapshot } from "./remake-action";
import { ApiError } from "@/shared/api/errors";
const calls = vi.hoisted(() => ({ preflight: vi.fn(), execute: vi.fn() }));
vi.mock("@/shared/api/smart-remake", () => ({ getSmartRemakePreflight: calls.preflight }));
const budget = { capUsd: "1.50", maxAttempts: 10, maxDurationSeconds: 2000 };
const snapshot = {
    requirements: {
        intent: "keep product",
        keep: [],
        replace: [],
        forbid: [],
        claims: [],
        requiresCharacter: false,
    },
    rights: {
        source: { basis: "owned", scope: "mine", declared: true, evidenceNote: "mine" },
        product: { basis: "owned", scope: "mine", declared: true, evidenceNote: "mine" },
        providerDisclosureAcknowledged: true,
    },
    budget,
} satisfies RemakeActionSnapshot;
const quote = (action: SmartRemakePreflightAction = "analyze") =>
    ({
        action,
        contextHash: "same",
        mode: "fixture",
        scope: { targetDuration: 8, sceneCount: 1, groupCount: 1, imageCount: 1 },
        calls: { analysis: 3, image: 0, video: 0, inspection: 0, total: 3 },
        budget: {
            knownActualUsd: "0",
            reservedUsd: "0",
            exposureUsd: "0",
            additionalReservationUsd: "1.5",
            minimumCapUsd: "1.5",
            minimumMaxAttempts: 3,
            minimumDurationSeconds: 1800,
            recommended: budget,
        },
        blockers: [],
    }) as SmartRemakePreflight;
const intent = (action: SmartRemakePreflightAction): RemakeActionIntent =>
    action === "repair"
        ? {
              action,
              fingerprint: "materials",
              sceneId: "s",
              baseVersionId: "v",
              draft: { prompt: "p", imagePrompt: "i", videoPrompt: "v" },
          }
        : action === "inspect"
          ? {
                action,
                fingerprint: "materials",
                subject: { kind: "scene", sceneId: "s", versionId: "v" },
            }
          : { action, fingerprint: "materials" };
function harness() {
    return renderHook(
        ({ fingerprint }) =>
            useRemakeAction({
                workspaceId: "w",
                fingerprint,
                request: (action) => ({ action: action.action }),
                validate: () => null,
                execute: calls.execute,
            }),
        { initialProps: { fingerprint: "materials" } },
    );
}
beforeEach(() => {
    vi.clearAllMocks();
    calls.preflight.mockImplementation(async (_w, request) => quote(request.action));
    calls.execute.mockResolvedValue(true);
});
afterEach(cleanup);
describe("explicit AI action confirmation", () => {
    it("executes an already-authorized action without opening a grant modal and ignores a rapid second click", async () => {
        let finish!: (value: boolean) => void;
        calls.execute.mockImplementation(
            () =>
                new Promise((resolve) => {
                    finish = resolve;
                }),
        );
        const hook = harness();
        const approved = { ...snapshot, budget: { mode: "unlimited" as const } };
        let first!: Promise<unknown>;
        act(() => {
            first = hook.result.current.openAction(intent("render"), approved);
            void hook.result.current.openAction(intent("render"), approved);
        });
        await act(async () => {
            await Promise.resolve();
            await Promise.resolve();
        });
        expect(hook.result.current.pendingAction).toBeNull();
        expect(hook.result.current.actionExecutingIntent?.action).toBe("render");
        expect(calls.execute).toHaveBeenCalledTimes(1);
        expect(calls.execute.mock.calls[0][1].budget).toEqual({ mode: "unlimited" });
        await act(async () => {
            finish(true);
            await first;
        });
        expect(hook.result.current.actionExecutingIntent).toBeNull();
    });
    it("does not execute a direct action after its studio unmounts while preflight is pending", async () => {
        let quoteResult!: (value: SmartRemakePreflight) => void;
        calls.preflight.mockReturnValueOnce(
            new Promise((resolve) => {
                quoteResult = resolve;
            }),
        );
        const hook = harness();
        let pending!: Promise<unknown>;
        act(() => {
            pending = hook.result.current.openAction(intent("analyze"), {
                ...snapshot,
                budget: { mode: "unlimited" },
            });
        });
        hook.unmount();
        await act(async () => {
            quoteResult(quote("analyze"));
            await pending;
        });
        expect(calls.execute).not.toHaveBeenCalled();
    });
    it("retains a planning error code for task recovery and clears it when closing", async () => {
        calls.execute.mockRejectedValueOnce(
            new ApiError(
                "SMART_REMAKE_TIMELINE_DENSITY_UNSUPPORTED",
                "Too many cuts for output frames",
                400,
            ),
        );
        const hook = harness();
        await act(() => hook.result.current.openAction(intent("analyze")));
        await act(() => hook.result.current.confirmAction(snapshot));
        expect(hook.result.current.actionErrorCode).toBe(
            "SMART_REMAKE_TIMELINE_DENSITY_UNSUPPORTED",
        );
        act(() => hook.result.current.cancelAction());
        expect(hook.result.current.actionErrorCode).toBeNull();
    });
    it.each(["analyze", "reanalyze", "render", "repair", "inspect"] as const)(
        "only executes %s after confirming a fresh read-only proposal",
        async (action) => {
            const hook = harness();
            await act(() => hook.result.current.openAction(intent(action)));
            expect(calls.preflight).toHaveBeenCalledTimes(1);
            expect(calls.execute).not.toHaveBeenCalled();
            expect(hook.result.current.pendingAction?.action).toBe(action);
            await act(() => hook.result.current.confirmAction(snapshot));
            expect(calls.preflight).toHaveBeenCalledTimes(2);
            expect(calls.execute).toHaveBeenCalledWith(intent(action), snapshot);
            expect(hook.result.current.pendingAction).toBeNull();
        },
    );
    it("cancels without executing and ignores an old proposal returned after cancellation", async () => {
        const hook = harness();
        let resolve!: (p: SmartRemakePreflight) => void;
        calls.preflight.mockReturnValueOnce(
            new Promise((r) => {
                resolve = r;
            }),
        );
        let opened!: Promise<void>;
        act(() => {
            opened = hook.result.current.openAction(intent("analyze"));
        });
        act(() => hook.result.current.cancelAction());
        await act(async () => {
            resolve(quote());
            await opened;
        });
        expect(hook.result.current.pendingAction).toBeNull();
        expect(hook.result.current.actionPreflight).toBeNull();
        expect(calls.execute).not.toHaveBeenCalled();
    });
    it("rejects stale material snapshots and prevents double-confirm submissions", async () => {
        const hook = harness();
        await act(() => hook.result.current.openAction(intent("analyze")));
        hook.rerender({ fingerprint: "changed" });
        await act(async () => {
            expect(await hook.result.current.confirmAction(snapshot)).toBe("invalid");
        });
        expect(calls.execute).not.toHaveBeenCalled();
        hook.rerender({ fingerprint: "materials" });
        await act(async () => {
            await Promise.all([
                hook.result.current.confirmAction(snapshot),
                hook.result.current.confirmAction(snapshot),
            ]);
        });
        expect(calls.execute).toHaveBeenCalledTimes(1);
    });
    it("refreshes changed pricing and needs a second explicit confirmation", async () => {
        const hook = harness();
        await act(() => hook.result.current.openAction(intent("analyze")));
        calls.preflight.mockResolvedValue({ ...quote(), contextHash: "new-pricing" });
        await act(async () => {
            expect(await hook.result.current.confirmAction(snapshot)).toBe("changed");
        });
        expect(calls.execute).not.toHaveBeenCalled();
        await act(() => hook.result.current.confirmAction(snapshot));
        expect(calls.execute).toHaveBeenCalledTimes(1);
    });
    it("does not submit when the server requires reconciliation", async () => {
        const hook = harness();
        await act(() => hook.result.current.openAction(intent("render")));
        calls.preflight.mockResolvedValue({
            ...quote("render"),
            blockers: [{ code: "pending", message: "Kiểm tra trạng thái", action: "reconcile" }],
        });
        await act(() => hook.result.current.confirmAction(snapshot));
        expect(calls.execute).not.toHaveBeenCalled();
        expect(hook.result.current.actionError).toContain("Kiểm tra trạng thái");
    });
});

it("retries a failed preview without executing and shows a failed execution for manual recovery", async () => {
    const hook = harness();
    calls.preflight.mockRejectedValueOnce(new Error("Preview unavailable"));
    await act(() => hook.result.current.openAction(intent("analyze")));
    expect(hook.result.current.actionError).toBe("Preview unavailable");
    expect(calls.execute).not.toHaveBeenCalled();
    await act(() => hook.result.current.retryAction());
    expect(hook.result.current.actionPreflight).not.toBeNull();
    calls.execute.mockRejectedValueOnce(new Error("Receipt unavailable; reconcile first"));
    await act(() => hook.result.current.confirmAction(snapshot));
    expect(hook.result.current.actionError).toContain("reconcile first");
    expect(hook.result.current.pendingAction).not.toBeNull();
    act(() => hook.result.current.cancelAction());
    await act(() => hook.result.current.retryAction());
    await act(async () => {
        expect(await hook.result.current.confirmAction(snapshot)).toBe("blocked");
    });
});
it("does not accept an intent that became stale while refreshing its final preflight", async () => {
    const hook = harness();
    await act(() => hook.result.current.openAction(intent("analyze")));
    let resolve!: (value: SmartRemakePreflight) => void;
    calls.preflight.mockReturnValueOnce(
        new Promise((r) => {
            resolve = r;
        }),
    );
    let confirming!: Promise<unknown>;
    act(() => {
        confirming = hook.result.current.confirmAction(snapshot);
    });
    // Escape cannot dismiss a confirmation after the explicit submission boundary starts.
    act(() => hook.result.current.cancelAction());
    expect(hook.result.current.pendingAction).not.toBeNull();
    hook.rerender({ fingerprint: "new material" });
    await act(async () => {
        resolve(quote());
        expect(await confirming).toBe("invalid");
    });
    expect(calls.execute).not.toHaveBeenCalled();
});
it("validates material input before fetching and never creates a pending action for invalid media", async () => {
    const hook = renderHook(() =>
        useRemakeAction({
            workspaceId: "w",
            fingerprint: "materials",
            request: () => ({ action: "analyze" }),
            validate: () => "Thêm video mẫu",
            execute: calls.execute,
        }),
    );
    await act(() => hook.result.current.openAction(intent("analyze")));
    expect(hook.result.current.actionError).toBe("Thêm video mẫu");
    expect(hook.result.current.pendingAction).toBeNull();
    expect(calls.preflight).not.toHaveBeenCalled();
});

it("keeps an unsuccessful operation open with the operation error instead of losing it behind the modal", async () => {
    const hook = renderHook(() =>
        useRemakeAction({
            workspaceId: "w",
            fingerprint: "materials",
            request: () => ({ action: "analyze" }),
            validate: () => null,
            execute: calls.execute,
            failureMessage: () => "Chưa nhận receipt; kiểm tra trạng thái",
        }),
    );
    calls.execute.mockResolvedValueOnce(false);
    await act(() => hook.result.current.openAction(intent("analyze")));
    await act(() => hook.result.current.confirmAction(snapshot));
    expect(hook.result.current.pendingAction).not.toBeNull();
    expect(hook.result.current.actionError).toContain("receipt");
});

describe("confirmed policy snapshot identity", () => {
    it("captures confirmed policy values before the asynchronous preflight", async () => {
        const hook = harness();
        await act(() => hook.result.current.openAction(intent("analyze")));
        let finish!: (value: SmartRemakePreflight) => void;
        calls.preflight.mockReturnValueOnce(
            new Promise((resolve) => {
                finish = resolve;
            }),
        );
        const approved = structuredClone(snapshot);
        let confirmation!: Promise<unknown>;
        act(() => {
            confirmation = hook.result.current.confirmAction(approved);
        });
        approved.budget.capUsd = "99.00";
        approved.rights.source.scope = "Changed outside confirmation";
        await act(async () => {
            finish(quote());
            await confirmation;
        });
        expect(calls.execute).toHaveBeenCalledWith(intent("analyze"), snapshot);
    });
});
