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
} from "lucide-react";
import { useEffect } from "react";

const nav = [
    { to: "/dashboard", label: "Overview", icon: LayoutDashboard },
    { to: "/creative-library", label: "Creative Library", icon: Images },
    { to: "/campaigns", label: "Campaigns", icon: Megaphone },
    { to: "/ugc-review", label: "UGC Review", icon: Video },
    { to: "/performance", label: "Performance", icon: BarChart3 },
    { to: "/products", label: "Products", icon: Package },
    { to: "/settings", label: "Settings", icon: SettingsIcon },
];

export function SearchCommand({
    open,
    onOpenChange,
}: {
    open: boolean;
    onOpenChange: (v: boolean) => void;
}) {
    const navigate = useNavigate();

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
            <CommandInput placeholder="Search campaigns, creators, assets…" />
            <CommandList>
                <CommandEmpty>No results.</CommandEmpty>
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
                                {n.label}
                            </CommandItem>
                        );
                    })}
                </CommandGroup>
            </CommandList>
        </CommandDialog>
    );
}
