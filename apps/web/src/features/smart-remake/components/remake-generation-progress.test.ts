// @vitest-environment jsdom
import { createElement } from "react";
import { readFileSync } from "node:fs";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { SmartRemakeProject } from "@/shared/api/smart-remake";
import { RemakeGenerationProgress } from "./remake-generation-progress";

afterEach(cleanup);
const project = (status: "running" | "failed" = "running") =>
    ({
        id: "p",
        targetDuration: 16,
        productImageUrl: "/product.webp",
        sourceVideoUrl: "/source.mp4",
        scenes: [],
        sourceSceneMap: { scenes: [{ id: "source", thumbnailUrl: "/source.webp" }] },
        renderPlan: {
            fps: 24,
            units: [
                { id: "unit-a", sourceSceneId: "source" },
                { id: "unit-b", sourceSceneId: "source" },
            ],
            groups: [
                { id: "a", renderUnitIds: ["unit-a"], targetDurationFrames: 192 },
                { id: "b", renderUnitIds: ["unit-b"], targetDurationFrames: 192 },
            ],
        },
        generationProgress: {
            operationId: "op",
            status,
            startedAt: "2026-11-26T10:00:00Z",
            updatedAt: "2026-11-26T10:01:10Z",
            groups: [
                {
                    groupId: "a",
                    stage: status === "failed" ? "blocked" : "preparing_image",
                    videoSubmitted: false,
                    conditioningImageUrl: "/opening.webp",
                    errorCode:
                        status === "failed" ? "SMART_REMAKE_CONDITIONING_BLOCKED" : undefined,
                    inspectionReportId: "report",
                },
                { groupId: "b", stage: "queued", videoSubmitted: false },
            ],
        },
    }) as unknown as SmartRemakeProject;

it("shows exactly two six-second windows for a twelve-second Wan run", () => {
    const value = project();
    value.targetDuration = 12;
    value.renderPlan!.groups = value.renderPlan!.groups!.map((group) => ({
        ...group,
        rawDurationFrames: 144,
        targetDurationFrames: 144,
    }));
    render(createElement(RemakeGenerationProgress, { project: value }));
    expect(screen.getByText("2 lượt dự kiến")).toBeTruthy();
    expect(screen.getByText("0–6 giây")).toBeTruthy();
    expect(screen.getByText("6–12 giây")).toBeTruthy();
    expect(screen.queryByText("8–16 giây")).toBeNull();
});

it("shows two planned provider windows and real zero submissions while labeling all references as images", () => {
    render(createElement(RemakeGenerationProgress, { project: project() }));
    expect(screen.getByText("2 lượt dự kiến")).toBeTruthy();
    expect(screen.getByText("0 lượt đã gửi KIE")).toBeTruthy();
    expect(screen.getByText("0–8 giây")).toBeTruthy();
    expect(screen.getByText("8–16 giây")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Đang tạo ảnh mở đầu" })).toBeTruthy();
    expect(screen.getByText("Chưa bắt đầu")).toBeTruthy();
    expect(screen.getByText("Ảnh mở đầu đã tạo · chưa phải video")).toBeTruthy();
    expect(screen.queryByRole("progressbar")).toBeNull();
    expect(document.body.textContent).not.toMatch(/\d+\s*%|sắp xong|ước tính còn|video đã tạo/);
});
it("stops animation on an insufficient-evidence block and links the real inspection only on click", () => {
    const onViewInspection = vi.fn();
    render(
        createElement(RemakeGenerationProgress, { project: project("failed"), onViewInspection }),
    );
    expect(screen.getByText("Chưa đủ bằng chứng kiểm tra ảnh")).toBeTruthy();
    expect(document.querySelector('[data-active="true"]')).toBeNull();
    expect(onViewInspection).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Xem kết quả kiểm tra ảnh" }));
    expect(onViewInspection).toHaveBeenCalledWith("report");
    expect(document.body.textContent).not.toContain("Ảnh sai");
    expect(screen.getByText("Chưa bắt đầu")).toBeTruthy();
});
it("keeps legacy counts unknown and checking status explicit without submitting anything", () => {
    const current = project();
    const { generationProgress: _omitted, ...legacy } = current;
    const onCheckStatus = vi.fn();
    render(createElement(RemakeGenerationProgress, { project: legacy, onCheckStatus }));
    expect(screen.getByText("Chưa xác nhận số lượt đã gửi KIE")).toBeTruthy();
    expect(screen.queryByText("0 lượt đã gửi KIE")).toBeNull();
    expect(onCheckStatus).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Kiểm tra trạng thái" }));
    expect(onCheckStatus).toHaveBeenCalledTimes(1);
});
it("uses plain text for IDs and supports reduced motion without fake progress timing", () => {
    const current = project();
    current.sourceSceneMap!.scenes[0].id = "<script>bad()</script>";
    render(createElement(RemakeGenerationProgress, { project: current }));
    expect(document.querySelector("script")).toBeNull();
    const css = readFileSync(
        "src/features/smart-remake/components/remake-generation-progress.css",
        "utf8",
    );
    expect(css).toContain("prefers-reduced-motion: reduce");
    expect(css).toContain('data-active="true"');
});
it("names the actual running phase and exposes each completed reference while the next image is still pending", () => {
    const current = project();
    current.renderPlan!.groups![0].renderUnitIds = ["unit-a", "unit-b"];
    current.generationProgress!.groups[0].conditioningImages = [
        { renderUnitId: "unit-a", url: "/first.webp" },
        { renderUnitId: "unit-b", url: "/second.webp" },
    ];
    render(createElement(RemakeGenerationProgress, { project: current }));
    expect(screen.getByRole("heading", { name: "Đang tạo ảnh mở đầu" })).toBeTruthy();
    expect(
        screen
            .getAllByRole("img", { name: "Ảnh tham chiếu đã tạo cho cảnh 1" })
            .map((image) => image.getAttribute("src")),
    ).toEqual(["/first.webp", "/second.webp"]);

    expect(screen.getByText("2 ảnh đã tạo")).toBeTruthy();
});
it("shows a retained real clip as soon as available while the other window is still pending", () => {
    const current = project();
    current.generationProgress!.groups[0] = {
        ...current.generationProgress!.groups[0],
        stage: "completed",
        videoSubmitted: true,
        videoUrl: "/owned-clip.mp4",
    };
    current.generationProgress!.groups[1] = {
        ...current.generationProgress!.groups[1],
        stage: "generating",
        videoSubmitted: true,
    };
    render(createElement(RemakeGenerationProgress, { project: current }));
    expect(screen.getByRole("heading", { name: "KIE đang tạo clip" })).toBeTruthy();
    const video = screen.getByLabelText("Clip 1 đã tạo") as HTMLVideoElement;
    expect(video.getAttribute("src")).toBe("/owned-clip.mp4");
    expect(video.controls).toBe(true);
    expect(screen.getByText("2 lượt đã gửi KIE")).toBeTruthy();
});
it("does not describe a video/provider failure as an image verification problem", () => {
    const current = project("failed");
    current.generationProgress!.groups[0].errorCode = "KIE_TASK_FAILED";
    render(createElement(RemakeGenerationProgress, { project: current }));
    expect(screen.getByRole("heading", { name: "Cần xử lý trước khi tạo tiếp" })).toBeTruthy();
    expect(screen.queryByText("Cần kiểm tra ảnh trước khi tạo video")).toBeNull();
});
it("distinguishes two reference images from different render fragments of the same source scene", () => {
    const current = project();
    current.renderPlan!.groups![0].renderUnitIds = ["unit-a", "unit-b"];
    current.generationProgress!.groups[0].conditioningImages = [
        { renderUnitId: "unit-a", url: "/first.webp" },
        { renderUnitId: "unit-b", url: "/last.webp" },
    ];
    render(createElement(RemakeGenerationProgress, { project: current }));
    expect(screen.getByRole("button", { name: "Phóng to ảnh tham chiếu 1 · cảnh 1" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Phóng to ảnh tham chiếu 2 · cảnh 1" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Phóng to ảnh tham chiếu 2 · cảnh 1" }));
    expect(screen.getByRole("heading", { name: "Ảnh tham chiếu 2 · cảnh 1" })).toBeTruthy();
});
it("keeps script navigation secondary and explicit without generating anything", () => {
    const onViewScript = vi.fn();
    render(createElement(RemakeGenerationProgress, { project: project("failed"), onViewScript }));
    expect(onViewScript).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Xem kịch bản" }));
    expect(onViewScript).toHaveBeenCalledTimes(1);
});

it("shows the KIE failure and retained reason on the affected clip only", () => {
    const current = project("failed");
    Object.assign(current.generationProgress!.groups[0], {
        errorCode: "KIE_TASK_FAILED",
        videoSubmitted: true,
        providerError: {
            providerCode: "500",
            providerMessage: "Internal Error, Please try again later.",
        },
        providerTaskId: "kie-task-one",
    });
    render(createElement(RemakeGenerationProgress, { project: current }));
    const alert = screen.getByRole("alert");
    expect(alert.textContent).toContain("Lỗi từ nhà cung cấp kie.ai");
    expect(alert.textContent).toContain("lỗi nội bộ");
    expect(alert.textContent).toContain("Internal Error, Please try again later.");
    expect(alert.textContent).toContain("kie-task-one");
    expect(alert.closest("article")?.textContent).toContain("Clip 1");
    expect(screen.queryByText("Cần kiểm tra ảnh trước khi tạo video")).toBeNull();
    expect(document.body.textContent).not.toMatch(/hoàn tiền|prompt quá dài/);
});

it("keeps a KIE timeout uncertain and offers a status check without resubmitting", () => {
    const current = project("failed");
    Object.assign(current.generationProgress!.groups[0], {
        stage: "unknown",
        errorCode: "KIE_POLL_TIMEOUT",
        videoSubmitted: true,
        providerTaskId: "kie-uncertain",
    });
    const onCheckStatus = vi.fn();
    render(createElement(RemakeGenerationProgress, { project: current, onCheckStatus }));
    expect(screen.getByRole("alert").textContent).toContain("Chưa nhận được kết quả từ kie.ai");
    expect(screen.getByRole("alert").textContent).toContain("Chưa xác định được kết quả");
    expect(screen.getByRole("alert").textContent).not.toMatch(/không tạo được|từ chối/);
    expect(onCheckStatus).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Kiểm tra trạng thái" }));
    expect(onCheckStatus).toHaveBeenCalledTimes(1);
});

it("escapes the provider response and keeps legacy KIE failures readable without details", () => {
    const current = project("failed");
    Object.assign(current.generationProgress!.groups[0], {
        errorCode: "KIE_TASK_FAILED",
        providerError: { providerMessage: "<img src=x onerror=alert(1)>" },
    });
    const view = render(createElement(RemakeGenerationProgress, { project: current }));
    expect(screen.getByText("<img src=x onerror=alert(1)>")).toBeTruthy();
    expect(document.querySelector("[onerror]")).toBeNull();
    const legacy = project("failed");
    legacy.generationProgress!.groups[0].errorCode = "KIE_TASK_FAILED";
    view.rerender(createElement(RemakeGenerationProgress, { project: legacy }));
    expect(screen.getByRole("alert").textContent).toContain("Lỗi từ nhà cung cấp kie.ai");
    expect(screen.queryByText("Chi tiết lỗi KIE")).toBeNull();
});

it("does not attribute an OpenAI image failure to KIE", () => {
    const current = project("failed");
    current.generationProgress!.groups[0].errorCode = "OPENAI_IMAGE_RATE_LIMITED";
    render(createElement(RemakeGenerationProgress, { project: current }));
    expect(screen.queryByText("Chi tiết lỗi KIE")).toBeNull();
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.getAllByText("Chưa gửi lượt tạo clip tới KIE")).toHaveLength(2);
});

it("names kie.ai when a submit returned an error without a task receipt", () => {
    const current = project("failed");
    Object.assign(current.generationProgress!.groups[0], {
        stage: "unknown",
        errorCode: "SMART_REMAKE_SUBMISSION_UNRESOLVED",
        videoSubmitted: null,
        providerError: { providerCode: 500, providerMessage: "Server exception" },
    });
    render(createElement(RemakeGenerationProgress, { project: current }));
    const alert = screen.getByRole("alert");
    expect(alert.textContent).toContain("Chưa nhận được kết quả từ kie.ai");
    expect(alert.textContent).toContain("Server exception");
    expect(alert.textContent).not.toContain("Lỗi từ nhà cung cấp");
    expect(screen.getByText("Chưa xác nhận số lượt đã gửi KIE")).toBeTruthy();
});
