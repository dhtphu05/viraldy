import { describe, expect, it } from "vitest";

import { getSmartRemakeWorkflowProgress } from "./smart-remake-progress";

describe("getSmartRemakeWorkflowProgress", () => {
    it("shows the active analysis stage and a measured completion percentage", () => {
        const progress = getSmartRemakeWorkflowProgress({
            analysisStep: 2,
            isCompiling: true,
            isRendering: false,
            renderProgress: 0,
        });

        expect(progress.kind).toBe("analysis");
        expect(progress.currentStep).toBe(2);
        expect(progress.percentage).toBe(60);
        expect(progress.steps).toHaveLength(5);
        expect(progress.steps[2]?.label).toBe("Đang nhận diện sản phẩm");
    });

    it("switches to the four-stage video creation flow", () => {
        const progress = getSmartRemakeWorkflowProgress({
            analysisStep: 4,
            isCompiling: false,
            isRendering: true,
            renderProgress: 63,
        });

        expect(progress.kind).toBe("render");
        expect(progress.currentStep).toBe(2);
        expect(progress.percentage).toBe(63);
        expect(progress.steps).toHaveLength(4);
        expect(progress.steps[2]?.label).toBe("Đang dựng chuyển động");
    });
});
