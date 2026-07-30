import { Link, useRouterState } from "@tanstack/react-router";
import { PanelLeftClose, PanelLeft, Sparkles } from "lucide-react";
import { useAppStore } from "@/app/store/app-store";
import { cn } from "@/shared/lib/utils";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/shared/ui/tooltip";
import { navigationGroups, type ShellNavItem } from "./navigation";

function NavLinkRow({ item, collapsed }: { item: ShellNavItem; collapsed: boolean }) {
    const pathname = useRouterState({ select: (s) => s.location.pathname });
    const active = pathname === item.to || pathname.startsWith(item.to + "/");
    const Icon = item.icon;
    const link = (
        <Link
            to={item.to}
            className={cn(
                "relative flex min-h-10 items-center gap-3 rounded-xl px-2.5 py-2 text-sm font-medium transition-colors duration-[180ms] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                collapsed && "justify-center px-0",
                active
                    ? "bg-primary-soft text-primary-active"
                    : "text-text-secondary hover:bg-surface-soft hover:text-text-primary",
            )}
            aria-current={active ? "page" : undefined}
        >
            {active && !collapsed && (
                <span
                    aria-hidden
                    className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-r-full bg-primary"
                />
            )}
            <Icon className={cn("h-[18px] w-[18px] shrink-0", active && "text-primary")} />
            {!collapsed && <span className="truncate">{item.label}</span>}
            {active && collapsed && (
                <span
                    aria-hidden
                    className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-r-full bg-primary"
                />
            )}
        </Link>
    );

    if (!collapsed) return link;
    return (
        <Tooltip>
            <TooltipTrigger asChild>{link}</TooltipTrigger>
            <TooltipContent side="right">{item.label}</TooltipContent>
        </Tooltip>
    );
}

export function AppSidebar() {
    const collapsed = useAppStore((s) => s.sidebarCollapsed);
    const toggle = useAppStore((s) => s.toggleSidebar);

    return (
        <TooltipProvider delayDuration={150}>
            <aside
                aria-label="Primary"
                className={cn(
                    "hidden shrink-0 flex-col border-r border-hairline bg-surface transition-[width] duration-200 md:flex",
                    collapsed ? "w-[72px]" : "w-[240px]",
                )}
                style={{ transitionTimingFunction: "cubic-bezier(0.2, 0.8, 0.2, 1)" }}
            >
                <div
                    className={cn(
                        "flex h-16 items-center gap-2 px-4",
                        collapsed && "justify-center px-0",
                    )}
                >
                    <span className="grid h-8 w-8 place-items-center rounded-full bg-primary text-primary-foreground">
                        <Sparkles className="h-4 w-4" />
                    </span>
                    {!collapsed && (
                        <div className="min-w-0">
                            <p className="truncate text-sm font-semibold text-text-primary">
                                Viraldy
                            </p>
                            <p className="truncate text-[11px] text-text-tertiary">
                                Creative Intelligence
                            </p>
                        </div>
                    )}
                </div>

                <nav className={cn("flex-1 overflow-y-auto px-2 pb-4", collapsed && "px-2")}>
                    {navigationGroups.map((group, index) => (
                        <div
                            key={group.label}
                            className={cn(
                                index > 0 &&
                                    (collapsed ? "mt-2 border-t border-divider pt-2" : "mt-4"),
                            )}
                        >
                            {!collapsed && (
                                <p className="mb-1 px-2 text-[10px] font-semibold uppercase text-text-tertiary first:pt-2">
                                    {group.label}
                                </p>
                            )}
                            <div className="flex flex-col gap-0.5">
                                {group.items.map((item) => (
                                    <NavLinkRow key={item.to} item={item} collapsed={collapsed} />
                                ))}
                            </div>
                        </div>
                    ))}
                </nav>

                <div
                    className={cn(
                        "border-t border-hairline p-2",
                        collapsed && "flex justify-center",
                    )}
                >
                    <button
                        type="button"
                        onClick={toggle}
                        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
                        className="inline-flex h-8 w-8 items-center justify-center rounded-md text-text-tertiary transition-colors hover:bg-surface-soft hover:text-text-primary focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    >
                        {collapsed ? (
                            <PanelLeft className="h-4 w-4" />
                        ) : (
                            <PanelLeftClose className="h-4 w-4" />
                        )}
                    </button>
                </div>
            </aside>
        </TooltipProvider>
    );
}

export function MobileSidebarContent({ onNavigate }: { onNavigate?: () => void }) {
    const pathname = useRouterState({ select: (s) => s.location.pathname });
    return (
        <div className="flex h-full flex-col">
            <div className="flex h-16 items-center gap-2 px-4">
                <span className="grid h-8 w-8 place-items-center rounded-full bg-primary text-primary-foreground">
                    <Sparkles className="h-4 w-4" />
                </span>
                <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-text-primary">Viraldy</p>
                    <p className="truncate text-[11px] text-text-tertiary">Creative Intelligence</p>
                </div>
            </div>
            <nav className="flex-1 overflow-y-auto px-2 pb-4">
                {navigationGroups.map((group) => (
                    <div key={group.label} className="mt-3 first:mt-0">
                        <p className="mb-1 px-2 text-[10px] font-semibold uppercase text-text-tertiary">
                            {group.label}
                        </p>
                        <div className="flex flex-col gap-0.5">
                            {group.items.map((item) => {
                                const active =
                                    pathname === item.to || pathname.startsWith(item.to + "/");
                                const Icon = item.icon;
                                return (
                                    <Link
                                        key={item.to}
                                        to={item.to}
                                        onClick={onNavigate}
                                        className={cn(
                                            "relative flex min-h-10 items-center gap-3 rounded-xl px-2.5 py-2 text-sm font-medium transition-colors duration-[180ms] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                                            active
                                                ? "bg-primary-soft text-primary-active"
                                                : "text-text-secondary hover:bg-surface-soft",
                                        )}
                                    >
                                        {active && (
                                            <span
                                                aria-hidden
                                                className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-r-full bg-primary"
                                            />
                                        )}
                                        <Icon
                                            className={cn(
                                                "h-[18px] w-[18px]",
                                                active && "text-primary",
                                            )}
                                        />
                                        {item.label}
                                    </Link>
                                );
                            })}
                        </div>
                    </div>
                ))}
            </nav>
        </div>
    );
}
