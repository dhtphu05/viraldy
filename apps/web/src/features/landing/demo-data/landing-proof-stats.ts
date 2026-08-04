export interface LandingProofMetrics {
    creativeSignalsAnalyzed: number;
    videosReviewed: number;
    productsAnalyzed: number;
    creativeDirectionsGenerated: number;
    videosAnalyzedToday: number;
}

export const landingMetrics: LandingProofMetrics = {
    creativeSignalsAnalyzed: 142850,
    videosReviewed: 18412,
    productsAnalyzed: 3491,
    creativeDirectionsGenerated: 10473,
    videosAnalyzedToday: 412,
};

export function getFormattedMetrics() {
    return {
        creativeSignalsAnalyzed: landingMetrics.creativeSignalsAnalyzed.toLocaleString(),
        videosReviewed: landingMetrics.videosReviewed.toLocaleString(),
        productsAnalyzed: landingMetrics.productsAnalyzed.toLocaleString(),
        creativeDirectionsGenerated: landingMetrics.creativeDirectionsGenerated.toLocaleString(),
        videosAnalyzedToday: landingMetrics.videosAnalyzedToday.toLocaleString(),
        currentTime: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
}
