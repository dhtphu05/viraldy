import { Check, Loader2 } from "lucide-react";
import type { SmartRemakeProject, SmartRemakeSceneVersion } from "@/shared/api/smart-remake";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import { canUseRemakeVersion } from "../lib/remake-review";

const primaryButton =
    "min-h-12 bg-[#e00b41] text-sm text-white hover:bg-[#c90a3a] focus-visible:ring-[#e00b41]/40";

export function RemakeVersionReview({
    project,
    sceneId,
    version,
    busy,
    onAccept,
}: {
    project: SmartRemakeProject;
    sceneId: string;
    version: SmartRemakeSceneVersion;
    busy: boolean;
    onAccept(versionId: string): void;
}) {
    const canApply = canUseRemakeVersion(project, sceneId, version.id);
    const checked = version.technicalCheck.status === "passed";
    const historical = Boolean(version.usedByRevision);
    return (
        <div className="space-y-4">
            <div>
                <h3 className="font-medium text-text-primary">
                    {historical ? "Xem lại bản trước" : "Duyệt bản mới"}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-text-secondary">
                    Đối chiếu sản phẩm và chuyển động trên hai bản. Kiểm tra kỹ thuật không đánh giá
                    độ đúng của sản phẩm hoặc chất lượng sáng tạo.
                </p>
            </div>
            <div
                className={cn(
                    "rounded-2xl p-4 text-sm",
                    checked
                        ? "bg-primary-soft text-text-primary"
                        : "bg-surface-soft text-text-secondary",
                )}
            >
                <p className="flex items-center gap-2 font-medium">
                    {checked && <Check className="size-4" aria-hidden="true" />}
                    {checked
                        ? "Đạt kiểm tra kỹ thuật"
                        : version.technicalCheck.status === "failed"
                          ? "Chưa đạt kiểm tra kỹ thuật"
                          : "Cần kiểm tra thêm"}
                </p>
                {version.technicalCheck.findings.length > 0 && (
                    <ul className="mt-2 list-disc space-y-1 pl-5">
                        {version.technicalCheck.findings.map((finding, index) => (
                            <li key={`${index}-${finding}`}>{finding}</li>
                        ))}
                    </ul>
                )}
                {!checked && (
                    <p className="mt-2 text-xs">
                        Chưa thể áp dụng bản này. Hãy tạo bản khác hoặc kiểm tra lại dữ liệu dự án.
                    </p>
                )}
                {checked && !canApply && (
                    <p className="mt-2 text-xs">
                        Bản đang dùng đã thay đổi hoặc bản này đã được áp dụng. Hãy chọn lại bản phù
                        hợp trong lịch sử.
                    </p>
                )}
            </div>
            <details>
                <summary className="min-h-11 cursor-pointer rounded-lg py-3 text-sm font-medium text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                    Nâng cao · Yêu cầu đã dùng cho phiên bản này
                </summary>
                <dl className="space-y-3 rounded-xl bg-surface-soft p-4 text-xs leading-relaxed text-text-secondary">
                    <div>
                        <dt className="mb-1 font-medium text-text-primary">Video</dt>
                        <dd className="whitespace-pre-wrap break-words">{version.videoPrompt}</dd>
                    </div>
                    <div>
                        <dt className="mb-1 font-medium text-text-primary">Hình ảnh</dt>
                        <dd className="whitespace-pre-wrap break-words">{version.imagePrompt}</dd>
                    </div>
                    <div>
                        <dt className="mb-1 font-medium text-text-primary">Mô tả tổng thể</dt>
                        <dd className="whitespace-pre-wrap break-words">{version.prompt}</dd>
                    </div>
                </dl>
            </details>
            <Button
                type="button"
                className={cn(primaryButton, "w-full")}
                disabled={busy || !canApply}
                onClick={() => onAccept(version.id)}
            >
                {busy ? (
                    <Loader2 className="motion-safe:animate-spin" aria-hidden="true" />
                ) : (
                    <Check aria-hidden="true" />
                )}
                {historical ? "Khôi phục bản này" : "Dùng bản này"}
            </Button>
            <p className="text-xs leading-relaxed text-text-secondary">
                {project.schemaVersion === 2
                    ? "Dùng bản này sẽ cập nhật bản nháp và bỏ duyệt đoạn cắt cũ. Chọn lại đoạn phù hợp rồi ghép; video đã xuất vẫn được giữ."
                    : "Áp dụng sẽ ghép lại toàn video với cảnh này. Các cảnh khác giữ nguyên; bản trước vẫn có trong lịch sử."}
            </p>
        </div>
    );
}
