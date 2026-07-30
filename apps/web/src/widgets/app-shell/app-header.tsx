import { WorkspaceSwitcher } from "./workspace-switcher";
import { NotificationPopover } from "./notification-popover";
import { SearchCommand } from "./search-command";
import { Sheet, SheetContent, SheetTrigger } from "@/shared/ui/sheet";
import { MobileSidebarContent } from "./app-sidebar";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/shared/ui/dropdown-menu";
import { HelpCircle, Menu, Search } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

export function AppHeader() {
    const [searchOpen, setSearchOpen] = useState(false);
    const [mobileNavOpen, setMobileNavOpen] = useState(false);

    return (
        <header className="relative z-10 flex h-16 shrink-0 items-center gap-2 border-b border-hairline bg-surface/95 px-3 backdrop-blur sm:px-4">
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
                    <Search className="h-4 w-4 shrink-0" />
                    <span className="min-w-0 flex-1 truncate whitespace-nowrap text-left">
                        Search products, campaigns, system responses…
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
                    <Search className="h-4 w-4" />
                </button>
                <button
                    type="button"
                    aria-label="Help"
                    onClick={() => toast("Help center", { description: "Docs coming soon." })}
                    className="inline-flex h-9 w-9 items-center justify-center rounded-md text-text-secondary transition-colors hover:bg-surface-soft hover:text-text-primary focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                >
                    <HelpCircle className="h-4 w-4" />
                </button>
                <NotificationPopover />
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <button
                            type="button"
                            aria-label="Account"
                            className="ml-1 grid h-8 w-8 place-items-center rounded-full bg-primary-soft text-xs font-semibold text-primary-active ring-1 ring-inset ring-primary/10 transition-colors hover:bg-primary-softer focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                        >
                            MK
                        </button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-56">
                        <DropdownMenuLabel>
                            <div className="flex flex-col">
                                <span className="text-sm font-medium text-text-primary">
                                    Mika Kwan
                                </span>
                                <span className="text-xs text-text-tertiary">
                                    mika@viraldy.demo
                                </span>
                            </div>
                        </DropdownMenuLabel>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                            onSelect={() => toast("Account", { description: "Demo mode" })}
                        >
                            Account
                        </DropdownMenuItem>
                        <DropdownMenuItem onSelect={() => toast("Preferences saved")}>
                            Preferences
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem onSelect={() => toast("Signed out (demo)")}>
                            Sign out
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>

            <SearchCommand open={searchOpen} onOpenChange={setSearchOpen} />
        </header>
    );
}
