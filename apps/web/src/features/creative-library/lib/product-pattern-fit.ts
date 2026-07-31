import type {
    CreativeAngle,
    ProductCategory,
    SeedProduct,
} from "@/features/creative-library/types/creative";

type PatternSource = {
    category: ProductCategory;
    angle: CreativeAngle;
    linkedProductId?: string;
};

type FitProduct = Pick<
    SeedProduct,
    "id" | "name" | "category" | "readiness" | "fulfillmentRisk" | "linkedCampaignCount"
>;

export type ProductPatternFit = {
    level: "recommended" | "possible" | "low";
    score: number;
    reasons: string[];
    risk: string;
};

const DEMONSTRATION_ANGLES: CreativeAngle[] = [
    "Product demonstration",
    "Before-and-after",
    "Problem–solution",
    "Comparison",
];

export function evaluateProductPatternFit(
    source: PatternSource,
    product: FitProduct,
): ProductPatternFit {
    const sameCategory = source.category === product.category;
    const relatedHomeContext =
        !sameCategory &&
        [source.category, product.category].every((category) =>
            ["Home & Kitchen", "Home Organization"].includes(category),
        );
    const demonstrationFriendly = DEMONSTRATION_ANGLES.includes(source.angle);
    const alreadyLinked = source.linkedProductId === product.id;

    let score = sameCategory ? 3 : relatedHomeContext ? 1.5 : 0;
    if (alreadyLinked) score += 2;
    if (demonstrationFriendly) score += 1;
    if (product.readiness === "Ready") score += 1;
    if (product.readiness === "Setup needed") score -= 1;
    if (product.readiness === "Out of stock") score -= 3;
    if (product.fulfillmentRisk === "Low") score += 0.5;
    if (product.fulfillmentRisk === "High") score -= 2;
    if (product.linkedCampaignCount > 0) score += 0.5;

    const reasons = [
        ...(alreadyLinked ? ["Already linked to this source creative"] : []),
        sameCategory
            ? `Same ${product.category} buying context`
            : relatedHomeContext
              ? "Related home-environment setting"
              : "A new buyer and setting can test the pattern in another category",
        demonstrationFriendly
            ? "Pattern supports visible product proof"
            : "Pattern can preserve its narrative structure",
        product.linkedCampaignCount > 0
            ? "Existing campaign context can support adaptation"
            : "Fresh test with no existing campaign bias",
    ].slice(0, 3);

    const risk =
        product.readiness !== "Ready"
            ? "Product is not ready for a production test."
            : product.fulfillmentRisk === "High"
              ? "High fulfillment risk may delay creator sampling."
              : sameCategory
                ? "Do not reuse source wording or scene composition."
                : "Buyer context, proof, and setting must be rebuilt for this category.";

    return {
        level: score >= 4 ? "recommended" : score >= 1.5 ? "possible" : "low",
        score,
        reasons,
        risk,
    };
}

export function rankProductsByPatternFit<T extends FitProduct>(
    source: PatternSource,
    products: T[],
) {
    return products
        .map((product) => ({
            product,
            fit: evaluateProductPatternFit(source, product),
        }))
        .sort((a, b) => b.fit.score - a.fit.score || a.product.name.localeCompare(b.product.name));
}
