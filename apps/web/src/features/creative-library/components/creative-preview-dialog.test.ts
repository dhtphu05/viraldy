import { createElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { CreativeReference } from "../types/creative";
import {
    consumeSmartRemakeHandoff,
    setSmartRemakeHandoff,
    type SmartRemakeHandoff,
} from "@/features/smart-remake/lib/smart-remake-handoff";

const mocks = vi.hoisted(() => ({
    load: vi.fn(),
    navigate: vi.fn(),
    handoff: vi.fn(),
    clearHandoff: vi.fn(),
    confirm: null as (() => void) | null,
    changeOpen: null as ((open: boolean) => void) | null,
}));
vi.mock("@tanstack/react-router", () => ({ useNavigate: () => mocks.navigate }));
vi.mock("@/features/smart-remake/lib/remake-library", () => ({
    loadRemakeLibraryVideo: mocks.load,
}));
vi.mock("@/features/smart-remake/lib/smart-remake-handoff", async (importOriginal) => {
    const actual =
        await importOriginal<typeof import("@/features/smart-remake/lib/smart-remake-handoff")>();
    return {
        ...actual,
        setSmartRemakeHandoff: (handoff: SmartRemakeHandoff) => {
            mocks.handoff(handoff);
            actual.setSmartRemakeHandoff(handoff);
        },
        clearSmartRemakeHandoff: (handoff: SmartRemakeHandoff) => {
            mocks.clearHandoff(handoff);
            actual.clearSmartRemakeHandoff(handoff);
        },
    };
});
vi.mock("@/shared/ui/dialog", async () => {
    const { createElement } = await import("react");
    const part = ({ children, className }: { children?: ReactNode; className?: string }) =>
        createElement("div", { className }, children);
    return {
        Dialog: ({
            children,
            open,
            onOpenChange,
        }: {
            children: ReactNode;
            open: boolean;
            onOpenChange(open: boolean): void;
        }) => {
            mocks.changeOpen = onOpenChange;
            return open ? createElement("section", null, children) : null;
        },
        DialogClose: ({ children }: { children: ReactNode }) => children,
        DialogContent: part,
        DialogDescription: part,
        DialogHeader: part,
        DialogTitle: part,
    };
});
vi.mock("@/shared/ui/button", async () => {
    const { createElement } = await import("react");
    return {
        Button: (props: { children?: ReactNode; "aria-label"?: string; onClick?: () => void }) => {
            if (props["aria-label"] === "Dùng video làm mẫu trong Smart Remake")
                mocks.confirm = props.onClick ?? null;
            return createElement("button", props, props.children);
        },
    };
});
import { CreativePreviewDialog } from "./creative-preview-dialog";
const creative: CreativeReference = {
    id: "video",
    title: "Video tham khảo",
    hookExcerpt: "Cách mở nắp",
    platform: "TikTok",
    durationSec: 12,
    mediaKind: "video",
    mediaUrl: "/video.mp4",
    mediaAspectRatio: "9:16",
    brandOrCreator: "Shop",
    angle: "Product demonstration",
    category: "Home & Kitchen",
    tags: [],
    boardIds: [],
    analysisStatus: "unanalyzed",
    savedAt: "",
    thumbSeed: "video",
};
function mount() {
    const onOpenChange = vi.fn();
    const html = renderToStaticMarkup(
        createElement(CreativePreviewDialog, { creative, onOpenChange }),
    );
    return { html, onOpenChange };
}
beforeEach(() => {
    vi.clearAllMocks();
    consumeSmartRemakeHandoff();
    mocks.confirm = null;
    mocks.changeOpen = null;
    mocks.navigate.mockResolvedValue(undefined);
});
describe("CreativePreviewDialog", () => {
    it("previews natively without importing or generating until explicit confirmation", () => {
        const { html } = mount();
        expect(html).toContain('controls=""');
        expect(html).toContain("object-contain");
        expect(html).not.toContain("autoPlay");
        expect(html).not.toContain('muted=""');
        expect(html).toContain("Lưu trên trình duyệt này");
        expect(html).toContain("Chưa chạy phân tích hoặc tạo video");
        expect(mocks.load).not.toHaveBeenCalled();
        expect(mocks.handoff).not.toHaveBeenCalled();
    });
    it("hands only the chosen video to Smart Remake and stays open until navigation succeeds", async () => {
        const file = new File(["video"], "source.mp4", { type: "video/mp4" });
        mocks.load.mockResolvedValue(file);
        let completeNavigation!: () => void;
        mocks.navigate.mockReturnValue(
            new Promise<void>((resolve) => {
                completeNavigation = resolve;
            }),
        );
        const { onOpenChange } = mount();
        mocks.confirm!();
        await vi.waitFor(() =>
            expect(mocks.navigate).toHaveBeenCalledWith({ to: "/smart-remake" }),
        );
        expect(mocks.handoff).toHaveBeenCalledWith({ referenceVideo: file, productImages: [] });
        expect(onOpenChange).not.toHaveBeenCalled();
        mocks.changeOpen!(false);
        expect(onOpenChange).not.toHaveBeenCalled();
        expect((mocks.load.mock.calls[0][1] as AbortSignal).aborted).toBe(false);
        completeNavigation();
        await vi.waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
        expect(mocks.clearHandoff).not.toHaveBeenCalled();
    });
    it("cancels a pending download on close and suppresses its late result", async () => {
        let completeDownload!: (file: File) => void;
        mocks.load.mockReturnValue(
            new Promise<File>((resolve) => {
                completeDownload = resolve;
            }),
        );
        const { onOpenChange } = mount();
        mocks.confirm!();
        mocks.confirm!();
        expect(mocks.load).toHaveBeenCalledTimes(1);
        const signal = mocks.load.mock.calls[0][1] as AbortSignal;
        mocks.changeOpen!(false);
        expect(signal.aborted).toBe(true);
        completeDownload(new File(["video"], "source.mp4", { type: "video/mp4" }));
        await Promise.resolve();
        await Promise.resolve();
        expect(mocks.handoff).not.toHaveBeenCalled();
        expect(mocks.navigate).not.toHaveBeenCalled();
        expect(onOpenChange).toHaveBeenCalledWith(false);
    });
    it("keeps failed downloads open and releases the request so the seller can retry", async () => {
        mocks.load.mockRejectedValueOnce(new Error("Chưa mở được file"));
        const { onOpenChange } = mount();
        mocks.confirm!();
        await vi.waitFor(() => expect(mocks.load).toHaveBeenCalledTimes(1));
        await Promise.resolve();
        expect(onOpenChange).not.toHaveBeenCalled();
        expect(mocks.navigate).not.toHaveBeenCalled();
        mocks.load.mockResolvedValueOnce(new File(["video"], "source.mp4", { type: "video/mp4" }));
        mocks.confirm!();
        await vi.waitFor(() => expect(mocks.navigate).toHaveBeenCalledTimes(1));
    });
    it("clears its handoff on failed navigation so a later visit cannot import it", async () => {
        mocks.load.mockResolvedValue(new File(["video"], "source.mp4", { type: "video/mp4" }));
        mocks.navigate.mockRejectedValueOnce(new Error("Chưa mở được trang"));
        const { onOpenChange } = mount();
        mocks.confirm!();
        await vi.waitFor(() => expect(mocks.clearHandoff).toHaveBeenCalledTimes(1));
        expect(mocks.clearHandoff).toHaveBeenCalledWith(mocks.handoff.mock.calls[0][0]);
        expect(consumeSmartRemakeHandoff()).toBeNull();
        expect(onOpenChange).not.toHaveBeenCalled();
        mocks.changeOpen!(false);
        expect(onOpenChange).toHaveBeenCalledWith(false);
    });
    it("does not clear another handoff when its navigation fails late", async () => {
        mocks.load.mockResolvedValue(new File(["video"], "source.mp4", { type: "video/mp4" }));
        let failNavigation!: (cause: Error) => void;
        mocks.navigate.mockReturnValue(
            new Promise<void>((_, reject) => {
                failNavigation = reject;
            }),
        );
        mount();
        mocks.confirm!();
        await vi.waitFor(() => expect(mocks.navigate).toHaveBeenCalledTimes(1));
        const newer: SmartRemakeHandoff = {
            referenceVideo: new File(["newer"], "newer.mp4", { type: "video/mp4" }),
            productImages: [],
        };
        setSmartRemakeHandoff(newer);
        failNavigation(new Error("Chưa mở được trang"));
        await vi.waitFor(() => expect(mocks.clearHandoff).toHaveBeenCalledTimes(1));
        expect(consumeSmartRemakeHandoff()).toBe(newer);
    });
});
