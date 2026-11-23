import { afterEach, describe, expect, it, vi } from "vitest";

import {
    renderSmartRemake,
    type SmartRemakeCompileResult,
    type SmartRemakeHealth,
} from "@/shared/api/smart-remake";
import { renderSmartRemakeVideo } from "./smart-remake-render";

vi.mock("@/shared/api/smart-remake", () => ({ renderSmartRemake: vi.fn() }));

const compileResult = { inputSummary: { targetDuration: 8 } } as SmartRemakeCompileResult;
const productImage = { name: "product.jpg", type: "image/jpeg" } as File;
const health: SmartRemakeHealth = {
    enabled: true,
    mode: "live",
    providers: ["unifically", "flowkit"],
    unificallyConfigured: true,
    flowkitUrlSet: false,
    limits: { referenceVideoBytes: 30_000_000, productImageBytes: 10_000_000 },
};

describe("renderSmartRemakeVideo", () => {
    afterEach(() => {
        vi.unstubAllGlobals();
        vi.useRealTimers();
        vi.resetAllMocks();
    });

    it("preserves the 20-second local recording flow when its optional video exists", async () => {
        vi.useFakeTimers();
        vi.stubGlobal(
            "fetch",
            vi
                .fn()
                .mockResolvedValue(
                    new Response(null, { headers: { "Content-Type": "video/mp4" } }),
                ),
        );
        const pending = renderSmartRemakeVideo("ws-1", { compileResult, health });
        const settled = vi.fn();
        void pending.then(settled);

        await vi.advanceTimersByTimeAsync(19_999);
        expect(settled).not.toHaveBeenCalled();
        await vi.advanceTimersByTimeAsync(1);

        await expect(pending).resolves.toEqual({
            finalVideoUrl: "/smart-remake/02_After.mp4",
            status: "completed",
        });
        expect(renderSmartRemake).not.toHaveBeenCalled();
    });

    it.each([404, 200])(
        "uses the configured real render API when the local output is missing (HTML %s)",
        async (status) => {
            vi.stubGlobal(
                "fetch",
                vi
                    .fn()
                    .mockResolvedValue(
                        new Response(null, { status, headers: { "Content-Type": "text/html" } }),
                    ),
            );
            const apiResult = {
                finalVideoUrl: "https://media.example/video.mp4",
                status: "completed" as const,
            };
            vi.mocked(renderSmartRemake).mockResolvedValue(
                apiResult as Awaited<ReturnType<typeof renderSmartRemake>>,
            );

            await expect(
                renderSmartRemakeVideo("ws-1", { compileResult, productImage, health }),
            ).resolves.toEqual(apiResult);
            expect(renderSmartRemake).toHaveBeenCalledWith("ws-1", {
                compileResult,
                productImage,
                provider: "unifically",
                projectName: "Smart Remake",
            });
        },
    );

    it("uses FlowKit when it is the configured renderer and preserves submitted status without a video", async () => {
        vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Network unavailable")));
        const apiResult = { finalVideoUrl: "", status: "submitted" as const };
        vi.mocked(renderSmartRemake).mockResolvedValue(
            apiResult as Awaited<ReturnType<typeof renderSmartRemake>>,
        );

        await expect(
            renderSmartRemakeVideo("ws-1", {
                compileResult,
                productImage,
                health: { ...health, unificallyConfigured: false, flowkitUrlSet: true },
            }),
        ).resolves.toEqual(apiResult);
        expect(renderSmartRemake).toHaveBeenCalledWith(
            "ws-1",
            expect.objectContaining({ provider: "flowkit" }),
        );
    });

    it.each([
        undefined,
        { ...health, mode: "fixture" as const },
        { ...health, unificallyConfigured: false },
    ])(
        "shows an unavailable message instead of a broken demo output when no live renderer is configured",
        async (health) => {
            vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 404 })));

            await expect(
                renderSmartRemakeVideo("ws-1", { compileResult, productImage, health }),
            ).rejects.toThrow("dịch vụ tạo video");
            expect(renderSmartRemake).not.toHaveBeenCalled();
        },
    );

    it("asks for an uploaded product image before real rendering a linked product", async () => {
        vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 404 })));

        await expect(renderSmartRemakeVideo("ws-1", { compileResult, health })).rejects.toThrow(
            "tải ảnh sản phẩm",
        );
        expect(renderSmartRemake).not.toHaveBeenCalled();
    });

    it("propagates real rendering failures instead of returning the absent local video", async () => {
        vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 404 })));
        vi.mocked(renderSmartRemake).mockRejectedValue(new Error("Provider failed"));

        await expect(
            renderSmartRemakeVideo("ws-1", { compileResult, productImage, health }),
        ).rejects.toThrow("Provider failed");
    });
});
