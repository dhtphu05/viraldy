# Adding A Job

Use durable jobs for work that can outlive an API request.

Required flow:

```text
API/service -> create processing_jobs row -> commit -> dispatcher -> Celery task -> service/repository -> DB progress/result
```

Rules:

- Pass stable IDs only, not binary data or large payloads.
- Store source of truth in PostgreSQL.
- Keep Redis as queue/coordination only.
- Make tasks idempotent.
- Keep Celery task functions thin.
- Keep state transitions in `jobs/service.py`, `jobs/policies.py`, or repository methods.

Current example:

- API entry: `modules/assets/router.py`
- Workflow: `modules/assets/service.py`
- Public job contract: `modules/jobs/public.py`
- Queue dispatcher: `modules/jobs/dispatcher.py`
- Worker task: `worker/tasks/process_asset.py`
