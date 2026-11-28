// @vitest-environment jsdom
import { createElement } from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import * as mediaApi from "@/shared/api/smart-remake-generated-media";
import {
    RemakeGeneratedImage,
    RemakeKiePrompt,
    RemakeGeneratedMedia,
} from "./remake-generated-media";

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
});

const image = {
    renderUnitId: "unit",
    requestHash: "a".repeat(64),
    frameRole: "opening" as const,
    url: "https://private.example.test/preview",
};
const identities = { workspaceId: "workspace", projectId: "project", operationId: "render" };

it("downloads the original using a fresh signed URL on every click", async () => {
    const download = vi
        .spyOn(mediaApi, "getSmartRemakeGeneratedImageDownload")
        .mockResolvedValueOnce({
            url: "https://private.example.test/fresh-one",
            filename: "opening.png",
        })
        .mockResolvedValueOnce({
            url: "https://private.example.test/fresh-two",
            filename: "opening.png",
        });
    const links: Array<{ url: string; filename: string }> = [];
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
        this: HTMLAnchorElement,
    ) {
        links.push({ url: this.href, filename: this.download });
    });
    render(
        createElement(RemakeGeneratedImage, { ...identities, image, ordinal: 1, sceneIndex: 1 }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Tải ảnh gốc · Ảnh đầu" }));
    await waitFor(() => expect(links).toHaveLength(1));
    fireEvent.click(screen.getByRole("button", { name: "Tải ảnh gốc · Ảnh đầu" }));
    await waitFor(() => expect(links).toHaveLength(2));
    expect(download).toHaveBeenNthCalledWith(
        1,
        "workspace",
        "project",
        "render",
        image.requestHash,
    );
    expect(links.map((link) => link.url)).toEqual([
        "https://private.example.test/fresh-one",
        "https://private.example.test/fresh-two",
    ]);
    expect(links.every((link) => link.filename === "opening.png")).toBe(true);
});

it("keeps an image visible when download fails and retries without starting generation", async () => {
    const download = vi
        .spyOn(mediaApi, "getSmartRemakeGeneratedImageDownload")
        .mockRejectedValueOnce(new Error("unavailable"))
        .mockResolvedValueOnce({
            url: "https://private.example.test/retry",
            filename: "opening.png",
        });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    render(createElement(RemakeGeneratedImage, { ...identities, image, ordinal: 1 }));
    fireEvent.click(screen.getByRole("button", { name: "Tải ảnh gốc · Ảnh đầu" }));
    expect((await screen.findByRole("alert")).textContent).toContain("Chưa tải được ảnh");
    expect(screen.getByRole("img").getAttribute("src")).toBe(image.url);
    fireEvent.click(screen.getByRole("button", { name: "Thử tải lại · Ảnh đầu" }));
    await waitFor(() => expect(download).toHaveBeenCalledTimes(2));
});

it("does not navigate to a non-HTTP download returned by a failed service", async () => {
    vi.spyOn(mediaApi, "getSmartRemakeGeneratedImageDownload").mockResolvedValue({
        url: "javascript:alert(1)",
        filename: "image.png",
    });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    render(createElement(RemakeGeneratedImage, { ...identities, image, ordinal: 1 }));
    fireEvent.click(screen.getByRole("button", { name: "Tải ảnh gốc · Ảnh đầu" }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(click).not.toHaveBeenCalled();
});

it("provides an explicit refresh when a preview can no longer be loaded", () => {
    const onRefresh = vi.fn();
    render(createElement(RemakeGeneratedImage, { ...identities, image, ordinal: 1, onRefresh }));
    fireEvent.error(screen.getByRole("img"));
    fireEvent.click(screen.getByRole("button", { name: "Làm mới ảnh xem trước" }));
    expect(onRefresh).toHaveBeenCalledTimes(1);
});

it("can download directly from the enlarged image dialog", async () => {
    const download = vi.spyOn(mediaApi, "getSmartRemakeGeneratedImageDownload").mockResolvedValue({
        url: "https://private.example.test/enlarged",
        filename: "opening.png",
    });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    render(createElement(RemakeGeneratedImage, { ...identities, image, ordinal: 1 }));
    fireEvent.click(screen.getByRole("button", { name: "Phóng to ảnh tham chiếu 1 · clip" }));
    expect(screen.getByRole("dialog")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Tải ảnh gốc · Ảnh đầu" }));
    await waitFor(() => expect(download).toHaveBeenCalledTimes(1));
});

it("shows and copies the exact sent prompt as plain text and omits drafts", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
    const prompt = "  Final prompt\n<img src=x onerror=alert(1)>\n  ";
    render(
        createElement(RemakeKiePrompt, {
            videoSubmitted: true,
            request: { model: "wan/3-0-video", requestHash: "request", prompt },
        }),
    );
    expect(screen.getByText("Prompt đã gửi KIE")).toBeTruthy();
    expect(document.querySelector("pre")?.textContent).toBe(prompt);
    expect(document.querySelector("[onerror]")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Sao chép prompt" }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(prompt));
    expect(await screen.findByText("Đã sao chép")).toBeTruthy();
});

it("never labels a prepared or missing historical prompt as sent", () => {
    const view = render(
        createElement(RemakeKiePrompt, {
            videoSubmitted: false,
            request: { model: "wan/3-0-video", requestHash: "request", prompt: "UNSENT" },
        }),
    );
    expect(document.body.textContent).not.toContain("UNSENT");
    expect(document.body.textContent).not.toContain("Prompt đã gửi KIE");
    view.rerender(createElement(RemakeKiePrompt, { videoSubmitted: true }));
    expect(document.body.textContent).toContain("Lượt này chưa lưu prompt KIE");
    expect(screen.queryByRole("button", { name: "Sao chép prompt" })).toBeNull();
});

it("resets copied feedback when the displayed sent request changes", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
    const view = render(
        createElement(RemakeKiePrompt, {
            videoSubmitted: true,
            request: { model: "wan/3-0-video", requestHash: "first", prompt: "First request" },
        }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Sao chép prompt" }));
    expect(await screen.findByText("Đã sao chép")).toBeTruthy();
    view.rerender(
        createElement(RemakeKiePrompt, {
            videoSubmitted: true,
            request: { model: "wan/3-0-video", requestHash: "second", prompt: "Second request" },
        }),
    );
    expect(screen.queryByText("Đã sao chép")).toBeNull();
    expect(screen.getByRole("button", { name: "Sao chép prompt" })).toBeTruthy();
});

it("retains both bookends for a one-scene clip in the result dialog", () => {
    render(
        createElement(RemakeGeneratedMedia, {
            ...identities,
            groups: [
                {
                    index: 1,
                    videoSubmitted: true,
                    conditioningImages: [
                        image,
                        {
                            ...image,
                            frameRole: "ending",
                            requestHash: "b".repeat(64),
                            url: "/ending.png",
                        },
                    ],
                },
            ],
        }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Ảnh & prompt" }));
    expect(screen.getByRole("dialog")).toBeTruthy();
    expect(screen.getByText("Ảnh đầu")).toBeTruthy();
    expect(screen.getByText("Ảnh cuối")).toBeTruthy();
    expect(screen.getAllByRole("button", { name: /Tải ảnh gốc/ })).toHaveLength(2);
});
