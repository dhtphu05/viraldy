import type { SmartRemakeProject, SmartRemakeRenderPlan } from "@/shared/api/smart-remake";
import { DEMO_ASSETS } from "./remake-demo-state";
import type { RemakeRepairCandidate } from "../lib/remake-action";

const previewHash = "b9b9fef829ffdebdc025b96b31878488c1eb848f538612b63fd0a25b29437f90";
const clipHashes = [
    "28bd7947c39443fa8afb3c9983f6b2b72ecc0060661323c863bdabd8793d3a2f",
    "bf771cc499d61ab2c14c6d14518511d4b8bf8dd466add8df99f2fbd81e810d62",
];
const clipUrls = ["whole-preview-first.mp4", "whole-preview-second.mp4"];

export function createRemakeClipRepairDemo(source: SmartRemakeProject): {
    project: SmartRemakeProject;
    candidate: RemakeRepairCandidate;
} {
    const project = createRemakePreviewDemo(source, "ready");
    const group = project.renderPlan!.groups![0];
    const affectedVersions = group.renderUnitIds.map((sceneId, index) => ({
        sceneId,
        baseVersionId: project.scenes.find((scene) => scene.id === sceneId)!.activeVersionId!,
        candidateVersionId: `fixture-candidate-${index + 1}`,
    }));
    const operationId = "fixture-clip-repair";
    const repairBaseTimeline = project
        .draftTimeline!.items.filter((item) => group.renderUnitIds.includes(item.renderUnitId))
        .map(({ renderUnitId, versionId, inFrame, outFrame }) => ({
            renderUnitId,
            versionId,
            inFrame,
            outFrame,
        }));
    const candidate: RemakeRepairCandidate = {
        projectId: project.id,
        sceneId: affectedVersions[0].sceneId,
        versionId: affectedVersions[0].candidateVersionId,
        operationId,
        repairScope: "provider_group",
        renderGroupId: group.id,
        affectedVersions,
    };
    return {
        candidate,
        project: {
            ...project,
            scenes: project.scenes.map((scene) => {
                const binding = affectedVersions.find((value) => value.sceneId === scene.id);
                if (!binding) return scene;
                const base = scene.versions[0];
                return {
                    ...scene,
                    versions: [
                        ...scene.versions,
                        {
                            ...base,
                            id: binding.candidateVersionId,
                            parentVersionId: binding.baseVersionId,
                            mediaHash: clipHashes[1],
                            videoUrl: `${DEMO_ASSETS}${clipUrls[1]}`,
                            technicalCheck: { ...base.technicalCheck, mediaHash: clipHashes[1] },
                            providerMetadata: {
                                repairScope: "provider_group",
                                renderGroupId: group.id,
                                repairOperationId: operationId,
                                sourceOperationId: operationId,
                                repairAffectedVersions: affectedVersions,
                                repairBaseTimeline,
                            },
                        },
                    ],
                };
            }),
        },
    };
}

// Explicit UI fixture: the source is a 2× slower local copy of the preview.
// Source frame bounds double while output/provider clocks stay unchanged; no AI is called.
export function createRemakePreviewDemo(
    source: SmartRemakeProject,
    status: "ready" | "processing",
): SmartRemakeProject {
    const lengths = [...Array<number>(12).fill(12), ...Array<number>(12).fill(11), 12];
    let cursor = 0;
    const units: SmartRemakeRenderPlan["units"] = lengths.map((length, index) => {
        const start = cursor;
        cursor += length;
        return {
            id: `fixture-unit-${index + 1}`,
            sourceSceneId: `fixture-source-${index + 1}`,
            sceneIndex: index,
            sourceStartFrame: start,
            sourceEndFrame: cursor,
            rawDurationFrames: 144,
            targetDurationFrames: length,
            prompt: "Cảnh minh họa giao diện từ video có sẵn.",
            imagePrompt: "Ảnh tham chiếu minh họa.",
            videoPrompt: "Đoạn cắt minh họa, không gửi lượt tạo mới.",
        };
    });
    const groups: NonNullable<SmartRemakeRenderPlan["groups"]> = [0, 1].map((index) => {
        const members = units.filter((unit) => Math.floor(unit.sourceStartFrame! / 144) === index);
        return {
            id: `fixture-group-${index + 1}`,
            renderUnitIds: members.map((unit) => unit.id),
            rawDurationFrames: 144,
            targetDurationFrames: 144,
            segments: members.map((unit) => ({
                renderUnitId: unit.id,
                inFrame: unit.sourceStartFrame! - index * 144,
                outFrame: unit.sourceEndFrame! - index * 144,
            })),
        };
    });
    const scenes: SmartRemakeProject["scenes"] = units.map((unit, index) => {
        const groupIndex = index < 12 ? 0 : 1;
        const segment = groups[groupIndex].segments.find((item) => item.renderUnitId === unit.id)!;
        const versionId = `fixture-version-${index + 1}`;
        return {
            id: unit.id,
            index,
            startSecond: unit.sourceStartFrame! / 24,
            durationSeconds: unit.targetDurationFrames / 24,
            rawDurationFrames: 144,
            activeVersionId: versionId,
            prompt: unit.prompt,
            imagePrompt: unit.imagePrompt,
            videoPrompt: unit.videoPrompt,
            description: "Đoạn minh họa trong bộ dữ liệu UI, không phải kết quả AI mới.",
            versions: [
                {
                    id: versionId,
                    parentVersionId: null,
                    videoUrl: `${DEMO_ASSETS}${clipUrls[groupIndex]}`,
                    prompt: unit.prompt,
                    imagePrompt: unit.imagePrompt,
                    videoPrompt: unit.videoPrompt,
                    source: "generated",
                    createdAt: "2026-11-28T00:00:00Z",
                    rawDurationFrames: 144,
                    frameCount: 144,
                    renderGroupId: groups[groupIndex].id,
                    suggestedInFrame: segment.inFrame,
                    suggestedOutFrame: segment.outFrame,
                    technicalCheck: {
                        status: "passed",
                        mediaHash: clipHashes[groupIndex],
                        frameCount: 144,
                        checkedAt: "2026-11-28T00:00:00Z",
                        findings: [],
                    },
                },
            ],
        };
    });
    const timeline = {
        fps: 24 as const,
        totalFrames: 288,
        items: scenes.map((scene, index) => ({
            id: `fixture-selection-${index + 1}`,
            sourceSceneId: units[index].sourceSceneId,
            renderUnitId: scene.id,
            targetStartFrame: units[index].sourceStartFrame!,
            targetDurationFrames: units[index].targetDurationFrames,
            versionId: scene.activeVersionId,
            inFrame: scene.versions[0].suggestedInFrame!,
            outFrame: scene.versions[0].suggestedOutFrame!,
            reviewed: false,
        })),
    };
    return {
        ...source,
        id: "fixture-whole-preview",
        revision: 1,
        schemaVersion: 2,
        phase: "rendered",
        status: status === "ready" ? "ready" : "incomplete",
        targetDuration: 12,
        provider: "kie",
        sourceVideoUrl: `${DEMO_ASSETS}whole-preview-source.mp4`,
        finalVideoUrl: status === "ready" ? `${DEMO_ASSETS}whole-preview.mp4` : "",
        expectationsHash: source.expectationsHash ?? "fixture-whole-preview-base-expectations",
        constraintsHash: "fixture-whole-preview-constraints",
        scenes,
        sourceSceneMap: {
            fps: 24,
            timingMode: "fit_target",
            sourceStartFrame: 0,
            sourceFrameCount: 576,
            scenes: units.map((unit, index) => ({
                id: unit.sourceSceneId,
                startFrame: unit.sourceStartFrame! * 2,
                endFrame: unit.sourceEndFrame! * 2,
                targetDurationFrames: unit.targetDurationFrames,
                thumbnailUrl: `${DEMO_ASSETS}scene-${String((index % 13) + 1).padStart(2, "0")}.jpg`,
            })),
        },
        renderPlan: {
            fps: 24,
            provider: "kie",
            videoModel: "wan/3-0-video",
            videoResolution: "720P",
            audioRequired: true,
            groupingPolicy: "fixed_provider_windows",
            units: units.map((unit) => ({
                ...unit,
                sourceStartFrame: unit.sourceStartFrame! * 2,
                sourceEndFrame: unit.sourceEndFrame! * 2,
            })),
            groups,
        },
        draftTimeline: timeline,
        publishedTimeline: status === "ready" ? timeline : undefined,
        preview: {
            schemaVersion: 1,
            status,
            operationId: "fixture-compose",
            sourceRenderOperationId: "fixture-render",
            ...(status === "ready" ? { assemblyId: "fixture-assembly" } : {}),
        },
        assemblies:
            status === "ready"
                ? {
                      activeAssemblyId: "fixture-assembly",
                      records: [
                          {
                              id: "fixture-assembly",
                              projectId: "fixture-whole-preview",
                              schemaVersion: 2,
                              reviewMode: "whole_video",
                              parentAssemblyId: null,
                              mediaHash: previewHash,
                              manifestHash: "fixture-whole-preview-manifest",
                              constraintsHash: "fixture-whole-preview-constraints",
                              expectationsHash: "fixture-whole-preview-selected-expectations",
                              contextHash: "fixture-whole-preview-context",
                              revision: 1,
                              createdAt: "2026-11-28T00:00:00Z",
                              technicalCheck: {
                                  status: "passed",
                                  mediaHash: previewHash,
                                  frameCount: 288,
                              },
                              timeline,
                          },
                      ],
                  }
                : undefined,
        generationProgress: {
            operationId: "fixture-render",
            status: "completed",
            startedAt: "2026-11-28T00:00:00Z",
            updatedAt: "2026-11-28T00:00:00Z",
            groups: groups.map((group, index) => ({
                groupId: group.id,
                stage: "completed",
                videoSubmitted: null,
                videoUrl: `${DEMO_ASSETS}${clipUrls[index]}`,
            })),
        },
        pendingOperation: undefined,
        lastOperation: undefined,
        generationRecovery: undefined,
        inspectionSummary: undefined,
        release: undefined,
    };
}
