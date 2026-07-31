import { describe, expect, it } from "vitest";

import { deriveRuntimeStatus } from "./runtime-status";

const capabilities = {
    text_chat: true,
    vision_chat: true,
    audio_transcription: true,
    json_schema: true,
    image_url: true,
    base64_image: true,
};

describe("deriveRuntimeStatus", () => {
    it("does not present fixture mode as a live runtime", () => {
        const status = deriveRuntimeStatus({
            backendConfigured: true,
            loading: false,
            error: null,
            readiness: {
                mode: "fixture",
                provider: "fixture",
                configured: true,
                capabilities,
                missing: [],
            },
        });

        expect(status).toMatchObject({
            label: "Fixture runtime",
            tone: "info",
            active: false,
            provider: "fixture",
        });
        expect(status.message).toContain("no model request");
    });

    it("labels mock mode without implying live qualification", () => {
        const status = deriveRuntimeStatus({
            backendConfigured: true,
            loading: false,
            error: null,
            readiness: {
                mode: "mock",
                provider: "openai-compatible",
                configured: true,
                capabilities,
                missing: [],
            },
        });

        expect(status.label).toBe("Mock runtime");
        expect(status.provider).toBe("openai-compatible");
        expect(status.message).toContain("does not qualify");
    });

    it("keeps live provider configuration separate from qualification", () => {
        const status = deriveRuntimeStatus({
            backendConfigured: true,
            loading: false,
            error: null,
            readiness: {
                mode: "live",
                provider: "openai",
                configured: true,
                capabilities,
                missing: [],
            },
        });

        expect(status).toMatchObject({
            label: "Live provider configured",
            tone: "ok",
            active: true,
            provider: "openai",
        });
        expect(status.message).toContain("Qualification status is evaluated separately");
    });

    it("reports an unconfigured mock provider as not ready", () => {
        const status = deriveRuntimeStatus({
            backendConfigured: true,
            loading: false,
            error: null,
            readiness: {
                mode: "mock",
                provider: "openai-compatible",
                configured: false,
                capabilities,
                missing: ["AI_API_KEY"],
            },
        });

        expect(status).toMatchObject({
            label: "Provider not ready",
            tone: "warn",
            active: false,
        });
        expect(status.message).toContain("AI API Key");
        expect(status.message).not.toContain("AI_API_KEY");
    });
});
