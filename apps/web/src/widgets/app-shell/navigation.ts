import {
    BarChart3,
    Images,
    LayoutDashboard,
    Megaphone,
    Package,
    Settings,
    ScanSearch,
    Video,
    Wand2,
    Workflow,
} from "lucide-react";
import type { ComponentType } from "react";
import type { ViraldyIconName } from "@/shared/ui/viraldy-icon";

export type ShellNavItem = {
    to: string;
    label: string;
    icon: ComponentType<{ className?: string }>;
    iconName?: ViraldyIconName;
};

export type ShellNavGroup = {
    label: string;
    items: ShellNavItem[];
};

export const navigationGroups: ShellNavGroup[] = [
    {
        label: "Workspace",
        items: [
            {
                to: "/dashboard",
                label: "Overview",
                icon: LayoutDashboard,
                iconName: "overview",
            },
            {
                to: "/mvp",
                label: "Production Run",
                icon: Workflow,
                iconName: "productionRun",
            },
        ],
    },
    {
        label: "Create & Operate",
        items: [
            {
                to: "/creative-library",
                label: "Creative Library",
                icon: Images,
                iconName: "creativeLibrary",
            },
            {
                to: "/smart-remake",
                label: "Smart Remake",
                icon: Wand2,
            },
            {
                to: "/tiktok-scorer",
                label: "TikTok Scorer",
                icon: ScanSearch,
                iconName: "tiktokScorer",
            },
            {
                to: "/campaigns",
                label: "Campaigns",
                icon: Megaphone,
                iconName: "campaigns",
            },
        ],
    },
    {
        label: "Validate & Learn",
        items: [
            {
                to: "/ugc-review",
                label: "UGC Review",
                icon: Video,
                iconName: "ugcReview",
            },
            {
                to: "/performance",
                label: "Performance",
                icon: BarChart3,
                iconName: "performanceReport",
            },
        ],
    },
    {
        label: "Manage",
        items: [
            {
                to: "/products",
                label: "Products",
                icon: Package,
                iconName: "productCatalog",
            },
            { to: "/settings", label: "Settings", icon: Settings },
        ],
    },
];

export const navigationItems = navigationGroups.flatMap((group) => group.items);
