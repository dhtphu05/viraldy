import type {
    SmartRemakeCompileResult,
    SmartRemakeProject,
    SmartRemakeSourceAudio,
    SmartRemakeTimelineSelectionInput,
} from "@/shared/api/smart-remake";

export const DEMO_ASSETS = "/smart-remake/report-demo/";

export type RemakeDemoFixture = {
    project: SmartRemakeProject;
    compiled: SmartRemakeCompileResult;
    quickSummary: {
        summary: string;
        observations: { label: string; detail: string }[];
        sourceAudio: SmartRemakeSourceAudio;
    };
    comparison: { sceneId: string; beforeVersionId: string; afterVersionId: string };
    provenance: { analysisCompletedAt: string };
};

// Demo interactions update this in-memory copy only. They never call project APIs.
export function selectDemoRanges(
    project: SmartRemakeProject,
    selections: SmartRemakeTimelineSelectionInput[],
): SmartRemakeProject {
    if (!project.draftTimeline) return project;
    return {
        ...project,
        draftTimeline: {
            ...project.draftTimeline,
            items: project.draftTimeline.items.map((item) => {
                const selection = selections.find(
                    (value) => value.renderUnitId === item.renderUnitId,
                );
                return selection ? { ...item, ...selection } : item;
            }),
        },
    };
}

export function applyDemoVersion(
    project: SmartRemakeProject,
    sceneId: string,
    versionId: string,
): SmartRemakeProject {
    const scene = project.scenes.find((value) => value.id === sceneId);
    if (!scene?.versions.some((version) => version.id === versionId)) return project;
    return {
        ...project,
        scenes: project.scenes.map((value) =>
            value.id === sceneId ? { ...value, activeVersionId: versionId } : value,
        ),
        draftTimeline: project.draftTimeline && {
            ...project.draftTimeline,
            items: project.draftTimeline.items.map((item) =>
                item.renderUnitId === sceneId ? { ...item, versionId, reviewed: false } : item,
            ),
        },
    };
}
