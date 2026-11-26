// @vitest-environment jsdom
import { createElement } from "react";
import { readFileSync } from "node:fs";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Dialog, DialogContent } from "@/shared/ui/dialog";
import { RemakeAnalysisLoading } from "./remake-analysis-loading";

afterEach(() => {
    cleanup();
    vi.useRealTimers();
});

function loading(props: Parameters<typeof RemakeAnalysisLoading>[0]) {
    return createElement(
        Dialog,
        { open: true },
        createElement(DialogContent, null, createElement(RemakeAnalysisLoading, props)),
    );
}

describe("analysis waiting experience", () => {
    it("distinguishes preparation from analysis without inventing progress", () => {
        const { rerender } = render(loading({ action: "analyze" }));
        expect(screen.getByRole("heading", { name: "Đang chuẩn bị phân tích" })).toBeTruthy();
        rerender(loading({ action: "analyze", phase: "analyzing" }));
        expect(screen.getByRole("heading", { name: "Đang đọc video mẫu" })).toBeTruthy();
        expect(screen.getByRole("status").textContent).toContain(
            "Bạn sẽ duyệt kịch bản trước khi tạo video.",
        );
        expect(screen.queryByRole("progressbar")).toBeNull();
        expect(document.body.textContent).not.toMatch(/\d+\s*%|hoàn tất|đã phân tích/i);
    });

    it("explains what the AI studies and keeps the selected product visible", () => {
        render(
            loading({
                action: "analyze",
                phase: "analyzing",
                productUrl: "blob:selected-product",
                durationSeconds: 16,
            }),
        );
        expect(screen.getByText("Góc quay")).toBeTruthy();
        expect(screen.getByText("Hành động")).toBeTruthy();
        expect(screen.getByText("Nhịp dựng")).toBeTruthy();
        expect(screen.getByText(/16 giây tư liệu/)).toBeTruthy();
        expect(screen.getByRole("img", { name: "Sản phẩm của bạn" }).getAttribute("src")).toBe(
            "blob:selected-product",
        );
    });

    it("names a script update and works without a product preview or duration", () => {
        render(loading({ action: "reanalyze", phase: "analyzing" }));
        expect(screen.getByRole("heading", { name: "Đang cập nhật kịch bản" })).toBeTruthy();
        expect(screen.queryByRole("img", { name: "Sản phẩm của bạn" })).toBeNull();
        expect(document.body.textContent).not.toMatch(/undefined|NaN|0 giây tư liệu/);
        expect(screen.getByRole("status")).toBeTruthy();
    });
});

const analysisProgress = {
    schemaVersion: 1 as const,
    operationId: "compile-operation",
    requestKey: "compile-request",
    status: "running" as const,
    stage: "resolving_scenes" as const,
    startedAt: "2026-11-26T09:00:00.000Z",
    updatedAt: "2026-11-26T09:00:20.000Z",
    sourceDurationSeconds: 30,
    sceneCount: 12,
    scenes: Array.from({ length: 12 }, (_, index) => ({
        index,
        startSecond: index * 2.5,
        endSecond: (index + 1) * 2.5,
        action: `Đặt chiếc hộp tại vị trí ${index + 1}`,
        camera: "Góc cận · máy quay cố định",
        transition: "Cắt sang cảnh kế tiếp",
    })),
};

describe("real analysis checkpoints", () => {
    it("renders inline without a dialog context and respects reduced motion", () => {
        render(createElement(RemakeAnalysisLoading, { action: "analyze", presentation: "inline" }));
        expect(screen.getByRole("heading", { name: "Đang chuẩn bị phân tích" }).tagName).toBe("H2");
        expect(screen.queryByRole("dialog")).toBeNull();
        const css = readFileSync(
            "src/features/smart-remake/components/remake-analysis-loading.css",
            "utf8",
        );
        expect(css).toContain("prefers-reduced-motion: reduce");
        expect(css).toContain("animation: none !important");
    });

    it("keeps actual references available while recognition is still unknown", () => {
        render(
            loading({
                action: "analyze",
                phase: "analyzing",
                sourceUrl: "blob:source",
                productUrl: "blob:product",
            }),
        );
        expect(screen.getByLabelText("Video mẫu đang phân tích").getAttribute("src")).toBe(
            "blob:source",
        );
        expect(screen.getByLabelText("Video mẫu đang phân tích").hasAttribute("controls")).toBe(
            true,
        );
        expect(screen.getByRole("img", { name: "Sản phẩm của bạn" }).getAttribute("src")).toBe(
            "blob:product",
        );
        expect(screen.queryByText(/Đã nhận diện \d+ cảnh/)).toBeNull();
        expect(screen.queryByText("Đã nhận diện sản phẩm")).toBeNull();
        expect(screen.queryByRole("progressbar")).toBeNull();
    });

    it("reveals received scene evidence without inventing a product result", () => {
        const { rerender } = render(loading({ action: "analyze", phase: "analyzing" }));
        rerender(loading({ action: "analyze", phase: "analyzing", progress: analysisProgress }));
        expect(screen.getByText("Đã nhận diện 12 cảnh")).toBeTruthy();
        expect(screen.getByText("Đặt chiếc hộp tại vị trí 12")).toBeTruthy();
        expect(screen.getByText("27,5–30 giây nguồn")).toBeTruthy();
        expect(screen.getAllByText("Góc cận · máy quay cố định")).toHaveLength(12);
        expect(screen.getByText("Đang đối chiếu hành động và điểm chuyển cảnh")).toBeTruthy();
        expect(screen.queryByText("Đã nhận diện sản phẩm")).toBeNull();
    });

    it("shows product facts only after a real checkpoint includes them", () => {
        render(
            loading({
                action: "reanalyze",
                phase: "analyzing",
                progress: {
                    ...analysisProgress,
                    stage: "building_storyboard",
                    product: {
                        name: "Bình giữ nhiệt hồng",
                        details: ["Nắp trong suốt", "Tay cầm trắng"],
                    },
                },
            }),
        );
        expect(
            screen.getByRole("heading", { name: "Đang soạn kịch bản cho sản phẩm" }),
        ).toBeTruthy();
        expect(screen.getByText("Đã nhận diện sản phẩm")).toBeTruthy();
        expect(screen.getByText("Bình giữ nhiệt hồng")).toBeTruthy();
        expect(screen.getByText("Nắp trong suốt")).toBeTruthy();
        expect(screen.getByText("Tay cầm trắng")).toBeTruthy();
    });

    it("distinguishes the full scene count from the bounded preview", () => {
        render(loading({ action: "analyze", progress: { ...analysisProgress, sceneCount: 80 } }));
        expect(screen.getByText("Đã nhận diện 80 cảnh")).toBeTruthy();
        expect(screen.getByText("Hiện 12 trong 80 cảnh")).toBeTruthy();
        expect(screen.getAllByText(/Đặt chiếc hộp tại vị trí/)).toHaveLength(12);
    });

    it("counts elapsed time without advancing recognition and offers read-only status checking", () => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date("2026-11-26T09:00:00.000Z"));
        const check = vi.fn();
        render(
            loading({
                action: "analyze",
                phase: "analyzing",
                startedAt: Date.now(),
                onCheckStatus: check,
            }),
        );
        expect(screen.queryByRole("button", { name: "Kiểm tra trạng thái" })).toBeNull();
        act(() => vi.advanceTimersByTime(65_000));
        expect(screen.getByLabelText("Thời gian đã chờ").textContent).toContain("1:05");
        expect(screen.queryByText(/Đã nhận diện \d+ cảnh/)).toBeNull();
        fireEvent.click(screen.getByRole("button", { name: "Kiểm tra trạng thái" }));
        expect(check).toHaveBeenCalledTimes(1);
        expect(screen.getByText(/không gửi lại yêu cầu AI/)).toBeTruthy();
    });

    it("describes a long media preparation without claiming AI is already processing", () => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date("2026-11-26T09:00:00.000Z"));
        render(loading({ action: "analyze", phase: "preparing", startedAt: Date.now() }));
        act(() => vi.advanceTimersByTime(45_000));
        expect(
            screen.getByText(
                "Đang tải và kiểm tra tư liệu. Thời gian chờ phụ thuộc dung lượng và kết nối.",
            ),
        ).toBeTruthy();
        expect(screen.queryByRole("button", { name: "Kiểm tra trạng thái" })).toBeNull();
        expect(screen.queryByText(/AI có thể cần thêm thời gian|Đang tìm cách quay/)).toBeNull();
    });

    it("preserves received results when status updates fail", () => {
        render(
            loading({
                action: "analyze",
                progress: analysisProgress,
                statusError: "Chưa lấy được cập nhật mới.",
                onCheckStatus: vi.fn(),
                checkingStatus: true,
            }),
        );
        expect(screen.getByRole("alert").textContent).toContain("Chưa lấy được cập nhật mới.");
        expect(screen.getByText("Đặt chiếc hộp tại vị trí 1")).toBeTruthy();
        expect(
            (screen.getByRole("button", { name: "Đang kiểm tra…" }) as HTMLButtonElement).disabled,
        ).toBe(true);
    });

    it.each([
        ["validating_source", "Đang kiểm tra tư liệu"],
        ["analyzing_source", "Đang đọc cảnh, hành động và nhịp quay"],
        ["identifying_product", "Đang nhận diện sản phẩm từ ảnh chính"],
        ["completed", "Kịch bản đã sẵn sàng"],
        ["failed", "Chưa hoàn tất phân tích"],
    ] as const)("names the server's %s stage", (stage, title) => {
        render(loading({ action: "analyze", progress: { ...analysisProgress, stage } }));
        expect(screen.getByRole("heading", { name: title })).toBeTruthy();
    });

    it("keeps failed results visible and makes checking available immediately", () => {
        render(
            loading({
                action: "analyze",
                startedAt: Date.now(),
                progress: {
                    ...analysisProgress,
                    status: "failed",
                    stage: "failed",
                    product: { name: "Bình hồng", details: [] },
                },
                onCheckStatus: vi.fn(),
            }),
        );
        expect(screen.getByText("Đặt chiếc hộp tại vị trí 12")).toBeTruthy();
        expect(screen.getByRole("button", { name: "Kiểm tra trạng thái" })).toBeTruthy();
        expect(screen.getByText(/Kết quả đã nhận vẫn được giữ/)).toBeTruthy();
    });

    it("describes a completed checkpoint as ready rather than still waiting for AI", () => {
        render(
            loading({
                action: "analyze",
                progress: { ...analysisProgress, status: "completed", stage: "completed" },
            }),
        );
        expect(
            screen.getByText("Phân tích đã xong. Đang lấy kịch bản đã lưu để bạn xem."),
        ).toBeTruthy();
        expect(screen.queryByText(/AI có thể cần thêm thời gian/)).toBeNull();
    });

    it("does not show invalid media duration or fabricate unavailable scene details", () => {
        render(
            loading({
                action: "analyze",
                durationSeconds: NaN,
                progress: {
                    ...analysisProgress,
                    sourceDurationSeconds: undefined,
                    scenes: [
                        {
                            index: 0,
                            startSecond: 0,
                            endSecond: 1.3333333333,
                            action: "Đặt bình lên bàn",
                        },
                    ],
                    sceneCount: 1,
                },
            }),
        );
        expect(screen.getByText("0–1,33 giây nguồn")).toBeTruthy();
        expect(screen.getByText("Đặt bình lên bàn")).toBeTruthy();
        expect(document.body.textContent).not.toContain("NaN");
        expect(screen.queryByText("Góc cận · máy quay cố định")).toBeNull();
    });

    it("announces checkpoint updates but keeps the clock out of the live region", () => {
        const { rerender } = render(loading({ action: "analyze" }));
        const title = screen.getByRole("heading", { name: "Đang chuẩn bị phân tích" });
        expect(document.activeElement).toBe(title);
        rerender(loading({ action: "analyze", progress: analysisProgress }));
        expect(document.activeElement).toBe(title);
        expect(
            screen.getByLabelText("Thời gian đã chờ").closest('[aria-live="polite"]'),
        ).toBeNull();
        expect(screen.getByRole("status", { name: "Tiến trình phân tích" }).textContent).toContain(
            "12 cảnh",
        );
    });
});

describe("early video summary", () => {
    const quickSummary = {
        status: "completed" as const,
        summary: "Video giới thiệu chiếc bình bằng thao tác đặt, cầm và mở nắp.",
        observations: [
            { label: "Cách thể hiện", detail: "Cận sản phẩm trên bàn, ánh sáng tự nhiên." },
        ],
    };
    const waitingProgress = {
        ...analysisProgress,
        stage: "analyzing_source" as const,
        scenes: [],
        sceneCount: undefined,
    };

    it("does not fabricate a quick result for older or absent progress", () => {
        render(loading({ action: "analyze", phase: "analyzing", progress: waitingProgress }));
        expect(screen.queryByRole("region", { name: "Tóm tắt nhanh từ video" })).toBeNull();
    });

    it("shows a real pending summary without claiming a scene count or product recognition", () => {
        render(
            loading({
                action: "analyze",
                progress: { ...waitingProgress, quickSummary: { status: "pending" } },
            }),
        );
        expect(screen.getByRole("region", { name: "Tóm tắt nhanh từ video" })).toBeTruthy();
        expect(screen.getByText("AI đang đọc nhanh nội dung video.")).toBeTruthy();
        expect(screen.queryByText(/Đã nhận diện \d+ cảnh/)).toBeNull();
        expect(screen.queryByText("Đã nhận diện sản phẩm")).toBeNull();
    });

    it("marks returned observations as preliminary and renders all content as plain text", () => {
        const summary = '<img src="x" onerror="alert(1)">';
        const detail = '<a href="javascript:alert(1)">Sản phẩm</a>';
        const { container } = render(
            loading({
                action: "analyze",
                progress: {
                    ...waitingProgress,
                    quickSummary: {
                        status: "completed",
                        summary,
                        observations: [{ label: "Điều thấy được", detail }],
                    },
                },
            }),
        );
        expect(screen.getByText(summary)).toBeTruthy();
        expect(screen.getByText(detail)).toBeTruthy();
        expect(
            screen.getByText("Nhận xét sơ bộ; phân tích chi tiết sẽ xác nhận từng cảnh."),
        ).toBeTruthy();
        expect(container.querySelector('img[src="x"]')).toBeNull();
        expect(document.querySelector('a[href^="javascript:"]')).toBeNull();
        expect(screen.queryByText("Đã nhận diện sản phẩm")).toBeNull();
    });

    it("keeps an unavailable preview nonblocking without offering a paid retry", () => {
        render(
            loading({
                action: "analyze",
                startedAt: Date.now(),
                progress: { ...waitingProgress, quickSummary: { status: "unavailable" } },
            }),
        );
        expect(screen.getByText("Chưa nhận được tóm tắt nhanh.")).toBeTruthy();
        expect(
            screen.getByText("Lượt phân tích chính chưa có kết quả đủ để hiển thị."),
        ).toBeTruthy();
        expect(screen.queryByRole("button", { name: /Thử lại|Tạo lại|Gửi lại/ })).toBeNull();
        expect(
            screen.getByRole("heading", { name: "Đang đọc cảnh, hành động và nhịp quay" }),
        ).toBeTruthy();
    });

    it("preserves the preliminary preview alongside later detailed scenes", () => {
        const { rerender } = render(
            loading({ action: "analyze", progress: { ...waitingProgress, quickSummary } }),
        );
        expect(screen.getByText(quickSummary.summary)).toBeTruthy();
        rerender(loading({ action: "analyze", progress: { ...analysisProgress, quickSummary } }));
        expect(screen.getByText(quickSummary.summary)).toBeTruthy();
        expect(screen.getByText("Cận sản phẩm trên bàn, ánh sáng tự nhiên.")).toBeTruthy();
        expect(screen.getByText("Đã nhận diện 12 cảnh")).toBeTruthy();
        expect(screen.getByText("Đặt chiếc hộp tại vị trí 12")).toBeTruthy();
    });

    it("announces a received summary without moving keyboard focus or announcing clock ticks", () => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date("2026-11-26T09:00:00.000Z"));
        const props = {
            action: "analyze" as const,
            productUrl: "blob:product",
            startedAt: Date.now(),
        };
        const { rerender } = render(
            loading({
                ...props,
                progress: { ...waitingProgress, quickSummary: { status: "pending" } },
            }),
        );
        const preview = screen.getByRole("button", { name: "Phóng to ảnh sản phẩm" });
        act(() => preview.focus());
        rerender(loading({ ...props, progress: { ...waitingProgress, quickSummary } }));
        expect(document.activeElement).toBe(preview);
        const live = screen.getByRole("status", { name: "Tiến trình phân tích" });
        expect(live.textContent).toContain("Đã có tóm tắt nhanh, nhận xét sơ bộ.");
        const announcement = live.textContent;
        act(() => vi.advanceTimersByTime(2_000));
        expect(live.textContent).toBe(announcement);
        expect(document.activeElement).toBe(preview);
    });

    it("does not claim detailed work is continuing after a failed analysis", () => {
        render(
            loading({
                action: "analyze",
                progress: {
                    ...waitingProgress,
                    status: "failed",
                    stage: "failed",
                    quickSummary: { status: "unavailable" },
                },
            }),
        );
        expect(screen.queryByText("Phân tích chi tiết vẫn đang tiếp tục.")).toBeNull();
        expect(
            screen.getByText(
                "Tóm tắt nhanh chưa có dữ liệu. Xem trạng thái phân tích để biết bước tiếp theo.",
            ),
        ).toBeTruthy();
    });
});

describe("partial main analysis observations", () => {
    const observations = [
        { label: "Hành động", detail: "Cầm bình, xoay nắp rồi đưa lên miệng." },
        { label: "Cách quay", detail: "Máy quay cố định, góc ngang và cận sản phẩm." },
    ];
    const partial = {
        ...analysisProgress,
        scenes: [],
        sceneCount: undefined,
        preliminaryObservations: observations,
        quickSummary: { status: "unavailable" as const, reason: "timeout" as const },
    };

    it("reveals received main observations while scene timing is still unresolved", () => {
        render(loading({ action: "analyze", progress: partial }));
        expect(screen.getByRole("heading", { name: "AI đã đọc được" })).toBeTruthy();
        expect(screen.getByText(observations[0].detail)).toBeTruthy();
        expect(screen.getByText(observations[1].detail)).toBeTruthy();
        expect(screen.getByText("Nhận định sơ bộ; đang đối chiếu mốc cảnh.")).toBeTruthy();
        expect(
            screen.queryByText("Thông tin từng cảnh sẽ xuất hiện khi AI trả kết quả."),
        ).toBeNull();
        expect(screen.queryByText(/Đã nhận diện \d+ cảnh/)).toBeNull();
        expect(screen.queryByText(/giây nguồn/)).toBeNull();
        expect(screen.getByText("Chưa nhận được tóm tắt nhanh.")).toBeTruthy();
        expect(
            screen.getByText("Lượt đọc nhanh chưa trả kết quả trong thời gian chờ."),
        ).toBeTruthy();
        expect(screen.queryByRole("button", { name: /Thử lại|Tạo lại|Gửi lại/ })).toBeNull();
    });

    it("retains observed facts after failure without claiming more analysis is running", () => {
        render(
            loading({
                action: "analyze",
                progress: { ...partial, status: "failed", stage: "failed" },
                onCheckStatus: vi.fn(),
            }),
        );
        expect(screen.getByText(observations[0].detail)).toBeTruthy();
        expect(
            screen.getByText("Nhận định sơ bộ đã nhận; mốc cảnh chưa được xác nhận."),
        ).toBeTruthy();
        expect(screen.getByRole("button", { name: "Kiểm tra trạng thái" })).toBeTruthy();
        expect(
            screen.queryByText(/đang đối chiếu mốc cảnh|AI đang đọc nhanh|vẫn đang tiếp tục/),
        ).toBeNull();
    });

    it("does not leave a legacy pending quick label spinning after a failed result", () => {
        render(
            loading({
                action: "analyze",
                progress: {
                    ...partial,
                    status: "failed",
                    stage: "failed",
                    quickSummary: { status: "pending" },
                },
            }),
        );
        expect(screen.getByText(observations[0].detail)).toBeTruthy();
        expect(screen.queryByText("AI đang đọc nhanh nội dung video.")).toBeNull();
        expect(screen.getByText("Chưa nhận được tóm tắt nhanh.")).toBeTruthy();
    });

    it.each([
        ["invalid_response", "Kết quả đọc nhanh chưa đọc được đầy đủ."],
        ["unavailable", "Chưa lấy được kết quả đọc nhanh."],
    ] as const)(
        "explains the sanitized quick failure %s without a retry action",
        (reason, message) => {
            render(
                loading({
                    action: "analyze",
                    progress: { ...partial, quickSummary: { status: "unavailable", reason } },
                }),
            );
            expect(screen.getByText(message)).toBeTruthy();
            expect(screen.getByText(observations[0].detail)).toBeTruthy();
            expect(screen.queryByRole("button", { name: /Thử lại|Tạo lại|Gửi lại/ })).toBeNull();
        },
    );

    it("uses plain text for partial observations and announces them without moving focus", () => {
        const { rerender, container } = render(loading({ action: "analyze" }));
        const heading = screen.getByRole("heading", { name: "Đang chuẩn bị phân tích" });
        const detail = '<img src="x" onerror="alert(1)">';
        rerender(
            loading({
                action: "analyze",
                progress: { ...partial, preliminaryObservations: [{ label: "Quan sát", detail }] },
            }),
        );
        expect(screen.getByText(detail)).toBeTruthy();
        expect(container.querySelector('img[src="x"]')).toBeNull();
        expect(screen.getByRole("status", { name: "Tiến trình phân tích" }).textContent).toContain(
            "Đã có nhận định sơ bộ từ lượt phân tích chính.",
        );
        expect(document.activeElement).toBe(heading);
    });

    it("replaces preliminary cards with verified scene windows once available", () => {
        const { rerender } = render(loading({ action: "analyze", progress: partial }));
        rerender(
            loading({
                action: "analyze",
                progress: { ...analysisProgress, preliminaryObservations: observations },
            }),
        );
        expect(screen.getByText("Đã nhận diện 12 cảnh")).toBeTruthy();
        expect(screen.getByText("Đặt chiếc hộp tại vị trí 12")).toBeTruthy();
        expect(screen.queryByText(observations[0].detail)).toBeNull();
        expect(screen.queryByRole("heading", { name: "AI đã đọc được" })).toBeNull();
    });

    it("freezes the elapsed clock at the received terminal checkpoint", () => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date("2026-11-26T09:10:00.000Z"));
        render(
            loading({
                action: "analyze",
                progress: {
                    ...partial,
                    status: "failed",
                    stage: "failed",
                    startedAt: "2026-11-26T09:00:00.000Z",
                    updatedAt: "2026-11-26T09:01:13.000Z",
                },
            }),
        );
        const clock = screen.getByLabelText("Thời gian đã chờ");
        expect(clock.textContent).toContain("1:13");
        expect(clock.textContent).not.toContain("Đã chờ");
        act(() => vi.advanceTimersByTime(60_000));
        expect(clock.textContent).toContain("1:13");
    });
});
