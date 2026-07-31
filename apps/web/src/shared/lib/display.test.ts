import { describe, expect, it } from "vitest";

import { humanizeSystemText } from "./display";

describe("humanizeSystemText", () => {
    it("humanizes embedded snake-case tokens without rewriting normal prose", () => {
        expect(humanizeSystemText("Test whether result_first improves qualified signal.")).toBe(
            "Test whether result first improves qualified signal.",
        );
        expect(humanizeSystemText("Shipping claims need seller confirmation.")).toBe(
            "Shipping claims need seller confirmation.",
        );
    });
});
