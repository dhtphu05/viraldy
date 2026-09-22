import overviewIcon from "./navigation/overview.png";
import productionRunIcon from "./navigation/production_run.png";
import creativeLibraryIcon from "./navigation/creative_library.png";
import tiktokScorerIcon from "./navigation/tiktok_scorer.png";
import campaignsIcon from "./navigation/campaigns.png";
import ugcReviewIcon from "./navigation/ugc_review.png";
import performanceIcon from "./navigation/performance.png";
import productsIcon from "./navigation/products.png";
import workspaceIcon from "./shell/workspace.png";
import notificationsIcon from "./shell/notifications.png";
import searchIcon from "./shell/search.png";
import accountIcon from "./shell/account.png";
import logoutIcon from "./shell/logout.png";
import collapseSidebarIcon from "./shell/collapse_sidebar.png";
import expandSidebarIcon from "./shell/expand_sidebar.png";
import analyzeCreativeIcon from "./actions/analyze_creative.png";
import startProductionRunIcon from "./actions/start_production_run.png";
import newCampaignIcon from "./actions/new_campaign.png";
import importCreativeIcon from "./actions/import_creative.png";
import importProductIcon from "./actions/import_product.png";
import importPerformanceIcon from "./actions/import_performance.png";
import uploadVideoIcon from "./actions/upload_video.png";
import createVariantsIcon from "./actions/create_variants.png";
import requestSparkCodeIcon from "./actions/request_spark_code.png";
import sendRevisionsIcon from "./actions/send_revisions.png";
import shipSamplesIcon from "./actions/ship_samples.png";
import creativeDnaIcon from "./intelligence/creative_dna.png";
import campaignPackIcon from "./intelligence/campaign_pack.png";
import creatorIcon from "./intelligence/creator.png";
import productCatalogIcon from "./intelligence/product_catalog.png";
import videoAssetIcon from "./intelligence/video_asset.png";
import ugcAssetIcon from "./intelligence/ugc_asset.png";
import performanceReportIcon from "./intelligence/performance_report.png";
import evidenceIcon from "./intelligence/evidence.png";
import patternIcon from "./intelligence/pattern.png";
import hookIcon from "./intelligence/hook.png";
import angleIcon from "./intelligence/angle.png";
import buyerPersonaIcon from "./intelligence/buyer_persona.png";
import scaleIcon from "./decisions/scale.png";
import fixIcon from "./decisions/fix.png";
import rehireIcon from "./decisions/rehire.png";
import stopTestingIcon from "./decisions/stop_testing.png";
import approvedIcon from "./status/approved.png";
import warningIcon from "./status/warning.png";
import blockedIcon from "./status/blocked.png";

export const VIRALDY_ICONS = {
    overview: overviewIcon,
    productionRun: productionRunIcon,
    creativeLibrary: creativeLibraryIcon,
    tiktokScorer: tiktokScorerIcon,
    campaigns: campaignsIcon,
    ugcReview: ugcReviewIcon,
    performance: performanceIcon,
    products: productsIcon,
    workspace: workspaceIcon,
    notifications: notificationsIcon,
    search: searchIcon,
    account: accountIcon,
    logout: logoutIcon,
    collapseSidebar: collapseSidebarIcon,
    expandSidebar: expandSidebarIcon,
    analyzeCreative: analyzeCreativeIcon,
    startProductionRun: startProductionRunIcon,
    newCampaign: newCampaignIcon,
    importCreative: importCreativeIcon,
    importProduct: importProductIcon,
    importPerformance: importPerformanceIcon,
    uploadVideo: uploadVideoIcon,
    createVariants: createVariantsIcon,
    requestSparkCode: requestSparkCodeIcon,
    sendRevisions: sendRevisionsIcon,
    shipSamples: shipSamplesIcon,
    creativeDna: creativeDnaIcon,
    campaignPack: campaignPackIcon,
    creator: creatorIcon,
    productCatalog: productCatalogIcon,
    videoAsset: videoAssetIcon,
    ugcAsset: ugcAssetIcon,
    performanceReport: performanceReportIcon,
    evidence: evidenceIcon,
    pattern: patternIcon,
    hook: hookIcon,
    angle: angleIcon,
    buyerPersona: buyerPersonaIcon,
    scale: scaleIcon,
    fix: fixIcon,
    rehire: rehireIcon,
    stopTesting: stopTestingIcon,
    approved: approvedIcon,
    warning: warningIcon,
    blocked: blockedIcon,
} as const;

export type ViraldyIconName = keyof typeof VIRALDY_ICONS;

export const VIRALDY_NAVIGATION_ICONS = {
    "/dashboard": "overview",
    "/mvp": "productionRun",
    "/creative-library": "creativeLibrary",
    "/tiktok-scorer": "tiktokScorer",
    "/campaigns": "campaigns",
    "/ugc-review": "ugcReview",
    "/performance": "performanceReport",
    "/products": "productCatalog",
} as const satisfies Record<string, ViraldyIconName>;

export const VIRALDY_ACTION_ICONS = {
    analyzeCreative: "analyzeCreative",
    startProductionRun: "startProductionRun",
    newCampaign: "newCampaign",
    importCreative: "importCreative",
    importProduct: "importProduct",
    importPerformance: "importPerformance",
    uploadVideo: "uploadVideo",
    createVariants: "createVariants",
    requestSparkCode: "requestSparkCode",
    sendRevisions: "sendRevisions",
    shipSamples: "shipSamples",
} as const satisfies Record<string, ViraldyIconName>;

export const VIRALDY_DECISION_ICONS = {
    Scale: "scale",
    Fix: "fix",
    Rehire: "rehire",
    "Stop testing": "stopTesting",
    Stop: "stopTesting",
} as const satisfies Record<string, ViraldyIconName>;

export const VIRALDY_STATUS_ICONS = {
    approved: "approved",
    warning: "warning",
    blocked: "blocked",
} as const satisfies Record<string, ViraldyIconName>;
