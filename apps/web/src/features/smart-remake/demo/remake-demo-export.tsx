import { Check, FileText } from "lucide-react";
import type { SmartRemakeProject } from "@/shared/api/smart-remake";
import { Button } from "@/shared/ui/button";
import { RemakePlayer } from "../components/remake-player";
import { DEMO_ASSETS } from "./remake-demo-state";

export function RemakeDemoExport({ project }: { project: SmartRemakeProject }) {
    const failures =
        project.inspectionSummary?.reports
            .flatMap((report) => report.findings)
            .filter((finding) => finding.status === "failed").length ?? 0;
    return (
        <section className="report-demo-export" aria-label="Duyệt và xuất bản minh họa">
            <RemakePlayer
                url={`${DEMO_ASSETS}preview-ai.mp4`}
                scope={null}
                versionLabel="Bản ghép có nhãn AI · 16 giây"
            />
            <div>
                <span className="report-demo-status">
                    <FileText size={15} /> Bản xuất minh họa · Có nhãn AI
                </span>
                <h2 className="mt-5 text-xl font-semibold">Duyệt bản video này</h2>
                <div className="report-demo-export__checks">
                    <p>
                        <Check size={16} /> Bản ghép 16 giây · 720 × 1280 · 24 fps
                    </p>
                    <p>
                        <Check size={16} /> Nhãn “AI-generated” đã được ghi vào video
                    </p>
                    <p>Inspector bản trước sửa: {failures} vấn đề cần sửa</p>
                    <p>Bản ghép minh họa này chưa được kiểm tra nội dung và phê duyệt.</p>
                </div>
                <Button disabled className="w-full">
                    Duyệt nội dung bản ghép này
                </Button>
                <p className="my-4 text-xs leading-relaxed text-text-secondary">
                    Hoàn tất kiểm tra và xem xét các vấn đề trên đúng bản ghép trước khi duyệt thành
                    phẩm. File bên dưới là video minh họa đã chuẩn bị, có nhãn AI.
                </p>
                <a
                    className="report-demo-download"
                    href={`${DEMO_ASSETS}preview-ai.mp4`}
                    download="viraldy-demo-ai.mp4"
                >
                    Tải video minh họa có nhãn AI
                </a>
            </div>
        </section>
    );
}
