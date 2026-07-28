import type { CreativeAnalysis } from "@/features/creative-library/types/creative";

const analysis1: CreativeAnalysis = {
    creativeId: "cr-1",
    decision: "Strong reference",
    reason: "Fast product reveal, strong problem–solution structure, and a relatable creator opening. Adaptable to any 'hidden mess' product with minimal changes.",
    dnaScore: 88,
    confidence: "High",
    analysisType: "Full visual + transcript",
    markers: [
        {
            id: "m1",
            at: 0,
            label: "Hook",
            kind: "hook",
            note: "POV problem statement, no product yet.",
        },
        {
            id: "m2",
            at: 1.8,
            label: "Product reveal",
            kind: "reveal",
            note: "Organizer enters the frame just after the pain point lands.",
        },
        {
            id: "m3",
            at: 6.4,
            label: "Main demo",
            kind: "demo",
            note: "Handheld demonstration of the sliding mechanism.",
        },
        { id: "m4", at: 12.1, label: "Proof", kind: "proof", note: "Before/after cabinet shot." },
        {
            id: "m5",
            at: 16.9,
            label: "Offer",
            kind: "offer",
            note: "Price tag stamp with strikethrough.",
        },
        { id: "m6", at: 19.5, label: "CTA", kind: "cta", note: "Yellow-basket tap animation." },
        {
            id: "m7",
            at: 21.2,
            label: "Risk",
            kind: "risk",
            note: "Music sample flagged in a comment thread.",
        },
    ],
    sections: [
        {
            id: "opening",
            title: "Opening",
            elements: [
                { id: "o1", label: "Hook type", value: "POV problem", tone: "ok", score: 84 },
                {
                    id: "o2",
                    label: "Hook text",
                    value: "POV: you finally open the cabinet you've been avoiding",
                },
                {
                    id: "o3",
                    label: "First 3-second structure",
                    value: "Face → problem → reveal",
                    tone: "ok",
                    score: 82,
                },
                { id: "o4", label: "Face presence", value: "Yes, on-screen", tone: "ok" },
                {
                    id: "o5",
                    label: "Visual interruption",
                    value: "Cabinet door slam cut",
                    tone: "ok",
                    score: 78,
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
                    value: "1.8s",
                    timestamp: 1.8,
                    tone: "ok",
                    score: 92,
                },
                { id: "p2", label: "Product screen time", value: "62%", score: 78, tone: "ok" },
                {
                    id: "p3",
                    label: "Close-up quality",
                    value: "Two clear close-ups",
                    tone: "ok",
                    score: 80,
                },
                {
                    id: "p4",
                    label: "Demonstration type",
                    value: "Handheld installation",
                    tone: "ok",
                },
                {
                    id: "p5",
                    label: "Transformation visibility",
                    value: "Before/after in-frame",
                    tone: "ok",
                    score: 86,
                },
            ],
        },
        {
            id: "narrative",
            title: "Narrative",
            elements: [
                { id: "n1", label: "Main angle", value: "Problem–solution", tone: "ok" },
                { id: "n2", label: "Buyer problem", value: "Cluttered under-sink cabinet" },
                { id: "n3", label: "Emotional trigger", value: "Shame + relief", tone: "info" },
                {
                    id: "n4",
                    label: "Proof mechanism",
                    value: "In-frame before/after",
                    tone: "ok",
                    score: 84,
                },
                { id: "n5", label: "Creator persona", value: "Relatable home creator, 30s" },
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
                    score: 74,
                },
                { id: "c2", label: "CTA", value: "Tap yellow basket", tone: "ok" },
                {
                    id: "c3",
                    label: "CTA timing",
                    value: "19.5s (late in 22s video)",
                    tone: "warn",
                    score: 58,
                },
                { id: "c4", label: "Product tag", value: "Present", tone: "ok" },
                { id: "c5", label: "TikTok Shop mention", value: "Yes, voiceover", tone: "ok" },
                {
                    id: "c6",
                    label: "Trust mechanism",
                    value: "Comment pin: 'my second one'",
                    tone: "info",
                },
            ],
        },
        {
            id: "execution",
            title: "Execution",
            elements: [
                { id: "e1", label: "Video length", value: "22s", tone: "ok" },
                { id: "e2", label: "Pacing", value: "Fast, 7 scenes", score: 82 },
                { id: "e3", label: "Scene count", value: "7" },
                {
                    id: "e4",
                    label: "On-screen text",
                    value: "Sans, high-contrast, 3 captions",
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
    ],
    evidence: [
        {
            id: "ev-1",
            title: "Product reveal is early",
            timestamp: 1.8,
            detail: "Product enters the frame immediately after the opening problem statement.",
            confidence: "High",
            action: "Keep the early reveal structure.",
        },
        {
            id: "ev-2",
            title: "CTA lands late",
            timestamp: 19.5,
            detail: "The tap-to-buy overlay only appears in the last 3 seconds of a 22s video.",
            confidence: "Medium",
            action: "Move CTA overlay to 12–14s for your version.",
        },
        {
            id: "ev-3",
            title: "Sound choice may be a rights risk",
            timestamp: 21.2,
            detail: "Trending audio is a commercial track — verify licensing before Spark Ads.",
            confidence: "Medium",
            action: "Swap for a commercially cleared sound.",
        },
    ],
    keep: [
        {
            id: "k1",
            label: "Fast product reveal",
            detail: "Bring the product into frame within 2 seconds.",
        },
        {
            id: "k2",
            label: "Clear problem–solution structure",
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
            detail: "Same angle, same cabinet, side-by-side.",
        },
    ],
    change: [
        {
            id: "ch1",
            label: "Buyer persona",
            detail: "Your audience skews younger — rewrite the pain in their language.",
        },
        {
            id: "ch2",
            label: "Product-specific proof",
            detail: "Show your organizer with your SKU's cabinet dimensions.",
        },
        {
            id: "ch3",
            label: "Offer framing",
            detail: "Lead with 'free shipping' instead of the strikethrough.",
        },
        { id: "ch4", label: "CTA timing", detail: "Move CTA to 12–14s." },
    ],
    avoid: [
        {
            id: "a1",
            label: "Exact opening sentence",
            detail: "Do not reuse '@tidy.emma's line verbatim.",
        },
        { id: "a2", label: "Creator identity", detail: "Do not imply endorsement." },
        {
            id: "a3",
            label: "Scene-by-scene sequence",
            detail: "Change scene order to avoid duplication flags.",
        },
        { id: "a4", label: "Commercial audio track", detail: "Rights risk on Spark Ads." },
    ],
    transcript: [
        { at: 0, text: "POV: you finally open the cabinet you've been avoiding for 6 months." },
        { at: 2, text: "This organizer just slides right in." },
        { at: 6, text: "Watch — it hooks under the shelf, no drilling." },
        { at: 12, text: "And here's the same cabinet, 30 seconds later." },
        { at: 17, text: "It's on sale right now on TikTok Shop." },
        { at: 20, text: "Tap the yellow basket to grab yours." },
    ],
};

// Reuse-and-vary helper so we don't repeat massive objects
function variant(base: CreativeAnalysis, overrides: Partial<CreativeAnalysis>): CreativeAnalysis {
    return { ...base, ...overrides };
}

const analysis2 = variant(analysis1, {
    creativeId: "cr-2",
    decision: "Useful with adaptation",
    reason: "Emotional reaction is strong, but the exact scene and creator opening should not be copied. Adapt the structure to your gift SKU.",
    dnaScore: 82,
    confidence: "Medium",
    analysisType: "Full visual + transcript",
});

const analysis3 = variant(analysis1, {
    creativeId: "cr-3",
    decision: "Useful with adaptation",
    reason: "Day-in-the-life format works, but product screen-time is low and CTA is missing.",
    dnaScore: 71,
    confidence: "Medium",
});

const analysis4 = variant(analysis1, {
    creativeId: "cr-4",
    decision: "Strong reference",
    reason: "Clean before/after with strong claim. Adapt claim to your SKU's real numbers.",
    dnaScore: 79,
    confidence: "High",
});

const analysis5 = variant(analysis1, {
    creativeId: "cr-5",
    decision: "Useful with adaptation",
    reason: "Long-form testimonial. Trim to 30s and lead with the outcome.",
    dnaScore: 74,
    confidence: "Medium",
});

const analysis6 = variant(analysis1, {
    creativeId: "cr-6",
    decision: "Weak product fit",
    reason: "Comparison mentions competitor SKUs — legal risk if adapted directly.",
    dnaScore: 66,
    confidence: "Low",
});

const analysis7 = variant(analysis1, {
    creativeId: "cr-7",
    decision: "Strong reference",
    reason: "Fast pacing, high hook retention, adaptable to any counter-clutter SKU.",
    dnaScore: 85,
    confidence: "High",
});

export const seedAnalyses: Record<string, CreativeAnalysis> = {
    "cr-1": analysis1,
    "cr-2": analysis2,
    "cr-3": analysis3,
    "cr-4": analysis4,
    "cr-5": analysis5,
    "cr-6": analysis6,
    "cr-7": analysis7,
};
