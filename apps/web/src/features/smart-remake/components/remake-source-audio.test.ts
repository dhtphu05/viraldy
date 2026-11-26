// @vitest-environment jsdom
import { createElement } from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { SmartRemakeCompileResult, SmartRemakeSourceAudio } from "@/shared/api/smart-remake";
import { getRemakeSourceAudio } from "../lib/remake-source-audio";
import { RemakeSourceAudio } from "./remake-source-audio";
import { RemakeAnalysisLoading } from "./remake-analysis-loading";
import { RemakeStoryboard } from "./remake-storyboard";

afterEach(cleanup);

const audio: SmartRemakeSourceAudio = {
    schemaVersion: 1,
    speech: "present",
    transcript: "Chiếc bình này giữ nước lạnh rất lâu.",
    language: "Tiếng Việt",
    music: "present",
    description: "Nhạc nhẹ với tiếng gõ đều.",
    pace: "medium",
};

const progress = {
    schemaVersion: 1 as const,
    operationId: "compile-operation",
    requestKey: "compile-request",
    status: "running" as const,
    stage: "analyzing_source" as const,
    startedAt: "2026-11-26T09:00:00Z",
    updatedAt: "2026-11-26T09:00:04Z",
    scenes: [],
};

describe("observed source audio", () => {
    it("renders actual transcript, music and rhythm as read-only source observations", () => {
        render(createElement(RemakeSourceAudio, { value: audio }));
        expect(screen.getByRole("region", { name: "Âm thanh trong video mẫu" })).toBeTruthy();
        expect(screen.getByText("AI nhận diện từ video mẫu")).toBeTruthy();
        expect(screen.getByText(audio.transcript!)).toBeTruthy();
        expect(screen.getByText("Tiếng Việt")).toBeTruthy();
        expect(screen.getByText(audio.description!)).toBeTruthy();
        expect(screen.getByText("Nhịp vừa")).toBeTruthy();
        expect(screen.queryByRole("textbox")).toBeNull();
        expect(screen.queryByRole("progressbar")).toBeNull();
        const summary = screen.getByText("Trích lời thoại nghe được");
        summary.focus();
        expect(document.activeElement).toBe(summary);
        const transcript = screen.getByText(audio.transcript!);
        transcript.focus();
        expect(document.activeElement).toBe(transcript);
    });

    it("keeps unknown audio distinct from detected silence or a fabricated transcript", () => {
        render(
            createElement(RemakeSourceAudio, {
                value: { ...audio, speech: "unclear", music: "not_detected", pace: "unclear" },
            }),
        );
        expect(screen.getByText("Chưa nghe rõ lời thoại")).toBeTruthy();
        expect(screen.getByText("Chưa nhận diện nhạc nền")).toBeTruthy();
        expect(screen.getByText("Chưa rõ nhịp")).toBeTruthy();
        expect(screen.queryByText(audio.transcript!)).toBeNull();
        expect(screen.queryByText(audio.description!)).toBeNull();
        expect(document.body.textContent).not.toMatch(/im lặng|không có âm thanh/i);
    });

    it("does not invent observations for missing or malformed historical fields", () => {
        const { container, rerender } = render(createElement(RemakeSourceAudio, {}));
        expect(container.textContent).toBe("");
        rerender(createElement(RemakeSourceAudio, { value: { transcript: "invented" } }));
        expect(container.textContent).toBe("");
        expect(getRemakeSourceAudio({ ...audio, schemaVersion: 2 })).toBeNull();
        expect(getRemakeSourceAudio({ ...audio, speech: "unknown" })).toBeNull();
        expect(getRemakeSourceAudio({ ...audio, music: "unknown" })).toBeNull();
        expect(getRemakeSourceAudio(null)).toBeNull();
    });

    it("escapes transcript markup and bounds optional data from restored JSON", () => {
        render(
            createElement(RemakeSourceAudio, {
                value: {
                    ...audio,
                    transcript: '<script>alert("source")</script>',
                    language: 7,
                    description: "x".repeat(350),
                    pace: "300 BPM",
                },
            }),
        );
        expect(screen.getByText('<script>alert("source")</script>')).toBeTruthy();
        expect(document.querySelector("script")).toBeNull();
        expect(screen.queryByText("300 BPM")).toBeNull();
        expect(screen.getByText("x".repeat(300))).toBeTruthy();
        expect(
            getRemakeSourceAudio({ ...audio, transcript: "x".repeat(4100) })?.transcript,
        ).toHaveLength(4000);
    });

    it("only shows the pending message while a real audio observation request is pending", () => {
        const { rerender } = render(createElement(RemakeSourceAudio, { pending: true }));
        expect(screen.getByText("Đang đọc lời thoại, nhạc và nhịp từ video mẫu.")).toBeTruthy();
        expect(screen.queryByText("Đã nhận diện lời thoại")).toBeNull();
        rerender(
            createElement(RemakeSourceAudio, {
                value: { ...audio, speech: "not_detected", music: "unclear" },
            }),
        );
        expect(screen.getByText("Chưa nhận diện lời thoại")).toBeTruthy();
        expect(screen.getByText("Chưa nghe rõ nhạc nền")).toBeTruthy();
        expect(screen.queryByText("Đang đọc lời thoại, nhạc và nhịp từ video mẫu.")).toBeNull();
    });

    it("prefers detailed audio over quick observations during analysis", () => {
        render(
            createElement(RemakeAnalysisLoading, {
                action: "analyze",
                presentation: "inline",
                phase: "analyzing",
                progress: {
                    ...progress,
                    sourceAudio: audio,
                    quickSummary: {
                        status: "completed",
                        summary: "Đang giới thiệu chiếc bình.",
                        sourceAudio: { ...audio, transcript: "Nhận định sơ bộ." },
                    },
                },
            }),
        );
        expect(screen.getByText(audio.transcript!)).toBeTruthy();
        expect(screen.queryByText("Nhận định sơ bộ.")).toBeNull();
        expect(screen.getByText("AI nhận diện từ video mẫu")).toBeTruthy();
        expect(screen.queryByText("Nhận diện sơ bộ từ video mẫu")).toBeNull();
    });

    it("shows received quick audio and preserves it during status failures", () => {
        render(
            createElement(RemakeAnalysisLoading, {
                action: "analyze",
                presentation: "inline",
                phase: "analyzing",
                statusError: "Chưa lấy được trạng thái.",
                progress: {
                    ...progress,
                    quickSummary: {
                        status: "completed",
                        summary: "Video giới thiệu chiếc bình.",
                        sourceAudio: audio,
                    },
                },
            }),
        );
        expect(screen.getByText(audio.transcript!)).toBeTruthy();
        expect(screen.getByText("Nhận diện sơ bộ từ video mẫu")).toBeTruthy();
        expect(screen.getByRole("alert").textContent).toBe("Chưa lấy được trạng thái.");
    });

    it("never keeps an audio pending indicator after compile failure", () => {
        const { rerender } = render(
            createElement(RemakeAnalysisLoading, {
                action: "analyze",
                presentation: "inline",
                progress: { ...progress, quickSummary: { status: "pending" } },
            }),
        );
        expect(screen.getByText("Đang đọc lời thoại, nhạc và nhịp từ video mẫu.")).toBeTruthy();
        rerender(
            createElement(RemakeAnalysisLoading, {
                action: "analyze",
                presentation: "inline",
                progress: {
                    ...progress,
                    status: "failed",
                    stage: "failed",
                    quickSummary: { status: "pending" },
                },
            }),
        );
        expect(screen.queryByText("Đang đọc lời thoại, nhạc và nhịp từ video mẫu.")).toBeNull();
    });

    it("keeps source observations available in a restored storyboard without exposing generated dialogue as transcript", () => {
        const compiled: SmartRemakeCompileResult = {
            success: true,
            mode: "smart_remake",
            renderSubmitted: false,
            inputSummary: { targetDuration: 8, aspectRatio: "9:16", language: null },
            referenceAnalysis: {
                sourceAudio: audio,
                audioPlan: { dialogue: "Generated voice direction" },
            },
            analyzeOutput: {},
            productLock: {},
            sceneMap: { targetDuration: 8, sceneCount: 0, scenes: [] },
            compiledPrompts: [],
            compilerDiagnostics: {},
            diagnostics: {},
            versions: {},
            warnings: [],
        };
        render(
            createElement(RemakeStoryboard, { compileResult: compiled, onSceneChange: vi.fn() }),
        );
        expect(screen.getByText(audio.transcript!)).toBeTruthy();
        expect(screen.queryByText("Generated voice direction")).toBeNull();
    });
});
