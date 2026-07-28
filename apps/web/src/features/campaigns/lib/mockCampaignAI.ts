import type {
    AngleConcept,
    CampaignPack,
    CampaignObjective,
    CampaignPlatform,
    ClaimWarning,
    Hook,
    HookType,
    ScriptBlock,
    ScriptBlockKind,
    StoryboardScene,
} from "@/features/campaigns/types/campaign";
import { angleTemplates } from "@/features/campaigns/mocks/campaignAngles";
import { hookTemplates } from "@/features/campaigns/mocks/campaignHooks";
import { sceneTemplates } from "@/features/campaigns/mocks/campaignScenes";
import { seedProducts } from "@/features/products/data/products";

// Simple deterministic id using a counter seeded by input
function makeId(prefix: string, seed: string, i = 0) {
    let h = 0;
    for (let k = 0; k < seed.length; k++) h = (h * 31 + seed.charCodeAt(k)) | 0;
    return `${prefix}-${Math.abs(h).toString(36)}${i ? `-${i}` : ""}`;
}

function productContext(productId?: string) {
    const p = seedProducts.find((x) => x.id === productId);
    return {
        name: p?.name ?? "your product",
        category: p?.category ?? "product",
        environment:
            p?.category === "Home & Kitchen" || p?.category === "Home Organization"
                ? "kitchen"
                : p?.category === "Beauty"
                  ? "vanity"
                  : p?.category === "Pet"
                    ? "living room"
                    : p?.category === "POD Gifts"
                      ? "living room"
                      : "home",
        problem:
            p?.category === "Beauty"
                ? "morning routine"
                : p?.category === "Pet"
                  ? "pet hair on the couch"
                  : p?.category === "POD Gifts"
                    ? "finding a personal gift"
                    : "everyday clutter",
    };
}

const ADAPTATION_DELAY = 700;
const GENERATION_DELAY = 900;

export function delay<T>(value: T, ms = GENERATION_DELAY): Promise<T> {
    return new Promise((r) => setTimeout(() => r(value), ms));
}

export function generateAdaptation(productId: string | undefined, sourceHook: string, variant = 0) {
    const ctx = productContext(productId);
    const alt = variant % 2 === 0;
    return delay(
        {
            sourceHook: sourceHook || "I didn't expect this small tool to fix my messy counter.",
            sourceAngle: "Small-space organization",
            sourceDemo: "Immediate before-and-after in the same frame",
            adaptedHook: alt
                ? `My ${ctx.environment} finally stopped looking chaotic.`
                : `I stopped fighting my ${ctx.environment} and started using ${ctx.name}.`,
            adaptedAngle: `Focused on the specific buyer problem: ${ctx.problem}`,
            adaptedDemo: `Show the ${ctx.environment} today, add ${ctx.name}, show the outcome in the same frame.`,
            whyChanged:
                "Retained the narrative structure and early reveal, but the buyer problem, environment, and proof mechanism are specific to this product.",
            keep: [
                "Narrative structure — problem, reveal, demo, proof",
                "Early product reveal in the first 5 seconds",
                "Handheld creator style",
                "Visible visual transformation",
            ],
            change: [
                `Buyer persona to match ${ctx.category} owners`,
                `Buyer problem to ${ctx.problem}`,
                `Proof mechanism specific to ${ctx.name}`,
                "Offer wording and CTA",
                `Environment (${ctx.environment})`,
            ],
            avoid: [
                "Exact wording from the source video",
                "Creator identity references",
                "Competitor product names",
                "Exact shot sequence",
                "Brand-specific claims from the source",
            ],
        },
        ADAPTATION_DELAY,
    );
}

export function generateAngles(
    productId: string | undefined,
    seed: string,
): Promise<AngleConcept[]> {
    const ctx = productContext(productId);
    const pool = angleTemplates.slice(0, 5);
    return delay(
        pool.map((t, i) => ({
            ...t,
            id: makeId("angle", `${seed}-${i}`),
            buyerProblem: `${t.buyerProblem} In this case: ${ctx.problem}.`,
            productProof: `${t.productProof}. Applied to ${ctx.name}.`,
        })),
    );
}

export function generateOneAngle(
    productId: string | undefined,
    existing: AngleConcept[],
    seed: string,
): Promise<AngleConcept> {
    const used = new Set(existing.map((a) => a.name));
    const pick =
        angleTemplates.find((t) => !used.has(t.name)) ??
        angleTemplates[existing.length % angleTemplates.length];
    const ctx = productContext(productId);
    return delay({
        ...pick,
        id: makeId("angle", `${seed}-new-${existing.length}`),
        buyerProblem: `${pick.buyerProblem} In this case: ${ctx.problem}.`,
        productProof: `${pick.productProof}. Applied to ${ctx.name}.`,
    });
}

function fill(text: string, ctx: ReturnType<typeof productContext>) {
    return text
        .replaceAll("{product}", ctx.name)
        .replaceAll("{environment}", ctx.environment)
        .replaceAll("{problem_area}", ctx.environment + " drawer")
        .replaceAll("{problem}", ctx.problem)
        .replaceAll("{category}", ctx.category)
        .replaceAll("{routine}", ctx.problem)
        .replaceAll("{identity_moment}", "cares about the details")
        .replaceAll("{gift_recipient}", "mom")
        .replaceAll("{occasion}", "birthday");
}

export function generateHooks(
    productId: string | undefined,
    angle: AngleConcept | undefined,
    seed: string,
): Promise<Hook[]> {
    const ctx = productContext(productId);
    const types: HookType[] = [
        "Problem-first",
        "Curiosity",
        "Product reveal",
        "Social proof",
        "Comparison",
        "Emotional identity",
        "Gift reaction",
    ];
    const out: Hook[] = [];
    types.forEach((type, ti) => {
        hookTemplates[type].forEach((t, hi) => {
            out.push({
                ...t,
                id: makeId("hook", `${seed}-${ti}-${hi}`),
                text: fill(t.text, ctx),
                sourceAngleId: angle?.id,
            });
        });
    });
    return delay(out);
}

export function generateOneHook(
    productId: string | undefined,
    type: HookType,
    existing: Hook[],
    seed: string,
): Promise<Hook> {
    const ctx = productContext(productId);
    const templates = hookTemplates[type];
    const t = templates[existing.filter((h) => h.type === type).length % templates.length];
    return delay({
        ...t,
        id: makeId("hook", `${seed}-${type}-${existing.length}`),
        text: fill(t.text, ctx),
    });
}

export function generateScript(
    productId: string | undefined,
    angle: AngleConcept | undefined,
    hook: Hook | undefined,
    seed: string,
): Promise<ScriptBlock[]> {
    const ctx = productContext(productId);
    const kinds: ScriptBlockKind[] = [
        "Hook",
        "Buyer Problem",
        "Product Introduction",
        "Demo",
        "Proof",
        "Benefits",
        "Offer",
        "CTA",
    ];
    const map: Record<ScriptBlockKind, string> = {
        Hook: hook?.text ?? `My ${ctx.environment} finally stopped looking chaotic.`,
        "Buyer Problem": `Every day I dealt with ${ctx.problem} and just accepted it as normal.`,
        "Product Introduction": `Then I tried ${ctx.name}. Same ${ctx.environment}, small setup.`,
        Demo: `Here is what it looks like in real use — no cuts, one take.`,
        Proof: `And here is the result, from the same angle, one week later.`,
        Benefits: `The three things that actually changed: less time, less mess, and I stopped avoiding this space.`,
        Offer: `It's available in TikTok Shop right now with the offer shown on the product tag.`,
        CTA: `Tap the product tag if you want the exact one I'm using.`,
    };
    return delay(
        kinds.map((k, i) => ({
            id: makeId("blk", `${seed}-${k}-${i}`),
            kind: k,
            text: map[k],
        })),
    );
}

export function regenerateScriptSection(
    productId: string | undefined,
    block: ScriptBlock,
    seed: string,
): Promise<ScriptBlock> {
    const ctx = productContext(productId);
    const variants: Record<ScriptBlockKind, string[]> = {
        Hook: [
            `My ${ctx.environment} looked clean until I opened one drawer.`,
            `I stopped fighting my ${ctx.environment} and just used this.`,
        ],
        "Buyer Problem": [
            `The problem wasn't the space. It was that I never gave it a system.`,
            `I kept buying containers hoping the mess would fix itself.`,
        ],
        "Product Introduction": [
            `${ctx.name} is the one thing I set up and forgot about.`,
            `${ctx.name} slides in without changing anything else in the ${ctx.environment}.`,
        ],
        Demo: [
            `One shot, one take, no cuts — this is the actual setup.`,
            `Watch me install it and start using it in real time.`,
        ],
        Proof: [
            `Same angle, one week later. Nothing else changed.`,
            `Here is the same view after a full week of normal use.`,
        ],
        Benefits: [
            `Less time cleaning, no argument about where things live.`,
            `It stayed organized because the system does the work.`,
        ],
        Offer: [
            `Available in TikTok Shop right now — the pinned tag has everything.`,
            `The offer on the tag reflects what I paid, no gimmick.`,
        ],
        CTA: [
            `Tap the tag to see it in the shop.`,
            `Check the product tag before it sells out again.`,
        ],
    };
    const options = variants[block.kind];
    let h = 0;
    for (let k = 0; k < seed.length; k++) h = (h + seed.charCodeAt(k)) | 0;
    const pick = options[Math.abs(h + block.text.length) % options.length];
    return delay({ ...block, text: pick });
}

export function generateStoryboard(
    productId: string | undefined,
    seed: string,
): Promise<StoryboardScene[]> {
    return delay(
        sceneTemplates.map((s, i) => ({
            ...s,
            id: makeId("scene", `${seed}-${s.label}-${i}`),
        })),
    );
}

export function regenerateStoryboardScene(
    scene: StoryboardScene,
    seed: string,
): Promise<StoryboardScene> {
    const options: Record<string, Partial<StoryboardScene>> = {
        Hook: {
            visualDirection: "POV walking into the space with the problem visible.",
            framing: "Handheld, 45° down angle",
        },
        Problem: {
            visualDirection: "Static wide shot of the environment showing the mess.",
            framing: "Wide, tripod feel",
        },
        "Product Reveal": {
            visualDirection: "Hard cut to product held at reveal height in the same environment.",
            framing: "Center frame, product hero",
        },
        Demo: {
            visualDirection: "Over-the-shoulder single-take use of the product.",
            framing: "Over-shoulder",
        },
    };
    const alt = options[scene.label];
    let h = 0;
    for (let k = 0; k < seed.length; k++) h = (h + seed.charCodeAt(k)) | 0;
    const variant = h % 2 === 0;
    return delay({
        ...scene,
        visualDirection: alt?.visualDirection ?? scene.visualDirection,
        framing: variant ? (alt?.framing ?? scene.framing) : scene.framing,
    });
}

const RISKY_PATTERNS: { rx: RegExp; risk: ClaimWarning["risk"]; reason: string }[] = [
    { rx: /guarantee/i, risk: "High", reason: "Guarantee claims require legal review." },
    {
        rx: /best ever|best in the world/i,
        risk: "Medium",
        reason: "Superlative claims should be qualified.",
    },
    {
        rx: /cure|heal|treat/i,
        risk: "High",
        reason: "Health claims are restricted on TikTok Shop and Meta.",
    },
    { rx: /passive income|get rich/i, risk: "High", reason: "Income claims are restricted." },
    {
        rx: /overnight|instant results/i,
        risk: "Medium",
        reason: "Speed claims should reflect realistic outcomes.",
    },
    {
        rx: /free shipping worldwide/i,
        risk: "Medium",
        reason: "Shipping claims should reflect actual policy.",
    },
];

export function checkClaims(text: string): ClaimWarning[] {
    const out: ClaimWarning[] = [];
    RISKY_PATTERNS.forEach((p, i) => {
        if (p.rx.test(text)) {
            out.push({
                id: `w-${i}-${text.length}`,
                phrase: text.match(p.rx)?.[0] ?? "claim",
                risk: p.risk,
                reason: p.reason,
            });
        }
    });
    return out;
}

export function generateCreatorBrief(pack: CampaignPack, productName: string): string {
    const primaryAngle = pack.angleOptions.find((a) => a.id === pack.primaryAngleId);
    const selectedHooks = pack.hookOptions.filter((h) => pack.selectedHookIds.includes(h.id));
    const script = pack.script.map((b) => `## ${b.kind}\n${b.text}`).join("\n\n");
    const storyboard = pack.storyboard
        .map(
            (s, i) =>
                `${i + 1}. ${s.label} (${s.durationRange})\n   Visual: ${s.visualDirection}\n   Line: ${s.spokenLine}`,
        )
        .join("\n");
    return [
        `CREATOR BRIEF — ${pack.name}`,
        ``,
        `Product: ${productName}`,
        `Goal: ${pack.objective}`,
        `Market: ${pack.market}`,
        `Platform: ${pack.platform}`,
        `Creator tone: ${pack.creatorTone}`,
        ``,
        `MAIN ANGLE`,
        primaryAngle ? `${primaryAngle.name} — ${primaryAngle.buyerProblem}` : "Not selected",
        ``,
        `HOOKS`,
        selectedHooks.map((h, i) => `${i + 1}. ${h.text}`).join("\n") || "Not selected",
        ``,
        `SCRIPT`,
        script,
        ``,
        `STORYBOARD`,
        storyboard,
        ``,
        `CTA`,
        pack.cta.primary,
        ``,
        `DO`,
        pack.cta.claimsAllowed.map((c) => `• ${c}`).join("\n") || "• Use natural language",
        ``,
        `DON'T`,
        pack.cta.claimsToAvoid.map((c) => `• ${c}`).join("\n") || "• Avoid unverified claims",
        ``,
        `DELIVERABLES`,
        `${pack.deliverables.numberOfVideos} × ${pack.deliverables.targetDurationSec}s ${pack.deliverables.aspectRatio}`,
        `Raw footage: ${pack.deliverables.rawFootageRequired ? "yes" : "no"}`,
        `Revisions: ${pack.deliverables.revisionRounds}`,
        pack.deliverables.dueDate ? `Due: ${pack.deliverables.dueDate}` : "",
        ``,
        `RIGHTS`,
        `TikTok Organic: ${pack.rights.tiktokOrganic ? "yes" : "no"}`,
        `TikTok Spark Ads: ${pack.rights.tiktokSpark ? "yes" : "no"}`,
        `Meta Ads: ${pack.rights.metaAds ? "yes" : "no"}`,
        `Duration: ${pack.rights.usageDurationDays} days`,
        pack.spark.required
            ? `Spark authorization required for ${pack.spark.durationDays} days.`
            : `No Spark authorization required.`,
    ]
        .filter(Boolean)
        .join("\n");
}

export function defaultObjectiveDefaults(objective: CampaignObjective, platform: CampaignPlatform) {
    const rightsBase = {
        tiktokOrganic: true,
        tiktokSpark: platform.includes("Spark"),
        metaAds: platform.includes("Meta"),
        website: false,
        email: false,
        editingAllowed: true,
        rawFootageIncluded: false,
        usageDurationDays: 180,
        creatorAttribution: true,
    };
    const sparkRequired = platform.includes("Spark") || objective === "Spark Ads Test";
    return {
        rights: rightsBase,
        spark: {
            required: sparkRequired,
            durationDays: sparkRequired ? 60 : 0,
            requestTiming: sparkRequired ? "Request within 24h of publish" : "Not required",
        },
    };
}
