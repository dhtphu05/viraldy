import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { Button } from "@/shared/ui/button";
import { EmptyState, LoadingState } from "@/shared/ui/empty-state";
import { Skeleton } from "@/shared/ui/skeleton";

describe("EmptyState", () => {
    it("associates its copy and keeps the recovery action available", () => {
        const html = renderToStaticMarkup(
            createElement(EmptyState, {
                title: "No campaigns match these filters",
                description: "Clear filters to see every campaign.",
                action: createElement(Button, null, "Clear filters"),
            }),
        );

        expect(html).toContain("data-empty-state");
        expect(html).toContain("aria-labelledby");
        expect(html).toContain("aria-describedby");
        expect(html).toContain("No campaigns match these filters");
        expect(html).toContain("Clear filters");
    });

    it("supports a compact success state without decorative motion", () => {
        const html = renderToStaticMarkup(
            createElement(EmptyState, {
                compact: true,
                tone: "success",
                title: "No blocking decisions",
            }),
        );

        expect(html).toContain("bg-ok-soft");
        expect(html).toContain("items-start");
        expect(html).not.toContain("animate-");
    });
});

describe("loading skeletons", () => {
    it("hides visual placeholders from assistive technology", () => {
        const html = renderToStaticMarkup(createElement(Skeleton, { className: "h-4" }));

        expect(html).toContain('aria-hidden="true"');
        expect(html).toContain("bg-surface-muted");
        expect(html).toContain("motion-reduce:animate-none");
    });

    it("announces loading once while rendering stable placeholders", () => {
        const html = renderToStaticMarkup(
            createElement(LoadingState, { label: "Loading campaign history" }),
        );

        expect(html).toContain('role="status"');
        expect(html).toContain('aria-busy="true"');
        expect(html).toContain("Loading campaign history");
        expect(html.match(/aria-hidden="true"/g)).toHaveLength(3);
    });
});
