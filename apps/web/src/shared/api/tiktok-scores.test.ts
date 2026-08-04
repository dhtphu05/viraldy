import { afterEach, describe, expect, expectTypeOf, it, vi } from "vitest";

import {
    buildTikTokScoreListPath,
    createTikTokScore,
    scoreProfilePath,
    trackTikTokScoreEvent,
} from "./tiktok-scores";
import type { TikTokScoreEventInput } from "./tiktok-scores";

afterEach(() => {
    vi.unstubAllGlobals();
});

describe("TikTok score API", () => {
    it("reserves lifecycle analytics for authoritative server emitters", () => {
        type ClientEvent = TikTokScoreEventInput["eventType"];

        expectTypeOf<"tiktok_score_started">().not.toMatchTypeOf<ClientEvent>();
        expectTypeOf<"tiktok_score_completed">().not.toMatchTypeOf<ClientEvent>();
        expectTypeOf<"tiktok_score_failed">().not.toMatchTypeOf<ClientEvent>();
        expectTypeOf<"tiktok_revision_uploaded">().not.toMatchTypeOf<ClientEvent>();
        expectTypeOf<"tiktok_evidence_opened">().toMatchTypeOf<ClientEvent>();
    });

    it("builds an encoded workspace history path with only active filters", () => {
        expect(
            buildTikTokScoreListPath("workspace/one", {
                search: "coffee demo",
                status: "completed",
                score_mode: "all",
                limit: 20,
                offset: 40,
            }),
        ).toBe(
            "/workspaces/workspace%2Fone/tiktok-scores?search=coffee+demo&status=completed&limit=20&offset=40",
        );
        expect(scoreProfilePath("workspace/one")).toBe(
            "/workspaces/workspace%2Fone/tiktok-score-profiles",
        );
    });

    it("sends one idempotency key in both the canonical body and request header", async () => {
        const fetchMock = vi.fn().mockResolvedValue(
            new Response(
                JSON.stringify({
                    success: true,
                    data: {
                        score_run: {
                            id: "score-1",
                            status: "queued",
                            asset_version_id: "version-1",
                        },
                        job: { id: "job-1", status: "queued" },
                    },
                    error: null,
                    request_id: "request-1",
                }),
                { status: 202, headers: { "Content-Type": "application/json" } },
            ),
        );
        vi.stubGlobal("fetch", fetchMock);

        const response = await createTikTokScore("workspace-1", {
            assetId: "asset-1",
            assetVersionId: "version-1",
            productId: null,
            mode: "quick",
            intendedUse: "tiktok_organic",
            profile: "general_tiktok_v1",
            profileSelectionMode: "user_selected",
            profileSelectionConfidence: null,
            creativeDirectionContextId: null,
            idempotencyKey: "score-submit-1",
        });

        const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
        expect(init.headers).toMatchObject({
            "Content-Type": "application/json",
            "Idempotency-Key": "score-submit-1",
        });
        expect(JSON.parse(String(init.body))).toMatchObject({
            asset_id: "asset-1",
            asset_version_id: "version-1",
            score_mode: "quick",
            score_profile: "general_tiktok_v1",
            idempotency_key: "score-submit-1",
        });
        expect(response.run.id).toBe("score-1");
        expect(response.jobId).toBe("job-1");
    });

    it("keeps analytics best effort and strips media content from its payload", async () => {
        const fetchMock = vi.fn().mockRejectedValue(new TypeError("offline"));
        vi.stubGlobal("fetch", fetchMock);

        await expect(
            trackTikTokScoreEvent({
                eventType: "tiktok_evidence_opened",
                workspaceId: "workspace-1",
                scoreRunId: "score-1",
                assetVersionId: "version-1",
                evidenceId: "evidence-1",
                mode: "quick",
                profile: "general_tiktok_v1",
                intendedUse: "tiktok_organic",
            }),
        ).resolves.toBeUndefined();

        const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
        expect(url).toBe("/api/backend/workspaces/workspace-1/tiktok-scores/score-1/events");
        const body = JSON.parse(String(init.body));
        expect(body).toEqual({
            event_type: "tiktok_evidence_opened",
            asset_version_id: "version-1",
            evidence_id: "evidence-1",
            score_mode: "quick",
            score_profile: "general_tiktok_v1",
            intended_use: "tiktok_organic",
        });
        expect(JSON.stringify(body)).not.toMatch(/transcript|ocr|media|url/i);
    });

    it("uses the workspace-scoped endpoint when opening the scorer without a run", async () => {
        const fetchMock = vi.fn().mockResolvedValue(
            new Response(JSON.stringify({ success: true, data: null, error: null }), {
                status: 202,
                headers: { "Content-Type": "application/json" },
            }),
        );
        vi.stubGlobal("fetch", fetchMock);

        await trackTikTokScoreEvent({
            eventType: "tiktok_scorer_opened",
            workspaceId: "workspace-1",
        });

        const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
        expect(url).toBe("/api/backend/workspaces/workspace-1/tiktok-scores/events");
        expect(JSON.parse(String(init.body))).toEqual({
            event_type: "tiktok_scorer_opened",
        });
    });
});
