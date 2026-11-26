import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { expect, it, vi } from "vitest";
import type { SmartRemakeProject } from "@/shared/api/smart-remake";
import { RemakeOutput } from "./remake-output";

function generationProject(blocked = false): SmartRemakeProject {
    return {
        id: "project",
        revision: 1,
        schemaVersion: 2,
        phase: "compiled",
        status: "incomplete",
        provider: "kie",
        targetDuration: 16,
        finalVideoUrl: "",
        productImageUrl: "/product.png",
        sourceVideoUrl: "/source.mp4",
        scenes: [],
        renderPlan: {
            fps: 24,
            provider: "kie",
            groupingPolicy: "fixed_provider_windows",
            units: ["a", "b"].map((id) => ({
                id,
                sourceSceneId: id,
                sceneIndex: 0,
                rawDurationFrames: 192,
                targetDurationFrames: 192,
                prompt: "scene",
                imagePrompt: "image",
                videoPrompt: "video",
            })),
            groups: ["a", "b"].map((id) => ({
                id,
                renderUnitIds: [id],
                rawDurationFrames: 192,
                targetDurationFrames: 192,
                segments: [{ renderUnitId: id, inFrame: 0, outFrame: 192 }],
            })),
        },
        generationProgress: {
            operationId: "operation",
            status: blocked ? "failed" : "running",
            startedAt: "2026-11-26T11:57:12Z",
            updatedAt: "2026-11-26T11:58:20Z",
            groups: [
                {
                    groupId: "a",
                    stage: blocked ? "blocked" : "preparing_image",
                    videoSubmitted: false,
                    conditioningImageUrl: "/opening.png",
                    ...(blocked
                        ? {
                              errorCode: "SMART_REMAKE_CONDITIONING_BLOCKED",
                              inspectionReportId: "inspection",
                          }
                        : {}),
                },
                { groupId: "b", stage: "queued", videoSubmitted: false },
            ],
        },
    };
}

function output(project: SmartRemakeProject) {
    return renderToStaticMarkup(
        createElement(RemakeOutput, {
            workspaceId: "workspace",
            project,
            result: null,
            busy: false,
            guided: true,
            onRepair: vi.fn(),
            onAccept: vi.fn(),
            onRefresh: vi.fn(),
        }),
    );
}

it("shows the two video windows and completed image during preparation before the first clip exists", () => {
    const html = output(generationProject());
    expect(html).toContain("2 lượt dự kiến");
    expect(html).toContain("0 lượt đã gửi KIE");
    expect(html).toContain("0–8 giây");
    expect(html).toContain("8–16 giây");
    expect(html).toContain("Đang tạo ảnh mở đầu");
    expect(html).toContain("/opening.png");
    expect(html).not.toContain("Chưa có clip để xem");
});

it("shows a stopped image check without claiming that KIE is rendering or that a product mismatch was observed", () => {
    const html = output(generationProject(true));
    expect(html).toContain("Chưa đủ bằng chứng kiểm tra ảnh");
    expect(html).toContain("0 lượt đã gửi KIE");
    expect(html).not.toContain('data-active="true"');
    expect(html).not.toContain("Chưa có clip để xem");
    expect(html).not.toContain("Ảnh sai");
});
