import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "./smart-remake";
import * as intakeUploads from "./smart-remake-uploads";

afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
});
const response = (data: unknown) => Response.json({ data, meta: { requestId: "fixture" } });

describe("Smart Remake owned project boundaries", () => {
    it("forwards cancellation only when an owned project read supplies a signal", async () => {
        const fetch = vi.fn().mockResolvedValue(response({ id: "owned" }));
        vi.stubGlobal("fetch", fetch);
        const controller = new AbortController();
        await api.getSmartRemakeProject("workspace", "owned", { signal: controller.signal });
        expect(fetch).toHaveBeenCalledWith(
            "/api/backend/workspaces/workspace/smart-remake/projects/owned",
            expect.objectContaining({ signal: controller.signal }),
        );
        expect(fetch.mock.calls[0][1].method).toBeUndefined();
    });
    it("retains inputs and declarations in intake without compiling or rendering", async () => {
        const project = { id: "owned", revision: 1, phase: "intake" };
        const fetch = vi.fn().mockResolvedValue(response({ project }));
        vi.stubGlobal("fetch", fetch);
        const metadata = { idempotencyKey: "intake-1", targetDuration: 8 };
        const source = new File(["source"], "source.mp4", { type: "video/mp4" });
        const product = new File(["product"], "product.png", { type: "image/png" });
        vi.spyOn(intakeUploads, "uploadSmartRemakeInputs").mockResolvedValue({
            sourceAssetVersionId: "source-version",
            productAssetVersionId: "product-version",
        });
        await expect(
            api.createSmartRemakeProject("workspace", {
                metadata: metadata as api.SmartRemakeIntakeMetadata,
                referenceVideo: source,
                productImage: product,
            }),
        ).resolves.toEqual({ project });
        expect(fetch).toHaveBeenCalledTimes(1);
        expect(fetch.mock.calls[0][0]).toBe(
            "/api/backend/workspaces/workspace/smart-remake/projects/from-assets",
        );
        expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({
            metadata,
            sourceAssetVersionId: "source-version",
            productAssetVersionId: "product-version",
        });
    });

    it("compiles the owned intake and revision without replacing retained media", async () => {
        const fetch = vi.fn().mockResolvedValue(response({ projectId: "owned" }));
        vi.stubGlobal("fetch", fetch);
        await api.compileSmartRemake("workspace", {
            projectId: "owned",
            expectedRevision: 1,
            idempotencyKey: "analysis-1",
            targetDuration: 8,
            timelineMode: "reference",
            language: "vi",
            prompt: "intent",
            description: "",
        });
        const body = fetch.mock.calls[0][1].body as FormData;
        expect(body.get("projectId")).toBe("owned");
        expect(body.get("expectedRevision")).toBe("1");
        expect(body.get("idempotencyKey")).toBe("analysis-1");
        expect(body.has("referenceVideo")).toBe(false);
        expect(body.has("productImage")).toBe(false);
    });

    it.each([
        [
            "inspections",
            "inspectSmartRemakeSubject",
            { subject: { kind: "assembly", assemblyId: "a" } },
        ],
        [
            "inspection-reviews",
            "reviewSmartRemakeFinding",
            {
                reportId: "report",
                findingId: "finding",
                decision: "accept",
                reason: "Reviewed original evidence",
            },
        ],
        ["approvals", "approveSmartRemakeAssembly", { assemblyId: "a", reportId: "report" }],
        ["exports", "exportSmartRemakeAssembly", { assemblyId: "a", approvalId: "approval" }],
        ["restore", "restoreSmartRemakeAssembly", { assemblyId: "old" }],
        ["deletions", "deleteSmartRemakeProject", { reason: "Stop using input" }],
    ])(
        "posts %s with stable mutation identity and no artifact URL",
        async (path, method, extra) => {
            const fetch = vi.fn().mockResolvedValue(response({ status: "completed" }));
            vi.stubGlobal("fetch", fetch);
            const input = { expectedRevision: 7, idempotencyKey: `fixture-${path}`, ...extra };
            const request = api[method as keyof typeof api] as unknown as (
                w: string,
                p: string,
                i: unknown,
            ) => Promise<unknown>;
            await request("workspace", "owned", input);
            expect(fetch.mock.calls[0][0]).toBe(
                `/api/backend/workspaces/workspace/smart-remake/projects/owned/${path}`,
            );
            expect(fetch.mock.calls[0][1].method).toBe("POST");
            expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual(input);
        },
    );

    it.each(["requirements", "rights", "budget"] as const)(
        "patches %s through its owned endpoint",
        async (field) => {
            const fetch = vi.fn().mockResolvedValue(response({ project: { id: "owned" } }));
            vi.stubGlobal("fetch", fetch);
            const input = { expectedRevision: 8, idempotencyKey: `edit-${field}`, [field]: {} };
            await api.updateSmartRemakeContext("workspace", "owned", field, input);
            expect(fetch.mock.calls[0][0]).toContain(`/projects/owned/${field}`);
            expect(fetch.mock.calls[0][1].method).toBe("PATCH");
        },
    );

    it("propagates a blocked export instead of returning the preview URL", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockResolvedValue(
                Response.json(
                    {
                        error: {
                            code: "SMART_REMAKE_RELEASE_BLOCKED",
                            message: "Approval required",
                        },
                    },
                    { status: 409 },
                ),
            ),
        );
        await expect(
            api.exportSmartRemakeAssembly("workspace", "owned", {
                expectedRevision: 9,
                idempotencyKey: "export-1",
                assemblyId: "a",
                approvalId: "missing",
            }),
        ).rejects.toMatchObject({ status: 409 });
    });
});

it("preflights an action with JSON metadata without uploading media or submitting an operation", async () => {
    const input: api.SmartRemakePreflightRequest = {
        action: "repair",
        projectId: "owned",
        expectedRevision: 7,
        sceneId: "scene",
        baseVersionId: "version",
    };
    const preflight = { action: "repair", contextHash: "immutable-preview", blockers: [] };
    const fetch = vi.fn().mockResolvedValue(response(preflight));
    vi.stubGlobal("fetch", fetch);
    await expect(api.getSmartRemakePreflight("workspace", input)).resolves.toEqual(preflight);
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch.mock.calls[0][0]).toBe("/api/backend/workspaces/workspace/smart-remake/preflight");
    expect(fetch.mock.calls[0][1].method).toBe("POST");
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual(input);
});

it("looks up the original repair receipt without replaying its mutation", async () => {
    const receipt = { receipt: { operationId: "operation", candidateVersionId: "candidate" } };
    const fetch = vi.fn().mockResolvedValue(response(receipt));
    vi.stubGlobal("fetch", fetch);
    await expect(
        api.getSmartRemakeRepairReceipt("workspace", "owned", "repair/key ?"),
    ).resolves.toEqual(receipt);
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch.mock.calls[0][0]).toBe(
        "/api/backend/workspaces/workspace/smart-remake/projects/owned/repair-receipts?requestKey=repair%2Fkey%20%3F",
    );
    expect(fetch.mock.calls[0][1]?.method ?? "GET").toBe("GET");
});

it("sends structured repair intent without synthesized legacy prompts", async () => {
    const fetch = vi.fn().mockResolvedValue(response({ operationId: "repair", status: "running" }));
    vi.stubGlobal("fetch", fetch);
    const input = {
        baseVersionId: "base",
        expectedRevision: 7,
        idempotencyKey: "repair-intent",
        repairIntent: {
            schemaVersion: 1 as const,
            issues: ["action" as const],
            instruction: "Rót chậm hơn",
        },
    };
    await api.repairSmartRemakeScene("workspace", "owned", "scene", input);
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual(input);
});
