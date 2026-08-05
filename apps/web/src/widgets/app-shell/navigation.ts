import {
    BarChart3,
    Images,
    LayoutDashboard,
    Megaphone,
    Package,
    Settings,
    ScanSearch,
    Video,
    Workflow,
} from "lucide-react";
import type { ComponentType } from "react";

export type ShellNavItem = {
    to: string;
    label: string;
    icon: ComponentType<{ className?: string }>;
    iconSrc?: string;
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
                iconSrc: "/sidebar-icons/overview.png",
            },
            {
                to: "/mvp",
                label: "Production Run",
                icon: Workflow,
                iconSrc: "/sidebar-icons/production_run.png",
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
                iconSrc: "/sidebar-icons/creative_lib.png",
            },
            { to: "/tiktok-scorer", label: "TikTok Scorer", icon: ScanSearch },
            {
                to: "/campaigns",
                label: "Campaigns",
                icon: Megaphone,
                iconSrc: "/sidebar-icons/campaign.png",
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
                iconSrc: "/sidebar-icons/ugc_review.png",
            },
            {
                to: "/performance",
                label: "Performance",
                icon: BarChart3,
                iconSrc: "/sidebar-icons/performance.png",
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
                iconSrc: "/sidebar-icons/product.png",
            },
            {
                to: "/settings",
                label: "Settings",
                icon: Settings,
                iconSrc: "/sidebar-icons/setting.png",
            },
        ],
    },
];

export const navigationItems = navigationGroups.flatMap((group) => group.items);
