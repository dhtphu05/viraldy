import {
    CommandDialog,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandList,
} from "@/shared/ui/command";
import { useNavigate } from "@tanstack/react-router";
import {
    LayoutDashboard,
    Images,
    Megaphone,
    Video,
    BarChart3,
    Package,
    Settings as SettingsIcon,
    Workflow,
    Plus,
    Upload,
    BarChart2,
    VideoIcon,
    Sparkles,
} from "lucide-react";
import { useEffect } from "react";
import { useAllCampaigns, useAppStore } from "@/app/store/app-store";
import { seedProducts } from "@/features/products/data/products";
import { seedCreators } from "@/features/ugc-review/mocks/creators";
import type { PerfRecommendation } from "@/features/performance/types/performance";

const nav = [
    { to: "/dashboard", label: "Overview", icon: LayoutDashboard },
    { to: "/production", label: "Production Studio", icon: Workflow },
    { to: "/creative-library", label: "Creative Library", icon: Images },
    { to: "/campaigns", label: "Campaigns", icon: Megaphone },
    { to: "/ugc-review", label: "UGC Review", icon: Video },
    { to: "/performance", label: "Performance", icon: BarChart3 },
    { to: "/products", label: "Products", icon: Package },
    { to: "/settings", label: "Settings", icon: SettingsIcon },
];

const quickActions = [
    {
        label: "Open Production Studio",
        hint: "Analyze, adapt, brief, review",
        icon: Workflow,
        to: "/production",
    },
    { label: "New campaign", hint: "Create campaign shell", icon: Plus, to: "/campaigns/new" },
    {
        label: "Upload UGC",
        hint: "Open review upload dialog",
        icon: Upload,
        to: "/ugc-review",
        search: { upload: true },
    },
    {
        label: "Import creative",
        hint: "Add a creative reference",
        icon: Sparkles,
        to: "/creative-library",
        search: { import: true },
    },
    {
        label: "Import performance data",
        hint: "Map campaign metrics",
        icon: BarChart2,
        to: "/performance",
        search: { import: true },
    },
] as const;

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

    return (
        <CommandDialog open={open} onOpenChange={onOpenChange}>
            <CommandInput placeholder="Search products, campaigns, and system responses…" />
            <CommandList>
                <CommandEmpty>No results.</CommandEmpty>
                <CommandGroup heading="Quick actions">
                    {quickActions.map((action) => {
                        const Icon = action.icon;
                        return (
                            <CommandItem
                                key={action.label}
                                value={`${action.label} ${action.hint}`}
                                onSelect={() => {
                                    onOpenChange(false);
                                    if ("search" in action) {
                                        navigate({ to: action.to, search: action.search });
                                    } else {
                                        navigate({ to: action.to });
                                    }
                                }}
                            >
                                <Icon className="mr-2 h-4 w-4" />
                                <span className="min-w-0 flex-1">{action.label}</span>
                                <span className="hidden min-w-0 max-w-[45%] truncate text-xs text-text-tertiary sm:block">
                                    {action.hint}
                                </span>
                            </CommandItem>
                        );
                    })}
                </CommandGroup>
                <CommandGroup heading="Navigate">
                    {nav.map((n) => {
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
                                <Icon className="mr-2 h-4 w-4" />
                                <span>{n.label}</span>
                            </CommandItem>
                        );
                    })}
                </CommandGroup>
                <CommandGroup heading="Campaigns">
                    {campaigns.slice(0, 8).map((campaign) => (
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
                <CommandGroup heading="Creatives">
                    {creatives
                        .filter((creative) => !creative.archived)
                        .slice(0, 8)
                        .map((creative) => (
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
                <CommandGroup heading="UGC assets">
                    {ugcAssets.slice(0, 8).map((asset) => {
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
                <CommandGroup heading="Products">
                    {seedProducts.map((product) => (
                        <CommandItem
                            key={product.id}
                            value={`${product.name} ${product.category} ${product.readiness} product`}
                            onSelect={() => {
                                onOpenChange(false);
                                navigate({ to: "/products", search: { productId: product.id } });
                            }}
                        >
                            <Package className="mr-2 h-4 w-4" />
                            <span className="min-w-0 flex-1 truncate">{product.name}</span>
                            <span className="truncate text-xs text-text-tertiary">
                                {product.category}
                            </span>
                        </CommandItem>
                    ))}
                    {seedProducts.map((product) => (
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
                <CommandGroup heading="Performance recommendations">
                    {perfRecommendations.slice(0, 8).map((rec: PerfRecommendation) => (
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
                            <span className="truncate text-xs text-text-tertiary">{rec.kind}</span>
                        </CommandItem>
                    ))}
                </CommandGroup>
            </CommandList>
        </CommandDialog>
    );
}
