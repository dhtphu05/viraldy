import { AppHeader } from "./app-header";
import { AppSidebar } from "./app-sidebar";
import type { ReactNode } from "react";

export function AppShell({ children, footer }: { children: ReactNode; footer?: ReactNode }) {
    return (
        <div className="flex h-dvh w-full overflow-hidden bg-background">
            <AppSidebar />
            <div className="flex min-w-0 flex-1 flex-col">
                <AppHeader />
                <main className="app-scroll-container min-h-0 flex-1 overflow-y-auto">
                    <div className="mx-auto w-full max-w-[1600px] px-4 py-6 sm:px-6 sm:py-8 lg:px-10">
                        {children}
                    </div>
                </main>
                {footer && (
                    <footer
                        aria-label="Page actions"
                        className="shrink-0 bg-background px-4 pb-[max(0.75rem,env(safe-area-inset-bottom))] sm:px-6 lg:px-10"
                    >
                        <div className="mx-auto w-full max-w-[1600px]">{footer}</div>
                    </footer>
                )}
            </div>
        </div>
    );
}
