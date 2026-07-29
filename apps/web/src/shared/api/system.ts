import { apiGet } from "./client";

export type AiCapabilities = {
    text_chat: boolean;
    vision_chat: boolean;
    audio_transcription: boolean;
    json_schema: boolean;
    image_url: boolean;
    base64_image: boolean;
};

export type AiReadiness = {
    mode: string;
    provider: string;
    configured: boolean;
    capabilities: AiCapabilities;
    missing: string[];
};

export function getAiReadiness() {
    return apiGet<AiReadiness>("/system/ai-readiness");
}
