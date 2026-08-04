import { Link } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { SectionWrapper } from "./section-wrapper";

const tiktokShopItems = [
    "Turn competitor and creator references into reusable patterns.",
    "Build product-specific TikTok directions.",
    "Prepare creator-ready briefs.",
    "Review affiliate and UGC drafts.",
    "Catch missing demos, weak proof and unclear CTA.",
    "Create precise revision instructions.",
    "Keep the learning connected to the product.",
];

export function UseCaseTikTokShop() {
    return (
        <SectionWrapper id="sellers" background="surface">
            <div className="grid gap-12 lg:grid-cols-2 lg:items-center">
                <div>
                    <p className="text-xs font-semibold uppercase text-primary">Use Case</p>
                    <h2 className="mt-2 text-2xl font-bold text-text-primary sm:text-3xl">
                        For TikTok Shop sellers
                    </h2>
                    <p className="mt-3 text-sm text-text-secondary">
                        You need more than content ideas. You need product demonstrations, creator
                        briefs and videos that are ready for the next decision.
                    </p>
                    <p className="mt-3 text-sm font-medium text-text-primary">Use Viraldy to:</p>
                    <ul className="mt-3 space-y-1.5">
                        {tiktokShopItems.map((item) => (
                            <li key={item} className="flex items-start gap-2 text-sm text-text-secondary">
                                <span className="mt-0.5 shrink-0 text-primary">&bull;</span>
                                {item}
                            </li>
                        ))}
                    </ul>
                    <Button asChild size="sm" className="mt-5">
                        <Link to="/login">
                            Build My Next TikTok
                            <ArrowRight className="ml-1 h-4 w-4" />
                        </Link>
                    </Button>
                </div>
            </div>
        </SectionWrapper>
    );
}
