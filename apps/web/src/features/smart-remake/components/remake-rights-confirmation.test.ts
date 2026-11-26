// @vitest-environment jsdom
import { createElement, useState } from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { RemakeRightsConfirmation } from "./remake-rights-confirmation";
import { emptyRemakeRights } from "../lib/remake-intake";

afterEach(cleanup);

function renderModal() {
    const onConfirm = vi.fn();
    function Fixture() {
        const [open, setOpen] = useState(true);
        return createElement(RemakeRightsConfirmation, {
            open,
            onOpenChange: setOpen,
            rights: emptyRemakeRights(),
            onConfirm,
        });
    }
    render(createElement(Fixture));
    return onConfirm;
}

describe("media rights confirmation", () => {
    it("starts unchecked, links to the full policy without replacing uploads, and needs both choices", () => {
        const onConfirm = renderModal();
        const checks = screen.getAllByRole("checkbox") as HTMLInputElement[];
        expect(checks).toHaveLength(2);
        expect(checks.every((check) => !check.checked)).toBe(true);
        const link = screen.getByRole("link", { name: /Đọc chính sách đầy đủ/ });
        expect(link.getAttribute("href")).toBe("/policies/media-rights");
        expect(link.getAttribute("target")).toBe("_blank");
        const save = screen.getByRole("button", { name: "Lưu xác nhận" }) as HTMLButtonElement;
        expect(save.disabled).toBe(true);
        fireEvent.click(checks[0]);
        expect(save.disabled).toBe(true);
        fireEvent.click(checks[1]);
        expect(save.disabled).toBe(false);
        fireEvent.click(save);
        expect(onConfirm).toHaveBeenCalledWith(
            expect.objectContaining({
                source: expect.objectContaining({
                    basis: "attested",
                    declared: true,
                    scope: "",
                    evidenceNote: "",
                }),
                product: expect.objectContaining({ basis: "attested", declared: true }),
                providerDisclosureAcknowledged: true,
                attestation: { policyVersion: "smart-remake-media-rights-v1", accepted: true },
            }),
        );
        expect(screen.queryByRole("dialog")).toBeNull();
    });
    it("returns focus to the opening button after Escape", async () => {
        function FocusFixture() {
            const [open, setOpen] = useState(false);
            return createElement(
                "div",
                null,
                createElement("button", { onClick: () => setOpen(true) }, "Đọc và xác nhận"),
                createElement(RemakeRightsConfirmation, {
                    open,
                    onOpenChange: setOpen,
                    rights: emptyRemakeRights(),
                    onConfirm: vi.fn(),
                }),
            );
        }
        render(createElement(FocusFixture));
        const trigger = screen.getByRole("button", { name: "Đọc và xác nhận" });
        trigger.focus();
        fireEvent.click(trigger);
        expect(screen.getByRole("dialog")).toBeTruthy();
        fireEvent.keyDown(document, { key: "Escape", code: "Escape" });
        await waitFor(() => expect(document.activeElement).toBe(trigger));
    });
    it("cancel and Escape close without accepting rights", () => {
        const onConfirm = renderModal();
        fireEvent.click(screen.getAllByRole("checkbox")[0]);
        fireEvent.click(screen.getByRole("button", { name: "Để sau" }));
        expect(onConfirm).not.toHaveBeenCalled();
        cleanup();
        const escapeConfirm = renderModal();
        fireEvent.keyDown(document, { key: "Escape", code: "Escape" });
        expect(escapeConfirm).not.toHaveBeenCalled();
        expect(screen.queryByRole("dialog")).toBeNull();
    });
});
