import { createFileRoute } from "@tanstack/react-router";
import { PlaceholderPage } from "@/widgets/app-shell/placeholder-page";
import { Package } from "lucide-react";

export const Route = createFileRoute("/products")({
    head: () => ({ meta: [{ title: "Products — Viraldy" }] }),
    component: () => (
        <PlaceholderPage
            title="Products"
            description="Your TikTok Shop, POD, and cross-border catalog connected to creatives, samples, and performance."
            icon={Package}
            emptyTitle="Product catalog coming soon"
            emptyDescription="Sync products, attach reference creatives, and track sample allocation in the next phase."
        />
    ),
});
