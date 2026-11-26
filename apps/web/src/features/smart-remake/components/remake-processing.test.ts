// @vitest-environment jsdom
import { createElement } from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { RemakeProcessing } from "./remake-processing";

afterEach(cleanup);

it("announces the actual operation when analysis changes to generation", () => {
    const { rerender } = render(createElement(RemakeProcessing, { kind: "analyze" }));
    expect(screen.getByRole("status").textContent).toContain("Đang phân tích video mẫu");
    expect(screen.getByRole("status").textContent).toContain("duyệt kịch bản trước khi tạo video");
    rerender(createElement(RemakeProcessing, { kind: "generate" }));
    expect(screen.getByRole("status").textContent).toContain("Đang tạo video cho bạn");
    expect(screen.getByRole("status").textContent).toContain("kịch bản đã duyệt");
    expect(screen.queryByRole("progressbar")).toBeNull();
    expect(document.body.textContent).not.toMatch(/\d+\s*%|hoàn tất|đã phân tích/i);
});

it("keeps the seller's selected media visible without autoplaying or replacing it with examples", () => {
    const { container } = render(
        createElement(RemakeProcessing, {
            kind: "generate",
            sourceUrl: "blob:my-video",
            productUrl: "blob:my-product",
        }),
    );
    expect(container.querySelector("video")?.getAttribute("src")).toBe("blob:my-video");
    expect(container.querySelector("video")?.autoplay).toBe(false);
    expect(screen.getByAltText("Sản phẩm đang dùng").getAttribute("src")).toBe("blob:my-product");
    expect(screen.getByText("Giữ trang này mở trong lúc xử lý nhé.")).toBeTruthy();
});
