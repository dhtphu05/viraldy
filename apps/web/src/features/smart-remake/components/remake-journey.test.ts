import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { expect, it, vi } from "vitest";
import { RemakeJourney } from "./remake-journey";

it("names each step and keeps unavailable results disabled", () => {
    const html = renderToStaticMarkup(
        createElement(RemakeJourney, {
            step: "prepare",
            hasPlan: false,
            hasResult: false,
            busy: false,
            onChange: vi.fn(),
        }),
    );
    expect(html).toContain('aria-current="step"');
    expect(html).toContain("Chọn tư liệu");
    expect(html).toContain("Duyệt kịch bản");
    expect(html).toContain("Xem &amp; ghép");
    expect((html.match(/disabled=""/g) ?? []).length).toBe(2);
});

it("allows returning to an existing result when a new plan is not ready", () => {
    const html = renderToStaticMarkup(
        createElement(RemakeJourney, {
            step: "prepare",
            hasPlan: false,
            hasResult: true,
            busy: false,
            onChange: vi.fn(),
        }),
    );
    expect((html.match(/disabled=""/g) ?? []).length).toBe(1);
});

it("keeps pending results navigable without calling them a saved draft", () => {
    const html = renderToStaticMarkup(
        createElement(RemakeJourney, {
            step: "plan",
            hasPlan: true,
            hasResult: true,
            busy: false,
            outputUrl: null,
            onChange: vi.fn(),
        }),
    );
    expect(html).toContain("Chưa có video");
    expect(html).not.toContain("Bản nháp");
    expect(html).not.toContain('aria-label="Có thể mở"');
    expect(html).not.toContain('disabled=""');
});
