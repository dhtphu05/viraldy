import type { SmartRemakeProject } from "@/shared/api/smart-remake";
import { createRemakePreviewDemo } from "../demo/remake-preview-demo";
import { getRemakeClipGroups } from "./remake-clip-groups";

export const clipProject = () =>
    createRemakePreviewDemo(
        { id: "source", scenes: [], targetDuration: 12 } as unknown as SmartRemakeProject,
        "ready",
    );

export function groupCandidate() {
    const project = clipProject();
    const group = getRemakeClipGroups(project)[0];
    const affectedVersions = group.memberIds.map((sceneId, index) => ({
        sceneId,
        baseVersionId: project.scenes.find((scene) => scene.id === sceneId)!.activeVersionId!,
        candidateVersionId: `candidate-${index}`,
    }));
    const operationId = "group-repair";
    const receipt = {
        projectId: project.id,
        sceneId: affectedVersions[0].sceneId,
        versionId: affectedVersions[0].candidateVersionId,
        operationId,
        repairScope: "provider_group" as const,
        renderGroupId: group.id,
        affectedVersions,
    };
    const next = {
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
                        mediaHash: "candidate-hash",
                        videoUrl: "/candidate.mp4",
                        technicalCheck: { ...base.technicalCheck, mediaHash: "candidate-hash" },
                        providerMetadata: {
                            repairScope: "provider_group",
                            renderGroupId: group.id,
                            repairOperationId: operationId,
                            sourceOperationId: operationId,
                            requestId: "provider-task",
                            repairBaseTimeline: project
                                .draftTimeline!.items.filter((item) =>
                                    group.memberIds.includes(item.renderUnitId),
                                )
                                .map(({ renderUnitId, versionId, inFrame, outFrame }) => ({
                                    renderUnitId,
                                    versionId,
                                    inFrame,
                                    outFrame,
                                })),
                            repairAffectedVersions: affectedVersions.map((item) => ({
                                candidateVersionId: item.candidateVersionId,
                                baseVersionId: item.baseVersionId,
                                sceneId: item.sceneId,
                            })),
                        },
                    },
                ],
            };
        }),
    };
    return { project: next, group, receipt };
}
