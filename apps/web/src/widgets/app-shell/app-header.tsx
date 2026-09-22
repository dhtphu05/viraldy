import { WorkspaceSwitcher } from "./workspace-switcher";
import { NotificationPopover } from "./notification-popover";
import { SearchCommand } from "./search-command";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/shared/ui/sheet";
import { MobileSidebarContent } from "./app-sidebar";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/shared/ui/dropdown-menu";
import { Link, useRouteContext } from "@tanstack/react-router";
import { Menu } from "lucide-react";
import { useState } from "react";
import { ViraldyIcon } from "@/shared/ui/viraldy-icon";

export function AppHeader() {
    const [searchOpen, setSearchOpen] = useState(false);
    const [mobileNavOpen, setMobileNavOpen] = useState(false);
    const { auth } = useRouteContext({ from: "__root__" });
    const user = auth.user;

    return (
        <header className="relative z-10 flex h-16 shrink-0 items-center gap-2 border-b border-divider bg-surface px-3 sm:px-4">
            <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
                <SheetTrigger asChild>
                    <button
                        type="button"
                        aria-label="Open navigation"
                        className="inline-flex h-9 w-9 items-center justify-center rounded-md text-text-secondary transition-colors hover:bg-surface-soft md:hidden"
                    >
                        <Menu className="h-4 w-4" />
                    </button>
                </SheetTrigger>
                <SheetContent side="left" className="w-[280px] p-0">
                    <SheetTitle className="sr-only">Primary navigation</SheetTitle>
                    <MobileSidebarContent onNavigate={() => setMobileNavOpen(false)} />
                </SheetContent>
            </Sheet>

            <WorkspaceSwitcher />

            <div className="mx-auto hidden min-w-0 max-w-md flex-1 lg:block">
                <button
                    type="button"
                    onClick={() => setSearchOpen(true)}
                    className="inline-flex h-9 w-full items-center gap-2 rounded-md bg-surface-soft px-3 text-sm text-text-tertiary transition-colors hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                >
                    <ViraldyIcon name="search" size="md" />
                    <span className="min-w-0 flex-1 truncate whitespace-nowrap text-left">
                        Search products, campaigns, assets…
                    </span>
                    <kbd className="shrink-0 rounded border border-hairline bg-surface px-1.5 py-0.5 text-[10px] font-medium text-text-tertiary">
                        ⌘K
                    </kbd>
                </button>
            </div>

            <div className="ml-auto flex items-center gap-1">
                <button
                    type="button"
                    onClick={() => setSearchOpen(true)}
                    aria-label="Search"
                    className="inline-flex h-9 w-9 items-center justify-center rounded-md text-text-secondary transition-colors hover:bg-surface-soft lg:hidden"
                >
                    <ViraldyIcon name="search" size="md" />
                </button>
                <NotificationPopover />
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <button
                            type="button"
                            aria-label="Account"
                            className="ml-1 grid h-9 w-9 place-items-center rounded-md text-text-secondary transition-colors hover:bg-surface-soft hover:text-text-primary focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                        >
                            <ViraldyIcon name="account" size="md" />
                        </button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-56">
                        <DropdownMenuLabel>
                            <div className="flex flex-col">
                                <span className="text-sm font-medium text-text-primary">
                                    {user?.display_name ?? "Viraldy user"}
                                </span>
                                <span className="text-xs text-text-tertiary">
                                    {user?.email ?? "Signed in"}
                                </span>
                            </div>
                        </DropdownMenuLabel>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem asChild>
                            <Link to="/account">Account settings</Link>
                        </DropdownMenuItem>
                        <DropdownMenuItem asChild>
                            <Link to="/settings">Workspace preferences</Link>
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <form action="/api/auth/logout" method="post">
                            <DropdownMenuItem asChild>
                                <button type="submit" className="w-full">
                                    Sign out
                                </button>
                            </DropdownMenuItem>
                        </form>
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>

            <SearchCommand open={searchOpen} onOpenChange={setSearchOpen} />
        </header>
    );
}
