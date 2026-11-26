import type { SmartRemakeProject } from "@/shared/api/smart-remake";

export function canUseRemakeVersion(
    project: SmartRemakeProject,
    sceneId: string,
    versionId: string,
): boolean {
    const scene = project.scenes.find((item) => item.id === sceneId);
    const version = scene?.versions.find((item) => item.id === versionId);
    if (!scene || !version || version.id === scene.activeVersionId) return false;
    if (version.technicalCheck.status !== "passed") return false;
    return Boolean(version.usedByRevision) || version.parentVersionId === scene.activeVersionId;
}

export function latestRemakeProject(
    current: SmartRemakeProject | null,
    incoming: SmartRemakeProject,
): SmartRemakeProject {
    return current?.id === incoming.id && current.revision > incoming.revision ? current : incoming;
}
