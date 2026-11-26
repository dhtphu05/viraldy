// @vitest-environment jsdom
import { describe, expect, it } from "vitest";
import { Blob as NativeBlob } from "node:buffer";
import { hashRemakeFile } from "./remake-media-binding";

describe("retained media byte binding", () => {
    it("accepts native binary Blobs without converting media to text", async () => {
        const blob = new NativeBlob(["source"]);
        expect(await hashRemakeFile(blob as unknown as Blob)).toBe(
            "41cf6794ba4200b839c53531555f0f3998df4cbb01a4d5cb0b94e3ca5e23947d",
        );
    });
    it("hashes actual bytes rather than filename or File object identity", async () => {
        const first = new File(["source"], "one.mp4", { type: "video/mp4" });
        const restored = new File(["source"], "restored.mov", { type: "video/quicktime" });
        const changed = new File(["changed"], "one.mp4", { type: "video/mp4" });
        expect(await hashRemakeFile(first)).toBe(
            "41cf6794ba4200b839c53531555f0f3998df4cbb01a4d5cb0b94e3ca5e23947d",
        );
        expect(await hashRemakeFile(restored)).toBe(await hashRemakeFile(first));
        expect(await hashRemakeFile(changed)).not.toBe(await hashRemakeFile(first));
    });
});
