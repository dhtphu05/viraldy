// @vitest-environment jsdom
import { createElement } from "react";
import { cleanup, fireEvent, render } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { RemakeClipThumbnail } from "./remake-clip-thumbnail";

afterEach(cleanup);

it("decodes an actual first frame without autoplaying the clip", () => {
    const view = render(createElement(RemakeClipThumbnail, { src: "/clip.mp4" }));
    const video = view.container.querySelector("video")!;
    Object.defineProperty(video, "duration", { value: 8, configurable: true });
    expect(video.autoplay).toBe(false);
    expect(video.style.opacity).toBe("0");
    fireEvent.loadedMetadata(video);
    expect(video.currentTime).toBe(0.05);
    fireEvent.seeked(video);
    expect(video.style.opacity).toBe("1");
});

it("offers a labelled fallback when a thumbnail fails to load", () => {
    const view = render(
        createElement(RemakeClipThumbnail, { src: "/broken.mp4", label: "Hình xem trước cảnh 1" }),
    );
    fireEvent.error(view.container.querySelector("video")!);
    expect(view.container.querySelector("video")).toBeNull();
    expect(view.container.textContent).toContain("Hình xem trước cảnh 1");
    expect(view.container.textContent).toContain("Chưa tải được hình xem trước");
});
