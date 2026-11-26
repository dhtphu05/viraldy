import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { RemakePlayer } from "./remake-player";

describe("RemakePlayer", () => {
    it("waits for real metadata without imposing a video ratio or autoplay", () => {
        const html = renderToStaticMarkup(
            createElement(RemakePlayer, { url: "/output.mp4", scope: null }),
        );

        expect(html).toContain("Đang đọc thông tin video");
        expect(html).toContain("Toàn bộ video");
        expect(html).toContain("object-contain");
        expect(html).not.toContain("aspect-ratio:16");
        expect(html).not.toContain("aspect-ratio:9");
        expect(html).not.toContain("autoPlay");
        expect(html).not.toContain("autoplay");
        expect(html).toContain('aria-label="Vị trí phát video"');
    });

    it("keeps both comparison sources mounted with named accessible controls", () => {
        const html = renderToStaticMarkup(
            createElement(RemakePlayer, {
                url: "/current.mp4",
                compareUrl: "/candidate.mp4",
                scope: { start: 8, end: 16 },
                versionLabel: "Bản đã duyệt",
                compareLabel: "Thử lần 2",
            }),
        );

        expect(html.match(/<video /g)).toHaveLength(2);
        expect(html).toContain('src="/current.mp4"');
        expect(html).toContain('src="/candidate.mp4"');
        expect(html).toContain("Bản đã duyệt");
        expect(html).toContain("Thử lần 2");
        expect(html).toContain('aria-label="Chọn phiên bản để xem và nghe"');
        expect(html).toContain("Đoạn được chọn");
    });
    it("makes separate raw clip offsets visible when comparing the same logical scene", () => {
        const html = renderToStaticMarkup(
            createElement(RemakePlayer, {
                url: "/shared.mp4",
                compareUrl: "/singleton.mp4",
                scope: { start: 3, end: 8 },
                compareScope: { start: 0, end: 5 },
            }),
        );
        expect(html).toContain("Hai đoạn phát cùng nhịp cảnh");
        expect(html).toContain("0:03–0:08");
        expect(html).toContain("0:00–0:05");
    });
});
