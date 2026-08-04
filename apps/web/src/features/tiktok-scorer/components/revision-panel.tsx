import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { FileUp, Loader2 } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { validateVideoFile } from "../lib/tiktok-score-view-model";
import type { ScoreProfileCode, TikTokFixAction, TikTokScoreRun } from "../types";
import { queryKeys } from "@/shared/api/query-keys";
import { createTikTokScoreRevision, listTikTokScoreProfiles } from "@/shared/api/tiktok-scores";
import { uploadAssetRevision } from "@/shared/api/uploads";
import { Alert, AlertDescription, AlertTitle } from "@/shared/ui/alert";
import { Button } from "@/shared/ui/button";
import { Progress } from "@/shared/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import { SurfaceCard } from "@/shared/ui/surface-card";

export function RevisionPanel({
    run,
    workspaceId,
    fixes,
}: {
    run: TikTokScoreRun;
    workspaceId: string;
    fixes: TikTokFixAction[];
}) {
    const navigate = useNavigate();
    const [file, setFile] = useState<File | null>(null);
    const [fileError, setFileError] = useState<string | null>(null);
    const [profile, setProfile] = useState<ScoreProfileCode>(run.profile.code);
    const [progress, setProgress] = useState(0);
    const idempotencyRef = useRef<string | null>(null);
    const uploadedVersionRef = useRef<string | null>(null);
    const profiles = useQuery({
        queryKey: queryKeys.tiktokScores.profiles(workspaceId),
        queryFn: () => listTikTokScoreProfiles(workspaceId),
        retry: 0,
    });
    const revision = useMutation({
        mutationFn: async () => {
            if (!run.assetId || !file) {
                throw new Error("The original asset link or revision file is unavailable.");
            }
            const idempotencyKey = idempotencyRef.current ?? crypto.randomUUID();
            idempotencyRef.current = idempotencyKey;
            const assetVersionId =
                uploadedVersionRef.current ??
                (await uploadAssetRevision(workspaceId, run.assetId, file, setProgress)).id;
            uploadedVersionRef.current = assetVersionId;
            const result = await createTikTokScoreRevision(workspaceId, run.id, {
                assetVersionId,
                profile,
                profileOverrideReason:
                    profile === run.profile.code
                        ? null
                        : "Profile overridden during revision upload.",
                acceptedFixActionIds: fixes
                    .filter(
                        (fix) =>
                            fix.latestEvent === "accepted" ||
                            fix.latestEvent === "marked_completed",
                    )
                    .map((fix) => fix.id),
                idempotencyKey,
            });
            return result;
        },
        onSuccess: (result) => {
            if (result.comparisonId) {
                void navigate({
                    to: "/tiktok-scorer/$scoreId/compare/$comparisonId",
                    params: { scoreId: run.id, comparisonId: result.comparisonId },
                    search: { jobId: undefined },
                });
            } else {
                void navigate({
                    to: "/tiktok-scorer/$scoreId",
                    params: { scoreId: result.run.id },
                    search: { jobId: result.jobId ?? undefined },
                });
            }
        },
        onError: (error) =>
            toast.error(error instanceof Error ? error.message : "Revision could not be uploaded"),
    });
    return (
        <SurfaceCard padding="lg">
            <div className="flex items-start gap-3">
                <FileUp className="mt-0.5 h-5 w-5 text-primary" />
                <div>
                    <h2 className="font-semibold text-text-primary">
                        Upload Draft {run.revisionCount + 2}
                    </h2>
                    <p className="mt-1 text-sm text-text-secondary">
                        Creates a new immutable asset version and score run. Draft 1 and its
                        evidence are never overwritten.
                    </p>
                </div>
            </div>
            <dl className="mt-4 grid gap-3 rounded-xl bg-surface-soft p-4 text-sm sm:grid-cols-3">
                <SummaryItem label="Carries forward" value={humanize(run.scoreMode)} />
                <SummaryItem label="Intended use" value={humanize(run.intendedUse)} />
                <SummaryItem label="Profile" value={run.profile.label} />
            </dl>
            {!run.assetId ? (
                <Alert className="mt-4">
                    <AlertTitle>Revision upload unavailable</AlertTitle>
                    <AlertDescription>
                        This score response does not include the source asset ID required to create
                        an immutable revision.
                    </AlertDescription>
                </Alert>
            ) : (
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                    <div>
                        <label
                            className="block text-sm font-medium text-text-primary"
                            htmlFor="score-revision-file"
                        >
                            Revised video
                        </label>
                        <input
                            id="score-revision-file"
                            type="file"
                            accept="video/mp4,video/quicktime,.mp4,.mov"
                            className="mt-2 block w-full text-sm text-text-secondary file:mr-3 file:rounded-md file:border-0 file:bg-primary-soft file:px-3 file:py-2 file:text-primary-active"
                            onChange={(event) => {
                                const next = event.target.files?.[0] ?? null;
                                const error = next ? validateVideoFile(next, null) : null;
                                idempotencyRef.current = null;
                                uploadedVersionRef.current = null;
                                setProgress(0);
                                setFileError(error);
                                setFile(error ? null : next);
                            }}
                        />
                        {fileError && <p className="mt-1 text-sm text-destructive">{fileError}</p>}
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-text-primary">
                            Profile for revision
                        </label>
                        <Select
                            value={profile}
                            onValueChange={(value) => {
                                setProfile(value as ScoreProfileCode);
                                idempotencyRef.current = null;
                            }}
                        >
                            <SelectTrigger className="mt-2">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {profiles.data?.map((item) => (
                                    <SelectItem key={item.code} value={item.code}>
                                        {item.label}
                                    </SelectItem>
                                )) ?? (
                                    <SelectItem value={run.profile.code}>
                                        {run.profile.label}
                                    </SelectItem>
                                )}
                            </SelectContent>
                        </Select>
                    </div>
                </div>
            )}
            {revision.isPending && (
                <div className="mt-4" role="status">
                    <div className="mb-2 flex justify-between text-sm text-text-secondary">
                        <span>Uploading immutable revision</span>
                        <span>{progress}%</span>
                    </div>
                    <Progress value={progress} />
                </div>
            )}
            <div className="mt-4 flex justify-end">
                <Button
                    type="button"
                    onClick={() => revision.mutate()}
                    disabled={!run.assetId || !file || revision.isPending}
                >
                    {revision.isPending ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                        <FileUp className="h-4 w-4" />
                    )}
                    Upload revision and compare
                </Button>
            </div>
        </SurfaceCard>
    );
}

function SummaryItem({ label, value }: { label: string; value: string }) {
    return (
        <div>
            <dt className="text-xs font-medium uppercase text-text-tertiary">{label}</dt>
            <dd className="mt-1 text-sm font-medium text-text-primary">{value}</dd>
        </div>
    );
}

function humanize(value: string) {
    return value
        .replace(/_v\d+$/, "")
        .replace(/_/g, " ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
