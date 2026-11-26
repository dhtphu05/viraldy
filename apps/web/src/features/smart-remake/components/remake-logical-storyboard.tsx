import { useId } from "react";
import { Clock3, Film } from "lucide-react";
import type { SmartRemakeCompileResult } from "@/shared/api/smart-remake";
import { Textarea } from "@/shared/ui/textarea";
import { RemakeImagePreview } from "./remake-image-preview";

interface Props {
    compiled: SmartRemakeCompileResult;
    selectedScene: number;
    onSceneChange(index: number, patch: Record<string, string>): void;
    disabled?: boolean;
}

const seconds = (frames: number) => Number((frames / 24).toFixed(3));
const promptFields = [
    ["videoPrompt", "video"],
    ["imagePrompt", "ảnh"],
    ["prompt", "tổng hợp"],
] as const;

export function RemakeLogicalStoryboard({
    compiled,
    selectedScene,
    onSceneChange,
    disabled,
}: Props) {
    const id = useId();
    const sources = compiled.sourceSceneMap?.scenes ?? [];
    const units = compiled.renderPlan?.units ?? [];
    return sources.map((source, index) => {
        const start = sources
            .slice(0, index)
            .reduce((sum, scene) => sum + scene.targetDurationFrames, 0);
        const fragments = units
            .map((unit, unitIndex) => ({ unit, unitIndex }))
            .filter(({ unit }) => unit.sourceSceneId === source.id);
        const shots = source.shotPlan?.shots;
        const description = Array.isArray(shots)
            ? shots
                  .map((shot) => (typeof shot?.action === "string" ? shot.action : ""))
                  .filter(Boolean)
                  .join(" · ")
            : source.prompt;
        return (
            <section
                key={source.id}
                hidden={selectedScene !== index}
                aria-labelledby={`${id}-${index}-title`}
                className="remake-script-scene min-w-0 space-y-5 rounded-3xl bg-surface p-5 sm:p-6"
            >
                <header className="remake-script-scene__header">
                    <div className="min-w-0 flex-1">
                        <h2
                            id={`${id}-${index}-title`}
                            className="text-lg font-semibold text-text-primary"
                        >
                            Cảnh {index + 1}
                        </h2>
                    </div>
                    {source.thumbnailUrl && (
                        <div className="remake-script-scene__thumbnail">
                            <RemakeImagePreview
                                src={source.thumbnailUrl}
                                alt={`Khung hình tham chiếu cảnh ${index + 1}`}
                                compact
                            />
                        </div>
                    )}
                </header>
                <div className="remake-script-scene__timing">
                    <p>
                        <Film aria-hidden="true" /> {seconds(source.startFrame)}–
                        {seconds(source.endFrame)} giây nguồn
                    </p>
                    <p>
                        <Clock3 aria-hidden="true" /> {seconds(start)}–
                        {seconds(start + source.targetDurationFrames)} giây đầu ra
                    </p>
                </div>
                <div className="remake-script-scene__action space-y-3">
                    <h3 className="text-sm font-medium">Điều sẽ diễn ra</h3>
                    <p className="whitespace-pre-wrap text-sm leading-relaxed text-text-secondary">
                        {description || "Hành động và cách quay từ cảnh tương ứng trong video mẫu."}
                    </p>
                </div>
                <p className="remake-script-scene__intent text-sm leading-relaxed text-text-secondary">
                    <span>
                        Giữ hành động và cách quay của cảnh, thay bằng sản phẩm của bạn. Thời lượng
                        được phân bổ lại để giữ đủ cảnh trong video đầu ra.
                    </span>
                </p>
                <details className="remake-script-scene__advanced rounded-2xl bg-surface-soft p-4">
                    <summary className="min-h-8 cursor-pointer text-sm font-medium">
                        Nâng cao · Prompt tự động của cảnh
                    </summary>
                    <div className="mt-4 space-y-4">
                        {promptFields.map(([field, label]) => (
                            <label key={field} className="block space-y-2 text-sm">
                                <span>
                                    Prompt {label} của cảnh {index + 1}
                                </span>
                                <Textarea
                                    readOnly
                                    value={source[field] ?? ""}
                                    className="min-h-28 bg-surface"
                                />
                            </label>
                        ))}
                        <details className="rounded-xl bg-surface p-3">
                            <summary className="min-h-8 cursor-pointer text-sm font-medium">
                                Hướng dẫn thực thi · {fragments.length} đoạn render
                            </summary>
                            <p className="my-3 text-xs leading-relaxed text-text-secondary">
                                Các đoạn này thực hiện cùng một cảnh nguồn. Số lượt KIE được tính
                                theo nhóm render, không theo số cảnh phân tích.
                            </p>
                            <div className="space-y-5">
                                {fragments.map(({ unit, unitIndex }) => (
                                    <div key={unit.id} className="space-y-3">
                                        <h4 className="text-sm font-medium">
                                            Đoạn render {unitIndex + 1} ·{" "}
                                            {seconds(unit.targetDurationFrames)} giây sử dụng
                                        </h4>
                                        {promptFields.map(([field, label]) => (
                                            <label key={field} className="block space-y-2 text-xs">
                                                <span>
                                                    Prompt {label} đoạn render {unitIndex + 1}
                                                </span>
                                                <Textarea
                                                    disabled={disabled}
                                                    value={
                                                        typeof compiled.sceneMap.scenes[
                                                            unitIndex
                                                        ]?.[field] === "string"
                                                            ? (compiled.sceneMap.scenes[unitIndex][
                                                                  field
                                                              ] as string)
                                                            : unit[field]
                                                    }
                                                    onChange={(event) =>
                                                        onSceneChange(unitIndex, {
                                                            [field]: event.target.value,
                                                        })
                                                    }
                                                    className="min-h-28 bg-surface-soft"
                                                />
                                            </label>
                                        ))}
                                    </div>
                                ))}
                            </div>
                        </details>
                    </div>
                </details>
            </section>
        );
    });
}
