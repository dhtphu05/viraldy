import type { Campaign } from "@/shared/types";
import type {
    CampaignObjective,
    CampaignMarket,
    CampaignPlatform,
    CampaignPackStatus,
} from "@/features/campaigns/types/campaign";

export type CampaignSummaryExtras = {
    packId?: string;
    objective?: CampaignObjective;
    market?: CampaignMarket;
    platform?: CampaignPlatform;
    packStatus?: CampaignPackStatus;
    primaryAngle?: string;
    referenceCount?: number;
    hookCount?: number;
    deliverables?: number;
    updatedAt?: string;
};

export type SeedCampaign = Campaign & CampaignSummaryExtras;

const daysAgo = (d: number) => new Date(Date.now() - d * 86_400_000).toISOString();

export const campaigns: SeedCampaign[] = [
    {
        id: "c-1",
        packId: "pack-1",
        name: "Kitchen Organizer US Launch",
        product: "Compact Kitchen Organizer",
        status: "Live",
        activeAssets: 6,
        ugcScore: 82,
        gmv: 42180,
        nextAction: "Approve 2 revisions",
        objective: "TikTok Shop Affiliate",
        market: "US",
        platform: "TikTok Shop",
        packStatus: "Active",
        primaryAngle: "Small-space organization",
        referenceCount: 3,
        hookCount: 3,
        deliverables: 6,
        updatedAt: daysAgo(0.2),
    },
    {
        id: "c-2",
        packId: "pack-2",
        name: "Dog Mom Holiday Gift Campaign",
        product: "Personalized Dog Mom Blanket",
        status: "Live",
        activeAssets: 4,
        ugcScore: 74,
        gmv: 31460,
        nextAction: "Collect Spark codes",
        objective: "POD Gift Campaign",
        market: "US",
        platform: "TikTok Organic",
        packStatus: "Awaiting UGC",
        primaryAngle: "Gift reveal",
        referenceCount: 2,
        hookCount: 3,
        deliverables: 4,
        updatedAt: daysAgo(0.5),
    },
    {
        id: "c-3",
        packId: "pack-3",
        name: "Beauty Mirror Creator Test",
        product: "Portable Beauty Mirror",
        status: "Testing",
        activeAssets: 3,
        ugcScore: 61,
        gmv: 8420,
        nextAction: "Audit product page",
        objective: "Spark Ads Test",
        market: "US",
        platform: "TikTok Spark Ads",
        packStatus: "Creator production",
        primaryAngle: "Travel routine proof",
        referenceCount: 2,
        hookCount: 3,
        deliverables: 3,
        updatedAt: daysAgo(1.4),
    },
    {
        id: "c-4",
        packId: "pack-4",
        name: "Pet Hair Roller Affiliate Test",
        product: "Pet Hair Removal Roller",
        status: "Testing",
        activeAssets: 2,
        ugcScore: 68,
        gmv: 5210,
        nextAction: "Ship samples",
        objective: "TikTok Shop Affiliate",
        market: "US",
        platform: "TikTok Shop",
        packStatus: "Ready for creator",
        primaryAngle: "One-swipe demo",
        referenceCount: 2,
        hookCount: 3,
        deliverables: 2,
        updatedAt: daysAgo(2.1),
    },
];
