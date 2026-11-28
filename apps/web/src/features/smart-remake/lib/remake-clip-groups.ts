import type {
    SmartRemakeProject,
    SmartRemakeSceneVersion,
    SmartRemakeRepairAffectedVersion,
} from "@/shared/api/smart-remake";
import type { RemakeRepairCandidate } from "./remake-action";

type Scene = SmartRemakeProject["scenes"][number];
type Version = SmartRemakeSceneVersion;
type AffectedVersion = SmartRemakeRepairAffectedVersion;
export type RemakeClipGroup = {
    id: string;
    index: number;
    startSecond: number;
    endSecond: number;
    durationSeconds: number;
    memberIds: string[];
    anchorScene?: Scene;
    anchorVersion?: Version;
    baseFingerprint: string;
    videoUrl?: string;
    ready: boolean;
    pending: boolean;
    usesDefaultRanges: boolean;
};

const mediaHash = (version: Version | undefined) =>
    version?.mediaHash ?? version?.technicalCheck.mediaHash;

function sameAffectedVersions(value: unknown, expected: AffectedVersion[]): boolean {
    return (
        Array.isArray(value) &&
        value.length === expected.length &&
        value.every((entry, index) => {
            if (!entry || typeof entry !== "object") return false;
            const binding = entry as Record<string, unknown>;
            return (
                binding.sceneId === expected[index].sceneId &&
                binding.baseVersionId === expected[index].baseVersionId &&
                binding.candidateVersionId === expected[index].candidateVersionId
            );
        })
    );
}

export function getRemakeClipGroups(project: SmartRemakeProject): RemakeClipGroup[] {
    const plan = project.renderPlan;
    if (plan?.groupingPolicy !== "fixed_provider_windows") return [];
    let cursor = 0;
    return (plan.groups ?? []).map((group, index) => {
        const rawFrames =
            group.rawDurationFrames ??
            plan.units.find((unit) => unit.id === group.renderUnitIds[0])?.rawDurationFrames ??
            192;
        const startFrame = cursor;
        const startSecond = startFrame / plan.fps;
        cursor += group.targetDurationFrames;
        const members = group.renderUnitIds.map((id) =>
            project.scenes.find((scene) => scene.id === id),
        );
        const versions: Array<Version | undefined> = members.map((scene) =>
            scene?.versions.find((version) => version.id === scene.activeVersionId),
        );
        const first = versions[0];
        const hash = mediaHash(first);
        const mediaReady = Boolean(
            group.renderUnitIds.length &&
            hash &&
            versions.every(
                (version) =>
                    version?.videoUrl &&
                    version.technicalCheck.status === "passed" &&
                    mediaHash(version) === hash &&
                    mediaHash(version) === version.technicalCheck.mediaHash &&
                    (!version.renderGroupId || version.renderGroupId === group.id) &&
                    (version.frameCount ?? version.technicalCheck.frameCount ?? rawFrames) ===
                        rawFrames,
            ),
        );
        const selections = group.renderUnitIds.map((id) =>
            project.draftTimeline?.items.find((item) => item.renderUnitId === id),
        );
        let targetFrame = startFrame;
        const selectionValid =
            selections.every((item, memberIndex) => {
                if (
                    !item ||
                    item.versionId !== members[memberIndex]?.activeVersionId ||
                    !Number.isInteger(item.inFrame) ||
                    !Number.isInteger(item.outFrame) ||
                    item.inFrame < 0 ||
                    item.outFrame > rawFrames ||
                    item.targetDurationFrames <= 0 ||
                    item.outFrame - item.inFrame !== item.targetDurationFrames ||
                    item.targetStartFrame !== targetFrame
                )
                    return false;
                targetFrame += item.targetDurationFrames;
                return true;
            }) && targetFrame === cursor;
        const ready = mediaReady && selectionValid;
        const usesDefaultRanges =
            selectionValid &&
            selections.every((item, memberIndex) => {
                const segment = group.segments.find(
                    (value) => value.renderUnitId === group.renderUnitIds[memberIndex],
                );
                return item?.inFrame === segment?.inFrame && item?.outFrame === segment?.outFrame;
            });
        return {
            id: group.id,
            index: index + 1,
            startSecond,
            endSecond: cursor / plan.fps,
            durationSeconds: rawFrames / plan.fps,
            memberIds: [...group.renderUnitIds],
            anchorScene: members[0],
            anchorVersion: first,
            baseFingerprint: JSON.stringify(
                members.map((scene, memberIndex) => [
                    scene?.id,
                    scene?.activeVersionId,
                    mediaHash(versions[memberIndex]),
                    selections[memberIndex]?.versionId,
                    selections[memberIndex]?.inFrame,
                    selections[memberIndex]?.outFrame,
                    selections[memberIndex]?.targetStartFrame,
                    selections[memberIndex]?.targetDurationFrames,
                ]),
            ),
            videoUrl: mediaReady ? first?.videoUrl : undefined,
            ready,
            usesDefaultRanges,
            pending:
                !ready &&
                Boolean(
                    project.generationProgress?.groups.some(
                        (state) =>
                            state.groupId === group.id &&
                            [
                                "queued",
                                "preparing_image",
                                "checking_image",
                                "submitting_video",
                                "generating",
                                "checking",
                            ].includes(state.stage),
                    ),
                ),
        };
    });
}

export function getRemakeClipCandidate(
    project: SmartRemakeProject,
    group: RemakeClipGroup,
    receipt: RemakeRepairCandidate | null | undefined,
): { sceneId: string; version: Version } | null {
    if (
        !group.ready ||
        !receipt ||
        receipt.projectId !== project.id ||
        receipt.repairScope !== "provider_group" ||
        receipt.renderGroupId !== group.id ||
        !receipt.operationId
    )
        return null;
    const affected = receipt.affectedVersions;
    if (
        !affected?.length ||
        affected.length !== group.memberIds.length ||
        affected.some(
            (binding, index) =>
                binding.sceneId !== group.memberIds[index] ||
                typeof binding.baseVersionId !== "string" ||
                !binding.baseVersionId ||
                typeof binding.candidateVersionId !== "string" ||
                !binding.candidateVersionId,
        )
    )
        return null;
    const anchor = affected[0];
    if (receipt.sceneId !== anchor.sceneId || receipt.versionId !== anchor.candidateVersionId)
        return null;
    const versions: Version[] = [];
    for (const binding of affected) {
        if (typeof binding.baseVersionId !== "string" || !binding.baseVersionId) return null;
        const scene = project.scenes.find((value) => value.id === binding.sceneId);
        const version: Version | undefined = scene?.versions.find(
            (value) => value.id === binding.candidateVersionId,
        );
        const metadata = version?.providerMetadata;
        if (
            !version ||
            scene?.activeVersionId !== binding.baseVersionId ||
            version.parentVersionId !== binding.baseVersionId ||
            !version.videoUrl ||
            version.technicalCheck.status !== "passed" ||
            !mediaHash(version) ||
            mediaHash(version) !== version.technicalCheck.mediaHash ||
            metadata?.repairScope !== "provider_group" ||
            metadata.renderGroupId !== group.id ||
            metadata.repairOperationId !== receipt.operationId ||
            !sameAffectedVersions(metadata.repairAffectedVersions, affected)
        )
            return null;
        if (
            metadata.sourceOperationId !== undefined &&
            metadata.sourceOperationId !== receipt.operationId
        )
            return null;
        const frozenTimeline = metadata.repairBaseTimeline;
        if (
            !Array.isArray(frozenTimeline) ||
            frozenTimeline.length !== group.memberIds.length ||
            frozenTimeline.some((entry, index) => {
                if (!entry || typeof entry !== "object") return true;
                const saved = entry as Record<string, unknown>;
                const current = project.draftTimeline?.items.find(
                    (item) => item.renderUnitId === group.memberIds[index],
                );
                return (
                    !current ||
                    saved.renderUnitId !== current.renderUnitId ||
                    saved.versionId !== current.versionId ||
                    saved.inFrame !== current.inFrame ||
                    saved.outFrame !== current.outFrame
                );
            })
        )
            return null;
        versions.push(version);
    }
    const first = versions[0];
    if (
        versions.some(
            (version) =>
                mediaHash(version) !== mediaHash(first) ||
                version.technicalCheck.mediaHash !== first.technicalCheck.mediaHash ||
                (version.frameCount ?? version.technicalCheck.frameCount) !==
                    group.durationSeconds * 24,
        )
    )
        return null;
    const requestIds = versions.map((version) => version.providerMetadata?.requestId);
    if (
        requestIds.some((id) => id !== undefined) &&
        requestIds.some((id) => typeof id !== "string" || id !== requestIds[0])
    )
        return null;
    return { sceneId: anchor.sceneId, version: first };
}
