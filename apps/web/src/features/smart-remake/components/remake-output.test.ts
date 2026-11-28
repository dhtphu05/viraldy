import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import type {
    SmartRemakeAssembly,
    SmartRemakeProject,
    SmartRemakeSceneVersion,
} from "@/shared/api/smart-remake";
import { RemakeOutput, RemakeVersionReview } from "./remake-output";

const version: SmartRemakeSceneVersion = {
    id: "active",
    parentVersionId: null,
    videoUrl: "https://example.com/scene.mp4",
    prompt: "Original intent",
    imagePrompt: "Original image",
    videoPrompt: "Original motion",
    source: "generated",
    createdAt: "2026-11-24T00:00:00Z",
    usedByRevision: 1,
    technicalCheck: { status: "passed", findings: [], checkedAt: "", mediaHash: "" },
};
const candidate: SmartRemakeSceneVersion = {
    ...version,
    id: "candidate",
    parentVersionId: "active",
    usedByRevision: null,
    videoUrl: "https://example.com/candidate.mp4",
    videoPrompt: "SNAPSHOT_NEW_MOTION",
};
const project: SmartRemakeProject = {
    id: "project",
    revision: 1,
    status: "ready",
    finalVideoUrl: "https://example.com/whole.mp4",
    downloadUrl: "https://example.com/download",
    provider: "unifically",
    targetDuration: 16,
    scenes: [
        {
            id: "scene-1",
            index: 0,
            startSecond: 0,
            durationSeconds: 8,
            activeVersionId: "active",
            prompt: "Original intent",
            imagePrompt: "Original image",
            videoPrompt: "Original motion",
            versions: [version, candidate],
        },
    ],
};
const props = {
    workspaceId: "workspace",
    project,
    result: null,
    busy: false,
    onRepair: vi.fn(),
    onAccept: vi.fn(),
    onRefresh: vi.fn(),
};

describe("RemakeOutput", () => {
    it("never exposes the private preview or legacy download URL as an export link", () => {
        const html = renderToStaticMarkup(createElement(RemakeOutput, props));
        expect(html).not.toContain('href="https://example.com/download"');
        expect(html).not.toContain('href="https://example.com/whole.mp4"');
    });
    const timelineProject: SmartRemakeProject = {
        ...project,
        schemaVersion: 2,
        targetDuration: 8,
        draftTimeline: {
            fps: 24,
            totalFrames: 192,
            items: [
                {
                    id: "item",
                    renderUnitId: "scene-1",
                    sourceSceneId: "source",
                    targetStartFrame: 0,
                    targetDurationFrames: 192,
                    versionId: "active",
                    inFrame: 0,
                    outFrame: 192,
                    reviewed: false,
                },
            ],
        },
    };
    it("labels a six-second generated clip using its actual stored frame count", () => {
        const html = renderToStaticMarkup(
            createElement(RemakeOutput, {
                ...props,
                project: {
                    ...timelineProject,
                    targetDuration: 12,
                    scenes: timelineProject.scenes.map((scene) => ({
                        ...scene,
                        versions: scene.versions.map((item) => ({
                            ...item,
                            rawDurationFrames: 144,
                        })),
                    })),
                },
            }),
        );
        expect(html).toContain("Clip AI · 6 giây");
        expect(html).not.toContain("Clip AI · 8 giây");
    });
    it("makes the matched whole preview primary and keeps scene confirmation inside Advanced", () => {
        const value: SmartRemakeProject = {
            ...timelineProject,
            assemblies: {
                activeAssemblyId: "preview",
                records: [
                    {
                        id: "preview",
                        reviewMode: "whole_video",
                        timeline: timelineProject.draftTimeline!,
                        technicalCheck: { status: "passed", mediaHash: "preview" },
                    } as SmartRemakeAssembly,
                ],
            },
        };
        const html = renderToStaticMarkup(
            createElement(RemakeOutput, { ...props, project: value, guided: true }),
        );
        expect(html).toContain("Bản xem trước toàn video");
        expect(html).toContain("Chưa duyệt xuất");
        expect(html).toContain('src="https://example.com/whole.mp4"');
        expect(html).not.toContain("Dùng đoạn này");
        expect(html).not.toContain("Đã chọn");
        expect(html).toContain("Nâng cao");
        expect(props.onRepair).not.toHaveBeenCalled();
    });

    it("labels a six-second saved raw clip without rewriting legacy clip durations", () => {
        const value: SmartRemakeProject = {
            ...timelineProject,
            targetDuration: 12,
            scenes: timelineProject.scenes.map((scene) => ({
                ...scene,
                rawDurationFrames: 144,
                durationSeconds: 6,
                versions: scene.versions.map((version) => ({ ...version, rawDurationFrames: 144 })),
            })),
        };
        const html = renderToStaticMarkup(
            createElement(RemakeOutput, { ...props, project: value }),
        );
        expect(html).toContain("Clip AI · 6 giây");
        expect(html).not.toContain("Clip AI · 8 giây");
    });
    it.each([false, true])(
        "keeps original generated images and prompt tools accessible on completed output (guided: %s)",
        (guided) => {
            const completed = {
                ...timelineProject,
                assemblies: {
                    activeAssemblyId: "preview",
                    records: [
                        {
                            id: "preview",
                            reviewMode: "whole_video",
                            timeline: timelineProject.draftTimeline!,
                            technicalCheck: { status: "passed", mediaHash: "preview" },
                        } as SmartRemakeAssembly,
                    ],
                },
                renderPlan: {
                    fps: 24,
                    provider: "kie",
                    units: [{ id: "scene-1", sourceSceneId: "source" }],
                    groups: [
                        { id: "group", renderUnitIds: ["scene-1"], targetDurationFrames: 192 },
                    ],
                },
                generationProgress: {
                    operationId: "original-render",
                    status: "completed",
                    startedAt: "2026-11-26T10:00:00Z",
                    updatedAt: "2026-11-26T10:01:00Z",
                    groups: [
                        {
                            groupId: "group",
                            stage: "completed",
                            videoSubmitted: true,
                            conditioningImages: [
                                {
                                    renderUnitId: "scene-1",
                                    url: "/opening.png",
                                    requestHash: "a".repeat(64),
                                    frameRole: "opening",
                                },
                            ],
                            kieRequest: {
                                model: "wan/3-0-video",
                                prompt: "EXACT_SENT_PROMPT",
                                requestHash: "request",
                            },
                        },
                    ],
                },
            } as unknown as SmartRemakeProject;
            const html = renderToStaticMarkup(
                createElement(RemakeOutput, { ...props, project: completed, guided }),
            );
            expect(html).toContain("Ảnh &amp; prompt");
            expect(html).not.toContain("EXACT_SENT_PROMPT");
        },
    );
    it.each([
        [0, "0–1.333"],
        [1 / 3, "0.333–1.667"],
    ] as const)(
        "rounds fractional scene ranges for display from %s seconds",
        (startSecond, expected) => {
            const value = {
                ...timelineProject,
                scenes: timelineProject.scenes.map((scene) => ({
                    ...scene,
                    startSecond,
                    durationSeconds: 32 / 24,
                })),
            };
            const html = renderToStaticMarkup(
                createElement(RemakeOutput, { ...props, project: value }),
            );
            expect(html).toContain(`Cảnh 1 · ${expected} giây`);
            expect(html).not.toContain("1.3333333333333333");
            expect(html).not.toContain("0.3333333333333333");
        },
    );
    it("shows the raw clip and unreviewed draft independently of a published video", () => {
        const html = renderToStaticMarkup(
            createElement(RemakeOutput, {
                ...props,
                project: timelineProject,
                onTimelineSave: vi.fn(),
                onPublish: vi.fn(),
            }),
        );
        expect(html).toContain("Các cảnh sẽ ghép");
        expect(html).toContain("Đoạn cắt mặc định · Chưa chọn");
        expect(html).toContain("Clip AI · 8 giây");
        expect(html).toContain("Xem video đã xuất");
        expect(html).not.toContain(project.downloadUrl);
        const compose = (html.match(/<button[^>]*>[\s\S]*?<\/button>/g) ?? []).find((button) =>
            button.includes("Ghép video · 8 giây"),
        );
        expect(compose).toContain('disabled=""');
    });
    it("opens a grouped scene in its saved trim interval before any preview button click", () => {
        const value = {
            ...timelineProject,
            scenes: timelineProject.scenes.map((scene) => ({
                ...scene,
                startSecond: 3,
                durationSeconds: 5,
            })),
            draftTimeline: {
                ...timelineProject.draftTimeline!,
                items: timelineProject.draftTimeline!.items.map((item) => ({
                    ...item,
                    inFrame: 72,
                    outFrame: 192,
                    targetDurationFrames: 120,
                })),
            },
        };
        const html = renderToStaticMarkup(
            createElement(RemakeOutput, { ...props, project: value, onTimelineSave: vi.fn() }),
        );
        expect(html).toContain("Đoạn được chọn");
        expect(html).not.toContain("Toàn bộ video");
        expect(html).toContain("Cảnh 1 · 3–8 giây");
    });
    it("enables composition only after every fixed-length segment is reviewed", () => {
        const html = renderToStaticMarkup(
            createElement(RemakeOutput, {
                ...props,
                project: {
                    ...timelineProject,
                    draftTimeline: {
                        ...timelineProject.draftTimeline!,
                        items: timelineProject.draftTimeline!.items.map((item) => ({
                            ...item,
                            reviewed: true,
                        })),
                    },
                },
                onTimelineSave: vi.fn(),
                onPublish: vi.fn(),
            }),
        );
        const compose = (html.match(/<button[^>]*>[\s\S]*?<\/button>/g) ?? []).find((button) =>
            button.includes("Ghép video · 8 giây"),
        );
        expect(compose).toBeDefined();
        expect(compose).not.toContain('disabled=""');
    });
    it("uses actual frame bounds before the planned eight-second clip length", () => {
        const html = renderToStaticMarkup(
            createElement(RemakeOutput, {
                ...props,
                project: {
                    ...timelineProject,
                    scenes: [
                        {
                            ...timelineProject.scenes[0],
                            versions: [
                                {
                                    ...version,
                                    rawDurationFrames: 192,
                                    technicalCheck: { ...version.technicalCheck, frameCount: 191 },
                                },
                            ],
                        },
                    ],
                },
                onTimelineSave: vi.fn(),
                onPublish: vi.fn(),
            }),
        );
        expect(html).toContain("Clip này chưa đủ 8 giây");
        const use = (html.match(/<button[^>]*>[\s\S]*?<\/button>/g) ?? []).find((button) =>
            button.includes("Dùng đoạn này"),
        );
        expect(use).toContain('disabled=""');
    });
    it("keeps timeline scene browsing enabled while another v2 operation runs", () => {
        const html = renderToStaticMarkup(
            createElement(RemakeOutput, {
                ...props,
                project: {
                    ...timelineProject,
                    pendingOperation: { id: "job", status: "running", needsReconciliation: false },
                },
                onTimelineSave: vi.fn(),
                onPublish: vi.fn(),
            }),
        );
        const scene = (html.match(/<button[^>]*>[\s\S]*?<\/button>/g) ?? []).find((button) =>
            button.includes("<strong>Cảnh 1</strong>"),
        );
        expect(scene).toBeDefined();
        expect(scene).not.toContain('disabled=""');
        expect(html).toContain(version.videoUrl);
        expect(html).not.toContain(project.downloadUrl);
    });
    it("starts with actual private preview and scene media without an unchecked download", () => {
        const html = renderToStaticMarkup(createElement(RemakeOutput, props));
        expect(html).toContain(project.finalVideoUrl);
        expect(html).toContain(version.videoUrl);
        expect(html).toContain("0–8 giây");
        expect(html).toContain("Preview riêng tư");
        expect(html).not.toContain(project.downloadUrl);
        expect(html).not.toContain(candidate.videoPrompt);
    });
    it("does not present submitted output as playable or repairable", () => {
        const html = renderToStaticMarkup(
            createElement(RemakeOutput, {
                ...props,
                project: null,
                result: { status: "submitted", finalVideoUrl: "https://example.com/not-ready.mp4" },
            }),
        );
        expect(html).toContain("Đang tạo video");
        expect(html).not.toContain("<video");
        expect(html).not.toContain("Tạo lại cảnh");
    });
    it("labels demonstration video and does not offer targeted repair", () => {
        const html = renderToStaticMarkup(
            createElement(RemakeOutput, {
                ...props,
                project: null,
                result: { status: "completed", finalVideoUrl: "/demo.mp4", isDemo: true },
            }),
        );
        expect(html).toContain("Video minh họa");
        expect(html).not.toContain("Tạo lại cảnh");
    });
    it("keeps scene selection available when the whole video is incomplete", () => {
        const html = renderToStaticMarkup(
            createElement(RemakeOutput, {
                ...props,
                project: {
                    ...project,
                    status: "incomplete",
                    finalVideoUrl: "",
                    scenes: [
                        project.scenes[0],
                        {
                            ...project.scenes[0],
                            id: "scene-2",
                            index: 1,
                            startSecond: 8,
                            activeVersionId: null,
                            versions: [],
                        },
                    ],
                },
            }),
        );
        expect(html).toContain("Cần hoàn thiện cảnh");
        expect(html).toContain("Danh sách cảnh");
        expect(html).toContain("8–16 giây");
        expect(html).toContain(version.videoUrl);
        expect(html).not.toContain('src=""');
        expect(html).not.toContain("Tải toàn video");
    });
    it("does not claim a fixture validation has started a real video job", () => {
        const html = renderToStaticMarkup(
            createElement(RemakeOutput, {
                ...props,
                project: null,
                result: { status: "submitted", finalVideoUrl: "", provider: "fixture" },
            }),
        );
        expect(html).toContain("Đã kiểm tra yêu cầu · Chưa tạo video");
        expect(html).not.toContain("Đang tạo video");
        expect(html).not.toContain("Video sẽ xuất hiện");
        expect(html).not.toContain("Kiểm tra kết quả");
    });
    it("makes saved candidates discoverable from the scene strip", () => {
        const html = renderToStaticMarkup(createElement(RemakeOutput, props));
        expect(html).toContain("1 bản mới chờ xem");
    });
    it("offers composition recovery only when every scene has a checked active clip", () => {
        const incomplete: SmartRemakeProject = {
            ...project,
            status: "incomplete",
            finalVideoUrl: "",
        };
        const html = renderToStaticMarkup(
            createElement(RemakeOutput, { ...props, project: incomplete }),
        );
        expect(html).toContain("Ghép lại video");
        expect(html).toContain("Không tạo lại cảnh bằng AI");
        const missing = renderToStaticMarkup(
            createElement(RemakeOutput, {
                ...props,
                project: {
                    ...incomplete,
                    scenes: [
                        ...incomplete.scenes,
                        {
                            ...project.scenes[0],
                            id: "missing",
                            activeVersionId: null,
                            versions: [],
                        },
                    ],
                },
            }),
        );
        expect(missing).not.toContain("Ghép lại video");
        const failed = renderToStaticMarkup(
            createElement(RemakeOutput, {
                ...props,
                project: {
                    ...incomplete,
                    scenes: [
                        {
                            ...project.scenes[0],
                            versions: [
                                {
                                    ...version,
                                    technicalCheck: { ...version.technicalCheck, status: "failed" },
                                },
                            ],
                        },
                    ],
                },
            }),
        );
        expect(failed).not.toContain("Ghép lại video");
    });
    it("blocks scene changes while an existing operation reconciles and keeps refresh enabled", () => {
        const html = renderToStaticMarkup(
            createElement(RemakeOutput, {
                ...props,
                project: {
                    ...project,
                    pendingOperation: {
                        id: "pending",
                        status: "running",
                        needsReconciliation: true,
                    },
                },
            }),
        );
        expect(html).toContain('aria-busy="true"');
        expect(html).toContain(
            "Chưa xác định được kết quả của yêu cầu trước. Bấm Kiểm tra lại để cập nhật; nếu trạng thái không đổi, hãy nhờ hỗ trợ kiểm tra tác vụ trước khi tạo tiếp.",
        );
        const buttons = html.match(/<button\b[^>]*>[\s\S]*?<\/button>/g) ?? [];
        const refresh = buttons.find((button) => button.includes("Kiểm tra lại"));
        const scene = buttons.find((button) => button.includes("Hình xem trước cảnh 1"));
        expect(refresh).toBeDefined();
        expect(refresh).not.toContain('disabled=""');
        expect(scene).toContain('disabled=""');
    });
    it("explains that saved KIE work updates automatically and cannot be sent again", () => {
        const html = renderToStaticMarkup(
            createElement(RemakeOutput, {
                ...props,
                project: {
                    ...project,
                    provider: "kie",
                    status: "incomplete",
                    finalVideoUrl: "",
                    scenes: [{ ...project.scenes[0], activeVersionId: null, versions: [] }],
                    pendingOperation: {
                        id: "pending",
                        status: "running",
                        needsReconciliation: false,
                    },
                },
            }),
        );
        expect(html).toContain("Đang tạo video");
        expect(html).toContain("Kết quả sẽ tự cập nhật");
        expect(html).not.toContain("Cần hoàn thiện cảnh");
        expect(html).not.toContain("Tải toàn video");
        expect(html).toContain('aria-busy="true"');
        const buttons = html.match(/<button\b[^>]*>[\s\S]*?<\/button>/g) ?? [];
        expect(buttons.find((button) => button.includes(">Cảnh 1</span>"))).toContain(
            'disabled=""',
        );
    });
    it("treats a running result as pending when project recovery is not yet available", () => {
        const html = renderToStaticMarkup(
            createElement(RemakeOutput, {
                ...props,
                project: null,
                result: { status: "running", provider: "kie", finalVideoUrl: "" },
            }),
        );
        expect(html).toContain("Đang tạo video");
        expect(html).not.toContain("<video");
        expect(html).not.toContain("Tải toàn video");
    });
    it.each([
        ["KIE_CREDITS_EXHAUSTED", "hết lượt sử dụng"],
        ["KIE_AUTH_FAILED", "Nhờ quản trị viên kiểm tra kết nối"],
    ])(
        "announces %s after async failure while keeping the good video and clips",
        (errorCode, expected) => {
            const html = renderToStaticMarkup(
                createElement(RemakeOutput, {
                    ...props,
                    project: {
                        ...project,
                        provider: "kie",
                        lastOperation: { id: "failed-repair", status: "failed", errorCode },
                    },
                }),
            );
            expect(html).toContain('role="alert"');
            expect(html).toContain(expected);
            expect(html).toContain(project.finalVideoUrl);
            expect(html).toContain(version.videoUrl);
            expect(html).toContain("Preview riêng tư");
            expect(html).toContain('aria-busy="false"');
            expect(html).not.toContain(errorCode);
        },
    );
    it("removes the previous failure alert when the latest operation succeeds", () => {
        const html = renderToStaticMarkup(
            createElement(RemakeOutput, {
                ...props,
                project: {
                    ...project,
                    provider: "kie",
                    lastOperation: { id: "completed-repair", status: "completed" },
                },
            }),
        );
        expect(html).not.toContain('role="alert"');
        expect(html).toContain(project.finalVideoUrl);
    });
});

describe("RemakeVersionReview", () => {
    const render = (next = candidate) =>
        renderToStaticMarkup(
            createElement(RemakeVersionReview, {
                project: {
                    ...project,
                    scenes: [{ ...project.scenes[0], versions: [version, next] }],
                },
                sceneId: "scene-1",
                version: next,
                busy: false,
                onAccept: vi.fn(),
            }),
        );
    it("shows the generated version's immutable prompt snapshot", () => {
        expect(render()).toContain("SNAPSHOT_NEW_MOTION");
        expect(render()).toContain("Dùng bản này");
        expect(render()).not.toContain('disabled=""');
    });
    it.each(["failed", "needs_review"] as const)(
        "blocks %s candidates and shows findings",
        (status) => {
            const html = render({
                ...candidate,
                technicalCheck: {
                    ...candidate.technicalCheck,
                    status,
                    findings: ["Không xác nhận được thời lượng"],
                },
            });
            expect(html).toContain("Không xác nhận được thời lượng");
            expect(html).toContain('disabled=""');
        },
    );
    it("blocks stale candidates even when their technical check passed", () => {
        expect(render({ ...candidate, parentVersionId: "obsolete" })).toContain('disabled=""');
    });
    it("offers explicit restore for a previously used version", () => {
        const html = render({ ...candidate, parentVersionId: "obsolete", usedByRevision: 1 });
        expect(html).toContain("Khôi phục bản này");
        expect(html).not.toContain('disabled=""');
    });
});
