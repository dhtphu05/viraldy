import { Film, RefreshCw } from "lucide-react";
import type { SmartRemakeProject } from "@/shared/api/smart-remake";
import { Button } from "@/shared/ui/button";
import { RemakeGenerationProgress } from "./remake-generation-progress";
import { getRemakeGenerationProgress } from "../lib/remake-generation-progress";

interface Props {
    project: SmartRemakeProject;
    guided?: boolean;
    busy: boolean;
    recoveryPresented?: boolean;
    operationError: string | null;
    onRefresh(): void;
    onViewInspection?(reportId: string): void;
}

export function RemakeEmptyOutput({
    project,
    guided,
    busy,
    recoveryPresented,
    operationError,
    onRefresh,
    onViewInspection,
}: Props) {
    if (!recoveryPresented && getRemakeGenerationProgress(project))
        return (
            <RemakeGenerationProgress
                project={project}
                busy={busy}
                onCheckStatus={onRefresh}
                onViewInspection={onViewInspection}
            />
        );
    const sourceCount = project.sourceSceneMap?.scenes.length ?? project.scenes.length;
    const fragmentCount = project.renderPlan?.units.length ?? project.scenes.length;
    const uncertain =
        project.pendingOperation?.needsReconciliation || project.lastOperation?.needsReconciliation;
    return (
        <section
            aria-label="Kết quả Smart Remake"
            className="remake-output space-y-4"
            aria-busy={busy || Boolean(project.pendingOperation)}
        >
            <header className="remake-output-header flex flex-wrap items-center justify-between gap-3">
                <div>
                    <h2 className={guided ? "sr-only" : "text-xl font-semibold"}>Xem & ghép</h2>
                    <div className="remake-output-specs" aria-label="Thông tin video">
                        <span>{project.targetDuration} giây</span>
                        <span>{sourceCount} cảnh nguồn</span>
                        <span>{fragmentCount} đoạn dựng</span>
                    </div>
                </div>
                {!recoveryPresented && (
                    <Button type="button" variant="ghost" disabled={busy} onClick={onRefresh}>
                        <RefreshCw aria-hidden="true" />
                        {uncertain || project.pendingOperation
                            ? "Kiểm tra trạng thái"
                            : "Làm mới dự án"}
                    </Button>
                )}
            </header>
            {fragmentCount > sourceCount && (
                <p className="text-xs leading-relaxed text-text-secondary">
                    Một cảnh nguồn có thể được chia thành hai đoạn khi đi qua mốc 8 giây; số cảnh
                    nguồn không đổi.
                </p>
            )}
            {!recoveryPresented && (
                <div className="remake-output-empty" role="status">
                    <Film aria-hidden="true" />
                    <div>
                        <h3>Chưa có clip để xem</h3>
                        <p>
                            {uncertain
                                ? "Kiểm tra trạng thái lượt đã gửi trước khi tạo tiếp."
                                : project.pendingOperation
                                  ? "Các clip sẽ xuất hiện khi lượt tạo video hoàn tất."
                                  : "Tư liệu và kịch bản đã lưu vẫn được giữ. Kiểm tra lượt tạo video để tiếp tục."}
                        </p>
                    </div>
                </div>
            )}
            {operationError && (
                <p
                    role="alert"
                    className="rounded-xl bg-destructive-soft p-4 text-sm text-destructive"
                >
                    {operationError}
                </p>
            )}
        </section>
    );
}
