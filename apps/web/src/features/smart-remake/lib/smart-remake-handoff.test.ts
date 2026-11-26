import { beforeEach, describe, expect, it } from "vitest";

import { consumeSmartRemakeHandoff, setSmartRemakeHandoff } from "./smart-remake-handoff";

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
});
