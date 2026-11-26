import { beforeEach, describe, expect, it } from "vitest";

import {
    clearSmartRemakeHandoff,
    consumeSmartRemakeHandoff,
    setSmartRemakeHandoff,
} from "./smart-remake-handoff";

function fakeFile(name: string) {
    return { name, type: "video/mp4", size: 16 } as File;
}

describe("Smart Remake handoff", () => {
    beforeEach(() => {
        consumeSmartRemakeHandoff();
    });

    it("passes the selected video and every uploaded product image once", () => {
        const referenceVideo = fakeFile("viral-reference.mp4");
        const productImages = [fakeFile("front.png"), fakeFile("side.png")];

        setSmartRemakeHandoff({ referenceVideo, productImages });

        expect(consumeSmartRemakeHandoff()).toEqual({ referenceVideo, productImages });
        expect(consumeSmartRemakeHandoff()).toBeNull();
    });

    it("returns no handoff when navigation did not originate from the demo finder", () => {
        expect(consumeSmartRemakeHandoff()).toBeNull();
    });

    it("clears a failed navigation's own transfer before a later Smart Remake visit", () => {
        const handoff = { referenceVideo: fakeFile("failed.mp4"), productImages: [] };
        setSmartRemakeHandoff(handoff);
        clearSmartRemakeHandoff(handoff);
        expect(consumeSmartRemakeHandoff()).toBeNull();
    });

    it("does not clear a newer transfer when an older navigation fails", () => {
        const older = { referenceVideo: fakeFile("older.mp4"), productImages: [] };
        const newer = { referenceVideo: fakeFile("newer.mp4"), productImages: [] };
        setSmartRemakeHandoff(older);
        setSmartRemakeHandoff(newer);
        clearSmartRemakeHandoff(older);
        expect(consumeSmartRemakeHandoff()).toBe(newer);
    });
});
