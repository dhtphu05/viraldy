import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { RemakeExcerptControls, RemakeSourceTimeline } from "./remake-source-timeline";
import { RemakeTrimTools } from "./remake-trim-tools";

describe("source excerpt controls", () => {
    it("shows a fixed-length window and accessible frame-accurate alternatives", () => {
        const html = renderToStaticMarkup(
            createElement(RemakeExcerptControls, {
                durationSeconds: 24,
                targetSeconds: 16,
                startFrame: 48,
                currentSeconds: 5,
                onChange: vi.fn(),
                disabled: false,
            }),
        );
        expect(html).toContain("Đoạn mẫu sẽ dùng");
        expect(html).toContain("2–18 giây");
        expect(html).toContain("Dùng vị trí hiện tại");
        expect(html).toContain('aria-label="Điểm bắt đầu đoạn mẫu"');
        expect(html).toContain('max="192"');
        expect(html).not.toContain("autoPlay");
    });
    it("explains a source that is too short rather than squeezing its timing", () => {
        const html = renderToStaticMarkup(
            createElement(RemakeExcerptControls, {
                durationSeconds: 10,
                targetSeconds: 16,
                startFrame: 0,
                currentSeconds: 0,
                onChange: vi.fn(),
                disabled: false,
            }),
        );
        expect(html).toContain('role="alert"');
        expect(html).toContain("Video mẫu chưa đủ 16 giây");
    });
});

describe("raw clip trim review", () => {
    const item = {
        id: "item",
        sourceSceneId: "source",
        renderUnitId: "unit",
        targetStartFrame: 0,
        targetDurationFrames: 72,
        versionId: "version",
        inFrame: 0,
        outFrame: 72,
        reviewed: false,
    };
    const props = {
        item,
        versionId: "version",
        rawFrameCount: 192,
        busy: false,
        onSave: vi.fn(),
        onPreview: vi.fn(),
    };
    it("labels a suggested range as unreviewed and requires explicit use", () => {
        const html = renderToStaticMarkup(createElement(RemakeTrimTools, props));
        expect(html).toContain("Clip AI · 8 giây");
        expect(html).toContain("Đoạn sẽ dùng · 3 giây");
        expect(html).toContain("Đoạn cắt mặc định · Chưa chọn");
        expect(html).toContain("Dùng đoạn này");
        expect(html).toContain('aria-label="Điểm bắt đầu trong clip AI, frame"');
        expect(html).toContain('max="120"');
        expect(html).toContain('aria-label="Lùi điểm bắt đầu 1 frame"');
        expect(html).toContain('aria-label="Tiến điểm bắt đầu 1 frame"');
    });
    it("blocks review if the measured raw clip cannot cover the planned length", () => {
        const html = renderToStaticMarkup(
            createElement(RemakeTrimTools, { ...props, rawFrameCount: 48 }),
        );
        expect(html).toContain("Clip này chưa đủ 3 giây");
        const save = html.match(/<button[^>]*>[\s\S]*?Dùng đoạn này[\s\S]*?<\/button>/)?.[0];
        expect(save).toContain('disabled=""');
    });
    it("keeps a later scene's suggested offset in a shared clip unreviewed", () => {
        const html = renderToStaticMarkup(
            createElement(RemakeTrimTools, {
                ...props,
                sharedClip: true,
                item: { ...item, targetDurationFrames: 120, inFrame: 72, outFrame: 192 },
            }),
        );
        expect(html).toContain("Clip chung nhiều cảnh");
        expect(html).toContain('value="3"');
        expect(html).toContain("Đoạn cắt mặc định · Chưa chọn");
        expect(html).toContain("3–8 giây");
    });
    it("does not silently approve an item when its version changes", () => {
        const html = renderToStaticMarkup(
            createElement(RemakeTrimTools, {
                ...props,
                item: { ...item, reviewed: true },
                versionId: "replacement",
            }),
        );
        expect(html).toContain("Đoạn cắt mặc định · Chưa chọn");
        expect(html).not.toContain("Đã chọn đoạn · Chưa duyệt nội dung");
    });
});

describe("source scene filmstrip", () => {
    it("uses one source player, proportional scene durations and explicit script updates", () => {
        const html = renderToStaticMarkup(
            createElement(RemakeSourceTimeline, {
                referenceUrl: "/source.mp4",
                sourceStartFrame: 24,
                totalFrames: 384,
                sourceCutFrames: [0, 72, 192, 288, 384],
                selectedScene: 0,
                onSelect: vi.fn(),
                onCutsChange: vi.fn(),
                onRecompile: vi.fn(),
                compiledCutFrames: [0, 192, 384],
                disabled: false,
            }),
        );
        expect(html.match(/<video\b/g)).toHaveLength(1);
        expect(html).toContain("object-contain");
        expect(html).toContain("3 giây");
        expect(html).toContain("5 giây");
        expect(html).toContain("Cập nhật kịch bản");
        expect(html).toContain("Mốc cắt đã thay đổi");
        expect(html).toContain('aria-label="Mốc cắt sau cảnh 1, giây"');
    });
    it("blocks invalid boundaries without dropping scenes", () => {
        const html = renderToStaticMarkup(
            createElement(RemakeSourceTimeline, {
                sourceStartFrame: 0,
                totalFrames: 384,
                sourceCutFrames: [0, 216, 200, 384],
                compiledCutFrames: [0, 192, 384],
                selectedScene: 0,
                onSelect: vi.fn(),
                onCutsChange: vi.fn(),
                onRecompile: vi.fn(),
                disabled: false,
            }),
        );
        expect(html).toContain('role="alert"');
        expect(html).toContain("Mỗi cảnh cần có độ dài lớn hơn 0 và đúng thứ tự");
        const update = html.match(/<button[^>]*>[\s\S]*?Cập nhật kịch bản[\s\S]*?<\/button>/)?.[0];
        expect(update).toContain('disabled=""');
    });
    it("shows retained real scene thumbnails when available with one source player", () => {
        const html = renderToStaticMarkup(
            createElement(RemakeSourceTimeline, {
                referenceUrl: "/source.mp4",
                sourceStartFrame: 0,
                totalFrames: 192,
                sourceCutFrames: [0, 48, 192],
                compiledCutFrames: [0, 48, 192],
                selectedScene: 0,
                onSelect: vi.fn(),
                thumbnails: ["/real-frame-2.jpg", undefined],
            }),
        );
        expect(html).toContain('src="/real-frame-2.jpg"');
        expect(html.match(/<video\b/g)).toHaveLength(1);
        expect(html.match(/<img\b/g)).toHaveLength(1);
    });
});
