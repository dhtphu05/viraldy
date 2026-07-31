import { describe, expect, it } from "vitest";

import {
    demoCreativeSourceUrl,
    findImportedProduct,
    findImportedReference,
} from "./production-run-handoff";

describe("production run handoff", () => {
    it("finds a product by explicit frontend provenance before matching its name", () => {
        const products = [
            {
                id: "same-name",
                name: "Quilted Sofa Cover",
                external_source: null,
                external_id: null,
                metadata_json: {},
            },
            {
                id: "imported",
                name: "Older catalog label",
                external_source: "frontend_demo",
                external_id: "p-sofa-cover",
                metadata_json: {},
            },
        ];

        expect(
            findImportedProduct(products, {
                id: "p-sofa-cover",
                name: "Quilted Sofa Cover",
            })?.id,
        ).toBe("imported");
    });

    it("uses an exact product name only when no provenance match exists", () => {
        const products = [
            {
                id: "same-name",
                name: "Quilted Sofa Cover",
                external_source: null,
                external_id: null,
                metadata_json: {},
            },
        ];

        expect(
            findImportedProduct(products, {
                id: "p-sofa-cover",
                name: "Quilted Sofa Cover",
            })?.id,
        ).toBe("same-name");
    });

    it("finds a backend reference through the stable creative source URL", () => {
        const sourceUrl = demoCreativeSourceUrl("cr-sofa-cover");
        const references = [
            { id: "other", source_url: null },
            { id: "sofa", source_url: sourceUrl },
        ];

        expect(findImportedReference(references, "cr-sofa-cover")?.id).toBe("sofa");
    });
});
