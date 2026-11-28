// @vitest-environment jsdom
import { createElement } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { SmartRemakeCompileResult } from "@/shared/api/smart-remake";
import * as previewApi from "@/shared/api/smart-remake-prompt-preview";
import { RemakePlannedKiePrompts } from "./remake-kie-prompt-preview";
import { updateRemakeScene } from "../lib/remake-studio";
import { RemakeStoryboard } from "./remake-storyboard";

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
});

function compiled(videoPrompt = "Current motion"): SmartRemakeCompileResult {
    return {
        projectId: "project",
        revision: 2,
        schemaVersion: 2,
        inputSummary: { targetDuration: 8, aspectRatio: "9:16", language: "vi" },
        compiledPrompts: [],
        renderPlan: {
            fps: 24,
            groups: [{ id: "group", renderUnitIds: ["unit"], targetDurationFrames: 192 }],
            units: [
                {
                    id: "unit",
                    targetDurationFrames: 192,
                    prompt: "Intent",
                    imagePrompt: "Image",
                    videoPrompt: "Current motion",
                },
            ],
        },
        sceneMap: { scenes: [{ prompt: "Intent", imagePrompt: "Image", videoPrompt }] },
    } as unknown as SmartRemakeCompileResult;
}
const result = (prompt: string) => ({
    projectId: "project",
    revision: 4,
    groups: [{ groupId: "group", model: "wan/3-0-video", prompt }],
});
const props = { workspaceId: "workspace", projectRevision: 4, compileResult: compiled() };

it("makes KIE prompts discoverable at script review outside the advanced settings fold", () => {
    render(
        createElement(RemakeStoryboard, {
            ...props,
            onSceneChange: vi.fn(),
        }),
    );
    const trigger = screen.getByRole("button", { name: "Clip 1 · Xem prompt KIE" });
    expect(trigger.closest("details")).toBeNull();
    expect(screen.getByRole("region", { name: "Prompt KIE ở bước duyệt kịch bản" })).toBeTruthy();
});

it("keeps both clip prompts above all 24 scene cards for a twelve-second project", async () => {
    const value = compiled();
    const units = Array.from({ length: 24 }, (_, index) => ({
        ...value.renderPlan!.units[0],
        id: `unit-${index + 1}`,
        targetDurationFrames: 12,
    }));
    const groups = [0, 12].map((start, index) => ({
        id: `group-${index + 1}`,
        renderUnitIds: units.slice(start, start + 12).map((unit) => unit.id),
        targetDurationFrames: 144,
        rawDurationFrames: 288,
        segments: [],
    }));
    const preview = vi.spyOn(previewApi, "previewSmartRemakeKiePrompts").mockResolvedValue({
        ...result("unused"),
        groups: groups.map((group) => ({
            groupId: group.id,
            model: "wan/3-0-video",
            prompt: `Planned ${group.id}`,
        })),
    });
    render(
        createElement(RemakeStoryboard, {
            ...props,
            compileResult: {
                ...value,
                inputSummary: { ...value.inputSummary, targetDuration: 12 },
                renderPlan: { ...value.renderPlan!, units, groups },
                sceneMap: {
                    ...value.sceneMap,
                    scenes: units.map(() => ({ ...value.sceneMap.scenes[0] })),
                },
            },
            onSceneChange: vi.fn(),
        }),
    );
    const trigger = screen.getByRole("button", { name: "Clip 2 · Xem prompt KIE" });
    const firstScene = screen.getByRole("heading", { name: /^Cảnh 1$/ });
    expect(
        trigger.compareDocumentPosition(firstScene) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    fireEvent.click(trigger);
    expect(await screen.findByText("Planned group-2")).toBeTruthy();
    expect(preview.mock.calls[0][2].scenePrompts).toHaveLength(24);
});

it("opens and copies a planned prompt in review without creating a video", async () => {
    const preview = vi
        .spyOn(previewApi, "previewSmartRemakeKiePrompts")
        .mockResolvedValue(result("Exact planned prompt\n<script>literal</script>"));
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
    render(createElement(RemakePlannedKiePrompts, props));
    expect(preview).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Clip 1 · Xem prompt KIE" }));
    expect(await screen.findByText("Prompt sẽ gửi KIE")).toBeTruthy();
    expect(document.body.textContent).not.toContain("Prompt đã gửi KIE");
    expect(document.querySelector("pre")?.textContent).toBe(
        "Exact planned prompt\n<script>literal</script>",
    );
    expect(document.querySelector("script")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Sao chép prompt" }));
    await waitFor(() =>
        expect(writeText).toHaveBeenCalledWith("Exact planned prompt\n<script>literal</script>"),
    );
    expect(preview).toHaveBeenCalledTimes(1);
    expect(preview.mock.calls[0].slice(0, 3)).toEqual([
        "workspace",
        "project",
        {
            expectedRevision: 4,
            scenePrompts: [
                {
                    renderUnitId: "unit",
                    prompt: "Intent",
                    imagePrompt: "Image",
                    videoPrompt: "Current motion",
                },
            ],
        },
    ]);
});

it("sends local prompt edits directly and never replaces them with the saved plan text", async () => {
    const preview = vi
        .spyOn(previewApi, "previewSmartRemakeKiePrompts")
        .mockResolvedValue(result("Edited compiled prompt"));
    render(
        createElement(RemakePlannedKiePrompts, {
            ...props,
            compileResult: compiled("Edited movement"),
        }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Clip 1 · Xem prompt KIE" }));
    await screen.findByText("Edited compiled prompt");
    expect(preview.mock.calls[0][2].scenePrompts?.[0].videoPrompt).toBe("Edited movement");
});

it("normalizes only edited fields exactly as generation does and preserves saved whitespace", async () => {
    const preview = vi
        .spyOn(previewApi, "previewSmartRemakeKiePrompts")
        .mockResolvedValue(result("Normalized preview"));
    const saved = compiled("  Saved motion\n ");
    const sceneDrafts = { 0: { imagePrompt: "  New image\n " } };
    const ready = updateRemakeScene(saved, 0, sceneDrafts[0]);
    render(
        createElement(RemakePlannedKiePrompts, {
            ...props,
            compileResult: saved,
            sceneDrafts,
        }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Clip 1 · Xem prompt KIE" }));
    await screen.findByText("Normalized preview");
    expect(preview.mock.calls[0][2].scenePrompts?.[0]).toMatchObject({
        imagePrompt: ready.sceneMap.scenes[0].imagePrompt,
        videoPrompt: ready.sceneMap.scenes[0].videoPrompt,
    });
    expect(preview.mock.calls[0][2].scenePrompts?.[0].videoPrompt).toBe("  Saved motion\n ");
});

it("invalidates the cached prompt and copy state when requirements change", async () => {
    const preview = vi
        .spyOn(previewApi, "previewSmartRemakeKiePrompts")
        .mockResolvedValueOnce(result("OLD_REQUIREMENTS"))
        .mockResolvedValueOnce(result("NEW_REQUIREMENTS"));
    Object.defineProperty(navigator, "clipboard", {
        configurable: true,
        value: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
    const requirements = {
        intent: "Initial intent",
        keep: [],
        replace: [],
        forbid: [],
        claims: [],
        requiresCharacter: false,
    };
    const view = render(createElement(RemakePlannedKiePrompts, { ...props, requirements }));
    fireEvent.click(screen.getByRole("button", { name: "Clip 1 · Xem prompt KIE" }));
    await screen.findByText("OLD_REQUIREMENTS");
    fireEvent.click(screen.getByRole("button", { name: "Sao chép prompt" }));
    await screen.findByRole("button", { name: "Đã sao chép" });
    view.rerender(
        createElement(RemakePlannedKiePrompts, {
            ...props,
            requirements: { ...requirements, intent: "Changed intent" },
        }),
    );
    expect(document.body.textContent).not.toContain("OLD_REQUIREMENTS");
    fireEvent.click(screen.getByRole("button", { name: "Clip 1 · Xem prompt KIE" }));
    await screen.findByText("NEW_REQUIREMENTS");
    expect(screen.getByRole("button", { name: "Sao chép prompt" })).toBeTruthy();
    expect(preview.mock.calls[1][2].requirements?.intent).toBe("Changed intent");
});

it("discards a late preview from an older draft after the scene text changes", async () => {
    let resolveOld!: (value: ReturnType<typeof result>) => void;
    const preview = vi
        .spyOn(previewApi, "previewSmartRemakeKiePrompts")
        .mockImplementationOnce(
            () =>
                new Promise((resolve) => {
                    resolveOld = resolve;
                }),
        )
        .mockResolvedValueOnce(result("NEW_PREVIEW"));
    const view = render(createElement(RemakePlannedKiePrompts, props));
    fireEvent.click(screen.getByRole("button", { name: "Clip 1 · Xem prompt KIE" }));
    expect(preview).toHaveBeenCalledTimes(1);
    view.rerender(
        createElement(RemakePlannedKiePrompts, { ...props, compileResult: compiled("New draft") }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Clip 1 · Xem prompt KIE" }));
    await screen.findByText("NEW_PREVIEW");
    await act(async () => resolveOld(result("OLD_PREVIEW")));
    expect(document.body.textContent).not.toContain("OLD_PREVIEW");
    expect(screen.getByText("NEW_PREVIEW")).toBeTruthy();
});

it("blocks previews for stale cuts/groups and explains missing legacy project data", () => {
    const preview = vi.spyOn(previewApi, "previewSmartRemakeKiePrompts");
    const view = render(createElement(RemakePlannedKiePrompts, { ...props, stale: true }));
    const button = screen.getByRole("button", {
        name: "Clip 1 · Xem prompt KIE",
    }) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    fireEvent.click(button);
    expect(preview).not.toHaveBeenCalled();
    expect(document.body.textContent).toContain("Cập nhật kịch bản");
    view.rerender(createElement(RemakePlannedKiePrompts, { compileResult: compiled() }));
    expect(
        (screen.getByRole("button", { name: "Clip 1 · Xem prompt KIE" }) as HTMLButtonElement)
            .disabled,
    ).toBe(true);
    expect(document.body.textContent).toContain("Chưa có dữ liệu");
});

it("retries a failed preview without touching generation", async () => {
    const preview = vi
        .spyOn(previewApi, "previewSmartRemakeKiePrompts")
        .mockRejectedValueOnce(new Error("offline"))
        .mockResolvedValueOnce(result("Retried preview"));
    render(createElement(RemakePlannedKiePrompts, props));
    fireEvent.click(screen.getByRole("button", { name: "Clip 1 · Xem prompt KIE" }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Thử lại" }));
    expect(await screen.findByText("Retried preview")).toBeTruthy();
    expect(preview).toHaveBeenCalledTimes(2);
});
