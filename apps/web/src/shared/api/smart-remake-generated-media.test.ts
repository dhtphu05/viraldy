import { afterEach, expect, it, vi } from "vitest";
import { getSmartRemakeGeneratedImageDownload } from "./smart-remake-generated-media";

afterEach(() => vi.unstubAllGlobals());

it("requests a fresh owned image download without proxying the image bytes", async () => {
    const fetch = vi.fn().mockResolvedValue(
        Response.json({
            data: {
                url: "https://private.example.test/image?signature=fresh",
                filename: "opening.png",
            },
            meta: { requestId: "test" },
        }),
    );
    vi.stubGlobal("fetch", fetch);
    const result = await getSmartRemakeGeneratedImageDownload(
        "workspace",
        "project",
        "render",
        "a".repeat(64),
    );
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch.mock.calls[0][0]).toBe(
        `/api/backend/workspaces/workspace/smart-remake/projects/project/generation/render/images/${"a".repeat(64)}/download`,
    );
    expect(result).toEqual({
        url: "https://private.example.test/image?signature=fresh",
        filename: "opening.png",
    });
});
