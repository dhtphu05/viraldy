import type { SmartRemakeCompileResult } from "@/shared/api/smart-remake";

export type RemakeSceneView = {
    id: string;
    index: number;
    start: number;
    end: number;
    title: string;
    description: string;
    prompt: string;
    imagePrompt: string;
    videoPrompt: string;
};

export type RemakeScenePatch = Partial<
    Pick<RemakeSceneView, "prompt" | "imagePrompt" | "videoPrompt">
>;

function text(value: unknown): string {
    return typeof value === "string" ? value.trim() : "";
}

function record(value: unknown): Record<string, unknown> {
    return value !== null && typeof value === "object" && !Array.isArray(value)
        ? (value as Record<string, unknown>)
        : {};
}

export function getSceneRange(index: number): { start: number; end: number } {
    return { start: index * 8, end: (index + 1) * 8 };
}

export function getRemakeScenes(
    compiled: SmartRemakeCompileResult | null | undefined,
): RemakeSceneView[] {
    return (compiled?.sceneMap.scenes ?? []).map((scene, index) => {
        const shotPlan = record(scene.shotPlan);
        const shots = Array.isArray(shotPlan.shots) ? shotPlan.shots : [];
        const description = shots
            .map((shot) => {
                const details = record(shot);
                return text(details.physicalAction) || text(details.action);
            })
            .filter(Boolean)
            .join(" · ");

        const unit = compiled?.schemaVersion === 2 ? compiled.renderPlan?.units[index] : undefined;
        const startFrame =
            compiled?.renderPlan?.units
                .slice(0, index)
                .reduce((sum, value) => sum + value.targetDurationFrames, 0) ?? 0;
        const range = unit
            ? { start: startFrame / 24, end: (startFrame + unit.targetDurationFrames) / 24 }
            : getSceneRange(index);

        return {
            id: unit?.id || text(scene.id) || `scene-${index + 1}`,
            index,
            ...range,
            title: text(scene.textOverlay) || `Cảnh ${index + 1}`,
            description: description || text(scene.description),
            prompt: typeof scene.prompt === "string" ? scene.prompt : "",
            imagePrompt: typeof scene.imagePrompt === "string" ? scene.imagePrompt : "",
            videoPrompt: typeof scene.videoPrompt === "string" ? scene.videoPrompt : "",
        };
    });
}

export function updateRemakeScene(
    compiled: SmartRemakeCompileResult,
    index: number,
    patch: RemakeScenePatch,
): SmartRemakeCompileResult {
    const scene = compiled.sceneMap.scenes[index];
    if (!Number.isInteger(index) || !scene) throw new Error("Cảnh không tồn tại.");

    const fields = ["prompt", "imagePrompt", "videoPrompt"] as const;
    const updates = Object.fromEntries(
        fields
            .filter((field) => patch[field] !== undefined)
            .map((field) => {
                const value = text(patch[field]);
                if (!value) throw new Error("Nội dung tạo cảnh không được để trống.");
                return [field, value];
            })
            .filter(([field, value]) => scene[field] !== value),
    );
    if (!Object.keys(updates).length) return compiled;

    const originals = {
        originalPrompt:
            typeof scene.originalPrompt === "string" ? scene.originalPrompt : scene.prompt,
        originalImagePrompt:
            typeof scene.originalImagePrompt === "string"
                ? scene.originalImagePrompt
                : scene.imagePrompt,
        originalVideoPrompt:
            typeof scene.originalVideoPrompt === "string"
                ? scene.originalVideoPrompt
                : scene.videoPrompt,
    };
    const updatedScene = { ...scene, ...updates, promptEdited: true, ...originals };
    if (compiled.sourceSceneMap?.timingMode === "fit_target") {
        return {
            ...compiled,
            sceneMap: {
                ...compiled.sceneMap,
                scenes: compiled.sceneMap.scenes.map((item, itemIndex) =>
                    itemIndex === index ? updatedScene : item,
                ),
            },
            ...(compiled.renderPlan
                ? {
                      renderPlan: {
                          ...compiled.renderPlan,
                          units: compiled.renderPlan.units.map((unit, unitIndex) =>
                              unitIndex === index ? { ...unit, ...updates } : unit,
                          ),
                      },
                  }
                : {}),
        };
    }
    const displayOrder = typeof scene.displayOrder === "number" ? scene.displayOrder : index;
    const mirrorIndex = compiled.compiledPrompts.findIndex(
        (item) => item.displayOrder === displayOrder,
    );
    const compiledPrompts =
        mirrorIndex === -1
            ? [
                  ...compiled.compiledPrompts,
                  {
                      displayOrder,
                      promptEdited: true,
                      ...originals,
                      ...Object.fromEntries(fields.map((field) => [field, updatedScene[field]])),
                  },
              ]
            : compiled.compiledPrompts.map((item, itemIndex) =>
                  itemIndex === mirrorIndex
                      ? { ...item, ...updates, promptEdited: true, ...originals }
                      : item,
              );

    return {
        ...compiled,
        sceneMap: {
            ...compiled.sceneMap,
            scenes: compiled.sceneMap.scenes.map((item, itemIndex) =>
                itemIndex === index ? updatedScene : item,
            ),
        },
        compiledPrompts,
    };
}

export function getContainedMediaSize(
    width: number,
    height: number,
    maxWidth: number,
    maxHeight: number,
): { width: number; height: number } {
    if (
        ![width, height, maxWidth, maxHeight].every((value) => Number.isFinite(value) && value > 0)
    ) {
        return { width: 0, height: 0 };
    }
    const scale = Math.min(maxWidth / width, maxHeight / height);
    return {
        width: Math.min(width * scale, maxWidth),
        height: Math.min(height * scale, maxHeight),
    };
}
