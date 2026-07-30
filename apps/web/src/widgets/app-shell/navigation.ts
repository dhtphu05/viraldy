import {
    BarChart3,
    Images,
    LayoutDashboard,
    Megaphone,
    Package,
    Settings,
    Video,
    Workflow,
} from "lucide-react";
import type { ComponentType } from "react";

export type ShellNavItem = {
    to: string;
    label: string;
    icon: ComponentType<{ className?: string }>;
};

export type ShellNavGroup = {
    label: string;
    items: ShellNavItem[];
};

export const navigationGroups: ShellNavGroup[] = [
    {
        label: "Workspace",
        items: [
            { to: "/dashboard", label: "Overview", icon: LayoutDashboard },
            { to: "/mvp", label: "Production Run", icon: Workflow },
        ],
    },
    {
        label: "Create & Operate",
        items: [
            { to: "/creative-library", label: "Creative Library", icon: Images },
            { to: "/campaigns", label: "Campaigns", icon: Megaphone },
        ],
    },
    {
        label: "Validate & Learn",
        items: [
            { to: "/ugc-review", label: "UGC Review", icon: Video },
            { to: "/performance", label: "Performance", icon: BarChart3 },
        ],
    },
    {
        label: "Manage",
        items: [
            { to: "/products", label: "Products", icon: Package },
            { to: "/settings", label: "Settings", icon: Settings },
        ],
    },
];

export const navigationItems = navigationGroups.flatMap((group) => group.items);
