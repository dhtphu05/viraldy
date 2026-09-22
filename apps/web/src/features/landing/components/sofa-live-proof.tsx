import { Sparkles } from "lucide-react";

import {
    DecisionSummary,
    Dimensions,
    ScoreVideoPreview,
    StrengthsAndBlockers,
} from "@/features/tiktok-scorer/components/score-result-panels";
import type { TikTokScoreRun } from "@/features/tiktok-scorer/types";
import { SectionWrapper } from "./section-wrapper";

const sofaScoreRun: TikTokScoreRun = {
    id: "25ae97d6-208d-4a0c-a715-4aab03db4d91",
    workspaceId: "cb53ecaa-6fc1-4dfa-af17-00468185f6de",
    assetId: "7a867853-4b8c-470a-ba96-824741c5a4bc",
    assetVersionId: "948dd736-6eba-4fad-9d0e-31ad21705768",
    assetName: "ugc-video-sofa.mp4",
    productId: "791513ff-2f06-40fb-9074-f70b515e5859",
    productName: "Stretch Sofa Cover Live Demo",
    status: "completed",
    currentStage: "completed",
    jobId: "bce37c38-b5b4-43ed-ba6c-f118ada1824f",
    score: 94,
    confidence: "medium",
    decision: "structurally_ready",
    paidUseRightsStatus: "not_applicable",
    finalPaidReadiness: "not_applicable",
    scoreMode: "product_aware",
    intendedUse: "tiktok_organic",
    profile: {
        code: "general_tiktok_v1",
        label: "General TikTok",
        selectionMode: "user_selected",
        confidence: null,
        reason: null,
        alternatives: [],
        evidenceIds: [],
    },
    dimensions: [
        {
            code: "claim_safety",
            label: "Claim Safety",
            score: 70,
            applicability: "applicable",
            evidenceStatus: "sufficient",
            confidence: "medium",
            reason: "Claim safety is derived from persisted spoken and overlay claim evidence.",
            positiveSignals: ["No high-risk claim candidate was observed."],
            missingSignals: [],
            uncertainty: [],
            evidenceIds: [
                "00266715-e8e2-4dc1-9d2c-9c71b7205318",
                "22957e46-5a33-4ebd-92f1-7072898e07cd",
                "f1078ee6-b1c3-433b-8b60-5ebb60275d6e",
            ],
            ruleCodes: ["V2_CLAIM_SAFETY"],
        },
        {
            code: "creator_authenticity",
            label: "Creator Authenticity",
            score: 100,
            applicability: "applicable",
            evidenceStatus: "sufficient",
            confidence: "medium",
            reason: "Delivery is evaluated from observed voice, context, and firsthand-use cues.",
            positiveSignals: ["Natural creator delivery"],
            missingSignals: [],
            uncertainty: [],
            evidenceIds: ["3ecdcadd-f21b-45ee-9fe8-e0d6cead5ace"],
            ruleCodes: ["V2_CREATOR_AUTHENTICITY"],
        },
        {
            code: "cta_readiness",
            label: "CTA Readiness",
            score: 85,
            applicability: "applicable",
            evidenceStatus: "sufficient",
            confidence: "medium",
            reason: "CTA readiness is based on observed action clarity and supported shop cues.",
            positiveSignals: ["A clear call to action was observed."],
            missingSignals: [],
            uncertainty: [],
            evidenceIds: ["09ed4aaa-7ffe-4d8f-8658-1f7768556982"],
            ruleCodes: ["V2_CTA_READINESS"],
        },
        {
            code: "demo_clarity",
            label: "Demo Clarity",
            score: 100,
            applicability: "applicable",
            evidenceStatus: "sufficient",
            confidence: "medium",
            reason: "Demo clarity is derived from observed steps, mechanism, and result.",
            positiveSignals: ["A demo is observed."],
            missingSignals: [],
            uncertainty: [],
            evidenceIds: [
                "031e8a52-8b39-4a4e-8824-b3bdf68e123e",
                "034c0937-dc32-4bbb-a538-da7008bac190",
                "1ee9e596-0329-44db-9714-f926a69e68d2",
                "3d2d4294-ab84-48e3-bd8d-d24b6f08b493",
                "5dd17513-06d9-45ba-bfe6-870116fa4aea",
                "a38f9a88-32d6-4004-b473-7780a0b723d0",
            ],
            ruleCodes: ["V2_DEMO_CLARITY"],
        },
        {
            code: "hook_clarity",
            label: "Hook Clarity",
            score: 88,
            applicability: "applicable",
            evidenceStatus: "sufficient",
            confidence: "medium",
            reason: "Opening clarity is derived from the persisted hook observation.",
            positiveSignals: ["An opening hook was observed."],
            missingSignals: [],
            uncertainty: [],
            evidenceIds: ["f27feea4-0ba0-4dfa-a43e-420238b5f14f"],
            ruleCodes: ["V2_HOOK_CLARITY"],
        },
        {
            code: "offer_clarity",
            label: "Value & Offer Clarity",
            score: null,
            applicability: "unknown",
            evidenceStatus: "insufficient",
            confidence: "low",
            reason: "Value or offer clarity is not established by available evidence.",
            positiveSignals: [],
            missingSignals: ["Sufficient persisted evidence"],
            uncertainty: ["Value or offer clarity is not established by available evidence."],
            evidenceIds: [],
            ruleCodes: [],
        },
        {
            code: "product_visibility",
            label: "Product Visibility",
            score: 100,
            applicability: "applicable",
            evidenceStatus: "sufficient",
            confidence: "medium",
            reason: "Visibility is based on observed clarity, in-use footage, and readable framing.",
            positiveSignals: [
                "Clear product appearance",
                "Product shown in use",
                "Readable close-up",
            ],
            missingSignals: [],
            uncertainty: [],
            evidenceIds: [
                "81fda637-ba62-49cc-a87b-c4154bf4950c",
                "58157c79-f646-4a24-b07a-bc38f6ef2a1d",
                "cc7088c8-64ef-4a2c-b795-8ee1d3c1bf2a",
                "4044b271-a805-44e3-88dd-f43c5f9aafb8",
            ],
            ruleCodes: ["V2_PRODUCT_VISIBILITY"],
        },
        {
            code: "proof_strength",
            label: "Proof Strength",
            score: 100,
            applicability: "applicable",
            evidenceStatus: "sufficient",
            confidence: "medium",
            reason: "Proof strength is based on observable, specific evidence rather than outcome claims.",
            positiveSignals: ["Observable proof"],
            missingSignals: [],
            uncertainty: [],
            evidenceIds: ["c31c11dc-1db7-4096-91f6-5b98e35676ee"],
            ruleCodes: ["V2_PROOF_STRENGTH"],
        },
        {
            code: "tiktok_native_fit",
            label: "TikTok-Native Fit",
            score: 100,
            applicability: "applicable",
            evidenceStatus: "sufficient",
            confidence: "medium",
            reason: "TikTok-native fit is based on observed format, captions, and native execution cues.",
            positiveSignals: [
                "Vertical framing",
                "Readable on-screen text",
                "TikTok-native execution cues",
            ],
            missingSignals: [],
            uncertainty: [],
            evidenceIds: [
                "f1078ee6-b1c3-433b-8b60-5ebb60275d6e",
                "5b44e756-4837-40d1-aa49-d27a30ce1b4a",
                "a9d638ef-8f8d-4054-9c2b-5c45b50323be",
            ],
            ruleCodes: ["V2_TIKTOK_NATIVE_FIT"],
        },
    ],
    findings: [],
    fixes: [],
    strengths: [
        {
            code: "PRESERVE_HOOK_CLARITY",
            title: "Preserve hook clarity",
            sourceDimension: "hook_clarity",
            evidenceIds: ["f27feea4-0ba0-4dfa-a43e-420238b5f14f"],
        },
        {
            code: "PRESERVE_PRODUCT_VISIBILITY",
            title: "Preserve product visibility",
            sourceDimension: "product_visibility",
            evidenceIds: [
                "81fda637-ba62-49cc-a87b-c4154bf4950c",
                "58157c79-f646-4a24-b07a-bc38f6ef2a1d",
                "cc7088c8-64ef-4a2c-b795-8ee1d3c1bf2a",
                "4044b271-a805-44e3-88dd-f43c5f9aafb8",
            ],
        },
        {
            code: "PRESERVE_DEMO_CLARITY",
            title: "Preserve demo clarity",
            sourceDimension: "demo_clarity",
            evidenceIds: [
                "031e8a52-8b39-4a4e-8824-b3bdf68e123e",
                "034c0937-dc32-4bbb-a538-da7008bac190",
            ],
        },
        {
            code: "PRESERVE_PROOF_STRENGTH",
            title: "Preserve proof strength",
            sourceDimension: "proof_strength",
            evidenceIds: ["c31c11dc-1db7-4096-91f6-5b98e35676ee"],
        },
        {
            code: "PRESERVE_CREATOR_AUTHENTICITY",
            title: "Preserve creator authenticity",
            sourceDimension: "creator_authenticity",
            evidenceIds: ["3ecdcadd-f21b-45ee-9fe8-e0d6cead5ace"],
        },
    ],
    evidence: [],
    sceneInventory: null,
    optionalUpgrades: [],
    uncertainty: [],
    mediaUrl: "/demo-media/sofa-cover-ugc.mp4",
    mediaExpiresAt: null,
    partialEvidence: false,
    revisionCount: 0,
    comparisonIds: [],
    parentScoreRunId: null,
    failureCode: null,
    failureMessage: null,
    createdAt: "2026-08-06T02:21:45.386280Z",
    updatedAt: null,
    completedAt: "2026-08-06T02:23:45.035700Z",
};

export function SofaLiveProof() {
    return (
        <SectionWrapper
            id="sofa-live-proof"
            background="surface"
            className="py-20 border-b border-hairline"
        >
            <div className="mx-auto max-w-5xl">
                <div className="mx-auto mb-10 max-w-4xl text-center">
                    <span className="inline-flex items-center gap-2 rounded-full bg-ok-soft px-3 py-1.5 text-xs font-semibold text-ok">
                        <Sparkles className="h-3.5 w-3.5" />
                        Live TikTok Scorer example · sofa cover UGC
                    </span>
                    <h2 className="mt-4 text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
                        See what Viraldy returns after reviewing a real creator video.
                    </h2>
                    <p className="mt-4 text-lg leading-relaxed text-text-secondary">
                        We ran a sofa cover UGC video through TikTok Scorer and kept the output
                        evidence-led: video under review, structural readiness, strengths to
                        preserve, blockers, and dimension-level reasons. No virality promise, no
                        vague “make the hook better” feedback.
                    </p>
                </div>

                <div className="space-y-5">
                    <ScoreVideoPreview run={sofaScoreRun} mediaUrl={sofaScoreRun.mediaUrl} />
                    <DecisionSummary run={sofaScoreRun} />
                    <StrengthsAndBlockers run={sofaScoreRun} />
                    <Dimensions dimensions={sofaScoreRun.dimensions} />
                </div>
            </div>
        </SectionWrapper>
    );
}
