import type { AppState } from "../store-types";
import type { StoreSet } from "../slice-types";

export function createShellSlice(set: StoreSet): Partial<AppState> {
    return {
        toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
        setSidebarCollapsed: (v) => set({ sidebarCollapsed: v }),
        setCurrentWorkspace: (id) => set({ currentWorkspaceId: id }),
    };
}
