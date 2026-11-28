import { afterEach, expect, it, vi } from "vitest";
import { previewSmartRemakeKiePrompts } from "./smart-remake-prompt-preview";

afterEach(() => vi.unstubAllGlobals());

it("requests a read-only prompt preview with the current scene draft and revision", async () => {
    const data = {
        projectId: "project",
        revision: 4,
        groups: [{ groupId: "group", model: "wan/3-0-video", prompt: "Exact planned text" }],
    };
    const fetch = vi.fn().mockResolvedValue(Response.json({ data, meta: { requestId: "test" } }));
    vi.stubGlobal("fetch", fetch);
    const input = {
        expectedRevision: 4,
        scenePrompts: [
            {
                renderUnitId: "unit",
                prompt: "Intent",
                imagePrompt: "Image",
                videoPrompt: "Edited movement",
            },
        ],
    };
    expect(await previewSmartRemakeKiePrompts("workspace", "project", input)).toEqual(data);
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch.mock.calls[0][0]).toBe(
        "/api/backend/workspaces/workspace/smart-remake/projects/project/generation/prompt-preview",
    );
    expect(fetch.mock.calls[0][1].method).toBe("POST");
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual(input);
});
