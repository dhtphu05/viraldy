import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { SmartRemakeProject } from "@/shared/api/smart-remake";
import { createRemakePreviewDemo } from "../demo/remake-preview-demo";
import { RemakeOutput } from "./remake-output";

function fixture() {
    const source: SmartRemakeProject = {
        id: "source",
        revision: 1,
        status: "ready",
        provider: "kie",
        targetDuration: 12,
        finalVideoUrl: "",
        scenes: [],
    };
    return { ...createRemakePreviewDemo(source, "ready"), sourceVideoUrl: "/original.mp4" };
}

function output(project: SmartRemakeProject) {
    const onPublish = vi.fn();
    const onRepair = vi.fn();
    const html = renderToStaticMarkup(
        createElement(RemakeOutput, {
            workspaceId: "workspace",
            project,
            result: null,
            busy: false,
            guided: true,
            onRepair,
            onAccept: vi.fn(),
            onRefresh: vi.fn(),
            onPublish,
        }),
    );
    expect(onPublish).not.toHaveBeenCalled();
    expect(onRepair).not.toHaveBeenCalled();
    return html;
}

describe("whole preview source comparison", () => {
    it("shows original and finished remake in the same preview with shared playback", () => {
        const html = output(fixture());
        const preview = html.slice(
            html.indexOf('aria-label="Bản xem trước toàn video"'),
            html.indexOf("Muốn sửa phần nào?"),
        );
        expect(preview).toContain('src="/original.mp4"');
        expect(preview).toContain('src="/smart-remake/report-demo/whole-preview.mp4"');
        expect(preview.match(/<video /g)).toHaveLength(2);
        expect(preview).toContain("Video gốc");
        expect(preview).toContain("Bản remake");
    });

    it("keeps the completed preview usable when an older project lacks its source mapping", () => {
        const html = output({ ...fixture(), sourceSceneMap: undefined });
        expect(html).toContain('src="/smart-remake/report-demo/whole-preview.mp4"');
        expect(html).not.toContain('src="/original.mp4"');
        expect(html).toContain("Chưa có đủ mốc cảnh để đồng bộ video gốc");
    });

    it("does not attach current source mapping to an outdated assembly", () => {
        const project = fixture();
        const html = output({
            ...project,
            draftTimeline: {
                ...project.draftTimeline!,
                items: project.draftTimeline!.items.map((item, index) =>
                    index === 0 ? { ...item, versionId: "other" } : item,
                ),
            },
        });
        expect(html).not.toContain('src="/original.mp4"');
        expect(html).not.toContain('src="/smart-remake/report-demo/whole-preview.mp4"');
    });
});
