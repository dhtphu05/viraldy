import { ArrowLeft, ArrowUpRight, Check, FileText, ShieldCheck } from "lucide-react";

import { BrandLogo } from "@/shared/ui/brand-logo";
import {
    MEDIA_RIGHTS_ATTESTATION_TEXT,
    MEDIA_RIGHTS_POLICY_DATE,
    MEDIA_RIGHTS_POLICY_SUMMARY,
    MEDIA_RIGHTS_POLICY_VERSION,
} from "./media-rights-policy";

const sections = [
    {
        id: "quyen-su-dung",
        title: "01. Quyền với tư liệu bạn tải lên",
        paragraphs: [
            "Bạn cần sở hữu hoặc có đủ giấy phép, sự cho phép cần thiết để tải video, ảnh sản phẩm và tư liệu tham chiếu lên Viraldy, xử lý bằng AI và sử dụng cho mục đích quảng bá sản phẩm của dự án.",
            "Bạn chịu trách nhiệm về quyền sử dụng đối với hình ảnh, video, nhãn hiệu và các nội dung có trong tư liệu. Việc một nội dung được đăng công khai không tự tạo quyền sử dụng nội dung đó trong quảng cáo.",
            "Nếu giấy phép có giới hạn về thời gian, kênh phát hành hoặc yêu cầu ghi công, bạn cần tuân thủ các giới hạn đó. Bạn có thể bổ sung thông tin giấy phép và ghi công trong phần chi tiết quyền của dự án.",
        ],
    },
    {
        id: "hinh-anh-nhan-vat",
        title: "02. Hình ảnh và danh tính người thật",
        paragraphs: [
            "Bạn cần có sự đồng ý cần thiết của người xuất hiện trong tư liệu cho việc xử lý và sử dụng hình ảnh của họ theo mục đích của dự án.",
            "Nếu yêu cầu giữ hoặc tái tạo một nhân vật thật, bạn phải xác nhận riêng phạm vi đồng ý sử dụng hình ảnh và cung cấp tư liệu nhân vật có quyền sử dụng. Xác nhận chung cho video và ảnh sản phẩm không thay thế bước này.",
            "Không sử dụng tư liệu để mạo danh, tạo sự chứng thực sản phẩm giả hoặc làm người xem hiểu nhầm một người đã đồng ý quảng bá sản phẩm.",
        ],
    },
    {
        id: "xu-ly-bang-ai",
        title: "03. Xử lý tư liệu bằng AI",
        paragraphs: [
            "Khi bạn chạy Smart Remake, tư liệu liên quan được gửi tới các nhà cung cấp AI theo từng bước: Gemini để phân tích và kiểm tra, OpenAI để tạo ảnh tham chiếu, KIE để tạo video. Việc xử lý cũng chịu chính sách áp dụng của các nhà cung cấp tương ứng.",
            "Chỉ gửi tư liệu bạn được phép chia sẻ để xử lý bằng AI. Bạn cần xác nhận riêng việc gửi tư liệu tới nhà cung cấp AI trước khi bắt đầu tác vụ.",
            "Đọc trang này hoặc mở modal không tự chạy tác vụ AI. Chi phí phát sinh khi bạn chủ động bắt đầu các bước có sử dụng dịch vụ trả phí, trong giới hạn ngân sách đã đặt cho dự án.",
        ],
    },
    {
        id: "su-dung-ket-qua",
        title: "04. Kiểm tra và sử dụng video đầu ra",
        paragraphs: [
            "Kết quả AI có thể sai chi tiết sản phẩm, thao tác, chữ hoặc tuyên bố quảng cáo. Bạn cần kiểm tra video, xác nhận nội dung phù hợp với sản phẩm và chỉ sử dụng các tuyên bố có căn cứ.",
            "Kết quả kiểm tra của Smart Remake không phải kết luận xác minh bản quyền. Bạn vẫn cần bảo đảm có đủ quyền cho cách sử dụng và phát hành video dự kiến.",
            "Giữ nhãn AI của bản xuất và thực hiện các yêu cầu công bố nội dung AI áp dụng cho kênh bạn đăng video.",
        ],
    },
    {
        id: "ghi-nhan-xac-nhan",
        title: "05. Ghi nhận xác nhận và cập nhật tư liệu",
        paragraphs: [
            "Viraldy ghi nhận tài khoản xác nhận, thời điểm, nội dung và phiên bản chính sách cùng bộ tư liệu của dự án. Trạng thái “Người dùng đã xác nhận quyền” ghi nhận cam kết của bạn; trạng thái này không có nghĩa quyền sở hữu đã được xác minh độc lập.",
            "Khi thay video hoặc ảnh tham chiếu, bạn cần xác nhận lại cho bộ tư liệu mới. Bạn cũng cần cập nhật xác nhận nếu quyền sử dụng hoặc phạm vi được cho phép thay đổi.",
            "Viraldy có thể chặn xử lý hoặc xuất video khi quyền bị thu hồi, thiếu sự đồng ý cần thiết hoặc tư liệu không đáp ứng chính sách sử dụng.",
        ],
    },
];

export function MediaRightsPage() {
    return (
        <div className="min-h-screen bg-background text-text-primary">
            <header className="border-b border-hairline bg-surface">
                <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-5 py-4 sm:px-8">
                    <a href="/" aria-label="Trang chủ Viraldy">
                        <BrandLogo />
                    </a>
                    <a
                        href="/smart-remake"
                        className="inline-flex min-h-11 items-center gap-2 rounded-xl px-3 text-sm text-text-secondary hover:bg-surface-soft focus-visible:outline-2 focus-visible:outline-ring"
                    >
                        <ArrowLeft className="size-4" /> Về Smart Remake
                    </a>
                </div>
            </header>
            <main className="mx-auto max-w-6xl px-5 py-10 sm:px-8 sm:py-14">
                <div className="mb-10 max-w-3xl space-y-5">
                    <span className="inline-flex items-center gap-2 rounded-full bg-primary-soft px-3 py-1.5 text-xs font-medium text-primary">
                        <ShieldCheck className="size-4" /> QUYỀN TƯ LIỆU · SMART REMAKE
                    </span>
                    <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
                        Chính sách sử dụng tư liệu
                    </h1>
                    <p className="max-w-2xl text-base leading-7 text-text-secondary">
                        Tạo video cho sản phẩm của bạn với quyền sử dụng rõ ràng. Chính sách này
                        giải thích những gì bạn xác nhận khi đưa video và ảnh vào Smart Remake.
                    </p>
                    <p className="text-xs text-text-tertiary">
                        Cập nhật {MEDIA_RIGHTS_POLICY_DATE} · Phiên bản{" "}
                        {MEDIA_RIGHTS_POLICY_VERSION}
                    </p>
                </div>
                <div className="grid items-start gap-8 lg:grid-cols-[240px_minmax(0,1fr)] lg:gap-12">
                    <aside className="space-y-4 lg:sticky lg:top-6">
                        <p className="flex items-center gap-2 text-sm font-medium">
                            <FileText className="size-4 text-primary" /> Nội dung chính sách
                        </p>
                        <nav aria-label="Nội dung chính sách" className="space-y-1">
                            {sections.map((section) => (
                                <a
                                    key={section.id}
                                    href={`#${section.id}`}
                                    className="block rounded-xl px-3 py-2.5 text-sm leading-6 text-text-secondary hover:bg-surface hover:text-primary focus-visible:outline-2 focus-visible:outline-ring"
                                >
                                    {section.title}
                                </a>
                            ))}
                        </nav>
                    </aside>
                    <article className="min-w-0 space-y-7">
                        <div className="space-y-4 rounded-3xl border border-primary/10 bg-primary-soft p-5 sm:p-7">
                            <h2 className="text-lg font-semibold">
                                Ba điều cần biết trước khi tạo
                            </h2>
                            <ul className="space-y-3">
                                {MEDIA_RIGHTS_POLICY_SUMMARY.map((item) => (
                                    <li key={item} className="flex gap-3 text-sm leading-6">
                                        <Check className="mt-1 size-4 shrink-0 text-primary" />
                                        <span>{item}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                        {sections.map((section) => (
                            <section
                                key={section.id}
                                id={section.id}
                                className="scroll-mt-6 space-y-4 rounded-3xl bg-surface p-5 sm:p-7"
                                aria-labelledby={`${section.id}-title`}
                            >
                                <h2 id={`${section.id}-title`} className="text-lg font-semibold">
                                    {section.title}
                                </h2>
                                {section.paragraphs.map((paragraph) => (
                                    <p
                                        key={paragraph}
                                        className="text-sm leading-7 text-text-secondary"
                                    >
                                        {paragraph}
                                    </p>
                                ))}
                            </section>
                        ))}
                        <section className="space-y-4 rounded-3xl border border-hairline bg-surface p-5 sm:p-7">
                            <h2 className="text-lg font-semibold">Nội dung bạn xác nhận</h2>
                            <blockquote className="border-l-2 border-primary pl-4 text-sm leading-7 text-text-secondary">
                                {MEDIA_RIGHTS_ATTESTATION_TEXT}
                            </blockquote>
                            <p className="text-xs leading-6 text-text-tertiary">
                                Việc xác nhận được thực hiện trong dự án Smart Remake. Đọc trang
                                chính sách này không tự ghi nhận sự đồng ý của bạn.
                            </p>
                            <a
                                href="/smart-remake"
                                className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-primary px-4 text-sm font-medium text-white hover:bg-primary-active focus-visible:outline-2 focus-visible:outline-ring"
                            >
                                Mở Smart Remake <ArrowUpRight className="size-4" />
                            </a>
                        </section>
                    </article>
                </div>
            </main>
        </div>
    );
}
