import { ArrowRight, Camera, Clapperboard, Images, Sparkles } from "lucide-react";
import { RemakeProcessingVisual } from "./remake-processing-visual";

export function RemakeProcessing({
    kind,
    sourceUrl,
    productUrl,
}: {
    kind: "analyze" | "generate";
    sourceUrl?: string | null;
    productUrl?: string | null;
}) {
    const analyzing = kind === "analyze";
    return (
        <section
            className="remake-enter remake-processing rounded-3xl bg-surface p-5 sm:p-8"
            aria-label="Tiến trình Smart Remake"
        >
            <div className="remake-processing__eyebrow">
                <span aria-hidden="true" /> SMART REMAKE ·{" "}
                {analyzing ? "ĐỌC CẢM HỨNG" : "TẠO CHUYỂN ĐỘNG"}
            </div>
            <RemakeProcessingVisual kind={kind} />
            <div
                role="status"
                aria-live="polite"
                aria-atomic="true"
                className="space-y-2 text-center"
            >
                <h2 className="text-xl font-semibold text-text-primary">
                    {analyzing ? "Đang phân tích video mẫu…" : "Đang tạo video cho bạn…"}
                </h2>
                <p className="mx-auto max-w-lg text-sm leading-relaxed text-text-secondary">
                    {analyzing
                        ? "AI đang đọc cách quay, hành động và nhịp dựng của mẫu. Bạn sẽ duyệt kịch bản trước khi tạo video."
                        : "Chuẩn bị ảnh tham chiếu và tạo các nhóm cảnh theo kịch bản đã duyệt. Bạn sẽ xem từng đoạn trước khi ghép video."}
                </p>
            </div>
            <div className="remake-processing__concepts">
                <span>
                    <Camera aria-hidden="true" /> {analyzing ? "Góc quay" : "Ảnh tham chiếu"}
                </span>
                <span>
                    <Images aria-hidden="true" /> {analyzing ? "Hành động" : "Cảnh quay"}
                </span>
                <span>
                    <Clapperboard aria-hidden="true" /> {analyzing ? "Nhịp dựng" : "Chuyển động"}
                </span>
            </div>
            {(sourceUrl || productUrl) && (
                <div className="remake-processing__context">
                    {sourceUrl && (
                        <div>
                            <video
                                src={sourceUrl}
                                muted
                                playsInline
                                preload="metadata"
                                aria-label="Video mẫu đang dùng"
                            />
                            <span>Video mẫu</span>
                        </div>
                    )}
                    {sourceUrl && productUrl && (
                        <span className="text-text-tertiary" aria-hidden="true">
                            +
                        </span>
                    )}
                    {productUrl && (
                        <div>
                            <img src={productUrl} alt="Sản phẩm đang dùng" />
                            <span>Sản phẩm của bạn</span>
                        </div>
                    )}
                    <ArrowRight className="size-4 shrink-0 text-text-tertiary" aria-hidden="true" />
                    <div>
                        <span className="remake-processing__destination">
                            <Sparkles aria-hidden="true" />
                        </span>
                        <span>{analyzing ? "Kịch bản mới" : "Video của bạn"}</span>
                    </div>
                </div>
            )}
            <p className="text-center text-xs text-text-secondary">
                Giữ trang này mở trong lúc xử lý nhé.
            </p>
        </section>
    );
}
