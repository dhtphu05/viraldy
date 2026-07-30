import { apiGet } from "./client";

export type JobStatus =
    "queued" | "running" | "retrying" | "succeeded" | "completed" | "failed" | "cancelled";

export type JobResponse = {
    id: string;
    workspace_id: string;
    subject_type: string;
    subject_id: string;
    job_type: string;
    status: JobStatus;
    progress: number;
    stage: string | null;
    output_json: Record<string, unknown> | null;
    error_code: string | null;
    error_message: string | null;
};

export function getJob(workspaceId: string, jobId: string) {
    return apiGet<JobResponse>(`/workspaces/${workspaceId}/jobs/${jobId}`);
}
