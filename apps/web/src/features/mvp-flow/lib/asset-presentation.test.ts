import { describe, expect, it } from "vitest";

import { assetDisplayName } from "./asset-presentation";

describe("assetDisplayName", () => {
    it("uses seller-facing metadata before a stable type fallback", () => {
        expect(
            assetDisplayName({
                id: "dda2f020-badc-428c-9ded-633022d6e121",
                asset_type: "reference",
                metadata_json: { title: "Sofa transformation" },
            }),
        ).toBe("Sofa transformation");
        expect(
            assetDisplayName({
                id: "dda2f020-badc-428c-9ded-633022d6e121",
                asset_type: "reference",
                metadata_json: {},
            }),
        ).toBe("Reference video");
    });

    it("never exposes an asset id as the visible label", () => {
        const id = "dda2f020-badc-428c-9ded-633022d6e121";

        expect(assetDisplayName({ id, asset_type: "ugc", metadata_json: {} })).toBe("UGC video");
        expect(assetDisplayName({ id, asset_type: "ugc", metadata_json: {} })).not.toContain(id);
    });
});
