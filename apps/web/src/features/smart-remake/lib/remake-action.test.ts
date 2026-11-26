import { describe, expect, it } from "vitest";
import { getRemakeActionBudgetError, remakePreflightChanged } from "./remake-action";
import type { SmartRemakePreflight } from "@/shared/api/smart-remake";
const quote = {
    action: "analyze",
    contextHash: "saved-context",
    mode: "live",
    scope: { targetDuration: 8, sceneCount: 0, groupCount: 0, imageCount: 0 },
    calls: { analysis: 3, image: 0, video: 0, inspection: 0, total: 3 },
    budget: {
        knownActualUsd: "0",
        reservedUsd: "0",
        exposureUsd: "0",
        additionalReservationUsd: "0.300001",
        minimumCapUsd: "0.300001",
        minimumMaxAttempts: 3,
        minimumDurationSeconds: 1800,
        recommended: { capUsd: "0.300001", maxAttempts: 3, maxDurationSeconds: 1800 },
    },
    blockers: [],
} as SmartRemakePreflight;
describe("action budget approval", () => {
    it("compares six decimal USD values exactly and rejects scientific notation", () => {
        const budget = { capUsd: "0.300000", maxAttempts: 3, maxDurationSeconds: 1800 };
        expect(getRemakeActionBudgetError(budget, quote)).toContain("0.300001");
        expect(getRemakeActionBudgetError({ ...budget, capUsd: "0.300001" }, quote)).toBeNull();
        expect(getRemakeActionBudgetError({ ...budget, capUsd: "3e-1" }, quote)).not.toBeNull();
    });
    it("requires confirmation again for changed context or costs but allows elapsed time inside approved limits", () => {
        const budget = { capUsd: "1", maxAttempts: 20, maxDurationSeconds: 2000 };
        expect(
            remakePreflightChanged(
                quote,
                { ...quote, budget: { ...quote.budget!, minimumDurationSeconds: 1801 } },
                budget,
            ),
        ).toBe(false);
        expect(remakePreflightChanged(quote, { ...quote, contextHash: "new-config" }, budget)).toBe(
            true,
        );
        expect(
            remakePreflightChanged(
                quote,
                { ...quote, budget: { ...quote.budget!, minimumCapUsd: "1.000001" } },
                budget,
            ),
        ).toBe(true);
    });
});

it("checks reserved attempt and elapsed-time headroom before an explicit confirmation", () => {
    const valid = { capUsd: "1", maxAttempts: 3, maxDurationSeconds: 1800 };
    expect(getRemakeActionBudgetError({ ...valid, maxAttempts: 2 }, quote)).toContain("3 lượt");
    expect(getRemakeActionBudgetError({ ...valid, maxDurationSeconds: 1799 }, quote)).toContain(
        "1800 giây",
    );
    expect(getRemakeActionBudgetError(valid, { ...quote, budget: null })).toContain("Kết nối lại");
    expect(
        remakePreflightChanged(quote, { ...quote, calls: { ...quote.calls, total: 4 } }, valid),
    ).toBe(true);
});
