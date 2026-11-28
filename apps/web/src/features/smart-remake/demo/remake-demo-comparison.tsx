import { Check } from "lucide-react";
import type { SmartRemakeProject } from "@/shared/api/smart-remake";
import { Button } from "@/shared/ui/button";
import { RemakePlayer } from "../components/remake-player";
import type { RemakeDemoFixture } from "./remake-demo-state";

export function RemakeDemoComparison({
    project,
    comparison,
    onChoose,
}: {
    project: SmartRemakeProject;
    comparison: RemakeDemoFixture["comparison"];
    onChoose(versionId: string): void;
}) {
    const scene = project.scenes.find((value) => value.id === comparison.sceneId);
    const before = scene?.versions.find((version) => version.id === comparison.beforeVersionId);
    const after = scene?.versions.find((version) => version.id === comparison.afterVersionId);
    if (!before || !after) return <p>Chưa có đủ hai video trước và sau sửa.</p>;
    const checked = [before, after].every((version) => version.technicalCheck.status === "passed");
    return (
        <section className="report-demo-comparison" aria-label="So sánh hai bản trước và sau sửa">
            <RemakePlayer
                url={before.videoUrl}
                compareUrl={after.videoUrl}
                scope={{ start: 0, end: 8 }}
                compareScope={{ start: 0, end: 8 }}
                versionLabel="Bản hiện tại"
                compareLabel="Bản tạo lại"
            />
            <div className="report-demo-comparison__decision">
                <div>
                    <span className="report-demo-status">
                        <Check size={16} />{" "}
                        {checked ? "Hai bản đạt kiểm tra kỹ thuật" : "Cần kiểm tra kỹ thuật thêm"}
                    </span>
                    <h2>Giữ bản nào cho cảnh này?</h2>
                    <p>
                        Đối chiếu sản phẩm, chuyển động và bối cảnh trước khi chọn. Kiểm tra kỹ
                        thuật không thay thế duyệt nội dung.
                    </p>
                </div>
                <div>
                    <Button variant="ghost" onClick={() => onChoose(before.id)}>
                        Giữ bản hiện tại
                    </Button>
                    <Button
                        onClick={() => onChoose(after.id)}
                        className="bg-primary-active text-white"
                    >
                        Dùng bản mới
                    </Button>
                </div>
            </div>
            <p className="mt-4 text-xs text-text-secondary">
                Nguồn: output_truoc_vali.mp4 và output_vali.mp4 (đoạn 0–8 giây). Phiên demo chỉ nhập
                hai tệp do người dùng cung cấp.
            </p>
        </section>
    );
}
