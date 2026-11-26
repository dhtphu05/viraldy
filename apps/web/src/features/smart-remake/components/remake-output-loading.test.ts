import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { expect, it, vi } from "vitest";
import type { SmartRemakeProject } from "@/shared/api/smart-remake";
import { RemakeOutput } from "./remake-output";

const props = {
    workspaceId: "workspace",
    result: null,
    busy: false,
    onRepair: vi.fn(),
    onAccept: vi.fn(),
    onRefresh: vi.fn(),
};
const project: SmartRemakeProject = {
    id: "project",
    revision: 1,
    status: "incomplete",
    provider: "kie",
    targetDuration: 8,
    finalVideoUrl: "",
    scenes: [],
};

it("animates confirmed pending generation without claiming a percentage or completed result", () => {
    const html = renderToStaticMarkup(
        createElement(RemakeOutput, {
            ...props,
            project: {
                ...project,
                pendingOperation: { id: "job", status: "running", needsReconciliation: false },
            },
        }),
    );
    expect(html).toContain('data-active="true"');
    expect(html).toContain("Kết quả sẽ tự cập nhật");
    expect(html).not.toContain('role="progressbar"');
});

it("does not suggest active generation when the previous result needs reconciliation", () => {
    const html = renderToStaticMarkup(
        createElement(RemakeOutput, {
            ...props,
            project: {
                ...project,
                pendingOperation: { id: "job", status: "running", needsReconciliation: true },
            },
        }),
    );
    expect(html).not.toContain('data-active="true"');
    expect(html).toContain("Chưa xác định được kết quả");
    expect(html).toContain("Kiểm tra lại");
});

it("keeps fixture mode distinct from actual video generation", () => {
    const html = renderToStaticMarkup(
        createElement(RemakeOutput, {
            ...props,
            project: null,
            result: { status: "running", provider: "fixture", finalVideoUrl: "" },
        }),
    );
    expect(html).not.toContain('data-active="true"');
    expect(html).toContain("Chế độ kiểm tra không tạo video");
});
