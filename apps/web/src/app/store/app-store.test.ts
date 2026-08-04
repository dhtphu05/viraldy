import { describe, expect, it } from "vitest";

import { initialAppState } from "./initial-state";
import { mergePersistedState } from "./app-store";
import type { AppState } from "./store-types";

describe("UGC runtime state", () => {
    it("does not seed fake UGC review assets", () => {
        expect(initialAppState.ugcAssets).toEqual([]);
    });

    it("drops legacy persisted mock analysis state during hydration", () => {
        const merged = mergePersistedState(
            {
                ugcAssets: [{ id: "seed-ugc" }],
                ugcAnalyses: { "seed-ugc": { score: 99 } },
                ugcIssues: { "seed-ugc": [{ title: "fake issue" }] },
                ugcRights: { "seed-ugc": { sparkAllowed: true } },
                ugcActivity: [{ id: "fake-activity" }],
                ugcJobs: { "seed-ugc": { step: 10 } },
            },
            initialAppState as AppState,
        );

        expect(merged.ugcAssets).toEqual([]);
        expect("ugcAnalyses" in merged).toBe(false);
        expect("ugcIssues" in merged).toBe(false);
        expect("ugcRights" in merged).toBe(false);
        expect("ugcActivity" in merged).toBe(false);
        expect("ugcJobs" in merged).toBe(false);
    });
});
