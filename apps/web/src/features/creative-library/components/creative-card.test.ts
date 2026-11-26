import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { CreativeReference } from "../types/creative";
import { CreativeCard } from "./creative-card";

const creative: CreativeReference = {
    id: "video",
    title: "Mở nắp bình giữ nhiệt",
    hookExcerpt: "Mở nắp bằng một tay",
    platform: "TikTok",
    durationSec: 15,
    mediaKind: "video",
    mediaUrl: "/demo-media/video.mp4",
    mediaAspectRatio: "16:9",
    brandOrCreator: "Demo",
    angle: "Product demonstration",
    category: "Home & Kitchen",
    tags: ["demo"],
    boardIds: [],
    analysisStatus: "unanalyzed",
    savedAt: "2026-11-24T00:00:00Z",
    thumbSeed: "video",
};
function render(next = creative, compact = false) {
    return renderToStaticMarkup(
        createElement(CreativeCard, { creative: next, compact, onAction: vi.fn() }),
    );
}
describe("CreativeCard", () => {
    it("lets an unanalyzed video start Smart Remake and names preview separately from details", () => {
        const html = render();
        expect(html).toContain("Tạo với Smart Remake");
        expect(html).toContain('aria-label="Xem video Mở nắp bình giữ nhiệt"');
        expect(html).toContain('aria-label="Mở chi tiết Mở nắp bình giữ nhiệt"');
        expect(html).toContain("Có file video");
        expect(html).toContain("Minh họa");
    });
    it("does not offer video generation for references with only a poster", () => {
        const html = render({ ...creative, mediaUrl: undefined, posterUrl: "/poster.jpg" });
        expect(html).not.toContain("Tạo với Smart Remake");
        expect(html).toContain("Chưa có file video");
        expect(html).toContain("Mở chi tiết");
    });
    it("keeps the entire frame visible and does not autoplay or loop on hover", () => {
        const html = render();
        expect(html).toContain("object-contain");
        expect(html).not.toContain("object-cover");
        expect(html).not.toContain("autoPlay");
        expect(html).not.toContain('loop=""');
    });
    it("uses a horizontal compact layout instead of only changing the thumbnail crop", () => {
        expect(render(creative, true)).toContain("sm:flex-row");
        expect(render(creative, false)).not.toContain("sm:flex-row");
    });
});
