import { describe, expect, it } from "vitest";
import {
    DEFAULT_REMAKE_INTENT,
    emptyRemakeRights,
    getRemakeIntakeError,
    normalizeRemakeRequirements,
    remakeRightsInput,
    getRemakeResumeStep,
    confirmRemakeMediaRights,
    hasCurrentRemakeRightsAttestation,
    invalidateRemakeMediaRights,
    getRemakeRightsError,
    remakeBudgetInput,
} from "./remake-intake";
import type { SmartRemakeProject } from "@/shared/api/smart-remake";

const requirement = {
    intent: "Keep product",
    keep: [],
    replace: [],
    forbid: [],
    claims: [],
    requiresCharacter: false,
};
const budget = { capUsd: "3.00", maxAttempts: 12, maxDurationSeconds: 600 };
const declaration = {
    basis: "owned" as const,
    scope: "Internal dev",
    declared: true,
    evidenceNote: "Generated artwork",
};
const rights = { source: declaration, product: declaration, providerDisclosureAcknowledged: true };

describe("owned intake preparation", () => {
    it("accepts unlimited app policy without inventing a USD, attempt or time grant", () => {
        expect(getRemakeIntakeError(requirement, rights, { mode: "unlimited" }, false)).toBeNull();
        expect(remakeBudgetInput({ mode: "unlimited" })).toEqual({ mode: "unlimited" });
        expect(getRemakeRightsError(requirement, emptyRemakeRights(), false)).toBeTruthy();
    });
    it("has no implied rights or provider consent", () => {
        const initial = emptyRemakeRights();
        expect(initial.source.declared).toBe(false);
        expect(initial.product.scope).toBe("");
        expect(initial.providerDisclosureAcknowledged).toBe(false);
    });
    it("preserves explicit requirements while normalizing submission whitespace", () => {
        const input = { ...requirement, intent: " Keep product ", keep: ["", " shape ", " "] };
        expect(normalizeRemakeRequirements(input).keep).toEqual(["shape"]);
        expect(input.keep).toEqual(["", " shape ", " "]);
    });
    it("accepts explicit complete declarations and positive bounded cap", () => {
        expect(getRemakeIntakeError(requirement, rights, budget, false)).toBeNull();
    });
    it("uses the Smart Remake goal when no custom intent is supplied", () => {
        const input = { ...requirement, intent: " \n " };
        expect(normalizeRemakeRequirements(input).intent).toBe(DEFAULT_REMAKE_INTENT);
        expect(getRemakeIntakeError(input, rights, budget, false)).toBeNull();
        expect(input.intent).toBe(" \n ");
        expect(
            normalizeRemakeRequirements({ ...requirement, intent: " Custom goal " }).intent,
        ).toBe("Custom goal");
    });
    it.each(["", "0", "-1", "NaN", "1e3", "1.1234567"])(
        "rejects unbounded/invalid USD cap %s",
        (capUsd) => {
            expect(
                getRemakeIntakeError(requirement, rights, { ...budget, capUsd }, false),
            ).toBeTruthy();
        },
    );
    it("requires all asset evidence, disclosure and character consent", () => {
        expect(
            getRemakeIntakeError(
                requirement,
                { ...rights, source: { ...declaration, revoked: true } },
                budget,
                false,
            ),
        ).toBeTruthy();
        expect(
            getRemakeIntakeError(
                requirement,
                { ...rights, product: { ...declaration, evidenceNote: "" } },
                budget,
                false,
            ),
        ).toBeTruthy();
        expect(
            getRemakeIntakeError(
                requirement,
                { ...rights, providerDisclosureAcknowledged: false },
                budget,
                false,
            ),
        ).toBeTruthy();
        expect(
            getRemakeIntakeError(
                { ...requirement, requiresCharacter: true },
                rights,
                budget,
                false,
            ),
        ).toBeTruthy();
        expect(
            getRemakeIntakeError(requirement, { ...rights, character: declaration }, budget, true),
        ).toBeTruthy();
        expect(
            getRemakeIntakeError(
                { ...requirement, requiresCharacter: true },
                {
                    ...rights,
                    character: declaration,
                    characterConsent: {
                        consented: true,
                        scope: "Dev",
                        evidenceNote: "Original illustration",
                    },
                },
                budget,
                true,
            ),
        ).toBeNull();
        expect(
            getRemakeIntakeError(requirement, rights, { ...budget, maxAttempts: 0 }, false),
        ).toBeTruthy();
        expect(
            getRemakeIntakeError(
                requirement,
                rights,
                { ...budget, maxDurationSeconds: 1.5 },
                false,
            ),
        ).toBeTruthy();
    });
    it("requires the character policy when an original character reference is retained", () => {
        const withCharacter = {
            ...rights,
            character: declaration,
            characterConsent: {
                consented: true,
                scope: "Dev illustration",
                evidenceNote: "Self-authored illustration, no real person",
            },
        };
        expect(getRemakeIntakeError(requirement, withCharacter, budget, true)).toContain(
            "Xác nhận yêu cầu giữ nhân vật",
        );
    });
    it("does not send server verification metadata as client assertions", () => {
        const saved = {
            ...rights,
            source: {
                ...declaration,
                verified: true,
                declaredBy: "server",
                verification: { status: "reviewed" },
            },
        };
        expect(remakeRightsInput(saved).source).toEqual({
            ...declaration,
            revoked: false,
            attribution: null,
        });
        expect(saved.source.verified).toBe(true);
    });
    it("restores intake, unrendered plan and existing media without submitting work", () => {
        const base = {
            phase: "intake",
            schemaVersion: 2,
            scenes: [],
        } as unknown as SmartRemakeProject;
        expect(getRemakeResumeStep(base)).toBe("prepare");
        expect(getRemakeResumeStep({ ...base, phase: "compiled", renderPlan: {} as never })).toBe(
            "plan",
        );
        expect(
            getRemakeResumeStep({
                ...base,
                phase: "compiled",
                renderPlan: {} as never,
                pendingOperation: { id: "job", status: "running", needsReconciliation: false },
            }),
        ).toBe("result");
        expect(
            getRemakeResumeStep({
                ...base,
                phase: "rendered",
                scenes: [{ versions: [{}] }] as never,
            }),
        ).toBe("result");
    });
});

describe("versioned media rights attestation", () => {
    it("allows an explicit current attestation without invented evidence and preserves original inputs", () => {
        const initial = emptyRemakeRights();
        const accepted = confirmRemakeMediaRights(initial);
        expect(getRemakeIntakeError(requirement, accepted, budget, false)).toBeNull();
        expect(accepted.source.basis).toBe("attested");
        expect(accepted.source.scope).toBe("");
        expect(accepted.source.evidenceNote).toBe("");
        expect(initial.source.declared).toBe(false);
        expect(hasCurrentRemakeRightsAttestation(accepted)).toBe(true);
    });
    it("rejects missing, unaccepted, revoked and outdated policy receipts", () => {
        const accepted = confirmRemakeMediaRights(emptyRemakeRights());
        for (const attestation of [
            undefined,
            { policyVersion: "old", accepted: true },
            { ...accepted.attestation!, accepted: false },
            { ...accepted.attestation!, revoked: true },
        ]) {
            const invalid = { ...accepted, attestation } as typeof accepted;
            expect(hasCurrentRemakeRightsAttestation(invalid)).toBe(false);
            expect(getRemakeIntakeError(requirement, invalid, budget, false)).toBeTruthy();
        }
    });
    it("removes consent on media change and strips server receipt metadata from mutations", () => {
        const accepted = confirmRemakeMediaRights(emptyRemakeRights());
        const saved = {
            ...accepted,
            attestation: {
                ...accepted.attestation!,
                acceptedBy: "server",
                acceptedAt: "now",
                statement: "server text",
            },
        };
        expect(remakeRightsInput(saved).attestation).toEqual(accepted.attestation);
        const changed = invalidateRemakeMediaRights(saved);
        expect(hasCurrentRemakeRightsAttestation(changed)).toBe(false);
        expect(changed.source.declared).toBe(false);
        expect(changed.product.declared).toBe(false);
        expect(changed.providerDisclosureAcknowledged).toBe(false);
        expect(accepted.source.declared).toBe(true);
    });
    it("still requires evidence when optional details choose a specific licence basis", () => {
        const accepted = confirmRemakeMediaRights(emptyRemakeRights());
        expect(
            getRemakeIntakeError(
                requirement,
                { ...accepted, source: { ...accepted.source, basis: "licensed" } },
                budget,
                false,
            ),
        ).toBeTruthy();
    });
    it("does not replace character consent or the explicit budget", () => {
        const accepted = confirmRemakeMediaRights(emptyRemakeRights());
        expect(
            getRemakeIntakeError(requirement, accepted, { ...budget, capUsd: "" }, false),
        ).toContain("trần USD");
        expect(
            getRemakeIntakeError(
                { ...requirement, requiresCharacter: true },
                accepted,
                budget,
                true,
            ),
        ).toBeTruthy();
    });
});
