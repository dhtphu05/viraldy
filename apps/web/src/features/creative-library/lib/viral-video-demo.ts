import type { CreativeReference } from "@/features/creative-library/types/creative";
import { seedCreatives } from "@/features/creative-library/mocks/creatives";
import { isDemoVideoAvailable } from "@/shared/lib/optional-demo-media";

export const MAX_PRODUCT_IMAGE_BYTES = 10 * 1024 * 1024;
export const DEMO_SEARCH_DELAY_MS = 6_000;

const SUPPORTED_IMAGE_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

type ViralVideoMetrics = {
    videoViews: number;
    impressions: number;
    likes: number;
    comments: number;
    shares: number;
    clicks: number;
    orders: number;
    revenue: number;
    adSpend: number;
    roas: number;
    ctr: number;
    cvr: number;
    cpc: number;
    cpa: number;
};

export type ViralVideoRecommendation = CreativeReference & {
    fileName: string;
    rank: number;
    metrics: ViralVideoMetrics;
};

const LY_DEMO_VIDEOS: Array<CreativeReference & { fileName: string }> = [
    {
        id: "ly-01-before",
        fileName: "01_Before.mp4",
        title: "Không gian trước khi làm mới",
        hookExcerpt: "Một góc phòng quen thuộc trước khi bắt đầu thay đổi.",
        platform: "TikTok",
        durationSec: 10,
        mediaKind: "video",
        mediaUrl: "/product_ads/ly/01_Before.mp4",
        mediaAspectRatio: "9:16",
        brandOrCreator: "Video mẫu · Ly",
        angle: "Before-and-after",
        category: "Home & Kitchen",
        tags: ["demo", "before-after"],
        boardIds: [],
        analysisStatus: "ready",
        savedAt: "2026-09-28T00:00:00.000Z",
        thumbSeed: "ly-before",
    },
    {
        id: "ly-01",
        fileName: "01.mp4",
        title: "Thử bình giữ nhiệt LocknLock",
        hookExcerpt: "Cùng xem chiếc bình giữ nhiệt trong một trải nghiệm nhanh.",
        platform: "TikTok",
        durationSec: 29,
        mediaKind: "video",
        mediaUrl: "/product_ads/ly/01.mp4",
        mediaAspectRatio: "9:16",
        brandOrCreator: "Video mẫu · Ly",
        angle: "Product demonstration",
        category: "Home & Kitchen",
        tags: ["demo", "tumbler"],
        boardIds: [],
        analysisStatus: "ready",
        savedAt: "2026-09-28T00:00:00.000Z",
        thumbSeed: "ly-01",
    },
    {
        id: "ly-02",
        fileName: "02.mp4",
        title: "Cận cảnh ly giữ nhiệt",
        hookExcerpt: "Một góc quay gần làm nổi bật thiết kế và nắp ly.",
        platform: "TikTok",
        durationSec: 29,
        mediaKind: "video",
        mediaUrl: "/product_ads/ly/02.mp4",
        mediaAspectRatio: "9:16",
        brandOrCreator: "Video mẫu · Ly",
        angle: "Product demonstration",
        category: "Home & Kitchen",
        tags: ["demo", "close-up"],
        boardIds: [],
        analysisStatus: "ready",
        savedAt: "2026-09-28T00:00:00.000Z",
        thumbSeed: "ly-02",
    },
    {
        id: "ly-03",
        fileName: "03.mp4",
        title: "Chia sẻ trải nghiệm tại cửa hàng",
        hookExcerpt: "Một lời giới thiệu tự nhiên ngay trong lúc chọn sản phẩm.",
        platform: "TikTok",
        durationSec: 101,
        mediaKind: "video",
        mediaUrl: "/product_ads/ly/03.mp4",
        mediaAspectRatio: "9:16",
        brandOrCreator: "Video mẫu · Ly",
        angle: "Testimonial",
        category: "Home & Kitchen",
        tags: ["demo", "testimonial"],
        boardIds: [],
        analysisStatus: "ready",
        savedAt: "2026-09-28T00:00:00.000Z",
        thumbSeed: "ly-03",
    },
    {
        id: "ly-04",
        fileName: "04.mp4",
        title: "Pha đồ uống với ly hai lớp",
        hookExcerpt: "Một cách gần gũi để cho thấy chiếc ly được dùng hằng ngày.",
        platform: "TikTok",
        durationSec: 25,
        mediaKind: "video",
        mediaUrl: "/product_ads/ly/04.mp4",
        mediaAspectRatio: "9:16",
        brandOrCreator: "Video mẫu · Ly",
        angle: "Product demonstration",
        category: "Home & Kitchen",
        tags: ["demo", "drink"],
        boardIds: [],
        analysisStatus: "ready",
        savedAt: "2026-09-28T00:00:00.000Z",
        thumbSeed: "ly-04",
    },
    {
        id: "ly-05",
        fileName: "05.mp4",
        title: "Mở hộp bình giữ nhiệt màu pastel",
        hookExcerpt: "Cận cảnh màu sắc, kiểu dáng và những chi tiết nhỏ của sản phẩm.",
        platform: "TikTok",
        durationSec: 48,
        mediaKind: "video",
        mediaUrl: "/product_ads/ly/05.mp4",
        mediaAspectRatio: "9:16",
        brandOrCreator: "Video mẫu · Ly",
        angle: "Product demonstration",
        category: "Home & Kitchen",
        tags: ["demo", "unboxing"],
        boardIds: [],
        analysisStatus: "ready",
        savedAt: "2026-09-28T00:00:00.000Z",
        thumbSeed: "ly-05",
    },
];

const DEMO_CAMPAIGN_METRICS_BY_CREATIVE_ID = new Map<
    string,
    {
        rank: number;
        videoViews: number;
        impressions: number;
        likes: number;
        comments: number;
        shares: number;
        clicks: number;
        orders: number;
        revenue: number;
        adSpend: number;
    }
>([
    [
        "ly-01-before",
        {
            rank: 1,
            videoViews: 1_250_000,
            impressions: 1_500_000,
            likes: 87_000,
            comments: 3_200,
            shares: 8_700,
            clicks: 78_000,
            orders: 4_680,
            revenue: 304_200_000,
            adSpend: 66_000_000,
        },
    ],
    [
        "ly-01",
        {
            rank: 2,
            videoViews: 980_000,
            impressions: 1_400_000,
            likes: 58_800,
            comments: 2_450,
            shares: 6_400,
            clicks: 68_600,
            orders: 3_910,
            revenue: 242_420_000,
            adSpend: 57_720_000,
        },
    ],
    [
        "ly-02",
        {
            rank: 3,
            videoViews: 740_000,
            impressions: 1_000_000,
            likes: 44_400,
            comments: 1_850,
            shares: 4_300,
            clicks: 45_000,
            orders: 2_390,
            revenue: 133_840_000,
            adSpend: 35_221_050,
        },
    ],
    [
        "ly-03",
        {
            rank: 4,
            videoViews: 610_000,
            impressions: 800_000,
            likes: 36_600,
            comments: 1_540,
            shares: 3_800,
            clicks: 33_600,
            orders: 1_650,
            revenue: 222_000_000,
            adSpend: 63_428_570,
        },
    ],
    [
        "ly-04",
        {
            rank: 5,
            videoViews: 425_000,
            impressions: 750_000,
            likes: 25_500,
            comments: 1_100,
            shares: 2_700,
            clicks: 29_250,
            orders: 1_340,
            revenue: 60_300_000,
            adSpend: 19_451_610,
        },
    ],
    [
        "ly-05",
        {
            rank: 6,
            videoViews: 330_000,
            impressions: 650_000,
            likes: 19_800,
            comments: 900,
            shares: 2_000,
            clicks: 23_400,
            orders: 980,
            revenue: 210_700_000,
            adSpend: 75_250_000,
        },
    ],
]);

export function validateProductImages(files: File[]) {
    const accepted: File[] = [];
    const rejected: File[] = [];

    for (const file of files) {
        if (!SUPPORTED_IMAGE_TYPES.has(file.type) || file.size > MAX_PRODUCT_IMAGE_BYTES) {
            rejected.push(file);
        } else {
            accepted.push(file);
        }
    }

    return { accepted, rejected };
}

export async function getDemoVideoResults(): Promise<ViralVideoRecommendation[]> {
    const available = await Promise.all(
        LY_DEMO_VIDEOS.map((creative) => isDemoVideoAvailable(creative.mediaUrl!)),
    );
    const fallbackVideos = seedCreatives.filter(
        (creative) =>
            creative.mediaKind === "video" && creative.mediaUrl?.startsWith("/demo-media/"),
    );
    return LY_DEMO_VIDEOS.flatMap((localVideo, index) => {
        const campaign = DEMO_CAMPAIGN_METRICS_BY_CREATIVE_ID.get(localVideo.id);
        const creative = available[index] ? localVideo : fallbackVideos[index];
        if (!campaign || !creative?.mediaUrl) return [];
        const metrics: ViralVideoMetrics = {
            videoViews: campaign.videoViews,
            impressions: campaign.impressions,
            likes: campaign.likes,
            comments: campaign.comments,
            shares: campaign.shares,
            clicks: campaign.clicks,
            orders: campaign.orders,
            revenue: campaign.revenue,
            adSpend: campaign.adSpend,
            roas: campaign.revenue / campaign.adSpend,
            ctr: (campaign.clicks / campaign.impressions) * 100,
            cvr: (campaign.orders / campaign.clicks) * 100,
            cpc: campaign.adSpend / campaign.clicks,
            cpa: campaign.adSpend / campaign.orders,
        };
        return [
            {
                ...creative,
                fileName: creative.mediaUrl.split("/").at(-1)!,
                tags: [...creative.tags, "demo"],
                rank: campaign.rank,
                metrics,
            },
        ];
    }).sort((left, right) => left.rank - right.rank);
}
