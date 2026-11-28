// @vitest-environment jsdom
import { createElement } from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { SmartRemakeDemoPage } from "./smart-remake-demo-page";
import { confirmRemakeMediaRights, emptyRemakeRights } from "../lib/remake-intake";

afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    window.history.replaceState({}, "", "/");
});

it("uses the production clip confirmation modal without submitting a provider or project request", async () => {
    window.history.replaceState({}, "", "/demo/smart-remake?scenario=whole-preview-ready#output");
    const fetch = vi.fn(async (url: string) =>
        Response.json(
            url.endsWith("inspection.json")
                ? {}
                : {
                      project: {
                          id: "fixture",
                          targetDuration: 16,
                          scenes: [],
                          rights: confirmRemakeMediaRights(emptyRemakeRights()),
                          requirements: {
                              intent: "UI fixture",
                              keep: [],
                              replace: [],
                              forbid: [],
                              claims: [],
                              requiresCharacter: false,
                          },
                      },
                  },
        ),
    );
    vi.stubGlobal("fetch", fetch);
    vi.stubGlobal("scrollTo", vi.fn());
    const view = render(createElement(SmartRemakeDemoPage));
    await waitFor(() => expect(screen.getByRole("button", { name: "Sửa Clip 2" })).toBeTruthy());
    expect(
        view.container.querySelector('video[src="/smart-remake/report-demo/whole-preview.mp4"]'),
    ).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Sửa Clip 2" }));
    fireEvent.click(screen.getByRole("button", { name: "Tạo lại clip 2" }));
    expect(await screen.findByRole("heading", { name: "Tạo lại clip 2?" })).toBeTruthy();
    expect(screen.getByText("Clip tạo lại 6 giây")).toBeTruthy();
    expect(screen.getByText(/hai ảnh đầu\/cuối.*1 lượt Wan/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Quay lại" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    fireEvent.click(screen.getByRole("button", { name: "Tạo lại clip 2" }));
    fireEvent.click(await screen.findByRole("button", { name: "Xác nhận và tạo lại clip 2" }));
    await waitFor(() =>
        expect(
            screen.getByText("Đã xác nhận trong bộ minh họa. Không gọi AI hoặc tạo lượt trả phí."),
        ).toBeTruthy(),
    );
    expect(fetch.mock.calls.map(([url]) => url)).toEqual([
        "/smart-remake/report-demo/fixture.json",
        "/smart-remake/report-demo/inspection.json",
    ]);
});
