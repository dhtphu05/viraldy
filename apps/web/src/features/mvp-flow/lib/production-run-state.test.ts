import { describe, expect, it } from "vitest";

import {
    deriveProductionRunPhases,
    deriveStaleOutputs,
    highestPriorityUnresolvedPhase,
    productionContextReady,
    resolveProductionAssetId,
    reviewOutcomeReady,
    successfulJobOutputId,
    type ProductionContext,
} from "./production-run-state";

const completeContext: ProductionContext = {
    entryType: "reference-first",
    productId: "product-1",
    primaryReferenceId: "reference-1",
    objective: "Affiliate test",
    market: "US",
    buyerPersona: "Small-space renter",
    buyerPain: "No usable vanity space",
    desiredOutcome: "A compact daily setup",
};

describe("Production Run state", () => {
    it("always selects exactly one active phase", () => {
        const phases = deriveProductionRunPhases({
            context: completeContext,
            dnaId: "dna-1",
            patternKitId: "pattern-1",
            viralKitId: "viral-1",
            selectedConceptId: "concept-1",
            conceptConfirmed: true,
            packId: "pack-1",
        });

        expect(phases.filter((phase) => phase.active)).toHaveLength(1);
        expect(phases.find((phase) => phase.active)?.id).toBe("review");
    });

    it.each(["reference-first", "product-first"] as const)(
        "supports the %s entry while keeping UGC optional",
        (entryType) => {
            const context = { ...completeContext, entryType };
            expect(productionContextReady(context)).toBe(true);
            expect(
                highestPriorityUnresolvedPhase({
                    context,
                    dnaId: "dna-1",
                    patternKitId: "pattern-1",
                }),
            ).toBe("adapt");
        },
    );

    it("keeps context active until seller context is complete", () => {
        const phases = deriveProductionRunPhases({
            context: { ...completeContext, buyerPain: "" },
        });
        expect(phases.find((phase) => phase.active)?.id).toBe("context");
        expect(phases.find((phase) => phase.id === "decode")?.status).toBe("locked");
    });

    it("resumes at the highest-priority unresolved phase", () => {
        expect(
            highestPriorityUnresolvedPhase({
                context: completeContext,
                dnaId: "dna-1",
                patternKitId: "pattern-1",
                viralKitId: "viral-1",
                selectedConceptId: "concept-1",
                conceptConfirmed: false,
                packId: "pack-1",
            }),
        ).toBe("adapt");
    });

    it("marks product changes downstream stale", () => {
        expect(deriveStaleOutputs({ productId: "p1" }, { productId: "p2" })).toEqual([
            "pattern-kit",
            "viral-kit",
            "campaign-pack",
            "preflight",
        ]);
    });

    it("marks concept changes as Pack and Preflight stale", () => {
        expect(
            deriveStaleOutputs(
                { selectedConceptId: "concept-1" },
                { selectedConceptId: "concept-2" },
            ),
        ).toEqual(["campaign-pack", "preflight"]);
    });

    it("marks Pack and UGC version changes as Preflight stale", () => {
        expect(
            deriveStaleOutputs(
                { packVersionId: "v1", ugcAssetVersionId: "ugc-v1" },
                { packVersionId: "v2", ugcAssetVersionId: "ugc-v2" },
            ),
        ).toEqual(["preflight"]);
    });

    it("does not use a fixture in normal mode and lets uploaded media override fallback", () => {
        expect(resolveProductionAssetId({ fixtureAssetId: "fixture" })).toBeUndefined();
        expect(
            resolveProductionAssetId({
                uploadedAssetId: "uploaded",
                fixtureAssetId: "fixture",
                allowFixtureFallback: true,
            }),
        ).toBe("uploaded");
    });

    it("auto-loads successful job outputs only", () => {
        expect(
            successfulJobOutputId(
                {
                    status: "succeeded",
                    output_json: { creative_dna_version_id: "dna-2" },
                },
                "creative_dna_version_id",
            ),
        ).toBe("dna-2");
        expect(
            successfulJobOutputId(
                {
                    status: "running",
                    output_json: { creative_dna_version_id: "dna-2" },
                },
                "creative_dna_version_id",
            ),
        ).toBeUndefined();
    });

    it("blocks the ready outcome while hard blockers remain", () => {
        expect(reviewOutcomeReady({ reviewComplete: true, hardBlockerCount: 1 })).toBe(false);
        expect(reviewOutcomeReady({ reviewComplete: true, hardBlockerCount: 0 })).toBe(true);
    });
});
