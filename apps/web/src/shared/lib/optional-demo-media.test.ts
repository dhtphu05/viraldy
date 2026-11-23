import { afterEach, describe, expect, it, vi } from "vitest";

import { isDemoVideoAvailable } from "./optional-demo-media";

describe("isDemoVideoAvailable", () => {
    afterEach(() => vi.unstubAllGlobals());

    it("checks video availability without downloading the recording", async () => {
        const fetch = vi
            .fn()
            .mockResolvedValue(new Response(null, { headers: { "Content-Type": "video/mp4" } }));
        vi.stubGlobal("fetch", fetch);

        await expect(isDemoVideoAvailable("/smart-remake/02_After.mp4")).resolves.toBe(true);
        expect(fetch).toHaveBeenCalledWith(
            "/smart-remake/02_After.mp4",
            expect.objectContaining({ method: "HEAD", signal: expect.any(AbortSignal) }),
        );
    });

    it.each([
        [404, "video/mp4"],
        [200, "text/html"],
        [200, ""],
    ])("rejects missing or non-video responses (%s, %s)", async (status, contentType) => {
        vi.stubGlobal(
            "fetch",
            vi
                .fn()
                .mockResolvedValue(
                    new Response(null, { status, headers: { "Content-Type": contentType } }),
                ),
        );

        await expect(isDemoVideoAvailable("/smart-remake/02_After.mp4")).resolves.toBe(false);
    });

    it.each([new TypeError("Network unavailable"), new DOMException("Timed out", "TimeoutError")])(
        "treats a failed check as unavailable: %s",
        async (error) => {
            vi.stubGlobal("fetch", vi.fn().mockRejectedValue(error));

            await expect(isDemoVideoAvailable("/smart-remake/02_After.mp4")).resolves.toBe(false);
        },
    );
});
