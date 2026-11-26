import { describe, expect, it } from "vitest";
import { seedCreatives } from "../mocks/creatives";
import type { CreativeReference } from "../types/creative";
import {
    getCreativeMediaKind,
    isIllustrativeCreative,
    matchesCreativeQuery,
} from "./library-catalog";

const creative = {
    id: "my-saved-video",
    title: "Bình giữ nhiệt màu hồng",
    hookExcerpt: "Mở nắp chỉ với một tay",
    platform: "TikTok",
    brandOrCreator: "Đồ bếp của tôi",
    angle: "Product demonstration",
    category: "Home & Kitchen",
    tags: ["mùa hè"],
    notes: "Ưu tiên góc quay gần",
    durationSec: 24,
    mediaKind: "video",
    mediaUrl: "blob:my-video",
} as CreativeReference;

describe("seller library catalog", () => {
    it.each([
        "binh giu nhiet",
        "MO NAP",
        "do bep",
        "tiktok",
        "demonstration",
        "home",
        "mua he",
        "goc quay",
    ])("finds the same saved reference by seller vocabulary: %s", (query) => {
        expect(matchesCreativeQuery(creative, query)).toBe(true);
    });
    it("allows empty search and rejects unrelated terms", () => {
        expect(matchesCreativeQuery(creative, "  ")).toBe(true);
        expect(matchesCreativeQuery(creative, "không tồn tại")).toBe(false);
    });
    it("distinguishes source file presence from a reference or an image", () => {
        expect(getCreativeMediaKind(creative)).toBe("video");
        expect(getCreativeMediaKind({ ...creative, mediaUrl: undefined })).toBe("reference");
        expect(getCreativeMediaKind({ ...creative, mediaKind: "image" })).toBe("image");
        expect(getCreativeMediaKind({ ...creative, mediaKind: undefined })).toBe("video");
    });
    it("labels seeded analyses and demo media as illustrations, not a seller's own result", () => {
        expect(isIllustrativeCreative(seedCreatives[0])).toBe(true);
        expect(isIllustrativeCreative({ ...creative, mediaUrl: "/demo-media/clip.mp4" })).toBe(
            true,
        );
        expect(isIllustrativeCreative({ ...creative, tags: ["demo-import"] })).toBe(true);
        expect(isIllustrativeCreative(creative)).toBe(false);
    });
});
