// @vitest-environment jsdom
import { createElement } from "react";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { RemakeAnalysisLoading } from "./remake-analysis-loading";

afterEach(cleanup);

describe("analysis imported media", () => {
    it.each([2, 3])(
        "keeps all %i imported product images visible with the selected primary",
        (count) => {
            const productUrls = Array.from(
                { length: count },
                (_, index) => `/product-${index}.png`,
            );
            const { container } = render(
                createElement(RemakeAnalysisLoading, {
                    action: "analyze",
                    presentation: "inline",
                    sourceUrl: "/portrait.mp4",
                    productUrls,
                    primaryIndex: 1,
                }),
            );
            expect(container.querySelectorAll("figure")).toHaveLength(count + 1);
            expect(screen.getAllByRole("img", { name: /Ảnh sản phẩm \d/ })).toHaveLength(count);
            productUrls.forEach((src, index) => {
                const card = screen.getByRole("figure", { name: `Ảnh sản phẩm ${index + 1}` });
                expect(within(card).getByRole("img").getAttribute("src")).toBe(src);
                expect(Boolean(within(card).queryByText("Ảnh chính"))).toBe(index === 1);
            });
            expect(container.querySelector("video")?.getAttribute("src")).toBe("/portrait.mp4");
        },
    );

    it("enlarges the clicked supplementary photo without changing the primary", () => {
        render(
            createElement(RemakeAnalysisLoading, {
                action: "analyze",
                presentation: "inline",
                productUrls: ["/front.png", "/back.png", "/detail.png"],
                primaryIndex: 1,
            }),
        );
        const detail = screen.getByRole("figure", { name: "Ảnh sản phẩm 3" });
        const primary = screen.getByRole("figure", { name: "Ảnh sản phẩm 2" });
        fireEvent.click(within(detail).getByRole("button", { name: "Phóng to ảnh sản phẩm" }));
        const dialog = screen.getByRole("dialog");
        expect(within(dialog).getByRole("img").getAttribute("src")).toBe("/detail.png");
        expect(within(primary).getByText("Ảnh chính")).toBeTruthy();
    });

    it("keeps the single saved image marked primary when its old index was higher", () => {
        render(
            createElement(RemakeAnalysisLoading, {
                action: "analyze",
                presentation: "inline",
                productUrl: "/saved-main.png",
                primaryIndex: 2,
            }),
        );
        expect(screen.getByRole("img", { name: "Sản phẩm của bạn" }).getAttribute("src")).toBe(
            "/saved-main.png",
        );
        expect(screen.getByText("Ảnh chính")).toBeTruthy();
    });
});
