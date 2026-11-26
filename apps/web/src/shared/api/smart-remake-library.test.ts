import { afterEach, describe, expect, it, vi } from "vitest";

import { listSmartRemakeProjects } from "./smart-remake-library";

afterEach(() => vi.unstubAllGlobals());

describe("saved Smart Remake projects", () => {
    it("opts into unfinished projects with a read-only collection request", async () => {
        const fetch = vi.fn().mockResolvedValue(Response.json({ data: { items: [], total: 0 } }));
        vi.stubGlobal("fetch", fetch);
        await listSmartRemakeProjects("workspace", { includeUnfinished: true });
        expect(fetch.mock.calls[0][0]).toBe(
            "/api/backend/workspaces/workspace/smart-remake/projects?limit=24&offset=0&includeUnfinished=true",
        );
        expect(fetch.mock.calls[0][1].method).toBeUndefined();
    });
    it("reads the workspace collection with pagination and cancellation", async () => {
        const data = { items: [], total: 40, limit: 24, offset: 24 };
        const fetch = vi.fn().mockResolvedValue(Response.json({ data }));
        vi.stubGlobal("fetch", fetch);
        const controller = new AbortController();

        await expect(
            listSmartRemakeProjects("workspace", { offset: 24, signal: controller.signal }),
        ).resolves.toEqual(data);
        expect(fetch).toHaveBeenCalledWith(
            "/api/backend/workspaces/workspace/smart-remake/projects?limit=24&offset=24",
            expect.objectContaining({ signal: controller.signal }),
        );
        expect(fetch.mock.calls[0][1].method).toBeUndefined();
    });

    it("defaults to the first page and retains server-approved download links", async () => {
        const item = { id: "project", downloadUrl: "https://media.example/export.mp4" };
        const fetch = vi
            .fn()
            .mockResolvedValue(
                Response.json({ data: { items: [item], total: 1, limit: 24, offset: 0 } }),
            );
        vi.stubGlobal("fetch", fetch);

        const result = await listSmartRemakeProjects("workspace");
        expect(result.items[0]).toEqual(item);
        expect(fetch.mock.calls[0][0]).toBe(
            "/api/backend/workspaces/workspace/smart-remake/projects?limit=24&offset=0",
        );
    });

    it("propagates collection errors instead of returning an empty gallery", async () => {
        vi.stubGlobal(
            "fetch",
            vi
                .fn()
                .mockResolvedValue(
                    Response.json(
                        { error: { code: "WORKSPACE_FORBIDDEN", message: "Access denied" } },
                        { status: 403 },
                    ),
                ),
        );

        await expect(listSmartRemakeProjects("workspace")).rejects.toMatchObject({
            code: "WORKSPACE_FORBIDDEN",
            status: 403,
        });
    });

    it("retains generated clips without requiring a completed composition or inventing a download", async () => {
        const item = {
            id: "project",
            finalVideoUrl: "",
            videos: [
                {
                    id: "version",
                    label: "Clip 1",
                    kind: "clip",
                    url: "https://media.example/clip.mp4",
                    durationSeconds: 8,
                },
            ],
        };
        vi.stubGlobal(
            "fetch",
            vi
                .fn()
                .mockResolvedValue(
                    Response.json({ data: { items: [item], total: 1, limit: 24, offset: 0 } }),
                ),
        );

        const result = await listSmartRemakeProjects("workspace");
        expect(result.items[0].videos).toEqual(item.videos);
        expect(result.items[0].finalVideoUrl).toBe("");
        expect(result.items[0].downloadUrl).toBeUndefined();
    });
});
