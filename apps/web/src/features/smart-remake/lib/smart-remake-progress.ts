export const SMART_REMAKE_ANALYSIS_STEPS = [
    {
        label: "Đang xem nhịp video mẫu",
        detail: "Tìm phần mở đầu, điểm nhấn và cách câu chuyện được kể.",
    },
    {
        label: "Đang chọn những khoảnh khắc đáng nhớ",
        detail: "Giữ lại cảm xúc và nhịp điệu phù hợp nhất từ video của bạn.",
    },
    {
        label: "Đang nhận diện sản phẩm",
        detail: "Ghi nhận các chi tiết để sản phẩm luôn xuất hiện nhất quán.",
    },
    {
        label: "Đang lên ý tưởng cho video mới",
        detail: "Kết hợp sản phẩm của bạn với cảm hứng từ video mẫu.",
    },
    {
        label: "Đang viết kịch bản video mới",
        detail: "Hoàn thiện từng phân đoạn để sẵn sàng cho bước tạo video.",
    },
] as const;

const SMART_REMAKE_RENDER_STEPS = [
    {
        label: "Đang chuẩn bị khung hình",
        detail: "Sắp xếp sản phẩm và bố cục cho video mới.",
    },
    {
        label: "Đang tạo cảnh quay",
        detail: "Biến từng phần của kịch bản thành các cảnh video.",
    },
    {
        label: "Đang dựng chuyển động",
        detail: "Hoàn thiện nhịp chuyển cảnh và cảm giác xem liền mạch.",
    },
    {
        label: "Đang hoàn thiện video",
        detail: "Kiểm tra những chi tiết cuối cùng trước khi gửi video cho bạn.",
    },
] as const;

export function getSmartRemakeWorkflowProgress({
    analysisStep,
    isCompiling,
    isRendering,
    renderProgress,
}: {
    analysisStep: number;
    isCompiling: boolean;
    isRendering: boolean;
    renderProgress: number;
}) {
    if (isRendering) {
        const percentage = clampPercentage(renderProgress);
        return {
            kind: "render" as const,
            steps: SMART_REMAKE_RENDER_STEPS,
            currentStep: Math.min(
                Math.floor((percentage / 100) * SMART_REMAKE_RENDER_STEPS.length),
                SMART_REMAKE_RENDER_STEPS.length - 1,
            ),
            percentage,
        };
    }

    const currentStep = Math.min(Math.max(analysisStep, 0), SMART_REMAKE_ANALYSIS_STEPS.length - 1);
    return {
        kind: isCompiling ? ("analysis" as const) : ("ready" as const),
        steps: SMART_REMAKE_ANALYSIS_STEPS,
        currentStep,
        percentage: isCompiling
            ? Math.round(((currentStep + 1) / SMART_REMAKE_ANALYSIS_STEPS.length) * 100)
            : 100,
    };
}

function clampPercentage(value: number) {
    return Math.min(100, Math.max(0, value));
}
