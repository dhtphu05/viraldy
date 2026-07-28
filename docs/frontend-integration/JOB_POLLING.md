# Job Polling

Clients poll `GET /api/v1/workspaces/{workspace_id}/jobs/{job_id}` until status is `completed`, `failed`, or `cancelled`.
