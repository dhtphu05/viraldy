// @vitest-environment jsdom
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { SmartRemakeProject, SmartRemakeSceneVersion } from "@/shared/api/smart-remake";
import { RemakeOutput } from "../components/remake-output";
import { RemakeRepairForm } from "../components/remake-repair-form";
import { getRemakeResultNextAction } from "./remake-result-next-action";
import { getRemakeSceneLabel } from "./remake-scene-label";

const version: SmartRemakeSceneVersion = {
    id: "active",
    parentVersionId: null,
    videoUrl: "/clip.mp4",
    prompt: "action",
    imagePrompt: "image",
    videoPrompt: "video",
    source: "generated",
    createdAt: "",
    technicalCheck: { status: "passed", findings: [], checkedAt: "", mediaHash: "clip" },
};
const units = [0, 1].map((index) => ({
    id: `fragment-${index}`,
    sourceSceneId: "logical-source",
    sceneIndex: index,
    fragmentIndex: index,
    fragmentCount: 2,
    sourceStartFrame: index * 360,
    sourceEndFrame: (index + 1) * 360,
    rawDurationFrames: 192,
    targetDurationFrames: 192,
    prompt: "action",
    imagePrompt: "image",
    videoPrompt: "video",
}));
const project: SmartRemakeProject = {
    id: "project",
    revision: 1,
    schemaVersion: 2,
    status: "ready",
    provider: "kie",
    targetDuration: 16,
    finalVideoUrl: "",
    sourceSceneMap: {
        fps: 24,
        sourceStartFrame: 0,
        sourceFrameCount: 720,
        timingMode: "fit_target",
        scenes: [{ id: "logical-source", startFrame: 0, endFrame: 720, targetDurationFrames: 384 }],
    },
    renderPlan: { fps: 24, provider: "kie", units },
    scenes: units.map((unit, index) => ({
        id: unit.id,
        index,
        startSecond: index * 8,
        durationSeconds: 8,
        activeVersionId: index === 0 ? "active" : null,
        prompt: "action",
        imagePrompt: "image",
        videoPrompt: "video",
        versions: index === 0 ? [version] : [],
    })),
    draftTimeline: {
        fps: 24,
        totalFrames: 384,
        items: units.map((unit, index) => ({
            id: `item-${index}`,
            sourceSceneId: "logical-source",
            renderUnitId: unit.id,
            targetStartFrame: index * 192,
            targetDurationFrames: 192,
            inFrame: 0,
            outFrame: 192,
            versionId: index === 0 ? "active" : null,
            reviewed: false,
        })),
    },
};
const text = (html: string) => html.replace(/<[^>]*>/g, "").replace(/\s+/g, " ");

describe("logical scene labels across render fragments", () => {
    it("keeps legacy and unavailable project labels readable", () => {
        expect(getRemakeSceneLabel(null, "missing", 4)).toBe("Cảnh 5");
        expect(getRemakeSceneLabel({ ...project, renderPlan: undefined }, "fragment-1")).toBe(
            "Cảnh 2",
        );
        expect(getRemakeSceneLabel(project, "missing", 3)).toBe("Cảnh 4");
    });

    it("uses the logical source order for an unsplit scene after a fragmented scene", () => {
        const laterSource = {
            ...project.sourceSceneMap!,
            scenes: [
                { ...project.sourceSceneMap!.scenes[0], endFrame: 600, targetDurationFrames: 240 },
                { id: "next-source", startFrame: 600, endFrame: 720, targetDurationFrames: 144 },
            ],
        };
        const laterUnit = {
            ...units[1],
            id: "later-unit",
            sourceSceneId: "next-source",
            sceneIndex: 2,
            fragmentIndex: 0,
            fragmentCount: 1,
        };
        expect(
            getRemakeSceneLabel(
                {
                    ...project,
                    sourceSceneMap: laterSource,
                    renderPlan: { ...project.renderPlan!, units: [...units, laterUnit] },
                },
                "later-unit",
                2,
            ),
        ).toBe("Cảnh 2");
    });

    it("guides to a provider fragment without inventing another source scene", () => {
        expect(getRemakeResultNextAction({ project })).toMatchObject({
            sceneId: "fragment-1",
            label: "Xem cảnh 1 · đoạn 2/2 cần xử lý",
        });
    });

    it("names a new candidate by its logical scene and provider fragment", () => {
        const candidateProject = {
            ...project,
            scenes: project.scenes.map((scene, index) =>
                index === 1 ? { ...scene, versions: [{ ...version, id: "candidate" }] } : scene,
            ),
        };
        expect(
            getRemakeResultNextAction({
                project: candidateProject,
                candidate: { projectId: project.id, sceneId: "fragment-1", versionId: "candidate" },
            }),
        ).toMatchObject({
            sceneId: "fragment-1",
            versionId: "candidate",
            label: "Xem bản mới cảnh 1 · đoạn 2/2",
        });
    });

    it("shows source scene count separately while requiring review of every fragment", () => {
        const html = renderToStaticMarkup(
            createElement(RemakeOutput, {
                workspaceId: "workspace",
                project,
                result: null,
                busy: false,
                onRepair: vi.fn(),
                onAccept: vi.fn(),
                onRefresh: vi.fn(),
            }),
        );
        const output = text(html);
        expect(output).toContain("Cảnh 1 · đoạn 1/2");
        expect(output).toContain("Cảnh 1 · đoạn 2/2");
        expect(output).toContain("1 cảnh nguồn");
        expect(output).toContain("Đã chọn 0/2 đoạn");
        expect(output).not.toContain("Cảnh 2");
    });

    it("makes the selected fragment explicit in repair scope and CTA", () => {
        const html = renderToStaticMarkup(
            createElement(RemakeRepairForm, {
                workspaceId: "workspace",
                projectId: project.id,
                scene: { ...project.scenes[1], activeVersionId: version.id, versions: [version] },
                active: version,
                sceneLabel: "Cảnh 1 · đoạn 2/2",
                busy: false,
                onRepair: vi.fn(),
            }),
        );
        expect(text(html)).toContain("Tạo lại cảnh 1 · đoạn 2/2");
        expect(text(html)).toContain("8 giây của cảnh 1 · đoạn 2/2");
    });
});
