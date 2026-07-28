# Job Lifecycle

Main path:

```text
queued -> dispatching -> running -> completed
```

Retry/failure path:

```text
running -> retrying -> running -> failed
```

The foundation creates the database job before enqueueing Celery work. If dispatch fails, the durable job remains queued/dispatching for a future recovery command. Worker tasks load state from PostgreSQL, update progress stages, persist output, and store safe failure messages.
