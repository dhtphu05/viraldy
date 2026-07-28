import type {
    CreativeAnalysis,
    CreativeReference,
    DnaTimelineMarker,
    DnaSection,
    DnaEvidence,
    KcaItem,
} from "@/features/creative-library/types/creative";

// Deterministic mock analysis generator used when a creative is analyzed at
// runtime. Values vary with duration and title so imported references get
// plausible, internally-consistent results.

function hashSeed(input: string): number {
    let h = 2166136261;
    for (let i = 0; i < input.length; i++) {
        h ^= input.charCodeAt(i);
        h = Math.imul(h, 16777619);
    }
    return Math.abs(h);
}

export function buildMockAnalysis(c: CreativeReference): CreativeAnalysis {
    const seed = hashSeed(c.id + c.title);
    const rand = (min: number, max: number) => min + ((seed % 1000) / 1000) * (max - min);
    const dur = Math.max(6, c.durationSec);

    const revealAt = Math.min(dur * 0.12, 3);
    const demoAt = Math.min(dur * 0.35, 10);
    const proofAt = Math.min(dur * 0.55, 18);
    const offerAt = Math.min(dur * 0.78, dur - 3);
    const ctaAt = Math.max(offerAt + 1.5, dur - 2);

    const dnaScore = Math.round(rand(62, 89));
    const confidence: CreativeAnalysis["confidence"] =
        dnaScore >= 80 ? "High" : dnaScore >= 70 ? "Medium" : "Low";

    const decision: CreativeAnalysis["decision"] =
        dnaScore >= 82
            ? "Strong reference"
            : dnaScore >= 70
              ? "Useful with adaptation"
              : "Weak product fit";

    const reason =
        decision === "Strong reference"
            ? `Fast product reveal at ${revealAt.toFixed(1)}s and a clear ${c.angle.toLowerCase()} structure. Safe to adapt with SKU-specific proof.`
            : decision === "Useful with adaptation"
              ? `${c.angle} structure works, but pacing and offer framing should be rewritten before your SKU can safely reuse it.`
              : `Format is not a strong fit for direct adaptation. Extract only the opening beat and rebuild the demo natively.`;

    const markers: DnaTimelineMarker[] = [
        {
            id: "m-hook",
            at: 0,
            label: "Hook",
            kind: "hook",
            note: `Opening line: “${c.hookExcerpt}”`,
        },
        {
            id: "m-reveal",
            at: revealAt,
            label: "Product reveal",
            kind: "reveal",
            note: "Product enters the frame.",
        },
        {
            id: "m-demo",
            at: demoAt,
            label: "Main demo",
            kind: "demo",
            note: "Handheld demonstration segment.",
        },
        {
            id: "m-proof",
            at: proofAt,
            label: "Proof",
            kind: "proof",
            note: "Before / after or transformation shot.",
        },
        {
            id: "m-offer",
            at: offerAt,
            label: "Offer",
            kind: "offer",
            note: "Price or discount stamp appears.",
        },
        { id: "m-cta", at: ctaAt, label: "CTA", kind: "cta", note: "Explicit tap-to-buy overlay." },
    ];

    const sections: DnaSection[] = [
        {
            id: "opening",
            title: "Opening",
            elements: [
                {
                    id: "o1",
                    label: "Hook type",
                    value: c.angle,
                    tone: "ok",
                    score: Math.round(rand(70, 90)),
                },
                { id: "o2", label: "Hook text", value: c.hookExcerpt },
                {
                    id: "o3",
                    label: "First 3-second structure",
                    value: "Face → problem → reveal",
                    tone: "ok",
                    score: Math.round(rand(72, 88)),
                },
                { id: "o4", label: "Face presence", value: "Yes, on-screen", tone: "ok" },
                {
                    id: "o5",
                    label: "Visual interruption",
                    value: "Hard cut on beat",
                    tone: "ok",
                    score: Math.round(rand(65, 85)),
                },
            ],
        },
        {
            id: "product",
            title: "Product",
            elements: [
                {
                    id: "p1",
                    label: "First product appearance",
                    value: `${revealAt.toFixed(1)}s`,
                    timestamp: revealAt,
                    tone: "ok",
                    score: 90,
                },
                {
                    id: "p2",
                    label: "Product screen time",
                    value: `${Math.round(rand(45, 72))}%`,
                    tone: "ok",
                    score: Math.round(rand(70, 85)),
                },
                { id: "p3", label: "Close-up quality", value: "Two clear close-ups", tone: "ok" },
                { id: "p4", label: "Demonstration type", value: "Handheld", tone: "ok" },
                {
                    id: "p5",
                    label: "Transformation visibility",
                    value: "Before/after in-frame",
                    tone: "ok",
                    score: Math.round(rand(72, 90)),
                },
            ],
        },
        {
            id: "narrative",
            title: "Narrative",
            elements: [
                { id: "n1", label: "Main angle", value: c.angle, tone: "ok" },
                { id: "n2", label: "Buyer problem", value: "Specific everyday pain in-category" },
                {
                    id: "n3",
                    label: "Emotional trigger",
                    value: "Relief + validation",
                    tone: "info",
                },
                { id: "n4", label: "Proof mechanism", value: "In-frame demonstration", tone: "ok" },
                { id: "n5", label: "Creator persona", value: c.brandOrCreator },
            ],
        },
        {
            id: "conversion",
            title: "Conversion",
            elements: [
                {
                    id: "c1",
                    label: "Offer clarity",
                    value: "Price + strikethrough",
                    tone: "ok",
                    score: Math.round(rand(60, 80)),
                },
                { id: "c2", label: "CTA", value: "Tap yellow basket", tone: "ok" },
                {
                    id: "c3",
                    label: "CTA timing",
                    value: `${ctaAt.toFixed(1)}s (${ctaAt > dur * 0.85 ? "late" : "on-time"})`,
                    tone: ctaAt > dur * 0.85 ? "warn" : "ok",
                    score: ctaAt > dur * 0.85 ? Math.round(rand(50, 65)) : Math.round(rand(70, 85)),
                },
                { id: "c4", label: "Product tag", value: "Present", tone: "ok" },
                { id: "c5", label: "TikTok Shop mention", value: "Yes, voiceover", tone: "ok" },
                {
                    id: "c6",
                    label: "Trust mechanism",
                    value: "Pinned social proof comment",
                    tone: "info",
                },
            ],
        },
        {
            id: "execution",
            title: "Execution",
            elements: [
                {
                    id: "e1",
                    label: "Video length",
                    value: `${dur}s`,
                    tone: dur > 55 ? "warn" : "ok",
                },
                {
                    id: "e2",
                    label: "Pacing",
                    value: "Fast, high cut rate",
                    score: Math.round(rand(72, 88)),
                },
                { id: "e3", label: "Scene count", value: String(Math.max(4, Math.round(dur / 4))) },
                {
                    id: "e4",
                    label: "On-screen text",
                    value: "Sans, high-contrast captions",
                    tone: "ok",
                },
                {
                    id: "e5",
                    label: "Voiceover / sound",
                    value: "Creator voice + trending audio",
                    tone: "info",
                },
            ],
        },
    ];

    const evidence: DnaEvidence[] = [
        {
            id: "ev-reveal",
            title: "Product reveal is early",
            timestamp: revealAt,
            detail: `The product enters the frame at ${revealAt.toFixed(1)}s, immediately after the opening beat.`,
            confidence: "High",
            action: "Keep the early reveal structure.",
        },
        {
            id: "ev-cta",
            title: ctaAt > dur * 0.85 ? "CTA lands late" : "CTA is well-timed",
            timestamp: ctaAt,
            detail:
                ctaAt > dur * 0.85
                    ? `Tap-to-buy overlay only appears in the last seconds of a ${dur}s video.`
                    : `CTA overlay lands with time for viewers to act.`,
            confidence: "Medium",
            action:
                ctaAt > dur * 0.85
                    ? "Move CTA overlay 4–6s earlier in your version."
                    : "Preserve the CTA placement for your adaptation.",
        },
        {
            id: "ev-audio",
            title: "Trending audio may carry rights risk",
            timestamp: dur - 1,
            detail: "Commercial track detected — verify licensing before Spark Ads.",
            confidence: "Medium",
            action: "Swap for a commercially cleared sound.",
        },
    ];

    const keep: KcaItem[] = [
        {
            id: "k1",
            label: "Fast product reveal",
            detail: `Bring the product into frame within ${Math.max(1, Math.round(revealAt))}s.`,
        },
        {
            id: "k2",
            label: `Clear ${c.angle.toLowerCase()} structure`,
            detail: "Pain → product → transformation.",
        },
        {
            id: "k3",
            label: "Handheld creator demonstration",
            detail: "Feels native to the platform.",
        },
        {
            id: "k4",
            label: "Before-and-after proof",
            detail: "Same angle, same setup, side-by-side.",
        },
    ];
    const change: KcaItem[] = [
        {
            id: "ch1",
            label: "Buyer persona",
            detail: "Rewrite the pain in your audience's language.",
        },
        {
            id: "ch2",
            label: "Product-specific proof",
            detail: "Show your SKU with real numbers or dimensions.",
        },
        {
            id: "ch3",
            label: "Offer framing",
            detail: "Lead with free shipping or bundle value, not the discount.",
        },
        {
            id: "ch4",
            label: "CTA timing",
            detail:
                ctaAt > dur * 0.85
                    ? "Move CTA earlier — around 60% mark."
                    : "Keep placement, refresh copy.",
        },
    ];
    const avoid: KcaItem[] = [
        {
            id: "a1",
            label: "Exact opening sentence",
            detail: "Do not reuse the creator's line verbatim.",
        },
        { id: "a2", label: "Creator identity", detail: "Do not imply endorsement." },
        {
            id: "a3",
            label: "Scene-by-scene sequence",
            detail: "Change scene order to avoid duplication flags.",
        },
        { id: "a4", label: "Commercial audio track", detail: "Rights risk on Spark Ads." },
    ];

    const transcript = [
        { at: 0, text: c.hookExcerpt },
        { at: revealAt, text: "Here's the product that solves it." },
        { at: demoAt, text: "Watch how it works in real time." },
        { at: proofAt, text: "And here's the result — same place, moments later." },
        { at: offerAt, text: "It's on sale right now on TikTok Shop." },
        { at: ctaAt, text: "Tap the yellow basket to grab yours." },
    ];

    return {
        creativeId: c.id,
        decision,
        reason,
        dnaScore,
        confidence,
        analysisType: "Full visual + transcript",
        markers,
        sections,
        evidence,
        keep,
        change,
        avoid,
        transcript,
    };
}

export const analysisSteps = [
    { key: "prep", label: "Preparing creative" },
    { key: "transcribe", label: "Transcribing audio" },
    { key: "ocr", label: "Reading on-screen text" },
    { key: "scenes", label: "Detecting scenes" },
    { key: "hook", label: "Identifying hook and product reveal" },
    { key: "elements", label: "Extracting creative elements" },
    { key: "adapt", label: "Building adaptation recommendation" },
];
