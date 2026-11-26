import type { SmartRemakeProject } from "@/shared/api/smart-remake";

export function getRemakeSceneLabel(
    project: SmartRemakeProject | null | undefined,
    renderUnitId: string,
    fallbackIndex = 0,
): string {
    const unit = project?.renderPlan?.units.find((item) => item.id === renderUnitId);
    const sourceIndex = unit
        ? (project?.sourceSceneMap?.scenes.findIndex((scene) => scene.id === unit.sourceSceneId) ??
          -1)
        : -1;
    const index =
        sourceIndex >= 0
            ? sourceIndex
            : (project?.scenes.find((scene) => scene.id === renderUnitId)?.index ?? fallbackIndex);
    const label = `Cảnh ${index + 1}`;
    const fragmentCount = unit?.fragmentCount ?? 1;
    return fragmentCount > 1
        ? `${label} · đoạn ${(unit?.fragmentIndex ?? 0) + 1}/${fragmentCount}`
        : label;
}
