// @vitest-environment jsdom
import { createElement } from "react";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { clipProject, groupCandidate } from "../lib/remake-clip-groups.fixture";
import { RemakeClipGroups } from "./remake-clip-groups";
import { RemakeOutput } from "./remake-output";

afterEach(cleanup);
describe("clip-level review and repair", () => {
    it("keeps exactly two clip cards while the whole preview is being assembled", () => {
        const project = {
            ...clipProject(),
            finalVideoUrl: "",
            assemblies: undefined,
            preview: { schemaVersion: 1 as const, status: "processing" as const },
        };
        render(
            createElement(RemakeOutput, {
                workspaceId: "workspace",
                project,
                result: null,
                guided: true,
                busy: false,
                onRepair: vi.fn(),
                onRepairGroup: vi.fn(),
                onAccept: vi.fn(),
                onRefresh: vi.fn(),
            }),
        );
        expect(screen.getAllByRole("article")).toHaveLength(2);
        expect(
            screen.getByText("Đang ghép bản xem trước 12 giây từ các clip đã tạo."),
        ).toBeTruthy();
        expect(screen.queryByText("Các clip đã sẵn sàng để bạn xem")).toBeNull();
    });
    it("labels the comparison source as a raw clip when Advanced trims differ", () => {
        const { project, receipt } = groupCandidate();
        const timeline = {
            ...project.draftTimeline!,
            items: project.draftTimeline!.items.map((item, index) =>
                index ? item : { ...item, inFrame: 1, outFrame: item.outFrame + 1 },
            ),
        };
        const frozen = timeline.items
            .filter((item) =>
                project.renderPlan!.groups![0].renderUnitIds.includes(item.renderUnitId),
            )
            .map(({ renderUnitId, versionId, inFrame, outFrame }) => ({
                renderUnitId,
                versionId,
                inFrame,
                outFrame,
            }));
        const current = {
            ...project,
            draftTimeline: timeline,
            scenes: project.scenes.map((scene) => ({
                ...scene,
                versions: scene.versions.map((version) =>
                    version.providerMetadata
                        ? {
                              ...version,
                              providerMetadata: {
                                  ...version.providerMetadata,
                                  repairBaseTimeline: frozen,
                              },
                          }
                        : version,
                ),
            })),
        };
        render(
            createElement(RemakeClipGroups, {
                workspaceId: "workspace",
                project: current,
                busy: false,
                repairCandidate: receipt,
                onAccept: vi.fn(),
                onRepairGroup: vi.fn(),
            }),
        );
        fireEvent.click(screen.getByRole("button", { name: "Xem bản mới Clip 1" }));
        expect(screen.getByRole("button", { name: "Clip gốc 1" })).toBeTruthy();
        expect(screen.getByText(/bản 12s phía trên mới phản ánh đoạn cắt/)).toBeTruthy();
        expect(screen.queryByText("Clip 1 đang dùng")).toBeNull();
    });
    it("resets an old group repair draft after an Advanced trim edit and labels the raw clip explicitly", () => {
        const project = clipProject();
        const props = {
            workspaceId: "workspace",
            project,
            busy: false,
            onRepairGroup: vi.fn(),
            onAccept: vi.fn(),
        };
        const view = render(createElement(RemakeClipGroups, props));
        fireEvent.click(screen.getByRole("button", { name: "Sửa Clip 2" }));
        fireEvent.change(screen.getByLabelText("Bạn muốn thay đổi điều gì? (không bắt buộc)"), {
            target: { value: "Yêu cầu dựa trên đoạn cũ" },
        });
        const anchorId = project.renderPlan!.groups![1].renderUnitIds[0];
        const changed = {
            ...project,
            draftTimeline: {
                ...project.draftTimeline!,
                items: project.draftTimeline!.items.map((item) =>
                    item.renderUnitId !== anchorId
                        ? item
                        : { ...item, inFrame: item.inFrame + 1, outFrame: item.outFrame + 1 },
                ),
            },
        };
        view.rerender(createElement(RemakeClipGroups, { ...props, project: changed }));
        expect(screen.getByText(/Đây là clip gốc 6 giây.*bản 12s phía trên/)).toBeTruthy();
        fireEvent.click(screen.getByRole("button", { name: "Sửa Clip 2" }));
        expect(
            (
                screen.getByLabelText(
                    "Bạn muốn thay đổi điều gì? (không bắt buộc)",
                ) as HTMLTextAreaElement
            ).value,
        ).toBe("");
        expect(props.onRepairGroup).not.toHaveBeenCalled();
    });
    it("ignores a stale source-scene selection and opens explicit repair navigation at the clip form", async () => {
        const project = clipProject();
        const props = {
            workspaceId: "workspace",
            project,
            result: null,
            guided: true,
            busy: false,
            initialSceneId: project.scenes[0].id,
            onRepair: vi.fn(),
            onRepairGroup: vi.fn(),
            onAccept: vi.fn(),
            onRefresh: vi.fn(),
        };
        const view = render(createElement(RemakeOutput, props));
        expect(screen.queryByText("Các cảnh sẽ ghép · 12 giây")).toBeNull();
        expect(
            screen
                .getByRole("button", { name: "Nâng cao · Cảnh nguồn và đoạn cắt" })
                .getAttribute("aria-expanded"),
        ).toBe("false");
        expect(screen.getAllByRole("article")).toHaveLength(2);
        view.rerender(
            createElement(RemakeOutput, {
                ...props,
                navigation: {
                    requestId: "repair-second-clip",
                    sceneId: project.renderPlan!.groups![1].renderUnitIds[0],
                    view: "repair",
                },
            }),
        );
        await waitFor(() =>
            expect(screen.getByText("Bạn muốn sửa Clip 2 ở điểm nào?")).toBeTruthy(),
        );
        expect(
            screen
                .getByRole("button", { name: "Nâng cao · Cảnh nguồn và đoạn cắt" })
                .getAttribute("aria-expanded"),
        ).toBe("false");
        expect(props.onRepair).not.toHaveBeenCalled();
        expect(props.onRepairGroup).not.toHaveBeenCalled();
    });
    it("shows two whole clips and submits normal-language repair only for the selected group", async () => {
        const onRepairGroup = vi.fn().mockResolvedValue(null);
        const onAccept = vi.fn();
        render(
            createElement(RemakeClipGroups, {
                workspaceId: "workspace",
                project: clipProject(),
                busy: false,
                onRepairGroup,
                onAccept,
            }),
        );
        expect(screen.getAllByRole("article")).toHaveLength(2);
        expect(screen.getByText("0–6 giây")).toBeTruthy();
        expect(screen.getByText("6–12 giây")).toBeTruthy();
        expect(document.querySelectorAll("video[controls]")).toHaveLength(2);
        expect(screen.queryByText("Dùng đoạn này")).toBeNull();
        expect(onRepairGroup).not.toHaveBeenCalled();
        fireEvent.click(screen.getByRole("button", { name: "Sửa Clip 2" }));
        expect(
            screen.getByText(
                "AI sẽ tạo lại toàn bộ Clip 2 (6 giây). Các clip khác được giữ nguyên.",
            ),
        ).toBeTruthy();
        expect(screen.queryByText("Nâng cao · Prompt tự động")).toBeNull();
        fireEvent.change(screen.getByLabelText("Bạn muốn thay đổi điều gì? (không bắt buộc)"), {
            target: { value: "Giữ đúng tay cầm và mở nắp chậm hơn." },
        });
        fireEvent.click(screen.getByRole("button", { name: "Xem Clip 2" }));
        fireEvent.click(screen.getByRole("button", { name: "Sửa Clip 2" }));
        expect(
            (
                screen.getByLabelText(
                    "Bạn muốn thay đổi điều gì? (không bắt buộc)",
                ) as HTMLTextAreaElement
            ).value,
        ).toContain("Giữ đúng tay cầm");
        fireEvent.click(screen.getByRole("button", { name: "Tạo lại clip 2" }));
        await waitFor(() =>
            expect(onRepairGroup).toHaveBeenCalledWith("fixture-group-2", {
                schemaVersion: 1,
                issues: ["alternate_take"],
                instruction: "Giữ đúng tay cầm và mở nắp chậm hơn.",
            }),
        );
        expect(onAccept).not.toHaveBeenCalled();
    });
    it("never falls back to a scene repair when group submission is not connected", () => {
        render(
            createElement(RemakeClipGroups, {
                workspaceId: "workspace",
                project: clipProject(),
                busy: false,
                onAccept: vi.fn(),
            }),
        );
        expect(
            (screen.getByRole("button", { name: "Sửa Clip 1" }) as HTMLButtonElement).disabled,
        ).toBe(true);
    });
    it("offers only an exact complete group candidate and accepts the anchor once", async () => {
        const { project, receipt } = groupCandidate();
        const onAccept = vi.fn().mockResolvedValue(true);
        render(
            createElement(RemakeClipGroups, {
                workspaceId: "workspace",
                project,
                busy: false,
                onRepairGroup: vi.fn(),
                repairCandidate: receipt,
                onAccept,
            }),
        );
        expect(onAccept).not.toHaveBeenCalled();
        fireEvent.click(screen.getByRole("button", { name: "Xem bản mới Clip 1" }));
        const card = screen.getByRole("article", { name: "Clip 1" });
        expect(
            within(card).getByText(
                "Đây là toàn bộ clip 6 giây. Bản mới chỉ thay thế khi bạn áp dụng.",
            ),
        ).toBeTruthy();
        fireEvent.click(screen.getByRole("button", { name: "Dùng bản mới cho Clip 1" }));
        await waitFor(() =>
            expect(onAccept).toHaveBeenCalledExactlyOnceWith(receipt.sceneId, receipt.versionId),
        );
    });
});
