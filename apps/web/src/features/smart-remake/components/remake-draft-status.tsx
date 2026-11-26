import { Button } from "@/shared/ui/button";
import type { RemakeDraftSaveStatus } from "../lib/use-remake-studio-draft";

const labels: Record<RemakeDraftSaveStatus, string> = {
    loading: "Đang khôi phục nháp…",
    unsaved: "Có thay đổi chưa lưu trên thiết bị",
    saving: "Đang lưu tư liệu và chỉnh sửa…",
    saved: "Đã lưu trên thiết bị này",
    error: "Chưa lưu được trên thiết bị",
    conflict: "Có nháp cần xem lại",
};
const sections: Record<string, string> = {
    intake: "tư liệu",
    requirements: "yêu cầu",
    storyboard: "kịch bản",
    repair: "sửa cảnh",
    view: "màn đang xem",
};
interface Props {
    status: RemakeDraftSaveStatus;
    error?: string | null;
    conflicts?: Record<string, unknown>;
    onRetry?(): void;
    onDiscard?(section: string): void;
    onRemove?(): void;
}
export function RemakeDraftStatus(props: Props) {
    const conflicts = Object.entries(props.conflicts ?? {});
    return (
        <section
            aria-label="Nháp trên thiết bị"
            className="rounded-2xl border border-control-border bg-surface px-4 py-3 text-xs text-text-secondary"
        >
            <div className="flex flex-wrap items-center justify-between gap-2">
                <p role="status" aria-live="polite">
                    {labels[props.status]}
                </p>
                {props.status === "error" && props.onRetry && (
                    <Button type="button" variant="ghost" onClick={props.onRetry}>
                        Thử lưu lại
                    </Button>
                )}
            </div>
            {props.error && (
                <p role="alert" className="mt-2 text-warn">
                    {props.error}
                </p>
            )}
            <details className="mt-1">
                <summary className="min-h-8 cursor-pointer py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                    Về bản nháp trên thiết bị
                    {conflicts.length ? ` · ${conflicts.length} phần cần xem lại` : ""}
                </summary>
                <p>
                    Video, ảnh và chỉnh sửa được lưu trong trình duyệt này. Xóa dữ liệu trình duyệt
                    sẽ xóa nháp. Dự án trên máy chủ được giữ riêng.
                </p>
                {conflicts.map(([name, section]) => (
                    <div key={name} className="mt-3 space-y-2 border-t border-control-border pt-3">
                        <h3 className="font-medium">Nháp {sections[name] ?? name} cũ</h3>
                        <p>
                            Phần này không còn khớp dữ liệu hiện tại. Bạn có thể chọn và sao chép
                            nội dung trước khi bỏ nháp cũ.
                        </p>
                        <details>
                            <summary className="min-h-9 cursor-pointer py-2">
                                Nâng cao: xem nội dung để sao chép
                            </summary>
                            <pre
                                tabIndex={0}
                                className="max-h-48 overflow-auto whitespace-pre-wrap break-words rounded-xl bg-surface-soft p-3"
                            >
                                {JSON.stringify(
                                    section && typeof section === "object" && "value" in section
                                        ? section.value
                                        : section,
                                    null,
                                    2,
                                )}
                            </pre>
                        </details>
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => props.onDiscard?.(name)}
                        >
                            Bỏ nháp {sections[name] ?? name} cũ
                        </Button>
                    </div>
                ))}
                {props.onRemove && (
                    <Button type="button" variant="ghost" className="mt-2" onClick={props.onRemove}>
                        Xóa nháp trên thiết bị này
                    </Button>
                )}
            </details>
        </section>
    );
}
