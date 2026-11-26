// @vitest-environment jsdom
import { cleanup, fireEvent, render } from "@testing-library/react";
import { createElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { SmartRemakeProject, SmartRemakeSceneVersion } from "@/shared/api/smart-remake";
import { RemakeOutput } from "./remake-output";

const active: SmartRemakeSceneVersion = {
    id: "active",
    parentVersionId: null,
    videoUrl: "/active.mp4",
    prompt: "scene",
    imagePrompt: "image",
    videoPrompt: "motion",
    source: "generated",
    createdAt: "",
    usedByRevision: 1,
    technicalCheck: { status: "passed", findings: [], checkedAt: "", mediaHash: "hash" },
};
const candidate = {
    ...active,
    id: "candidate",
    parentVersionId: "active",
    usedByRevision: null,
    videoUrl: "/candidate.mp4",
};
const project: SmartRemakeProject = {
    id: "project",
    revision: 1,
    schemaVersion: 2,
    status: "ready",
    provider: "kie",
    targetDuration: 8,
    finalVideoUrl: "",
    scenes: [
        {
            id: "scene",
            index: 0,
            startSecond: 0,
            durationSeconds: 8,
            activeVersionId: "active",
            prompt: "scene",
            imagePrompt: "image",
            videoPrompt: "motion",
            versions: [active],
        },
    ],
};
const props = {
    workspaceId: "workspace",
    project,
    result: null,
    busy: false,
    onRepair: vi.fn().mockResolvedValue(null),
    onAccept: vi.fn().mockResolvedValue(false),
    onRefresh: vi.fn(),
};
afterEach(cleanup);

describe("guided result focus", () => {
    it("does not repeat output metadata or empty tools below an existing generation recovery", () => {
        const empty = {
            ...project,
            scenes: [{ ...project.scenes[0], activeVersionId: null, versions: [] }],
        };
        const view = render(
            createElement(RemakeOutput, {
                ...props,
                project: empty,
                guided: true,
                generationRecoveryVisible: true,
            }),
        );
        expect(view.container.textContent).toBe("");
        expect(props.onRefresh).not.toHaveBeenCalled();
    });

    it("keeps a separate operation failure visible even when recovery is already shown", () => {
        const empty: SmartRemakeProject = {
            ...project,
            lastOperation: {
                id: "other",
                status: "failed",
                errorCode: "SMART_REMAKE_INPUT_CHANGED",
            },
            scenes: [{ ...project.scenes[0], activeVersionId: null, versions: [] }],
        };
        const view = render(
            createElement(RemakeOutput, {
                ...props,
                project: empty,
                guided: true,
                generationRecoveryVisible: true,
            }),
        );
        expect(view.getByRole("alert")).toBeTruthy();
        expect(view.queryByText("Chưa có clip để xem")).toBeNull();
        expect(view.queryByLabelText("Thông tin video")).toBeNull();
    });

    it("keeps player and scene tools visible while video metadata stays collapsed", () => {
        const refresh = vi.fn();
        const view = render(
            createElement(RemakeOutput, { ...props, guided: true, onRefresh: refresh }),
        );
        const details = view.getByText("1 cảnh nguồn").closest("details");
        expect(details).not.toBeNull();
        expect(details?.open).toBe(false);
        expect(view.container.querySelector('video[src="/active.mp4"]')).toBeTruthy();
        expect(view.getByRole("button", { name: "Sửa cảnh" })).toBeTruthy();
        fireEvent.click(view.getByText("Thông tin video"));
        fireEvent.click(view.getByRole("button", { name: "Làm mới dự án" }));
        expect(refresh).toHaveBeenCalledTimes(1);
    });

    it("uses one repair entry point in guided watch mode and keeps its form reachable", () => {
        const view = render(createElement(RemakeOutput, { ...props, guided: true }));
        expect(view.queryByText("Cảnh này đã đạt chưa?")).toBeNull();
        expect(view.queryByRole("button", { name: "Sửa và tạo lại cảnh" })).toBeNull();
        fireEvent.click(view.getByRole("button", { name: "Sửa cảnh" }));
        expect(view.getByLabelText("Bạn muốn thay đổi điều gì? (không bắt buộc)")).toBeTruthy();
        expect(props.onRepair).not.toHaveBeenCalled();
    });

    it("describes a saved trim as selected while content still needs review", () => {
        const value: SmartRemakeProject = {
            ...project,
            draftTimeline: {
                fps: 24,
                totalFrames: 192,
                items: [
                    {
                        id: "item",
                        sourceSceneId: "source",
                        renderUnitId: "scene",
                        targetStartFrame: 0,
                        targetDurationFrames: 192,
                        versionId: "active",
                        inFrame: 0,
                        outFrame: 192,
                        reviewed: true,
                    },
                ],
            },
        };
        const view = render(
            createElement(RemakeOutput, {
                ...props,
                project: value,
                guided: true,
                onTimelineSave: vi.fn(),
            }),
        );
        const selectedScene = view.getByRole("button", { name: /Cảnh 1.*Đã chọn/ });
        expect(selectedScene.getAttribute("title")).toContain("Đã chọn");
        expect(selectedScene.textContent).not.toMatch(/Đã duyệt|Chưa duyệt/);
        expect(view.getByText("Đã chọn đoạn · Chưa duyệt nội dung")).toBeTruthy();
    });
});

describe("confirmed repair handoff", () => {
    it("distinguishes 24 logical source scenes from 25 execution fragments", () => {
        const scenes = Array.from({ length: 25 }, (_, index) => ({
            ...project.scenes[0],
            id: `unit-${index}`,
            index,
            activeVersionId: null,
            versions: [],
        }));
        const value: SmartRemakeProject = {
            ...project,
            targetDuration: 16,
            scenes,
            sourceSceneMap: {
                fps: 24,
                sourceStartFrame: 0,
                sourceFrameCount: 720,
                scenes: Array.from({ length: 24 }, (_, index) => ({
                    id: `source-${index}`,
                    startFrame: index * 30,
                    endFrame: (index + 1) * 30,
                    targetDurationFrames: 16,
                })),
            },
        };
        const view = render(createElement(RemakeOutput, { ...props, project: value }));
        expect(view.getByText("24 cảnh nguồn")).toBeTruthy();
        expect(view.getByText("25 đoạn dựng")).toBeTruthy();
        expect(view.getByText(/Một cảnh nguồn có thể được chia/)).toBeTruthy();
        expect(view.queryByText("25 cảnh nguồn")).toBeNull();
    });
    it("does not offer repair, comparison or history before a usable base clip, even with forced navigation", () => {
        const empty = {
            ...project,
            scenes: [{ ...project.scenes[0], activeVersionId: null, versions: [] }],
        };
        const view = render(
            createElement(RemakeOutput, {
                ...props,
                project: empty,
                navigation: { requestId: "forced", sceneId: "scene", view: "repair" },
            }),
        );
        expect(
            view.queryByRole("button", { name: /^Sửa cảnh$|Sửa và tạo lại cảnh|So sánh|Lịch sử/ }),
        ).toBeNull();
        expect(view.queryByLabelText("Bạn muốn thay đổi điều gì? (không bắt buộc)")).toBeNull();
        expect(view.queryByRole("form")).toBeNull();
        expect(view.getByText("Chưa có clip để xem")).toBeTruthy();
        expect(props.onRepair).not.toHaveBeenCalled();
        view.rerender(createElement(RemakeOutput, props));
        fireEvent.click(view.getByRole("button", { name: "Sửa cảnh" }));
        expect(view.getByLabelText("Bạn muốn thay đổi điều gì? (không bắt buộc)")).toBeTruthy();
    });
    it("only opens a matching comparison after an explicit navigation and never on polling", () => {
        const view = render(createElement(RemakeOutput, props));
        expect(view.queryByText("Duyệt bản mới")).toBeNull();
        const repairCandidate = { projectId: "project", sceneId: "scene", versionId: "candidate" };
        view.rerender(createElement(RemakeOutput, { ...props, repairCandidate }));
        expect(view.queryByText("Duyệt bản mới")).toBeNull();
        const updated = {
            ...project,
            scenes: [{ ...project.scenes[0], versions: [active, candidate] }],
        };
        view.rerender(createElement(RemakeOutput, { ...props, project: updated, repairCandidate }));
        expect(view.queryByText("Duyệt bản mới")).toBeNull();
        const navigation = {
            requestId: "open-candidate",
            sceneId: "scene",
            versionId: "candidate",
            view: "compare" as const,
        };
        view.rerender(
            createElement(RemakeOutput, {
                ...props,
                project: updated,
                repairCandidate,
                navigation,
            }),
        );
        expect(view.getByText("Duyệt bản mới")).toBeTruthy();
        fireEvent.click(view.getByRole("button", { name: /^Xem$/ }));
        view.rerender(
            createElement(RemakeOutput, {
                ...props,
                project: { ...updated },
                repairCandidate: { ...repairCandidate },
                navigation,
            }),
        );
        expect(view.queryByText("Duyệt bản mới")).toBeNull();
    });

    it("keeps cancellation, queued repair and another project's candidate from opening comparison", () => {
        const updated = {
            ...project,
            scenes: [{ ...project.scenes[0], versions: [active, candidate] }],
        };
        const view = render(
            createElement(RemakeOutput, { ...props, project: updated, repairCandidate: null }),
        );
        expect(view.queryByText("Duyệt bản mới")).toBeNull();
        view.rerender(
            createElement(RemakeOutput, {
                ...props,
                project: updated,
                repairCandidate: { projectId: "other", sceneId: "scene", versionId: "candidate" },
            }),
        );
        expect(view.queryByText("Duyệt bản mới")).toBeNull();
        expect(props.onRepair).not.toHaveBeenCalled();
    });
});
