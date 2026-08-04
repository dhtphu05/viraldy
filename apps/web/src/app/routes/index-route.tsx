import { createFileRoute, redirect } from "@tanstack/react-router";
import { LandingPage } from "@/features/landing/landing-page";

export const Route = createFileRoute("/")({
    head: () => ({
        meta: [
            { title: "Viraldy — Creative Intelligence for TikTok Shop" },
            {
                name: "description",
                content:
                    "Turn winning creative patterns into product-specific ideas, creator-ready briefs, and exact video fixes — before you spend. Viraldy helps TikTok Shop sellers, POD brands, and agencies make better creative decisions.",
            },
            { property: "og:title", content: "Viraldy — Creative Intelligence for TikTok Shop" },
            {
                property: "og:description",
                content:
                    "Turn winning creative patterns into product-specific ideas, creator-ready briefs, and exact video fixes — before you spend.",
            },
            { property: "og:type", content: "website" },
            { name: "twitter:card", content: "summary_large_image" },
        ],
    }),
    beforeLoad: ({ context }) => {
        if (context.auth.authenticated) {
            throw redirect({ to: "/dashboard" });
        }
    },
    component: () => <LandingPage />,
});
