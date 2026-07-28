import { AppHeader } from "./app-header";
import { AppSidebar } from "./app-sidebar";
import type { ReactNode } from "react";

export function AppShell({ children }: { children: ReactNode }) {
    return (
        <div className="flex h-dvh w-full overflow-hidden bg-background">
            <AppSidebar />
            <div className="flex min-w-0 flex-1 flex-col">
                <AppHeader />
                <main className="min-h-0 flex-1 overflow-y-auto">
                    <div className="mx-auto w-full max-w-[1600px] px-4 py-6 sm:px-6 sm:py-8 lg:px-10">
                        {children}
                    </div>
                </main>
            </div>
        </div>
    );
}
