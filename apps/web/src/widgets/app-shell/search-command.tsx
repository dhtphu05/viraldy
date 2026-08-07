import {
    CommandDialog,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandList,
} from "@/shared/ui/command";
import { useNavigate } from "@tanstack/react-router";
import { BarChart3, Images, Megaphone, Package, Plus, SearchX, VideoIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { useAllCampaigns, useAppStore } from "@/app/store/app-store";
import { seedProducts } from "@/features/products/data/products";
import { seedCreators } from "@/features/ugc-review/mocks/creators";
import type { PerfRecommendation } from "@/features/performance/types/performance";
import { ViraldyIcon } from "@/shared/ui/viraldy-icon";
import { navigationItems } from "./navigation";

const quickActions = [
    {
        label: "Start production run",
        hint: "Analyze, adapt, brief, validate",
        iconName: "startProductionRun",
        to: "/mvp",
    },
    {
        label: "New campaign",
        hint: "Create campaign shell",
        iconName: "newCampaign",
        to: "/campaigns/new",
    },
    {
        label: "Upload UGC",
        hint: "Open review upload dialog",
        iconName: "uploadVideo",
        to: "/ugc-review",
        search: { campaignId: undefined, upload: true },
    },
    {
        label: "Import creative",
        hint: "Add a creative reference",
        iconName: "importCreative",
        to: "/creative-library",
        search: { import: true },
    },
    {
        label: "Import performance data",
        hint: "Map campaign metrics",
        iconName: "importPerformance",
        to: "/performance",
        search: { import: true },
    },
] as const;

function matchesQuery(query: string, ...values: Array<string | undefined>) {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) return true;
    const haystack = values.filter(Boolean).join(" ").toLowerCase();
    return normalizedQuery.split(/\s+/).every((token) => haystack.includes(token));
}

export function SearchCommand({
    open,
    onOpenChange,
}: {
    open: boolean;
    onOpenChange: (v: boolean) => void;
}) {
    const navigate = useNavigate();
    const campaigns = useAllCampaigns();
    const setDraft = useAppStore((s) => s.setDraft);
    const creatives = useAppStore((s) => s.creatives);
    const ugcAssets = useAppStore((s) => s.ugcAssets);
    const perfRecommendations = useAppStore((s) => s.perfRecommendations);
    const [query, setQuery] = useState("");

    const quickActionResults = quickActions.filter((action) =>
        matchesQuery(query, action.label, action.hint),
    );
    const navigationResults = navigationItems.filter((item) => matchesQuery(query, item.label));
    const campaignResults = campaigns
        .slice(0, 8)
        .filter((campaign) =>
            matchesQuery(query, campaign.name, campaign.product, campaign.objective),
        );
    const creativeResults = creatives
        .filter((creative) => !creative.archived)
        .slice(0, 8)
        .filter((creative) =>
            matchesQuery(
                query,
                creative.title,
                creative.brandOrCreator,
                creative.angle,
                creative.tags.join(" "),
            ),
        );
    const ugcResults = ugcAssets.slice(0, 8).filter((asset) => {
        const creator = seedCreators.find((item) => item.id === asset.creatorId);
        return matchesQuery(query, asset.title, creator?.name, asset.decision, asset.objective);
    });
    const productResults = seedProducts.filter((product) =>
        matchesQuery(query, product.name, product.category, product.readiness),
    );
    const campaignProductResults = seedProducts.filter((product) =>
        matchesQuery(query, "start campaign", product.name, product.category),
    );
    const performanceResults = perfRecommendations
        .slice(0, 8)
        .filter((recommendation: PerfRecommendation) =>
            matchesQuery(
                query,
                recommendation.title,
                recommendation.kind,
                recommendation.object,
                recommendation.nextAction,
            ),
        );

    useEffect(() => {
        function handler(e: KeyboardEvent) {
            if ((e.key === "k" || e.key === "K") && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                onOpenChange(!open);
            }
        }
        window.addEventListener("keydown", handler);
        return () => window.removeEventListener("keydown", handler);
    }, [open, onOpenChange]);

    useEffect(() => {
        if (!open) setQuery("");
    }, [open]);

    return (
        <CommandDialog open={open} onOpenChange={onOpenChange}>
            <CommandInput
                value={query}
                onValueChange={setQuery}
                placeholder="Search products, campaigns, assets…"
            />
            <CommandList>
                <CommandEmpty>
                    <div className="flex flex-col items-center px-6 py-3 text-center">
                        <span className="grid h-10 w-10 place-items-center rounded-full bg-surface-muted text-text-secondary">
                            <SearchX className="h-5 w-5" />
                        </span>
                        <p className="mt-3 font-medium text-text-primary">No matching result</p>
                        <p className="mt-1 max-w-xs text-xs leading-5 text-text-secondary">
                            Try a product, campaign, creator, asset, or action such as “upload UGC”.
                        </p>
                    </div>
                </CommandEmpty>
                {quickActionResults.length > 0 && (
                    <CommandGroup heading="Quick actions">
                        {quickActionResults.map((action) => {
                            return (
                                <CommandItem
                                    key={action.label}
                                    value={`${action.label} ${action.hint}`}
                                    onSelect={() => {
                                        onOpenChange(false);
                                        if (action.to === "/ugc-review") {
                                            navigate({
                                                to: "/ugc-review",
                                                search: action.search,
                                            });
                                        } else if (action.to === "/creative-library") {
                                            navigate({
                                                to: "/creative-library",
                                                search: action.search,
                                            });
                                        } else if (action.to === "/performance") {
                                            navigate({
                                                to: "/performance",
                                                search: action.search,
                                            });
                                        } else {
                                            navigate({ to: action.to });
                                        }
                                    }}
                                >
                                    <ViraldyIcon
                                        name={action.iconName}
                                        size="sm"
                                        className="mr-2"
                                    />
                                    <span className="min-w-0 flex-1">{action.label}</span>
                                    <span className="hidden min-w-0 max-w-[45%] truncate text-xs text-text-tertiary sm:block">
                                        {action.hint}
                                    </span>
                                </CommandItem>
                            );
                        })}
                    </CommandGroup>
                )}
                {navigationResults.length > 0 && (
                    <CommandGroup heading="Navigate">
                        {navigationResults.map((n) => {
                            const Icon = n.icon;
                            return (
                                <CommandItem
                                    key={n.to}
                                    value={n.label}
                                    onSelect={() => {
                                        onOpenChange(false);
                                        navigate({ to: n.to });
                                    }}
                                >
                                    {n.iconName ? (
                                        <ViraldyIcon name={n.iconName} size="sm" className="mr-2" />
                                    ) : (
                                        <Icon className="mr-2 h-4 w-4" />
                                    )}
                                    <span>{n.label}</span>
                                </CommandItem>
                            );
                        })}
                    </CommandGroup>
                )}
                {campaignResults.length > 0 && (
                    <CommandGroup heading="Campaigns">
                        {campaignResults.map((campaign) => (
                            <CommandItem
                                key={campaign.id}
                                value={`${campaign.name} ${campaign.product} ${campaign.objective ?? ""} campaign`}
                                onSelect={() => {
                                    onOpenChange(false);
                                    navigate({
                                        to: "/campaigns/$campaignId",
                                        params: { campaignId: campaign.id },
                                    });
                                }}
                            >
                                <Megaphone className="mr-2 h-4 w-4" />
                                <span className="min-w-0 flex-1 truncate">{campaign.name}</span>
                                <span className="truncate text-xs text-text-tertiary">
                                    {campaign.product}
                                </span>
                            </CommandItem>
                        ))}
                    </CommandGroup>
                )}
                {creativeResults.length > 0 && (
                    <CommandGroup heading="Creatives">
                        {creativeResults.map((creative) => (
                            <CommandItem
                                key={creative.id}
                                value={`${creative.title} ${creative.brandOrCreator} ${creative.angle} ${creative.tags.join(" ")} creative asset`}
                                onSelect={() => {
                                    onOpenChange(false);
                                    navigate({
                                        to: "/creative-library/$creativeId",
                                        params: { creativeId: creative.id },
                                    });
                                }}
                            >
                                <Images className="mr-2 h-4 w-4" />
                                <span className="min-w-0 flex-1 truncate">{creative.title}</span>
                                <span className="truncate text-xs text-text-tertiary">
                                    {creative.brandOrCreator}
                                </span>
                            </CommandItem>
                        ))}
                    </CommandGroup>
                )}
                {ugcResults.length > 0 && (
                    <CommandGroup heading="UGC assets">
                        {ugcResults.map((asset) => {
                            const creator = seedCreators.find((c) => c.id === asset.creatorId);
                            return (
                                <CommandItem
                                    key={asset.id}
                                    value={`${asset.title} ${creator?.name ?? ""} ${asset.decision} ugc video`}
                                    onSelect={() => {
                                        onOpenChange(false);
                                        navigate({
                                            to: "/ugc-review/$assetId",
                                            params: { assetId: asset.id },
                                        });
                                    }}
                                >
                                    <VideoIcon className="mr-2 h-4 w-4" />
                                    <span className="min-w-0 flex-1 truncate">{asset.title}</span>
                                    <span className="truncate text-xs text-text-tertiary">
                                        {creator?.name ?? "Unknown creator"}
                                    </span>
                                </CommandItem>
                            );
                        })}
                    </CommandGroup>
                )}
                {(productResults.length > 0 || campaignProductResults.length > 0) && (
                    <CommandGroup heading="Products">
                        {productResults.map((product) => (
                            <CommandItem
                                key={product.id}
                                value={`${product.name} ${product.category} ${product.readiness} product`}
                                onSelect={() => {
                                    onOpenChange(false);
                                    navigate({
                                        to: "/products",
                                        search: { productId: product.id },
                                    });
                                }}
                            >
                                <Package className="mr-2 h-4 w-4" />
                                <span className="min-w-0 flex-1 truncate">{product.name}</span>
                                <span className="truncate text-xs text-text-tertiary">
                                    {product.category}
                                </span>
                            </CommandItem>
                        ))}
                        {campaignProductResults.map((product) => (
                            <CommandItem
                                key={`start-${product.id}`}
                                value={`start campaign ${product.name} ${product.category}`}
                                onSelect={() => {
                                    setDraft({ productId: product.id });
                                    onOpenChange(false);
                                    navigate({ to: "/campaigns/new" });
                                }}
                            >
                                <Plus className="mr-2 h-4 w-4" />
                                <span className="min-w-0 flex-1 truncate">
                                    Start campaign for {product.name}
                                </span>
                            </CommandItem>
                        ))}
                    </CommandGroup>
                )}
                {performanceResults.length > 0 && (
                    <CommandGroup heading="Performance recommendations">
                        {performanceResults.map((rec: PerfRecommendation) => (
                            <CommandItem
                                key={rec.id}
                                value={`${rec.title} ${rec.kind} ${rec.object} ${rec.nextAction} performance recommendation`}
                                onSelect={() => {
                                    onOpenChange(false);
                                    navigate({
                                        to: "/performance/$campaignId",
                                        params: { campaignId: rec.campaignId },
                                    });
                                }}
                            >
                                <BarChart3 className="mr-2 h-4 w-4" />
                                <span className="min-w-0 flex-1 truncate">{rec.title}</span>
                                <span className="truncate text-xs text-text-tertiary">
                                    {rec.kind}
                                </span>
                            </CommandItem>
                        ))}
                    </CommandGroup>
                )}
            </CommandList>
        </CommandDialog>
    );
}
