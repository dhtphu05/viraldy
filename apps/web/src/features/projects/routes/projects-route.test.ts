// @vitest-environment jsdom

import { createElement, type ComponentType, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
    listSmartRemakeProjects,
    type SmartRemakeProjectList,
} from "@/shared/api/smart-remake-library";
import { Route } from "./projects-route";

const workspace = vi.hoisted(() => ({
    id: "workspace-a" as string | undefined,
    loading: false,
    error: false,
    refetch: vi.fn(),
}));

vi.mock("@/shared/hooks/use-workspace", () => ({
    useApiWorkspace: () => ({
        workspaceId: workspace.id,
        workspaces: {
            isLoading: workspace.loading,
            isError: workspace.error,
            refetch: workspace.refetch,
        },
    }),
}));
vi.mock("@/shared/api/smart-remake-library", () => ({ listSmartRemakeProjects: vi.fn() }));
vi.mock("@tanstack/react-router", () => ({
    createFileRoute: () => (options: unknown) => ({ options }),
    Link: ({ to, children }: { to: string; children: ReactNode }) =>
        createElement("a", { href: to }, children),
}));
vi.mock("@/widgets/app-shell/app-shell", () => ({
    AppShell: ({ children }: { children: ReactNode }) => createElement("div", null, children),
}));
vi.mock("@/features/smart-remake/components/remake-player", () => ({
    RemakePlayer: ({ url }: { url: string }) => createElement("video", { src: url }),
}));

const page = (name: string, offset = 0, total = 1): SmartRemakeProjectList => ({
    items: [
        {
            id: `project-${name}`,
            projectName: name,
            createdAt: "2026-11-26T10:00:00Z",
            finalVideoUrl: `https://media.example/${name}.mp4`,
            status: "ready",
            targetDuration: 16,
            provider: "kie",
            videos: [
                {
                    id: "final",
                    label: "Video hoàn chỉnh",
                    kind: "final",
                    url: `https://media.example/${name}.mp4`,
                    durationSeconds: 16,
                },
            ],
        },
    ],
    total,
    limit: 24,
    offset,
});

beforeEach(() => {
    vi.clearAllMocks();
    workspace.id = "workspace-a";
    workspace.loading = false;
    workspace.error = false;
});
afterEach(cleanup);

function renderPage() {
    const client = new QueryClient({ defaultOptions: { queries: { retryDelay: 0 } } });
    const element = () =>
        createElement(
            QueryClientProvider,
            { client },
            createElement(Route.options.component as ComponentType),
        );
    const view = render(element());
    return { ...view, refresh: () => view.rerender(element()) };
}

describe("Project route", () => {
    it("loads persistent videos from the active workspace", async () => {
        vi.mocked(listSmartRemakeProjects).mockResolvedValue(page("Video đã lưu"));
        renderPage();

        expect(await screen.findByText("Video đã lưu")).toBeTruthy();
        expect(listSmartRemakeProjects).toHaveBeenCalledWith("workspace-a", {
            offset: 0,
            signal: expect.any(AbortSignal),
            includeUnfinished: true,
        });
        expect(screen.getByRole("link", { name: "Tạo video" }).getAttribute("href")).toBe(
            "/smart-remake",
        );
    });

    it("clears playback immediately when switching workspaces", async () => {
        vi.mocked(listSmartRemakeProjects).mockImplementation(async (workspaceId) =>
            page(workspaceId),
        );
        const view = renderPage();
        fireEvent.click(await screen.findByRole("button", { name: "Xem video workspace-a" }));
        expect(screen.getByRole("dialog")).toBeTruthy();

        workspace.id = "workspace-b";
        view.refresh();
        expect(screen.queryByRole("dialog")).toBeNull();
        expect(await screen.findByRole("button", { name: "Xem video workspace-b" })).toBeTruthy();
        expect(screen.queryByText("workspace-a")).toBeNull();
    });

    it("loads another page from the server", async () => {
        vi.mocked(listSmartRemakeProjects).mockImplementation(async (_, options) =>
            page(options?.offset === 24 ? "Trang hai" : "Trang đầu", options?.offset, 25),
        );
        renderPage();
        await screen.findByText("Trang đầu");
        fireEvent.click(screen.getByRole("button", { name: "Trang sau" }));

        expect(await screen.findByText("Trang hai")).toBeTruthy();
        expect(listSmartRemakeProjects).toHaveBeenLastCalledWith("workspace-a", {
            offset: 24,
            signal: expect.any(AbortSignal),
            includeUnfinished: true,
        });
    });

    it("returns to an available page when saved outputs disappear from the current page", async () => {
        let total = 25;
        vi.mocked(listSmartRemakeProjects).mockImplementation(async (_, options) => {
            const offset = options?.offset ?? 0;
            return offset >= total
                ? { items: [], total, limit: 24, offset }
                : page(offset === 24 ? "Trang hai" : "Trang đầu", offset, total);
        });
        renderPage();
        await screen.findByText("Trang đầu");
        fireEvent.click(screen.getByRole("button", { name: "Trang sau" }));
        await screen.findByText("Trang hai");

        total = 24;
        fireEvent.click(screen.getByRole("button", { name: "Làm mới" }));
        expect(await screen.findByText("Trang đầu")).toBeTruthy();
        expect(screen.queryByText("Chưa có video đã lưu")).toBeNull();
    });

    it("distinguishes workspace loading, failure, and absence", async () => {
        workspace.id = undefined;
        workspace.loading = true;
        const view = renderPage();
        expect(screen.getByRole("status").textContent).toContain("Đang mở workspace");
        expect(listSmartRemakeProjects).not.toHaveBeenCalled();

        workspace.loading = false;
        workspace.error = true;
        view.refresh();
        expect(screen.getByRole("alert").textContent).toContain("Chưa mở được workspace");
        fireEvent.click(screen.getByRole("button", { name: "Thử lại" }));
        expect(workspace.refetch).toHaveBeenCalledOnce();

        workspace.error = false;
        view.refresh();
        await waitFor(() => expect(screen.getByText("Chưa có workspace")).toBeTruthy());
    });
});
