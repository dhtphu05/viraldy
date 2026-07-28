import type { CampaignTemplate } from "@/features/campaigns/types/campaign";

export const campaignTemplates: CampaignTemplate[] = [
    {
        id: "tpl-shop-test",
        name: "TikTok Shop Product Test",
        description:
            "Validate a product with a small creator pool. Focus on hook variety and quick conversion signals.",
        objective: "Organic Product Test",
        platform: "TikTok Shop",
        creatorType: "Micro creator",
        creatorTone: "Natural",
        suggestedAspectRatio: "9:16",
        suggestedDurationSec: 30,
    },
    {
        id: "tpl-affiliate",
        name: "Creator Affiliate Campaign",
        description:
            "Ship samples to affiliates and let them run their own creative interpretation with your product.",
        objective: "TikTok Shop Affiliate",
        platform: "TikTok Shop",
        creatorType: "Mid-tier creator",
        creatorTone: "Conversational",
        suggestedAspectRatio: "9:16",
        suggestedDurationSec: 45,
    },
    {
        id: "tpl-spark",
        name: "UGC for Spark Ads",
        description:
            "Structured UGC brief built to become Spark-authorized paid creative. Includes rights and Spark request.",
        objective: "Spark Ads Test",
        platform: "TikTok Spark Ads",
        creatorType: "UGC-only",
        creatorTone: "Minimal / Raw UGC",
        suggestedAspectRatio: "9:16",
        suggestedDurationSec: 22,
    },
    {
        id: "tpl-pod",
        name: "POD Personalized Gift",
        description:
            "Gift-reaction structure for personalized print-on-demand items. Emphasizes recipient emotion.",
        objective: "POD Gift Campaign",
        platform: "TikTok Organic",
        creatorType: "Lifestyle",
        creatorTone: "Emotional",
        suggestedAspectRatio: "9:16",
        suggestedDurationSec: 35,
    },
    {
        id: "tpl-drop-demo",
        name: "Dropshipping Product Demo",
        description:
            "Problem, quick demo, and proof. Built for scrollable, replayable product discovery.",
        objective: "Dropshipping Product Demo",
        platform: "TikTok Organic",
        creatorType: "Product expert",
        creatorTone: "Energetic",
        suggestedAspectRatio: "9:16",
        suggestedDurationSec: 28,
    },
    {
        id: "tpl-seeding",
        name: "Organic Creator Seeding",
        description:
            "No-cost seeding for a batch of micro-creators. Loose brief, hero product moments required.",
        objective: "Organic Product Test",
        platform: "TikTok Organic",
        creatorType: "Micro creator",
        creatorTone: "Natural",
        suggestedAspectRatio: "9:16",
        suggestedDurationSec: 30,
    },
];
