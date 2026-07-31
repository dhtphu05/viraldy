import type { SeedCampaign } from "@/features/campaigns/mocks/campaigns";
import type {
    CampaignMarket,
    CampaignObjective,
    CampaignPack,
    CreatorTone,
    StoryboardScene,
} from "@/features/campaigns/types/campaign";
import type { ViralConcept } from "@/features/mvp-flow/intelligence-types";

type CampaignHandoffInput = {
    backendPackId: string;
    product: {
        id: string;
        name: string;
        frontendSeedId?: string;
    };
    concept: ViralConcept;
    referenceCreativeId?: string;
    objective?: string;
    market?: string;
    buyerPersona?: string;
    buyerPain?: string;
    desiredOutcome?: string;
    sourceHook?: string;
    sourceAngle?: string;
    sourceDemo?: string;
    keep?: string[];
    change?: string[];
    avoid?: string[];
    now: string;
};

export function createCampaignHandoff(input: CampaignHandoffInput) {
    const campaignId = `campaign-${input.backendPackId}`;
    const packId = `pack-${input.backendPackId}`;
    const objective = campaignObjective(input.objective);
    const market = campaignMarket(input.market);
    const productId = input.product.frontendSeedId ?? input.product.id;
    const concept = input.concept;
    const name = `${input.product.name} - ${concept.name}`;
    const storyboard = conceptStoryboard(concept);

    const pack: CampaignPack = {
        id: packId,
        name,
        status: "Draft",
        objective,
        market,
        platform: "TikTok Shop",
        productId,
        buyerSegment: input.buyerPersona ?? concept.buyer_persona_label,
        language: "English",
        creatorType: "Micro creator",
        creatorTone: creatorTone(concept.delivery_style),
        referenceCreativeIds: input.referenceCreativeId ? [input.referenceCreativeId] : [],
        adaptation: {
            sourceHook: input.sourceHook ?? concept.hook.spoken_text ?? concept.opening_visual,
            sourceAngle: input.sourceAngle ?? concept.narrative_structure,
            sourceDemo: input.sourceDemo ?? concept.demo_mechanism,
            adaptedHook: concept.hook.spoken_text ?? concept.hook.overlay_text ?? concept.name,
            adaptedAngle: concept.creative_angle,
            adaptedDemo: concept.demo_mechanism,
            whyChanged: concept.test_hypothesis,
            keep: input.keep ?? [concept.narrative_structure, concept.hook.hook_type],
            change: input.change ?? [
                `Buyer context: ${input.buyerPain ?? concept.buyer_pain}`,
                `Product proof: ${concept.proof_mechanism}`,
            ],
            avoid: input.avoid ?? concept.claims_to_avoid,
            notes: `Expected learning: ${concept.expected_learning}`,
        },
        angleOptions: [
            {
                id: concept.id,
                name: concept.name,
                buyerProblem: input.buyerPain ?? concept.buyer_pain,
                emotionalTrigger: input.desiredOutcome ?? concept.desired_outcome,
                creatorPersona: concept.creator_persona,
                productProof: concept.proof_mechanism,
                recommendedFormat: concept.narrative_structure,
                fit: concept.confidence.toLowerCase() === "high" ? "Strong fit" : "Good test",
                reason: concept.test_hypothesis,
                referenceCreativeId: input.referenceCreativeId,
            },
        ],
        primaryAngleId: concept.id,
        secondaryAngleIds: [],
        hookOptions: [
            {
                id: `${concept.id}-hook`,
                text:
                    concept.hook.spoken_text ?? concept.hook.overlay_text ?? concept.opening_visual,
                type: "Problem-first",
                sourceAngleId: concept.id,
                creatorStyle: concept.delivery_style,
                fit: "Strong fit",
            },
        ],
        selectedHookIds: [`${concept.id}-hook`],
        script: [
            {
                id: `${concept.id}-script-hook`,
                kind: "Hook",
                text:
                    concept.hook.spoken_text ?? concept.hook.overlay_text ?? concept.opening_visual,
            },
            {
                id: `${concept.id}-script-problem`,
                kind: "Buyer Problem",
                text: input.buyerPain ?? concept.buyer_pain,
            },
            {
                id: `${concept.id}-script-demo`,
                kind: "Demo",
                text: `${concept.demo_mechanism}. ${concept.proof_mechanism}.`,
            },
            {
                id: `${concept.id}-script-cta`,
                kind: "CTA",
                text: concept.cta_strategy,
            },
        ],
        storyboard,
        cta: {
            primary: concept.cta_strategy,
            productTagInstruction: concept.cta_strategy,
            offerStatement: concept.offer_framing ?? "",
            coupon: "",
            shipping: "",
            claimsAllowed: [
                "Describe only the visible product demonstration.",
                ...concept.required_disclosures,
            ],
            claimsToAvoid: concept.claims_to_avoid,
            productLimitations: "",
            complianceNotes: "",
            warnings: [],
        },
        deliverables: {
            numberOfVideos: 3,
            rawFootageRequired: true,
            aspectRatio: "9:16",
            targetDurationSec: 30,
            captionRequired: true,
            productTagRequired: true,
            revisionRounds: 1,
        },
        rights: {
            tiktokOrganic: true,
            tiktokSpark: false,
            metaAds: false,
            website: false,
            email: false,
            editingAllowed: true,
            rawFootageIncluded: true,
            usageDurationDays: 180,
            creatorAttribution: true,
        },
        spark: {
            required: true,
            durationDays: 30,
            requestTiming: "Request after the organic cut is approved.",
        },
        reviewedWarningIds: [],
        createdAt: input.now,
        updatedAt: input.now,
        savedAt: input.now,
    };

    const summary: SeedCampaign = {
        id: campaignId,
        packId,
        name,
        product: input.product.name,
        status: "Draft",
        activeAssets: 0,
        ugcScore: 0,
        gmv: 0,
        nextAction: "Review creator brief",
        objective,
        market,
        platform: "TikTok Shop",
        packStatus: "Draft",
        primaryAngle: concept.name,
        referenceCount: pack.referenceCreativeIds.length,
        hookCount: pack.selectedHookIds.length,
        deliverables: pack.deliverables.numberOfVideos,
        updatedAt: input.now,
    };

    return { campaignId, packId, pack, summary };
}

function conceptStoryboard(concept: ViralConcept): StoryboardScene[] {
    const required: StoryboardScene[] = concept.must_show.map((scene, index) => ({
        id: `${concept.id}-scene-${scene.id}`,
        label: `Required scene ${index + 1}`,
        durationRange: scene.expected_before_ms
            ? `Before ${Math.round(scene.expected_before_ms / 1000)}s`
            : "3-6s",
        visualDirection: scene.instruction,
        spokenLine: "",
        productVisibility: "Prominent",
        framing: "Creator choice",
        mustShow: scene.severity === "hard",
    }));
    return [
        {
            id: `${concept.id}-scene-opening`,
            label: "Opening",
            durationRange: "0-3s",
            visualDirection: concept.opening_visual,
            spokenLine: concept.hook.spoken_text ?? "",
            onScreenText: concept.hook.overlay_text ?? undefined,
            productVisibility: concept.hook.product_present ? "Prominent" : "Contextual",
            framing: "Attention-first close shot",
            mustShow: true,
        },
        ...required,
        {
            id: `${concept.id}-scene-cta`,
            label: "CTA",
            durationRange: "Final 3s",
            visualDirection: concept.cta_strategy,
            spokenLine: concept.cta_strategy,
            productVisibility: "Prominent",
            framing: "Product and tag visible",
            mustShow: true,
        },
    ];
}

function campaignObjective(value?: string): CampaignObjective {
    const normalized = value?.toLowerCase() ?? "";
    if (normalized.includes("organic")) return "Organic Product Test";
    if (normalized.includes("spark")) return "Spark Ads Test";
    return "TikTok Shop Affiliate";
}

function campaignMarket(value?: string): CampaignMarket {
    return ["US", "UK", "CA", "AU", "DE"].includes(value ?? "") ? (value as CampaignMarket) : "US";
}

function creatorTone(value: string): CreatorTone {
    const normalized = value.toLowerCase();
    if (normalized.includes("energetic")) return "Energetic";
    if (normalized.includes("expert")) return "Expert";
    if (normalized.includes("emotion")) return "Emotional";
    if (normalized.includes("minimal") || normalized.includes("raw")) return "Minimal / Raw UGC";
    if (normalized.includes("conversation")) return "Conversational";
    return "Natural";
}
