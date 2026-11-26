import { describe, expect, it } from "vitest";
import type { SmartRemakeProject } from "@/shared/api/smart-remake";
import { canUseRemakeVersion, latestRemakeProject } from "./remake-review";

const project = {
    id: "project",
    revision: 2,
    scenes: [
        {
            id: "scene",
            activeVersionId: "active",
            versions: [
                { id: "active", parentVersionId: null, technicalCheck: { status: "passed" } },
                {
                    id: "candidate",
                    parentVersionId: "active",
                    technicalCheck: { status: "passed" },
                },
                { id: "stale", parentVersionId: "old", technicalCheck: { status: "passed" } },
                { id: "broken", parentVersionId: "active", technicalCheck: { status: "failed" } },
                {
                    id: "previous",
                    parentVersionId: null,
                    usedByRevision: 1,
                    technicalCheck: { status: "passed" },
                },
            ],
        },
    ],
} as unknown as SmartRemakeProject;

describe("controlled scene version review", () => {
    it("allows a checked candidate of the current scene version", () => {
        expect(canUseRemakeVersion(project, "scene", "candidate")).toBe(true);
    });
    it.each(["active", "stale", "broken", "unknown"])("does not accept %s", (id) => {
        expect(canUseRemakeVersion(project, "scene", id)).toBe(false);
    });
    it("allows an explicitly recorded historical version for restoration", () => {
        expect(canUseRemakeVersion(project, "scene", "previous")).toBe(true);
    });
    it("does not treat a version from another scene as a candidate", () => {
        expect(canUseRemakeVersion(project, "another-scene", "candidate")).toBe(false);
    });
    it("ignores an older response for the same project", () => {
        expect(latestRemakeProject(project, { ...project, revision: 1 })).toBe(project);
    });
    it("can replace the whole project without retaining an old candidate", () => {
        const next = { ...project, id: "new-project", revision: 1 };
        expect(latestRemakeProject(project, next)).toBe(next);
    });
});
