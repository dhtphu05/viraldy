import { afterEach, describe, expect, it, vi } from "vitest";

import * as api from "./smart-remake";

afterEach(() => vi.unstubAllGlobals());

function response(data: unknown) {
    return Response.json({ data, meta: { requestId: "test" } });
}

describe("Smart Remake controlled repair API", () => {
    it("sends KIE's stable render identity and preserves the queued project", async () => {
        const pending = {
            provider: "kie",
            status: "submitted",
            repairProject: {
                id: "project",
                pendingOperation: { id: "operation", status: "running" },
            },
        };
        const fetch = vi.fn().mockResolvedValue(response(pending));
        vi.stubGlobal("fetch", fetch);
        await expect(
            api.renderSmartRemake("workspace", {
                compileResult: {} as api.SmartRemakeCompileResult,
                productUrl: "https://shop.example/product",
                provider: "kie",
                projectName: "Smart Remake",
                idempotencyKey: "render-attempt-1",
            }),
        ).resolves.toEqual(pending);
        const body = fetch.mock.calls[0][1].body as FormData;
        expect(body.get("provider")).toBe("kie");
        expect(body.get("idempotencyKey")).toBe("render-attempt-1");
    });
    it("renders a linked product without requiring an uploaded image", async () => {
        const fetch = vi.fn().mockResolvedValue(response({ status: "completed" }));
        vi.stubGlobal("fetch", fetch);
        await api.renderSmartRemake("workspace", {
            compileResult: {} as api.SmartRemakeCompileResult,
            productUrl: "https://shop.example/product",
            provider: "unifically",
            projectName: "Smart Remake",
        });
        const body = fetch.mock.calls[0][1].body as FormData;
        expect(body.get("productUrl")).toBe("https://shop.example/product");
        expect(body.has("productImage")).toBe(false);
    });

    it("sends a scene version, revision and immutable prompt snapshot for repair", async () => {
        const fetch = vi.fn().mockResolvedValue(response({ status: "completed" }));
        vi.stubGlobal("fetch", fetch);
        const input = {
            baseVersionId: "version-1",
            expectedRevision: 3,
            prompt: "Keep the pink cup.",
            imagePrompt: "A pink cup with a white handle.",
            videoPrompt: "Open the lid slowly.",
            idempotencyKey: "repair-attempt-1",
        };
        await api.repairSmartRemakeScene("workspace", "project", "scene", input);
        expect(fetch).toHaveBeenCalledWith(
            "/api/backend/workspaces/workspace/smart-remake/projects/project/scenes/scene/repairs",
            expect.objectContaining({ method: "POST", body: JSON.stringify(input) }),
        );
    });

    it("accepts an owned version without letting the client provide clip URLs", async () => {
        const fetch = vi.fn().mockResolvedValue(response({ status: "completed" }));
        vi.stubGlobal("fetch", fetch);
        const input = {
            sceneId: "scene-1",
            versionId: "candidate-1",
            expectedRevision: 4,
            idempotencyKey: "accept-attempt-1",
        };
        await api.acceptSmartRemakeVersion("workspace", "project", input);
        expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual(input);
        expect(fetch.mock.calls[0][0]).toContain("/projects/project/accept");
    });

    it("loads a project in its workspace so versions can be reopened", async () => {
        const fetch = vi.fn().mockResolvedValue(response({ id: "project", scenes: [] }));
        vi.stubGlobal("fetch", fetch);
        await expect(api.getSmartRemakeProject("workspace", "project")).resolves.toMatchObject({
            id: "project",
        });
        expect(fetch.mock.calls[0][0]).toBe(
            "/api/backend/workspaces/workspace/smart-remake/projects/project",
        );
    });
});

describe("Smart Remake timeline v2 API", () => {
    it("keeps analysis scope separate from output duration", async () => {
        const fetch = vi.fn().mockResolvedValue(response({ schemaVersion: 2, projectId: "draft" }));
        vi.stubGlobal("fetch", fetch);
        await api.compileSmartRemake("workspace", {
            targetDuration: 8,
            language: "vi",
            prompt: "",
            description: "",
            timelineMode: "reference",
            analysisScope: "full_source",
            referenceStartFrame: 0,
            sourceCutFrames: [0, 72, 144, 216, 288, 360, 720],
        });
        const body = fetch.mock.calls[0][1].body as FormData;
        expect(body.get("analysisScope")).toBe("full_source");
        expect(body.get("targetDuration")).toBe("8");
        expect(body.get("sourceCutFrames")).toBe("[0,72,144,216,288,360,720]");
    });
    it("compiles an explicit excerpt and complete cut boundaries", async () => {
        const fetch = vi.fn().mockResolvedValue(response({ schemaVersion: 2, projectId: "draft" }));
        vi.stubGlobal("fetch", fetch);
        await api.compileSmartRemake("workspace", {
            targetDuration: 8,
            language: "vi",
            prompt: "",
            description: "",
            referenceVideo: new File(["video"], "source.mp4", { type: "video/mp4" }),
            timelineMode: "reference",
            referenceStartFrame: 48,
            sourceCutFrames: [0, 48, 192],
            renderGroupBreaks: [1],
        });
        const body = fetch.mock.calls[0][1].body as FormData;
        expect(body.get("timelineMode")).toBe("reference");
        expect(body.get("referenceStartFrame")).toBe("48");
        expect(body.get("sourceCutFrames")).toBe("[0,48,192]");
        expect(body.get("renderGroupBreaks")).toBe("[1]");
    });

    it("renders the saved project revision, with prompt edits only in the compile snapshot", async () => {
        const fetch = vi.fn().mockResolvedValue(response({ status: "running" }));
        vi.stubGlobal("fetch", fetch);
        await api.renderSmartRemake("workspace", {
            compileResult: { schemaVersion: 2 } as api.SmartRemakeCompileResult,
            provider: "kie",
            projectName: "Timeline",
            projectId: "saved-plan",
            expectedRevision: 3,
            idempotencyKey: "render-v2",
        });
        const body = fetch.mock.calls[0][1].body as FormData;
        expect(body.get("projectId")).toBe("saved-plan");
        expect(body.get("expectedRevision")).toBe("3");
        expect(body.has("productImage")).toBe(false);
    });

    it("patches selected owned versions and frame bounds without media URLs", async () => {
        const fetch = vi.fn().mockResolvedValue(response({ status: "completed" }));
        vi.stubGlobal("fetch", fetch);
        const input = {
            expectedRevision: 5,
            idempotencyKey: "trim-v2",
            items: [
                {
                    renderUnitId: "unit",
                    versionId: "version",
                    inFrame: 24,
                    outFrame: 72,
                    reviewed: true as const,
                },
            ],
        };
        await api.saveSmartRemakeTimeline("workspace", "draft", input);
        expect(fetch).toHaveBeenCalledWith(
            "/api/backend/workspaces/workspace/smart-remake/projects/draft/timeline",
            expect.objectContaining({ method: "PATCH", body: JSON.stringify(input) }),
        );
    });

    it("publishes a saved revision independently of paid generation", async () => {
        const fetch = vi.fn().mockResolvedValue(response({ status: "running" }));
        vi.stubGlobal("fetch", fetch);
        const input = { expectedRevision: 6, idempotencyKey: "compose-v2" };
        await api.publishSmartRemakeTimeline("workspace", "draft", input);
        expect(fetch).toHaveBeenCalledWith(
            "/api/backend/workspaces/workspace/smart-remake/projects/draft/publish",
            expect.objectContaining({ method: "POST", body: JSON.stringify(input) }),
        );
    });
});
