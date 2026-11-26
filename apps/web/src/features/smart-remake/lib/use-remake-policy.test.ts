// @vitest-environment jsdom
import { act, cleanup, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type {
    SmartRemakeBudgetPolicy,
    SmartRemakeProject,
    SmartRemakeRequirements,
    SmartRemakeRights,
} from "@/shared/api/smart-remake";
import { useRemakePolicy, type RemakeBusyStep } from "./use-remake-policy";
import {
    DEFAULT_REMAKE_INTENT,
    normalizeRemakeRequirements,
    remakeRightsInput,
} from "./remake-intake";

const api = vi.hoisted(() => ({
    create: vi.fn(),
    update: vi.fn(),
    inspect: vi.fn(),
    review: vi.fn(),
    approve: vi.fn(),
    restore: vi.fn(),
    remove: vi.fn(),
    export: vi.fn(),
    get: vi.fn(),
    rightsReview: vi.fn(),
}));
vi.mock("@/shared/api/smart-remake", async (original) => ({
    ...(await original<Record<string, unknown>>()),
    createSmartRemakeProject: api.create,
    updateSmartRemakeContext: api.update,
    inspectSmartRemakeSubject: api.inspect,
    reviewSmartRemakeFinding: api.review,
    approveSmartRemakeAssembly: api.approve,
    restoreSmartRemakeAssembly: api.restore,
    deleteSmartRemakeProject: api.remove,
    exportSmartRemakeAssembly: api.export,
    getSmartRemakeProject: api.get,
    reviewSmartRemakeRights: api.rightsReview,
}));

const requirements: SmartRemakeRequirements = {
    intent: "  Keep the product  ",
    keep: [" Pink ", ""],
    replace: [],
    forbid: [],
    claims: [],
    requiresCharacter: false,
};
const declaration = {
    basis: "owned" as const,
    scope: " Internal pilot ",
    evidenceNote: " Self-authored media ",
    declared: true,
    verification: { status: "reviewed", reviewedBy: "actor", reviewedAt: "now" },
};
const rights: SmartRemakeRights = {
    source: declaration,
    product: declaration,
    providerDisclosureAcknowledged: true,
};
const budget: SmartRemakeBudgetPolicy = { mode: "unlimited" };
const legacyBudget = { capUsd: "3.50", maxAttempts: 12, maxDurationSeconds: 900 };
function savedProject(patch: Partial<SmartRemakeProject> = {}): SmartRemakeProject {
    return {
        id: "owned",
        revision: 4,
        phase: "intake",
        schemaVersion: 2,
        status: "draft",
        scenes: [],
        provider: "kie",
        targetDuration: 8,
        finalVideoUrl: "/private-preview.mp4",
        sourceVideoUrl: "/source.mp4",
        productImageUrl: "/product.png",
        requirements: normalizeRemakeRequirements(requirements),
        rights: remakeRightsInput(rights),
        budget: { policy: budget },
        ...patch,
    };
}
const files = () => ({
    video: new File(["source"], "source.mp4", { type: "video/mp4" }),
    product: new File(["product"], "product.png", { type: "image/png" }),
    duration: 8 as const,
});
type Options = Parameters<typeof useRemakePolicy>[0];
function harness(project: SmartRemakeProject | null = savedProject()) {
    const errors: unknown[] = [];
    const kinds: RemakeBusyStep[] = [];
    const rememberProject = vi.fn();
    const setNotice = vi.fn();
    const validFile = vi.fn().mockReturnValue(true);
    const isLocked = vi.fn().mockReturnValue(false);
    const keys = new Map<string, string>();
    const operationKey = vi.fn((payload: unknown) => {
        const signature = JSON.stringify(payload);
        if (!keys.has(signature)) keys.set(signature, `intent-${keys.size + 1}`);
        return keys.get(signature)!;
    });
    const performOperation = vi.fn(
        async (_payload: unknown, request: (key: string) => Promise<unknown>) =>
            request("operation-key"),
    );
    const run: Options["run"] = async (kind, operation) => {
        kinds.push(kind);
        try {
            return await operation();
        } catch (error) {
            errors.push(error);
            return undefined;
        }
    };
    const hook = renderHook(
        ({ project: current }: { project: SmartRemakeProject | null }) =>
            useRemakePolicy({
                workspaceId: "workspace",
                project: current,
                run,
                rememberProject,
                operationKey,
                performOperation: performOperation as Options["performOperation"],
                validFile,
                setNotice,
                isLocked,
            }),
        { initialProps: { project } },
    );
    return {
        ...hook,
        errors,
        kinds,
        rememberProject,
        setNotice,
        validFile,
        isLocked,
        operationKey,
        performOperation,
    };
}
function fill(hook: ReturnType<typeof harness>) {
    act(() => {
        hook.result.current.onRequirementsChange(requirements);
        hook.result.current.onRightsChange(rights);
        hook.result.current.onBudgetChange(budget);
    });
}

beforeEach(() => {
    vi.clearAllMocks();
    api.create.mockResolvedValue({ project: savedProject() });
    api.get.mockResolvedValue(savedProject({ revision: 5 }));
    for (const method of [
        api.inspect,
        api.review,
        api.approve,
        api.restore,
        api.remove,
        api.rightsReview,
    ])
        method.mockResolvedValue({
            project: savedProject({ revision: 5 }),
            status: "completed",
            operationId: "operation",
        });
    api.update.mockImplementation(
        async (
            _workspace,
            _project,
            field: "requirements" | "rights" | "budget",
            input: Record<string, unknown>,
        ) => ({
            project: savedProject({
                revision: Number(input.expectedRevision) + 1,
                ...(field === "budget"
                    ? { budget: { policy: input.budget as SmartRemakeBudgetPolicy } }
                    : { [field]: input[field] }),
            }),
            status: "completed",
        }),
    );
});
afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
});

describe("policy state and owned intake", () => {
    it("starts with unrestricted usage and no claims of rights, disclosure or character consent", () => {
        const hook = harness(null);
        expect(hook.result.current.budget).toEqual(budget);
        expect(hook.result.current.rights.source.declared).toBe(false);
        expect(hook.result.current.rights.product.evidenceNote).toBe("");
        expect(hook.result.current.rights.providerDisclosureAcknowledged).toBe(false);
        expect(hook.result.current.characterFile).toBeNull();
        expect(hook.result.current.requirements.intent).toBe(DEFAULT_REMAKE_INTENT);
        expect(hook.result.current.intakeError).toContain("xác nhận quyền sử dụng tư liệu");
        hook.isLocked.mockReturnValue(true);
        fill(hook);
        act(() =>
            hook.result.current.onCharacterChange(
                new File(["person"], "person.png", { type: "image/png" }),
            ),
        );
        expect(hook.result.current.requirements.intent).toBe(DEFAULT_REMAKE_INTENT);
        expect(hook.result.current.budget).toEqual(budget);
        expect(hook.result.current.characterFile).toBeNull();
    });
    it("restores snapshots while stripping server verification from future mutation input", () => {
        const hook = harness(null);
        act(() => hook.result.current.loadContext(savedProject({ rights })));
        expect(hook.result.current.requirements).toEqual(normalizeRemakeRequirements(requirements));
        expect(hook.result.current.budget).toEqual(budget);
        expect(hook.result.current.rights.source).not.toHaveProperty("verification");
        expect(hook.result.current.intakeError).toBeNull();
        act(() =>
            hook.result.current.loadContext(
                savedProject({ requirements: undefined, rights: undefined, budget: undefined }),
            ),
        );
        expect(hook.result.current.budget).toEqual(budget);
    });
    it("compares canonical request fields without JSONB key order or server budget metadata", async () => {
        const saved = savedProject({
            requirements: {
                requiresCharacter: false,
                claims: [],
                forbid: [],
                replace: [],
                keep: ["Pink"],
                intent: "Keep the product",
                characterReferencePolicy: "product_and_character",
            },
            budget: {
                policy: Object.assign(
                    { mode: "unlimited" as const },
                    { startedAt: "2026-11-25T00:00:00Z" },
                ),
            },
        });
        const hook = harness(saved);
        fill(hook);
        expect(hook.result.current.contextDirty).toBe(false);
        act(() => hook.result.current.loadContext(saved));
        expect(hook.result.current.budget).toEqual(budget);
        await act(async () => {
            await hook.result.current.saveContext();
        });
        expect(api.update).not.toHaveBeenCalled();
    });
    it("restores exhausted legacy limits as unrestricted local policy without mutating the server", () => {
        const saved = savedProject({
            budget: { policy: { capUsd: "0", maxAttempts: 0, maxDurationSeconds: 1 } },
        });
        const hook = harness(saved);
        act(() => hook.result.current.loadContext(saved));
        expect(hook.result.current.budget).toEqual(budget);
        expect(hook.result.current.intakeError).toBeNull();
        expect(hook.result.current.contextDirty).toBe(true);
        expect(api.update).not.toHaveBeenCalled();
    });
    it("synchronizes a restored finite policy before continuing with the latest revision", async () => {
        const saved = savedProject({ budget: { policy: legacyBudget } });
        const hook = harness(saved);
        act(() => hook.result.current.loadContext(saved));
        let updated!: SmartRemakeProject;
        await act(async () => {
            updated = await hook.result.current.prepareProject({ video: null, duration: 8 });
        });
        expect(api.create).not.toHaveBeenCalled();
        expect(api.update).toHaveBeenCalledExactlyOnceWith("workspace", "owned", "budget", {
            expectedRevision: 4,
            idempotencyKey: "intent-1",
            budget,
        });
        expect(updated.revision).toBe(5);
        expect(updated.budget?.policy).toEqual(budget);
    });
    it("preserves the identity of a failed finite-policy upgrade without submitting AI", async () => {
        const saved = savedProject({ budget: { policy: legacyBudget } });
        const hook = harness(saved);
        act(() => hook.result.current.loadContext(saved));
        api.update.mockRejectedValueOnce(new Error("connection lost"));
        await expect(hook.result.current.syncContext(saved)).rejects.toThrow("connection lost");
        await act(async () => {
            await hook.result.current.syncContext(saved);
        });
        expect(api.update.mock.calls[1][3]).toEqual(api.update.mock.calls[0][3]);
        expect(api.create).not.toHaveBeenCalled();
        expect(api.inspect).not.toHaveBeenCalled();
    });
    it("canonicalizes legacy compatibility edits and explicit snapshots without changing rights or requirements", () => {
        const hook = harness(null);
        act(() => hook.result.current.onBudgetChange(legacyBudget));
        expect(hook.result.current.budget).toEqual(budget);
        act(() =>
            hook.result.current.applySnapshot({ requirements, rights, budget: legacyBudget }),
        );
        expect(hook.result.current.budget).toEqual(budget);
        expect(hook.result.current.requirements).toEqual(requirements);
        expect(hook.result.current.rights).toEqual(remakeRightsInput(rights));
    });
    it("uploads unrestricted intake and syncs unrestricted context even for an explicit finite snapshot", async () => {
        const hook = harness(null);
        await act(async () => {
            await hook.result.current.prepareProject({
                ...files(),
                snapshot: { requirements, rights, budget: legacyBudget },
            });
        });
        expect(api.create.mock.calls[0][1].metadata.budget).toEqual(budget);
        expect(api.create.mock.calls[0][1].metadata.requirements).toEqual(
            normalizeRemakeRequirements(requirements),
        );
        expect(api.create.mock.calls[0][1].metadata.rights).toEqual(remakeRightsInput(rights));
        expect(api.update).not.toHaveBeenCalled();
    });
    it("validates a character image and allows its explicit removal", () => {
        const hook = harness(null),
            image = new File(["person"], "person.png", { type: "image/png" });
        hook.validFile.mockReturnValue(false);
        act(() => hook.result.current.onCharacterChange(image));
        expect(hook.result.current.characterFile).toBeNull();
        hook.validFile.mockReturnValue(true);
        act(() => hook.result.current.onCharacterChange(image));
        expect(hook.result.current.characterFile).toBe(image);
        act(() => hook.result.current.onCharacterChange(null));
        expect(hook.result.current.characterFile).toBeNull();
    });
    it("uploads an owned intake once and reuses its identity after it is remembered", async () => {
        const hook = harness(null),
            input = files();
        fill(hook);
        let created!: SmartRemakeProject;
        await act(async () => {
            created = await hook.result.current.prepareProject(input);
        });
        const request = api.create.mock.calls[0][1];
        expect(request.metadata.requirements).toEqual(normalizeRemakeRequirements(requirements));
        expect(request.metadata.rights.source.verification).toBeUndefined();
        expect(request.referenceVideo).toBe(input.video);
        expect(request.productImage).toBe(input.product);
        expect(request.metadata.budget).toEqual(budget);
        expect(hook.rememberProject).toHaveBeenCalledWith(created);
        hook.rerender({ project: created });
        await act(async () => {
            await hook.result.current.prepareProject(input);
        });
        expect(api.create).toHaveBeenCalledTimes(1);
        expect(api.update).not.toHaveBeenCalled();
    });
    it("reuses restored file bytes only when they match the current owned media hashes", async () => {
        const input = files();
        const saved = savedProject({
            inputMediaHashes: {
                source: "41cf6794ba4200b839c53531555f0f3998df4cbb01a4d5cb0b94e3ca5e23947d",
                product: "a8792157cb4f27fb949c035f45518c61e884bb86e6f420204379c2baa8beb66e",
            },
        });
        const hook = harness(saved);
        act(() => hook.result.current.loadContext(saved));
        const restored = await hook.result.current.restoreIntakeBinding(saved, {
            video: input.video,
            product: input.product,
            character: null,
        });
        expect(restored).toBe(true);
        expect(hook.result.current.hasCurrentIntake(input.video, input.product, undefined, 8)).toBe(
            true,
        );
        await hook.result.current.prepareProject(input);
        expect(api.create).not.toHaveBeenCalled();
    });
    it("does not bind a restored draft with different bytes or absent server hashes", async () => {
        const hook = harness();
        const input = files();
        expect(
            await hook.result.current.restoreIntakeBinding(savedProject(), {
                video: input.video,
                product: input.product,
                character: null,
            }),
        ).toBe(false);
        expect(hook.result.current.hasCurrentIntake(input.video, input.product, undefined, 8)).toBe(
            false,
        );
    });
    it("abandons restored byte binding when the account changes during hashing", async () => {
        const saved = savedProject({
            inputMediaHashes: {
                source: "41cf6794ba4200b839c53531555f0f3998df4cbb01a4d5cb0b94e3ca5e23947d",
                product: "a8792157cb4f27fb949c035f45518c61e884bb86e6f420204379c2baa8beb66e",
            },
        });
        const hook = harness(saved),
            input = files();
        expect(
            await hook.result.current.restoreIntakeBinding(
                saved,
                { video: input.video, product: input.product, character: null },
                () => false,
            ),
        ).toBe(false);
        expect(hook.result.current.getIntakeBinding()).toBeNull();
    });
    it.each([false, true])(
        "prepares automatic remake without writing a goal (cleared=%s)",
        async (cleared) => {
            const hook = harness(null);
            act(() => {
                hook.result.current.onRightsChange(rights);
                hook.result.current.onBudgetChange(budget);
                if (cleared)
                    hook.result.current.onRequirementsChange({
                        ...hook.result.current.requirements,
                        intent: "",
                    });
            });
            expect(hook.result.current.intakeError).toBeNull();
            await act(async () => {
                await hook.result.current.prepareProject(files());
            });
            const request = api.create.mock.calls[0][1];
            expect(request.metadata.requirements.intent).toBe(DEFAULT_REMAKE_INTENT);
            expect(request.metadata.requirements.claims).toEqual([]);
            expect(request.metadata.budget).toEqual(budget);
            expect(hook.errors).toEqual([]);
        },
    );
    it("keeps the same unpaid intake idempotency key for an unchanged failed request", async () => {
        const hook = harness(null),
            input = files();
        fill(hook);
        api.create.mockRejectedValueOnce(new Error("connection lost"));
        await act(async () => {
            await expect(hook.result.current.prepareProject(input)).rejects.toThrow(
                "connection lost",
            );
        });
        await act(async () => {
            await hook.result.current.prepareProject(input);
        });
        expect(api.create.mock.calls[1][1].metadata.idempotencyKey).toBe(
            api.create.mock.calls[0][1].metadata.idempotencyKey,
        );
    });
    it("uses a new intake identity when pending metadata or duration changes", async () => {
        const hook = harness(null),
            input = files();
        fill(hook);
        api.create.mockRejectedValueOnce(new Error("connection lost"));
        await expect(hook.result.current.prepareProject(input)).rejects.toThrow("connection lost");
        act(() => hook.result.current.onBudgetChange({ ...legacyBudget, capUsd: "4.75" }));
        await act(async () => {
            await hook.result.current.prepareProject({ ...input, duration: 16 });
        });
        expect(api.create.mock.calls[1][1].metadata.idempotencyKey).not.toBe(
            api.create.mock.calls[0][1].metadata.idempotencyKey,
        );
        expect(api.create.mock.calls[1][1].metadata.targetDuration).toBe(16);
        expect(api.create.mock.calls[1][1].metadata.budget).toEqual(budget);
    });
    it("requires source reupload before replacing product or character of a reloaded project", async () => {
        const hook = harness();
        fill(hook);
        await act(async () => {
            await expect(
                hook.result.current.prepareProject({
                    video: null,
                    product: files().product,
                    duration: 8,
                }),
            ).rejects.toThrow("Thêm lại video mẫu");
        });
        await act(async () => {
            await expect(
                hook.result.current.prepareProject({
                    video: null,
                    productUrl: "https://shop.example/product",
                    duration: 8,
                }),
            ).rejects.toThrow("Thêm lại video mẫu");
        });
        act(() =>
            hook.result.current.onCharacterChange(
                new File(["person"], "person.png", { type: "image/png" }),
            ),
        );
        await act(async () => {
            await expect(
                hook.result.current.prepareProject({ video: null, duration: 8 }),
            ).rejects.toThrow("Thêm lại video mẫu");
        });
        expect(api.create).not.toHaveBeenCalled();
        expect(api.update).not.toHaveBeenCalled();
    });
    it("requires retained identity when neither uploads nor a saved intake exist", async () => {
        const hook = harness(null);
        await expect(
            hook.result.current.prepareProject({ video: null, duration: 8 }),
        ).rejects.toThrow("Lưu tư liệu");
    });
    it("records normalized metadata edits in revision order without echoing verification", async () => {
        const hook = harness(savedProject({ budget: { policy: legacyBudget } }));
        fill(hook);
        act(() => {
            hook.result.current.onRequirementsChange({ ...requirements, intent: " New intent " });
            hook.result.current.onRightsChange({
                ...rights,
                source: { ...declaration, scope: "New scope" },
            });
            hook.result.current.onBudgetChange({ ...legacyBudget, capUsd: "4.25" });
        });
        await act(async () => {
            await hook.result.current.saveContext();
        });
        expect(api.update.mock.calls.map((args) => [args[2], args[3].expectedRevision])).toEqual([
            ["requirements", 4],
            ["rights", 5],
            ["budget", 6],
        ]);
        expect(api.update.mock.calls[0][3].requirements.intent).toBe("New intent");
        expect(api.update.mock.calls[1][3].rights.source).not.toHaveProperty("verification");
        expect(api.update.mock.calls[2][3].budget).toEqual(budget);
        expect(hook.kinds).toContain("context");
        expect(hook.setNotice).toHaveBeenCalledWith(expect.not.stringContaining("ngân sách"));
    });
    it("resolves a linked product to uploaded image bytes and fails closed on unavailable media", async () => {
        const hook = harness(null),
            input = {
                video: files().video,
                duration: 8 as const,
                productUrl: "https://shop.example/product",
                productImageUrl: "/owned-image",
            };
        fill(hook);
        const fetch = vi.fn().mockResolvedValue({ ok: false });
        vi.stubGlobal("fetch", fetch);
        await expect(hook.result.current.prepareProject(input)).rejects.toThrow(
            "Chưa tải được ảnh",
        );
        fetch.mockResolvedValue({
            ok: true,
            blob: async () => new Blob(["product"], { type: "image/webp" }),
        });
        hook.validFile.mockReturnValue(false);
        await expect(hook.result.current.prepareProject(input)).rejects.toThrow(
            "Ảnh từ link chưa hợp lệ",
        );
        hook.validFile.mockReturnValue(true);
        await act(async () => {
            await hook.result.current.prepareProject(input);
        });
        expect(api.create.mock.calls[0][1].productImage.type).toBe("image/webp");
        const empty = harness(null);
        fill(empty);
        await expect(
            empty.result.current.prepareProject({ video: files().video, duration: 8 }),
        ).rejects.toThrow("Thêm ảnh sản phẩm");
    });
    it("retains the optional original character file in intake", async () => {
        const hook = harness(null);
        fill(hook);
        const character = new File(["person"], "person.png", { type: "image/png" });
        act(() => hook.result.current.onCharacterChange(character));
        await act(async () => {
            await hook.result.current.prepareProject(files());
        });
        expect(api.create.mock.calls[0][1].characterImage).toBe(character);
    });
});

describe("persisted policy mutations", () => {
    const actions = [
        [
            "inspect",
            "inspect",
            { subject: { kind: "scene", sceneId: "scene", versionId: "version" } },
        ],
        [
            "review",
            "review",
            {
                reportId: "report",
                findingId: "finding",
                decision: "accept",
                reason: "Viewed evidence",
            },
        ],
        ["approve", "approve", { assemblyId: "assembly", reportId: "report" }],
        ["restore", "restore", { assemblyId: "old" }],
        ["deleteProject", "remove", { reason: "Rights withdrawn" }],
        ["rightsReview", "rightsReview", { evidenceNote: "Human reviewed evidence" }],
    ] as const;
    const call = (hook: ReturnType<typeof harness>, action: string) => {
        switch (action) {
            case "inspect":
                return hook.result.current.inspect({
                    kind: "scene",
                    sceneId: "scene",
                    versionId: "version",
                });
            case "review":
                return hook.result.current.review("report", "finding", "accept", "Viewed evidence");
            case "approve":
                return hook.result.current.approve("assembly", "report");
            case "restore":
                return hook.result.current.restore("old");
            case "rightsReview":
                return hook.result.current.rightsReview("Human reviewed evidence");
            default:
                return hook.result.current.deleteProject("Rights withdrawn");
        }
    };
    it.each(actions)(
        "sends %s with current revision and operation identity",
        async (action, method, payload) => {
            const hook = harness();
            await act(async () => {
                await call(hook, action);
            });
            expect(api[method]).toHaveBeenCalledWith("workspace", "owned", {
                expectedRevision: 4,
                idempotencyKey: "operation-key",
                ...payload,
            });
            expect(hook.rememberProject).toHaveBeenCalledWith(
                expect.objectContaining({ revision: 5 }),
            );
        },
    );
    it.each(actions)(
        "propagates %s API rejection without replacing retained media",
        async (action, method) => {
            const hook = harness();
            api[method].mockRejectedValue(new Error("blocked"));
            await act(async () => {
                await expect(call(hook, action)).rejects.toThrow("Chưa hoàn tất thao tác");
            });
            expect(hook.rememberProject).not.toHaveBeenCalled();
            expect(hook.errors[0]).toMatchObject({ message: "blocked" });
        },
    );
    it("keeps a failed operation's returned project but reports its failure", async () => {
        const hook = harness();
        api.approve.mockResolvedValue({ project: savedProject({ revision: 5 }), status: "failed" });
        await act(async () => {
            await expect(hook.result.current.approve("assembly", "report")).rejects.toThrow(
                "Chưa hoàn tất thao tác",
            );
        });
        expect(hook.rememberProject).toHaveBeenCalled();
    });
    it("retains durable running operation state for later polling", async () => {
        const hook = harness();
        api.inspect.mockResolvedValue({
            project: savedProject({
                pendingOperation: {
                    id: "inspection",
                    status: "running",
                    needsReconciliation: false,
                },
            }),
            status: "running",
        });
        await act(async () => {
            await hook.result.current.inspect({ kind: "assembly", assemblyId: "assembly" });
        });
        expect(hook.rememberProject).toHaveBeenCalledWith(
            expect.objectContaining({
                pendingOperation: expect.objectContaining({ id: "inspection" }),
            }),
        );
    });
    it("refreshes authoritative project after a mutation returns bare metadata", async () => {
        const hook = harness();
        api.approve.mockResolvedValue({ id: "approval", status: "approved" });
        await act(async () => {
            await hook.result.current.approve("assembly", "report");
        });
        expect(api.get).toHaveBeenCalledWith("workspace", "owned");
        expect(hook.rememberProject).toHaveBeenCalledWith(expect.objectContaining({ revision: 5 }));
    });
    it("reports a failed authoritative refresh rather than inventing a completed project", async () => {
        const hook = harness();
        api.restore.mockResolvedValue({ id: "restored" });
        api.get.mockRejectedValue(new Error("refresh unavailable"));
        await act(async () => {
            await expect(hook.result.current.restore("old")).rejects.toThrow(
                "Chưa hoàn tất thao tác",
            );
        });
        expect(hook.rememberProject).not.toHaveBeenCalled();
    });
    it("does not mutate an absent project", async () => {
        const hook = harness(null);
        for (const [action] of actions) await call(hook, action);
        await hook.result.current.saveContext();
        expect(hook.performOperation).not.toHaveBeenCalled();
        expect(api.update).not.toHaveBeenCalled();
    });
});

describe("checked export", () => {
    it("requires an active approval and never falls back to a preview URL", async () => {
        const hook = harness(),
            click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
        await expect(hook.result.current.exportAssembly("assembly")).rejects.toThrow(
            "Duyệt đúng thành phẩm",
        );
        expect(api.export).not.toHaveBeenCalled();
        expect(click).not.toHaveBeenCalled();
    });
    it("downloads only the URL returned by checked export using current approval and revision", async () => {
        const project = savedProject({ release: { activeApprovalId: "approval" } });
        const hook = harness(project),
            urls: string[] = [];
        vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
            this: HTMLAnchorElement,
        ) {
            urls.push(this.href);
            expect(this.rel).toBe("noopener noreferrer");
        });
        api.export.mockResolvedValue({
            downloadUrl: "https://files.example/checked-ai.mp4",
            project: savedProject({ revision: 5 }),
        });
        await act(async () => {
            await hook.result.current.exportAssembly("assembly");
        });
        expect(api.export).toHaveBeenCalledWith(
            "workspace",
            "owned",
            expect.objectContaining({
                expectedRevision: 4,
                assemblyId: "assembly",
                approvalId: "approval",
                idempotencyKey: expect.any(String),
            }),
        );
        expect(urls).toEqual(["https://files.example/checked-ai.mp4"]);
        expect(hook.rememberProject).toHaveBeenCalledWith(expect.objectContaining({ revision: 5 }));
        expect(hook.setNotice).toHaveBeenCalledWith(expect.stringContaining("có nhãn AI"));
    });
    it("refreshes the authoritative revision after a bare checked-export response", async () => {
        const hook = harness(savedProject({ release: { activeApprovalId: "approval" } }));
        const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
        api.export.mockResolvedValue({ downloadUrl: "https://files.example/checked-ai.mp4" });
        api.get.mockResolvedValue(savedProject({ revision: 5 }));
        await act(async () => {
            await hook.result.current.exportAssembly("assembly");
        });
        expect(api.get).toHaveBeenCalledWith("workspace", "owned");
        expect(hook.rememberProject).toHaveBeenCalledWith(expect.objectContaining({ revision: 5 }));
        expect(click).toHaveBeenCalledOnce();
    });
    it.each(["missing_url", "api_error"])(
        "refuses export on %s without opening retained preview media",
        async (kind) => {
            const hook = harness(savedProject({ release: { activeApprovalId: "approval" } }));
            const click = vi
                .spyOn(HTMLAnchorElement.prototype, "click")
                .mockImplementation(() => {});
            if (kind === "api_error") api.export.mockRejectedValue(new Error("stale approval"));
            else api.export.mockResolvedValue({ project: savedProject() });
            await act(async () => {
                await expect(hook.result.current.exportAssembly("assembly")).rejects.toThrow(
                    "Chưa tải được video",
                );
            });
            expect(click).not.toHaveBeenCalled();
            expect(hook.rememberProject).not.toHaveBeenCalled();
        },
    );
});
