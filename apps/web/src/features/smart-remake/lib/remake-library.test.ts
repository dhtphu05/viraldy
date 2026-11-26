import { afterEach, describe, expect, it, vi } from "vitest";

import type { CreativeReference } from "@/features/creative-library/types/creative";
import {
    getRemakeLibraryVideos,
    isDemoLibraryVideo,
    loadRemakeLibraryVideo,
} from "./remake-library";

const video = {
    id: "saved-video",
    title: "Bình giữ nhiệt màu hồng",
    mediaKind: "video",
    mediaUrl: "/saved/clip.mp4",
    platform: "TikTok",
    durationSec: 24,
    brandOrCreator: "Shop của tôi",
    tags: ["mở hộp"],
    savedAt: "2026-11-24T00:00:00Z",
} as CreativeReference;

afterEach(() => vi.unstubAllGlobals());

describe("Smart Remake video library", () => {
    it("keeps available and metadata-only video references, excluding images and archived items", () => {
        const metadataOnly = {
            ...video,
            id: "url-only",
            mediaKind: undefined,
            mediaUrl: undefined,
        };
        const older = { ...video, id: "older", savedAt: "2026-11-23T00:00:00Z" };
        const entries = [
            older,
            { ...video, id: "image", mediaKind: "image" as const },
            video,
            { ...video, id: "archived", archived: true },
            metadataOnly,
        ];
        expect(getRemakeLibraryVideos(entries).map((item) => item.id)).toEqual([
            video.id,
            older.id,
            metadataOnly.id,
        ]);
        expect(entries[0]).toBe(older);
    });

    it("finds Vietnamese titles without accents and searches creator and tags", () => {
        expect(getRemakeLibraryVideos([video], " BINH GIU NHIET ")).toEqual([video]);
        expect(getRemakeLibraryVideos([video], "mo hop")).toEqual([video]);
        expect(getRemakeLibraryVideos([video], "shop cua toi")).toEqual([video]);
        expect(getRemakeLibraryVideos([video], "không tồn tại")).toEqual([]);
    });

    it("labels existing illustrative media without treating an uploaded reference as a demo", () => {
        expect(isDemoLibraryVideo({ ...video, mediaUrl: "/demo-media/clip.mp4" })).toBe(true);
        expect(isDemoLibraryVideo({ ...video, tags: ["demo"] })).toBe(true);
        expect(isDemoLibraryVideo(video)).toBe(false);
    });

    it("imports the selected bytes as a named File and forwards cancellation", async () => {
        const fetch = vi.fn().mockResolvedValue(
            new Response("selected-video", {
                headers: { "Content-Type": "video/mp4" },
            }),
        );
        vi.stubGlobal("fetch", fetch);
        const controller = new AbortController();
        const result = await loadRemakeLibraryVideo(video, controller.signal);
        expect(fetch).toHaveBeenCalledWith(video.mediaUrl, { signal: controller.signal });
        expect(result.name).toBe("Bình giữ nhiệt màu hồng.mp4");
        expect(result.type).toBe("video/mp4");
        expect(await result.text()).toBe("selected-video");
    });

    it("supports an untyped video download with an explicit supported filename", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockResolvedValue(
                new Response(new Uint8Array([1, 2]), {
                    headers: { "Content-Type": "application/octet-stream" },
                }),
            ),
        );
        const result = await loadRemakeLibraryVideo({
            ...video,
            mediaUrl: "/saved/clip.webm?token=1",
        });
        expect(result.type).toBe("video/webm");
        expect(result.name.endsWith(".webm")).toBe(true);
    });

    it("rejects missing media without fetching or substituting another video", async () => {
        const fetch = vi.fn();
        vi.stubGlobal("fetch", fetch);
        await expect(loadRemakeLibraryVideo({ ...video, mediaUrl: undefined })).rejects.toThrow(
            "file video",
        );
        expect(fetch).not.toHaveBeenCalled();
    });

    it.each([404, 403])("rejects an unavailable library video (%s)", async (status) => {
        const fetch = vi.fn().mockResolvedValue(new Response(null, { status }));
        vi.stubGlobal("fetch", fetch);
        await expect(loadRemakeLibraryVideo(video)).rejects.toThrow("Chưa mở được");
        expect(fetch).toHaveBeenCalledTimes(1);
    });

    it("rejects HTML returned at a video URL", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockResolvedValue(
                new Response("<html>Login</html>", {
                    headers: { "Content-Type": "text/html" },
                }),
            ),
        );
        await expect(loadRemakeLibraryVideo(video)).rejects.toThrow("MP4, MOV hoặc WebM");
    });

    it("rejects files beyond Smart Remake's 30 MB limit even though the library allows larger uploads", async () => {
        const bytes = new Uint8Array(30 * 1024 * 1024 + 1);
        vi.stubGlobal(
            "fetch",
            vi.fn().mockResolvedValue(
                new Response(bytes, {
                    headers: { "Content-Type": "video/mp4" },
                }),
            ),
        );
        await expect(loadRemakeLibraryVideo(video)).rejects.toThrow("30 MB");
    });

    it("does not return a file if the picker closes while the download resolves", async () => {
        const controller = new AbortController();
        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation(async () => {
                controller.abort();
                return new Response("late-video", { headers: { "Content-Type": "video/mp4" } });
            }),
        );
        await expect(loadRemakeLibraryVideo(video, controller.signal)).rejects.toMatchObject({
            name: "AbortError",
        });
    });
});
