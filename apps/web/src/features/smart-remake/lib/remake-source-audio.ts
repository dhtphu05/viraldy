import type { SmartRemakeSourceAudio } from "@/shared/api/smart-remake";

const statuses = new Set(["present", "not_detected", "unclear"]);
const paces = new Set(["slow", "medium", "fast", "unclear"]);

export function getRemakeSourceAudio(value: unknown): SmartRemakeSourceAudio | null {
    if (!value || typeof value !== "object") return null;
    const raw = value as Record<string, unknown>;
    if (
        raw.schemaVersion !== 1 ||
        typeof raw.speech !== "string" ||
        !statuses.has(raw.speech) ||
        typeof raw.music !== "string" ||
        !statuses.has(raw.music)
    )
        return null;
    const text = (field: string, limit: number) =>
        typeof raw[field] === "string" ? raw[field].trim().slice(0, limit) : undefined;
    return {
        schemaVersion: 1,
        speech: raw.speech as SmartRemakeSourceAudio["speech"],
        music: raw.music as SmartRemakeSourceAudio["music"],
        ...(raw.speech === "present"
            ? { transcript: text("transcript", 4000), language: text("language", 40) }
            : {}),
        ...(raw.music === "present" ? { description: text("description", 300) } : {}),
        ...(typeof raw.pace === "string" && paces.has(raw.pace)
            ? { pace: raw.pace as SmartRemakeSourceAudio["pace"] }
            : {}),
    };
}
