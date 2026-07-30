# Object Storage

Buckets are private. Uploads use short-lived presigned PUT URLs. Storage keys
never include original filenames or signed URLs.

## Hard Deletion

Hard deletion discovers keys from:

- asset versions;
- media artifact scalar keys and nested sampled-frame payloads;
- evidence scalar keys and nested multi-frame payloads;
- generation artifacts.

`fixtures/` keys are shared test assets and are never removed by tenant
deletion.

Business rows and a `storage_deletion_batches` outbox row are committed in the
same PostgreSQL transaction. Object deletion starts only after that commit.
S3-compatible DELETE is idempotent. A failed or partially completed batch stays
`pending`, records only a safe error, and is retried every five minutes by the
maintenance worker. The associated deletion audit remains
`storage_cleanup_pending` until the batch succeeds.

## Retention And Orphans

The workspace retention job:

- deletes `pending_upload` assets older than `ASSET_RETENTION_DAYS`;
- redacts model input/output summaries older than
  `MODEL_OUTPUT_RETENTION_DAYS`;
- lists `workspaces/{workspace_id}/` and removes objects older than the asset
  cutoff only when no database row references the key;
- protects recently modified objects and keys already owned by another pending
  cleanup batch.

Known referenced keys include asset versions, media artifacts and their nested
payload keys, evidence items and their nested frame keys, and generation
artifacts. Retention deletion uses the same durable outbox and retry path as
explicit hard deletion.

Run Celery workers with both queues and keep Beat active:

```bash
uv run celery -A viraldy.worker.celery_app worker --loglevel=INFO --queues=default,maintenance
uv run celery -A viraldy.worker.celery_app beat --loglevel=INFO
```

The retention job is requested per workspace through
`POST /api/v1/workspaces/{workspace_id}/deletions/retention`. It requires
`data.delete`.
