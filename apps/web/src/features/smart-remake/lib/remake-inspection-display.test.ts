import { describe, expect, it } from "vitest";
import type { SmartRemakeProject } from "@/shared/api/smart-remake";
import {
    getInspectionExpectationDisplay,
    getInspectionRequirementLabel,
} from "./remake-inspection";

describe("inspection requirement presentation", () => {
    it("labels a fragment finding by logical scene without changing its stable requirement ID", () => {
        const project = {
            scenes: [{ id: "unit-b", index: 1 }],
            sourceSceneMap: { scenes: [{ id: "logical" }] },
            renderPlan: {
                units: [
                    { id: "unit-b", sourceSceneId: "logical", fragmentIndex: 1, fragmentCount: 2 },
                ],
            },
        } as unknown as SmartRemakeProject;
        expect(getInspectionRequirementLabel("scene:unit-b:opening", project.scenes, project)).toBe(
            "Cảnh 1 · đoạn 2/2 · Khung mở đầu",
        );
    });
    it("labels stable scene checks using the persisted scene index", () => {
        const scenes = [{ id: "saved-scene", index: 2 }];
        expect(getInspectionRequirementLabel("scene:saved-scene:opening", scenes)).toBe(
            "Cảnh 3 · Khung mở đầu",
        );
        expect(getInspectionRequirementLabel("scene:saved-scene:presentation", scenes)).toBe(
            "Cảnh 3 · Cách thể hiện",
        );
        expect(getInspectionRequirementLabel("scene:saved-scene:action", scenes)).toBe(
            "Cảnh 3 · Thao tác",
        );
        expect(getInspectionRequirementLabel("scene:historical-uuid:opening", scenes)).toBe(
            "Khung mở đầu của cảnh",
        );
        expect(getInspectionRequirementLabel("keep:0", scenes)).toBe("keep:0");
    });

    it("separates complete structured facts without removing the natural requirement", () => {
        const facts = { shotPlan: { stateBefore: "closed", action: "open lid" }, userEdits: "" };
        const expected = `Match the intended opening state. ${JSON.stringify(facts)}`;
        const display = getInspectionExpectationDisplay(expected);
        expect(display.summary).toBe("Match the intended opening state.");
        expect(JSON.parse(display.details!)).toEqual(facts);
        expect(expected).toContain('"stateBefore":"closed"');
        expect(getInspectionExpectationDisplay("Only authorized claims: []")).toEqual({
            summary: "Only authorized claims:",
            details: "[]",
        });
    });

    it("keeps plain or malformed text intact instead of hiding seller requirements", () => {
        for (const expected of ["Keep the lid closed", "Keep [red] and {wood}", "Use {bad json}"])
            expect(getInspectionExpectationDisplay(expected)).toEqual({ summary: expected });
    });
});
