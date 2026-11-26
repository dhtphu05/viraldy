import { afterEach, describe, expect, it, vi } from "vitest";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

import {
    DEMO_SEARCH_DELAY_MS,
    getDemoVideoResults,
    MAX_PRODUCT_IMAGE_BYTES,
    validateProductImages,
} from "./viral-video-demo";

function fakeFile(name: string, type: string, size = 1024) {
    return { name, type, size, lastModified: 1 } as File;
}

describe("viral video demo helpers", () => {
    afterEach(() => vi.unstubAllGlobals());

    it("waits six seconds before showing recommendations after an image upload", () => {
        expect(DEMO_SEARCH_DELAY_MS).toBe(6_000);
    });

    it("accepts multiple supported product images without changing their order", () => {
        const first = fakeFile("front.webp", "image/webp");
        const second = fakeFile("side.png", "image/png");

        expect(validateProductImages([first, second])).toEqual({
            accepted: [first, second],
            rejected: [],
        });
    });

    it("rejects unsupported and oversized files while keeping valid images", () => {
        const valid = fakeFile("product.jpg", "image/jpeg");
        const unsupported = fakeFile("notes.pdf", "application/pdf");
        const oversized = fakeFile("large.png", "image/png", MAX_PRODUCT_IMAGE_BYTES + 1);

        expect(validateProductImages([valid, unsupported, oversized])).toEqual({
            accepted: [valid],
            rejected: [unsupported, oversized],
        });
    });

    it("accepts an image exactly at the per-file size limit", () => {
        const image = fakeFile("limit.jpg", "image/jpeg", MAX_PRODUCT_IMAGE_BYTES);

        expect(validateProductImages([image])).toEqual({ accepted: [image], rejected: [] });
    });

    it("preserves six ranked Ly recommendations when optional local videos are available", async () => {
        vi.stubGlobal(
            "fetch",
            vi
                .fn()
                .mockResolvedValue(
                    new Response(null, { headers: { "Content-Type": "video/mp4" } }),
                ),
        );
        const results = await getDemoVideoResults();

        expect(results).toHaveLength(6);
        expect(results.every((creative) => creative.mediaKind === "video")).toBe(true);
        expect(results.every((creative) => creative.mediaUrl?.startsWith("/product_ads/ly/"))).toBe(
            true,
        );
        expect(new Set(results.map((creative) => creative.mediaUrl)).size).toBe(6);
        expect(results.map((creative) => creative.fileName)).toContain("01_Before.mp4");
        expect(results.map((creative) => creative.rank)).toEqual([1, 2, 3, 4, 5, 6]);
        for (const { metrics } of results) {
            expect(metrics.revenue).toBeGreaterThan(0);
            expect(metrics.adSpend).toBeGreaterThan(0);
            expect(metrics.videoViews).toBeGreaterThan(0);
            expect(metrics.impressions).toBeGreaterThan(0);
            expect(metrics.clicks).toBeGreaterThan(0);
            expect(metrics.orders).toBeGreaterThan(0);
            expect(metrics.likes).toBeGreaterThan(0);
            expect(metrics.comments).toBeGreaterThan(0);
            expect(metrics.shares).toBeGreaterThan(0);
            expect(metrics.videoViews).toBeLessThanOrEqual(metrics.impressions);
            expect(metrics.clicks).toBeLessThanOrEqual(metrics.impressions);
            expect(metrics.orders).toBeLessThanOrEqual(metrics.clicks);
            expect(metrics.roas).toBeCloseTo(metrics.revenue / metrics.adSpend, 1);
            expect(metrics.ctr).toBeCloseTo((metrics.clicks / metrics.impressions) * 100, 1);
            expect(metrics.cvr).toBeCloseTo((metrics.orders / metrics.clicks) * 100, 1);
            expect(metrics.cpc).toBeCloseTo(metrics.adSpend / metrics.clicks, 1);
            expect(metrics.cpa).toBeCloseTo(metrics.adSpend / metrics.orders, 1);
        }
    });

    it.each([404, 200])(
        "uses tracked demo media when optional URLs return status %s with HTML",
        async (status) => {
            vi.stubGlobal(
                "fetch",
                vi
                    .fn()
                    .mockResolvedValue(
                        new Response(null, { status, headers: { "Content-Type": "text/html" } }),
                    ),
            );

            const results = await getDemoVideoResults();

            expect(results).toHaveLength(6);
            expect(new Set(results.map((video) => video.mediaUrl)).size).toBe(6);
            expect(results.map((video) => video.rank)).toEqual([1, 2, 3, 4, 5, 6]);
            for (const video of results) {
                expect(video.mediaUrl).toMatch(/^\/demo-media\/.*\.mp4$/);
                expect(video.fileName).toBe(video.mediaUrl!.split("/").at(-1));
                expect(video.tags).toContain("demo");
                expect(existsSync(resolve(process.cwd(), "public", video.mediaUrl!.slice(1)))).toBe(
                    true,
                );
                expect(video.metrics.revenue).toBeGreaterThan(0);
            }
        },
    );

    it("keeps available local videos while replacing only missing recommendations", async () => {
        vi.stubGlobal(
            "fetch",
            vi
                .fn()
                .mockImplementation(async (url: string) =>
                    url.endsWith("01_Before.mp4")
                        ? new Response(null, { headers: { "Content-Type": "video/mp4" } })
                        : new Response(null, { status: 404 }),
                ),
        );

        const results = await getDemoVideoResults();

        expect(results[0].mediaUrl).toBe("/product_ads/ly/01_Before.mp4");
        expect(results.slice(1).every((video) => video.mediaUrl?.startsWith("/demo-media/"))).toBe(
            true,
        );
    });

    it("still returns playable tracked recommendations when availability checks fail", async () => {
        vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Network unavailable")));

        const results = await getDemoVideoResults();

        expect(results).toHaveLength(6);
        expect(results.every((video) => video.mediaUrl?.startsWith("/demo-media/"))).toBe(true);
    });
});
