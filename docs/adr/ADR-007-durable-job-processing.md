# ADR-007 Durable Job Processing

Celery with Redis dispatches jobs, while PostgreSQL stores job records, progress, output, retry state, and idempotency keys.
