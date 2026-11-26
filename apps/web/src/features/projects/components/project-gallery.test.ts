// @vitest-environment jsdom

import { createElement } from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { SmartRemakeProjectVideo } from "@/shared/api/smart-remake-library";
import { ProjectGallery, type ProjectGalleryProps } from "./project-gallery";

vi.mock("@/features/smart-remake/components/remake-player", () => ({
    RemakePlayer: ({ url, poster }: { url: string; poster?: string }) =>
        createElement("video", { src: url, poster, "data-testid": "project-player" }),
}));

afterEach(cleanup);

const video: SmartRemakeProjectVideo = {
    id: "saved-project",
    projectName: "Bình giữ nhiệt",
    createdAt: "2026-11-26T10:00:00Z",
    status: "ready",
    targetDuration: 16,
    provider: "kie",
    finalVideoUrl: "https://media.example/preview.mp4",
    productImageUrl: "https://media.example/product.png",
    videos: [
        {
            id: "final",
            label: "Video hoàn chỉnh",
            kind: "final",
            url: "https://media.example/preview.mp4",
            durationSeconds: 16,
        },
    ],
};

const props: ProjectGalleryProps = {
    items: [video],
    total: 1,
    limit: 24,
    offset: 0,
    loading: false,
    refreshing: false,
    error: false,
    onRefresh: vi.fn(),
    onPageChange: vi.fn(),
};

describe("Project gallery", () => {
    it("opens a server project while its images are preparing without pretending a video exists", () => {
        render(
            createElement(ProjectGallery, {
                ...props,
                items: [
                    {
                        ...video,
                        finalVideoUrl: "",
                        videos: [],
                        status: "incomplete",
                        activity: {
                            kind: "render",
                            status: "running",
                            stage: "preparing_image",
                            plannedVideoCount: 2,
                            submittedVideoCount: 0,
                            completedImageCount: 1,
                        },
                    },
                ],
            }),
        );
        expect(screen.getByText("Đang tạo ảnh mở đầu")).toBeTruthy();
        expect(screen.getByText("1 ảnh đã tạo · 0/2 lượt KIE đã gửi")).toBeTruthy();
        expect(
            screen
                .getByRole("link", { name: `Mở dự án ${video.projectName}` })
                .getAttribute("href"),
        ).toBe("/smart-remake?projectId=saved-project");
        expect(screen.queryByTestId("project-player")).toBeNull();
        expect(screen.queryByRole("button", { name: `Xem video ${video.projectName}` })).toBeNull();
    });
    it("keeps an uncertain task distinct from a zero-submission count", () => {
        render(
            createElement(ProjectGallery, {
                ...props,
                items: [
                    {
                        ...video,
                        videos: [],
                        finalVideoUrl: "",
                        activity: {
                            kind: "render",
                            status: "running",
                            stage: "unknown",
                            needsReconciliation: true,
                            plannedVideoCount: 2,
                            submittedVideoCount: null,
                        },
                    },
                ],
            }),
        );
        expect(screen.getByText("Cần kiểm tra trạng thái")).toBeTruthy();
        expect(screen.getByText("Chưa xác nhận số lượt KIE đã gửi")).toBeTruthy();
        expect(document.body.textContent).not.toContain("0/2");
    });
    it("announces loading without claiming that the library is empty", () => {
        render(createElement(ProjectGallery, { ...props, items: [], loading: true }));

        expect(screen.getByRole("status").textContent).toContain("Đang tải video đã lưu");
        expect(screen.queryByText("Chưa có video đã lưu")).toBeNull();
    });

    it("offers retry when loading saved videos fails", () => {
        const onRefresh = vi.fn();
        render(createElement(ProjectGallery, { ...props, error: true, onRefresh }));

        expect(screen.getByRole("alert").textContent).toContain("Chưa tải được video");
        fireEvent.click(screen.getByRole("button", { name: "Thử lại" }));
        expect(onRefresh).toHaveBeenCalledOnce();
        expect(screen.queryByText(video.projectName)).toBeNull();
    });

    it("explains automatic saving when no videos have been created", () => {
        render(createElement(ProjectGallery, { ...props, items: [], total: 0 }));

        expect(screen.getByText("Chưa có dự án")).toBeTruthy();
        expect(screen.getByText(/Dự án Smart Remake sẽ xuất hiện khi bạn bắt đầu/)).toBeTruthy();
    });

    it("opens the selected video for playback and never turns preview access into a download", () => {
        render(createElement(ProjectGallery, props));

        expect(screen.getByText(video.projectName)).toBeTruthy();
        expect(screen.getByText("16 giây")).toBeTruthy();
        expect(screen.queryByRole("link", { name: /Tải video/ })).toBeNull();
        expect(screen.queryByTestId("project-player")).toBeNull();

        fireEvent.click(screen.getByRole("button", { name: `Xem video ${video.projectName}` }));
        expect(screen.getByRole("dialog")).toBeTruthy();
        expect(screen.getByTestId("project-player").getAttribute("src")).toBe(video.finalVideoUrl);
        expect(screen.getByTestId("project-player").getAttribute("poster")).toBe(
            video.productImageUrl,
        );
        expect(document.querySelector(`a[href="${video.finalVideoUrl}"]`)).toBeNull();
    });

    it("uses only an explicit server download URL", () => {
        const downloadUrl = "https://media.example/approved-export.mp4";
        render(
            createElement(ProjectGallery, {
                ...props,
                items: [{ ...video, downloadUrl }],
            }),
        );

        const download = screen.getByRole("link", { name: `Tải video ${video.projectName}` });
        expect(download.getAttribute("href")).toBe(downloadUrl);
        expect(download.getAttribute("download")).toBeTruthy();
    });

    it("keeps generated clips available before composition and plays the selected clip", () => {
        const clips: SmartRemakeProjectVideo = {
            ...video,
            finalVideoUrl: "",
            videos: [
                {
                    id: "clip-one",
                    label: "Clip 1",
                    kind: "clip",
                    url: "https://media.example/clip-one.mp4",
                    durationSeconds: 8,
                },
                {
                    id: "clip-two",
                    label: "Clip 2",
                    kind: "clip",
                    url: "https://media.example/clip-two.mp4",
                    durationSeconds: 7.5,
                },
            ],
        };
        render(createElement(ProjectGallery, { ...props, items: [clips] }));

        expect(screen.getByText("1 project đã lưu")).toBeTruthy();
        expect(screen.getByText("2 clip đã tạo")).toBeTruthy();
        expect(screen.queryByText("16 giây")).toBeNull();
        fireEvent.click(screen.getByRole("button", { name: `Xem video ${video.projectName}` }));
        expect(screen.getByTestId("project-player").getAttribute("src")).toBe(clips.videos[0].url);
        expect(screen.getByText("Chưa ghép thành video hoàn chỉnh")).toBeTruthy();

        fireEvent.click(screen.getByRole("button", { name: "Clip 2 · 7.5 giây" }));
        expect(screen.getByTestId("project-player").getAttribute("src")).toBe(clips.videos[1].url);
        expect(
            screen.getByRole("button", { name: "Clip 2 · 7.5 giây" }).getAttribute("aria-pressed"),
        ).toBe("true");
        expect(screen.queryByRole("link", { name: /Tải video/ })).toBeNull();

        fireEvent.click(screen.getByRole("button", { name: "Close" }));
        fireEvent.click(screen.getByRole("button", { name: `Xem video ${video.projectName}` }));
        expect(screen.getByTestId("project-player").getAttribute("src")).toBe(clips.videos[0].url);
    });

    it("distinguishes a finished video from its retained source clips", () => {
        render(
            createElement(ProjectGallery, {
                ...props,
                items: [
                    {
                        ...video,
                        videos: [
                            ...video.videos,
                            {
                                id: "clip",
                                label: "Clip 1",
                                kind: "clip",
                                url: "https://media.example/source-clip.mp4",
                                durationSeconds: 8,
                            },
                        ],
                    },
                ],
            }),
        );

        fireEvent.click(screen.getByRole("button", { name: `Xem video ${video.projectName}` }));
        expect(screen.getByTestId("project-player").getAttribute("src")).toBe(video.videos[0].url);
        expect(
            screen
                .getByRole("button", { name: "Video hoàn chỉnh · 16 giây" })
                .getAttribute("aria-pressed"),
        ).toBe("true");
        fireEvent.click(screen.getByRole("button", { name: "Clip 1 · 8 giây" }));
        expect(screen.getByTestId("project-player").getAttribute("src")).toBe(
            "https://media.example/source-clip.mp4",
        );
    });

    it("requests the next and previous pages without hiding saved history", () => {
        const onPageChange = vi.fn();
        render(createElement(ProjectGallery, { ...props, total: 65, offset: 24, onPageChange }));

        expect(screen.getByText("Trang 2 / 3")).toBeTruthy();
        fireEvent.click(screen.getByRole("button", { name: "Trang trước" }));
        expect(onPageChange).toHaveBeenLastCalledWith(0);
        fireEvent.click(screen.getByRole("button", { name: "Trang sau" }));
        expect(onPageChange).toHaveBeenLastCalledWith(48);
    });

    it("replaces expiring media URLs when the collection is refreshed", () => {
        const view = render(createElement(ProjectGallery, props));
        fireEvent.click(screen.getByRole("button", { name: `Xem video ${video.projectName}` }));

        const finalVideoUrl = "https://media.example/preview.mp4?signature=refreshed";
        view.rerender(
            createElement(ProjectGallery, {
                ...props,
                items: [
                    {
                        ...video,
                        finalVideoUrl,
                        videos: [{ ...video.videos[0], url: finalVideoUrl }],
                    },
                ],
            }),
        );
        expect(screen.getByTestId("project-player").getAttribute("src")).toBe(finalVideoUrl);
    });
});
